from django.contrib import admin
from django.utils.html import format_html
from .models import Room, Booking


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'room',
        'attendee_name',
        'attendee_email',
        'formatted_start',
        'formatted_end',
        'status_badge',
        'created_by',
    )
    list_filter = ('room', 'status', 'start_datetime')
    search_fields = ('title', 'attendee_name', 'attendee_email')
    date_hierarchy = 'start_datetime'
    readonly_fields = ('created_by', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('room', 'title', 'notes'),
        }),
        ('Asistente', {
            'fields': ('attendee_name', 'attendee_email'),
        }),
        ('Horario', {
            'fields': ('start_datetime', 'end_datetime'),
        }),
        ('Estado', {
            'fields': ('status',),
        }),
        ('Auditoría', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description='Inicio', ordering='start_datetime')
    def formatted_start(self, obj):
        return obj.start_datetime.strftime('%d/%m/%Y %H:%M')

    @admin.display(description='Fin', ordering='end_datetime')
    def formatted_end(self, obj):
        return obj.end_datetime.strftime('%d/%m/%Y %H:%M')

    @admin.display(description='Estado')
    def status_badge(self, obj):
        color = '#2ecc71' if obj.status == Booking.Status.CONFIRMED else '#e74c3c'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color,
            obj.get_status_display(),
        )
