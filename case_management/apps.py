# case_management/apps.py

from django.apps import AppConfig


class CaseManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'case_management'
    verbose_name = "مدیریت پرونده‌ها (کیس‌ها)"

    def ready(self):
        import case_management.signals  # noqa