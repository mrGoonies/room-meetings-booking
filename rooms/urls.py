from django.urls import path
from . import views

app_name = 'rooms'

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('bookings/new/', views.booking_create, name='booking_create'),
    path('bookings/<int:pk>/edit/', views.booking_edit, name='booking_edit'),
    path('bookings/<int:pk>/delete/', views.booking_delete, name='booking_delete'),
    path('bookings/availability/', views.booking_availability, name='booking_availability'),
]
