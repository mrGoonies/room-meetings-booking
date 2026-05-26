from django.apps import AppConfig


class RoomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rooms'
    verbose_name = 'Salas de Reuniones'

    def ready(self):
        import rooms.signals  # noqa: F401
