from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Role, UserRole, Permission, RolePermission, Confirm_moile


# ============================================================
# 📌 ۱. ادمین Role
# ============================================================

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['title', 'name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'title']
    list_editable = ['is_active']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'title', 'description')
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        }),
    )


# ============================================================
# 📌 ۲. ادمین UserRole
# ============================================================

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'is_active', 'assigned_at', 'assigned_by']
    list_filter = ['role', 'is_active']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'role__title']
    list_editable = ['is_active']

    raw_id_fields = ['user', 'assigned_by']


# ============================================================
# 📌 ۳. ادمین Permission (همون مدلی که میخواستی)
# ============================================================

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """مدیریت مجوزها - نمایش کامل و قابل ویرایش"""

    # 📋 ستون‌های نمایشی (همه فیلدها)
    list_display = [
        'id',
        'code',
        'name',
        'group',
        'description_preview',
    ]

    # 🔍 جستجو در همه فیلدها
    search_fields = [
        'code',
        'name',
        'group',
        'description',
    ]

    # 🎯 فیلتر بر اساس گروه
    list_filter = [
        'group',
    ]

    # ✏️ ویرایش مستقیم در لیست
    list_editable = [
        'name',
        'group',
    ]

    # 📊 مرتب‌سازی پیش‌فرض
    ordering = ['group', 'code']

    # 📄 تعداد آیتم در هر صفحه
    list_per_page = 50

    # 📝 گروه‌بندی فیلدها در فرم ویرایش
    fieldsets = (
        ('اطلاعات مجوز', {
            'fields': ('code', 'name', 'group', 'description'),
            'classes': ('wide',),
        }),
    )

    def description_preview(self, obj):
        """نمایش خلاصه توضیحات در لیست"""
        if obj.description:
            return obj.description[:50] + ('...' if len(obj.description) > 50 else '')
        return '-'

    description_preview.short_description = 'توضیحات'


# ============================================================
# 📌 ۴. ادمین RolePermission
# ============================================================

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'permission']
    list_filter = ['role']
    search_fields = ['role__name', 'permission__name']


# ============================================================
# 📌 ۵. ادمین Confirm_moile
# ============================================================

@admin.register(Confirm_moile)
class ConfirmMobileAdmin(admin.ModelAdmin):
    list_display = ['mobile', 'random_pass']


# ============================================================
# 📌 ۶. ادمین User (سفارشی شده)
# ============================================================

class CustomUserAdmin(BaseUserAdmin):
    list_display = [
        'username',
        'first_name',
        'last_name',
        'mobile',
        'get_roles_display',
        'is_active'
    ]

    list_filter = [
        'is_active',
        'is_staff',
        'is_superuser'
    ]

    search_fields = [
        'username',
        'first_name',
        'last_name',
        'mobile',
        'phone'
    ]

    fieldsets = BaseUserAdmin.fieldsets + (
        ('اطلاعات شخصی', {
            'fields': ('mobile', 'phone', 'confirm_mobile', 'birth_date', 'user_image')
        }),
        ('آدرس', {
            'fields': ('state', 'city', 'home_address', 'post_code')
        }),
        ('اطلاعات بانکی', {
            'fields': (
                'bank_name',
                'bank_card_number',
                'bank_account_number',
                'bank_sheba_number',
                'bank_address',
                'bank_code'
            )
        }),
        ('کیف پول', {
            'fields': ('wallet',)
        }),
        ('تنظیمات ظاهری', {
            'fields': ('back_mode',)
        }),
    )

    def get_roles_display(self, obj):
        return " , ".join(obj.get_role_names())

    get_roles_display.short_description = 'نقش‌ها'


# ============================================================
# 📌 ۷. ثبت User با CustomUserAdmin
# ============================================================

admin.site.register(User, CustomUserAdmin)

# ============================================================
# 📌 ۸. تنظیمات Header ادمین
# ============================================================

admin.site.site_header = '🚀 مدیریت سیستم Shanimo'
admin.site.site_title = 'پنل ادمین Shanimo'
admin.site.index_title = '📊 داشبورد مدیریت'