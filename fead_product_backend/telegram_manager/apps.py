# telegram_manager/apps.py
from django.apps import AppConfig


class TelegramManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telegram_manager'
    verbose_name = 'Telegram Manager'