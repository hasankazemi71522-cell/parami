# estate/management/commands/seed_requirements.py

from django.core.management.base import BaseCommand
from estate.models import Requirement


class Command(BaseCommand):
    help = 'ایجاد نیازهای خاص پیش‌فرض'

    def handle(self, *args, **options):
        requirements = Requirement.get_default_requirements()

        for data in requirements:
            obj, created = Requirement.objects.get_or_create(
                code=data['code'],
                defaults=data
            )
            status = '✅ ایجاد شد' if created else '⚠️ از قبل وجود داشت'
            self.stdout.write(f'{status}: {obj.name}')

        self.stdout.write(self.style.SUCCESS('✅ عملیات با موفقیت انجام شد'))