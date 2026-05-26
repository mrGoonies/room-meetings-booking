import datetime
import logging
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from .models import Room, Booking, EXTRAS_GROUPS
from .forms import BookingForm
from .emails import send_booking_update, send_booking_cancellation

logger = logging.getLogger(__name__)

DAY_START = 7
DAY_END = 21
PX_PER_HOUR = 60

ROOM_COLORS = ['#1B6535', '#2D8448', '#0D4D22', '#4DA870']

MONTHS_ES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]
DAYS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
DAYS_ABBR = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do']


@login_required
def calendar_view(request):
    date_str = request.GET.get('date')
    try:
        selected_date = date.fromisoformat(date_str)
    except (TypeError, ValueError):
        selected_date = timezone.localdate()

    rooms = list(Room.objects.filter(is_active=True))

    hours = [
        {'label': f'{h:02d}:00', 'top': (h - DAY_START) * PX_PER_HOUR}
        for h in range(DAY_START, DAY_END + 1)
    ]
    grid_height = (DAY_END - DAY_START) * PX_PER_HOUR

    rooms_data = []
    for idx, room in enumerate(rooms):
        color = ROOM_COLORS[idx % len(ROOM_COLORS)]
        bookings_qs = Booking.objects.filter(
            room=room,
            status=Booking.Status.CONFIRMED,
            start_datetime__date=selected_date,
        )
        bookings = []
        for b in bookings_qs:
            s = timezone.localtime(b.start_datetime)
            e = timezone.localtime(b.end_datetime)
            start_min = (s.hour - DAY_START) * 60 + s.minute
            end_min = (e.hour - DAY_START) * 60 + e.minute
            top = max(0, start_min)
            height = max(24, min(end_min, (DAY_END - DAY_START) * 60) - top)
            bookings.append({
                'obj': b,
                'top': top,
                'height': height,
                'start_str': s.strftime('%H:%M'),
                'end_str': e.strftime('%H:%M'),
            })
        rooms_data.append({'room': room, 'bookings': bookings, 'color': color})

    today = timezone.localdate()
    date_display = (
        f"{DAYS_ES[selected_date.weekday()]}, "
        f"{selected_date.day} de "
        f"{MONTHS_ES[selected_date.month - 1]} de "
        f"{selected_date.year}"
    )

    week_start = selected_date - timedelta(days=selected_date.weekday())
    week_days = [
        {
            'date_iso': (week_start + timedelta(days=i)).isoformat(),
            'day_abbr': DAYS_ABBR[i],
            'day_num': (week_start + timedelta(days=i)).day,
            'is_selected': (week_start + timedelta(days=i)) == selected_date,
            'is_today': (week_start + timedelta(days=i)) == today,
        }
        for i in range(7)
    ]

    context = {
        'selected_date': selected_date,
        'date_display': date_display,
        'prev_date': (selected_date - timedelta(days=1)).isoformat(),
        'next_date': (selected_date + timedelta(days=1)).isoformat(),
        'prev_week': (selected_date - timedelta(days=7)).isoformat(),
        'next_week': (selected_date + timedelta(days=7)).isoformat(),
        'week_days': week_days,
        'rooms_data': rooms_data,
        'hours': hours,
        'grid_height': grid_height,
        'today': today,
        'is_today': selected_date == today,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'rooms/partials/calendar_grid.html', context)

    template = 'rooms/calendar.html' if request.user.is_staff else 'rooms/calendar_viewer.html'
    return render(request, template, context)


@staff_member_required
def booking_create(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = Booking(
                room=form.cleaned_data['room'],
                attendee_name=form.cleaned_data['attendee_name'],
                attendee_email=form.cleaned_data['attendee_email'],
                title=form.cleaned_data['title'],
                start_datetime=form.cleaned_data['start_datetime'],
                end_datetime=form.cleaned_data['end_datetime'],
                notes=form.cleaned_data.get('notes', ''),
                extras=form.cleaned_data.get('extras', []),
                created_by=request.user,
            )
            booking.save()
            redirect_date = form.cleaned_data['date'].isoformat()
            return redirect(f'/?date={redirect_date}')
    else:
        initial_date = request.GET.get('date', timezone.localdate().isoformat())
        initial_room = request.GET.get('room')
        initial = {'date': initial_date}
        if initial_room:
            initial['room'] = initial_room
        form = BookingForm(initial=initial)

    return render(request, 'rooms/booking_form.html', {'form': form, 'extras_groups': EXTRAS_GROUPS})


@staff_member_required
def booking_edit(request, pk):
    booking = get_object_or_404(Booking, pk=pk)

    if request.method == 'POST':
        form = BookingForm(request.POST, exclude_pk=pk)
        if form.is_valid():
            booking.room = form.cleaned_data['room']
            booking.attendee_name = form.cleaned_data['attendee_name']
            booking.attendee_email = form.cleaned_data['attendee_email']
            booking.title = form.cleaned_data['title']
            booking.start_datetime = form.cleaned_data['start_datetime']
            booking.end_datetime = form.cleaned_data['end_datetime']
            booking.notes = form.cleaned_data.get('notes', '')
            booking.extras = form.cleaned_data.get('extras', [])
            booking.save()
            try:
                send_booking_update(booking)
            except Exception:
                logger.exception('Error enviando email de modificación para reserva pk=%s', booking.pk)
            return redirect(f'/?date={form.cleaned_data["date"].isoformat()}')
    else:
        local_start = timezone.localtime(booking.start_datetime)
        local_end = timezone.localtime(booking.end_datetime)
        form = BookingForm(
            exclude_pk=pk,
            initial={
                'room': booking.room_id,
                'attendee_name': booking.attendee_name,
                'attendee_email': booking.attendee_email,
                'title': booking.title,
                'date': local_start.date(),
                'start_time': local_start.time(),
                'end_time': local_end.time(),
                'notes': booking.notes,
            'extras': booking.extras,
            },
        )

    local_start = timezone.localtime(booking.start_datetime)
    return render(request, 'rooms/booking_form.html', {
        'form': form,
        'booking': booking,
        'extras_groups': EXTRAS_GROUPS,
        'redirect_date': local_start.date().isoformat(),
    })


@staff_member_required
def booking_delete(request, pk):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, pk=pk)
        redirect_date = timezone.localtime(booking.start_datetime).date().isoformat()
        try:
            send_booking_cancellation(booking)
        except Exception:
            logger.exception('Error enviando email de cancelación para reserva pk=%s', booking.pk)
        booking.delete()
        return redirect(f'/?date={redirect_date}')
    return redirect('rooms:calendar')


@login_required
def booking_availability(request):
    room_id = request.GET.get('room')
    date_str = request.GET.get('date')
    bookings = []
    room = None
    selected_date = None

    if room_id and date_str:
        try:
            room = Room.objects.get(pk=room_id, is_active=True)
            selected_date = datetime.date.fromisoformat(date_str)
            qs = Booking.objects.filter(
                room=room,
                status=Booking.Status.CONFIRMED,
                start_datetime__date=selected_date,
            ).order_by('start_datetime')
            for b in qs:
                s = timezone.localtime(b.start_datetime)
                e = timezone.localtime(b.end_datetime)
                bookings.append({
                    'obj': b,
                    'start_str': s.strftime('%H:%M'),
                    'end_str': e.strftime('%H:%M'),
                })
        except (Room.DoesNotExist, ValueError):
            pass

    context = {
        'bookings': bookings,
        'room': room,
        'selected_date': selected_date,
    }
    return render(request, 'rooms/partials/availability.html', context)
