# estate/management/commands/seed_usage_types.py

from django.core.management.base import BaseCommand
from django.db import transaction
from estate.models import UsageType


class Command(BaseCommand):
    help = 'ایجاد انواع کاربری ملک پیش‌فرض در سیستم'

    def add_arguments(self, parser):
        """
        افزودن آرگومان‌های اختیاری برای کنترل عملیات
        """
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
        """
        اجرای اصلی کامند
        """
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)

        # ============================================================
        # لیست انواع کاربری پیش‌فرض
        # ============================================================
        usage_types = [
            {
                'name': 'مسکونی',
                'code': 'RESIDENTIAL',
                'icon': 'fa-home',
                'color': '#4CAF50',
                'description': 'مناسب برای سکونت و زندگی',
                'order': 1,
                'is_active': True
            },
            {
                'name': 'تجاری',
                'code': 'COMMERCIAL',
                'icon': 'fa-store',
                'color': '#2196F3',
                'description': 'مناسب برای کسب و کار و فروش',
                'order': 2,
                'is_active': True
            },
            {
                'name': 'اداری',
                'code': 'OFFICE',
                'icon': 'fa-briefcase',
                'color': '#FF9800',
                'description': 'مناسب برای دفاتر کاری و اداری',
                'order': 3,
                'is_active': True
            },
            {
                'name': 'صنعتی',
                'code': 'INDUSTRIAL',
                'icon': 'fa-industry',
                'color': '#9E9E9E',
                'description': 'مناسب برای فعالیت‌های صنعتی و تولیدی',
                'order': 4,
                'is_active': True
            },
            {
                'name': 'مختلط (مسکونی-تجاری)',
                'code': 'MIXED',
                'icon': 'fa-layer-group',
                'color': '#9C27B0',
                'description': 'مناسب برای استفاده همزمان مسکونی و تجاری',
                'order': 5,
                'is_active': True
            },
            {
                'name': 'کشاورزی',
                'code': 'AGRICULTURAL',
                'icon': 'fa-tractor',
                'color': '#8BC34A',
                'description': 'مناسب برای فعالیت‌های کشاورزی و باغداری',
                'order': 6,
                'is_active': True
            },
            {
                'name': 'خدماتی',
                'code': 'SERVICE',
                'icon': 'fa-concierge-bell',
                'color': '#00BCD4',
                'description': 'مناسب برای ارائه خدمات (آرایشگاه، تعمیرگاه، و...)',
                'order': 7,
                'is_active': True
            },
            {
                'name': 'آموزشی',
                'code': 'EDUCATIONAL',
                'icon': 'fa-graduation-cap',
                'color': '#3F51B5',
                'description': 'مناسب برای مدارس، دانشگاه‌ها و آموزشگاه‌ها',
                'order': 8,
                'is_active': True
            },
            {
                'name': 'پزشکی',
                'code': 'MEDICAL',
                'icon': 'fa-hospital',
                'color': '#F44336',
                'description': 'مناسب برای مطب‌ها، کلینیک‌ها و درمانگاه‌ها',
                'order': 9,
                'is_active': True
            },
            {
                'name': 'ورزشی',
                'code': 'SPORTS',
                'icon': 'fa-running',
                'color': '#FF5722',
                'description': 'مناسب برای باشگاه‌ها و فضاهای ورزشی',
                'order': 10,
                'is_active': True
            },
            {
                'name': 'تفریحی',
                'code': 'ENTERTAINMENT',
                'icon': 'fa-gamepad',
                'color': '#E91E63',
                'description': 'مناسب برای کافی‌نت‌ها، سینماها و مراکز تفریحی',
                'order': 11,
                'is_active': True
            },
            {
                'name': 'انبار و لجستیک',
                'code': 'WAREHOUSE',
                'icon': 'fa-warehouse',
                'color': '#607D8B',
                'description': 'مناسب برای انبارداری و توزیع کالا',
                'order': 12,
                'is_active': True
            },
            {
                'name': 'هتلی و اقامتی',
                'code': 'HOSPITALITY',
                'icon': 'fa-hotel',
                'color': '#795548',
                'description': 'مناسب برای هتل‌ها، مهمان‌سراها و اقامتگاه‌ها',
                'order': 13,
                'is_active': True
            },
            {
                'name': 'سایر',
                'code': 'OTHER',
                'icon': 'fa-ellipsis-h',
                'color': '#6c757d',
                'description': 'سایر کاربری‌هایی که در لیست بالا نیستند',
                'order': 14,
                'is_active': True
            },
        ]

        # ============================================================
        # اگر force=True باشد، همه موارد موجود را پاک می‌کند
        # ============================================================

        if force:
            if not dry_run:
                count = UsageType.objects.count()
                UsageType.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'⚠️ {count} نوع کاربری قدیمی حذف شدند'))
            else:
                self.stdout.write(self.style.WARNING('⚠️ [DRY-RUN] حذف انواع کاربری موجود'))

        # ============================================================
        # ایجاد یا بروزرسانی انواع کاربری
        # ============================================================

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for data in usage_types:
                code = data['code']

                # بررسی وجود یا عدم وجود
                existing = UsageType.objects.filter(code=code).first()

                if existing:
                    # بروزرسانی اگر تغییر کرده باشد
                    if not dry_run:
                        if force:
                            # در حالت force، همه فیلدها را بروزرسانی می‌کنیم
                            for key, value in data.items():
                                setattr(existing, key, value)
                            existing.save()
                            updated_count += 1
                            self.stdout.write(f'🔄 بروزرسانی: {existing.name} (code: {code})')
                        else:
                            # در حالت عادی، فقط فیلدهای خالی را پر می‌کنیم
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
                    # ایجاد جدید
                    if not dry_run:
                        obj = UsageType.objects.create(**data)
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'✅ ایجاد شد: {obj.name} (code: {code})'))
                    else:
                        self.stdout.write(f'🔍 [DRY-RUN] ایجاد: {data["name"]} (code: {code})')

        # ============================================================
        # نمایش گزارش نهایی
        # ============================================================

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ این یک اجرای DRY-RUN است و هیچ تغییری اعمال نشده است'))
        else:
            self.stdout.write('=' * 60)
            self.stdout.write(self.style.SUCCESS('📊 گزارش نهایی:'))
            self.stdout.write(f'   ✅ ایجاد شده: {created_count} مورد')
            self.stdout.write(f'   🔄 بروزرسانی: {updated_count} مورد')
            self.stdout.write(f'   ⏭️ بدون تغییر: {skipped_count} مورد')
            self.stdout.write(f'   📋 مجموع کل: {UsageType.objects.count()} نوع کاربری')
            self.stdout.write('=' * 60)
            self.stdout.write(self.style.SUCCESS('✅ عملیات با موفقیت انجام شد'))

    # ============================================================
    # متد کمکی برای نمایش اطلاعات
    # ============================================================

    def show_summary(self):
        """نمایش خلاصه اطلاعات موجود"""
        total = UsageType.objects.count()
        active = UsageType.objects.filter(is_active=True).count()
        inactive = UsageType.objects.filter(is_active=False).count()

        self.stdout.write('=' * 60)
        self.stdout.write('📊 خلاصه اطلاعات موجود:')
        self.stdout.write(f'   📋 مجموع کل: {total} نوع کاربری')
        self.stdout.write(f'   ✅ فعال: {active} مورد')
        self.stdout.write(f'   ❌ غیرفعال: {inactive} مورد')
        self.stdout.write('=' * 60)