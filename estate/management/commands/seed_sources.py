# estate/management/commands/seed_sources.py

from django.core.management.base import BaseCommand
from estate.models import Source


class Command(BaseCommand):
    help = 'ایجاد منابع مشتری پیش‌فرض'

    def handle(self, *args, **options):
        sources = Source.get_default_sources()

        for data in sources:
            obj, created = Source.objects.get_or_create(
                code=data['code'],
                defaults=data
            )
            status = '✅ ایجاد شد' if created else '⚠️ از قبل وجود داشت'
            self.stdout.write(f'{status}: {obj.name}')

        self.stdout.write(self.style.SUCCESS('✅ عملیات با موفقیت انجام شد'))
