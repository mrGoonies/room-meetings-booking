from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

GROUPS = ['comercial', 'operaciones', 'administracion', 'gerencia']


class Command(BaseCommand):
    help = 'Crea los grupos de usuario necesarios si no existen.'

    def handle(self, *args, **options):
        for name in GROUPS:
            _, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Grupo creado: {name}'))
            else:
                self.stdout.write(f'  Grupo ya existe: {name}')
