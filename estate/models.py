# estate/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import jdatetime
import json

User = get_user_model()


# ============================================================
# 📌 مدل‌های پایه (Base Models)
# ============================================================

class TimeStampedModel(models.Model):
    """مدل پایه با زمان‌های ثبت و بروزرسانی"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """مدل پایه با حذف نرم"""
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ حذف")

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_active = True
        self.deleted_at = None
        self.save()


class UUIDModel(models.Model):
    """مدل پایه با UUID به جای ID عددی"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="شناسه یکتا"
    )

    class Meta:
        abstract = True


# ============================================================
# 📍 مدل‌های مکان و آدرس
# ============================================================

class Province(models.Model):
    """استان"""
    name = models.CharField(max_length=100, unique=True, verbose_name="نام استان")
    code = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="کد استان")

    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"
        ordering = ['name']

    def __str__(self):
        return self.name


class City(models.Model):
    """شهر"""
    province = models.ForeignKey(
        Province,
        on_delete=models.PROTECT,
        related_name='cities',
        verbose_name="استان"
    )
    name = models.CharField(max_length=100, verbose_name="نام شهر")
    code = models.CharField(max_length=100, null=True, blank=True, verbose_name="کد شهر")

    center_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="عرض جغرافیایی مرکز"
    )
    center_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="طول جغرافیایی مرکز"
    )

    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"
        ordering = ['province__name', 'name']
        unique_together = ['province', 'name']

    def __str__(self):
        return f"{self.name} - {self.province.name}"


class Neighborhood(models.Model):
    """محله"""
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='neighborhoods',
        verbose_name="شهر"
    )
    name = models.CharField(max_length=200, verbose_name="نام محله")

    center_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="عرض جغرافیایی مرکز"
    )
    center_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="طول جغرافیایی مرکز"
    )

    class Meta:
        verbose_name = "محله"
        verbose_name_plural = "محله‌ها"
        ordering = ['city__name', 'name']
        unique_together = ['city', 'name']

    def __str__(self):
        return f"{self.name} - {self.city.name}"


# ============================================================
# 🏠 مدل انواع ملک (PropertyType)
# ============================================================

class PropertyType(models.Model):
    """انواع ملک - قابل مدیریت در ادمین"""

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="نام نوع ملک"
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="کد نوع ملک",
        help_text="مثال: APARTMENT, VILLA, LAND"
    )
    icon = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="آیکون",
        help_text="نام کلاس آیکون (مثلاً fa-building)"
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="توضیحات"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ بروزرسانی"
    )

    class Meta:
        verbose_name = "نوع ملک"
        verbose_name_plural = "انواع ملک"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


# ============================================================
# 🏢 مدل انواع کاربری ملک (UsageType)
# ============================================================

class UsageType(models.Model):
    """
    انواع کاربری ملک
    مشخص می‌کند ملک برای چه کاربری‌هایی مناسب است
    قابل مدیریت کامل در پنل ادمین
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="نام کاربری",
        help_text="مثال: مسکونی، تجاری، اداری، صنعتی، مختلط، کشاورزی"
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="کد کاربری",
        help_text="مثال: RESIDENTIAL, COMMERCIAL, OFFICE, INDUSTRIAL, MIXED, AGRICULTURAL"
    )

    icon = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="آیکون",
        help_text="نام کلاس آیکون (مثلاً fa-home, fa-store, fa-briefcase)"
    )

    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="توضیحات",
        help_text="توضیحات کامل درباره این نوع کاربری"
    )

    color = models.CharField(
        max_length=20,
        default='#6c757d',
        verbose_name="رنگ",
        help_text="رنگ HEX برای نمایش در داشبورد (مثلاً #4CAF50)"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ بروزرسانی"
    )

    class Meta:
        verbose_name = "نوع کاربری"
        verbose_name_plural = "انواع کاربری"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @classmethod
    def get_default_usages(cls):
        """لیست کاربری‌های پیش‌فرض"""
        return [
            {'name': 'مسکونی', 'code': 'RESIDENTIAL', 'icon': 'fa-home', 'color': '#4CAF50', 'order': 1},
            {'name': 'تجاری', 'code': 'COMMERCIAL', 'icon': 'fa-store', 'color': '#2196F3', 'order': 2},
            {'name': 'اداری', 'code': 'OFFICE', 'icon': 'fa-briefcase', 'color': '#FF9800', 'order': 3},
            {'name': 'صنعتی', 'code': 'INDUSTRIAL', 'icon': 'fa-industry', 'color': '#9E9E9E', 'order': 4},
            {'name': 'مختلط (مسکونی-تجاری)', 'code': 'MIXED', 'icon': 'fa-layer-group', 'color': '#9C27B0', 'order': 5},
            {'name': 'کشاورزی', 'code': 'AGRICULTURAL', 'icon': 'fa-tractor', 'color': '#8BC34A', 'order': 6},
            {'name': 'خدماتی', 'code': 'SERVICE', 'icon': 'fa-concierge-bell', 'color': '#00BCD4', 'order': 7},
            {'name': 'آموزشی', 'code': 'EDUCATIONAL', 'icon': 'fa-graduation-cap', 'color': '#3F51B5', 'order': 8},
            {'name': 'پزشکی', 'code': 'MEDICAL', 'icon': 'fa-hospital', 'color': '#F44336', 'order': 9},
            {'name': 'ورزشی', 'code': 'SPORTS', 'icon': 'fa-running', 'color': '#FF5722', 'order': 10},
            {'name': 'تفریحی', 'code': 'ENTERTAINMENT', 'icon': 'fa-gamepad', 'color': '#E91E63', 'order': 11},
            {'name': 'انبار و لجستیک', 'code': 'WAREHOUSE', 'icon': 'fa-warehouse', 'color': '#607D8B', 'order': 12},
            {'name': 'هتلی و اقامتی', 'code': 'HOSPITALITY', 'icon': 'fa-hotel', 'color': '#795548', 'order': 13},
            {'name': 'سایر', 'code': 'OTHER', 'icon': 'fa-ellipsis-h', 'color': '#6c757d', 'order': 14},
        ]


# ============================================================
# 🆕 مدل نیازهای خاص (Requirement)
# ============================================================

class Requirement(models.Model):
    """
    مدل نیازهای خاص یا امکانات ملک
    قابل مدیریت کامل در پنل ادمین
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="نام نیاز",
        help_text="مثال: پارکینگ، آسانسور، انباری"
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="کد نیاز",
        help_text="مثال: PARKING, ELEVATOR, WAREHOUSE"
    )

    icon = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="آیکون",
        help_text="نام کلاس آیکون (مثلاً fa-car, fa-elevator)"
    )

    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="توضیحات"
    )

    category = models.CharField(
        max_length=50,
        default='general',
        verbose_name="دسته‌بندی",
        help_text="دسته‌بندی کلی نیاز (مثلاً: ساختمانی، امنیتی، رفاهی، زیرساخت)"
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ بروزرسانی"
    )

    class Meta:
        verbose_name = "نیاز خاص"
        verbose_name_plural = "نیازهای خاص"
        ordering = ['category', 'order', 'name']

    def __str__(self):
        return self.name

    @classmethod
    def get_default_requirements(cls):
        defaults = [
            {'name': 'پارکینگ', 'code': 'PARKING', 'icon': 'fa-car', 'category': 'ساختمانی'},
            {'name': 'آسانسور', 'code': 'ELEVATOR', 'icon': 'fa-arrow-up', 'category': 'ساختمانی'},
            {'name': 'انباری', 'code': 'WAREHOUSE', 'icon': 'fa-boxes', 'category': 'ساختمانی'},
            {'name': 'بالکن', 'code': 'BALCONY', 'icon': 'fa-archway', 'category': 'ساختمانی'},
            {'name': 'حیاط', 'code': 'YARD', 'icon': 'fa-tree', 'category': 'فضای باز'},
            {'name': 'استخر', 'code': 'POOL', 'icon': 'fa-swimmer', 'category': 'رفاهی'},
            {'name': 'سالن ورزشی', 'code': 'GYM', 'icon': 'fa-dumbbell', 'category': 'رفاهی'},
            {'name': 'نگهبانی', 'code': 'SECURITY', 'icon': 'fa-shield-alt', 'category': 'امنیتی'},
            {'name': 'فضای سبز', 'code': 'GREEN_SPACE', 'icon': 'fa-leaf', 'category': 'فضای باز'},
            {'name': 'حیوانات مجاز', 'code': 'PET_FRIENDLY', 'icon': 'fa-dog', 'category': 'سایر'},
            {'name': 'مبله', 'code': 'FURNISHED', 'icon': 'fa-couch', 'category': 'داخلی'},
            {'name': 'خانه هوشمند', 'code': 'SMART_HOME', 'icon': 'fa-microchip', 'category': 'زیرساخت'},
            {'name': 'گرمایش مرکزی', 'code': 'CENTRAL_HEATING', 'icon': 'fa-fire', 'category': 'ساختمانی'},
            {'name': 'مناسب معلولین', 'code': 'DISABLED_ACCESS', 'icon': 'fa-wheelchair', 'category': 'دسترسی'},
            {'name': 'شومینه', 'code': 'FIREPLACE', 'icon': 'fa-fireplace', 'category': 'رفاهی'},
            {'name': 'سونا', 'code': 'SAUNA', 'icon': 'fa-hot-tub', 'category': 'رفاهی'},
            {'name': 'جکوزی', 'code': 'JACUZZI', 'icon': 'fa-bath', 'category': 'رفاهی'},
            {'name': 'زمین بازی', 'code': 'PLAYGROUND', 'icon': 'fa-child', 'category': 'فضای باز'},
            {'name': 'دوجداره', 'code': 'DOUBLE_GLAZED', 'icon': 'fa-window-maximize', 'category': 'ساختمانی'},
            {'name': 'در ضد سرقت', 'code': 'METAL_DOOR', 'icon': 'fa-door-closed', 'category': 'امنیتی'},
            {'name': 'دوربین مداربسته', 'code': 'CAMERA', 'icon': 'fa-video', 'category': 'امنیتی'},
            {'name': 'آیفون', 'code': 'INTERCOM', 'icon': 'fa-phone-alt', 'category': 'زیرساخت'},
            {'name': 'فیبر نوری', 'code': 'FIBER_OPTIC', 'icon': 'fa-network-wired', 'category': 'زیرساخت'},
            {'name': 'ژنراتور', 'code': 'GENERATOR', 'icon': 'fa-bolt', 'category': 'زیرساخت'},
            {'name': 'سالن مطالعه', 'code': 'READING_ROOM', 'icon': 'fa-book-open', 'category': 'رفاهی'},
            {'name': 'سالن اجتماعات', 'code': 'MEETING_HALL', 'icon': 'fa-users', 'category': 'رفاهی'},
            {'name': 'لابی', 'code': 'LOBBY', 'icon': 'fa-building', 'category': 'ساختمانی'},
            {'name': 'شارژ خودرو برقی', 'code': 'EV_CHARGER', 'icon': 'fa-charging-station', 'category': 'زیرساخت'},
            {'name': 'روف گاردن', 'code': 'ROOF_GARDEN', 'icon': 'fa-seedling', 'category': 'فضای باز'},
            {'name': 'داکت اسپلیت', 'code': 'DUCT_SPLIT', 'icon': 'fa-snowflake', 'category': 'تأسیسات'},
            {'name': 'شیرآلات توکار', 'code': 'BUILT_IN_FAUCETS', 'icon': 'fa-faucet', 'category': 'داخلی'},
        ]
        return defaults


# ============================================================
# 🆕 مدل منبع مشتری (Source)
# ============================================================

class Source(models.Model):
    """
    مدل منابع مشتری
    قابل مدیریت کامل در پنل ادمین
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="نام منبع",
        help_text="مثال: دیوار، شیپور، اینستاگرام"
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="کد منبع",
        help_text="مثال: DIVAR, SHIPOUR, INSTAGRAM"
    )

    icon = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="آیکون",
        help_text="نام کلاس آیکون (مثلاً fa-instagram)"
    )

    color = models.CharField(
        max_length=20,
        default='#6c757d',
        verbose_name="رنگ",
        help_text="رنگ HEX برای نمایش در داشبورد (مثلاً #e4405f)"
    )

    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="توضیحات"
    )

    category = models.CharField(
        max_length=50,
        default='online',
        verbose_name="دسته‌بندی منبع",
        help_text="مثال: آنلاین، شبکه‌های اجتماعی، معرفی، آفلاین"
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ بروزرسانی"
    )

    class Meta:
        verbose_name = "منبع"
        verbose_name_plural = "منابع مشتری"
        ordering = ['category', 'order', 'name']

    def __str__(self):
        return self.name

    @classmethod
    def get_default_sources(cls):
        defaults = [
            {'name': 'دیوار', 'code': 'DIVAR', 'icon': 'fa-ad', 'color': '#00aaff', 'category': 'آنلاین'},
            {'name': 'شیپور', 'code': 'SHIPOUR', 'icon': 'fa-bullhorn', 'color': '#ff6b00', 'category': 'آنلاین'},
            {'name': 'اینستاگرام', 'code': 'INSTAGRAM', 'icon': 'fa-instagram', 'color': '#e4405f',
             'category': 'شبکه‌های اجتماعی'},
            {'name': 'تلگرام', 'code': 'TELEGRAM', 'icon': 'fa-telegram-plane', 'color': '#0088cc',
             'category': 'شبکه‌های اجتماعی'},
            {'name': 'معرفی مشتری', 'code': 'CUSTOMER_REFERRAL', 'icon': 'fa-user-friends', 'color': '#28a745',
             'category': 'معرفی'},
            {'name': 'معرفی کارشناس', 'code': 'EXPERT_REFERRAL', 'icon': 'fa-user-tie', 'color': '#17a2b8',
             'category': 'معرفی'},
            {'name': 'روزنامه', 'code': 'NEWSPAPER', 'icon': 'fa-newspaper', 'color': '#6c757d', 'category': 'آفلاین'},
            {'name': 'بنر تبلیغاتی', 'code': 'BILLBOARD', 'icon': 'fa-flag', 'color': '#ffc107', 'category': 'آفلاین'},
            {'name': 'همایش', 'code': 'EVENT', 'icon': 'fa-users', 'color': '#fd7e14', 'category': 'آفلاین'},
            {'name': 'سایت مشاور املاک', 'code': 'WEBSITE', 'icon': 'fa-globe', 'color': '#6610f2',
             'category': 'آنلاین'},
            {'name': 'پرسش از مشتری', 'code': 'CUSTOMER_INQUIRY', 'icon': 'fa-question-circle', 'color': '#20c997',
             'category': 'سایر'},
            {'name': 'سایر', 'code': 'OTHER', 'icon': 'fa-ellipsis-h', 'color': '#6c757d', 'category': 'سایر'},
        ]
        return defaults


# ============================================================
# 🆕 مدل‌های جدید برای جهت، وضعیت واحد، نوع سند و ...
# ============================================================

class Orientation(models.Model):
    """
    جهت‌های مختلف (شمالی، جنوبی، شرقی، غربی، و ترکیبی)
    قابل مدیریت در ادمین
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="نام جهت")
    code = models.CharField(max_length=20, unique=True, verbose_name="کد جهت")
    icon = models.CharField(max_length=50, null=True, blank=True, verbose_name="آیکون")
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "جهت"
        verbose_name_plural = "جهت‌ها"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @classmethod
    def get_default_orientations(cls):
        return [
            {'name': 'شمالی', 'code': 'NORTH', 'icon': 'fa-arrow-up', 'order': 1},
            {'name': 'جنوبی', 'code': 'SOUTH', 'icon': 'fa-arrow-down', 'order': 2},
            {'name': 'شرقی', 'code': 'EAST', 'icon': 'fa-arrow-right', 'order': 3},
            {'name': 'غربی', 'code': 'WEST', 'icon': 'fa-arrow-left', 'order': 4},
            {'name': 'شمال شرقی', 'code': 'NORTH_EAST', 'icon': 'fa-arrow-up-right', 'order': 5},
            {'name': 'شمال غربی', 'code': 'NORTH_WEST', 'icon': 'fa-arrow-up-left', 'order': 6},
            {'name': 'جنوب شرقی', 'code': 'SOUTH_EAST', 'icon': 'fa-arrow-down-right', 'order': 7},
            {'name': 'جنوب غربی', 'code': 'SOUTH_WEST', 'icon': 'fa-arrow-down-left', 'order': 8},
        ]


class UnitCondition(models.Model):
    """
    وضعیت واحد (مبله، نیمه مبله، خالی، ...)
    جایگزین FurnishingStatus قبلی
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="نام وضعیت")
    code = models.CharField(max_length=20, unique=True, verbose_name="کد وضعیت")
    icon = models.CharField(max_length=50, null=True, blank=True, verbose_name="آیکون")
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "وضعیت واحد"
        verbose_name_plural = "وضعیت‌های واحد"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @classmethod
    def get_default_conditions(cls):
        return [
            {'name': 'مبله', 'code': 'FURNISHED', 'icon': 'fa-couch', 'order': 1},
            {'name': 'نیمه مبله', 'code': 'SEMI_FURNISHED', 'icon': 'fa-chair', 'order': 2},
            {'name': 'خالی', 'code': 'UNFURNISHED', 'icon': 'fa-door-open', 'order': 3},
        ]


class DocumentType(models.Model):
    """
    نوع سند ملک (تک برگ، دفترچه، قولنامه، و ...)
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="نام نوع سند")
    code = models.CharField(max_length=20, unique=True, verbose_name="کد نوع سند")
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "نوع سند"
        verbose_name_plural = "انواع سند"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @classmethod
    def get_default_document_types(cls):
        return [
            {'name': 'تک برگ', 'code': 'SINGLE_PAGE', 'order': 1},
            {'name': 'دفترچه ای', 'code': 'NOTEBOOK', 'order': 2},
            {'name': 'قولنامه', 'code': 'PROMISSORY', 'order': 3},
            {'name': 'مبایعه نامه', 'code': 'SALE_AGREEMENT', 'order': 4},
            {'name': 'وکالت نامه', 'code': 'POWER_OF_ATTORNEY', 'order': 5},
            {'name': 'سایر', 'code': 'OTHER', 'order': 6},
        ]


class OwnershipDocumentType(models.Model):
    """
    نوع مالکیت سند (شخصی، اوقاف، دولتی، ...)
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="نام نوع مالکیت سند")
    code = models.CharField(max_length=20, unique=True, verbose_name="کد نوع مالکیت سند")
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "نوع مالکیت سند"
        verbose_name_plural = "انواع مالکیت سند"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @classmethod
    def get_default_ownership_document_types(cls):
        return [
            {'name': 'شخصی', 'code': 'PRIVATE', 'order': 1},
            {'name': 'اوقاف', 'code': 'WAQF', 'order': 2},
            {'name': 'دولتی', 'code': 'GOVERNMENT', 'order': 3},
            {'name': 'نظامی', 'code': 'MILITARY', 'order': 4},
            {'name': 'سایر', 'code': 'OTHER', 'order': 5},
        ]


# ============================================================
# 🔢 مدل شمارنده کد نمایشی
# ============================================================

class DisplayCodeCounter(models.Model):
    class Type(models.TextChoices):
        CUSTOMER = 'customer', 'مشتری'
        PROPERTY = 'property', 'ملک'

    type = models.CharField(
        max_length=10,
        choices=Type.choices,
        unique=True,
        verbose_name="نوع"
    )
    last_number = models.PositiveIntegerField(
        default=0,
        verbose_name="آخرین عدد اختصاص‌یافته"
    )

    class Meta:
        verbose_name = "شمارنده کد نمایشی"
        verbose_name_plural = "شمارنده‌های کد نمایشی"

    def __str__(self):
        return f"{self.get_type_display()} - آخرین عدد: {self.last_number}"

    @classmethod
    def get_next_number(cls, type_code):
        """
        دریافت عدد بعدی برای نوع مشخص (با قفل جهت جلوگیری از تداخل هم‌زمان).
        اگر شمارنده‌ای برای نوع موردنظر وجود نداشته باشد، آن را می‌سازد.
        """
        from django.db import transaction
        with transaction.atomic():
            counter, created = cls.objects.select_for_update().get_or_create(
                type=type_code,
                defaults={'last_number': 0}
            )
            next_number = counter.last_number + 1
            counter.last_number = next_number
            counter.save(update_fields=['last_number'])
        return next_number

    @classmethod
    def initialize_counters(cls):
        """ایجاد شمارنده‌های اولیه در صورت عدم وجود"""
        for type_code in cls.Type.values:
            cls.objects.get_or_create(type=type_code)


# ============================================================
# 👤 مدل مشتری (Customer)
# ============================================================

class Customer(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """مدل مشتری - خریدار/مستاجر/سرمایه‌گذار"""

    # ========== کد نمایشی یکتا ==========
    display_code = models.CharField(
        max_length=20,
        # unique=True,
        # editable=False,
        null=True,
        blank=True,
        verbose_name="کد نمایشی مشتری",
        help_text="فرمت: C-XXXXX (عدد ترتیبی ۵ رقمی)"
    )

    class CustomerType(models.TextChoices):
        BUYER = 'buyer', 'خریدار'
        TENANT = 'tenant', 'مستاجر'
        PRE_BUYER = 'pre_buyer', 'پیش خریدار'
        DEVELOPER = 'developer', 'سازنده'
        INVESTOR = 'investor', 'سرمایه‌گذار'
        ALL = 'all', 'همه موارد'

    class Status(models.TextChoices):
        NEW = 'new', 'در انتظار بررسی'
        CONFIRMED = 'confirmed', 'تایید شده'
        ASSIGNED = 'assigned', 'ارجاع شده'
        WAITING = 'waiting', 'در انتظار تصمیم'
        DEPOSIT = 'deposit', 'بیعانه'
        IN_MEETING = 'in_meeting', 'در جلسه مذاکره'
        CONTRACT = 'contract', 'قرارداد'
        CANCELLED = 'cancelled', 'کنسل شده'

    class RentType(models.TextChoices):
        RENT = 'rent', 'اجاره'
        MORTGAGE = 'mortgage', 'رهن'
        BOTH = 'both', 'اجاره و رهن'

    # ========== ارتباط با کاربر ==========
    user = models.OneToOneField(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='customer_profile',
        verbose_name="کاربر"
    )

    # ========== ثبت‌کننده مشتری ==========
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers_created',
        verbose_name="ثبت‌کننده مشتری"
    )

    # ========== سرپرست فعلی ==========
    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers_supervised',
        verbose_name="سرپرست",
    )

    # ========== کارشناس فعلی ==========
    expert = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers_experted',
        verbose_name="کارشناس",
    )

    # ========== اطلاعات پایه ==========
    customer_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=CustomerType.choices,
        default=CustomerType.BUYER,
        verbose_name="نوع مشتری"
    )
    status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name="وضعیت"
    )

    # ========== اطلاعات تماس تکمیلی ==========
    alternative_phone = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name="تلفن همراه دوم"
    )
    home_phone = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name="تلفن منزل"
    )
    work_phone = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name="تلفن محل کار"
    )

    # ========== اطلاعات شغلی ==========
    job_title = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="عنوان شغلی"
    )
    company_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="نام شرکت"
    )

    # ========== 💰 بودجه خرید ==========
    budget_min = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="حداقل بودجه خرید (تومان)"
    )
    budget_max = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="حداکثر بودجه خرید (تومان)"
    )

    # ========== 💰 بودجه اجاره ==========
    rent_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=RentType.choices,
        default=RentType.RENT,
        verbose_name="نوع اجاره"
    )

    mortgage_min = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="حداقل رهن (تومان)"
    )
    mortgage_max = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="حداکثر رهن (تومان)"
    )

    rent_min = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="حداقل اجاره ماهیانه (تومان)"
    )
    rent_max = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="حداکثر اجاره ماهیانه (تومان)"
    )

    # ========== 📍 مناطق مورد نظر ==========
    preferred_cities = models.ManyToManyField(
        City,
        blank=True,
        related_name='customers_preferred',
        verbose_name="شهرهای مورد نظر"
    )

    preferred_neighborhoods = models.ManyToManyField(
        Neighborhood,
        blank=True,
        related_name='customers_preferred',
        verbose_name="محله‌های مورد نظر"
    )

    # ========== 🏠 انواع ملک مورد نظر ==========
    preferred_property_types = models.ManyToManyField(
        PropertyType,
        blank=True,
        related_name='customers_preferred',
        verbose_name="انواع ملک مورد نظر"
    )

    # ========== 🏢 کاربری‌ها ==========
    # کاربری سندی (اصلی) مورد نظر
    primary_usage = models.ForeignKey(
        UsageType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='customers_primary',
        verbose_name="کاربری سندی مورد نظر",
        help_text="کاربری اصلی و سندی که مشتری به دنبال آن است"
    )

    # کاربری‌های فرعی (کاربردهای ملک) مورد نظر
    preferred_usage_types = models.ManyToManyField(
        UsageType,
        blank=True,
        related_name='customers_preferred',
        verbose_name="کاربردهای مورد نظر",
        help_text="کاربری‌هایی که مشتری به آنها علاقه دارد (کاربردهای فرعی)"
    )

    # ========== 🎯 نیازهای خاص ==========
    preferred_requirements = models.ManyToManyField(
        Requirement,
        blank=True,
        related_name='customers_preferred',
        verbose_name="نیازهای خاص مورد نظر",
        help_text="امکاناتی که مشتری در ملک مورد نظر خود می‌خواهد"
    )

    # ========== 📢 منبع مشتری ==========
    source = models.ForeignKey(
        Source,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='customers',
        verbose_name="منبع",
        help_text="منبعی که مشتری از طریق آن به ما معرفی شده است"
    )

    # ========== مشخصات فنی ملک ==========
    min_area = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="حداقل متراژ"
    )
    max_area = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="حداکثر متراژ"
    )
    min_rooms = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="حداقل اتاق"
    )
    max_rooms = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="حداکثر اتاق"
    )

    # ========== 🆕 فیلدهای جدید ==========

    # طبقه مورد نظر (حداقل و حداکثر)
    preferred_min_floor = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="حداقل طبقه مورد نظر"
    )
    preferred_max_floor = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="حداکثر طبقه مورد نظر"
    )

    # تعداد طبقات ساختمان مورد نظر (حداقل و حداکثر)
    preferred_min_total_floors = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="حداقل تعداد طبقات ساختمان"
    )
    preferred_max_total_floors = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="حداکثر تعداد طبقات ساختمان"
    )

    # تعداد واحد در طبقه (حداقل و حداکثر)
    preferred_min_units_per_floor = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="حداقل تعداد واحد در طبقه"
    )
    preferred_max_units_per_floor = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="حداکثر تعداد واحد در طبقه"
    )

    # جهت‌های ساختمان مورد نظر (چند گزینه)
    preferred_building_orientations = models.ManyToManyField(
        Orientation,
        blank=True,
        related_name='customers_building',
        verbose_name="جهت‌های ساختمان مورد نظر"
    )

    # جهت‌های واحد مورد نظر (چند گزینه)
    preferred_unit_orientations = models.ManyToManyField(
        Orientation,
        blank=True,
        related_name='customers_unit',
        verbose_name="جهت‌های واحد مورد نظر"
    )

    # وضعیت واحد مورد نظر (چند گزینه)
    preferred_unit_conditions = models.ManyToManyField(
        UnitCondition,
        blank=True,
        related_name='customers',
        verbose_name="وضعیت‌های واحد مورد نظر"
    )

    # نیاز به پایان کار
    need_completion_certificate = models.BooleanField(
        default=False,
        verbose_name="نیاز به پایان کار دارد؟"
    )

    # نیاز به سند
    need_document = models.BooleanField(
        default=False,
        verbose_name="نیاز به سند دارد؟"
    )

    # انواع سند مورد نظر (چند گزینه)
    preferred_document_types = models.ManyToManyField(
        DocumentType,
        blank=True,
        related_name='customers',
        verbose_name="انواع سند مورد نظر"
    )

    # انواع مالکیت سند مورد نظر (چند گزینه)
    preferred_ownership_document_types = models.ManyToManyField(
        OwnershipDocumentType,
        blank=True,
        related_name='customers',
        verbose_name="انواع مالکیت سند مورد نظر"
    )

    # میزان دانگ مورد نظر (حداقل و حداکثر)
    preferred_dong_min = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        verbose_name="حداقل دانگ مورد نظر (۱ تا ۶)"
    )
    preferred_dong_max = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        verbose_name="حداکثر دانگ مورد نظر (۱ تا ۶)"
    )

    # ========== نیازهای ویژه ==========
    special_needs = models.TextField(
        null=True,
        blank=True,
        verbose_name="نیازهای ویژه"
    )

    # ========== اولویت ==========
    priority = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name="اولویت (۰ تا ۱۰)"
    )

    # ========== توضیحات ==========
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="توضیحات"
    )

    # ========== تاریخچه تعاملات ==========
    last_contact = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="آخرین تماس"
    )
    total_interactions = models.PositiveIntegerField(
        default=0,
        verbose_name="تعداد کل تعاملات"
    )

    class Meta:
        verbose_name = "مشتری"
        verbose_name_plural = "مشتریان"
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['customer_type', 'status']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_by']),
            models.Index(fields=['source']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_customer_type_display()}"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.display_code:
            # تولید کد نمایشی هنگام ایجاد جدید
            next_num = DisplayCodeCounter.get_next_number(DisplayCodeCounter.Type.CUSTOMER)
            self.display_code = f"C-{next_num:05d}"
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def mobile(self):
        return self.user.mobile

    @property
    def email(self):
        return self.user.email

    @property
    def created_by_name(self):
        if self.created_by:
            return self.created_by.get_full_name() or self.created_by.username
        return "سیستم"

    @property
    def source_name(self):
        return self.source.name if self.source else "نامشخص"

    def get_requirements_list(self):
        return self.preferred_requirements.filter(is_active=True)

    def get_requirements_display(self):
        requirements = self.get_requirements_list()
        if requirements.exists():
            return ", ".join([r.name for r in requirements])
        return "مشخص نشده"

    def get_requirements_grouped(self):
        groups = {}
        requirements = self.get_requirements_list()
        for req in requirements:
            if req.category not in groups:
                groups[req.category] = []
            groups[req.category].append(req)
        return groups

    def get_budget_display(self):
        if self.budget_min and self.budget_max:
            return f"{self.budget_min:,} - {self.budget_max:,} تومان"
        elif self.budget_max:
            return f"حداکثر {self.budget_max:,} تومان"
        elif self.budget_min:
            return f"حداقل {self.budget_min:,} تومان"
        return "مشخص نشده"

    def get_rent_display(self):
        parts = []
        if self.rent_min and self.rent_max:
            parts.append(f"اجاره: {self.rent_min:,} - {self.rent_max:,} تومان")
        elif self.rent_max:
            parts.append(f"اجاره حداکثر: {self.rent_max:,} تومان")
        elif self.rent_min:
            parts.append(f"اجاره حداقل: {self.rent_min:,} تومان")
        if self.mortgage_min and self.mortgage_max:
            parts.append(f"رهن: {self.mortgage_min:,} - {self.mortgage_max:,} تومان")
        elif self.mortgage_max:
            parts.append(f"رهن حداکثر: {self.mortgage_max:,} تومان")
        elif self.mortgage_min:
            parts.append(f"رهن حداقل: {self.mortgage_min:,} تومان")
        return " | ".join(parts) if parts else "مشخص نشده"

    def get_all_budget_display(self):
        result = []
        if self.budget_min or self.budget_max:
            result.append(f"خرید: {self.get_budget_display()}")
        if self.rent_min or self.rent_max or self.mortgage_min or self.mortgage_max:
            result.append(f"اجاره: {self.get_rent_display()}")
        return " | ".join(result) if result else "مشخص نشده"

    def get_preferred_areas_display(self):
        cities = self.preferred_cities.all()
        neighborhoods = self.preferred_neighborhoods.all()
        parts = []
        if cities.exists():
            parts.append(f"شهرها: {', '.join([c.name for c in cities])}")
        if neighborhoods.exists():
            parts.append(f"محله‌ها: {', '.join([n.name for n in neighborhoods])}")
        return " | ".join(parts) if parts else "مشخص نشده"

    def get_property_types_display(self):
        types = self.preferred_property_types.filter(is_active=True)
        if types.exists():
            return ", ".join([t.name for t in types])
        return "مشخص نشده"

    def get_jalali_created(self):
        try:
            jalali = jdatetime.date.fromgregorian(date=self.created_at)
            return f"{jalali.year}/{jalali.month}/{jalali.day}"
        except:
            return "نامشخص"

    # ============================================================
    # ✅ متدهای کمکی جدید برای مدیریت وضعیت‌های جلسه و قرارداد
    # ============================================================

    def is_available_for_assignment(self):
        """بررسی اینکه مشتری قابل انتساب به کارشناس جدید است یا خیر"""
        return self.status not in [self.Status.IN_MEETING, self.Status.CONTRACT]

    def is_in_meeting_or_contract(self):
        """بررسی اینکه مشتری در جلسه یا قرارداد است"""
        return self.status in [self.Status.IN_MEETING, self.Status.CONTRACT]

    # ============================================================
    # ✅ متد برای دریافت مناطق انتخاب شده به صورت JSON
    # ============================================================

    def get_selected_locations_json(self):
        """
        دریافت مناطق انتخاب شده به صورت JSON برای ذخیره در فرم
        """
        locations = []
        for neighborhood in self.preferred_neighborhoods.select_related('city__province').all():
            locations.append({
                'province_id': neighborhood.city.province.id,
                'province_name': neighborhood.city.province.name,
                'city_id': neighborhood.city.id,
                'city_name': neighborhood.city.name,
                'neighborhood_id': neighborhood.id,
                'neighborhood_name': neighborhood.name,
            })
        return json.dumps(locations, ensure_ascii=False)

    # ============================================================
    # متد ثبت/بروزرسانی مشتری
    # ============================================================

    @classmethod
    def create_or_update_from_mobile(cls, mobile, created_by=None, user_data=None, customer_data=None):
        from django.db import transaction
        from django.core.exceptions import ValidationError

        if not mobile:
            raise ValidationError("شماره موبایل الزامی است")

        with transaction.atomic():
            user = User.objects.filter(mobile=mobile).first()
            user_created = False

            if user:
                if user_data:
                    for key, value in user_data.items():
                        if value is not None:
                            setattr(user, key, value)
                    user.save()
            else:
                user_created = True
                user_data = user_data or {}
                username = user_data.get('username', mobile)

                user = User.objects.create_user(
                    username=username,
                    mobile=mobile,
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    email=user_data.get('email', ''),
                    password=user_data.get('password', User.objects.make_random_password())
                )

                if not user.has_role('customer'):
                    user.assign_role('customer')

            customer = cls.objects.filter(user=user).first()
            created = False

            if customer:
                if customer_data:
                    for key, value in customer_data.items():
                        if value is not None and key not in [
                            'preferred_cities', 'preferred_neighborhoods',
                            'preferred_property_types', 'preferred_requirements',
                            'preferred_usage_types', 'preferred_building_orientations',
                            'preferred_unit_orientations', 'preferred_unit_conditions',
                            'preferred_document_types', 'preferred_ownership_document_types'
                        ]:
                            setattr(customer, key, value)

                    if created_by and not customer.created_by:
                        customer.created_by = created_by

                    customer.save()

                    # ManyToMany fields
                    if customer_data.get('preferred_cities') is not None:
                        customer.preferred_cities.set(customer_data['preferred_cities'])
                    if customer_data.get('preferred_neighborhoods') is not None:
                        customer.preferred_neighborhoods.set(customer_data['preferred_neighborhoods'])
                    if customer_data.get('preferred_property_types') is not None:
                        customer.preferred_property_types.set(customer_data['preferred_property_types'])
                    if customer_data.get('preferred_requirements') is not None:
                        customer.preferred_requirements.set(customer_data['preferred_requirements'])
                    if customer_data.get('preferred_usage_types') is not None:
                        customer.preferred_usage_types.set(customer_data['preferred_usage_types'])
                    if customer_data.get('preferred_building_orientations') is not None:
                        customer.preferred_building_orientations.set(customer_data['preferred_building_orientations'])
                    if customer_data.get('preferred_unit_orientations') is not None:
                        customer.preferred_unit_orientations.set(customer_data['preferred_unit_orientations'])
                    if customer_data.get('preferred_unit_conditions') is not None:
                        customer.preferred_unit_conditions.set(customer_data['preferred_unit_conditions'])
                    if customer_data.get('preferred_document_types') is not None:
                        customer.preferred_document_types.set(customer_data['preferred_document_types'])
                    if customer_data.get('preferred_ownership_document_types') is not None:
                        customer.preferred_ownership_document_types.set(customer_data['preferred_ownership_document_types'])
            else:
                created = True
                customer_data = customer_data or {}

                customer = cls.objects.create(
                    user=user,
                    created_by=created_by,
                    customer_type=customer_data.get('customer_type', cls.CustomerType.BUYER),
                    status=customer_data.get('status', cls.Status.NEW),
                    budget_min=customer_data.get('budget_min'),
                    budget_max=customer_data.get('budget_max'),
                    rent_type=customer_data.get('rent_type', cls.RentType.RENT),
                    mortgage_min=customer_data.get('mortgage_min'),
                    mortgage_max=customer_data.get('mortgage_max'),
                    rent_min=customer_data.get('rent_min'),
                    rent_max=customer_data.get('rent_max'),
                    min_area=customer_data.get('min_area'),
                    max_area=customer_data.get('max_area'),
                    min_rooms=customer_data.get('min_rooms'),
                    max_rooms=customer_data.get('max_rooms'),
                    special_needs=customer_data.get('special_needs'),
                    priority=customer_data.get('priority', 0),
                    source=customer_data.get('source'),
                    description=customer_data.get('description'),
                    alternative_phone=customer_data.get('alternative_phone'),
                    home_phone=customer_data.get('home_phone'),
                    work_phone=customer_data.get('work_phone'),
                    job_title=customer_data.get('job_title'),
                    company_name=customer_data.get('company_name'),
                    primary_usage=customer_data.get('primary_usage'),
                    preferred_min_floor=customer_data.get('preferred_min_floor'),
                    preferred_max_floor=customer_data.get('preferred_max_floor'),
                    preferred_min_total_floors=customer_data.get('preferred_min_total_floors'),
                    preferred_max_total_floors=customer_data.get('preferred_max_total_floors'),
                    preferred_min_units_per_floor=customer_data.get('preferred_min_units_per_floor'),
                    preferred_max_units_per_floor=customer_data.get('preferred_max_units_per_floor'),
                    need_completion_certificate=customer_data.get('need_completion_certificate', False),
                    need_document=customer_data.get('need_document', False),
                    preferred_dong_min=customer_data.get('preferred_dong_min'),
                    preferred_dong_max=customer_data.get('preferred_dong_max'),
                )

                if customer_data.get('preferred_cities'):
                    customer.preferred_cities.set(customer_data['preferred_cities'])
                if customer_data.get('preferred_neighborhoods'):
                    customer.preferred_neighborhoods.set(customer_data['preferred_neighborhoods'])
                if customer_data.get('preferred_property_types'):
                    customer.preferred_property_types.set(customer_data['preferred_property_types'])
                if customer_data.get('preferred_requirements'):
                    customer.preferred_requirements.set(customer_data['preferred_requirements'])
                if customer_data.get('preferred_usage_types'):
                    customer.preferred_usage_types.set(customer_data['preferred_usage_types'])
                if customer_data.get('preferred_building_orientations'):
                    customer.preferred_building_orientations.set(customer_data['preferred_building_orientations'])
                if customer_data.get('preferred_unit_orientations'):
                    customer.preferred_unit_orientations.set(customer_data['preferred_unit_orientations'])
                if customer_data.get('preferred_unit_conditions'):
                    customer.preferred_unit_conditions.set(customer_data['preferred_unit_conditions'])
                if customer_data.get('preferred_document_types'):
                    customer.preferred_document_types.set(customer_data['preferred_document_types'])
                if customer_data.get('preferred_ownership_document_types'):
                    customer.preferred_ownership_document_types.set(customer_data['preferred_ownership_document_types'])

            return customer, created, user_created


# ============================================================
# 🏠 مدل ملک (Property)
# ============================================================

class Property(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """
    مدل ثبت ملک
    """

    # ========== کد نمایشی یکتا ==========
    display_code = models.CharField(
        max_length=20,
        # unique=True,
        # editable=False,
        null=True,
        blank=True,
        verbose_name="کد نمایشی ملک",
        help_text="فرمت: P-XXXXX (عدد ترتیبی ۵ رقمی)"
    )

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار'
        CONFIRMED = 'confirmed', 'تایید شده'
        DEPOSIT = 'deposit', 'بیعانه'
        IN_MEETING = 'in_meeting', 'در جلسه مذاکره'
        CONTRACT = 'contract', 'قرارداد'
        CANCELLED = 'cancelled', 'کنسل شده'

    class ContractType(models.TextChoices):
        SALE = 'sale', 'فروش'
        RENT = 'rent', 'اجاره'
        PRE_SALE = 'pre_sale', 'پیش فروش'
        BOTH = 'both', 'فروش و اجاره'
        PARTNERSHIP = 'partnership', 'مشارکت در ساخت'
        INVESTMENT = 'investment', 'جذب سرمایه'

    class OwnershipType(models.TextChoices):
        OWNER = 'owner', 'مالک'
        TENANT = 'tenant', 'مستاجر'
        MANAGER = 'manager', 'مدیر'
        LAWYER = 'lawyer', 'وکیل'
        OTHER = 'other', 'سایر'

    class ParkingType(models.TextChoices):
        NONE = 'none', 'بدون پارکینگ'
        ONE = 'one', 'یک پارکینگ'
        TWO = 'two', 'دو پارکینگ'
        THREE = 'three', 'سه پارکینگ'
        FOUR = 'four', 'چهار پارکینگ'
        MORE = 'more', 'بیشتر از چهار'

    # ==========================================================
    # 📋 اطلاعات پایه
    # ==========================================================

    title = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="عنوان ملک"
    )

    property_type = models.ForeignKey(
        PropertyType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='properties',
        verbose_name="نوع ملک"
    )

    # ========== 🆕 کاربری سندی (اصلی) ==========
    primary_usage = models.ForeignKey(
        UsageType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='primary_properties',
        verbose_name="کاربری سندی (اصلی)",
        help_text="کاربری اصلی و سند این ملک"
    )

    # ========== کاربری‌های فرعی (کاربردهای ملک) ==========
    usage_types = models.ManyToManyField(
        UsageType,
        blank=True,
        related_name='properties',
        verbose_name="کاربردهای ملک",
        help_text="کاربری‌هایی که این ملک برای آنها مناسب است (کاربردهای فرعی)"
    )

    status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="وضعیت"
    )

    contract_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=ContractType.choices,
        default=ContractType.SALE,
        verbose_name="نوع قرارداد"
    )

    # ==========================================================
    # 💰 قیمت‌ها
    # ==========================================================

    price = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="قیمت فروش (تومان)"
    )

    # 🆕 قیمت هر متر
    price_per_meter = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="قیمت هر متر (تومان)",
        help_text="قیمت هر متر مربع ملک"
    )

    # ==========================================================
    # 📷 تصویر نما (ویژه و محرمانه)
    # ==========================================================

    showcase_image = models.ImageField(
        upload_to='properties/showcase/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="تصویر نما",
        help_text="تصویر ویژه و محرمانه ملک - فقط کاربران مجاز می‌توانند آن را مشاهده کنند"
    )

    is_price_negotiable = models.BooleanField(
        default=False,
        verbose_name="قیمت توافقی"
    )

    is_rent_convertible = models.BooleanField(
        default=False,
        verbose_name="رهن و اجاره قابل تبدیل"
    )

    rent_price = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="اجاره ماهیانه (تومان)"
    )

    mortgage_price = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="رهن (تومان)"
    )

    is_rent_negotiable = models.BooleanField(
        default=False,
        verbose_name="اجاره توافقی"
    )

    # ==========================================================
    # 📐 مشخصات فیزیکی
    # ==========================================================

    area = models.FloatField(
        null=True,
        blank=True,
        verbose_name="متراژ (متر مربع)"
    )

    rooms = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="تعداد اتاق"
    )

    floor = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="طبقه"
    )

    total_floors = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="تعداد کل طبقات"
    )

    # 🆕 تعداد واحد در طبقه
    units_per_floor = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="تعداد واحد در طبقه"
    )

    built_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="سال ساخت"
    )

    is_new_building = models.BooleanField(
        default=False,
        verbose_name="نوساز"
    )

    parking_type = models.CharField(
        max_length=20,
        choices=ParkingType.choices,
        default=ParkingType.NONE,
        verbose_name="پارکینگ"
    )

    ownership_type = models.CharField(
        max_length=20,
        choices=OwnershipType.choices,
        default=OwnershipType.OWNER,
        verbose_name="نوع مالکیت"
    )

    # ========== 🆕 وضعیت واحد (جایگزین furnishing_status) ==========
    unit_condition = models.ForeignKey(
        UnitCondition,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='properties',
        verbose_name="وضعیت واحد"
    )

    # ========== 🆕 جهت‌ها ==========
    building_orientation = models.ForeignKey(
        Orientation,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='properties_building',
        verbose_name="جهت ساختمان"
    )

    unit_orientation = models.ForeignKey(
        Orientation,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='properties_unit',
        verbose_name="جهت واحد"
    )

    # ========== 🆕 وضعیت پایان کار ==========
    has_completion_certificate = models.BooleanField(
        default=False,
        verbose_name="دارای پایان کار"
    )

    # ========== 🆕 وضعیت سند ==========
    has_document = models.BooleanField(
        default=False,
        verbose_name="دارای سند"
    )

    # ========== 🆕 نوع سند ==========
    document_type = models.ForeignKey(
        DocumentType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='properties',
        verbose_name="نوع سند"
    )

    # ========== 🆕 نوع مالکیت سند ==========
    ownership_document_type = models.ForeignKey(
        OwnershipDocumentType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='properties',
        verbose_name="نوع مالکیت سند"
    )

    # ========== 🆕 میزان دانگ ==========
    dong = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        verbose_name="میزان دانگ (۱ تا ۶)"
    )

    # ==========================================================
    # 📍 موقعیت مکانی (استفاده از مدل‌های موجود)
    # ==========================================================

    province = models.ForeignKey(
        Province,
        on_delete=models.PROTECT,
        related_name='properties',
        null=True,
        blank=True,
        verbose_name="استان"
    )

    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='properties',
        null=True,
        blank=True,
        verbose_name="شهر"
    )

    neighborhood = models.ForeignKey(
        Neighborhood,
        on_delete=models.PROTECT,
        related_name='properties',
        null=True,
        blank=True,
        verbose_name="محله"
    )

    address = models.TextField(
        null=True,
        blank=True,
        verbose_name="آدرس دقیق"
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="عرض جغرافیایی"
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="طول جغرافیایی"
    )

    # ==========================================================
    # 🎯 امکانات (استفاده از مدل Requirement موجود)
    # ==========================================================

    requirements = models.ManyToManyField(
        Requirement,
        blank=True,
        related_name='properties',
        verbose_name="امکانات ملک"
    )

    # ==========================================================
    # 📝 توضیحات
    # ==========================================================

    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="توضیحات کامل"
    )

    short_description = models.CharField(
        max_length=300,
        null=True,
        blank=True,
        verbose_name="توضیح مختصر"
    )

    # ==========================================================
    # 📞 اطلاعات تماس
    # ==========================================================

    contact_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="نام تماس"
    )

    contact_phone = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name="شماره تماس"
    )

    contact_email = models.EmailField(
        null=True,
        blank=True,
        verbose_name="ایمیل تماس"
    )

    # ==========================================================
    # 👤 مالک ملک (فقط User)
    # ==========================================================

    owner = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='owned_properties',
        verbose_name="مالک ملک"
    )

    # ==========================================================
    # 👤 ثبت‌کننده
    # ==========================================================

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='properties_created',
        verbose_name="ثبت‌کننده"
    )

    # ========== سرپرست فعلی ==========
    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='properties_supervised',
        verbose_name="سرپرست",
    )

    # ========== کارشناس فعلی ==========
    expert = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='properties_experted',
        verbose_name="کارشناس",
    )

    # ==========================================================
    # 🏷️ وضعیت نمایش
    # ==========================================================

    is_visible = models.BooleanField(
        default=True,
        verbose_name="قابل مشاهده"
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name="ویژه"
    )

    is_verified = models.BooleanField(
        default=False,
        verbose_name="تایید شده"
    )

    # ==========================================================
    # 📊 آمار
    # ==========================================================

    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name="تعداد بازدید"
    )

    favorites_count = models.PositiveIntegerField(
        default=0,
        verbose_name="تعداد علاقه‌مندی‌ها"
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ انتشار"
    )

    # ==========================================================
    # 📋 Meta
    # ==========================================================

    class Meta:
        verbose_name = "ملک"
        verbose_name_plural = "املاک"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'contract_type']),
            models.Index(fields=['city', 'neighborhood']),
            models.Index(fields=['is_visible']),
        ]

    def __str__(self):
        return f"{self.title} - {self.property_type.name}"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.display_code:
            next_num = DisplayCodeCounter.get_next_number(DisplayCodeCounter.Type.PROPERTY)
            self.display_code = f"P-{next_num:05d}"
        super().save(*args, **kwargs)

    @property
    def full_location(self):
        """موقعیت کامل ملک - با مدیریت None"""
        parts = []

        if self.province:
            parts.append(self.province.name)
        if self.city:
            parts.append(self.city.name)
        if self.neighborhood:
            parts.append(self.neighborhood.name)

        return " - ".join(parts) if parts else "موقعیت ثبت نشده"

    @property
    def formatted_price(self):
        return f"{int(self.price):,} تومان"

    @property
    def formatted_rent(self):
        if self.rent_price:
            return f"{int(self.rent_price):,} تومان"
        return "نامشخص"

    @property
    def formatted_mortgage(self):
        if self.mortgage_price:
            return f"{int(self.mortgage_price):,} تومان"
        return "نامشخص"

    @property
    def owner_name(self):
        """دریافت نام مالک"""
        if self.owner:
            return self.owner.get_full_name()
        return "نامشخص"

    @property
    def requirements_list(self):
        return ", ".join([r.name for r in self.requirements.filter(is_active=True)])

    # ==========================================================
    # ✅ متدهای کمکی جدید برای مدیریت وضعیت‌های جلسه و قرارداد
    # ==========================================================

    def is_available_for_use(self):
        """بررسی اینکه فایل قابل استفاده برای معرفی یا بازدید است"""
        return self.status not in [self.Status.IN_MEETING, self.Status.CONTRACT]

    def is_in_meeting_or_contract(self):
        """بررسی اینکه فایل در جلسه یا قرارداد است"""
        return self.status in [self.Status.IN_MEETING, self.Status.CONTRACT]

    # ==========================================================
    # 🖼️ متدهای تصاویر و ویدئوها
    # ==========================================================

    def get_main_image(self):
        """دریافت تصویر اصلی"""
        return self.images.filter(is_main=True).first()

    def get_all_images(self):
        """دریافت همه تصاویر"""
        return self.images.all().order_by('order')

    def get_main_video(self):
        """دریافت ویدئو اصلی"""
        return self.videos.filter(is_main=True).first()

    def get_all_videos(self):
        """دریافت همه ویدئوها"""
        return self.videos.all().order_by('order')

    def soft_delete(self):
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()

    @property
    def formatted_price_per_meter(self):
        if self.price_per_meter:
            return f"{int(self.price_per_meter):,} تومان"
        return "نامشخص"

    @property
    def auto_calculate_price_per_meter(self):
        """محاسبه خودکار قیمت متری از روی قیمت کل و متراژ"""
        if self.price and self.area and self.area > 0:
            return int(self.price / self.area)
        return None


# ============================================================
# 🖼️ مدل تصاویر ملک (PropertyImage)
# ============================================================

def property_image_path(instance, filename):
    """مسیر ذخیره تصاویر"""
    return f"properties/{instance.property_ref.id}/images/{filename}"


class PropertyImage(models.Model):
    """تصاویر ملک"""

    property_ref = models.ForeignKey(
        'Property',
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="ملک"
    )

    image = models.ImageField(
        upload_to=property_image_path,
        verbose_name="تصویر"
    )

    caption = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="عنوان"
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش"
    )

    is_main = models.BooleanField(
        default=False,
        verbose_name="تصویر اصلی",
        help_text="این تصویر به عنوان تصویر اصلی نمایش داده شود"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان آپلود"
    )

    class Meta:
        verbose_name = "تصویر ملک"
        verbose_name_plural = "تصاویر ملک"
        ordering = ['order', '-uploaded_at']

    def __str__(self):
        return f"تصویر {self.order} - {self.property_ref.title}"

    def save(self, *args, **kwargs):
        if self.is_main:
            PropertyImage.objects.filter(property_ref=self.property_ref, is_main=True).exclude(id=self.id).update(is_main=False)
        super().save(*args, **kwargs)


# ============================================================
# 🎬 مدل ویدئوهای ملک (PropertyVideo)
# ============================================================

def property_video_path(instance, filename):
    """مسیر ذخیره ویدئوها"""
    return f"properties/{instance.property_ref.id}/videos/{filename}"


class PropertyVideo(models.Model):
    """ویدئوهای ملک"""

    class VideoType(models.TextChoices):
        UPLOAD = 'upload', 'آپلود شده'
        LINK = 'link', 'لینک خارجی'

    property_ref = models.ForeignKey(
        'Property',
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name="ملک"
    )

    video_type = models.CharField(
        max_length=10,
        choices=VideoType.choices,
        default=VideoType.UPLOAD,
        verbose_name="نوع ویدئو"
    )

    video_file = models.FileField(
        upload_to=property_video_path,
        null=True,
        blank=True,
        verbose_name="فایل ویدئو",
        help_text="فایل ویدئو با فرمت‌های mp4, avi, mov"
    )

    video_link = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="لینک ویدئو",
        help_text="لینک ویدئو از سایت‌هایی مثل آپارات، یوتیوب، ویمئو"
    )

    thumbnail = models.ImageField(
        upload_to=property_video_path,
        null=True,
        blank=True,
        verbose_name="تصویر بندانگشتی"
    )

    title = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="عنوان ویدئو"
    )

    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="توضیحات ویدئو"
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش"
    )

    is_main = models.BooleanField(
        default=False,
        verbose_name="ویدئو اصلی"
    )

    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="مدت زمان (ثانیه)"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان آپلود"
    )

    class Meta:
        verbose_name = "ویدئوی ملک"
        verbose_name_plural = "ویدئوهای ملک"
        ordering = ['order', '-uploaded_at']

    def __str__(self):
        return f"ویدئو {self.order} - {self.property_ref.title}"

    @property
    def video_url(self):
        """دریافت آدرس ویدئو"""
        if self.video_type == self.VideoType.LINK and self.video_link:
            return self.video_link
        if self.video_file:
            return self.video_file.url
        return None

    @property
    def embed_url(self):
        """دریافت لینک قابل نمایش برای ویدئوهای خارجی"""
        if self.video_type == self.VideoType.LINK and self.video_link:
            import re
            if 'aparat.com' in self.video_link:
                return self.video_link.replace('/v/', '/embed/')
            if 'youtube.com' in self.video_link or 'youtu.be' in self.video_link:
                match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', self.video_link)
                if match:
                    return f"https://www.youtube.com/embed/{match.group(1)}"
            return self.video_link
        return None

    @property
    def is_external_link(self):
        return self.video_type == self.VideoType.LINK

    @property
    def is_uploaded_file(self):
        return self.video_type == self.VideoType.UPLOAD

    def save(self, *args, **kwargs):
        if self.is_main:
            PropertyVideo.objects.filter(property_ref=self.property_ref, is_main=True).exclude(id=self.id).update(is_main=False)
        super().save(*args, **kwargs)


# ============================================================
# 📝 مدل یادداشت‌ها و نظرات (Note)
# ============================================================

class Note(models.Model):
    class NoteType(models.TextChoices):
        GENERAL = 'general', 'یادداشت عمومی'
        CUSTOMER = 'customer', 'یادداشت مشتری'
        PROPERTY = 'property', 'یادداشت ملک'
        IMPORTANT = 'important', 'نکته مهم'
        WARNING = 'warning', 'هشدار'
        REVIEW = 'review', 'نظر کارشناسی'

    class Priority(models.TextChoices):
        LOW = 'low', 'کم'
        MEDIUM = 'medium', 'متوسط'
        HIGH = 'high', 'بالا'
        URGENT = 'urgent', 'فوری'

    customer = models.ForeignKey(
        'Customer',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notes',
        verbose_name="مشتری مرتبط"
    )
    property_ref = models.ForeignKey(
        'Property',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notes',
        verbose_name="ملک مرتبط"
    )

    note_type = models.CharField(
        max_length=20,
        choices=NoteType.choices,
        default=NoteType.GENERAL,
        verbose_name="نوع یادداشت"
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="اولویت"
    )
    title = models.CharField(max_length=200, verbose_name="عنوان")
    content = models.TextField(verbose_name="متن یادداشت")

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes_created',
        verbose_name="نویسنده"
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes_assigned',
        verbose_name="اختصاص داده شده به"
    )

    is_resolved = models.BooleanField(default=False, verbose_name="برطرف شده")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ برطرف شدن")
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes_resolved',
        verbose_name="برطرف کننده"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    due_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ سررسید")

    class Meta:
        verbose_name = "یادداشت"
        verbose_name_plural = "یادداشت‌ها"
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['customer', 'is_resolved']),
            models.Index(fields=['property_ref', 'is_resolved']),
            models.Index(fields=['assigned_to', 'is_resolved']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        target = self.customer or self.property_ref
        return f"{self.get_note_type_display()} - {self.title} ({target})"

    def mark_as_resolved(self, user):
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.save()

    @property
    def target_name(self):
        if self.customer:
            return f"مشتری: {self.customer.full_name}"
        elif self.property_ref:
            return f"ملک: {self.property_ref.title}"
        return "عمومی"

    @property
    def priority_color(self):
        colors = {
            'low': 'secondary',
            'medium': 'primary',
            'high': 'warning',
            'urgent': 'danger'
        }
        return colors.get(self.priority, 'secondary')

    @property
    def priority_icon(self):
        icons = {
            'low': 'fa-arrow-down',
            'medium': 'fa-minus',
            'high': 'fa-arrow-up',
            'urgent': 'fa-exclamation-triangle'
        }
        return icons.get(self.priority, 'fa-circle')


# ============================================================
# 🔍 مدل تشخیص تکراری (DuplicateCheck)
# ============================================================

class DuplicateCheck(models.Model):
    class CheckType(models.TextChoices):
        CUSTOMER = 'customer', 'مشتری'
        PROPERTY = 'property', 'ملک'

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار بررسی'
        CONFIRMED = 'confirmed', 'تکراری تایید شد'
        REJECTED = 'rejected', 'تکراری رد شد'
        FALSE = 'false', 'تکراری نیست'

    check_type = models.CharField(max_length=10, choices=CheckType.choices, verbose_name="نوع بررسی")
    check_id = models.UUIDField(null=True, blank=True, verbose_name="شناسه مورد بررسی")

    duplicate_ids = models.JSONField(default=list, verbose_name="شناسه‌های تکراری")
    duplicate_data = models.JSONField(default=dict, verbose_name="داده‌های تکراری")

    similarity_score = models.FloatField(default=0, verbose_name="امتیاز تشابه")
    match_details = models.JSONField(default=dict, blank=True, verbose_name="جزئیات تطابق")

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, verbose_name="وضعیت")

    checked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='duplicate_checks',
        verbose_name="بررسی‌کننده"
    )

    reviewer_note = models.TextField(null=True, blank=True, verbose_name="یادداشت بررسی‌کننده")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    checked_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ بررسی")

    class Meta:
        verbose_name = "بررسی تکراری"
        verbose_name_plural = "بررسی‌های تکراری"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['check_type', 'check_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.get_check_type_display()} - {self.check_id} - {self.get_status_display()}"

    def confirm_duplicate(self, user, note=None):
        self.status = self.Status.CONFIRMED
        self.checked_by = user
        self.checked_at = timezone.now()
        if note:
            self.reviewer_note = note
        self.save()

    def reject_duplicate(self, user, note=None):
        self.status = self.Status.REJECTED
        self.checked_by = user
        self.checked_at = timezone.now()
        if note:
            self.reviewer_note = note
        self.save()

    def mark_as_false(self, user, note=None):
        self.status = self.Status.FALSE
        self.checked_by = user
        self.checked_at = timezone.now()
        if note:
            self.reviewer_note = note
        self.save()


# ============================================================
# 🎯 مدل تطابق (Match)
# ============================================================

class Match(UUIDModel, TimeStampedModel):
    """
    مدل تطابق بین مشتری و ملک
    زمان ثبت هر مشتری یا ملک، به صورت خودکار محاسبه و ذخیره میشه
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار بررسی'
        REVIEWED = 'reviewed', 'بررسی شده'
        SENT = 'sent', 'ارسال شده به مشتری'
        INTERESTED = 'interested', 'مشتری علاقه‌مند'
        NOT_INTERESTED = 'not_interested', 'مشتری علاقه‌مند نیست'
        VISIT_DONE = 'visit_done', 'بازدید انجام شده'
        OFFERED = 'offered', 'پیشنهاد داده شده'
        CONVERTED = 'converted', 'تبدیل به معامله'
        REJECTED = 'rejected', 'رد شده'

    class MatchType(models.TextChoices):
        AUTO = 'auto', 'خودکار'
        MANUAL = 'manual', 'دستی'

    class IntroductionStatus(models.TextChoices):
        PENDING = 'pending', 'در انتظار معرفی'
        SUCCESS = 'success', 'معرفی موفق (مشتری علاقه‌مند شد)'
        FAIL = 'fail', 'معرفی ناموفق (مشتری علاقه‌ای نداشت)'
        NOT_APPLICABLE = 'not_applicable', 'قابل معرفی نیست'

    # ==========================================================
    # 🔗 ارتباط با مدل‌های اصلی
    # ==========================================================

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name="مشتری"
    )

    property_ref = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name="ملک"
    )

    # ==========================================================
    # 📊 امتیاز کلی تطابق (۰ تا ۱۰۰)
    # ==========================================================

    match_score = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="امتیاز تطابق کلی"
    )

    # ==========================================================
    # 📊 امتیازات جزئی (هر کدوم ۰ تا ۱۰۰)
    # ==========================================================

    score_location = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="امتیاز موقعیت مکانی"
    )

    score_price = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="امتیاز قیمت"
    )

    score_area = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="امتیاز متراژ"
    )

    score_rooms = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="امتیاز تعداد اتاق"
    )

    score_requirements = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="امتیاز امکانات"
    )

    score_property_type = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="امتیاز نوع ملک"
    )

    score_contract = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="امتیاز نوع قرارداد"
    )

    score_rent = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="امتیاز اجاره/رهن"
    )

    score_ownership = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="امتیاز نوع مالکیت"
    )

    # ==========================================================
    # 📋 اطلاعات تطابق
    # ==========================================================

    match_type = models.CharField(
        max_length=10,
        choices=MatchType.choices,
        default=MatchType.AUTO,
        verbose_name="نوع تطابق"
    )

    match_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="جزئیات تطابق",
        help_text="ذخیره جزئیات کامل تطابق به صورت JSON"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="وضعیت"
    )

    # ==========================================================
    # 📝 یادداشت‌ها
    # ==========================================================

    expert_note = models.TextField(
        null=True,
        blank=True,
        verbose_name="یادداشت کارشناس"
    )

    customer_feedback = models.TextField(
        null=True,
        blank=True,
        verbose_name="بازخورد مشتری"
    )

    # ==========================================================
    # 🆕 فیلدهای مربوط به نتیجه معرفی (Introduction)
    # ==========================================================

    introduction_status = models.CharField(
        max_length=20,
        choices=IntroductionStatus.choices,
        default=IntroductionStatus.PENDING,
        verbose_name="وضعیت معرفی",
        help_text="نتیجه معرفی این فایل به مشتری"
    )

    introduction_note = models.TextField(
        null=True,
        blank=True,
        verbose_name="یادداشت معرفی",
        help_text="توضیح کارشناس درباره علت موفقیت یا عدم موفقیت معرفی"
    )

    introduction_confirmed = models.BooleanField(
        default=False,
        verbose_name="تایید شده توسط سرپرست؟"
    )

    introduction_confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_introductions',
        verbose_name="تایید کننده (سرپرست)"
    )

    introduction_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ تایید"
    )

    # ==========================================================
    # 📅 تاریخچه
    # ==========================================================

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ ارسال به مشتری"
    )

    viewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ مشاهده توسط مشتری"
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ بررسی توسط کارشناس"
    )

    # ==========================================================
    # 👤 کاربران
    # ==========================================================

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matches_created',
        verbose_name="ثبت‌کننده تطابق"
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matches_reviewed',
        verbose_name="بررسی‌کننده تطابق"
    )

    class Meta:
        verbose_name = "تطابق"
        verbose_name_plural = "تطابق‌ها"
        ordering = ['-match_score', '-created_at']
        unique_together = ['customer', 'property_ref']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['property_ref', 'status']),
            models.Index(fields=['match_score']),
            models.Index(fields=['status', 'match_score']),
            models.Index(fields=['introduction_status', 'introduction_confirmed']),
        ]

    def __str__(self):
        return f"{self.customer.full_name} - {self.property_ref.title} ({self.match_score}%)"

    # ==========================================================
    # 🏷️ پراپرتی‌ها
    # ==========================================================

    @property
    def is_high_match(self):
        return self.match_score >= 70

    @property
    def is_good_match(self):
        return 50 <= self.match_score < 70

    @property
    def is_low_match(self):
        return self.match_score < 50

    @property
    def match_level(self):
        if self.match_score >= 70:
            return "عالی"
        elif self.match_score >= 50:
            return "خوب"
        else:
            return "ضعیف"

    @property
    def match_level_class(self):
        if self.match_score >= 70:
            return "success"
        elif self.match_score >= 50:
            return "warning"
        else:
            return "danger"

    @property
    def introduction_status_display(self):
        return dict(self.IntroductionStatus.choices).get(self.introduction_status, self.introduction_status)

    # ==========================================================
    # 📈 متدهای مدیریت وضعیت تطابق
    # ==========================================================

    def send_to_customer(self):
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])

    def mark_as_viewed(self):
        self.status = self.Status.VIEWED
        self.viewed_at = timezone.now()
        self.save(update_fields=['status', 'viewed_at'])

    def mark_as_interested(self, feedback=None):
        self.status = self.Status.INTERESTED
        if feedback:
            self.customer_feedback = feedback
        self.save(update_fields=['status', 'customer_feedback'])

    def mark_as_not_interested(self, feedback=None):
        self.status = self.Status.NOT_INTERESTED
        if feedback:
            self.customer_feedback = feedback
        self.save(update_fields=['status', 'customer_feedback'])

    def mark_as_visit_done(self):
        self.status = self.Status.VISIT_DONE
        self.save(update_fields=['status'])

    def mark_as_offered(self):
        self.status = self.Status.OFFERED
        self.save(update_fields=['status'])

    def mark_as_converted(self):
        self.status = self.Status.CONVERTED
        self.save(update_fields=['status'])

    def mark_as_rejected(self):
        self.status = self.Status.REJECTED
        self.save(update_fields=['status'])

    # ==========================================================
    # 🆕 متدهای مدیریت معرفی
    # ==========================================================

    def set_introduction_result(self, status, note=None, confirmed_by=None):
        self.introduction_status = status
        if note is not None:
            self.introduction_note = note
        if confirmed_by:
            self.confirm_introduction(confirmed_by)
        self.save(update_fields=['introduction_status', 'introduction_note'])
        return self

    def confirm_introduction(self, supervisor):
        self.introduction_confirmed = True
        self.introduction_confirmed_by = supervisor
        self.introduction_confirmed_at = timezone.now()
        self.save(update_fields=[
            'introduction_confirmed',
            'introduction_confirmed_by',
            'introduction_confirmed_at'
        ])
        return self

    def is_introduction_confirmed(self):
        return self.introduction_confirmed

    def get_introduction_summary(self):
        return {
            'status': self.introduction_status,
            'status_display': self.introduction_status_display,
            'note': self.introduction_note,
            'is_confirmed': self.introduction_confirmed,
            'confirmed_by': self.introduction_confirmed_by.get_full_name() if self.introduction_confirmed_by else None,
            'confirmed_at': self.introduction_confirmed_at,
        }

    def get_score_summary(self):
        return {
            'total': self.match_score,
            'location': self.score_location,
            'price': self.score_price,
            'area': self.score_area,
            'rooms': self.score_rooms,
            'requirements': self.score_requirements,
            'property_type': self.score_property_type,
            'contract': self.score_contract,
            'rent': self.score_rent,
            'ownership': self.score_ownership,
        }