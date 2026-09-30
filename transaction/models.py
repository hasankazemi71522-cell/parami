# transaction/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()


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
# 📄 مدل قرارداد (Contract)
# ============================================================

class Contract(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار بررسی مدارک'
        DOCUMENTS_REVIEWED = 'documents_reviewed', 'مدارک بررسی شد'
        CONTRACT_DRAFTED = 'contract_drafted', 'پیش‌نویس قرارداد آماده'
        SIGNED_BY_CUSTOMER = 'signed_by_customer', 'امضای مشتری'
        SIGNED_BY_OTHER = 'signed_by_other', 'امضای طرف دیگر'
        COMPLETED = 'completed', 'تکمیل و نهایی شد'
        CANCELLED = 'cancelled', 'لغو شد'

    # ====== ارتباطات اصلی ======
    process = models.OneToOneField(
        'case_management.CustomerProcess',
        on_delete=models.CASCADE,
        related_name='contract',
        verbose_name="فرآیند مرتبط"
    )
    customer = models.ForeignKey(
        'estate.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contracts',
        verbose_name="مشتری قرارداد"
    )
    property_ref = models.ForeignKey(
        'estate.Property',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contracts',
        verbose_name="ملک قرارداد"
    )
    source_visit = models.ForeignKey(
        'case_management.Visit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_contracts',
        verbose_name="بازدید منجر به قرارداد",
        help_text="بازدیدی که نتیجه آن به تنظیم قرارداد منجر شد"
    )

    # ====== اطلاعات قرارداد ======
    contract_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contracts_handled',
        verbose_name="مسئول قرارداد"
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="وضعیت قرارداد"
    )
    draft_file = models.FileField(
        upload_to='contracts/drafts/',
        null=True,
        blank=True,
        verbose_name="فایل پیش‌نویس قرارداد"
    )
    signed_file = models.FileField(
        upload_to='contracts/signed/',
        null=True,
        blank=True,
        verbose_name="فایل امضاشده قرارداد"
    )
    supporting_documents = models.FileField(
        upload_to='contracts/supporting/',
        null=True,
        blank=True,
        verbose_name="مدارک پشتیبان"
    )
    review_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="یادداشت‌های واحد قرارداد"
    )
    contract_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="یادداشت‌های تکمیلی قرارداد"
    )
    signature_date_customer = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ امضای مشتری"
    )
    signature_date_other = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ امضای طرف دیگر"
    )
    finalization_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ نهایی‌سازی قرارداد"
    )
    contract_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="شماره قرارداد"
    )
    is_confidential = models.BooleanField(
        default=False,
        verbose_name="محرمانه؟"
    )

    CONTRACT_TYPE_CHOICES = [
        ('sale', 'فروش'),
        ('rent', 'اجاره'),
        ('partnership', 'مشارکت در ساخت'),
        ('investment', 'سرمایه‌گذاری'),
    ]
    contract_type = models.CharField(
        max_length=20,
        choices=CONTRACT_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="نوع قرارداد"
    )
    final_amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="مبلغ نهایی قرارداد (تومان)"
    )
    rent_amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="مبلغ اجاره ماهیانه (تومان)"
    )
    mortgage_amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="مبلغ رهن (تومان)"
    )
    rent_end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ پایان اجاره"
    )
    commission_amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="مبلغ کمیسیون (تومان)",
        help_text="اگر خالی باشد، توسط حسابداری محاسبه می‌شود"
    )

    class Meta:
        verbose_name = "قرارداد"
        verbose_name_plural = "قراردادها"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['property_ref']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"قرارداد {self.contract_number or str(self.id)[:8]}"

    def get_customer(self):
        if self.customer:
            return self.customer
        return self.process.customer if self.process else None

    def get_property(self):
        if self.property_ref:
            return self.property_ref
        if self.source_visit and self.source_visit.property_ref:
            return self.source_visit.property_ref
        if self.process:
            last_visit = self.process.visits.filter(property_ref__isnull=False).order_by('-created_at').first()
            if last_visit:
                return last_visit.property_ref
        return None

    def get_source_visit(self):
        if self.source_visit:
            return self.source_visit
        if self.process:
            return self.process.visits.filter(
                meeting_result__isnull=False,
                meeting_status='held'
            ).order_by('-created_at').first()
        return None

    @property
    def customer_name(self):
        customer = self.get_customer()
        return customer.full_name if customer else "---"

    @property
    def property_title(self):
        property_obj = self.get_property()
        return property_obj.title if property_obj else "---"

    @property
    def expert(self):
        return self.process.expert if self.process else None

    @property
    def supervisor(self):
        return self.process.supervisor if self.process else None

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    def get_total_transaction_amount(self):
        """
        محاسبه مبلغ کل معامله
        اولویت: 1. final_amount قرارداد، 2. قیمت ملک، 3. مبلغ رهن
        """
        if self.final_amount:
            return self.final_amount

        property_obj = self.get_property()
        if not property_obj:
            return Decimal(0)

        if property_obj.price:
            return property_obj.price

        if property_obj.mortgage_price:
            return property_obj.mortgage_price

        return Decimal(0)

    def is_ready_for_completion(self):
        if not self.contract_type:
            return False
        if not self.final_amount:
            return False
        if not self.signature_date_customer:
            return False
        if not self.signed_file:
            return False
        return True

    def get_commission_base_amount(self):
        if self.commission_amount:
            return self.commission_amount
        return self.final_amount or Decimal(0)


# ============================================================
# ⚙️ تنظیمات کمیسیون (CommissionSetting)
# ============================================================

class CommissionSetting(models.Model):
    class Meta:
        verbose_name = "تنظیمات کمیسیون"
        verbose_name_plural = "تنظیمات کمیسیون"

    property_register_share = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="سهم ثبت‌کننده فایل (%)"
    )
    customer_register_share = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="سهم ثبت‌کننده مشتری (%)"
    )
    expert_share = models.PositiveIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="سهم کارشناس (%)"
    )
    supervisor_share = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="سهم سرپرست (%)"
    )
    meeting_manager_share = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="سهم مدیر جلسه (%)"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_settings_updated',
        verbose_name="بروزرسانی‌کننده"
    )
    note = models.TextField(null=True, blank=True, verbose_name="یادداشت تغییرات")

    def __str__(self):
        return f"تنظیمات کمیسیون (بروزرسانی: {self.updated_at.strftime('%Y/%m/%d')})"

    @classmethod
    def get_default_settings(cls):
        settings, created = cls.objects.get_or_create(id=1)
        return settings


# ============================================================
# 💰 مدل کمیسیون (Commission)
# ============================================================

class Commission(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار محاسبه'
        CALCULATED = 'calculated', 'محاسبه شد'
        WALLET_TRANSFERRED = 'wallet_transferred', 'واریز به کیف پول'
        PARTIAL_PAID = 'partial_paid', 'تسویه ناقص'
        PAID = 'paid', 'تسویه کامل'
        CANCELLED = 'cancelled', 'لغو شد'

    contract = models.OneToOneField(
        Contract,
        on_delete=models.CASCADE,
        related_name='commission',
        verbose_name="قرارداد"
    )
    accountant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commissions_handled',
        verbose_name="حسابدار مسئول"
    )

    # ====== مبالغ اصلی ======
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="مبلغ کل معامله (تومان)"
    )
    total_commission = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="مبلغ کل کمیسیون (دریافتی از طرفین)"
    )

    # ====== درصدهای سهم (اعداد صحیح) ======
    property_register_share = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="سهم ثبت‌کننده فایل (%)"
    )
    customer_register_share = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="سهم ثبت‌کننده مشتری (%)"
    )
    expert_share = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="سهم کارشناس (%)"
    )
    supervisor_share = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="سهم سرپرست (%)"
    )
    meeting_manager_share = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="سهم مدیر جلسه (%)"
    )

    # ====== مبالغ سهم‌ها (بر اساس total_commission محاسبه می‌شوند) ======
    property_register_amount = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="مبلغ سهم ثبت‌کننده فایل"
    )
    customer_register_amount = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="مبلغ سهم ثبت‌کننده مشتری"
    )
    expert_amount = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="مبلغ سهم کارشناس"
    )
    supervisor_amount = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="مبلغ سهم سرپرست"
    )
    meeting_manager_amount = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="مبلغ سهم مدیر جلسه"
    )

    # ====== جمع سهم‌ها (برای تطابق با total_commission) ======
    total_share_sum = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="جمع سهم‌های پرداختی به اعضا"
    )

    # ====== وضعیت ======
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="وضعیت تسویه"
    )

    # ====== واریز به کیف پول ======
    wallet_transferred_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="تاریخ واریز به کیف پول"
    )
    wallet_transferred_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transfers',
        verbose_name="واریزکننده به کیف پول"
    )

    # ====== تسویه مستقیم ======
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ تسویه کامل")
    payment_receipt = models.FileField(
        upload_to='commissions/receipts/',
        null=True,
        blank=True,
        verbose_name="فایل رسید پرداخت"
    )
    payment_notes = models.TextField(null=True, blank=True, verbose_name="یادداشت‌های پرداخت")

    class Meta:
        verbose_name = "کمیسیون"
        verbose_name_plural = "کمیسیون‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"کمیسیون قرارداد {self.contract.contract_number or str(self.contract.id)[:8]}"

    @property
    def customer(self):
        return self.contract.customer

    # ==========================================================
    # 🔧 متد محاسبه کمیسیون
    # ==========================================================

    def calculate_commission(self, accountant=None):
        """
        محاسبه سهم‌های کمیسیون بر اساس مبلغ کل کمیسیون (total_commission)
        ⚠️ توجه: total_commission تغییر نمی‌کند، فقط سهم‌ها محاسبه می‌شوند
        """
        # اگر مبلغ کل کمیسیون صفر باشد، محاسبه نمی‌شود
        if self.total_commission == 0:
            return None

        # اگر درصدها صفر هستند، از تنظیمات پیش‌فرض بگیر
        if all([
            self.property_register_share == 0,
            self.customer_register_share == 0,
            self.expert_share == 0,
            self.supervisor_share == 0,
            self.meeting_manager_share == 0
        ]):
            settings = CommissionSetting.get_default_settings()
            self.property_register_share = settings.property_register_share
            self.customer_register_share = settings.customer_register_share
            self.expert_share = settings.expert_share
            self.supervisor_share = settings.supervisor_share
            self.meeting_manager_share = settings.meeting_manager_share

        total_comm = self.total_commission  # ✅ مبلغ کل کمیسیون را تغییر نمی‌دهیم
        hundred = Decimal(100)

        # محاسبه سهم‌ها
        self.property_register_amount = (Decimal(self.property_register_share) / hundred) * total_comm
        self.customer_register_amount = (Decimal(self.customer_register_share) / hundred) * total_comm
        self.expert_amount = (Decimal(self.expert_share) / hundred) * total_comm
        self.supervisor_amount = (Decimal(self.supervisor_share) / hundred) * total_comm
        self.meeting_manager_amount = (Decimal(self.meeting_manager_share) / hundred) * total_comm

        # گرد کردن به عدد صحیح
        self.property_register_amount = self.property_register_amount.to_integral_value()
        self.customer_register_amount = self.customer_register_amount.to_integral_value()
        self.expert_amount = self.expert_amount.to_integral_value()
        self.supervisor_amount = self.supervisor_amount.to_integral_value()
        self.meeting_manager_amount = self.meeting_manager_amount.to_integral_value()

        # محاسبه جمع سهم‌ها
        self.total_share_sum = (
            self.property_register_amount +
            self.customer_register_amount +
            self.expert_amount +
            self.supervisor_amount +
            self.meeting_manager_amount
        )

        self.status = self.Status.CALCULATED
        if accountant:
            self.accountant = accountant
        self.save()
        return self.get_shares_dict()

    # ==========================================================
    # 📊 دریافت اطلاعات سهم‌ها به صورت دیکشنری
    # ==========================================================

    def get_shares_dict(self):
        return {
            'property_register': {
                'percentage': int(self.property_register_share),
                'amount': int(self.property_register_amount),
                'recipient': self.contract.property_ref.created_by if self.contract.property_ref else None,
            },
            'customer_register': {
                'percentage': int(self.customer_register_share),
                'amount': int(self.customer_register_amount),
                'recipient': self.contract.customer.created_by if self.contract.customer else None,
            },
            'expert': {
                'percentage': int(self.expert_share),
                'amount': int(self.expert_amount),
                'recipient': self.contract.expert,
            },
            'supervisor': {
                'percentage': int(self.supervisor_share),
                'amount': int(self.supervisor_amount),
                'recipient': self.contract.supervisor,
            },
            'meeting_manager': {
                'percentage': int(self.meeting_manager_share),
                'amount': int(self.meeting_manager_amount),
                'recipient': self._get_meeting_manager(),
            },
            'total_commission': int(self.total_commission),
            'total_amount': int(self.total_amount),
            'total_share_sum': int(self.total_share_sum),
        }

    def _get_meeting_manager(self):
        last_visit = self.contract.process.visits.filter(
            negotiation_manager__isnull=False
        ).order_by('-created_at').first()
        return last_visit.negotiation_manager if last_visit else None

    # ==========================================================
    # 💰 متدهای تسویه
    # ==========================================================

    def mark_as_paid(self, accountant=None, receipt=None, notes=None):
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        if accountant:
            self.accountant = accountant
        if receipt:
            self.payment_receipt = receipt
        if notes:
            self.payment_notes = notes
        self.save()
        return self

    def mark_as_partial_paid(self, notes=None):
        self.status = self.Status.PARTIAL_PAID
        if notes:
            self.payment_notes = notes
        self.save()
        return self


# ============================================================
# 💳 مدل درخواست برداشت از کیف پول (WithdrawalRequest)
# ============================================================

class WithdrawalRequest(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار بررسی'
        APPROVED = 'approved', 'تایید شده'
        PAID = 'paid', 'پرداخت شد'
        REJECTED = 'rejected', 'رد شد'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='withdrawal_requests',
        verbose_name="متقاضی"
    )
    amount = models.PositiveIntegerField(
        verbose_name="مبلغ درخواستی (تومان)"
    )

    bank_name = models.CharField(
        max_length=50,
        verbose_name="نام بانک"
    )
    account_number = models.CharField(
        max_length=30,
        verbose_name="شماره حساب"
    )
    card_number = models.CharField(
        max_length=16,
        verbose_name="شماره کارت"
    )
    sheba_number = models.CharField(
        max_length=50,
        verbose_name="شماره شبا"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="وضعیت"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_withdrawals',
        verbose_name="بررسی‌کننده"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان بررسی"
    )
    payment_receipt = models.FileField(
        upload_to='withdrawals/receipts/',
        null=True,
        blank=True,
        verbose_name="فایل رسید پرداخت"
    )
    note = models.TextField(
        null=True,
        blank=True,
        verbose_name="یادداشت"
    )

    class Meta:
        verbose_name = "درخواست برداشت"
        verbose_name_plural = "درخواست‌های برداشت"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"درخواست {self.user.get_full_name()} - {self.amount:,} تومان"

    def can_approve(self):
        return True

    def approve(self, reviewer=None):
        """
        تایید درخواست برداشت (بدون کسر مجدد، چون قبلاً کسر شده)
        """
        # دیگر نیازی به بررسی موجودی نیست چون قبلاً کسر شده
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()
        return self

    def mark_as_paid(self, receipt=None, note=None):
        self.status = self.Status.PAID
        if receipt:
            self.payment_receipt = receipt
        if note:
            self.note = note
        self.save()
        return self

    # transaction/models.py

    def reject(self, reviewer=None, reason=None):
        """
        رد درخواست (بدون کسر، فقط وضعیت تغییر می‌کند)
        برگشت مبلغ در ویو انجام می‌شود
        """
        self.status = self.Status.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        if reason:
            self.note = reason
        self.save()
        return self


# ============================================================
# 📞 خدمات پس از فروش (AfterSalesService)
# ============================================================

class AfterSalesService(UUIDModel, TimeStampedModel):
    class Satisfaction(models.TextChoices):
        SATISFIED = 'satisfied', 'رضایت‌مند'
        NEUTRAL = 'neutral', 'متوسط'
        UNSATISFIED = 'unsatisfied', 'ناراضی'
        NOT_CONTACTED = 'not_contacted', 'تماس گرفته نشده'

    class ContactStatus(models.TextChoices):
        PENDING = 'pending', 'در انتظار تماس'
        CONTACTED = 'contacted', 'تماس گرفته شد'
        FOLLOW_UP = 'follow_up', 'نیاز به پیگیری مجدد'
        CLOSED = 'closed', 'بسته شد'

    contract = models.OneToOneField(
        Contract,
        on_delete=models.CASCADE,
        related_name='aftersales',
        verbose_name="قرارداد"
    )
    handled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aftersales_handled',
        verbose_name="مسئول پیگیری"
    )
    contact_status = models.CharField(
        max_length=20,
        choices=ContactStatus.choices,
        default=ContactStatus.PENDING,
        verbose_name="وضعیت تماس"
    )
    contact_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ آخرین تماس")
    next_follow_up_date = models.DateTimeField(null=True, blank=True, verbose_name="زمان پیگیری بعدی")

    # ✅ رضایت مشتری
    satisfaction = models.CharField(
        max_length=15,
        choices=Satisfaction.choices,
        default=Satisfaction.NOT_CONTACTED,
        verbose_name="رضایت مشتری"
    )
    # ✅ رضایت مالک فایل
    satisfaction_owner = models.CharField(
        max_length=15,
        choices=Satisfaction.choices,
        default=Satisfaction.NOT_CONTACTED,
        verbose_name="رضایت مالک فایل"
    )

    feedback = models.TextField(null=True, blank=True, verbose_name="بازخورد مشتری")
    feedback_owner = models.TextField(null=True, blank=True, verbose_name="بازخورد مالک فایل")

    new_referral = models.BooleanField(default=False, verbose_name="معرفی مشتری جدید؟")
    referral_details = models.TextField(null=True, blank=True, verbose_name="جزئیات معرفی")
    loyal_customer = models.BooleanField(default=False, verbose_name="مشتری وفادار؟")
    notes = models.TextField(null=True, blank=True, verbose_name="یادداشت‌های تکمیلی")
    is_closed = models.BooleanField(default=False, verbose_name="پرونده بسته شد؟")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ بسته شدن")

    class Meta:
        verbose_name = "خدمات پس از فروش"
        verbose_name_plural = "خدمات پس از فروش"
        ordering = ['-created_at']

    def __str__(self):
        return f"خدمات پس از فروش - {self.contract.customer.full_name}"

    @property
    def customer(self):
        return self.contract.customer

    @property
    def property_owner(self):
        """دریافت مالک فایل از قرارداد"""
        prop = self.contract.get_property()
        return prop.owner if prop and prop.owner else None

    @property
    def is_follow_up_due(self):
        if self.next_follow_up_date and self.contact_status != self.ContactStatus.CLOSED:
            return timezone.now() >= self.next_follow_up_date
        return False

    def record_contact(self, satisfaction=None, satisfaction_owner=None, feedback=None, feedback_owner=None, handled_by=None):
        self.contact_status = self.ContactStatus.CONTACTED
        self.contact_date = timezone.now()
        if satisfaction is not None:
            self.satisfaction = satisfaction
        if satisfaction_owner is not None:
            self.satisfaction_owner = satisfaction_owner
        if feedback is not None:
            self.feedback = feedback
        if feedback_owner is not None:
            self.feedback_owner = feedback_owner
        if handled_by:
            self.handled_by = handled_by
        self.save()
        return self

    def schedule_follow_up(self, follow_up_date):
        self.contact_status = self.ContactStatus.FOLLOW_UP
        self.next_follow_up_date = follow_up_date
        self.save()
        return self

    def mark_as_closed(self):
        self.is_closed = True
        self.closed_at = timezone.now()
        self.contact_status = self.ContactStatus.CLOSED
        self.save()
        return self