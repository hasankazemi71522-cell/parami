# case_management/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from datetime import timedelta
import uuid

from estate.models import Customer, Property  # ✅ برای سیگنال‌ها

User = get_user_model()


# ============================================================
# 📌 مدل‌های پایه (مشترک با پروژه)
# ============================================================

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="شناسه یکتا"
    )

    class Meta:
        abstract = True


# ============================================================
# 📊 مدل اصلی فرآیند (CustomerProcess)
# ============================================================

class CustomerProcess(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        ASSIGNED = 'assigned', 'اختصاص داده شده'
        CONTACT_PENDING = 'contact_pending', 'نیاز به تماس'
        CONTACTED = 'contacted', 'تماس گرفته شده'
        INTRO_PENDING = 'intro_pending', 'در انتظار معرفی'
        INTRODUCED = 'introduced', 'معرفی انجام شد'
        VISIT_PENDING = 'visit_pending', 'در انتظار درخواست بازدید'
        VISIT_SCHEDULED = 'visit_scheduled', 'بازدید برنامه‌ریزی شد'
        VISIT_DONE = 'visit_done', 'بازدید انجام شد'
        NEGOTIATION = 'negotiation', 'جلسه مذاکره'
        CONTRACT_PENDING = 'contract_pending', 'در انتظار تنظیم قرارداد'
        SENT_TO_ACCOUNTING = 'sent_to_accounting', 'ارسال به حسابداری'   # ✅ جدید
        CLOSED_SUCCESS = 'closed_success', 'بسته شده (موفق)'
        CLOSED_FAIL = 'closed_fail', 'بسته شده (ناموفق)'
        CANCELLED = 'cancelled', 'لغو شده توسط مشتری'
        CONVERTED = 'converted', 'تبدیل به قرارداد'

    class CloseReason(models.TextChoices):
        CONTRACT = 'contract', 'تبدیل به قرارداد'
        CANCELLED_BY_CUSTOMER = 'cancelled_by_customer', 'کنسل توسط مشتری'
        CANCELLED_BY_EXPERT = 'cancelled_by_expert', 'کنسل توسط کارشناس'
        NOT_INTERESTED = 'not_interested', 'مشتری علاقه‌ای نداشت'
        PRICE_MISMATCH = 'price_mismatch', 'عدم تطابق قیمت'
        OTHER = 'other', 'سایر'

    # ====== ارتباطات ======
    customer = models.ForeignKey(
        'estate.Customer',
        on_delete=models.CASCADE,
        related_name='processes',
        verbose_name="مشتری"
    )
    expert = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='processes_as_expert',
        verbose_name="کارشناس"
    )
    supervisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='processes_as_supervisor',
        verbose_name="سرپرست"
    )

    # ====== وضعیت و زمان‌ها ======
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ASSIGNED,
        verbose_name="وضعیت"
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان اختصاص")

    # تاریخچه زمان‌های کلیدی
    contact_made_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تماس")
    introduction_completed_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تکمیل معرفی")

    # مهلت‌ها (به صورت خودکار محاسبه می‌شوند)
    contact_deadline = models.DateTimeField(null=True, blank=True, verbose_name="مهلت تماس (۲۴ ساعت)")
    intro_deadline = models.DateTimeField(null=True, blank=True, verbose_name="مهلت معرفی (۲۴ ساعت پس از تماس)")
    visit_result_deadline = models.DateTimeField(null=True, blank=True, verbose_name="مهلت ثبت نتیجه بازدید (۲۴ ساعت)")

    # وضعیت گزارش تخلف به سرپرست (برای جلوگیری از ارسال مکرر)
    missed_contact_reported = models.BooleanField(default=False)
    missed_intro_reported = models.BooleanField(default=False)
    missed_visit_result_reported = models.BooleanField(default=False)

    # ====== نتیجه نهایی ======
    final_result = models.TextField(null=True, blank=True, verbose_name="نتیجه نهایی")
    is_successful = models.BooleanField(default=False, verbose_name="موفقیت آمیز؟")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان بسته شدن")

    # ====== فیلدهای جدید برای بسته شدن فرآیند ======
    close_reason = models.CharField(
        max_length=30,
        choices=CloseReason.choices,
        null=True,
        blank=True,
        verbose_name="دلیل بسته شدن"
    )
    close_note = models.TextField(
        null=True,
        blank=True,
        verbose_name="توضیحات بسته شدن"
    )
    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_processes',
        verbose_name="بسته کننده"
    )

    class Meta:
        verbose_name = "فرآیند مشتری"
        verbose_name_plural = "فرآیندهای مشتری"
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['status', 'expert']),
            models.Index(fields=['status', 'supervisor']),
            models.Index(fields=['contact_deadline']),
            models.Index(fields=['intro_deadline']),
        ]

    def __str__(self):
        return f"{self.customer.full_name} - {self.expert.get_full_name()} ({self.get_status_display()})"

    def set_contact_deadline(self):
        """تنظیم مهلت تماس (۲۴ ساعت از زمان انتساب)"""
        self.contact_deadline = self.assigned_at + timedelta(hours=24)

    def set_intro_deadline(self):
        """تنظیم مهلت معرفی (۲۴ ساعت از زمان تماس)"""
        if self.contact_made_at:
            self.intro_deadline = self.contact_made_at + timedelta(hours=24)

    def set_visit_result_deadline(self, visit_done_at):
        """تنظیم مهلت ثبت نتیجه بازدید (۲۴ ساعت پس از بازدید)"""
        if visit_done_at:
            self.visit_result_deadline = visit_done_at + timedelta(hours=24)

    @property
    def is_contact_deadline_passed(self):
        if self.contact_deadline and not self.contact_made_at:
            return timezone.now() > self.contact_deadline
        return False

    @property
    def is_intro_deadline_passed(self):
        if self.intro_deadline and not self.introduction_completed_at:
            return timezone.now() > self.intro_deadline
        return False

    @property
    def is_visit_result_deadline_passed(self):
        if self.visit_result_deadline:
            last_visit = self.visits.filter(status=Visit.Status.DONE).first()
            if last_visit and not last_visit.visit_result:
                return timezone.now() > self.visit_result_deadline
        return False

    # ==========================================================
    # ✅ متدهای کمکی جدید برای بررسی وضعیت
    # ==========================================================

    def is_in_contract_phase(self):
        """بررسی اینکه فرآیند در مرحله تنظیم قرارداد است"""
        return self.status == self.Status.CONTRACT_PENDING

    def is_sent_to_accounting(self):
        """بررسی اینکه فرآیند به حسابداری ارسال شده است"""
        return self.status == self.Status.SENT_TO_ACCOUNTING

    def is_closed(self):
        """بررسی اینکه فرآیند بسته شده است (هر نوع بسته شدن)"""
        return self.status in [
            self.Status.CLOSED_SUCCESS,
            self.Status.CLOSED_FAIL,
            self.Status.CANCELLED,
            self.Status.CONVERTED,
            self.Status.SENT_TO_ACCOUNTING,
        ]


# ============================================================
# 📝 گزارش معرفی (IntroductionReport)
# ============================================================

class IntroductionReport(UUIDModel, TimeStampedModel):
    class Result(models.TextChoices):
        SUCCESS = 'success', 'موفق (مشتری علاقه‌مند شد)'
        FAIL = 'fail', 'ناموفق (مشتری علاقه‌ای نداشت)'
        PENDING = 'pending', 'در انتظار پاسخ مشتری'

    process = models.ForeignKey(
        CustomerProcess,
        on_delete=models.CASCADE,
        related_name='introduction_reports',
        verbose_name="فرآیند"
    )
    property_ref = models.ForeignKey(
        'estate.Property',
        on_delete=models.CASCADE,
        related_name='introduction_reports',
        verbose_name="ملک معرفی شده"
    )
    result = models.CharField(
        max_length=10,
        choices=Result.choices,
        default=Result.PENDING,
        verbose_name="نتیجه"
    )
    expert_note = models.TextField(
        verbose_name="توضیح کارشناس",
        blank=True,
        help_text="توضیح دهید چرا مشتری علاقه‌مند شد یا نشد"
    )
    follow_up_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان پیگیری بعدی",
        help_text="اگر نیاز به تماس مجدد است، زمان آن را مشخص کنید"
    )

    class Meta:
        verbose_name = "گزارش معرفی"
        verbose_name_plural = "گزارش‌های معرفی"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['follow_up_date']),
            models.Index(fields=['process', 'property_ref']),
        ]

    def __str__(self):
        return f"{self.process.customer.full_name} -> {self.property_ref.title} ({self.get_result_display()})"

    @property
    def is_follow_up_due(self):
        if self.follow_up_date:
            return timezone.now() >= self.follow_up_date
        return False


# ============================================================
# 🏠 بازدید (Visit)
# ============================================================

class Visit(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = 'requested', 'درخواست شده'
        SCHEDULED = 'scheduled', 'برنامه‌ریزی شده'
        CONFIRMED = 'confirmed', 'تأیید نهایی (روز بازدید)'
        DONE = 'done', 'انجام شد'
        CANCELLED = 'cancelled', 'لغو شد'
        POSTPONED = 'postponed', 'به تعویق افتاد'

    process = models.ForeignKey(
        CustomerProcess,
        on_delete=models.CASCADE,
        related_name='visits',
        verbose_name="فرآیند"
    )
    property_ref = models.ForeignKey(
        'estate.Property',
        on_delete=models.CASCADE,
        related_name='visits',
        verbose_name="ملک مورد بازدید"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
        verbose_name="وضعیت"
    )
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان درخواست")
    scheduled_time = models.DateTimeField(null=True, blank=True, verbose_name="زمان برنامه‌ریزی شده")
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تأیید نهایی")
    done_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان انجام بازدید")

    # نتیجه بازدید
    visit_result = models.TextField(null=True, blank=True, verbose_name="نتیجه بازدید")
    negotiation_requested = models.BooleanField(
        default=False,
        verbose_name="آیا به جلسه مذاکره رسید؟"
    )
    negotiation_scheduled = models.BooleanField(
        default=False,
        verbose_name="آیا جلسه مذاکره هماهنگ شد؟"
    )

    # ====== فیلدهای مدیریت جلسه ======
    negotiation_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_visits',
        verbose_name="مدیر جلسه مذاکره",
        help_text="کاربری با نقش meetingchair که مسئول برگزاری جلسه مذاکره است"
    )

    meeting_result = models.TextField(
        null=True,
        blank=True,
        verbose_name="نتیجه جلسه مذاکره",
        help_text="نتیجه جلسه مذاکره که توسط مدیر جلسه ثبت می‌شود"
    )

    meeting_note = models.TextField(
        null=True,
        blank=True,
        verbose_name="یادداشت جلسه",
        help_text="یادداشت‌های تکمیلی جلسه"
    )

    meeting_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'در انتظار برگزاری'),
            ('held', 'برگزار شد'),
            ('cancelled', 'لغو شد'),
            ('postponed', 'به تعویق افتاد'),
        ],
        default='pending',
        verbose_name="وضعیت برگزاری جلسه"
    )

    meeting_held_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان برگزاری جلسه"
    )

    meeting_result_confirmed = models.BooleanField(
        default=False,
        verbose_name="نتیجه جلسه تایید شده؟"
    )

    # یادآوری ارسال شد؟
    reminder_sent = models.BooleanField(default=False, verbose_name="یادآوری ارسال شد")

    class Meta:
        verbose_name = "بازدید"
        verbose_name_plural = "بازدیدها"
        ordering = ['-scheduled_time', '-created_at']

    def __str__(self):
        return f"بازدید {self.property_ref.title} - {self.process.customer.full_name} ({self.get_status_display()})"

    @property
    def is_today(self):
        if self.scheduled_time:
            return self.scheduled_time.date() == timezone.now().date()
        return False


# ============================================================
# 📜 لاگ فعالیت‌ها (ProcessLog)
# ============================================================

class ProcessLog(UUIDModel, TimeStampedModel):
    class ActionType(models.TextChoices):
        STATUS_CHANGE = 'status_change', 'تغییر وضعیت'
        CONTACT_MADE = 'contact_made', 'تماس گرفته شد'
        INTRO_REPORTED = 'intro_reported', 'گزارش معرفی ثبت شد'
        VISIT_REQUESTED = 'visit_requested', 'درخواست بازدید'
        VISIT_SCHEDULED = 'visit_scheduled', 'برنامه‌ریزی بازدید'
        VISIT_DONE = 'visit_done', 'بازدید انجام شد'
        VISIT_CANCELLED = 'visit_cancelled', 'لغو بازدید'
        NEGOTIATION_REQUESTED = 'negotiation_requested', 'درخواست جلسه مذاکره'
        PROCESS_CLOSED = 'process_closed', 'بسته شدن فرآیند'
        DEADLINE_WARNING = 'deadline_warning', 'اخطار مهلت'
        WITHDRAWAL_REQUEST = 'withdrawal_request',

    process = models.ForeignKey(
        CustomerProcess,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="فرآیند",
        null=True,
        blank=True
    )
    action = models.CharField(
        max_length=30,
        choices=ActionType.choices,
        verbose_name="نوع اقدام"
    )
    description = models.TextField(verbose_name="توضیحات")
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='process_logs',
        verbose_name="انجام‌دهنده"
    )
    old_value = models.CharField(max_length=100, null=True, blank=True)
    new_value = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = "لاگ فعالیت"
        verbose_name_plural = "لاگ‌های فعالیت"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} - {self.process.customer.full_name}"


# ============================================================
# 🚨 اخطار به سرپرست (SupervisorAlert)
# ============================================================

class SupervisorAlert(UUIDModel, TimeStampedModel):
    class Type(models.TextChoices):
        MISSED_CONTACT = 'missed_contact', 'عدم تماس در مهلت مقرر'
        MISSED_INTRODUCTION = 'missed_introduction', 'عدم معرفی کامل در مهلت'
        MISSED_VISIT_RESULT = 'missed_visit_result', 'عدم ثبت نتیجه بازدید'
        VISIT_REMINDER = 'visit_reminder', 'یادآوری بازدید امروز'

    process = models.ForeignKey(
        CustomerProcess,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name="فرآیند مرتبط"
    )
    alert_type = models.CharField(
        max_length=30,
        choices=Type.choices,
        verbose_name="نوع اخطار"
    )
    message = models.TextField(verbose_name="متن اخطار")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده؟")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان خواندن")

    class Meta:
        verbose_name = "اخطار به سرپرست"
        verbose_name_plural = "اخطارهای سرپرست"
        ordering = ['-created_at', 'is_read']

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.process.customer.full_name}"


# ============================================================
# 📝 نت فرآیند (ProcessNote)
# ============================================================

class ProcessNote(models.Model):
    class NoteType(models.TextChoices):
        CONTACT_REPORT = 'contact_report', 'گزارش تماس'
        GENERAL = 'general', 'یادداشت عمومی'
        IMPORTANT = 'important', 'نکته مهم'

    class Target(models.TextChoices):
        PUBLIC = 'public', 'عمومی'
        SUPERVISOR = 'supervisor', 'سرپرست'
        CALLCENTER = 'callcenter', 'کال سنتر'

    process = models.ForeignKey(
        CustomerProcess,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name="فرآیند"
    )
    note_type = models.CharField(
        max_length=20,
        choices=NoteType.choices,
        default=NoteType.GENERAL,
        verbose_name="نوع نت"
    )
    target = models.CharField(
        max_length=20,
        choices=Target.choices,
        default=Target.PUBLIC,
        verbose_name="مخاطب"
    )
    content = models.TextField(verbose_name="متن نت")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='process_notes',
        verbose_name="نویسنده"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")

    is_confirmed = models.BooleanField(default=False, verbose_name="تایید شده توسط کال سنتر")
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تایید")
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_notes',
        verbose_name="تایید کننده"
    )

    class Meta:
        verbose_name = "نت فرآیند"
        verbose_name_plural = "نت‌های فرآیند"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_note_type_display()} - {self.process.customer.full_name} - {self.created_at.strftime('%Y/%m/%d %H:%M')}"

    def confirm(self, user):
        self.is_confirmed = True
        self.confirmed_at = timezone.now()
        self.confirmed_by = user
        self.save()


# ============================================================
# 🔔 سیگنال‌ها
# ============================================================

@receiver(pre_save, sender=CustomerProcess)
def process_pre_save_handler(sender, instance, **kwargs):
    if not instance.id and not instance.contact_deadline:
        instance.set_contact_deadline()

    if instance.status == CustomerProcess.Status.CONTACTED and not instance.intro_deadline:
        if not instance.contact_made_at:
            instance.contact_made_at = timezone.now()
        instance.set_intro_deadline()


@receiver(post_save, sender=CustomerProcess)
def process_post_save_handler(sender, created, instance, **kwargs):
    if created:
        ProcessLog.objects.create(
            process=instance,
            action=ProcessLog.ActionType.STATUS_CHANGE,
            description=f"فرآیند با وضعیت {instance.get_status_display()} ایجاد شد",
            performed_by=instance.expert,
            new_value=instance.status
        )


@receiver(post_save, sender=Visit)
def visit_post_save_handler(sender, created, instance, **kwargs):
    if created:
        ProcessLog.objects.create(
            process=instance.process,
            action=ProcessLog.ActionType.VISIT_REQUESTED,
            description=f"درخواست بازدید برای {instance.property_ref.title} ثبت شد",
            performed_by=instance.process.expert,
        )

    if instance.status == Visit.Status.DONE and not instance.done_at:
        instance.done_at = timezone.now()
        instance.save(update_fields=['done_at'])
        instance.process.set_visit_result_deadline(instance.done_at)
        instance.process.save(update_fields=['visit_result_deadline'])
        ProcessLog.objects.create(
            process=instance.process,
            action=ProcessLog.ActionType.VISIT_DONE,
            description=f"بازدید {instance.property_ref.title} انجام شد",
            performed_by=instance.process.expert,
        )

    if instance.status == Visit.Status.CANCELLED:
        ProcessLog.objects.create(
            process=instance.process,
            action=ProcessLog.ActionType.VISIT_CANCELLED,
            description=f"بازدید {instance.property_ref.title} لغو شد",
            performed_by=instance.process.expert,
        )


@receiver(post_save, sender=IntroductionReport)
def intro_report_post_save_handler(sender, created, instance, **kwargs):
    if created:
        ProcessLog.objects.create(
            process=instance.process,
            action=ProcessLog.ActionType.INTRO_REPORTED,
            description=f"گزارش معرفی برای {instance.property_ref.title} ثبت شد: {instance.get_result_display()}",
            performed_by=instance.process.expert,
        )


# ============================================================
# 🔥 سیگنال‌های جدید برای مدیریت قفل شدن مشتری و فایل
# ============================================================

@receiver(post_save, sender=CustomerProcess)
def lock_customer_and_property_on_contract_pending(sender, instance, created, **kwargs):
    """
    وقتی وضعیت فرآیند به CONTRACT_PENDING تغییر کرد، مشتری و فایل قفل می‌شوند
    """
    if instance.status == CustomerProcess.Status.CONTRACT_PENDING:
        # قفل کردن مشتری
        if instance.customer and instance.customer.status != Customer.Status.IN_MEETING:
            instance.customer.status = Customer.Status.IN_MEETING
            instance.customer.save(update_fields=['status'])

        # قفل کردن فایل مرتبط با آخرین بازدید
        last_visit = instance.visits.filter(property_ref__isnull=False).order_by('-created_at').first()
        if last_visit and last_visit.property_ref:
            property_obj = last_visit.property_ref
            if property_obj.status != Property.Status.IN_MEETING:
                property_obj.status = Property.Status.IN_MEETING
                property_obj.save(update_fields=['status'])


@receiver(post_save, sender=CustomerProcess)
def unlock_customer_and_property_on_contract_cancel(sender, instance, created, **kwargs):
    """
    وقتی فرآیند از CONTRACT_PENDING به وضعیت دیگه‌ای تغییر کرد، مشتری و فایل آزاد می‌شوند
    (به جز SENT_TO_ACCOUNTING که بسته محسوب می‌شود)
    """
    if instance.status not in [CustomerProcess.Status.CONTRACT_PENDING, CustomerProcess.Status.SENT_TO_ACCOUNTING]:
        # اگر مشتری در وضعیت IN_MEETING بود، به CONFIRMED برگردون
        if instance.customer and instance.customer.status == Customer.Status.IN_MEETING:
            instance.customer.status = Customer.Status.CONFIRMED
            instance.customer.save(update_fields=['status'])

        # فایل مرتبط رو هم آزاد کن
        last_visit = instance.visits.filter(property_ref__isnull=False).order_by('-created_at').first()
        if last_visit and last_visit.property_ref:
            property_obj = last_visit.property_ref
            if property_obj.status == Property.Status.IN_MEETING:
                property_obj.status = Property.Status.CONFIRMED
                property_obj.save(update_fields=['status'])