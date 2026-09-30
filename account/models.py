from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime
import os


def get_filename_ext(filepath):
    base_name = os.path.basename(filepath)
    name, ext = os.path.splitext(base_name)
    return name, ext


def upload_image_path(instance, filename):
    name, ext = get_filename_ext(filename)
    final_name = f"{instance.id}{ext}"
    return f"users/image/{instance.id}/{final_name}"


class Confirm_moile(models.Model):
    mobile = models.CharField(max_length=12, blank=True, null=True)
    random_pass = models.IntegerField(blank=True, null=True)


# ==================== مدل جدید برای مدیریت دسترسی‌های پویا ====================
class Role(models.Model):
    """
    مدل نقش‌ها (دسترسی‌ها) - می‌توانید بدون کدنویسی نقش جدید ایجاد کنید
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="نام نقش")
    title = models.CharField(max_length=100, verbose_name="عنوان نمایشی")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "نقش"
        verbose_name_plural = "نقش‌ها"
        ordering = ['name']

    def __str__(self):
        return self.title


class UserRole(models.Model):
    """
    مدل ارتباط کاربر و نقش‌ها (هر کاربر می‌تواند چندین نقش داشته باشد)
    """
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_users')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_roles')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "نقش کاربر"
        verbose_name_plural = "نقش‌های کاربران"
        unique_together = ['user', 'role']  # هر کاربر فقط یک بار می‌تواند یک نقش را داشته باشد

    def __str__(self):
        return f"{self.user.username} - {self.role.title}"


class Permission(models.Model):
    """
    مدل مجوزهای دقیق (اختیاری - برای دسترسی‌های سطح پایین)
    """
    group = models.CharField(max_length=100, null=True, blank=True)
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)  # مثل: 'warehouse.view'
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "مجوز"
        verbose_name_plural = "مجوزها"

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """
    مدل ارتباط نقش و مجوزها (هر نقش می‌تواند چندین مجوز داشته باشد)
    """
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='permission_roles')

    class Meta:
        verbose_name = "مجوز نقش"
        verbose_name_plural = "مجوزهای نقش"
        unique_together = ['role', 'permission']


class User(AbstractUser):
    # user_information
    back_mode = models.CharField(max_length=50, blank=True, null=True)  # dark and light
    random_pass = models.IntegerField(blank=True, null=True)
    mobile = models.CharField(max_length=12, blank=True, null=True)
    phone = models.CharField(max_length=12, blank=True, null=True)
    confirm_mobile = models.BooleanField(default=False)
    state = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    home_address = models.CharField(max_length=400, blank=True, null=True)
    post_code = models.CharField(max_length=15, blank=True, null=True)
    birth_date = models.DateTimeField(blank=True, null=True)  # تاریخ تولد

    # bank_information
    bank_name = models.CharField(max_length=50, null=True, blank=True)
    bank_card_number = models.CharField(max_length=16, null=True, blank=True)  # شماره کارت
    bank_account_number = models.CharField(max_length=30, null=True, blank=True)  # شماره حساب (اصلاح نام فیلد)
    bank_sheba_number = models.CharField(max_length=50, null=True, blank=True)  # شبا
    bank_address = models.CharField(max_length=400, blank=True, null=True)  # شعبه بانک
    bank_code = models.CharField(max_length=12, blank=True, null=True)  # کد شعبه
    wallet = models.IntegerField(default=0, blank=True, null=True)
    referral = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',
        verbose_name="سرپرست",
        help_text="کاربری که این فرد زیر نظر او کار می‌کند."
    )

    # ============================================================
    # 📊 فیلدهای مدیریتی برای کارشناسان
    # ============================================================
    max_concurrent = models.PositiveIntegerField(
        default=5,
        verbose_name="حداکثر پرونده‌های همزمان",
        help_text="فقط برای کارشناسان"
    )
    is_available = models.BooleanField(
        default=True,
        verbose_name="در دسترس",
        help_text="آیا کارشناس برای پذیرش پرونده جدید در دسترس است؟"
    )

    # user_documents_image
    user_image = models.ImageField(upload_to=upload_image_path, null=True, blank=True)

    # حذف فیلد admin_access و جایگزینی با سیستم نقش‌ها
    # admin_access = models.BooleanField(default=False)  # حذف شود

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name else self.username

    # ==================== متدهای کمکی برای بررسی دسترسی‌ها ====================

    def has_role(self, role_name):
        """
        بررسی می‌کند که کاربر دارای یک نقش خاص هست یا نه
        استفاده: user.has_role('admin') یا user.has_role('warehouse')
        """
        return self.user_roles.filter(role__name=role_name, is_active=True).exists()

    def has_any_role(self, role_names):
        """
        بررسی می‌کند که کاربر حداقل یکی از نقش‌های مشخص شده را دارد
        استفاده: user.has_any_role(['admin', 'accountant'])
        """
        return self.user_roles.filter(role__name__in=role_names, is_active=True).exists()

    def has_all_roles(self, role_names):
        """
        بررسی می‌کند که کاربر تمام نقش‌های مشخص شده را دارد
        """
        user_roles = set(self.user_roles.filter(is_active=True).values_list('role__name', flat=True))
        return set(role_names).issubset(user_roles)

    def get_roles(self):
        """
        دریافت لیست تمام نقش‌های کاربر
        """
        return list(self.user_roles.filter(is_active=True).select_related('role'))

    def get_role_names(self):
        """
        دریافت لیست نام نقش‌های کاربر
        """
        return list(self.user_roles.filter(is_active=True).values_list('role__name', flat=True))

    def has_permission(self, permission_code):
        """
        بررسی می‌کند که کاربر دارای یک مجوز خاص هست یا نه
        استفاده: user.has_permission('warehouse.add_product')
        """
        return self.user_roles.filter(
            is_active=True,
            role__role_permissions__permission__code=permission_code,
            role__role_permissions__is_active=True
        ).exists()

    @property
    def is_admin(self):
        """بررسی ادمین بودن کاربر"""
        return self.has_role('admin')

    @property
    def is_accountant(self):
        """بررسی حسابدار بودن کاربر"""
        return self.has_role('accountant')

    @property
    def is_warehouse(self):
        """بررسی انباردار بودن کاربر"""
        return self.has_role('warehouse')

    @property
    def is_service(self):
        """بررسی خدمات بودن کاربر"""
        return self.has_role('service')

    @property
    def is_customer(self):
        """بررسی مشتری بودن کاربر"""
        return self.has_role('customer')

    def assign_role(self, role_name, assigned_by=None):
        """
        اختصاص نقش به کاربر
        """
        try:
            role = Role.objects.get(name=role_name, is_active=True)
            user_role, created = UserRole.objects.get_or_create(
                user=self,
                role=role,
                defaults={'assigned_by': assigned_by}
            )
            if not created and not user_role.is_active:
                user_role.is_active = True
                user_role.save()
            return True
        except Role.DoesNotExist:
            return False

    def remove_role(self, role_name):
        """
        حذف نقش از کاربر
        """
        try:
            user_role = self.user_roles.get(role__name=role_name)
            user_role.is_active = False
            user_role.save()
            return True
        except UserRole.DoesNotExist:
            return False