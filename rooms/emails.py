import logging
import threading
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import EXTRAS_MAP

logger = logging.getLogger(__name__)
COMPANY_NAME = getattr(settings, 'COMPANY_NAME', 'Tu Empresa')


def _send(subject, template, booking, recipient=None):
    target = recipient or booking.attendee_email
    if not target:
        return

    extras_labels = [EXTRAS_MAP.get(k, k) for k in (booking.extras or [])]
    body = render_to_string(template, {
        'booking': booking,
        'company_name': COMPANY_NAME,
        'extras_labels': extras_labels,
    })

    def _do_send():
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[target],
                fail_silently=False,
            )
        except Exception:
            logger.exception('Error enviando email "%s" a %s', subject, target)

    threading.Thread(target=_do_send, daemon=True).start()


# ── Correos al asistente ──────────────────────────────────────────────────────

def send_booking_confirmation(booking):
    _send(
        subject=f'Confirmación de sala: {booking.room} — {booking.start_datetime:%d/%m/%Y %H:%M}',
        template='rooms/email/booking_confirmation.txt',
        booking=booking,
    )


def send_booking_update(booking):
    _send(
        subject=f'Reserva modificada: {booking.room} — {booking.start_datetime:%d/%m/%Y %H:%M}',
        template='rooms/email/booking_update.txt',
        booking=booking,
    )


def send_booking_cancellation(booking):
    _send(
        subject=f'Reserva cancelada: {booking.room} — {booking.start_datetime:%d/%m/%Y %H:%M}',
        template='rooms/email/booking_cancellation.txt',
        booking=booking,
    )


# ── Notificaciones a recepción ────────────────────────────────────────────────

def send_reception_notification(booking, event='nueva'):
    reception_email = getattr(settings, 'RECEPTION_EMAIL', '')
    if not reception_email:
        logger.warning('RECEPTION_EMAIL no configurado — notificación a recepción omitida.')
        return

    subjects = {
        'nueva':      f'Nueva reserva: {booking.room} — {booking.start_datetime:%d/%m/%Y %H:%M}',
        'modificada': f'Reserva modificada: {booking.room} — {booking.start_datetime:%d/%m/%Y %H:%M}',
        'cancelada':  f'Reserva cancelada: {booking.room} — {booking.start_datetime:%d/%m/%Y %H:%M}',
    }

    extras_labels = [EXTRAS_MAP.get(k, k) for k in (booking.extras or [])]
    body = render_to_string('rooms/email/reception_notification.txt', {
        'booking': booking,
        'company_name': COMPANY_NAME,
        'extras_labels': extras_labels,
        'event': event,
    })

    def _do_send():
        try:
            send_mail(
                subject=subjects.get(event, subjects['nueva']),
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[reception_email],
                fail_silently=False,
            )
        except Exception:
            logger.exception('Error enviando notificación a recepción para reserva pk=%s', booking.pk)

    threading.Thread(target=_do_send, daemon=True).start()
