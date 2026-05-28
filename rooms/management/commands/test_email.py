from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Envía un correo de prueba para verificar la configuración SMTP'

    def add_arguments(self, parser):
        parser.add_argument('recipient', type=str, help='Dirección de destino del correo de prueba')

    def handle(self, *args, **options):
        recipient = options['recipient']
        self.stdout.write(f'Configuración actual:')
        self.stdout.write(f'  BACKEND : {settings.EMAIL_BACKEND}')
        self.stdout.write(f'  HOST    : {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
        self.stdout.write(f'  USER    : {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'  FROM    : {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'  TLS     : {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'Enviando a: {recipient} ...')
        try:
            send_mail(
                subject='Prueba de email — Irritec Salas',
                message='Este es un correo de prueba del sistema de salas de reuniones.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS('Correo enviado correctamente.'))
        except Exception as e:
            raise CommandError(f'Error al enviar: {e}')
