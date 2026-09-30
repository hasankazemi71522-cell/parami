# estate/management/commands/seed_orientations.py

from django.core.management.base import BaseCommand
from django.db import transaction
from estate.models import Orientation


class Command(BaseCommand):
    help = 'ایجاد جهت‌های پیش‌فرض در سیستم'

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

        orientations = [
            {'name': 'شمالی', 'code': 'NORTH', 'icon': 'fa-arrow-up', 'order': 1},
            {'name': 'جنوبی', 'code': 'SOUTH', 'icon': 'fa-arrow-down', 'order': 2},
            {'name': 'شرقی', 'code': 'EAST', 'icon': 'fa-arrow-right', 'order': 3},
            {'name': 'غربی', 'code': 'WEST', 'icon': 'fa-arrow-left', 'order': 4},
            {'name': 'شمال شرقی', 'code': 'NORTH_EAST', 'icon': 'fa-arrow-up-right', 'order': 5},
            {'name': 'شمال غربی', 'code': 'NORTH_WEST', 'icon': 'fa-arrow-up-left', 'order': 6},
            {'name': 'جنوب شرقی', 'code': 'SOUTH_EAST', 'icon': 'fa-arrow-down-right', 'order': 7},
            {'name': 'جنوب غربی', 'code': 'SOUTH_WEST', 'icon': 'fa-arrow-down-left', 'order': 8},
        ]

        if force and not dry_run:
            count = Orientation.objects.count()
            Orientation.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'⚠️ {count} جهت قدیمی حذف شدند'))

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for data in orientations:
                code = data['code']
                existing = Orientation.objects.filter(code=code).first()

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
                        obj = Orientation.objects.create(**data)
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
            self.stdout.write(f'   📋 مجموع کل: {Orientation.objects.count()} جهت')
            self.stdout.write('=' * 60)
            self.stdout.write(self.style.SUCCESS('✅ عملیات با موفقیت انجام شد'))