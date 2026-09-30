# estate/management/commands/seed_unit_conditions.py

from django.core.management.base import BaseCommand
from django.db import transaction
from estate.models import UnitCondition


class Command(BaseCommand):
    help = 'ایجاد وضعیت‌های واحد پیش‌فرض در سیستم'

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
        parser.add_argument(
            '--with-install',
            action='store_true',
            help='حالت نصب: در صورت نبود داده، ایجاد کن و در صورت وجود داده، بروزرسانی کن (رفتار پیش‌فرض)'
        )
        parser.add_argument(
            '--without-install',
            action='store_true',
            help='حالت بدون نصب: فقط داده‌های موجود را بروزرسانی کن (بدون ایجاد جدید)'
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)
        with_install = options.get('with_install', False)
        without_install = options.get('without_install', False)

        # اگر هیچکدام مشخص نشده باشد، with_install پیش‌فرض است
        if not with_install and not without_install:
            with_install = True
            self.stdout.write(self.style.WARNING('⚠️ حالت with-install (پیش‌فرض) فعال شد'))

        # اگر هر دو فعال باشند، without_install اولویت دارد
        if with_install and without_install:
            self.stdout.write(self.style.WARNING('⚠️ هر دو حالت with-install و without-install فعال هستند. without-install اولویت دارد.'))
            with_install = False

        conditions = [
            {'name': 'مبله', 'code': 'FURNISHED', 'icon': 'fa-couch', 'order': 1},
            {'name': 'نیمه مبله', 'code': 'SEMI_FURNISHED', 'icon': 'fa-chair', 'order': 2},
            {'name': 'خالی', 'code': 'UNFURNISHED', 'icon': 'fa-door-open', 'order': 3},
            # 🆕 دو وضعیت جدید با نصبیات و بدون نصبیات
            {'name': 'با نصبیات', 'code': 'WITH_INSTALLATION', 'icon': 'fa-tools', 'order': 4},
            {'name': 'بدون نصبیات', 'code': 'WITHOUT_INSTALLATION', 'icon': 'fa-times-circle', 'order': 5},
        ]

        if force and not dry_run:
            count = UnitCondition.objects.count()
            UnitCondition.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'⚠️ {count} وضعیت واحد قدیمی حذف شدند'))

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for data in conditions:
                code = data['code']
                existing = UnitCondition.objects.filter(code=code).first()

                if existing:
                    # ====== رکورد موجود است ======
                    if not dry_run:
                        if force:
                            # حالت force: همه فیلدها را بروزرسانی کن
                            for key, value in data.items():
                                setattr(existing, key, value)
                            existing.save()
                            updated_count += 1
                            self.stdout.write(f'🔄 بروزرسانی (اجباری): {existing.name} (code: {code})')
                        else:
                            # حالت عادی: فقط فیلدهای خالی را پر کن
                            changed = False
                            for key, value in data.items():
                                if key != 'code':
                                    current_value = getattr(existing, key)
                                    if current_value in [None, '', []]:
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
                    # ====== رکورد وجود ندارد ======
                    if without_install:
                        # حالت without-install: رکورد جدید ایجاد نمی‌شود
                        skipped_count += 1
                        self.stdout.write(self.style.WARNING(f'⏭️ [بدون نصب] رد شد: {data["name"]} (code: {code})'))
                    else:
                        # حالت with-install: ایجاد جدید
                        if not dry_run:
                            obj = UnitCondition.objects.create(**data)
                            created_count += 1
                            self.stdout.write(self.style.SUCCESS(f'✅ ایجاد شد: {obj.name} (code: {code})'))
                        else:
                            self.stdout.write(f'🔍 [DRY-RUN] ایجاد: {data["name"]} (code: {code})')

        # ====== گزارش نهایی ======
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ این یک اجرای DRY-RUN است و هیچ تغییری اعمال نشده است'))
        else:
            self.stdout.write('=' * 60)
            self.stdout.write(self.style.SUCCESS('📊 گزارش نهایی:'))
            self.stdout.write(f'   ✅ ایجاد شده: {created_count} مورد')
            self.stdout.write(f'   🔄 بروزرسانی: {updated_count} مورد')
            self.stdout.write(f'   ⏭️ بدون تغییر/رد شده: {skipped_count} مورد')
            self.stdout.write(f'   📋 مجموع کل: {UnitCondition.objects.count()} وضعیت واحد')
            self.stdout.write('=' * 60)
            self.stdout.write(self.style.SUCCESS('✅ عملیات با موفقیت انجام شد'))