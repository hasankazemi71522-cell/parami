# case_management/templatetags/jalali_filters.py

from django import template
from ..utils import gregorian_to_jalali

register = template.Library()


@register.filter
def show_jalali(datetime_obj):
    return gregorian_to_jalali(datetime_obj)


@register.filter
def show_jalali_date(datetime_obj):
    if not datetime_obj:
        return ''
    full = gregorian_to_jalali(datetime_obj)
    return full.split(' ')[0] if full else ''


@register.filter
def show_jalali_time(datetime_obj):
    if not datetime_obj:
        return ''
    full = gregorian_to_jalali(datetime_obj)
    return full.split(' ')[1] if full and ' ' in full else ''