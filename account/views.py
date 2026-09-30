from django.contrib.auth import authenticate, login, get_user_model, logout
from django.http import JsonResponse
from django.shortcuts import render, redirect
from account.models import User, Confirm_moile, Role, UserRole
from .myclass import send_message_login, send_message_signup
from datetime import datetime
from random import randint
import requests
from django.contrib.auth import logout
from django.contrib import messages

user = get_user_model()


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def logout_user(request):
    """خروج از حساب کاربری و هدایت به صفحه اصلی"""
    logout(request)
    messages.success(request, 'با موفقیت خارج شدید')
    return redirect('/')  # هدایت به صفحه اصلی


def login_page(request):
    if request.user.is_authenticated and request.user.is_active is True:
        return redirect('site_profile:dashboard')

    meta_keyword = []
    meta_description = ""
    context = {
        "title": "صفحه ورود",
        "meta_keyword": meta_keyword,
        "meta_description": meta_description,
    }

    if is_ajax(request):
        if request.GET.get('i') == "send_message":
            mobile_number = request.GET.get('mobile_number')
            person = User.objects.filter(mobile=mobile_number, is_active=True)
            if person.exists():
                my_random_msg = randint(1000, 9999)
                this_user = person.first()
                this_user.random_pass = my_random_msg
                this_user.save()
                print(my_random_msg)
                # send_message_login(mobile_number, my_random_msg)
                data = {
                    "i": 1,
                    "msg": "پیامک با موفقیت ارسال شد",
                }
            else:
                data = {
                    "i": 2,
                    "msg": "شماره وارد شده یافت نشد لطفا اول ثبت نام کنید",
                }
            return JsonResponse(data)

        if request.GET.get('i') == "login_this_user":
            password = request.GET.get('password')
            mobile_number = request.GET.get('mobile_number')
            person = User.objects.get(mobile=mobile_number, is_active=True)
            if int(password) == int(person.random_pass):
                person.confirm_mobile = True
                person.save()
                login(request, person)
                data = {
                    "msg": "رمز عبور صحیح است",
                    "i": 1,
                    "user_id": person.id,  # ← اضافه شد
                }
            else:
                data = {
                    "msg": "رمز عبور صحیح نیست لطفا مجدد امتحان نمایید",
                    "i": 2,
                }
            return JsonResponse(data)
    return render(request, 'login.html', context)


def login_pass(request):
    if request.user.is_authenticated:
        return redirect('site_profile:dashboard')

    meta_keyword = []
    meta_description = ""
    context = {
        "title": "ورود با پسورد",
        "meta_keyword": meta_keyword,
        "meta_description": meta_description,
    }

    if is_ajax(request):
        if request.GET.get('i') == "login_user":
            password = request.GET.get('password')
            username = request.GET.get('username')
            my_user = authenticate(request, username=username, password=password)
            if my_user is not None and my_user.is_active is True:
                login(request, my_user)
                data = {
                    "ok": "True",
                    "user_id": my_user.id,  # ← اضافه شد
                }
            elif my_user is not None and my_user.is_active is False:
                data = {
                    "msg": "پنل شما غیر فعال شده است",
                    "ok": "False",
                }
            else:
                data = {
                    "msg": "رمز عبور صحیح نیست لطفا مجدد امتحان نمایید",
                    "ok": "False",
                }
            return JsonResponse(data)
    return render(request, 'login_pass.html', context)


def register(request):
    if request.user.is_authenticated and request.user.is_active is True:
        userId = request.user.pk
        return redirect('site_profile:dashboard')
    meta_keyword = []
    meta_description = ""
    context = {
        "title": "ثبت نام",
        "meta_keyword": meta_keyword,
        "meta_description": meta_description,
    }
    if is_ajax(request):
        i = request.GET.get('i')
        if i == "send_message":
            mobile_number = request.GET.get('mobile_number')
            person = User.objects.filter(mobile=mobile_number)
            if person.count() != 0:
                data = {
                    "ok": "True",
                    "msg": "شماره موبایل ثبت شده قبلا در سیستم ثبت نام شده است.",
                }
            else:
                my_random_msg = randint(1000, 9999)
                this_msg = Confirm_moile.objects.filter(mobile=mobile_number)
                if this_msg.count() != 0:
                    this_msg = this_msg.first()
                    this_msg.random_pass = my_random_msg
                    this_msg.save()
                else:
                    new_user = Confirm_moile(mobile=mobile_number, random_pass=my_random_msg)
                    new_user.save()
                print(my_random_msg)
                send_message_login(mobile_number, my_random_msg)
                data = {
                    "ok": "False",
                    "msg": "پیامک ارسال شده را وارد نمایید",
                }
            return JsonResponse(data)

        if request.GET.get("i") == "signup_user":
            first_name = request.GET.get("first_name")
            last_name = request.GET.get("last_name")
            mobile = request.GET.get("mobile")
            password = request.GET.get("password")
            confirm_password = request.GET.get("confirm_password")
            confirm_mobile = request.GET.get("confirm_mobile")
            password = request.GET.get("password")
            realestate_access = request.GET.get("realestate_access")
            this_user = {"first_name": first_name, "last_name": last_name, "mobile": mobile,}
            for obj in this_user:
                if this_user[obj] == "":
                    data = {
                        "msg": "فرم کامل نیست",
                        "i": 2,
                    }
                    return JsonResponse(data)
            new_mobile = Confirm_moile.objects.get(mobile=mobile)

            if password == confirm_password:
                if int(confirm_mobile) == int(new_mobile.random_pass):
                    User.objects.create_user(username=mobile, password=password, first_name=first_name,
                                             last_name=last_name, email="", mobile=mobile,
                                             is_active=True,)
                    this_user = User.objects.get(mobile=mobile)
                    customer_role = Role.objects.get(name="customer")
                    new_user_role = UserRole(user=this_user, role=customer_role, assigned_by=this_user,
                                             )
                    new_user_role.save()
                    login(request, this_user)
                    fullname = first_name + " " + last_name
                    send_message_signup(fullname, mobile, password)
                    data = {
                        "msg": "ثبت نام شما با موفقیت انجام شد",
                        "i": 1,
                    }
                    return JsonResponse(data)
                else:
                    data = {
                        "msg": "کد پیامک شده درست وارد نگردید",
                        "i": 2,
                    }
                    return JsonResponse(data)
            else:
                data = {
                    "msg": "پسورد های وارد شده برابر نیستند",
                    "i": 2,
                }
                return JsonResponse(data)

    return render(request, 'register.html', context)


# فراموشی رمز عبور


def forgot_password(request):
    if request.user.is_authenticated and request.user.is_active is True:
        userId = request.user.pk
        return redirect('site_profile:dashboard')

    meta_keyword = []
    meta_description = ""
    context = {
        "title": "فراموشی رمز عبور",
        "meta_keyword": meta_keyword,
        "meta_description": meta_description,
    }

    if is_ajax(request):
        i = request.GET.get('i')

        # مرحله 1: ارسال کد تأیید
        if i == "send_code":
            mobile_number = request.GET.get('mobile_number')

            # بررسی وجود کاربر با این شماره موبایل
            person = User.objects.filter(mobile=mobile_number, is_active=True)

            if not person.exists():
                data = {
                    "i": 2,
                    "msg": "شماره موبایل وارد شده در سیستم ثبت نام نشده است",
                }
                return JsonResponse(data)

            # تولید کد تصادفی 4-6 رقمی
            my_random_code = randint(1000, 9999)

            # ذخیره کد در مدل Confirm_moile یا به روزرسانی آن
            confirm_obj = Confirm_moile.objects.filter(mobile=mobile_number)
            if confirm_obj.exists():
                confirm_obj = confirm_obj.first()
                confirm_obj.random_pass = my_random_code
                confirm_obj.save()
            else:
                Confirm_moile.objects.create(
                    mobile=mobile_number,
                    random_pass=my_random_code
                )

            # ذخیره کد در session برای استفاده در مرحله بعد
            request.session['reset_mobile'] = mobile_number
            request.session['reset_code'] = my_random_code

            # ارسال پیامک (در حال حاضر فقط چاپ می‌شود)
            print(my_random_code)
            send_message_login(mobile_number, my_random_code)  # فعال کردن در زمان واقعی

            data = {
                "i": 1,
                "msg": "کد تأیید برای شما ارسال شد",
            }
            return JsonResponse(data)

        # مرحله 2: تأیید کد
        if i == "verify_code":
            mobile_number = request.GET.get('mobile_number')
            code = request.GET.get('code')

            # بررسی کد از مدل یا session
            saved_code = request.session.get('reset_code')
            saved_mobile = request.session.get('reset_mobile')

            # همچنین می‌توان از مدل Confirm_moile بررسی کرد
            confirm_obj = Confirm_moile.objects.filter(mobile=mobile_number)

            if confirm_obj.exists():
                confirm_obj = confirm_obj.first()
                if int(code) == int(confirm_obj.random_pass) and saved_mobile == mobile_number:
                    data = {
                        "i": 1,
                        "msg": "کد تأیید صحیح است",
                    }
                else:
                    data = {
                        "i": 2,
                        "msg": "کد تأیید اشتباه است",
                    }
            else:
                data = {
                    "i": 2,
                    "msg": "درخواست نامعتبر. لطفاً مجدداً تلاش کنید",
                }
            return JsonResponse(data)

        # مرحله 3: بازنشانی رمز عبور
        if i == "reset_password":
            mobile_number = request.GET.get('mobile_number')
            code = request.GET.get('code')
            new_password = request.GET.get('new_password')

            # اعتبارسنجی رمز عبور جدید
            if len(new_password) < 4:
                data = {
                    "i": 2,
                    "msg": "رمز عبور باید حداقل 4 کاراکتر باشد",
                }
                return JsonResponse(data)

            # بررسی صحت کد
            confirm_obj = Confirm_moile.objects.filter(mobile=mobile_number)
            saved_mobile = request.session.get('reset_mobile')

            if not confirm_obj.exists() or saved_mobile != mobile_number:
                data = {
                    "i": 2,
                    "msg": "درخواست نامعتبر. لطفاً مجدداً تلاش کنید",
                }
                return JsonResponse(data)

            confirm_obj = confirm_obj.first()
            if int(code) != int(confirm_obj.random_pass):
                data = {
                    "i": 2,
                    "msg": "کد تأیید اشتباه است",
                }
                return JsonResponse(data)

            # دریافت کاربر و تغییر رمز عبور
            try:
                user_obj = User.objects.get(mobile=mobile_number, is_active=True)
                user_obj.set_password(new_password)
                user_obj.save()

                # پاک کردن session و کد تأیید
                del request.session['reset_mobile']
                del request.session['reset_code']
                confirm_obj.delete()

                data = {
                    "i": 1,
                    "msg": "رمز عبور با موفقیت تغییر کرد. لطفاً وارد شوید",
                }
            except User.DoesNotExist:
                data = {
                    "i": 2,
                    "msg": "کاربر یافت نشد",
                }

            return JsonResponse(data)

    return render(request, 'forgot_password.html', context)