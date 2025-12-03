# telegram_manager/urls.py (HTML - برای ادمین - فعلی)
from django.urls import path
from . import views

app_name = 'telegram_manager'

urlpatterns = [
    path('', views.message_list, name='message_list'),
    path('create/', views.create_message, name='create_message'),
    path('create/<uuid:channel_id>/', views.create_message, name='create_message_for_channel'),
    path('edit/<uuid:message_id>/', views.edit_message, name='edit_message'),
    path('send/<uuid:message_id>/', views.send_message, name='send_message'),
    path('delete/<uuid:message_id>/', views.delete_message, name='delete_message'),
]