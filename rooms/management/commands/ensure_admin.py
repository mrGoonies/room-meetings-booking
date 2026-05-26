import os
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crea el superusuario administrador si no existe ninguno'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_ADMIN_USER', 'admin')
        password = os.environ.get('DJANGO_ADMIN_PASSWORD')
        email    = os.environ.get('DJANGO_ADMIN_EMAIL', '')

        if not password:
            self.stdout.write(self.style.WARNING(
                'DJANGO_ADMIN_PASSWORD no definida — se omite la creación del admin.'
            ))
            return

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write('Superusuario ya existe — sin cambios.')
            return

        User.objects.create_superuser(username=username, password=password, email=email)
        self.stdout.write(self.style.SUCCESS(f'Superusuario "{username}" creado correctamente.'))
