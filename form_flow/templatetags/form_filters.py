# form_flow/templatetags/form_filters.py

from django import template
from datetime import datetime

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return ''
    return dictionary.get(key, '')


@register.filter
def format_duration(hours):
    if not hours:
        return '-'
    hours = float(hours)
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes} دقیقه"
    elif hours < 24:
        return f"{hours:.1f} ساعت"
    else:
        days = hours / 24
        return f"{days:.1f} روز"


@register.filter
def persian_date(date_str):
    if not date_str:
        return '-'
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%Y/%m/%d %H:%M")
    except:
        return date_str


@register.filter
def div(value, arg):
    try:
        if arg:
            return float(value) / float(arg)
        return 0
    except (ValueError, ZeroDivisionError):
        return 0


@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError):
        return 0


@register.filter
def floatformat(value, arg=1):
    try:
        return f"{float(value):.{arg}f}"
    except (ValueError, TypeError):
        return value


# ✅ فیلتر جدید برای فیلتر کردن بر اساس وضعیت
@register.filter
def filter_by_status(instances, status):
    """
    فیلتر کردن لیست فرم‌ها بر اساس وضعیت
    استفاده: instances|filter_by_status:'completed'
    """
    if not instances:
        return []

    # اگر instances یک QuerySet هست، از filter استفاده کن
    if hasattr(instances, 'filter'):
        return instances.filter(status=status)

    # اگر لیست هست، با لیست comprehension فیلتر کن
    return [i for i in instances if i.status == status]


@register.filter
def time_to_hours(time_str):
    """تبدیل رشته زمان به ساعت برای مقایسه"""
    if not time_str:
        return 0
    try:
        if 'ساعت' in time_str:
            import re
            hours = re.search(r'(\d+\.?\d*)', time_str)
            if hours:
                return float(hours.group(1))
        return 999
    except:
        return 999


@register.filter
def add(value, arg):
    """اضافه کردن دو عدد"""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value