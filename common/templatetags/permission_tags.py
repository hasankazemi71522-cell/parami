# common/templatetags/permission_tags.py

from django import template
from django.contrib.auth.models import Permission

register = template.Library()


@register.filter(name='has_perm')
def has_perm(user, perm_code):
    """
    بررسی می‌کند که کاربر دارای مجوز مشخص شده است یا خیر
    استفاده در تمپلیت: {{ user|has_perm:'user.view' }}
    """
    if not user or not user.is_authenticated:
        return False

    # ادمین به همه چیز دسترسی دارد
    if user.is_superuser:
        return True

    # اگر کاربر متد has_permission داشته باشد
    if hasattr(user, 'has_permission'):
        return user.has_permission(perm_code)

    # روش جایگزین برای مدل‌های استاندارد
    return user.has_perm(perm_code)


@register.filter(name='has_any_perm')
def has_any_perm(user, perm_list):
    """
    بررسی می‌کند که کاربر حداقل یکی از مجوزهای مشخص شده را دارد
    استفاده: {{ user|has_any_perm:'user.view,user.add,user.edit' }}
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    perms = [p.strip() for p in perm_list.split(',')]

    for perm in perms:
        if has_perm(user, perm):
            return True

    return False


@register.filter(name='has_all_perms')
def has_all_perms(user, perm_list):
    """
    بررسی می‌کند که کاربر تمام مجوزهای مشخص شده را دارد
    استفاده: {{ user|has_all_perms:'user.view,user.add' }}
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    perms = [p.strip() for p in perm_list.split(',')]

    for perm in perms:
        if not has_perm(user, perm):
            return False

    return True


@register.filter(name='has_role')
def has_role(user, role_name):
    """
    بررسی می‌کند که کاربر دارای نقش مشخص شده است یا خیر
    استفاده: {{ user|has_role:'admin' }}
    """
    if not user or not user.is_authenticated:
        return False

    if hasattr(user, 'has_role'):
        return user.has_role(role_name)

    return False


@register.filter(name='is_admin')
def is_admin(user):
    """
    بررسی می‌کند که کاربر ادمین است یا خیر
    استفاده: {{ user|is_admin }}
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if hasattr(user, 'is_admin'):
        return user.is_admin

    return False


@register.simple_tag(takes_context=True)
def check_perm(context, perm_code):
    """
    بررسی مجوز با دسترسی به context
    استفاده: {% check_perm 'user.view' as has_access %}
    """
    user = context.get('user') or context.get('this_user')
    if not user:
        return False

    if user.is_superuser:
        return True

    if hasattr(user, 'has_permission'):
        return user.has_permission(perm_code)

    return user.has_perm(perm_code)


@register.simple_tag(takes_context=True)
def check_role(context, role_name):
    """
    بررسی نقش با دسترسی به context
    استفاده: {% check_role 'admin' as is_admin %}
    """
    user = context.get('user') or context.get('this_user')
    if not user:
        return False

    if hasattr(user, 'has_role'):
        return user.has_role(role_name)

    return False