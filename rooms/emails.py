import logging
import threading
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import EXTRAS_MAP

logger = logging.getLogger(__name__)
COMPANY_NAME = getattr(settings, 'COMPANY_NAME', 'Tu Empresa')


def _send(subject, template, booking):
    if not booking.attendee_email:
        return

    extras_labels = [EXTRAS_MAP.get(k, k) for k in (booking.extras or [])]
    # Renderizar en el hilo principal (puede acceder a la BD via contexto)
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
                recipient_list=[booking.attendee_email],
                fail_silently=False,
            )
        except Exception:
            logger.exception('Error enviando email "%s" a %s', subject, booking.attendee_email)

    threading.Thread(target=_do_send, daemon=True).start()


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
