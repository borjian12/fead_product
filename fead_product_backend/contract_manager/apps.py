# contract_manager/apps.py
from django.apps import AppConfig


class ContractManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'contract_manager'
    verbose_name = 'Contract Manager'

    def ready(self):
        # برای سیگنال‌ها اگر نیاز باشد
        pass