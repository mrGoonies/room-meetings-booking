from django.db import models
from django.contrib.auth.models import User


EXTRAS_GROUPS = [
    {
        'label': 'Atención y catering',
        'icon': 'catering',
        'items': [
            ('agua_bebidas',    'Agua y bebidas'),
            ('cafe_te',         'Café / té'),
            ('galletas_snacks', 'Galletas / snacks'),
            ('catering',        'Catering completo'),
        ],
    },
    {
        'label': 'Equipamiento de sala',
        'icon': 'equipment',
        'items': [
            ('proyector',        'Proyector / pantalla'),
            ('videoconferencia', 'Videoconferencia (Teams, Zoom)'),
            ('pizarron',         'Pizarrón / whiteboard'),
        ],
    },
    {
        'label': 'Materiales',
        'icon': 'materials',
        'items': [
            ('decoracion',  'Decoración especial'),
            ('papeleria',   'Papelería (libretas, lapiceros)'),
            ('impresiones', 'Impresiones / documentos'),
        ],
    },
]

ALL_EXTRAS = [(k, v) for group in EXTRAS_GROUPS for k, v in group['items']]
EXTRAS_MAP  = dict(ALL_EXTRAS)


class Room(models.Model):
    name = models.CharField('Nombre', max_length=100, unique=True)
    description = models.TextField('Descripción', blank=True)
    capacity = models.PositiveSmallIntegerField('Capacidad (personas)', default=10)
    is_active = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name = 'Sala'
        verbose_name_plural = 'Salas'
        ordering = ['name']

    def __str__(self):
        return self.name


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', 'Confirmada'
        CANCELLED = 'cancelled', 'Cancelada'

    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        verbose_name='Sala',
        related_name='bookings',
        limit_choices_to={'is_active': True},
    )
    attendee_name = models.CharField('Nombre del asistente', max_length=200)
    attendee_email = models.EmailField('Correo del asistente')
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='Agendado por',
        related_name='bookings_created',
        editable=False,
    )
    title = models.CharField('Motivo / Título', max_length=200)
    start_datetime = models.DateTimeField('Inicio')
    end_datetime = models.DateTimeField('Fin')
    status = models.CharField(
        'Estado',
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED,
    )
    num_attendees = models.PositiveSmallIntegerField('Cantidad de asistentes', default=1)
    notes = models.TextField('Notas', blank=True)
    extras = models.JSONField('Servicios adicionales', default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['start_datetime']

    def __str__(self):
        return f'{self.room} — {self.title} ({self.start_datetime:%d/%m/%Y %H:%M})'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_datetime and self.end_datetime:
            if self.end_datetime <= self.start_datetime:
                raise ValidationError('La hora de fin debe ser posterior al inicio.')

            overlapping = Booking.objects.filter(
                room=self.room,
                status=Booking.Status.CONFIRMED,
                start_datetime__lt=self.end_datetime,
                end_datetime__gt=self.start_datetime,
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError(
                    f'La sala "{self.room}" ya tiene una reserva en ese horario.'
                )
