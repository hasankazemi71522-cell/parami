# transaction/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from case_management.models import CustomerProcess, ProcessLog
from estate.models import Customer, Property
from .models import Contract, Commission, AfterSalesService, CommissionSetting


# ============================================================
# 🔔 سیگنال تکمیل قرارداد (اصلاح شده - فقط total_commission ذخیره می‌شود)
# ============================================================

@receiver(post_save, sender=Contract)
def handle_contract_completion(sender, instance, created, **kwargs):
    """
    وقتی قرارداد تکمیل شد (COMPLETED):
    1. تغییر وضعیت فرآیند به SENT_TO_ACCOUNTING
    2. به‌روزرسانی وضعیت مشتری و ملک به 'CONTRACT'
    3. ایجاد کمیسیون با total_commission مشخص، ولی سهم‌ها صفر و وضعیت PENDING
    """
    if instance.status == Contract.Status.COMPLETED:
        process = instance.process

        # ====== 1. تغییر وضعیت فرآیند ======
        process.status = CustomerProcess.Status.SENT_TO_ACCOUNTING
        process.final_result = "قرارداد نهایی و امضا شد - ارسال به حسابداری"
        process.closed_at = timezone.now()
        process.is_successful = True
        process.closed_by = instance.contract_officer
        process.save()

        ProcessLog.objects.create(
            process=process,
            action=ProcessLog.ActionType.PROCESS_CLOSED,
            description=f"فرآیند پس از تکمیل قرارداد توسط {instance.contract_officer.get_full_name()} به حسابداری ارسال شد",
            performed_by=instance.contract_officer,
            new_value=CustomerProcess.Status.SENT_TO_ACCOUNTING
        )

        # ====== 2. به‌روزرسانی وضعیت مشتری و ملک ======
        if instance.customer:
            instance.customer.status = Customer.Status.CONTRACT
            instance.customer.save(update_fields=['status'])

        if instance.property_ref:
            instance.property_ref.status = Property.Status.CONTRACT
            instance.property_ref.save(update_fields=['status'])

        # ====== 3. ایجاد کمیسیون (فقط total_commission، بدون محاسبه سهم‌ها) ======
        if not hasattr(instance, 'commission'):
            settings = CommissionSetting.get_default_settings()

            # مبلغ کل معامله
            transaction_amount = instance.get_total_transaction_amount()

            # ====== تعیین مبلغ کل کمیسیون ======
            if instance.commission_amount:
                # اگر کاربر مبلغ کمیسیون را در فرم وارد کرده باشد
                total_commission = instance.commission_amount
            else:
                # در غیر این صورت از درصدهای پیش‌فرض محاسبه کن
                total_percent = (
                    settings.property_register_share +
                    settings.customer_register_share +
                    settings.expert_share +
                    settings.supervisor_share +
                    settings.meeting_manager_share
                )
                total_commission = int((total_percent / 100) * float(transaction_amount))

            # ====== ایجاد رکورد کمیسیون ======
            Commission.objects.create(
                contract=instance,
                total_amount=transaction_amount,          # مبلغ کل معامله
                total_commission=total_commission,        # مبلغ کل کمیسیون
                property_register_share=settings.property_register_share,
                customer_register_share=settings.customer_register_share,
                expert_share=settings.expert_share,
                supervisor_share=settings.supervisor_share,
                meeting_manager_share=settings.meeting_manager_share,
                # سهم‌ها (property_register_amount و ...) صفر می‌مانند (پیش‌فرض مدل)
                status=Commission.Status.PENDING,         # ✅ در انتظار محاسبه توسط حسابدار
                # accountant را خالی می‌گذاریم
            )


# ============================================================
# 🔔 سیگنال لغو قرارداد (بدون تغییر)
# ============================================================

@receiver(post_save, sender=Contract)
def handle_contract_cancellation(sender, instance, created, **kwargs):
    if instance.status == Contract.Status.CANCELLED:
        process = instance.process

        process.status = CustomerProcess.Status.NEGOTIATION
        process.final_result = "قرارداد منعقد نشد - لغو توسط واحد قرارداد - بازگشت به مرحله مذاکره"
        process.closed_at = None
        process.is_successful = False
        process.closed_by = None
        process.close_reason = None
        process.close_note = None
        process.save()

        ProcessLog.objects.create(
            process=process,
            action=ProcessLog.ActionType.STATUS_CHANGE,
            description=f"فرآیند پس از لغو قرارداد توسط {instance.contract_officer.get_full_name()} به مرحله مذاکره بازگشت",
            performed_by=instance.contract_officer,
            new_value=CustomerProcess.Status.NEGOTIATION
        )

        if instance.customer and instance.customer.status == Customer.Status.IN_MEETING:
            instance.customer.status = Customer.Status.CONFIRMED
            instance.customer.save(update_fields=['status'])

        if instance.property_ref and instance.property_ref.status == Property.Status.IN_MEETING:
            instance.property_ref.status = Property.Status.CONFIRMED
            instance.property_ref.save(update_fields=['status'])


# ============================================================
# 🔔 سیگنال ایجاد قرارداد (بدون تغییر)
# ============================================================

@receiver(post_save, sender=CustomerProcess)
def create_contract_when_contract_pending(sender, instance, created, **kwargs):
    if not created and instance.status == CustomerProcess.Status.CONTRACT_PENDING:
        if not hasattr(instance, 'contract'):
            source_visit = instance.visits.filter(
                meeting_result__isnull=False,
                meeting_status='held'
            ).order_by('-created_at').first()

            if not source_visit:
                source_visit = instance.visits.order_by('-created_at').first()

            Contract.objects.create(
                process=instance,
                customer=instance.customer,
                property_ref=source_visit.property_ref if source_visit else None,
                source_visit=source_visit,
                status=Contract.Status.PENDING
            )


# ============================================================
# 🔔 سیگنال ایجاد خدمات پس از فروش (بدون تغییر)
# ============================================================

@receiver(post_save, sender=Commission)
def create_aftersales_after_commission_paid(sender, instance, created, **kwargs):
    if instance.status in [Commission.Status.PAID, Commission.Status.WALLET_TRANSFERRED]:
        if not hasattr(instance.contract, 'aftersales'):
            AfterSalesService.objects.create(
                contract=instance.contract,
                contact_status=AfterSalesService.ContactStatus.PENDING
            )