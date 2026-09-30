# estate/apps.py

from django.apps import AppConfig


class EstateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'estate'

    def ready(self):
        # import estate.signals
        pass