# estate/management/commands/seed_ownership_document_types.py

from django.core.management.base import BaseCommand
from django.db import transaction
from estate.models import OwnershipDocumentType


class Command(BaseCommand):
    help = 'ایجاد انواع مالکیت سند پیش‌فرض در سیستم'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='اجبار به بازنشانی داده‌های موجود (حذف و ایجاد مجدد)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='نمایش عملیات بدون اجرای واقعی'
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)

        ownership_types = [
            {'name': 'شخصی', 'code': 'PRIVATE', 'order': 1},
            {'name': 'اوقاف', 'code': 'WAQF', 'order': 2},
            {'name': 'دولتی', 'code': 'GOVERNMENT', 'order': 3},
            {'name': 'نظامی', 'code': 'MILITARY', 'order': 4},
            {'name': 'سایر', 'code': 'OTHER', 'order': 5},
        ]

        if force and not dry_run:
            count = OwnershipDocumentType.objects.count()
            OwnershipDocumentType.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'⚠️ {count} نوع مالکیت سند قدیمی حذف شدند'))

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for data in ownership_types:
                code = data['code']
                existing = OwnershipDocumentType.objects.filter(code=code).first()

                if existing:
                    if not dry_run:
                        if force:
                            for key, value in data.items():
                                setattr(existing, key, value)
                            existing.save()
                            updated_count += 1
                            self.stdout.write(f'🔄 بروزرسانی: {existing.name} (code: {code})')
                        else:
                            changed = False
                            for key, value in data.items():
                                if key != 'code' and getattr(existing, key) in [None, '']:
                                    setattr(existing, key, value)
                                    changed = True
                            if changed:
                                existing.save()
                                updated_count += 1
                                self.stdout.write(f'🔄 تکمیل اطلاعات: {existing.name} (code: {code})')
                            else:
                                skipped_count += 1
                                self.stdout.write(f'⏭️ بدون تغییر: {existing.name} (code: {code})')
                    else:
                        self.stdout.write(f'🔍 [DRY-RUN] بروزرسانی: {data["name"]} (code: {code})')
                else:
                    if not dry_run:
                        obj = OwnershipDocumentType.objects.create(**data)
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'✅ ایجاد شد: {obj.name} (code: {code})'))
                    else:
                        self.stdout.write(f'🔍 [DRY-RUN] ایجاد: {data["name"]} (code: {code})')

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ این یک اجرای DRY-RUN است و هیچ تغییری اعمال نشده است'))
        else:
            self.stdout.write('=' * 60)
            self.stdout.write(self.style.SUCCESS('📊 گزارش نهایی:'))
            self.stdout.write(f'   ✅ ایجاد شده: {created_count} مورد')
            self.stdout.write(f'   🔄 بروزرسانی: {updated_count} مورد')
            self.stdout.write(f'   ⏭️ بدون تغییر: {skipped_count} مورد')
            self.stdout.write(f'   📋 مجموع کل: {OwnershipDocumentType.objects.count()} نوع مالکیت سند')
            self.stdout.write('=' * 60)
            self.stdout.write(self.style.SUCCESS('✅ عملیات با موفقیت انجام شد'))