# form_flow/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from dynamicform.models import FormTemplate, FormInput, FieldOption

User = get_user_model()


class FormInstance(models.Model):
    """
    کپی اجرایی از فرم نمونه (با قابلیت سفارشی‌سازی)
    """
    original_template = models.ForeignKey(
        FormTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instances',
        verbose_name="نمونه فرم اصلی"
    )

    name = models.CharField(max_length=200, unique=True, verbose_name="نام فرم کپی")
    title = models.CharField(max_length=200, verbose_name="عنوان فرم کپی")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    custom_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="نام اختصاصی")

    deadline_hours = models.PositiveIntegerField(
        default=24,  # ✅ پیش‌فرض ۲۴ ساعت (۱ روز)
        verbose_name="زمان مهلت (ساعت)",
        help_text="0 = بدون محدودیت زمانی"
    )

    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('in_progress', 'در حال تکمیل'),
        ('waiting', 'در انتظار'),
        ('overdue', 'تاخیر داشته'),
        ('completed', 'تکمیل شده'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
        ('canceled', 'لغو شده'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")

    current_step_number = models.PositiveIntegerField(default=1, verbose_name="شماره مرحله فعلی")
    step_started_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان شروع مرحله فعلی")
    step_deadline = models.DateTimeField(null=True, blank=True, verbose_name="مهلت مرحله فعلی")

    # ============ تاریخچه دقیق مراحل ============
    step_history = models.JSONField(default=list, blank=True, verbose_name="تاریخچه مراحل")
    # هر آیتم: {'step_number': 1, 'title': '...', 'started_at': '...', 'completed_at': '...',
    #           'duration_hours': 2.5, 'completed_by': 1, 'completed_by_name': 'علی',
    #           'was_overdue': False, 'deadline': '...', 'is_active': True}
    # =============================================

    # ============ زمان‌بندی هر مرحله ============
    step_deadlines = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="زمان مهلت هر مرحله",
        help_text="مثال: {'1': 24, '2': 48, '3': 72}"
    )
    # =============================================

    started_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان شروع")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان تکمیل")
    overdue_count = models.PositiveIntegerField(default=0, verbose_name="تعداد تاخیرها")

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_forms',
        verbose_name="ایجاد شده توسط"
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_forms',
        verbose_name="اختصاص داده شده به"
    )

    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    is_rejected = models.BooleanField(default=False)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        'account.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_forms'
    )
    rejection_reason = models.TextField(blank=True, null=True)
    rejection_level = models.CharField(
        max_length=10,
        choices=[('field', 'فیلد'), ('step', 'مرحله'), ('form', 'کل فرم')],
        blank=True,
        null=True
    )
    total_rejections = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "فرم در حال اجرا"
        verbose_name_plural = "فرم‌های در حال اجرا"
        ordering = ['-started_at']

    def __str__(self):
        return self.custom_name or self.title

    # ==================== متدهای زمان ====================

    def get_deadline(self):
        """دریافت زمان مهلت کل فرم"""
        if self.deadline_hours == 0:
            return None
        return self.started_at + timedelta(hours=self.deadline_hours)

    def is_overdue(self):
        """بررسی تاخیر کل فرم"""
        if self.deadline_hours == 0 or self.status in ['completed', 'approved', 'rejected', 'canceled']:
            return False
        deadline = self.get_deadline()
        if deadline and timezone.now() > deadline:
            return True
        return False

    def get_step_progress(self):
        """دریافت پیشرفت مرحله فعلی"""
        if not self.step_deadline:
            return {'progress': 0, 'remaining': None}
        now = timezone.now()
        total = (self.step_deadline - self.step_started_at).total_seconds()
        elapsed = (now - self.step_started_at).total_seconds()
        progress = min((elapsed / total) * 100, 100) if total > 0 else 0
        return {
            'progress': round(progress, 1),
            'remaining': (self.step_deadline - now).total_seconds() if now < self.step_deadline else 0,
            'is_overdue': now > self.step_deadline,
            'deadline': self.step_deadline,
        }

    def get_step_overdue_status(self, step_number):
        """بررسی تاخیر یک مرحله خاص"""
        history = self.step_history or []
        for item in history:
            if item.get('step_number') == step_number:
                return item.get('was_overdue', False)
        return False

    def get_step_duration(self, step_number):
        """دریافت مدت زمان تکمیل یک مرحله"""
        history = self.step_history or []
        for item in history:
            if item.get('step_number') == step_number:
                return item.get('duration_hours', 0)
        return 0

    # ==================== متدهای مراحل ====================

    def get_max_step(self):
        """دریافت آخرین شماره مرحله"""
        max_step = self.fields.aggregate(models.Max('step_number'))['step_number__max']
        return max_step or 1

    def get_fields_by_step(self, step_number):
        """دریافت فیلدهای یک مرحله"""
        return self.fields.filter(step_number=step_number, is_active=True).order_by('order')

    def get_available_fields(self, user):
        """دریافت فیلدهای قابل دسترس برای کاربر"""
        available = []
        for field in self.fields.filter(is_active=True).order_by('step_number', 'order'):
            if field.is_accessible_by(user):
                available.append(field)
        return available

    def get_step_title(self, step_number):
        """دریافت عنوان مرحله"""
        field = self.fields.filter(step_number=step_number).first()
        if field:
            # می‌تونی از عنوان فیلد اول استفاده کنی یا یه عنوان اختصاصی بدی
            return f"مرحله {step_number}"
        return f"مرحله {step_number}"

    def get_step_deadline(self, step_number):
        """دریافت مهلت یک مرحله به ساعت"""
        # اول چک کن که زمان اختصاصی برای این مرحله تعریف شده؟
        if self.step_deadlines and str(step_number) in self.step_deadlines:
            return self.step_deadlines[str(step_number)]

        # اگر نه، زمان کل رو بین مراحل تقسیم کن
        if self.deadline_hours > 0:
            max_step = self.get_max_step()
            if max_step > 0:
                return self.deadline_hours / max_step
            return self.deadline_hours
        return 0

    def get_all_steps_info(self):
        """دریافت اطلاعات کامل همه مراحل"""
        steps = {}
        for field in self.fields.filter(is_active=True).order_by('step_number', 'order'):
            step_num = field.step_number
            if step_num not in steps:
                steps[step_num] = {
                    'title': self.get_step_title(step_num),
                    'deadline_hours': self.get_step_deadline(step_num),
                    'fields': [],
                    'count': 0,
                    'is_completed': False,
                    'is_active': False,
                    'was_overdue': False,
                    'duration_hours': 0,
                    'completed_by': None,
                    'completed_at': None,
                }
            steps[step_num]['fields'].append(field)
            steps[step_num]['count'] += 1

        # بروزرسانی اطلاعات از تاریخچه
        history = self.step_history or []
        for item in history:
            step_num = item.get('step_number')
            if step_num in steps:
                steps[step_num]['is_completed'] = item.get('completed_at') is not None
                steps[step_num]['is_active'] = item.get('is_active', False)
                steps[step_num]['was_overdue'] = item.get('was_overdue', False)
                steps[step_num]['duration_hours'] = item.get('duration_hours', 0)
                steps[step_num]['completed_by'] = item.get('completed_by_name')
                steps[step_num]['completed_at'] = item.get('completed_at')

        return steps

    def get_step_status(self, step_number):
        """دریافت وضعیت یک مرحله (not_started, in_progress, completed, overdue)"""
        history = self.step_history or []
        for item in history:
            if item.get('step_number') == step_number:
                if item.get('completed_at'):
                    return 'completed'
                if item.get('was_overdue'):
                    return 'overdue'
                return 'in_progress'
        return 'not_started'

    # ==================== متدهای کنترل جریان ====================

    def start_step(self, step_number):
        """شروع یک مرحله جدید با ثبت در تاریخچه"""
        self.current_step_number = step_number
        self.step_started_at = timezone.now()

        # محاسبه مهلت مرحله بر اساس زمان‌بندی اختصاصی هر مرحله
        step_hours = self.get_step_deadline(step_number)
        if step_hours > 0:
            self.step_deadline = self.step_started_at + timedelta(hours=step_hours)
        else:
            self.step_deadline = None

        self.status = 'in_progress'
        self.save()

        # ثبت شروع مرحله در تاریخچه
        history = self.step_history or []
        existing = next((h for h in history if h.get('step_number') == step_number), None)

        if not existing:
            history.append({
                'step_number': step_number,
                'title': self.get_step_title(step_number),
                'started_at': self.step_started_at.isoformat(),
                'completed_at': None,
                'duration_hours': 0,
                'completed_by': None,
                'completed_by_name': None,
                'was_overdue': False,
                'deadline': self.step_deadline.isoformat() if self.step_deadline else None,
                'is_active': True
            })
            self.step_history = history
            self.save()

    def complete_step(self, step_number, user):
        """تکمیل یک مرحله با ثبت در تاریخچه"""
        now = timezone.now()
        was_overdue = self.step_deadline and now > self.step_deadline

        if was_overdue:
            self.overdue_count += 1

        # بروزرسانی تاریخچه
        history = self.step_history or []
        for item in history:
            if item.get('step_number') == step_number:
                item['completed_at'] = now.isoformat()
                item['completed_by'] = user.id
                item['completed_by_name'] = user.get_full_name() or user.username
                item['was_overdue'] = was_overdue
                item['is_active'] = False
                if item.get('started_at'):
                    start = timezone.datetime.fromisoformat(item['started_at'])
                    duration = (now - start).total_seconds() / 3600
                    item['duration_hours'] = round(duration, 2)
                break
        self.step_history = history

        max_step = self.get_max_step()
        if step_number >= max_step:
            self.status = 'completed'
            self.completed_at = now
        else:
            self.start_step(step_number + 1)

        self.save()
        self.activate_next_step(step_number + 1)

    def activate_next_step(self, next_step_number):
        """فعال‌سازی مرحله بعدی (برای نوتیفیکیشن)"""
        # TODO: پیاده‌سازی نوتیفیکیشن برای کاربران مرحله بعد
        pass

    # ==================== متدهای کمکی ====================

    def get_progress_percentage(self):
        """دریافت درصد پیشرفت کل فرم"""
        total_fields = self.fields.filter(is_active=True).count()
        if total_fields == 0:
            return 0
        filled_fields = self.field_values.count()
        return int((filled_fields / total_fields) * 100)

    def get_remaining_time_display(self):
        """نمایش زمان باقی‌مانده به صورت خوانا"""
        if self.status in ['completed', 'approved', 'rejected', 'canceled']:
            return "تکمیل شده"

        if self.deadline_hours == 0:
            return "بدون محدودیت"

        now = timezone.now()
        deadline = self.get_deadline()
        if not deadline:
            return "بدون محدودیت"

        remaining = deadline - now
        if remaining.total_seconds() <= 0:
            return "تاخیر داشته"

        days = remaining.days
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60

        if days > 0:
            return f"{days} روز و {hours} ساعت"
        elif hours > 0:
            return f"{hours} ساعت و {minutes} دقیقه"
        else:
            return f"{minutes} دقیقه"

    def get_deadline_status(self):
        """دریافت وضعیت مهلت به صورت رنگ‌بندی"""
        if self.status in ['completed', 'approved', 'rejected', 'canceled']:
            return {'class': 'success', 'text': 'تکمیل شده'}

        if self.deadline_hours == 0:
            return {'class': 'info', 'text': 'بدون محدودیت'}

        now = timezone.now()
        deadline = self.get_deadline()
        if not deadline:
            return {'class': 'info', 'text': 'بدون محدودیت'}

        remaining = deadline - now
        if remaining.total_seconds() <= 0:
            return {'class': 'danger', 'text': 'تاخیر داشته'}
        elif remaining.total_seconds() < 86400:  # کمتر از ۱ روز
            return {'class': 'warning', 'text': 'در حال اتمام'}
        else:
            return {'class': 'primary', 'text': 'در زمان'}


class InstanceField(models.Model):
    """
    فیلدهای کپی شده از فرم نمونه (برای هر کپی)
    """
    form_instance = models.ForeignKey(
        FormInstance,
        on_delete=models.CASCADE,
        related_name='fields',
        verbose_name="فرم کپی"
    )
    original_input = models.ForeignKey(
        FormInput,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="فیلد اصلی"
    )

    field_name = models.CharField(max_length=100, verbose_name="نام فیلد")
    field_title = models.CharField(max_length=200, verbose_name="عنوان فیلد")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    step_number = models.PositiveIntegerField(default=1, verbose_name="شماره مرحله")

    is_required = models.BooleanField(default=False, verbose_name="اجباری")
    placeholder = models.CharField(max_length=200, blank=True, null=True, verbose_name="متن راهنما")
    help_text = models.TextField(blank=True, null=True, verbose_name="راهنمای تکمیلی")
    default_value = models.TextField(blank=True, null=True, verbose_name="مقدار پیش‌فرض")

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

    # ============ زمان‌بندی اختصاصی این فیلد در کپی ============
    field_deadline_hours = models.PositiveIntegerField(
        default=0,
        verbose_name="مهلت این فیلد (ساعت)",
        help_text="0 = بدون محدودیت (از مهلت مرحله استفاده می‌شود)"
    )
    # ============================================================

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

    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "فیلد فرم کپی"
        verbose_name_plural = "فیلدهای فرم کپی"
        ordering = ['step_number', 'order']
        unique_together = ['form_instance', 'field_name']

    def __str__(self):
        return f"{self.form_instance.title} - {self.field_title}"

    def is_accessible_by(self, user):
        if self.access_type == 'all':
            return True
        elif self.access_type == 'specific_role':
            user_roles = user.user_roles.filter(is_active=True).values_list('role__id', flat=True)
            allowed_roles = self.allowed_roles.values_list('id', flat=True)
            return bool(set(user_roles) & set(allowed_roles))
        elif self.access_type == 'specific_user':
            return self.allowed_users.filter(id=user.id).exists()
        return False


class InstanceFieldOption(models.Model):
    """
    گزینه‌های فیلدهای کپی شده
    """
    instance_field = models.ForeignKey(
        InstanceField,
        on_delete=models.CASCADE,
        related_name='field_options',
        verbose_name="فیلد کپی"
    )
    key = models.CharField(max_length=100, verbose_name="کلید")
    value = models.CharField(max_length=200, verbose_name="مقدار نمایشی")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "گزینه فیلد کپی"
        verbose_name_plural = "گزینه‌های فیلد کپی"
        ordering = ['order']
        unique_together = ['instance_field', 'key']

    def __str__(self):
        return f"{self.key}: {self.value}"


class FormFieldValue(models.Model):
    """
    مقادیر پر شده برای هر فیلد در فرم کپی
    """
    form_instance = models.ForeignKey(
        FormInstance,
        on_delete=models.CASCADE,
        related_name='field_values',
        verbose_name="فرم کپی"
    )
    instance_field = models.ForeignKey(
        InstanceField,
        on_delete=models.PROTECT,
        related_name='field_values',
        verbose_name="فیلد کپی"
    )

    value = models.TextField(blank=True, null=True, verbose_name="مقدار متنی")
    file_value = models.FileField(upload_to='form_files/%Y/%m/%d/', blank=True, null=True, verbose_name="فایل")
    image_value = models.ImageField(upload_to='form_images/%Y/%m/%d/', blank=True, null=True, verbose_name="تصویر")

    filled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="پر شده توسط"
    )
    filled_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان پر کردن")

    class Meta:
        verbose_name = "مقدار فیلد"
        verbose_name_plural = "مقادیر فیلدها"
        unique_together = ['form_instance', 'instance_field']
        ordering = ['instance_field__step_number', 'instance_field__order']

    def __str__(self):
        return f"{self.instance_field.field_title}: {self.value[:30] if self.value else 'خالی'}"


class UserNotification(models.Model):
    """
    اعلان‌های کاربر
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200, verbose_name="عنوان")
    message = models.TextField(verbose_name="پیام")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده")
    link = models.CharField(max_length=500, blank=True, null=True, verbose_name="لینک")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")

    class Meta:
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title[:30]}"

    def mark_as_read(self):
        """علامت‌گذاری به عنوان خوانده شده"""
        self.is_read = True
        self.save()