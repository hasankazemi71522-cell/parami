# estate/management/commands/seed_property_types.py

from django.core.management.base import BaseCommand
from django.db import transaction
from estate.models import PropertyType


class Command(BaseCommand):
    help = 'ایجاد انواع ملک پیش‌فرض در سیستم'

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
        # لیست انواع ملک پیش‌فرض
        # ============================================================
        property_types = [
            {
                'name': 'آپارتمان',
                'code': 'APARTMENT',
                'icon': 'fa-building',
                'description': 'واحد مسکونی در ساختمان‌های چند طبقه',
                'order': 1,
                'is_active': True
            },
            {
                'name': 'ویلا',
                'code': 'VILLA',
                'icon': 'fa-home',
                'description': 'ساختمان مسکونی مستقل با حیاط و فضای سبز',
                'order': 2,
                'is_active': True
            },
            {
                'name': 'زمین',
                'code': 'LAND',
                'icon': 'fa-tree',
                'description': 'زمین خالی برای ساخت و ساز',
                'order': 3,
                'is_active': True
            },
            {
                'name': 'تجاری',
                'code': 'COMMERCIAL',
                'icon': 'fa-store',
                'description': 'مکان‌های تجاری مانند مغازه، پاساژ، مرکز خرید',
                'order': 4,
                'is_active': True
            },
            {
                'name': 'دفتر کار',
                'code': 'OFFICE',
                'icon': 'fa-briefcase',
                'description': 'فضای اداری و دفتر کار',
                'order': 5,
                'is_active': True
            },
            {
                'name': 'انبار',
                'code': 'WAREHOUSE',
                'icon': 'fa-warehouse',
                'description': 'فضای انباری و نگهداری کالا',
                'order': 6,
                'is_active': True
            },
            {
                'name': 'مغازه',
                'code': 'SHOP',
                'icon': 'fa-shop',
                'description': 'واحد تجاری کوچک برای فروش کالا و خدمات',
                'order': 7,
                'is_active': True
            },
            {
                'name': 'ساختمان کلنگی',
                'code': 'BUILDING',
                'icon': 'fa-city',
                'description': 'ساختمان قدیمی نیازمند بازسازی یا نوسازی',
                'order': 8,
                'is_active': True
            },
            {
                'name': 'پروژه سرمایه‌گذاری',
                'code': 'PROJECT',
                'icon': 'fa-chart-line',
                'description': 'پروژه‌های ساخت و ساز و سرمایه‌گذاری',
                'order': 9,
                'is_active': True
            },
            {
                'name': 'مزرعه',
                'code': 'FARM',
                'icon': 'fa-tractor',
                'description': 'زمین‌های کشاورزی و باغات',
                'order': 10,
                'is_active': True
            },
            {
                'name': 'کارخانه',
                'code': 'FACTORY',
                'icon': 'fa-industry',
                'description': 'فضای صنعتی و کارخانه‌ای',
                'order': 11,
                'is_active': True
            },
            {
                'name': 'پارکینگ',
                'code': 'PARKING',
                'icon': 'fa-parking',
                'description': 'فضای پارکینگ و توقفگاه',
                'order': 12,
                'is_active': True
            },
            {
                'name': 'مسکن مهر',
                'code': 'MEHR_HOUSING',
                'icon': 'fa-house',
                'description': 'واحدهای مسکن مهر و طرح‌های حمایتی',
                'order': 13,
                'is_active': True
            },
            {
                'name': 'کلینیک',
                'code': 'CLINIC',
                'icon': 'fa-hospital',
                'description': 'فضای درمانی و کلینیکی',
                'order': 14,
                'is_active': True
            },
            {
                'name': 'آموزشی',
                'code': 'EDUCATIONAL',
                'icon': 'fa-graduation-cap',
                'description': 'فضای آموزشی مانند مدرسه، دانشگاه، آموزشگاه',
                'order': 15,
                'is_active': True
            },
        ]

        # ============================================================
        # اگر force=True باشد، همه موارد موجود را پاک می‌کند
        # ============================================================

        if force:
            if not dry_run:
                count = PropertyType.objects.count()
                PropertyType.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'⚠️ {count} نوع ملک قدیمی حذف شدند'))
            else:
                self.stdout.write(self.style.WARNING('⚠️ [DRY-RUN] حذف انواع ملک موجود'))

        # ============================================================
        # ایجاد یا بروزرسانی انواع ملک
        # ============================================================

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for data in property_types:
                code = data['code']

                # بررسی وجود یا عدم وجود
                existing = PropertyType.objects.filter(code=code).first()

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
                        obj = PropertyType.objects.create(**data)
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
            self.stdout.write(f'   📋 مجموع کل: {PropertyType.objects.count()} نوع ملک')
            self.stdout.write('=' * 60)
            self.stdout.write(self.style.SUCCESS('✅ عملیات با موفقیت انجام شد'))

    # ============================================================
    # متد کمکی برای نمایش اطلاعات
    # ============================================================

    def show_summary(self):
        """نمایش خلاصه اطلاعات موجود"""
        total = PropertyType.objects.count()
        active = PropertyType.objects.filter(is_active=True).count()
        inactive = PropertyType.objects.filter(is_active=False).count()

        self.stdout.write('=' * 60)
        self.stdout.write('📊 خلاصه اطلاعات موجود:')
        self.stdout.write(f'   📋 مجموع کل: {total} نوع ملک')
        self.stdout.write(f'   ✅ فعال: {active} مورد')
        self.stdout.write(f'   ❌ غیرفعال: {inactive} مورد')
        self.stdout.write('=' * 60)