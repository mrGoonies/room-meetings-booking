from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking
from .emails import send_booking_confirmation


@receiver(post_save, sender=Booking)
def on_booking_saved(sender, instance, created, **kwargs):
    if created and instance.status == Booking.Status.CONFIRMED:
        try:
            send_booking_confirmation(instance)
        except Exception:
            # Log but don't crash the request if email fails
            import logging
            logging.getLogger(__name__).exception(
                'Error enviando email de confirmación para reserva pk=%s', instance.pk
            )
