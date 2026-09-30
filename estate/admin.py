# estate/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Province, City, Neighborhood, PropertyType, UsageType,
    Customer, Requirement, Source, Property, PropertyImage, PropertyVideo, Match,
    Orientation, UnitCondition, DocumentType, OwnershipDocumentType,DisplayCodeCounter
)

admin.site.register(DisplayCodeCounter)


# ============================================================
# 📍 ادمین استان‌ها
# ============================================================

@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']
    ordering = ['name']

    fieldsets = (
        ('اطلاعات استان', {
            'fields': ('name', 'code')
        }),
    )


# ============================================================
# 📍 ادمین شهرستان‌ها
# ============================================================

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'province', 'code']
    list_filter = ['province']
    search_fields = ['name', 'code']
    autocomplete_fields = ['province']
    ordering = ['province__name', 'name']

    fieldsets = (
        ('اطلاعات شهر', {
            'fields': ('name', 'province', 'code')
        }),
        ('موقعیت مکانی', {
            'fields': ('center_latitude', 'center_longitude'),
            'classes': ('collapse',)
        }),
    )


# ============================================================
# 📍 ادمین محله‌ها
# ============================================================

@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ['name', 'city']
    list_filter = ['city__province', 'city']
    search_fields = ['name']
    autocomplete_fields = ['city']
    ordering = ['city__name', 'name']

    fieldsets = (
        ('اطلاعات محله', {
            'fields': ('name', 'city')
        }),
        ('موقعیت مکانی', {
            'fields': ('center_latitude', 'center_longitude'),
            'classes': ('collapse',)
        }),
    )


# ============================================================
# 🏠 ادمین انواع ملک
# ============================================================

@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'icon_display', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['order', 'name']

    def icon_display(self, obj):
        if obj.icon:
            return format_html('<i class="{}"></i>', obj.icon)
        return '-'
    icon_display.short_description = 'آیکون'

    fieldsets = (
        ('اطلاعات نوع ملک', {
            'fields': ('name', 'code', 'icon')
        }),
        ('توضیحات', {
            'fields': ('description',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('order', 'is_active')
        }),
    )


# ============================================================
# 🆕 ادمین انواع کاربری ملک (UsageType)
# ============================================================

@admin.register(UsageType)
class UsageTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'icon_display', 'color_display', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'description']
    ordering = ['order', 'name']

    def icon_display(self, obj):
        if obj.icon:
            return format_html('<i class="{}"></i>', obj.icon)
        return '-'
    icon_display.short_description = 'آیکون'

    def color_display(self, obj):
        return format_html(
            '<span style="display:inline-block; width:20px; height:20px; '
            'background-color:{}; border-radius:4px; border:1px solid #ddd;"></span>',
            obj.color
        )
    color_display.short_description = 'رنگ'

    fieldsets = (
        ('اطلاعات کاربری', {
            'fields': ('name', 'code', 'icon', 'color')
        }),
        ('توضیحات', {
            'fields': ('description',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('order', 'is_active')
        }),
    )


# ============================================================
# 🆕 ادمین نیازهای خاص (Requirement)
# ============================================================

@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'icon_display', 'order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'code', 'category']
    ordering = ['category', 'order', 'name']

    def icon_display(self, obj):
        if obj.icon:
            return format_html('<i class="{}"></i>', obj.icon)
        return '-'
    icon_display.short_description = 'آیکون'

    fieldsets = (
        ('اطلاعات نیاز', {
            'fields': ('name', 'code', 'icon', 'category')
        }),
        ('توضیحات', {
            'fields': ('description',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('order', 'is_active')
        }),
    )


# ============================================================
# 🆕 ادمین منابع مشتری (Source)
# ============================================================

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'icon_display', 'color_display', 'order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'code', 'category']
    ordering = ['category', 'order', 'name']

    def icon_display(self, obj):
        if obj.icon:
            return format_html('<i class="{}"></i>', obj.icon)
        return '-'
    icon_display.short_description = 'آیکون'

    def color_display(self, obj):
        return format_html(
            '<span style="display:inline-block; width:20px; height:20px; '
            'background-color:{}; border-radius:4px; border:1px solid #ddd;"></span>',
            obj.color
        )
    color_display.short_description = 'رنگ'

    fieldsets = (
        ('اطلاعات منبع', {
            'fields': ('name', 'code', 'icon', 'color', 'category')
        }),
        ('توضیحات', {
            'fields': ('description',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('order', 'is_active')
        }),
    )


# ============================================================
# 🆕 ادمین جهت‌ها (Orientation)
# ============================================================

@admin.register(Orientation)
class OrientationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'icon_display', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'description']
    ordering = ['order', 'name']

    def icon_display(self, obj):
        if obj.icon:
            return format_html('<i class="{}"></i>', obj.icon)
        return '-'
    icon_display.short_description = 'آیکون'

    fieldsets = (
        ('اطلاعات جهت', {
            'fields': ('name', 'code', 'icon')
        }),
        ('توضیحات', {
            'fields': ('description',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('order', 'is_active')
        }),
    )


# ============================================================
# 🆕 ادمین وضعیت واحد (UnitCondition)
# ============================================================

@admin.register(UnitCondition)
class UnitConditionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'icon_display', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'description']
    ordering = ['order', 'name']

    def icon_display(self, obj):
        if obj.icon:
            return format_html('<i class="{}"></i>', obj.icon)
        return '-'
    icon_display.short_description = 'آیکون'

    fieldsets = (
        ('اطلاعات وضعیت واحد', {
            'fields': ('name', 'code', 'icon')
        }),
        ('توضیحات', {
            'fields': ('description',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('order', 'is_active')
        }),
    )


# ============================================================
# 🆕 ادمین انواع سند (DocumentType)
# ============================================================

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'description']
    ordering = ['order', 'name']

    fieldsets = (
        ('اطلاعات نوع سند', {
            'fields': ('name', 'code')
        }),
        ('توضیحات', {
            'fields': ('description',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('order', 'is_active')
        }),
    )


# ============================================================
# 🆕 ادمین انواع مالکیت سند (OwnershipDocumentType)
# ============================================================

@admin.register(OwnershipDocumentType)
class OwnershipDocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'description']
    ordering = ['order', 'name']

    fieldsets = (
        ('اطلاعات نوع مالکیت سند', {
            'fields': ('name', 'code')
        }),
        ('توضیحات', {
            'fields': ('description',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('order', 'is_active')
        }),
    )


# ============================================================
# 👤 ادمین مشتریان (Customer) - با پشتیبانی از فیلدهای جدید
# ============================================================

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'full_name_display', 'mobile_display', 'customer_type_badge',
        'status_badge', 'source_badge', 'primary_usage_badge',  # 🆕 primary_usage_badge
        'usage_types_badge', 'budget_summary', 'rent_summary',
        'created_by_display', 'created_at_jalali', 'priority_display'
    ]

    list_filter = [
        'customer_type', 'status', 'rent_type', 'priority',
        'source', 'primary_usage',  # 🆕 فیلتر بر اساس کاربری سندی
        'preferred_usage_types',  # 🆕 فیلتر بر اساس کاربری‌های فرعی
        'preferred_building_orientations',  # 🆕
        'preferred_unit_orientations',  # 🆕
        'preferred_unit_conditions',  # 🆕
        'preferred_document_types',  # 🆕
        'preferred_ownership_document_types',  # 🆕
        'need_completion_certificate',  # 🆕
        'need_document',  # 🆕
        'is_active', 'created_at'
    ]

    search_fields = [
        'user__first_name', 'user__last_name', 'user__username',
        'user__mobile', 'user__email',
        'alternative_phone', 'home_phone', 'work_phone',
        'company_name', 'job_title', 'description'
    ]

    readonly_fields = [
        'id', 'created_at', 'updated_at', 'deleted_at',
        'full_name_display', 'mobile_display', 'email_display',
        'created_at_jalali', 'updated_at_jalali'
    ]

    autocomplete_fields = [
        'user', 'created_by', 'source', 'primary_usage',  # 🆕
        'preferred_cities', 'preferred_neighborhoods',
        'preferred_property_types', 'preferred_requirements',
        'preferred_usage_types',  # 🆕
        'preferred_building_orientations',  # 🆕
        'preferred_unit_orientations',  # 🆕
        'preferred_unit_conditions',  # 🆕
        'preferred_document_types',  # 🆕
        'preferred_ownership_document_types'  # 🆕
    ]

    ordering = ['-priority', '-created_at']

    actions = ['make_active', 'make_inactive', 'set_high_priority', 'set_low_priority']

    fieldsets = (
        ('👤 اطلاعات کاربر', {
            'fields': (
                'user', 'created_by',
                'full_name_display', 'mobile_display', 'email_display'
            )
        }),
        ('📋 نوع و وضعیت', {
            'fields': (
                'customer_type', 'status', 'priority'
            )
        }),
        ('📞 اطلاعات تماس تکمیلی', {
            'fields': (
                'alternative_phone', 'home_phone', 'work_phone'
            )
        }),
        ('💼 اطلاعات شغلی', {
            'fields': (
                'job_title', 'company_name'
            )
        }),
        ('💰 بودجه خرید', {
            'fields': (
                'budget_min', 'budget_max'
            ),
            'classes': ('wide',)
        }),
        ('💰 بودجه اجاره', {
            'fields': (
                'rent_type',
                'mortgage_min', 'mortgage_max',
                'rent_min', 'rent_max'
            ),
            'classes': ('wide',)
        }),
        ('📍 مناطق مورد نظر', {
            'fields': (
                'preferred_cities', 'preferred_neighborhoods'
            ),
            'classes': ('wide',)
        }),
        ('🏠 انواع ملک مورد نظر', {
            'fields': (
                'preferred_property_types',
            ),
            'classes': ('wide',)
        }),
        ('🎯 نیازهای خاص مورد نظر', {
            'fields': (
                'preferred_requirements',
            ),
            'classes': ('wide',),
            'description': 'امکاناتی که مشتری در ملک مورد نظر خود می‌خواهد'
        }),
        # 🆕 بخش کاربری‌ها
        ('🏢 کاربری مورد نظر', {
            'fields': (
                'primary_usage',  # کاربری سندی (اصلی)
                'preferred_usage_types',  # کاربری‌های فرعی
            ),
            'classes': ('wide',),
            'description': 'کاربری سندی و کاربردهای فرعی که مشتری به آنها علاقه دارد'
        }),
        ('📢 منبع مشتری', {
            'fields': (
                'source',
            ),
            'description': 'منبعی که مشتری از طریق آن به ما معرفی شده است'
        }),
        ('📐 مشخصات فنی ملک', {
            'fields': (
                'min_area', 'max_area',
                'min_rooms', 'max_rooms'
            ),
            'classes': ('wide',)
        }),
        # 🆕 مشخصات فنی جدید (طبقه، تعداد طبقات، واحد در طبقه، دانگ)
        ('🏗️ مشخصات ساختمانی مورد نظر', {
            'fields': (
                'preferred_min_floor', 'preferred_max_floor',
                'preferred_min_total_floors', 'preferred_max_total_floors',
                'preferred_min_units_per_floor', 'preferred_max_units_per_floor',
                'preferred_dong_min', 'preferred_dong_max',
            ),
            'classes': ('wide',)
        }),
        # 🆕 جهت‌ها و وضعیت واحد
        ('🧭 جهت‌ها و وضعیت واحد مورد نظر', {
            'fields': (
                'preferred_building_orientations',
                'preferred_unit_orientations',
                'preferred_unit_conditions',
            ),
            'classes': ('wide',)
        }),
        # 🆕 وضعیت سند و پایان کار
        ('📄 وضعیت سند و پایان کار مورد نظر', {
            'fields': (
                'need_completion_certificate',
                'need_document',
                'preferred_document_types',
                'preferred_ownership_document_types',
            ),
            'classes': ('wide',)
        }),
        ('🎯 نیازهای ویژه', {
            'fields': (
                'special_needs',
            ),
            'classes': ('wide',)
        }),
        ('📝 منبع و توضیحات', {
            'fields': (
                'description',
            )
        }),
        ('📊 تاریخچه تعاملات', {
            'fields': (
                'last_contact', 'total_interactions'
            )
        }),
        ('⚙️ اطلاعات سیستمی', {
            'fields': (
                'id', 'is_active',
                'created_at', 'created_at_jalali',
                'updated_at', 'updated_at_jalali'
            ),
            'classes': ('collapse',)
        }),
    )

    # ========== متدهای نمایش ==========

    def full_name_display(self, obj):
        url = reverse('admin:account_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}" style="font-weight: bold;">{}</a>',
            url, obj.full_name
        )
    full_name_display.short_description = 'نام و نام خانوادگی'

    def mobile_display(self, obj):
        return format_html(
            '<span dir="ltr">{}</span>',
            obj.mobile
        )
    mobile_display.short_description = 'موبایل'

    def email_display(self, obj):
        if obj.email:
            return format_html('<a href="mailto:{}">{}</a>', obj.email, obj.email)
        return '-'
    email_display.short_description = 'ایمیل'

    def customer_type_badge(self, obj):
        colors = {
            'buyer': '#28a745',
            'tenant': '#17a2b8',
            'developer': '#ffc107',
            'investor': '#6f42c1',
            'all': '#6c757d',
        }
        color = colors.get(obj.customer_type, '#6c757d')
        text = obj.get_customer_type_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 12px;">{}</span>',
            color, text
        )
    customer_type_badge.short_description = 'نوع مشتری'

    def status_badge(self, obj):
        colors = {
            'new': '#17a2b8',
            'confirmed': '#28a745',
            'assigned': '#007bff',
            'waiting': '#fd7e14',
            'deposit': '#ffc107',
            'in_meeting': '#6f42c1',
            'contract': '#20c997',
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        text = obj.get_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 12px;">{}</span>',
            color, text
        )
    status_badge.short_description = 'وضعیت'

    def source_badge(self, obj):
        if obj.source:
            color = obj.source.color or '#6c757d'
            icon = obj.source.icon or ''
            return format_html(
                '<span style="background-color: {}; color: white; padding: 2px 10px; '
                'border-radius: 12px; font-size: 11px;">'
                '{} {}'
                '</span>',
                color,
                format_html('<i class="{}"></i>', icon) if icon else '',
                obj.source.name
            )
        return '-'
    source_badge.short_description = 'منبع'

    # 🆕 متد نمایش کاربری سندی
    def primary_usage_badge(self, obj):
        if obj.primary_usage:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 2px 10px; '
                'border-radius: 12px; font-size: 11px;">'
                '<i class="fas fa-star"></i> {}'
                '</span>',
                obj.primary_usage.color or '#6c757d',
                obj.primary_usage.name
            )
        return '-'
    primary_usage_badge.short_description = 'کاربری سندی'

    # 🆕 متد نمایش کاربری‌های فرعی
    def usage_types_badge(self, obj):
        usages = obj.preferred_usage_types.filter(is_active=True)
        if usages.exists():
            badges = []
            for usage in usages[:3]:
                badges.append(
                    format_html(
                        '<span style="background-color: {}; color: white; padding: 2px 8px; '
                        'border-radius: 10px; font-size: 10px; margin: 1px;">'
                        '{} {}'
                        '</span>',
                        usage.color or '#6c757d',
                        format_html('<i class="{}"></i>', usage.icon) if usage.icon else '',
                        usage.name
                    )
                )
            if usages.count() > 3:
                badges.append(
                    format_html(
                        '<span style="background-color: #6c757d; color: white; padding: 2px 8px; '
                        'border-radius: 10px; font-size: 10px; margin: 1px;">'
                        '+{}'
                        '</span>',
                        usages.count() - 3
                    )
                )
            return format_html(' '.join(badges))
        return '-'
    usage_types_badge.short_description = 'کاربری‌های فرعی'

    def priority_display(self, obj):
        if obj.priority == 0:
            return '-'
        stars = '⭐' * obj.priority
        return format_html(
            '<span style="color: #ffc107;">{}</span>',
            stars
        )
    priority_display.short_description = 'اولویت'

    def budget_summary(self, obj):
        if obj.budget_min and obj.budget_max:
            return format_html(
                '<span dir="ltr">{:,.0f} - {:,.0f} تومان</span>',
                obj.budget_min, obj.budget_max
            )
        elif obj.budget_max:
            return format_html(
                '<span dir="ltr">≤ {:,.0f} تومان</span>',
                obj.budget_max
            )
        elif obj.budget_min:
            return format_html(
                '<span dir="ltr">≥ {:,.0f} تومان</span>',
                obj.budget_min
            )
        return '-'
    budget_summary.short_description = 'بودجه خرید'

    def rent_summary(self, obj):
        parts = []
        if obj.rent_min and obj.rent_max:
            parts.append(f"اجاره: {obj.rent_min:,.0f} - {obj.rent_max:,.0f}")
        elif obj.rent_max:
            parts.append(f"اجاره: ≤ {obj.rent_max:,.0f}")
        elif obj.rent_min:
            parts.append(f"اجاره: ≥ {obj.rent_min:,.0f}")

        if obj.mortgage_min and obj.mortgage_max:
            parts.append(f"رهن: {obj.mortgage_min:,.0f} - {obj.mortgage_max:,.0f}")
        elif obj.mortgage_max:
            parts.append(f"رهن: ≤ {obj.mortgage_max:,.0f}")
        elif obj.mortgage_min:
            parts.append(f"رهن: ≥ {obj.mortgage_min:,.0f}")

        if parts:
            return format_html(
                '<span style="font-size: 11px;">{}</span>',
                ' | '.join(parts)
            )
        return '-'
    rent_summary.short_description = 'بودجه اجاره'

    def created_by_display(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return 'سیستم'
    created_by_display.short_description = 'ثبت‌کننده'

    def created_at_jalali(self, obj):
        return obj.get_jalali_created()
    created_at_jalali.short_description = 'تاریخ ایجاد (شمسی)'

    def updated_at_jalali(self, obj):
        try:
            import jdatetime
            jalali = jdatetime.date.fromgregorian(date=obj.updated_at)
            return f"{jalali.year}/{jalali.month}/{jalali.day}"
        except:
            return '-'
    updated_at_jalali.short_description = 'تاریخ بروزرسانی (شمسی)'

    # ========== اکشن‌ها ==========

    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} مشتری فعال شدند.')
    make_active.short_description = 'فعال کردن مشتریان انتخاب شده'

    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} مشتری غیرفعال شدند.')
    make_inactive.short_description = 'غیرفعال کردن مشتریان انتخاب شده'

    def set_high_priority(self, request, queryset):
        updated = queryset.update(priority=10)
        self.message_user(request, f'{updated} مشتری اولویت بالا گرفتند.')
    set_high_priority.short_description = 'تنظیم اولویت بالا (۱۰)'

    def set_low_priority(self, request, queryset):
        updated = queryset.update(priority=0)
        self.message_user(request, f'{updated} مشتری اولویت پایین گرفتند.')
    set_low_priority.short_description = 'تنظیم اولویت پایین (۰)'

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'created_by', 'source', 'primary_usage'  # 🆕
        ).prefetch_related(
            'preferred_cities', 'preferred_neighborhoods',
            'preferred_property_types', 'preferred_requirements',
            'preferred_usage_types',  # 🆕
            'preferred_building_orientations',  # 🆕
            'preferred_unit_orientations',  # 🆕
            'preferred_unit_conditions',  # 🆕
            'preferred_document_types',  # 🆕
            'preferred_ownership_document_types'  # 🆕
        )


# ============================================================
# 🏠 ادمین املاک (Property) - با پشتیبانی از فیلدهای جدید
# ============================================================

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = [
        'title_display', 'property_type', 'primary_usage_badge',
        'get_usage_types_display', 'unit_condition_badge',  # 🆕
        'price_display', 'area', 'units_per_floor_display',  # 🆕
        'status_badge', 'is_visible'
    ]

    list_filter = [
        'status', 'contract_type', 'property_type',
        'primary_usage',  # 🆕
        'usage_types',  # 🆕
        'unit_condition',  # 🆕
        'building_orientation',  # 🆕
        'unit_orientation',  # 🆕
        'has_completion_certificate',  # 🆕
        'has_document',  # 🆕
        'document_type',  # 🆕
        'ownership_document_type',  # 🆕
        'is_visible', 'is_featured', 'is_active'
    ]

    search_fields = [
        'title', 'address', 'description',
        'owner__first_name', 'owner__last_name',
        'owner__mobile'
    ]

    readonly_fields = ['id', 'created_at', 'updated_at', 'views_count']
    autocomplete_fields = [
        'owner', 'created_by', 'province', 'city', 'neighborhood',
        'primary_usage',  # 🆕
        'unit_condition',  # 🆕
        'building_orientation',  # 🆕
        'unit_orientation',  # 🆕
        'document_type',  # 🆕
        'ownership_document_type'  # 🆕
    ]
    filter_horizontal = ['requirements', 'usage_types']  # 🆕 اضافه کردن usage_types
    ordering = ['-created_at']

    fieldsets = (
        ('اطلاعات پایه', {
            'fields': (
                'title', 'property_type', 'status', 'contract_type'
            )
        }),
        # 🆕 بخش کاربری‌ها
        ('🏢 انواع کاربری ملک', {
            'fields': (
                'primary_usage',  # کاربری سندی
                'usage_types',   # کاربری‌های فرعی
            ),
            'classes': ('wide',),
            'description': 'کاربری سندی و کاربردهای فرعی این ملک'
        }),
        ('💰 قیمت‌ها', {
            'fields': (
                'price', 'is_price_negotiable',
                'rent_price', 'is_rent_negotiable',
                'mortgage_price'
            ),
            'classes': ('wide',)
        }),
        # 🆕 مشخصات فیزیکی (با فیلدهای جدید)
        ('📐 مشخصات فیزیکی', {
            'fields': (
                'area', 'rooms', 'floor', 'total_floors',
                'units_per_floor',  # 🆕
                'built_year', 'is_new_building',
                'parking_type', 'ownership_type',
                'unit_condition'  # 🆕 (جایگزین furnishing_status)
            ),
            'classes': ('wide',)
        }),
        # 🆕 جهت‌ها
        ('🧭 جهت‌ها', {
            'fields': (
                'building_orientation',
                'unit_orientation',
            ),
            'classes': ('wide',)
        }),
        # 🆕 وضعیت سند و پایان کار
        ('📄 وضعیت سند و پایان کار', {
            'fields': (
                'has_completion_certificate',
                'has_document',
                'document_type',
                'ownership_document_type',
                'dong',  # میزان دانگ
            ),
            'classes': ('wide',)
        }),
        ('📍 موقعیت مکانی', {
            'fields': (
                'province', 'city', 'neighborhood', 'address',
                'latitude', 'longitude'
            ),
            'classes': ('wide',)
        }),
        ('🎯 امکانات', {
            'fields': (
                'requirements',
            ),
            'classes': ('wide',)
        }),
        ('📝 توضیحات', {
            'fields': (
                'description', 'short_description'
            ),
            'classes': ('wide',)
        }),
        ('📞 اطلاعات تماس', {
            'fields': (
                'contact_name', 'contact_phone', 'contact_email'
            ),
            'classes': ('wide',)
        }),
        ('👤 مالک و ثبت‌کننده', {
            'fields': (
                'owner', 'created_by'
            )
        }),
        ('🏷️ وضعیت نمایش', {
            'fields': (
                'is_visible', 'is_featured', 'is_verified'
            )
        }),
        ('📊 آمار', {
            'fields': (
                'views_count', 'favorites_count', 'published_at'
            )
        }),
        ('⚙️ اطلاعات سیستمی', {
            'fields': (
                'id', 'is_active', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )

    # ========== متدهای نمایش ==========

    def title_display(self, obj):
        url = reverse('admin:estate_property_change', args=[obj.id])
        return format_html(
            '<a href="{}" style="font-weight: bold;">{}</a>',
            url, obj.title or 'بدون عنوان'
        )
    title_display.short_description = 'عنوان'

    def primary_usage_badge(self, obj):
        if obj.primary_usage:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 2px 10px; '
                'border-radius: 12px; font-size: 11px;">'
                '<i class="fas fa-star"></i> {}'
                '</span>',
                obj.primary_usage.color or '#6c757d',
                obj.primary_usage.name
            )
        return '-'
    primary_usage_badge.short_description = 'کاربری سندی'

    def get_usage_types_display(self, obj):
        usages = obj.usage_types.filter(is_active=True)
        if usages.exists():
            badges = []
            for usage in usages[:3]:
                badges.append(
                    format_html(
                        '<span style="background-color: {}; color: white; padding: 2px 8px; '
                        'border-radius: 10px; font-size: 10px; margin: 1px;">'
                        '<i class="{}"></i> {}'
                        '</span>',
                        usage.color or '#6c757d',
                        usage.icon or 'fa-tag',
                        usage.name
                    )
                )
            if usages.count() > 3:
                badges.append(
                    format_html(
                        '<span style="background-color: #6c757d; color: white; padding: 2px 8px; '
                        'border-radius: 10px; font-size: 10px; margin: 1px;">'
                        '+{}'
                        '</span>',
                        usages.count() - 3
                    )
                )
            return format_html(' '.join(badges))
        return '-'
    get_usage_types_display.short_description = 'کاربری‌ها'

    # 🆕 متد نمایش وضعیت واحد
    def unit_condition_badge(self, obj):
        if obj.unit_condition:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 2px 10px; '
                'border-radius: 12px; font-size: 11px;">'
                '<i class="{}"></i> {}'
                '</span>',
                obj.unit_condition.icon or 'fa-home',
                obj.unit_condition.name
            )
        return '-'
    unit_condition_badge.short_description = 'وضعیت واحد'

    # 🆕 متد نمایش واحد در طبقه
    def units_per_floor_display(self, obj):
        if obj.units_per_floor:
            return format_html(
                '<span dir="ltr">{} واحد</span>',
                obj.units_per_floor
            )
        return '-'
    units_per_floor_display.short_description = 'واحد در طبقه'

    def price_display(self, obj):
        if obj.price:
            return format_html(
                '<span dir="ltr">{:,.0f} تومان</span>',
                obj.price
            )
        return '-'
    price_display.short_description = 'قیمت'

    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'confirmed': '#28a745',
            'deposit': '#17a2b8',
            'in_meeting': '#6f42c1',
            'contract': '#20c997',
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'property_type', 'primary_usage', 'unit_condition',
            'building_orientation', 'unit_orientation',
            'document_type', 'ownership_document_type'
        ).prefetch_related(
            'usage_types', 'requirements'
        )


# ============================================================
# 🖼️ ادمین تصاویر ملک
# ============================================================

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ['property_ref', 'image_preview', 'order', 'is_main', 'uploaded_at']
    list_filter = ['is_main']
    search_fields = ['property_ref__title', 'caption']
    autocomplete_fields = ['property_ref']
    ordering = ['property_ref', 'order']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'تصویر'


# ============================================================
# 🎬 ادمین ویدئوهای ملک
# ============================================================

@admin.register(PropertyVideo)
class PropertyVideoAdmin(admin.ModelAdmin):
    list_display = ['property_ref', 'video_type', 'title', 'order', 'is_main', 'uploaded_at']
    list_filter = ['video_type', 'is_main']
    search_fields = ['property_ref__title', 'title', 'description']
    autocomplete_fields = ['property_ref']
    ordering = ['property_ref', 'order']


# ============================================================
# 🎯 ادمین تطابق‌ها (Match)
# ============================================================

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = [
        'customer_display', 'property_display', 'match_score_display',
        'match_level_badge', 'status_badge', 'created_at'
    ]
    list_filter = ['status', 'match_type', 'match_score', 'created_at']
    search_fields = ['customer__user__first_name', 'customer__user__last_name', 'property_ref__title']
    autocomplete_fields = ['customer', 'property_ref', 'created_by', 'reviewed_by']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-match_score', '-created_at']

    fieldsets = (
        ('🔗 ارتباطات', {
            'fields': ('customer', 'property_ref')
        }),
        ('📊 امتیازات', {
            'fields': (
                'match_score', 'score_location', 'score_price',
                'score_area', 'score_rooms', 'score_requirements',
                'score_property_type', 'score_contract',
                'score_rent', 'score_ownership'
            ),
            'classes': ('wide',)
        }),
        ('📋 اطلاعات تطابق', {
            'fields': ('match_type', 'match_details', 'status')
        }),
        ('📝 یادداشت‌ها', {
            'fields': ('expert_note', 'customer_feedback')
        }),
        ('📅 تاریخچه', {
            'fields': ('sent_at', 'viewed_at', 'reviewed_at')
        }),
        ('👤 کاربران', {
            'fields': ('created_by', 'reviewed_by')
        }),
        ('⚙️ اطلاعات سیستمی', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # ========== متدهای نمایش ==========

    def customer_display(self, obj):
        url = reverse('admin:estate_customer_change', args=[obj.customer.id])
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.customer.full_name
        )
    customer_display.short_description = 'مشتری'

    def property_display(self, obj):
        url = reverse('admin:estate_property_change', args=[obj.property_ref.id])
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.property_ref.title
        )
    property_display.short_description = 'ملک'

    def match_score_display(self, obj):
        return format_html(
            '<span style="font-weight: bold; font-size: 14px;">{}%</span>',
            obj.match_score
        )
    match_score_display.short_description = 'امتیاز'

    def match_level_badge(self, obj):
        colors = {
            'عالی': '#28a745',
            'خوب': '#ffc107',
            'ضعیف': '#dc3545',
        }
        color = colors.get(obj.match_level, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 10px; '
            'border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.match_level
        )
    match_level_badge.short_description = 'سطح تطابق'

    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'reviewed': '#17a2b8',
            'sent': '#007bff',
            'interested': '#28a745',
            'not_interested': '#dc3545',
            'visit_done': '#fd7e14',
            'offered': '#ffc107',
            'converted': '#20c997',
            'rejected': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 10px; '
            'border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'