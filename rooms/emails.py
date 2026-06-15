import logging
import threading
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import EXTRAS_MAP

logger = logging.getLogger(__name__)
COMPANY_NAME = getattr(settings, 'COMPANY_NAME', 'Tu Empresa')

# ── Emails por área ───────────────────────────────────────────────────────────
EQUIPMENT_EMAIL = 'soporte2.chile@irritec.com'
MATERIALS_EMAIL = 'marketing.chile@irritec.com'

EXTRAS_EQUIPMENT_KEYS = {'proyector', 'videoconferencia', 'pizarron'}
EXTRAS_MATERIALS_KEYS = {'decoracion', 'papeleria', 'impresiones'}

JEFATURA_MAP = {
    'comercial':      'german.hermosilla@irritec.com',
    'operaciones':    'ivan.bahamondes@irritec.com',
    'administracion': 'rudy.vasquez@irritec.com',
    'gerencia':       '',
}


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


# ── Notificaciones por área y jefatura ───────────────────────────────────────

def send_extras_notifications(booking):
    """Notifica a soporte2 (equipamiento) y marketing (materiales) según extras."""
    extras = set(booking.extras or [])

    if extras & EXTRAS_EQUIPMENT_KEYS:
        _send(
            subject=f'[Soporte] Equipamiento requerido: {booking.room} — {booking.start_datetime:%d/%m/%Y %H:%M}',
            template='rooms/email/area_notification.txt',
            booking=booking,
            recipient=EQUIPMENT_EMAIL,
        )

    if extras & EXTRAS_MATERIALS_KEYS:
        _send(
            subject=f'[Marketing] Materiales requeridos: {booking.room} — {booking.start_datetime:%d/%m/%Y %H:%M}',
            template='rooms/email/area_notification.txt',
            booking=booking,
            recipient=MATERIALS_EMAIL,
        )


def send_jefatura_notification(booking):
    """Notifica al jefe del área del usuario que agendó. Omite si el usuario es el propio jefe."""
    user = booking.created_by
    user_group_names = set(user.groups.values_list('name', flat=True))

    for group_name, jefatura_email in JEFATURA_MAP.items():
        if group_name in user_group_names:
            if user.email.lower() == jefatura_email.lower():
                logger.info(
                    'Notificación de jefatura omitida — el usuario es el jefe de su grupo (%s)',
                    group_name,
                )
                return
            _send(
                subject=f'Nueva reserva de sala: {booking.room} — {booking.start_datetime:%d/%m/%Y %H:%M}',
                template='rooms/email/area_notification.txt',
                booking=booking,
                recipient=jefatura_email,
            )
            return


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
