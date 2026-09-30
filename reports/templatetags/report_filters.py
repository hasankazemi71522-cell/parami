# reports/templatetags/report_filters.py

from django import template

register = template.Library()


@register.filter
def div(value, arg):
    """تقسیم دو عدد"""
    try:
        if arg:
            return float(value) / float(arg)
        return 0
    except (ValueError, ZeroDivisionError):
        return 0


@register.filter
def mul(value, arg):
    """ضرب دو عدد"""
    try:
        return float(value) * float(arg)
    except (ValueError):
        return 0


@register.filter
def percentage(value, total):
    """محاسبه درصد"""
    try:
        if total and total > 0:
            return (float(value) / float(total)) * 100
        return 0
    except (ValueError, ZeroDivisionError):
        return 0