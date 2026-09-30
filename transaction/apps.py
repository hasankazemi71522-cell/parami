# transaction/apps.py

from django.apps import AppConfig


class TransactionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'transaction'
    verbose_name = 'مدیریت معاملات و قراردادها'

    def ready(self):
        import transaction.signals