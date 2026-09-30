from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from form_flow.models import FormInstance, InstanceField

User = get_user_model()


class Rejection(models.Model):
    """مدل اصلی برگشت فرم"""

    LEVEL_CHOICES = [
        ('field', 'سطح فیلد'),
        ('step', 'سطح مرحله'),
        ('form', 'سطح کل فرم'),
    ]

    STATUS_CHOICES = [
        ('pending', 'در انتظار اصلاح'),
        ('responded', 'پاسخ داده شده'),
        ('fixed', 'اصلاح شده'),
        ('rejected_again', 'دوباره برگشت خورده'),
        ('approved', 'تایید شده'),
        ('expired', 'منقضی شده'),
    ]

    # ارتباط با فرم اصلی
    form_instance = models.ForeignKey(
        FormInstance,
        on_delete=models.CASCADE,
        related_name='rejections'
    )

    # سطح برگشت
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)

    # اگر سطح فیلد باشه
    instance_field = models.ForeignKey(
        InstanceField,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejections'
    )

    # اگر سطح مرحله باشه
    step_number = models.PositiveIntegerField(null=True, blank=True)

    # دلیل برگشت
    reason = models.TextField(verbose_name="دلیل برگشت")

    # کاربر برگشت‌زننده
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rejections_made'
    )

    # کاربر مسئول اصلاح (صاحب فرم یا شخص تعیین شده)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rejections_assigned'
    )

    # وضعیت
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # مهلت اصلاح (ساعت)
    deadline_hours = models.PositiveIntegerField(default=48)
    deadline_at = models.DateTimeField(null=True, blank=True)

    # برای زنجیره‌ای کردن برگشت‌ها (پاسخ به برگشت قبلی)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_rejections'  # ✅ تغییر داده شد
    )

    # تاریخچه
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "برگشت فرم"
        verbose_name_plural = "برگشت‌های فرم"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.form_instance.title} - {self.get_level_display()} - {self.rejected_by.username}"

    def is_expired(self):
        if self.deadline_at and timezone.now() > self.deadline_at:
            return True
        return False

    def get_target_display(self):
        """نمایش هدف برگشت"""
        if self.level == 'field' and self.instance_field:
            return f"فیلد: {self.instance_field.field_title}"
        elif self.level == 'step' and self.step_number:
            return f"مرحله: {self.step_number}"
        else:
            return "کل فرم"

    def get_previous_value(self):
        """دریافت مقدار قبلی فیلد (برای نمایش به کاربر)"""
        if self.level == 'field' and self.instance_field:
            try:
                from form_flow.models import FormFieldValue
                fv = FormFieldValue.objects.filter(
                    form_instance=self.form_instance,
                    instance_field=self.instance_field
                ).first()
                if fv:
                    return fv.value or fv.file_value or fv.image_value
            except:
                pass
        return None


class RejectionReply(models.Model):
    """پاسخ‌ها و گفتگوهای هر برگشت"""

    REPLY_TYPE_CHOICES = [
        ('response', 'پاسخ به برگشت'),
        ('clarification', 'درخواست توضیح بیشتر'),
        ('approve', 'تایید'),
        ('reject_again', 'برگشت مجدد'),
        ('fix', 'اصلاح شد'),
    ]

    rejection = models.ForeignKey(
        Rejection,
        on_delete=models.CASCADE,
        related_name='replies'  # ✅ این保持不变
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # متن پاسخ
    text = models.TextField(verbose_name="متن پاسخ")

    # نوع پاسخ
    reply_type = models.CharField(
        max_length=20,
        choices=REPLY_TYPE_CHOICES,
        default='response'
    )

    # فایل ضمیمه (اختیاری)
    attachment = models.FileField(
        upload_to='rejection_attachments/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="فایل ضمیمه"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "پاسخ به برگشت"
        verbose_name_plural = "پاسخ‌های برگشت"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} - {self.rejection.form_instance.title}"