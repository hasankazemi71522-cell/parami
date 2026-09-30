from django import template
from datetime import datetime

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    دریافت مقدار از دیکشنری با کلید
    استفاده: {{ dictionary|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def get_status_badge(status):
    """
    دریافت کلاس بوت‌استرپ برای وضعیت‌های مختلف برگشت
    استفاده: {{ rejection.status|get_status_badge }}
    """
    badges = {
        'pending': 'warning',
        'responded': 'info',
        'fixed': 'success',
        'rejected_again': 'danger',
        'approved': 'success',
        'expired': 'secondary'
    }
    return badges.get(status, 'secondary')


@register.filter
def get_status_text(status):
    """
    دریافت متن فارسی برای وضعیت‌های مختلف برگشت
    استفاده: {{ rejection.status|get_status_text }}
    """
    texts = {
        'pending': 'در انتظار اصلاح',
        'responded': 'پاسخ داده شده',
        'fixed': 'اصلاح شده',
        'rejected_again': 'دوباره برگشت خورده',
        'approved': 'تایید شده',
        'expired': 'منقضی شده'
    }
    return texts.get(status, status)


@register.filter
def get_reply_type_badge(reply_type):
    """
    دریافت کلاس بوت‌استرپ برای نوع پاسخ
    استفاده: {{ reply.reply_type|get_reply_type_badge }}
    """
    badges = {
        'response': 'secondary',
        'clarification': 'info',
        'approve': 'success',
        'reject_again': 'danger',
        'fix': 'primary'
    }
    return badges.get(reply_type, 'secondary')


@register.filter
def get_reply_type_text(reply_type):
    """
    دریافت متن فارسی برای نوع پاسخ
    استفاده: {{ reply.reply_type|get_reply_type_text }}
    """
    texts = {
        'response': 'پاسخ به برگشت',
        'clarification': 'درخواست توضیح بیشتر',
        'approve': 'تایید',
        'reject_again': 'برگشت مجدد',
        'fix': 'اصلاح شد'
    }
    return texts.get(reply_type, reply_type)


@register.filter
def get_level_badge(level):
    """
    دریافت کلاس بوت‌استرپ برای سطح برگشت
    استفاده: {{ rejection.level|get_level_badge }}
    """
    badges = {
        'field': 'warning',
        'step': 'info',
        'form': 'danger'
    }
    return badges.get(level, 'secondary')


@register.filter
def get_level_text(level):
    """
    دریافت متن فارسی برای سطح برگشت
    استفاده: {{ rejection.level|get_level_text }}
    """
    texts = {
        'field': 'سطح فیلد',
        'step': 'سطح مرحله',
        'form': 'سطح کل فرم'
    }
    return texts.get(level, level)


@register.filter
def format_datetime(value):
    """
    فرمت کردن تاریخ و زمان به صورت فارسی
    استفاده: {{ datetime|format_datetime }}
    """
    if not value:
        return '-'
    try:
        if isinstance(value, str):
            from datetime import datetime
            value = datetime.fromisoformat(value)
        return value.strftime("%Y/%m/%d %H:%M")
    except:
        return str(value)


@register.filter
def format_date(value):
    """
    فرمت کردن تاریخ به صورت فارسی
    استفاده: {{ date|format_date }}
    """
    if not value:
        return '-'
    try:
        if isinstance(value, str):
            from datetime import datetime
            value = datetime.fromisoformat(value)
        return value.strftime("%Y/%m/%d")
    except:
        return str(value)


@register.filter
def format_time(value):
    """
    فرمت کردن زمان به صورت فارسی
    استفاده: {{ time|format_time }}
    """
    if not value:
        return '-'
    try:
        if isinstance(value, str):
            from datetime import datetime
            value = datetime.fromisoformat(value)
        return value.strftime("%H:%M")
    except:
        return str(value)


@register.filter
def get_field_value(form_instance, field_id):
    """
    دریافت مقدار یک فیلد از فرم
    استفاده: {{ form_instance|get_field_value:field_id }}
    """
    try:
        from form_flow.models import FormFieldValue
        fv = FormFieldValue.objects.filter(
            form_instance=form_instance,
            instance_field_id=field_id
        ).first()
        if fv:
            if fv.value:
                return fv.value
            elif fv.file_value:
                return f'فایل: {fv.file_value.name.split("/")[-1]}'
            elif fv.image_value:
                return f'تصویر: {fv.image_value.name.split("/")[-1]}'
        return '—'
    except:
        return '—'


@register.filter
def get_field_filled_by(form_instance, field_id):
    """
    دریافت کاربر پرکننده یک فیلد
    استفاده: {{ form_instance|get_field_filled_by:field_id }}
    """
    try:
        from form_flow.models import FormFieldValue
        fv = FormFieldValue.objects.filter(
            form_instance=form_instance,
            instance_field_id=field_id
        ).first()
        if fv and fv.filled_by:
            return fv.filled_by.get_full_name() or fv.filled_by.username
        return '—'
    except:
        return '—'


@register.filter
def get_field_filled_at(form_instance, field_id):
    """
    دریافت زمان پر شدن یک فیلد
    استفاده: {{ form_instance|get_field_filled_at:field_id }}
    """
    try:
        from form_flow.models import FormFieldValue
        fv = FormFieldValue.objects.filter(
            form_instance=form_instance,
            instance_field_id=field_id
        ).first()
        if fv and fv.filled_at:
            return fv.filled_at.strftime("%Y/%m/%d %H:%M")
        return '—'
    except:
        return '—'


@register.filter
def get_assigned_users_count(instance):
    """
    تعداد کاربران مسئول اصلاح یک برگشت
    استفاده: {{ rejection|get_assigned_users_count }}
    """
    try:
        from .models import Rejection
        return Rejection.objects.filter(
            form_instance=instance,
            status__in=['pending', 'responded']
        ).values('assigned_to').distinct().count()
    except:
        return 0


@register.filter
def get_rejection_count(instance):
    """
    تعداد کل برگشت‌های یک فرم
    استفاده: {{ instance|get_rejection_count }}
    """
    try:
        from .models import Rejection
        return Rejection.objects.filter(form_instance=instance).count()
    except:
        return 0


@register.filter
def get_pending_rejection_count(instance):
    """
    تعداد برگشت‌های در انتظار اصلاح یک فرم
    استفاده: {{ instance|get_pending_rejection_count }}
    """
    try:
        from .models import Rejection
        return Rejection.objects.filter(
            form_instance=instance,
            status='pending'
        ).count()
    except:
        return 0


@register.filter
def is_assigned_to_user(rejection, user):
    """
    بررسی اینکه آیا برگشت به کاربر داده شده است
    استفاده: {{ rejection|is_assigned_to_user:user }}
    """
    if not rejection or not user:
        return False
    return rejection.assigned_to == user


@register.filter
def is_rejected_by_user(rejection, user):
    """
    بررسی اینکه آیا برگشت توسط کاربر داده شده است
    استفاده: {{ rejection|is_rejected_by_user:user }}
    """
    if not rejection or not user:
        return False
    return rejection.rejected_by == user


@register.filter
def can_user_fix_rejection(rejection, user):
    """
    بررسی اینکه آیا کاربر می‌تواند برگشت را اصلاح کند
    استفاده: {{ rejection|can_user_fix_rejection:user }}
    """
    if not rejection or not user:
        return False
    if user.is_admin or user.is_superuser:
        return True
    return rejection.assigned_to == user and rejection.status in ['pending', 'responded']


@register.filter
def can_user_reply_rejection(rejection, user):
    """
    بررسی اینکه آیا کاربر می‌تواند به برگشت پاسخ دهد
    استفاده: {{ rejection|can_user_reply_rejection:user }}
    """
    if not rejection or not user:
        return False
    if user.is_admin or user.is_superuser:
        return True
    return rejection.assigned_to == user


@register.filter
def is_expired(value):
    """
    بررسی اینکه آیا تاریخ منقضی شده است
    استفاده: {{ deadline_at|is_expired }}
    """
    if not value:
        return False
    from django.utils import timezone
    try:
        if isinstance(value, str):
            from datetime import datetime
            value = datetime.fromisoformat(value)
        return timezone.now() > value
    except:
        return False


@register.filter
def remaining_time(value):
    """
    محاسبه زمان باقی‌مانده
    استفاده: {{ deadline_at|remaining_time }}
    """
    if not value:
        return 'بدون محدودیت'
    from django.utils import timezone
    try:
        if isinstance(value, str):
            from datetime import datetime
            value = datetime.fromisoformat(value)

        remaining = value - timezone.now()
        if remaining.total_seconds() <= 0:
            return 'منقضی شده'

        days = remaining.days
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60

        if days > 0:
            return f"{days} روز و {hours} ساعت"
        elif hours > 0:
            return f"{hours} ساعت و {minutes} دقیقه"
        else:
            return f"{minutes} دقیقه"
    except:
        return '—'


@register.filter
def truncate_text(value, length=50):
    """
    کوتاه کردن متن
    استفاده: {{ text|truncate_text:100 }}
    """
    if not value:
        return ''
    if len(value) > length:
        return value[:length] + '...'
    return value


@register.filter
def get_full_name_or_username(user):
    """
    دریافت نام کامل یا نام کاربری
    استفاده: {{ user|get_full_name_or_username }}
    """
    if not user:
        return '—'
    return user.get_full_name() or user.username


@register.filter
def get_rejection_target_display(rejection):
    """
    دریافت نمایش هدف برگشت
    استفاده: {{ rejection|get_rejection_target_display }}
    """
    if not rejection:
        return '—'
    if rejection.level == 'field' and rejection.instance_field:
        return f"فیلد: {rejection.instance_field.field_title}"
    elif rejection.level == 'step' and rejection.step_number:
        return f"مرحله: {rejection.step_number}"
    elif rejection.level == 'form':
        return "کل فرم"
    return '—'


@register.filter
def get_rejection_level_icon(level):
    """
    دریافت آیکون برای سطح برگشت
    استفاده: {{ rejection.level|get_rejection_level_icon }}
    """
    icons = {
        'field': 'bi-pencil-square',
        'step': 'bi-layers',
        'form': 'bi-file-earmark'
    }
    return icons.get(level, 'bi-question-circle')


@register.filter
def get_status_icon(status):
    """
    دریافت آیکون برای وضعیت برگشت
    استفاده: {{ rejection.status|get_status_icon }}
    """
    icons = {
        'pending': 'bi-clock-history',
        'responded': 'bi-chat-dots',
        'fixed': 'bi-check-circle',
        'rejected_again': 'bi-x-circle',
        'approved': 'bi-check2-circle',
        'expired': 'bi-hourglass-split'
    }
    return icons.get(status, 'bi-question-circle')