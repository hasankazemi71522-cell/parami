from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta

from account.models import User, Role
from case_management.models import CustomerProcess
from estate.models import (
    Customer, Property, PropertyType, Source,
    Province, City, Neighborhood, Requirement, UsageType,
    Note, DuplicateCheck
)
from myclass.mydef import views_permissions
from myclass.mydef import to_shamsi_date, to_shamsi_datetime
from estate.views_duplicate import check_customer_duplicate_logic


# ============================================================
# 🗓️ توابع کمکی برای تبدیل تاریخ به رشته شمسی
# ============================================================

def get_shamsi_date(value):
    """تبدیل تاریخ میلادی به رشته شمسی (فقط تاریخ) - مثال: 1403/07/05"""
    if not value:
        return ''
    try:
        jalali = to_shamsi_date(value)
        if jalali:
            return f"{jalali.year}/{jalali.month:02d}/{jalali.day:02d}"
    except Exception as e:
        print(f"خطا در تبدیل تاریخ شمسی: {e}")
    return ''


def get_shamsi_datetime(value):
    """تبدیل تاریخ میلادی به رشته شمسی (تاریخ و ساعت) - مثال: 1403/07/05 14:30"""
    if not value:
        return ''
    try:
        jalali = to_shamsi_datetime(value)
        if jalali:
            return f"{jalali.year}/{jalali.month:02d}/{jalali.day:02d} {jalali.hour:02d}:{jalali.minute:02d}"
    except Exception as e:
        print(f"خطا در تبدیل تاریخ و ساعت شمسی: {e}")
    return ''


# ============================================================
# 👥 مدیریت کارشناسان (کال سنتر)
# ============================================================

@login_required
def manage_experts_callcenter(request):
    """
    مدیریت کارشناسان توسط کال سنتر
    نمایش لیست سرپرست‌ها، کارشناسان بدون سرپرست و کارشناسان تحت نظر سرپرست‌ها
    """
    user = request.user

    # بررسی مجوز
    permission, perimissin_list, perimissin_group = views_permissions(user, "manage_experts_callcenter")
    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    # ========== لیست سرپرست‌ها ==========
    supervisors = User.objects.filter(
        is_active=True,
        user_roles__role__name='supervisor',
        user_roles__is_active=True
    ).annotate(
        experts_count=Count(
            'subordinates',
            filter=Q(
                subordinates__is_active=True,
                subordinates__user_roles__role__name='expert',
                subordinates__user_roles__is_active=True,
            ),
            distinct=True  # ✅ برای جلوگیری از شمارش تکراری در صورت چند نقش
        )
    ).distinct().order_by('first_name', 'last_name')

    # ========== لیست کارشناسان بدون سرپرست ==========
    unassigned_experts = User.objects.filter(
        is_active=True,
        user_roles__role__name='expert',
        user_roles__is_active=True,
        referral__isnull=True
    ).distinct().order_by('first_name', 'last_name')

    # ========== لیست کارشناسان تحت نظر سرپرست‌ها ==========
    assigned_experts = User.objects.filter(
        is_active=True,
        user_roles__role__name='expert',
        user_roles__is_active=True,
        referral__isnull=False
    ).distinct().order_by('first_name', 'last_name')

    # جستجو در کارشناسان بدون سرپرست
    search = request.GET.get('search', '')
    if search:
        unassigned_experts = unassigned_experts.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(mobile__icontains=search) |
            Q(username__icontains=search)
        )

    # جستجو در کارشناسان تحت نظر
    assigned_search = request.GET.get('assigned_search', '')
    if assigned_search:
        assigned_experts = assigned_experts.filter(
            Q(first_name__icontains=assigned_search) |
            Q(last_name__icontains=assigned_search) |
            Q(mobile__icontains=assigned_search) |
            Q(username__icontains=assigned_search)
        )

    # جستجو در سرپرست‌ها
    supervisor_search = request.GET.get('supervisor_search', '')
    if supervisor_search:
        supervisors = supervisors.filter(
            Q(first_name__icontains=supervisor_search) |
            Q(last_name__icontains=supervisor_search) |
            Q(mobile__icontains=supervisor_search) |
            Q(username__icontains=supervisor_search)
        )

    # صفحه‌بندی کارشناسان بدون سرپرست
    paginator = Paginator(unassigned_experts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر کاربر
    for s in supervisors:
        s.date_joined_shamsi = get_shamsi_date(s.date_joined)
        s.last_login_shamsi = get_shamsi_datetime(s.last_login)
    for e in page_obj:
        e.date_joined_shamsi = get_shamsi_date(e.date_joined)
        e.last_login_shamsi = get_shamsi_datetime(e.last_login)
    for e in assigned_experts:
        e.date_joined_shamsi = get_shamsi_date(e.date_joined)
        e.last_login_shamsi = get_shamsi_datetime(e.last_login)

    # آمار
    stats = {
        'total_supervisors': supervisors.count(),
        'total_unassigned': unassigned_experts.count(),
        'total_assigned': assigned_experts.count(),
        'total_experts': User.objects.filter(
            user_roles__role__name='expert',
            user_roles__is_active=True,
            is_active=True
        ).distinct().count(),
    }

    context = {
        'supervisors': supervisors,
        'unassigned_experts': page_obj,
        'assigned_experts': assigned_experts,
        'stats': stats,
        'search': search,
        'assigned_search': assigned_search,
        'supervisor_search': supervisor_search,
        'title': 'مدیریت کارشناسان (کال سنتر)',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'workflow/manage_experts_callcenter.html', context)


@login_required
def assign_expert_to_supervisor(request):
    """
    اختصاص کارشناس به سرپرست توسط کال سنتر (با قابلیت تعیین ظرفیت)
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "manage_experts_callcenter")
    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    if request.method == 'POST':
        expert_id = request.POST.get('expert_id')
        supervisor_id = request.POST.get('supervisor_id')
        max_concurrent = request.POST.get('max_concurrent', 5)

        try:
            with transaction.atomic():
                expert = User.objects.get(id=expert_id)
                supervisor = User.objects.get(id=supervisor_id)

                if not expert.has_role('expert'):
                    messages.error(request, 'کاربر انتخاب شده کارشناس نیست')
                    return redirect('site_profile:manage_experts_callcenter')

                if not supervisor.has_role('supervisor'):
                    messages.error(request, 'کاربر انتخاب شده سرپرست نیست')
                    return redirect('site_profile:manage_experts_callcenter')

                if expert.referral:
                    messages.error(request,
                                   f'این کارشناس قبلاً به {expert.referral.get_full_name()} اختصاص داده شده است')
                    return redirect('site_profile:manage_experts_callcenter')

                expert.referral = supervisor
                expert.max_concurrent = int(max_concurrent)
                expert.is_available = True
                expert.save()

                messages.success(
                    request,
                    f'کارشناس {expert.get_full_name()} با ظرفیت {max_concurrent} پرونده به {supervisor.get_full_name()} اختصاص داده شد'
                )
                return redirect('site_profile:manage_experts_callcenter')

        except User.DoesNotExist:
            messages.error(request, 'کاربر مورد نظر یافت نشد')
        except Exception as e:
            messages.error(request, f'خطا: {str(e)}')

    return redirect('site_profile:manage_experts_callcenter')


@login_required
def transfer_expert(request):
    """
    انتقال کارشناس از یک سرپرست به سرپرست دیگر (توسط کال سنتر)
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "manage_experts_callcenter")
    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    if request.method == 'POST':
        expert_id = request.POST.get('expert_id')
        new_supervisor_id = request.POST.get('new_supervisor_id')
        max_concurrent = request.POST.get('max_concurrent', 5)

        try:
            with transaction.atomic():
                expert = User.objects.get(id=expert_id)
                new_supervisor = User.objects.get(id=new_supervisor_id)

                if not expert.has_role('expert'):
                    messages.error(request, 'کاربر انتخاب شده کارشناس نیست')
                    return redirect('site_profile:manage_experts_callcenter')

                if not new_supervisor.has_role('supervisor'):
                    messages.error(request, 'کاربر انتخاب شده سرپرست نیست')
                    return redirect('site_profile:manage_experts_callcenter')

                old_supervisor = expert.referral
                if not old_supervisor:
                    messages.error(request, 'این کارشناس زیر نظر هیچ سرپرستی نیست. ابتدا به یک سرپرست اختصاص دهید.')
                    return redirect('site_profile:manage_experts_callcenter')

                old_supervisor_name = old_supervisor.get_full_name()
                expert.referral = new_supervisor
                expert.max_concurrent = int(max_concurrent)
                expert.save()

                messages.success(
                    request,
                    f'کارشناس {expert.get_full_name()} با ظرفیت {max_concurrent} پرونده از {old_supervisor_name} به {new_supervisor.get_full_name()} منتقل شد'
                )
                return redirect('site_profile:manage_experts_callcenter')

        except User.DoesNotExist:
            messages.error(request, 'کاربر مورد نظر یافت نشد')
        except Exception as e:
            messages.error(request, f'خطا: {str(e)}')

    return redirect('site_profile:manage_experts_callcenter')


@login_required
def remove_expert_from_supervisor(request):
    """
    خارج کردن کارشناس از زیر مجموعه سرپرست (بازگشت به وضعیت بدون سرپرست)
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "manage_experts_callcenter")
    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    if request.method == 'POST':
        expert_id = request.POST.get('expert_id')

        try:
            with transaction.atomic():
                expert = User.objects.get(id=expert_id)

                if not expert.referral:
                    messages.error(request, 'این کارشناس زیر نظر هیچ سرپرستی نیست')
                    return redirect('site_profile:manage_experts_callcenter')

                supervisor_name = expert.referral.get_full_name()
                expert.referral = None
                expert.is_available = False
                expert.save()

                messages.success(
                    request,
                    f'کارشناس {expert.get_full_name()} از زیر مجموعه {supervisor_name} خارج شد'
                )
                return redirect('site_profile:manage_experts_callcenter')

        except User.DoesNotExist:
            messages.error(request, 'کاربر مورد نظر یافت نشد')
        except Exception as e:
            messages.error(request, f'خطا: {str(e)}')

    return redirect('site_profile:manage_experts_callcenter')


@login_required
def get_supervisor_experts(request, supervisor_id):
    """
    دریافت لیست کارشناسان یک سرپرست (API)
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "manage_experts_callcenter")
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    try:
        supervisor = User.objects.get(id=supervisor_id)
        experts = User.objects.filter(
            referral=supervisor,
            is_active=True,
            user_roles__role__name='expert',
            user_roles__is_active=True
        ).distinct().order_by('first_name', 'last_name')

        data = []
        for expert in experts:
            data.append({
                'id': expert.id,
                'full_name': expert.get_full_name(),
                'mobile': expert.mobile,
                'is_available': expert.is_available,
                'max_concurrent': expert.max_concurrent,
                'referral_id': expert.referral.id if expert.referral else None,
                'date_joined_shamsi': get_shamsi_date(expert.date_joined),  # ✅
            })

        return JsonResponse({
            'success': True,
            'supervisor_name': supervisor.get_full_name(),
            'experts': data,
            'count': len(data)
        })

    except User.DoesNotExist:
        return JsonResponse({'error': 'سرپرست یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def edit_expert_capacity(request):
    """
    ویرایش ظرفیت کارشناس (توسط کال سنتر) - API
    """
    user = request.user

    if request.method == 'POST':
        expert_id = request.POST.get('expert_id')
        max_concurrent = request.POST.get('max_concurrent')

        try:
            expert = User.objects.get(id=expert_id)
            expert.max_concurrent = int(max_concurrent)
            expert.save()

            return JsonResponse({
                'success': True,
                'message': f'ظرفیت کارشناس {expert.get_full_name()} به {max_concurrent} تغییر یافت'
            })
        except User.DoesNotExist:
            return JsonResponse({'error': 'کارشناس یافت نشد'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'روش نامعتبر'}, status=405)


@login_required
def remove_expert_from_supervisor_ajax(request):
    """
    حذف کارشناس از سرپرست (API)
    """
    user = request.user

    if request.method == 'POST':
        expert_id = request.POST.get('expert_id')

        try:
            expert = User.objects.get(id=expert_id)

            if not expert.referral:
                return JsonResponse({'error': 'این کارشناس زیر نظر هیچ سرپرستی نیست'}, status=400)

            supervisor_name = expert.referral.get_full_name()
            expert.referral = None
            expert.is_available = False
            expert.save()

            return JsonResponse({
                'success': True,
                'message': f'کارشناس {expert.get_full_name()} از زیر مجموعه {supervisor_name} خارج شد'
            })
        except User.DoesNotExist:
            return JsonResponse({'error': 'کارشناس یافت نشد'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'روش نامعتبر'}, status=405)


# ============================================================
# 📋 مدیریت مشتریان بدون سرپرست (کال سنتر)
# ============================================================

@login_required
def customers_without_supervisor(request):
    """
    نمایش لیست مشتریانی که سرپرست ندارند
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "customers_without_supervisor")
    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    customers = Customer.objects.filter(
        is_active=True,
        status__in=[Customer.Status.NEW]
    ).select_related(
        'user',
        'created_by',
        'source'
    ).prefetch_related(
        'preferred_cities',
        'preferred_neighborhoods',
        'preferred_property_types',
        'preferred_requirements'
    ).order_by('-priority', '-created_at')

    from estate.views_duplicate import check_customer_duplicate_logic

    customers_with_duplicate = []
    for customer in customers:
        customer_data = {
            'customer_type': customer.customer_type,
            'preferred_cities': list(customer.preferred_cities.values_list('id', flat=True)),
            'preferred_neighborhoods': list(customer.preferred_neighborhoods.values_list('id', flat=True)),
            'preferred_property_types': list(customer.preferred_property_types.values_list('id', flat=True)),
            'preferred_requirements': list(customer.preferred_requirements.values_list('id', flat=True)),
            'budget_min': str(customer.budget_min) if customer.budget_min else None,
            'budget_max': str(customer.budget_max) if customer.budget_max else None,
            'min_area': str(customer.min_area) if customer.min_area else None,
            'max_area': str(customer.max_area) if customer.max_area else None,
            'min_rooms': customer.min_rooms,
            'max_rooms': customer.max_rooms,
        }

        duplicate_result = check_customer_duplicate_logic(
            customer_data,
            customer_id=str(customer.id)
        )

        filtered_duplicates = []
        for dup in duplicate_result.get('duplicates', []):
            if dup['id'] != str(customer.id):
                filtered_duplicates.append(dup)

        customer.duplicate_info = {
            'has_duplicate': len(filtered_duplicates) > 0,
            'duplicates': filtered_duplicates[:5],
            'count': len(filtered_duplicates),
            'check_id': duplicate_result.get('duplicate_check_id')
        }

        customers_with_duplicate.append(customer)

    search = request.GET.get('search', '')
    if search:
        customers_with_duplicate = [c for c in customers_with_duplicate if
                                    search.lower() in c.full_name.lower() or
                                    search in c.mobile.lower() or
                                    (c.user.email and search.lower() in c.user.email.lower()) or
                                    search.lower() in (c.display_code or '').lower()
                                    ]

    customer_type = request.GET.get('customer_type', '')
    if customer_type:
        customers_with_duplicate = [c for c in customers_with_duplicate if c.customer_type == customer_type]

    source_filter = request.GET.get('source', '')
    if source_filter:
        customers_with_duplicate = [c for c in customers_with_duplicate if str(c.source_id) == source_filter]

    duplicate_filter = request.GET.get('duplicate_filter', '')
    if duplicate_filter == 'has_duplicate':
        customers_with_duplicate = [c for c in customers_with_duplicate if c.duplicate_info['has_duplicate']]
    elif duplicate_filter == 'no_duplicate':
        customers_with_duplicate = [c for c in customers_with_duplicate if not c.duplicate_info['has_duplicate']]

    paginator = Paginator(customers_with_duplicate, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر مشتری
    for c in page_obj:
        c.created_at_shamsi = get_shamsi_date(c.created_at)
        c.updated_at_shamsi = get_shamsi_date(c.updated_at)

    total = len(customers_with_duplicate)
    has_dup_count = len([c for c in customers_with_duplicate if c.duplicate_info['has_duplicate']])

    stats = {
        'total': total,
        'new': len([c for c in customers_with_duplicate if c.status == Customer.Status.NEW]),
        'without_supervisor': len([c for c in customers_with_duplicate if c.supervisor is None]),
        'has_duplicate': has_dup_count,
        'no_duplicate': total - has_dup_count,
        'by_type': {
            'buyer': len([c for c in customers_with_duplicate if c.customer_type == Customer.CustomerType.BUYER]),
            'tenant': len([c for c in customers_with_duplicate if c.customer_type == Customer.CustomerType.TENANT]),
            'developer': len(
                [c for c in customers_with_duplicate if c.customer_type == Customer.CustomerType.DEVELOPER]),
            'investor': len([c for c in customers_with_duplicate if c.customer_type == Customer.CustomerType.INVESTOR]),
        }
    }

    supervisors = User.objects.filter(
        is_active=True,
        user_roles__role__name='supervisor',
        user_roles__is_active=True
    ).annotate(
        experts_count=Count('subordinates', filter=Q(subordinates__is_active=True))
    ).order_by('first_name', 'last_name')

    assigned_experts = User.objects.filter(
        is_active=True,
        user_roles__role__name='expert',
        user_roles__is_active=True,
        referral__isnull=False
    ).distinct().order_by('first_name', 'last_name')

    sources = Source.objects.filter(is_active=True).order_by('name')

    context = {
        'customers': page_obj,
        'stats': stats,
        'supervisors': supervisors,
        'assigned_experts': assigned_experts,
        'sources': sources,
        'search': search,
        'customer_type': customer_type,
        'source_filter': source_filter,
        'duplicate_filter': duplicate_filter,
        'title': 'مدیریت مشتریان بدون سرپرست',
        'userId': user.id,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'workflow/customers_without_supervisor.html', context)


@login_required
def assign_supervisor_to_customer(request):
    """
    اختصاص سرپرست به مشتری توسط کال سنتر
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "customers_without_supervisor")
    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        supervisor_id = request.POST.get('supervisor_id')

        try:
            with transaction.atomic():
                customer = Customer.objects.get(
                    pk=customer_id,
                    is_active=True,
                    supervisor__isnull=True
                )

                supervisor = User.objects.get(
                    id=supervisor_id,
                    is_active=True,
                    user_roles__role__name='supervisor',
                    user_roles__is_active=True
                )

                customer.supervisor = supervisor
                customer.status = Customer.Status.CONFIRMED
                customer.last_contact = timezone.now()
                customer.total_interactions += 1
                customer.save()

                messages.success(
                    request,
                    f'سرپرست {supervisor.get_full_name()} با موفقیت به مشتری {customer.full_name} اختصاص داده شد'
                )
                return redirect('site_profile:customers_without_supervisor')

        except Customer.DoesNotExist:
            messages.error(request, 'مشتری مورد نظر یافت نشد یا قبلاً سرپرست به او اختصاص داده شده است')
        except User.DoesNotExist:
            messages.error(request, 'سرپرست مورد نظر یافت نشد')
        except Exception as e:
            messages.error(request, f'خطا: {str(e)}')

    return redirect('site_profile:customers_without_supervisor')


@login_required
def edit_customer_supervisor(request):
    """
    ویرایش سرپرست مشتری توسط کال سنتر
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "customers_without_supervisor")
    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        supervisor_id = request.POST.get('supervisor_id')

        try:
            with transaction.atomic():
                customer = Customer.objects.get(
                    pk=customer_id,
                    is_active=True
                )

                supervisor = User.objects.get(
                    id=supervisor_id,
                    is_active=True,
                    user_roles__role__name='supervisor',
                    user_roles__is_active=True
                )

                old_supervisor = customer.supervisor
                customer.supervisor = supervisor
                customer.status = Customer.Status.CONFIRMED
                customer.last_contact = timezone.now()
                customer.total_interactions += 1
                customer.save()

                old_name = old_supervisor.get_full_name() if old_supervisor else 'بدون سرپرست'
                messages.success(
                    request,
                    f'سرپرست مشتری {customer.full_name} از {old_name} به {supervisor.get_full_name()} تغییر یافت'
                )
                return redirect('site_profile:customers_without_supervisor')

        except Customer.DoesNotExist:
            messages.error(request, 'مشتری مورد نظر یافت نشد')
        except User.DoesNotExist:
            messages.error(request, 'سرپرست مورد نظر یافت نشد')
        except Exception as e:
            messages.error(request, f'خطا: {str(e)}')

    return redirect('site_profile:customers_without_supervisor')


@login_required
def confirm_customer(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        customer_obj = get_object_or_404(Customer, pk=customer_id)
        customer_obj.status = 'confirmed'
        customer_obj.save()
        process = CustomerProcess.objects.create(
            customer=customer_obj,
            expert=customer_obj.expert,
            supervisor=customer_obj.supervisor,
            status=CustomerProcess.Status.ASSIGNED,
            contact_deadline=timezone.now() + timedelta(hours=24)
        )
        messages.success(request, f'مشتری "{customer_obj.full_name}" با موفقیت تایید شد.')
    return redirect('site_profile:customers_without_supervisor')


@login_required
def delete_customer(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        customer_obj = get_object_or_404(Customer, pk=customer_id)
        customer_obj.soft_delete()
        messages.success(request, f'مشتری "{customer_obj.full_name}" با موفقیت حذف شد.')
    return redirect('site_profile:customers_without_supervisor')


# ============================================================
# 🏠 مدیریت فایل‌ها (املاک) بدون سرپرست (کال سنتر)
# ============================================================

@login_required
def properties_without_supervisor(request):
    """
    نمایش لیست املاکی که سرپرست ندارند
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "properties_without_supervisor")
    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    properties = Property.objects.filter(
        is_active=True,
        status__in=[Property.Status.PENDING]
    ).select_related(
        'property_type',
        'province',
        'city',
        'neighborhood',
        'owner',
        'created_by'
    ).prefetch_related(
        'usage_types',
        'requirements'
    ).order_by('-created_at')

    from estate.views_duplicate import check_property_duplicate_logic

    properties_with_duplicate = []
    for prop in properties:
        property_data = {
            'address': prop.address or '',
            'province_id': str(prop.province_id) if prop.province_id else None,
            'city_id': str(prop.city_id) if prop.city_id else None,
            'neighborhood_id': str(prop.neighborhood_id) if prop.neighborhood_id else None,
            'property_type_id': str(prop.property_type_id) if prop.property_type_id else None,
            'area': str(prop.area) if prop.area else None,
            'price': str(prop.price) if prop.price else None,
            'rent_price': str(prop.rent_price) if prop.rent_price else None,
            'rooms': prop.rooms,
            'contract_type': prop.contract_type,
        }

        duplicate_result = check_property_duplicate_logic(
            property_data,
            property_id=str(prop.id)
        )

        filtered_duplicates = []
        for dup in duplicate_result.get('duplicates', []):
            if dup['id'] != str(prop.id):
                filtered_duplicates.append(dup)

        prop.duplicate_info = {
            'has_duplicate': len(filtered_duplicates) > 0,
            'duplicates': filtered_duplicates[:5],
            'count': len(filtered_duplicates),
            'check_id': duplicate_result.get('duplicate_check_id')
        }

        properties_with_duplicate.append(prop)

    search = request.GET.get('search', '')
    if search:
        properties_with_duplicate = [p for p in properties_with_duplicate if
                                     search.lower() in (p.title or '').lower() or
                                     search.lower() in (p.address or '').lower() or
                                     search.lower() in (p.owner_name or '').lower() or
                                     search.lower() in (p.display_code or '').lower()
                                     ]

    property_type_filter = request.GET.get('property_type', '')
    if property_type_filter:
        properties_with_duplicate = [p for p in properties_with_duplicate if
                                     str(p.property_type_id) == property_type_filter]

    contract_type = request.GET.get('contract_type', '')
    if contract_type:
        properties_with_duplicate = [p for p in properties_with_duplicate if p.contract_type == contract_type]

    duplicate_filter = request.GET.get('duplicate_filter', '')
    if duplicate_filter == 'has_duplicate':
        properties_with_duplicate = [p for p in properties_with_duplicate if p.duplicate_info['has_duplicate']]
    elif duplicate_filter == 'no_duplicate':
        properties_with_duplicate = [p for p in properties_with_duplicate if not p.duplicate_info['has_duplicate']]

    paginator = Paginator(properties_with_duplicate, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر ملک
    for p in page_obj:
        p.created_at_shamsi = get_shamsi_date(p.created_at)
        p.updated_at_shamsi = get_shamsi_date(p.updated_at)

    total = len(properties_with_duplicate)
    has_dup_count = len([p for p in properties_with_duplicate if p.duplicate_info['has_duplicate']])

    stats = {
        'total': total,
        'pending': len([p for p in properties_with_duplicate if p.status == Property.Status.PENDING]),
        'without_supervisor': len([p for p in properties_with_duplicate if p.supervisor is None]),
        'has_duplicate': has_dup_count,
        'no_duplicate': total - has_dup_count,
        'sale': len([p for p in properties_with_duplicate if p.contract_type == Property.ContractType.SALE]),
        'rent': len([p for p in properties_with_duplicate if p.contract_type == Property.ContractType.RENT]),
    }

    supervisors = User.objects.filter(
        is_active=True,
        user_roles__role__name='supervisor',
        user_roles__is_active=True
    ).annotate(
        experts_count=Count('subordinates', filter=Q(subordinates__is_active=True))
    ).order_by('first_name', 'last_name')

    assigned_experts = User.objects.filter(
        is_active=True,
        user_roles__role__name='expert',
        user_roles__is_active=True,
        referral__isnull=False
    ).distinct().order_by('first_name', 'last_name')

    property_types = PropertyType.objects.filter(is_active=True).order_by('name')

    context = {
        'properties': page_obj,
        'stats': stats,
        'supervisors': supervisors,
        'assigned_experts': assigned_experts,
        'property_types': property_types,
        'search': search,
        'property_type_filter': property_type_filter,
        'contract_type': contract_type,
        'duplicate_filter': duplicate_filter,
        'title': 'مدیریت فایل‌های بدون سرپرست',
        'userId': user.id,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'workflow/properties_without_supervisor.html', context)


@login_required
def confirm_property(request):
    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        property_obj = get_object_or_404(Property, pk=property_id)
        property_obj.status = 'confirmed'
        property_obj.save()
        messages.success(request, f'فایل "{property_obj.title}" با موفقیت تایید شد.')
    return redirect('site_profile:properties_without_supervisor')


@login_required
def delete_property(request):
    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        property_obj = get_object_or_404(Property, pk=property_id)
        property_obj.soft_delete()
        messages.success(request, f'فایل "{property_obj.title}" با موفقیت حذف شد.')
    return redirect('site_profile:properties_without_supervisor')


@login_required
def assign_supervisor_to_property(request):
    """
    اختصاص سرپرست به ملک توسط کال سنتر
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "properties_without_supervisor")
    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        supervisor_id = request.POST.get('supervisor_id')

        try:
            with transaction.atomic():
                property_obj = Property.objects.get(
                    pk=property_id,
                    is_active=True,
                    supervisor__isnull=True
                )

                supervisor = User.objects.get(
                    id=supervisor_id,
                    is_active=True,
                    user_roles__role__name='supervisor',
                    user_roles__is_active=True
                )

                property_obj.supervisor = supervisor
                property_obj.status = Property.Status.CONFIRMED
                property_obj.save()

                messages.success(
                    request,
                    f'سرپرست {supervisor.get_full_name()} با موفقیت به ملک {property_obj.title} اختصاص داده شد'
                )
                return redirect('site_profile:properties_without_supervisor')

        except Property.DoesNotExist:
            messages.error(request, 'ملک مورد نظر یافت نشد یا قبلاً سرپرست به آن اختصاص داده شده است')
        except User.DoesNotExist:
            messages.error(request, 'سرپرست مورد نظر یافت نشد')
        except Exception as e:
            messages.error(request, f'خطا: {str(e)}')

    return redirect('site_profile:properties_without_supervisor')


@login_required
def edit_property_supervisor(request):
    """
    ویرایش سرپرست فایل (ملک) توسط کال سنتر
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "properties_without_supervisor")
    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        supervisor_id = request.POST.get('supervisor_id')

        try:
            with transaction.atomic():
                property_obj = Property.objects.get(
                    pk=property_id,
                    is_active=True
                )

                supervisor = User.objects.get(
                    id=supervisor_id,
                    is_active=True,
                    user_roles__role__name='supervisor',
                    user_roles__is_active=True
                )

                old_supervisor = property_obj.supervisor
                property_obj.supervisor = supervisor
                property_obj.status = Property.Status.CONFIRMED
                property_obj.save()

                old_name = old_supervisor.get_full_name() if old_supervisor else 'بدون سرپرست'
                messages.success(
                    request,
                    f'سرپرست فایل {property_obj.title} از {old_name} به {supervisor.get_full_name()} تغییر یافت'
                )
                return redirect('site_profile:properties_without_supervisor')

        except Property.DoesNotExist:
            messages.error(request, 'فایل مورد نظر یافت نشد')
        except User.DoesNotExist:
            messages.error(request, 'سرپرست مورد نظر یافت نشد')
        except Exception as e:
            messages.error(request, f'خطا: {str(e)}')

    return redirect('site_profile:properties_without_supervisor')


# ============================================================
# 📝 مدیریت یادداشت‌ها (کال سنتر)
# ============================================================

@login_required
def add_note_to_customer(request, customer_id):
    """
    افزودن یادداشت به مشتری توسط کال سنتر
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "add_note")
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    customer = get_object_or_404(Customer, pk=customer_id, is_active=True)

    title = request.POST.get('title')
    content = request.POST.get('content')
    note_type = request.POST.get('note_type', 'general')
    priority = request.POST.get('priority', 'medium')

    if not title or not content:
        return JsonResponse({'error': 'عنوان و متن یادداشت الزامی است'}, status=400)

    try:
        note = Note.objects.create(
            customer=customer,
            note_type=note_type,
            priority=priority,
            title=title,
            content=content,
            created_by=user,
        )

        return JsonResponse({
            'success': True,
            'message': 'یادداشت با موفقیت ثبت شد',
            'note_id': str(note.id)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def add_note_to_property(request, property_id):
    """
    افزودن یادداشت به ملک توسط کال سنتر
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "add_note")
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    property_obj = get_object_or_404(Property, pk=property_id, is_active=True)

    title = request.POST.get('title')
    content = request.POST.get('content')
    note_type = request.POST.get('note_type', 'general')
    priority = request.POST.get('priority', 'medium')

    if not title or not content:
        return JsonResponse({'error': 'عنوان و متن یادداشت الزامی است'}, status=400)

    try:
        note = Note.objects.create(
            property_ref=property_obj,
            note_type=note_type,
            priority=priority,
            title=title,
            content=content,
            created_by=user,
        )

        return JsonResponse({
            'success': True,
            'message': 'یادداشت با موفقیت ثبت شد',
            'note_id': str(note.id)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_notes(request, target_type, target_id):
    """
    دریافت لیست یادداشت‌های یک مشتری یا ملک
    """
    user = request.user

    if target_type == 'customer':
        notes = Note.objects.filter(
            customer_id=target_id,
            is_resolved=False
        ).select_related('created_by', 'assigned_to').order_by('-priority', '-created_at')
    elif target_type == 'property':
        notes = Note.objects.filter(
            property_ref_id=target_id,
            is_resolved=False
        ).select_related('created_by', 'assigned_to').order_by('-priority', '-created_at')
    else:
        return JsonResponse({'error': 'نوع نامعتبر'}, status=400)

    data = []
    for note in notes:
        data.append({
            'id': str(note.id),
            'title': note.title,
            'content': note.content,
            'note_type': note.get_note_type_display(),
            'priority': note.get_priority_display(),
            'priority_color': note.priority_color,
            'created_by': note.created_by.get_full_name() if note.created_by else 'سیستم',
            'created_at': get_shamsi_datetime(note.created_at),  # ✅ تاریخ شمسی
            'assigned_to': note.assigned_to.get_full_name() if note.assigned_to else '---',
        })

    return JsonResponse({
        'success': True,
        'notes': data,
        'count': len(data)
    })


@login_required
def resolve_note(request, note_id):
    """
    برطرف کردن یادداشت (بستن)
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "add_note")
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    note = get_object_or_404(Note, pk=note_id)
    note.mark_as_resolved(user)

    return JsonResponse({
        'success': True,
        'message': 'یادداشت با موفقیت برطرف شد'
    })