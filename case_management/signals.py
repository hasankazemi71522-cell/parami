# case_management/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from .models import CustomerProcess, Visit, IntroductionReport, ProcessLog
from estate.models import Match, Customer, Property


# ============================================================
# 🔔 سیگنال‌های مربوط به CustomerProcess
# ============================================================

@receiver(pre_save, sender=CustomerProcess)
def process_pre_save_handler(sender, instance, **kwargs):
    """
    تنظیم خودکار مهلت‌ها:
    - مهلت تماس (۲۴ ساعت از زمان انتساب) در اولین ذخیره
    - مهلت معرفی (۲۴ ساعت از زمان تماس) در صورت تغییر وضعیت به CONTACTED
    """
    # اگر رکورد جدید است و مهلت تماس تنظیم نشده
    if not instance.id and not instance.contact_deadline:
        instance.set_contact_deadline()

    # اگر وضعیت به CONTACTED تغییر کرد و مهلت معرفی تنظیم نشده است
    if instance.status == CustomerProcess.Status.CONTACTED and not instance.intro_deadline:
        if not instance.contact_made_at:
            instance.contact_made_at = timezone.now()
        instance.set_intro_deadline()


@receiver(post_save, sender=CustomerProcess)
def process_post_save_handler(sender, created, instance, **kwargs):
    """
    ثبت لاگ برای ایجاد و تغییر وضعیت‌های مهم
    """
    if created:
        ProcessLog.objects.create(
            process=instance,
            action=ProcessLog.ActionType.STATUS_CHANGE,
            description=f"فرآیند با وضعیت {instance.get_status_display()} ایجاد شد",
            performed_by=instance.expert,
            new_value=instance.status
        )

    # ✅ اصلاح: اضافه کردن وضعیت‌های CONVERTED و SENT_TO_ACCOUNTING
    if instance.status in [
        CustomerProcess.Status.CLOSED_SUCCESS,
        CustomerProcess.Status.CLOSED_FAIL,
        CustomerProcess.Status.CANCELLED,
        CustomerProcess.Status.CONVERTED,           # ✅ جدید
        CustomerProcess.Status.SENT_TO_ACCOUNTING,  # ✅ جدید
    ]:
        if not instance.closed_at:
            instance.closed_at = timezone.now()
            instance.save(update_fields=['closed_at'])

        ProcessLog.objects.create(
            process=instance,
            action=ProcessLog.ActionType.PROCESS_CLOSED,
            description=f"فرآیند با وضعیت {instance.get_status_display()} بسته شد",
            performed_by=instance.expert,
            new_value=instance.status
        )


# ============================================================
# 🔔 سیگنال‌های مربوط به Visit
# ============================================================

@receiver(post_save, sender=Visit)
def visit_post_save_handler(sender, created, instance, **kwargs):
    """
    ثبت لاگ و تنظیم مهلت نتیجه بازدید
    """
    if created:
        ProcessLog.objects.create(
            process=instance.process,
            action=ProcessLog.ActionType.VISIT_REQUESTED,
            description=f"درخواست بازدید برای {instance.property_ref.title} ثبت شد",
            performed_by=instance.process.expert,
        )

    # اگر وضعیت به SCHEDULED تغییر کرد
    if instance.status == Visit.Status.SCHEDULED and instance.scheduled_time:
        ProcessLog.objects.create(
            process=instance.process,
            action=ProcessLog.ActionType.VISIT_SCHEDULED,
            description=f"زمان بازدید {instance.property_ref.title} برای {instance.scheduled_time.strftime('%Y/%m/%d %H:%M')} برنامه‌ریزی شد",
            performed_by=instance.process.expert,
        )

        # ✅ اصلاح: تغییر وضعیت فرآیند به VISIT_SCHEDULED اگر در وضعیت مناسب است
        if instance.process.status in [
            CustomerProcess.Status.VISIT_PENDING,
            CustomerProcess.Status.INTRODUCED,
            CustomerProcess.Status.NEGOTIATION,  # ✅ اضافه شد
        ]:
            instance.process.status = CustomerProcess.Status.VISIT_SCHEDULED
            instance.process.save(update_fields=['status'])

    # اگر وضعیت به DONE تغییر کرد
    if instance.status == Visit.Status.DONE and not instance.done_at:
        instance.done_at = timezone.now()
        instance.save(update_fields=['done_at'])

        # تنظیم مهلت ثبت نتیجه بازدید در فرآیند اصلی
        instance.process.set_visit_result_deadline(instance.done_at)
        instance.process.save(update_fields=['visit_result_deadline'])

        ProcessLog.objects.create(
            process=instance.process,
            action=ProcessLog.ActionType.VISIT_DONE,
            description=f"بازدید {instance.property_ref.title} انجام شد",
            performed_by=instance.process.expert,
        )

    # اگر کنسل شد
    if instance.status == Visit.Status.CANCELLED:
        ProcessLog.objects.create(
            process=instance.process,
            action=ProcessLog.ActionType.VISIT_CANCELLED,
            description=f"بازدید {instance.property_ref.title} لغو شد",
            performed_by=instance.process.expert,
        )


# ============================================================
# 🔔 سیگنال‌های مربوط به IntroductionReport
# ============================================================

@receiver(post_save, sender=IntroductionReport)
def intro_report_post_save_handler(sender, created, instance, **kwargs):
    """
    ثبت لاگ و بررسی تکمیل شدن همه گزارش‌های معرفی
    """
    if created:
        ProcessLog.objects.create(
            process=instance.process,
            action=ProcessLog.ActionType.INTRO_REPORTED,
            description=f"گزارش معرفی برای {instance.property_ref.title} ثبت شد: {instance.get_result_display()}",
            performed_by=instance.process.expert,
        )

    # بررسی اینکه آیا تمام فایل‌های تطابق یافته برای این فرآیند گزارش شده‌اند؟
    total_matches = Match.objects.filter(
        customer=instance.process.customer,
        match_score__gte=50
    ).count()

    reported_count = instance.process.introduction_reports.count()

    if reported_count >= total_matches and total_matches > 0:
        # ✅ اصلاح: بررسی وضعیت مناسب برای تغییر به INTRODUCED
        # اگر وضعیت فعلی CONTACTED یا INTRO_PENDING باشد، تغییر وضعیت بده
        if instance.process.status in [
            CustomerProcess.Status.CONTACTED,
            CustomerProcess.Status.INTRO_PENDING,
        ]:
            instance.process.status = CustomerProcess.Status.INTRODUCED
            instance.process.introduction_completed_at = timezone.now()
            instance.process.save(update_fields=['status', 'introduction_completed_at'])

            ProcessLog.objects.create(
                process=instance.process,
                action=ProcessLog.ActionType.INTRO_REPORTED,
                description=f"همه گزارش‌های معرفی ({reported_count} مورد) تکمیل شد",
                performed_by=instance.process.expert,
                new_value=CustomerProcess.Status.INTRODUCED
            )


# ============================================================
# 🔔 سیگنال‌های مربوط به قفل/آزادسازی مشتری و فایل (از models.py منتقل شده)
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
    if instance.status not in [
        CustomerProcess.Status.CONTRACT_PENDING,
        CustomerProcess.Status.SENT_TO_ACCOUNTING,
    ]:
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