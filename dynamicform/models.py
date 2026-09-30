# dynamicform/models.py

from django.db import models
from account.models import User, Role
from django.core.exceptions import ValidationError
from django.utils import timezone


class InputTemplate(models.Model):
    """
    یک نمونه از هر نوع اینپوت با استایل مشخص
    """
    INPUT_TYPES = [
        ('text', 'متن کوتاه'),
        ('textarea', 'متن بلند'),
        ('number', 'عدد'),
        ('email', 'ایمیل'),
        ('phone', 'تلفن'),
        ('date', 'تاریخ'),
        ('datetime', 'تاریخ و زمان'),
        ('time', 'ساعت'),
        ('select', 'انتخاب از لیست'),
        ('checkbox', 'چک‌باکس'),
        ('radio', 'دکمه رادیویی'),
        ('file', 'فایل'),
        ('image', 'تصویر'),
        ('url', 'لینک'),
        ('color', 'رنگ'),
        ('password', 'رمز عبور'),
    ]

    input_type = models.CharField(max_length=20, choices=INPUT_TYPES, unique=True, verbose_name="نوع اینپوت")
    css_class = models.CharField(max_length=200, blank=True, null=True, verbose_name="کلاس CSS")
    wrapper_class = models.CharField(max_length=200, blank=True, null=True, verbose_name="کلاس کانتینر")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "نمونه اینپوت"
        verbose_name_plural = "نمونه اینپوت‌ها"

    def __str__(self):
        return f"{self.get_input_type_display()}"


class FormTemplate(models.Model):
    """
    فرم نمونه (الگو)
    """
    name = models.CharField(max_length=200, unique=True, verbose_name="نام فرم")
    title = models.CharField(max_length=200, verbose_name="عنوان نمایشی")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    inputs = models.ManyToManyField(
        InputTemplate,
        through='FormInput',
        related_name='forms',
        verbose_name="اینپوت‌ها"
    )

    allowed_roles = models.ManyToManyField(
        'account.Role',
        blank=True,
        related_name='accessible_forms',
        verbose_name="نقش‌های مجاز برای استفاده از فرم"
    )

    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="ایجاد شده توسط"
    )

    class Meta:
        verbose_name = "فرم نمونه"
        verbose_name_plural = "فرم‌های نمونه"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def user_can_access(self, user):
        if not user.is_authenticated:
            return False
        if not self.allowed_roles.exists():
            return True
        user_roles = user.user_roles.filter(is_active=True).values_list('role__id', flat=True)
        allowed_roles = self.allowed_roles.values_list('id', flat=True)
        return bool(set(user_roles) & set(allowed_roles))

    def get_max_step(self):
        max_step = self.forminput_set.aggregate(
            models.Max('step_number')
        )['step_number__max']
        return max_step or 1

    def get_fields_by_step(self, step_number):
        return self.forminput_set.filter(
            step_number=step_number
        ).order_by('order')

    def get_steps_info(self):
        steps = {}
        for field in self.forminput_set.all().order_by('step_number', 'order'):
            if field.step_number not in steps:
                steps[field.step_number] = {
                    'fields': [],
                    'count': 0
                }
            steps[field.step_number]['fields'].append(field)
            steps[field.step_number]['count'] += 1
        return steps


class FormInput(models.Model):
    """
    جدول واسط بین فرم و اینپوت‌ها
    """
    form = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, verbose_name="فرم")
    input = models.ForeignKey(InputTemplate, on_delete=models.PROTECT, verbose_name="نوع اینپوت")

    field_name = models.CharField(max_length=100, verbose_name="نام فیلد")
    field_title = models.CharField(max_length=200, verbose_name="عنوان فیلد")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")

    # شماره مرحله
    step_number = models.PositiveIntegerField(
        default=1,
        verbose_name="شماره مرحله",
        help_text="این فیلد در کدام مرحله باید پر شود؟ (همه فیلدهای با شماره یکسان، همزمان نمایش داده می‌شوند)"
    )

    is_required = models.BooleanField(default=False, verbose_name="اجباری")
    placeholder = models.CharField(max_length=200, blank=True, null=True, verbose_name="متن راهنما")
    help_text = models.TextField(blank=True, null=True, verbose_name="راهنمای تکمیلی")
    default_value = models.TextField(blank=True, null=True, verbose_name="مقدار پیش‌فرض")

    # ============ گزینه‌ها (حذف شد و به مدل جداگانه منتقل شد) ============
    # options = models.JSONField(blank=True, null=True)  # ❌ حذف شد
    # ====================================================================

    min_length = models.PositiveIntegerField(blank=True, null=True, verbose_name="حداقل طول")
    max_length = models.PositiveIntegerField(blank=True, null=True, verbose_name="حداکثر طول")
    min_value = models.IntegerField(blank=True, null=True, verbose_name="حداقل مقدار")
    max_value = models.IntegerField(blank=True, null=True, verbose_name="حداکثر مقدار")

    max_file_size = models.PositiveIntegerField(default=5, verbose_name="حداکثر حجم (مگابایت)")
    allowed_extensions = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="پسوندهای مجاز",
        help_text="مثال: .pdf,.doc,.docx یا .jpg,.png,.gif"
    )

    # ============ دسترسی (همون قبلی) ============
    access_type = models.CharField(
        max_length=20,
        choices=[
            ('all', 'همه کاربران'),
            ('specific_role', 'نقش خاص'),
            ('specific_user', 'شخص خاص'),
        ],
        default='all',
        verbose_name="نوع دسترسی"
    )
    allowed_roles = models.ManyToManyField('account.Role', blank=True, verbose_name="نقش‌های مجاز")
    allowed_users = models.ManyToManyField(User, blank=True, verbose_name="کاربران مجاز")

    # ==========================================

    class Meta:
        verbose_name = "فیلد فرم"
        verbose_name_plural = "فیلدهای فرم"
        ordering = ['step_number', 'order']
        unique_together = ['form', 'field_name']

    def __str__(self):
        return f"{self.form.title} - {self.field_title} (مرحله {self.step_number})"

    def get_allowed_extensions_list(self):
        if self.allowed_extensions:
            return [ext.strip() for ext in self.allowed_extensions.split(',')]
        return None

    def get_options_dict(self):
        """دریافت گزینه‌ها به صورت دیکشنری"""
        return {opt.key: opt.value for opt in self.field_options.all().order_by('order')}


class FieldOption(models.Model):
    """
    گزینه‌های فیلدهای انتخابی (select, radio, checkbox)
    """
    form_input = models.ForeignKey(FormInput, on_delete=models.CASCADE, related_name='field_options')
    key = models.CharField(max_length=100, verbose_name="کلید")
    value = models.CharField(max_length=200, verbose_name="مقدار نمایشی")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "گزینه فیلد"
        verbose_name_plural = "گزینه‌های فیلد"
        ordering = ['order']
        unique_together = ['form_input', 'key']

    def __str__(self):
        return f"{self.key}: {self.value}"