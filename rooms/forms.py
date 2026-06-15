import datetime
from django import forms
from django.utils import timezone
from .models import Room, Booking, ALL_EXTRAS


class BookingForm(forms.Form):

    def __init__(self, *args, exclude_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.exclude_pk = exclude_pk

    room = forms.ModelChoiceField(
        queryset=Room.objects.filter(is_active=True),
        label='Sala',
        empty_label='— Selecciona una sala —',
    )
    attendee_name = forms.CharField(label='Nombre completo', max_length=200)
    attendee_email = forms.EmailField(label='Correo electrónico')
    title = forms.CharField(label='Motivo / Título', max_length=200)
    num_attendees = forms.IntegerField(
        label='Cantidad de asistentes',
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'min': '1'}),
    )
    date = forms.DateField(
        label='Fecha',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    start_time = forms.TimeField(
        label='Hora de inicio',
        widget=forms.TimeInput(attrs={'type': 'time', 'step': '900'}),  # 15-min steps
    )
    end_time = forms.TimeField(
        label='Hora de fin',
        widget=forms.TimeInput(attrs={'type': 'time', 'step': '900'}),
    )
    notes = forms.CharField(
        label='Notas (opcional)',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    extras = forms.MultipleChoiceField(
        label='Servicios adicionales',
        choices=ALL_EXTRAS,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        room = cleaned_data.get('room')

        if not (date and start_time and end_time):
            return cleaned_data

        tz = timezone.get_current_timezone()
        start_dt = datetime.datetime.combine(date, start_time, tzinfo=tz)
        end_dt = datetime.datetime.combine(date, end_time, tzinfo=tz)

        if end_dt <= start_dt:
            self.add_error('end_time', 'La hora de fin debe ser posterior al inicio.')
            return cleaned_data

        if room:
            overlapping = Booking.objects.filter(
                room=room,
                status=Booking.Status.CONFIRMED,
                start_datetime__lt=end_dt,
                end_datetime__gt=start_dt,
            )
            if self.exclude_pk:
                overlapping = overlapping.exclude(pk=self.exclude_pk)
            if overlapping.exists():
                conflict = overlapping.first()
                s = timezone.localtime(conflict.start_datetime).strftime('%H:%M')
                e = timezone.localtime(conflict.end_datetime).strftime('%H:%M')
                raise forms.ValidationError(
                    f'La sala "{room}" ya tiene una reserva de {s} a {e} en ese horario.'
                )

        cleaned_data['start_datetime'] = start_dt
        cleaned_data['end_datetime'] = end_dt
        return cleaned_data
