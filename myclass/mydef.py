from django.contrib.auth import get_user_model, logout, login
from account.myclass import send_message_login
from random import randint
from account.models import User
from datetime import datetime
from site_profile.other_class.profile_class import three_digits
from account.models import User, Role, UserRole, Permission, RolePermission
user = get_user_model()
from django.utils import timezone
from persiantools.jdatetime import JalaliDate, JalaliDateTime
from datetime import datetime, date


def to_shamsi_date(value):
    """تبدیل تاریخ میلادی به شیء JalaliDate (فقط تاریخ) با رعایت تایم‌زون"""
    if not value:
        return None
    try:
        if isinstance(value, (date, datetime)):
            # اگر datetime است و timezone-aware نیست، آن را aware کن
            if isinstance(value, datetime):
                if timezone.is_naive(value):
                    value = timezone.make_aware(value, timezone.get_current_timezone())
                # تبدیل به timezone محلی
                local_value = timezone.localtime(value)
                return JalaliDate.to_jalali(local_value.date())
            return JalaliDate.to_jalali(value)
        elif isinstance(value, str):
            dt = datetime.fromisoformat(value)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            local_dt = timezone.localtime(dt)
            return JalaliDate.to_jalali(local_dt.date())
    except Exception as e:
        print(f"Error converting to shamsi date: {e}")
        return None
    return None


def to_shamsi_datetime(value):
    """تبدیل datetime میلادی به شیء JalaliDateTime (تاریخ و زمان) با رعایت تایم‌زون"""
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            # اگر timezone-naive بود، آن را aware کن
            if timezone.is_naive(value):
                value = timezone.make_aware(value, timezone.get_current_timezone())
            # تبدیل به timezone محلی (Asia/Tehran)
            local_value = timezone.localtime(value)
            return JalaliDateTime.to_jalali(local_value)
        elif isinstance(value, str):
            dt = datetime.fromisoformat(value)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            local_dt = timezone.localtime(dt)
            return JalaliDateTime.to_jalali(local_dt)
    except Exception as e:
        print(f"Error converting to shamsi datetime: {e}")
        return None
    return None


def views_permissions(user, view_name):
    this_user_role = UserRole.objects.filter(user=user, is_active=True)
    perimissin_list = []
    perimissin_group = []
    for obj in this_user_role:
        this_perimissions = RolePermission.objects.filter(role=obj.role)
        for perimission in this_perimissions:
            if perimission.permission.code not in perimissin_list:
                perimissin_list.append(perimission.permission.code)
            if perimission.permission.group not in perimissin_group:
                perimissin_group.append(perimission.permission.group)
    if user.is_superuser:
        perimission = True
    elif view_name not in perimissin_list:
        perimission = False
    else:
        perimission = True
    return (perimission, perimissin_list, perimissin_group)


def logout_user(this_user):
    logout(this_user)
    data = {
        "msg": 'با موفقیت خارج شدید'
    }
    return (data)



def edit_back_mode(this_user, mode):
    this_user.back_mode = mode
    this_user.save()



def send_random_code(mobile):
    new_users = User.objects.filter(mobile=mobile)
    if new_users.exists():
        new_user = new_users.first()
        my_random_msg = randint(1000, 9999)
        new_user.random_pass = my_random_msg
        new_user.save()
        send_message_login(mobile, my_random_msg)
        # print(my_random_msg)
        data = {
            "msg": "رمز ارسال شده را وارد نموده و ثبت درخواست نمایید",
        }
    else:
        my_random_msg = str(randint(1000, 9999))
        User.objects.create_user(username=mobile, password=my_random_msg,
                                 email="", mobile=mobile, )
        this_user = User.objects.get(mobile=mobile)
        this_user.random_pass = my_random_msg
        this_user.save()
        send_message_login(mobile, my_random_msg)
        # print(my_random_msg)
        data = {
            "msg": "رمز ارسال شده را وارد نموده و شروع به خرید کنید"
        }
    return (data)
