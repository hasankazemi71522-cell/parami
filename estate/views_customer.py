# estate/views_customer.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from account.models import User, Role, UserRole
import json
import random
import string

from case_management.utils import jalali_to_gregorian
from myclass.mydef import views_permissions
from myclass.mydef import to_shamsi_date, to_shamsi_datetime
from .models import (
    Customer, Province, City, Neighborhood,
    PropertyType, Requirement, Source, UsageType, Note,
    Orientation, UnitCondition, DocumentType, OwnershipDocumentType
)


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


def get_shamsi_time(value):
    """تبدیل تاریخ میلادی به رشته شمسی (فقط ساعت) - مثال: 14:30"""
    if not value:
        return ''
    try:
        jalali = to_shamsi_datetime(value)
        if jalali:
            return f"{jalali.hour:02d}:{jalali.minute:02d}"
    except Exception as e:
        print(f"خطا در تبدیل ساعت شمسی: {e}")
    return ''


# ============================================================
# 📋 لیست مشتریان
# ============================================================

@login_required
def customer_list(request):
    """
    نمایش لیست مشتریان با قابلیت جستجو و فیلتر پیشرفته
    + فیلترهای مدیریتی (کارشناس، سرپرست، ثبت‌کننده)
    + فیلتر بازه تاریخ ثبت (شمسی)
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "customer_list")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    # ========== بررسی نقش مدیریتی ==========
    roles = user.get_roles()
    role_list = []
    for role in roles:
        if role.role.name not in role_list:
            role_list.append(role.role.name)

    is_admin_or_callcenter = 'admin' in role_list or 'callcenter' in role_list

    # ========== کوئری پایه ==========
    if "show_all_customer_property" in perimissin_list:
        customers = Customer.objects.filter(is_active=True).select_related(
            'user', 'created_by', 'supervisor', 'expert', 'source'
        ).prefetch_related(
            'preferred_cities', 'preferred_neighborhoods',
            'preferred_property_types', 'preferred_requirements',
            'preferred_usage_types',
            'preferred_building_orientations',
            'preferred_unit_orientations',
            'preferred_unit_conditions',
            'preferred_document_types',
            'preferred_ownership_document_types'
        )
    else:
        customers = Customer.objects.filter(is_active=True, status="confirmed").select_related(
            'user', 'created_by', 'supervisor', 'expert', 'source'
        ).prefetch_related(
            'preferred_cities', 'preferred_neighborhoods',
            'preferred_property_types', 'preferred_requirements',
            'preferred_usage_types',
            'preferred_building_orientations',
            'preferred_unit_orientations',
            'preferred_unit_conditions',
            'preferred_document_types',
            'preferred_ownership_document_types'
        )

    # ========== متغیرهای فیلتر ==========
    has_filters = False
    filter_count = 0
    filter_data = {}

    # ========== جستجوی کد نمایشی ==========
    display_code = request.GET.get('display_code', '').strip()
    if display_code:
        customers = customers.filter(display_code__icontains=display_code)
        has_filters = True
        filter_count += 1

    # ========== جستجوی عمومی ==========
    search = request.GET.get('search', '')
    if search:
        customers = customers.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__mobile__icontains=search) |
            Q(user__email__icontains=search) |
            Q(alternative_phone__icontains=search) |
            Q(company_name__icontains=search) |
            Q(job_title__icontains=search) |
            Q(description__icontains=search)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر نوع مشتری ==========
    customer_type = request.GET.get('customer_type', '')
    if customer_type:
        customers = customers.filter(customer_type=customer_type)
        has_filters = True
        filter_count += 1

    # ========== فیلتر وضعیت ==========
    status = request.GET.get('status', '')
    if status:
        customers = customers.filter(status=status)
        has_filters = True
        filter_count += 1

    # ========== فیلتر منبع ==========
    source_id = request.GET.get('source', '')
    if source_id:
        customers = customers.filter(source_id=source_id)
        has_filters = True
        filter_count += 1

    # ========== فیلتر کاربری سندی (اصلی) ==========
    primary_usage = request.GET.get('primary_usage', '')
    if primary_usage:
        customers = customers.filter(primary_usage_id=primary_usage)
        has_filters = True
        filter_count += 1

    # ========== فیلتر کاربری‌های فرعی ==========
    preferred_usage_types = request.GET.getlist('preferred_usage_types')
    if preferred_usage_types:
        customers = customers.filter(preferred_usage_types__id__in=preferred_usage_types)
        has_filters = True
        filter_count += 1

    # ========== فیلتر استان ==========
    province_id = request.GET.get('province', '')
    filter_province_name = ''
    if province_id:
        customers = customers.filter(preferred_neighborhoods__city__province_id=province_id)
        has_filters = True
        filter_count += 1
        try:
            province = Province.objects.get(id=province_id)
            filter_province_name = province.name
        except:
            pass

    # ========== فیلتر شهرستان ==========
    city_id = request.GET.get('city', '')
    filter_city_name = ''
    if city_id:
        customers = customers.filter(preferred_neighborhoods__city_id=city_id)
        has_filters = True
        filter_count += 1
        try:
            city = City.objects.get(id=city_id)
            filter_city_name = city.name
        except:
            pass

    # ========== فیلتر محله ==========
    neighborhood_id = request.GET.get('neighborhood', '')
    filter_neighborhood_name = ''
    if neighborhood_id:
        customers = customers.filter(preferred_neighborhoods__id=neighborhood_id)
        has_filters = True
        filter_count += 1
        try:
            neighborhood = Neighborhood.objects.get(id=neighborhood_id)
            filter_neighborhood_name = neighborhood.name
        except:
            pass

    # ========== فیلتر بودجه خرید ==========
    budget_min = request.GET.get('budget_min', '')
    if budget_min:
        budget_min = budget_min.replace(',', '')
        customers = customers.filter(
            Q(budget_max__gte=budget_min) | Q(budget_min__gte=budget_min)
        )
        has_filters = True
        filter_count += 1

    budget_max = request.GET.get('budget_max', '')
    if budget_max:
        budget_max = budget_max.replace(',', '')
        customers = customers.filter(
            Q(budget_min__lte=budget_max) | Q(budget_max__lte=budget_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر بودجه اجاره ==========
    rent_min = request.GET.get('rent_min', '')
    if rent_min:
        rent_min = rent_min.replace(',', '')
        customers = customers.filter(
            Q(rent_max__gte=rent_min) | Q(rent_min__gte=rent_min)
        )
        has_filters = True
        filter_count += 1

    rent_max = request.GET.get('rent_max', '')
    if rent_max:
        rent_max = rent_max.replace(',', '')
        customers = customers.filter(
            Q(rent_min__lte=rent_max) | Q(rent_max__lte=rent_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر رهن ==========
    mortgage_min = request.GET.get('mortgage_min', '')
    if mortgage_min:
        mortgage_min = mortgage_min.replace(',', '')
        customers = customers.filter(
            Q(mortgage_max__gte=mortgage_min) | Q(mortgage_min__gte=mortgage_min)
        )
        has_filters = True
        filter_count += 1

    mortgage_max = request.GET.get('mortgage_max', '')
    if mortgage_max:
        mortgage_max = mortgage_max.replace(',', '')
        customers = customers.filter(
            Q(mortgage_min__lte=mortgage_max) | Q(mortgage_max__lte=mortgage_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر متراژ ==========
    min_area = request.GET.get('min_area', '')
    if min_area:
        customers = customers.filter(
            Q(max_area__gte=min_area) | Q(min_area__gte=min_area)
        )
        has_filters = True
        filter_count += 1

    max_area = request.GET.get('max_area', '')
    if max_area:
        customers = customers.filter(
            Q(min_area__lte=max_area) | Q(max_area__lte=max_area)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر تعداد اتاق ==========
    min_rooms = request.GET.get('min_rooms', '')
    if min_rooms:
        customers = customers.filter(
            Q(max_rooms__gte=min_rooms) | Q(min_rooms__gte=min_rooms)
        )
        has_filters = True
        filter_count += 1

    max_rooms = request.GET.get('max_rooms', '')
    if max_rooms:
        customers = customers.filter(
            Q(min_rooms__lte=max_rooms) | Q(max_rooms__lte=max_rooms)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر انواع ملک ==========
    property_types = request.GET.getlist('property_types')
    if property_types:
        customers = customers.filter(preferred_property_types__id__in=property_types)
        has_filters = True
        filter_count += 1

    # ========== فیلتر نیازهای خاص ==========
    requirements = request.GET.getlist('requirements')
    if requirements:
        for req in requirements:
            customers = customers.filter(preferred_requirements__id=req)
        has_filters = True
        filter_count += 1

    # ========== فیلتر اولویت ==========
    priority_min = request.GET.get('priority_min', '')
    if priority_min:
        customers = customers.filter(priority__gte=int(priority_min))
        has_filters = True
        filter_count += 1

    priority_max = request.GET.get('priority_max', '')
    if priority_max:
        customers = customers.filter(priority__lte=int(priority_max))
        has_filters = True
        filter_count += 1

    # ========== فیلتر فعال ==========
    is_active = request.GET.get('is_active', '')
    if is_active == '1':
        customers = customers.filter(is_active=True)
        has_filters = True
        filter_count += 1
    elif is_active == '0':
        customers = customers.filter(is_active=False)
        has_filters = True
        filter_count += 1

    # ========== فیلترهای جدید ==========
    preferred_min_floor = request.GET.get('preferred_min_floor', '')
    if preferred_min_floor:
        customers = customers.filter(
            Q(preferred_max_floor__gte=preferred_min_floor) |
            Q(preferred_min_floor__gte=preferred_min_floor)
        )
        has_filters = True
        filter_count += 1
    preferred_max_floor = request.GET.get('preferred_max_floor', '')
    if preferred_max_floor:
        customers = customers.filter(
            Q(preferred_min_floor__lte=preferred_max_floor) |
            Q(preferred_max_floor__lte=preferred_max_floor)
        )
        has_filters = True
        filter_count += 1

    preferred_min_total_floors = request.GET.get('preferred_min_total_floors', '')
    if preferred_min_total_floors:
        customers = customers.filter(
            Q(preferred_max_total_floors__gte=preferred_min_total_floors) |
            Q(preferred_min_total_floors__gte=preferred_min_total_floors)
        )
        has_filters = True
        filter_count += 1
    preferred_max_total_floors = request.GET.get('preferred_max_total_floors', '')
    if preferred_max_total_floors:
        customers = customers.filter(
            Q(preferred_min_total_floors__lte=preferred_max_total_floors) |
            Q(preferred_max_total_floors__lte=preferred_max_total_floors)
        )
        has_filters = True
        filter_count += 1

    preferred_min_units_per_floor = request.GET.get('preferred_min_units_per_floor', '')
    if preferred_min_units_per_floor:
        customers = customers.filter(
            Q(preferred_max_units_per_floor__gte=preferred_min_units_per_floor) |
            Q(preferred_min_units_per_floor__gte=preferred_min_units_per_floor)
        )
        has_filters = True
        filter_count += 1
    preferred_max_units_per_floor = request.GET.get('preferred_max_units_per_floor', '')
    if preferred_max_units_per_floor:
        customers = customers.filter(
            Q(preferred_min_units_per_floor__lte=preferred_max_units_per_floor) |
            Q(preferred_max_units_per_floor__lte=preferred_max_units_per_floor)
        )
        has_filters = True
        filter_count += 1

    building_orientations = request.GET.getlist('preferred_building_orientations')
    if building_orientations:
        customers = customers.filter(preferred_building_orientations__id__in=building_orientations)
        has_filters = True
        filter_count += 1

    unit_orientations = request.GET.getlist('preferred_unit_orientations')
    if unit_orientations:
        customers = customers.filter(preferred_unit_orientations__id__in=unit_orientations)
        has_filters = True
        filter_count += 1

    unit_conditions = request.GET.getlist('preferred_unit_conditions')
    if unit_conditions:
        customers = customers.filter(preferred_unit_conditions__id__in=unit_conditions)
        has_filters = True
        filter_count += 1

    need_completion_certificate = request.GET.get('need_completion_certificate', '')
    if need_completion_certificate in ['1', 'true']:
        customers = customers.filter(need_completion_certificate=True)
        has_filters = True
        filter_count += 1
    elif need_completion_certificate in ['0', 'false']:
        customers = customers.filter(need_completion_certificate=False)
        has_filters = True
        filter_count += 1

    need_document = request.GET.get('need_document', '')
    if need_document in ['1', 'true']:
        customers = customers.filter(need_document=True)
        has_filters = True
        filter_count += 1
    elif need_document in ['0', 'false']:
        customers = customers.filter(need_document=False)
        has_filters = True
        filter_count += 1

    document_types = request.GET.getlist('preferred_document_types')
    if document_types:
        customers = customers.filter(preferred_document_types__id__in=document_types)
        has_filters = True
        filter_count += 1

    ownership_document_types = request.GET.getlist('preferred_ownership_document_types')
    if ownership_document_types:
        customers = customers.filter(preferred_ownership_document_types__id__in=ownership_document_types)
        has_filters = True
        filter_count += 1

    preferred_dong_min = request.GET.get('preferred_dong_min', '')
    if preferred_dong_min:
        customers = customers.filter(
            Q(preferred_dong_max__gte=preferred_dong_min) |
            Q(preferred_dong_min__gte=preferred_dong_min)
        )
        has_filters = True
        filter_count += 1
    preferred_dong_max = request.GET.get('preferred_dong_max', '')
    if preferred_dong_max:
        customers = customers.filter(
            Q(preferred_dong_min__lte=preferred_dong_max) |
            Q(preferred_dong_max__lte=preferred_dong_max)
        )
        has_filters = True
        filter_count += 1

    # ============================================================
    # ✅ فیلترهای مدیریتی (فقط admin / callcenter)
    # ============================================================
    expert_filter = ''
    supervisor_filter = ''
    created_by_filter = ''

    if is_admin_or_callcenter:
        expert_filter = request.GET.get('expert', '').strip()
        if expert_filter:
            customers = customers.filter(expert_id=expert_filter)
            has_filters = True
            filter_count += 1

        supervisor_filter = request.GET.get('supervisor', '').strip()
        if supervisor_filter:
            customers = customers.filter(supervisor_id=supervisor_filter)
            has_filters = True
            filter_count += 1

        created_by_filter = request.GET.get('created_by', '').strip()
        if created_by_filter:
            customers = customers.filter(created_by_id=created_by_filter)
            has_filters = True
            filter_count += 1

    # ============================================================
    # ✅ فیلتر بازه تاریخ ثبت (شمسی → میلادی)
    # ============================================================
    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    if date_from_str:
        try:
            date_from = jalali_to_gregorian(date_from_str)
            customers = customers.filter(created_at__date__gte=date_from.date())
            has_filters = True
            filter_count += 1
        except ValueError:
            messages.warning(request, f'تاریخ شروع نامعتبر است: {date_from_str}')

    if date_to_str:
        try:
            date_to = jalali_to_gregorian(date_to_str)
            date_to = date_to.replace(hour=23, minute=59, second=59)
            customers = customers.filter(created_at__lte=date_to)
            has_filters = True
            filter_count += 1
        except ValueError:
            messages.warning(request, f'تاریخ پایان نامعتبر است: {date_to_str}')

    # ========== حذف موارد تکراری ==========
    customers = customers.distinct()

    # ========== مرتب‌سازی ==========
    sort_by = request.GET.get('sort', '-priority')
    allowed_sorts = ['priority', '-priority', 'created_at', '-created_at',
                     'user__first_name', '-user__first_name', 'status', '-status',
                     'display_code', '-display_code']
    if sort_by in allowed_sorts:
        customers = customers.order_by(sort_by)
    else:
        customers = customers.order_by('-priority', '-created_at')

    # ========== صفحه‌بندی ==========
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر مشتری در لیست
    for c in page_obj:
        c.created_at_shamsi = get_shamsi_date(c.created_at)
        c.updated_at_shamsi = get_shamsi_date(c.updated_at)
        c.deleted_at_shamsi = get_shamsi_date(c.deleted_at)

    # ========== آمار ==========
    stats = {
        'total': Customer.objects.all().count(),
        'confirmed': Customer.objects.filter(status="confirmed").count(),
        'assigned': Customer.objects.filter(status="assigned").count(),
        'waiting': Customer.objects.filter(status="waiting").count(),
        'deposit': Customer.objects.filter(status="deposit").count(),
        'contract': Customer.objects.filter(status="contract").count(),
        'cancelled': Customer.objects.filter(status="cancelled").count(),
    }

    # ========== لیست‌ها برای نمایش در فیلتر ==========
    sources = Source.objects.filter(is_active=True).order_by('category', 'order', 'name')
    property_types_all = PropertyType.objects.filter(is_active=True).order_by('order', 'name')
    requirements_all = Requirement.objects.filter(is_active=True).order_by('category', 'order', 'name')
    usage_types_all = UsageType.objects.filter(is_active=True).order_by('order', 'name')
    provinces_all = Province.objects.all().order_by('name')

    orientations_all = Orientation.objects.filter(is_active=True).order_by('order', 'name')
    unit_conditions_all = UnitCondition.objects.filter(is_active=True).order_by('order', 'name')
    document_types_all = DocumentType.objects.filter(is_active=True).order_by('order', 'name')
    ownership_document_types_all = OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name')

    # ========== لیست کارشناسان، سرپرستان و ثبت‌کنندگان ==========
    experts = []
    supervisors = []
    creators = []

    if is_admin_or_callcenter:
        experts = User.objects.filter(
            customers_experted__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

        supervisors = User.objects.filter(
            customers_supervised__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

        creators = User.objects.filter(
            customers_created__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

    context = {
        'customers': page_obj,
        'stats': stats,
        'sources': sources,
        'property_types': property_types_all,
        'requirements': requirements_all,
        'usage_types': usage_types_all,
        'provinces': provinces_all,
        'orientations': orientations_all,
        'unit_conditions': unit_conditions_all,
        'document_types': document_types_all,
        'ownership_document_types': ownership_document_types_all,

        # ✅ فیلترهای مدیریتی
        'experts': experts,
        'supervisors': supervisors,
        'creators': creators,
        'is_admin_or_callcenter': is_admin_or_callcenter,

        'title': 'لیست مشتریان',
        'userId': request.user.id,
        'this_user': request.user,
        'total_count': customers.count(),
        'sort_by': sort_by,
        'has_filters': has_filters,
        'filter_count': filter_count,

        'filter_display_code': display_code,
        'filter_search': search,
        'filter_customer_type': customer_type,
        'filter_status': status,
        'filter_source': source_id,
        'filter_primary_usage': primary_usage,
        'filter_preferred_usage_types': request.GET.getlist('preferred_usage_types'),
        'filter_is_active': is_active,
        'filter_priority_min': priority_min,
        'filter_priority_max': priority_max,
        'filter_province': province_id,
        'filter_province_name': filter_province_name,
        'filter_city': city_id,
        'filter_city_name': filter_city_name,
        'filter_neighborhood': neighborhood_id,
        'filter_neighborhood_name': filter_neighborhood_name,
        'filter_budget_min': budget_min,
        'filter_budget_max': budget_max,
        'filter_rent_min': rent_min,
        'filter_rent_max': rent_max,
        'filter_mortgage_min': mortgage_min,
        'filter_mortgage_max': mortgage_max,
        'filter_min_area': min_area,
        'filter_max_area': max_area,
        'filter_min_rooms': min_rooms,
        'filter_max_rooms': max_rooms,
        'filter_property_types': request.GET.getlist('property_types'),
        'filter_requirements': request.GET.getlist('requirements'),

        'filter_preferred_min_floor': preferred_min_floor,
        'filter_preferred_max_floor': preferred_max_floor,
        'filter_preferred_min_total_floors': preferred_min_total_floors,
        'filter_preferred_max_total_floors': preferred_max_total_floors,
        'filter_preferred_min_units_per_floor': preferred_min_units_per_floor,
        'filter_preferred_max_units_per_floor': preferred_max_units_per_floor,
        'filter_preferred_building_orientations': request.GET.getlist('preferred_building_orientations'),
        'filter_preferred_unit_orientations': request.GET.getlist('preferred_unit_orientations'),
        'filter_preferred_unit_conditions': request.GET.getlist('preferred_unit_conditions'),
        'filter_need_completion_certificate': need_completion_certificate,
        'filter_need_document': need_document,
        'filter_preferred_document_types': request.GET.getlist('preferred_document_types'),
        'filter_preferred_ownership_document_types': request.GET.getlist('preferred_ownership_document_types'),
        'filter_preferred_dong_min': preferred_dong_min,
        'filter_preferred_dong_max': preferred_dong_max,

        # ✅ فیلترهای مدیریتی در context
        'filter_expert': expert_filter,
        'filter_supervisor': supervisor_filter,
        'filter_created_by': created_by_filter,

        # ✅ بازه تاریخ
        'filter_date_from': date_from_str,
        'filter_date_to': date_to_str,

        'customer_types': Customer.CustomerType.choices,
        'statuses': Customer.Status.choices,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/customer/customer_list.html', context)

# ============================================================
#  📋 لیست مشتریان ثبتی من
# ============================================================

@login_required
def my_create_customer(request):
    """
    نمایش لیست مشتریان ثبت‌شده توسط کاربر جاری
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "customer_list")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    customers = Customer.objects.filter(created_by=request.user).select_related(
        'user', 'created_by', 'source'
    ).prefetch_related(
        'preferred_cities', 'preferred_neighborhoods',
        'preferred_property_types', 'preferred_requirements',
        'preferred_usage_types',
        'preferred_building_orientations',
        'preferred_unit_orientations',
        'preferred_unit_conditions',
        'preferred_document_types',
        'preferred_ownership_document_types'
    )

    # ========== متغیرهای فیلتر ==========
    has_filters = False
    filter_count = 0

    # ========== جستجوی کد نمایشی ==========
    display_code = request.GET.get('display_code', '').strip()
    if display_code:
        customers = customers.filter(display_code__icontains=display_code)
        has_filters = True
        filter_count += 1

    # ========== جستجوی عمومی ==========
    search = request.GET.get('search', '')
    if search:
        customers = customers.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__mobile__icontains=search) |
            Q(user__email__icontains=search) |
            Q(alternative_phone__icontains=search) |
            Q(company_name__icontains=search) |
            Q(job_title__icontains=search) |
            Q(description__icontains=search)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر نوع مشتری ==========
    customer_type = request.GET.get('customer_type', '')
    if customer_type:
        customers = customers.filter(customer_type=customer_type)
        has_filters = True
        filter_count += 1

    # ========== فیلتر وضعیت ==========
    status = request.GET.get('status', '')
    if status:
        customers = customers.filter(status=status)
        has_filters = True
        filter_count += 1

    # ========== فیلتر منبع ==========
    source_id = request.GET.get('source', '')
    if source_id:
        customers = customers.filter(source_id=source_id)
        has_filters = True
        filter_count += 1

    # ========== فیلتر کاربری سندی ==========
    primary_usage = request.GET.get('primary_usage', '')
    if primary_usage:
        customers = customers.filter(primary_usage_id=primary_usage)
        has_filters = True
        filter_count += 1

    # ========== فیلتر کاربری‌های فرعی ==========
    preferred_usage_types = request.GET.getlist('preferred_usage_types')
    if preferred_usage_types:
        customers = customers.filter(preferred_usage_types__id__in=preferred_usage_types)
        has_filters = True
        filter_count += 1

    # ========== فیلتر استان ==========
    province_id = request.GET.get('province', '')
    filter_province_name = ''
    if province_id:
        customers = customers.filter(preferred_neighborhoods__city__province_id=province_id)
        has_filters = True
        filter_count += 1
        try:
            province = Province.objects.get(id=province_id)
            filter_province_name = province.name
        except:
            pass

    # ========== فیلتر شهرستان ==========
    city_id = request.GET.get('city', '')
    filter_city_name = ''
    if city_id:
        customers = customers.filter(preferred_neighborhoods__city_id=city_id)
        has_filters = True
        filter_count += 1
        try:
            city = City.objects.get(id=city_id)
            filter_city_name = city.name
        except:
            pass

    # ========== فیلتر محله ==========
    neighborhood_id = request.GET.get('neighborhood', '')
    filter_neighborhood_name = ''
    if neighborhood_id:
        customers = customers.filter(preferred_neighborhoods__id=neighborhood_id)
        has_filters = True
        filter_count += 1
        try:
            neighborhood = Neighborhood.objects.get(id=neighborhood_id)
            filter_neighborhood_name = neighborhood.name
        except:
            pass

    # ========== فیلتر بودجه خرید ==========
    budget_min = request.GET.get('budget_min', '')
    if budget_min:
        budget_min = budget_min.replace(',', '')
        customers = customers.filter(
            Q(budget_max__gte=budget_min) | Q(budget_min__gte=budget_min)
        )
        has_filters = True
        filter_count += 1

    budget_max = request.GET.get('budget_max', '')
    if budget_max:
        budget_max = budget_max.replace(',', '')
        customers = customers.filter(
            Q(budget_min__lte=budget_max) | Q(budget_max__lte=budget_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر بودجه اجاره ==========
    rent_min = request.GET.get('rent_min', '')
    if rent_min:
        rent_min = rent_min.replace(',', '')
        customers = customers.filter(
            Q(rent_max__gte=rent_min) | Q(rent_min__gte=rent_min)
        )
        has_filters = True
        filter_count += 1

    rent_max = request.GET.get('rent_max', '')
    if rent_max:
        rent_max = rent_max.replace(',', '')
        customers = customers.filter(
            Q(rent_min__lte=rent_max) | Q(rent_max__lte=rent_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر رهن ==========
    mortgage_min = request.GET.get('mortgage_min', '')
    if mortgage_min:
        mortgage_min = mortgage_min.replace(',', '')
        customers = customers.filter(
            Q(mortgage_max__gte=mortgage_min) | Q(mortgage_min__gte=mortgage_min)
        )
        has_filters = True
        filter_count += 1

    mortgage_max = request.GET.get('mortgage_max', '')
    if mortgage_max:
        mortgage_max = mortgage_max.replace(',', '')
        customers = customers.filter(
            Q(mortgage_min__lte=mortgage_max) | Q(mortgage_max__lte=mortgage_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر متراژ ==========
    min_area = request.GET.get('min_area', '')
    if min_area:
        customers = customers.filter(
            Q(max_area__gte=min_area) | Q(min_area__gte=min_area)
        )
        has_filters = True
        filter_count += 1

    max_area = request.GET.get('max_area', '')
    if max_area:
        customers = customers.filter(
            Q(min_area__lte=max_area) | Q(max_area__lte=max_area)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر تعداد اتاق ==========
    min_rooms = request.GET.get('min_rooms', '')
    if min_rooms:
        customers = customers.filter(
            Q(max_rooms__gte=min_rooms) | Q(min_rooms__gte=min_rooms)
        )
        has_filters = True
        filter_count += 1

    max_rooms = request.GET.get('max_rooms', '')
    if max_rooms:
        customers = customers.filter(
            Q(min_rooms__lte=max_rooms) | Q(max_rooms__lte=max_rooms)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر انواع ملک ==========
    property_types = request.GET.getlist('property_types')
    if property_types:
        customers = customers.filter(preferred_property_types__id__in=property_types)
        has_filters = True
        filter_count += 1

    # ========== فیلتر نیازهای خاص ==========
    requirements = request.GET.getlist('requirements')
    if requirements:
        for req in requirements:
            customers = customers.filter(preferred_requirements__id=req)
        has_filters = True
        filter_count += 1

    # ========== فیلتر اولویت ==========
    priority_min = request.GET.get('priority_min', '')
    if priority_min:
        customers = customers.filter(priority__gte=int(priority_min))
        has_filters = True
        filter_count += 1

    priority_max = request.GET.get('priority_max', '')
    if priority_max:
        customers = customers.filter(priority__lte=int(priority_max))
        has_filters = True
        filter_count += 1

    # ========== فیلتر فعال ==========
    is_active = request.GET.get('is_active', '')
    if is_active == '1':
        customers = customers.filter(is_active=True)
        has_filters = True
        filter_count += 1
    elif is_active == '0':
        customers = customers.filter(is_active=False)
        has_filters = True
        filter_count += 1

    # ========== 🆕 فیلترهای جدید ==========
    preferred_min_floor = request.GET.get('preferred_min_floor', '')
    if preferred_min_floor:
        customers = customers.filter(
            Q(preferred_max_floor__gte=preferred_min_floor) |
            Q(preferred_min_floor__gte=preferred_min_floor)
        )
        has_filters = True
        filter_count += 1
    preferred_max_floor = request.GET.get('preferred_max_floor', '')
    if preferred_max_floor:
        customers = customers.filter(
            Q(preferred_min_floor__lte=preferred_max_floor) |
            Q(preferred_max_floor__lte=preferred_max_floor)
        )
        has_filters = True
        filter_count += 1

    preferred_min_total_floors = request.GET.get('preferred_min_total_floors', '')
    if preferred_min_total_floors:
        customers = customers.filter(
            Q(preferred_max_total_floors__gte=preferred_min_total_floors) |
            Q(preferred_min_total_floors__gte=preferred_min_total_floors)
        )
        has_filters = True
        filter_count += 1
    preferred_max_total_floors = request.GET.get('preferred_max_total_floors', '')
    if preferred_max_total_floors:
        customers = customers.filter(
            Q(preferred_min_total_floors__lte=preferred_max_total_floors) |
            Q(preferred_max_total_floors__lte=preferred_max_total_floors)
        )
        has_filters = True
        filter_count += 1

    preferred_min_units_per_floor = request.GET.get('preferred_min_units_per_floor', '')
    if preferred_min_units_per_floor:
        customers = customers.filter(
            Q(preferred_max_units_per_floor__gte=preferred_min_units_per_floor) |
            Q(preferred_min_units_per_floor__gte=preferred_min_units_per_floor)
        )
        has_filters = True
        filter_count += 1
    preferred_max_units_per_floor = request.GET.get('preferred_max_units_per_floor', '')
    if preferred_max_units_per_floor:
        customers = customers.filter(
            Q(preferred_min_units_per_floor__lte=preferred_max_units_per_floor) |
            Q(preferred_max_units_per_floor__lte=preferred_max_units_per_floor)
        )
        has_filters = True
        filter_count += 1

    building_orientations = request.GET.getlist('preferred_building_orientations')
    if building_orientations:
        customers = customers.filter(preferred_building_orientations__id__in=building_orientations)
        has_filters = True
        filter_count += 1

    unit_orientations = request.GET.getlist('preferred_unit_orientations')
    if unit_orientations:
        customers = customers.filter(preferred_unit_orientations__id__in=unit_orientations)
        has_filters = True
        filter_count += 1

    unit_conditions = request.GET.getlist('preferred_unit_conditions')
    if unit_conditions:
        customers = customers.filter(preferred_unit_conditions__id__in=unit_conditions)
        has_filters = True
        filter_count += 1

    need_completion_certificate = request.GET.get('need_completion_certificate', '')
    if need_completion_certificate in ['1', 'true']:
        customers = customers.filter(need_completion_certificate=True)
        has_filters = True
        filter_count += 1
    elif need_completion_certificate in ['0', 'false']:
        customers = customers.filter(need_completion_certificate=False)
        has_filters = True
        filter_count += 1

    need_document = request.GET.get('need_document', '')
    if need_document in ['1', 'true']:
        customers = customers.filter(need_document=True)
        has_filters = True
        filter_count += 1
    elif need_document in ['0', 'false']:
        customers = customers.filter(need_document=False)
        has_filters = True
        filter_count += 1

    document_types = request.GET.getlist('preferred_document_types')
    if document_types:
        customers = customers.filter(preferred_document_types__id__in=document_types)
        has_filters = True
        filter_count += 1

    ownership_document_types = request.GET.getlist('preferred_ownership_document_types')
    if ownership_document_types:
        customers = customers.filter(preferred_ownership_document_types__id__in=ownership_document_types)
        has_filters = True
        filter_count += 1

    preferred_dong_min = request.GET.get('preferred_dong_min', '')
    if preferred_dong_min:
        customers = customers.filter(
            Q(preferred_dong_max__gte=preferred_dong_min) |
            Q(preferred_dong_min__gte=preferred_dong_min)
        )
        has_filters = True
        filter_count += 1
    preferred_dong_max = request.GET.get('preferred_dong_max', '')
    if preferred_dong_max:
        customers = customers.filter(
            Q(preferred_dong_min__lte=preferred_dong_max) |
            Q(preferred_dong_max__lte=preferred_dong_max)
        )
        has_filters = True
        filter_count += 1

    # ========== حذف موارد تکراری ==========
    customers = customers.distinct()

    # ========== مرتب‌سازی ==========
    sort_by = request.GET.get('sort', '-priority')
    allowed_sorts = ['priority', '-priority', 'created_at', '-created_at',
                     'user__first_name', '-user__first_name', 'status', '-status',
                     'display_code', '-display_code']
    if sort_by in allowed_sorts:
        customers = customers.order_by(sort_by)
    else:
        customers = customers.order_by('-priority', '-created_at')

    # ========== صفحه‌بندی ==========
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر مشتری در لیست
    for c in page_obj:
        c.created_at_shamsi = get_shamsi_date(c.created_at)
        c.updated_at_shamsi = get_shamsi_date(c.updated_at)
        c.deleted_at_shamsi = get_shamsi_date(c.deleted_at)

    # ========== آمار ==========
    stats = {
        'total': Customer.objects.all().count(),
        'confirmed': Customer.objects.filter(status="confirmed").count(),
        'assigned': Customer.objects.filter(status="assigned").count(),
        'waiting': Customer.objects.filter(status="waiting").count(),
        'deposit': Customer.objects.filter(status="deposit").count(),
        'contract': Customer.objects.filter(status="contract").count(),
        'cancelled': Customer.objects.filter(status="cancelled").count(),
    }

    sources = Source.objects.filter(is_active=True).order_by('category', 'order', 'name')
    property_types_all = PropertyType.objects.filter(is_active=True).order_by('order', 'name')
    requirements_all = Requirement.objects.filter(is_active=True).order_by('category', 'order', 'name')
    usage_types_all = UsageType.objects.filter(is_active=True).order_by('order', 'name')
    provinces_all = Province.objects.all().order_by('name')

    orientations_all = Orientation.objects.filter(is_active=True).order_by('order', 'name')
    unit_conditions_all = UnitCondition.objects.filter(is_active=True).order_by('order', 'name')
    document_types_all = DocumentType.objects.filter(is_active=True).order_by('order', 'name')
    ownership_document_types_all = OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name')

    context = {
        'customers': page_obj,
        'stats': stats,
        'sources': sources,
        'property_types': property_types_all,
        'requirements': requirements_all,
        'usage_types': usage_types_all,
        'provinces': provinces_all,
        'orientations': orientations_all,
        'unit_conditions': unit_conditions_all,
        'document_types': document_types_all,
        'ownership_document_types': ownership_document_types_all,
        'title': 'لیست مشتریان',
        'userId': request.user.id,
        'this_user': request.user,
        'total_count': customers.count(),
        'sort_by': sort_by,
        'has_filters': has_filters,
        'filter_count': filter_count,

        'filter_display_code': display_code,
        'filter_search': search,
        'filter_customer_type': customer_type,
        'filter_status': status,
        'filter_source': source_id,
        'filter_primary_usage': primary_usage,
        'filter_preferred_usage_types': request.GET.getlist('preferred_usage_types'),
        'filter_is_active': is_active,
        'filter_priority_min': priority_min,
        'filter_priority_max': priority_max,
        'filter_province': province_id,
        'filter_province_name': filter_province_name,
        'filter_city': city_id,
        'filter_city_name': filter_city_name,
        'filter_neighborhood': neighborhood_id,
        'filter_neighborhood_name': filter_neighborhood_name,
        'filter_budget_min': budget_min,
        'filter_budget_max': budget_max,
        'filter_rent_min': rent_min,
        'filter_rent_max': rent_max,
        'filter_mortgage_min': mortgage_min,
        'filter_mortgage_max': mortgage_max,
        'filter_min_area': min_area,
        'filter_max_area': max_area,
        'filter_min_rooms': min_rooms,
        'filter_max_rooms': max_rooms,
        'filter_property_types': request.GET.getlist('property_types'),
        'filter_requirements': request.GET.getlist('requirements'),

        'filter_preferred_min_floor': preferred_min_floor,
        'filter_preferred_max_floor': preferred_max_floor,
        'filter_preferred_min_total_floors': preferred_min_total_floors,
        'filter_preferred_max_total_floors': preferred_max_total_floors,
        'filter_preferred_min_units_per_floor': preferred_min_units_per_floor,
        'filter_preferred_max_units_per_floor': preferred_max_units_per_floor,
        'filter_preferred_building_orientations': request.GET.getlist('preferred_building_orientations'),
        'filter_preferred_unit_orientations': request.GET.getlist('preferred_unit_orientations'),
        'filter_preferred_unit_conditions': request.GET.getlist('preferred_unit_conditions'),
        'filter_need_completion_certificate': need_completion_certificate,
        'filter_need_document': need_document,
        'filter_preferred_document_types': request.GET.getlist('preferred_document_types'),
        'filter_preferred_ownership_document_types': request.GET.getlist('preferred_ownership_document_types'),
        'filter_preferred_dong_min': preferred_dong_min,
        'filter_preferred_dong_max': preferred_dong_max,

        'customer_types': Customer.CustomerType.choices,
        'statuses': Customer.Status.choices,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/customer/my_create_customer.html', context)


# ============================================================
#  📋 لیست مشتریان زیر نظر کارشناس
# ============================================================

@login_required
def expert_customer(request):
    """
    نمایش لیست مشتریان زیر نظر کارشناس جاری
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "customer_list")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    customers = Customer.objects.filter(expert=request.user).select_related(
        'user', 'created_by', 'source'
    ).prefetch_related(
        'preferred_cities', 'preferred_neighborhoods',
        'preferred_property_types', 'preferred_requirements',
        'preferred_usage_types',
        'preferred_building_orientations',
        'preferred_unit_orientations',
        'preferred_unit_conditions',
        'preferred_document_types',
        'preferred_ownership_document_types'
    )

    # ========== متغیرهای فیلتر ==========
    has_filters = False
    filter_count = 0

    # ========== جستجوی کد نمایشی ==========
    display_code = request.GET.get('display_code', '').strip()
    if display_code:
        customers = customers.filter(display_code__icontains=display_code)
        has_filters = True
        filter_count += 1

    # ========== جستجوی عمومی ==========
    search = request.GET.get('search', '')
    if search:
        customers = customers.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__mobile__icontains=search) |
            Q(user__email__icontains=search) |
            Q(alternative_phone__icontains=search) |
            Q(company_name__icontains=search) |
            Q(job_title__icontains=search) |
            Q(description__icontains=search)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر نوع مشتری ==========
    customer_type = request.GET.get('customer_type', '')
    if customer_type:
        customers = customers.filter(customer_type=customer_type)
        has_filters = True
        filter_count += 1

    # ========== فیلتر وضعیت ==========
    status = request.GET.get('status', '')
    if status:
        customers = customers.filter(status=status)
        has_filters = True
        filter_count += 1

    # ========== فیلتر منبع ==========
    source_id = request.GET.get('source', '')
    if source_id:
        customers = customers.filter(source_id=source_id)
        has_filters = True
        filter_count += 1

    # ========== فیلتر کاربری سندی ==========
    primary_usage = request.GET.get('primary_usage', '')
    if primary_usage:
        customers = customers.filter(primary_usage_id=primary_usage)
        has_filters = True
        filter_count += 1

    # ========== فیلتر کاربری‌های فرعی ==========
    preferred_usage_types = request.GET.getlist('preferred_usage_types')
    if preferred_usage_types:
        customers = customers.filter(preferred_usage_types__id__in=preferred_usage_types)
        has_filters = True
        filter_count += 1

    # ========== فیلتر استان ==========
    province_id = request.GET.get('province', '')
    filter_province_name = ''
    if province_id:
        customers = customers.filter(preferred_neighborhoods__city__province_id=province_id)
        has_filters = True
        filter_count += 1
        try:
            province = Province.objects.get(id=province_id)
            filter_province_name = province.name
        except:
            pass

    # ========== فیلتر شهرستان ==========
    city_id = request.GET.get('city', '')
    filter_city_name = ''
    if city_id:
        customers = customers.filter(preferred_neighborhoods__city_id=city_id)
        has_filters = True
        filter_count += 1
        try:
            city = City.objects.get(id=city_id)
            filter_city_name = city.name
        except:
            pass

    # ========== فیلتر محله ==========
    neighborhood_id = request.GET.get('neighborhood', '')
    filter_neighborhood_name = ''
    if neighborhood_id:
        customers = customers.filter(preferred_neighborhoods__id=neighborhood_id)
        has_filters = True
        filter_count += 1
        try:
            neighborhood = Neighborhood.objects.get(id=neighborhood_id)
            filter_neighborhood_name = neighborhood.name
        except:
            pass

    # ========== فیلتر بودجه خرید ==========
    budget_min = request.GET.get('budget_min', '')
    if budget_min:
        budget_min = budget_min.replace(',', '')
        customers = customers.filter(
            Q(budget_max__gte=budget_min) | Q(budget_min__gte=budget_min)
        )
        has_filters = True
        filter_count += 1

    budget_max = request.GET.get('budget_max', '')
    if budget_max:
        budget_max = budget_max.replace(',', '')
        customers = customers.filter(
            Q(budget_min__lte=budget_max) | Q(budget_max__lte=budget_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر بودجه اجاره ==========
    rent_min = request.GET.get('rent_min', '')
    if rent_min:
        rent_min = rent_min.replace(',', '')
        customers = customers.filter(
            Q(rent_max__gte=rent_min) | Q(rent_min__gte=rent_min)
        )
        has_filters = True
        filter_count += 1

    rent_max = request.GET.get('rent_max', '')
    if rent_max:
        rent_max = rent_max.replace(',', '')
        customers = customers.filter(
            Q(rent_min__lte=rent_max) | Q(rent_max__lte=rent_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر رهن ==========
    mortgage_min = request.GET.get('mortgage_min', '')
    if mortgage_min:
        mortgage_min = mortgage_min.replace(',', '')
        customers = customers.filter(
            Q(mortgage_max__gte=mortgage_min) | Q(mortgage_min__gte=mortgage_min)
        )
        has_filters = True
        filter_count += 1

    mortgage_max = request.GET.get('mortgage_max', '')
    if mortgage_max:
        mortgage_max = mortgage_max.replace(',', '')
        customers = customers.filter(
            Q(mortgage_min__lte=mortgage_max) | Q(mortgage_max__lte=mortgage_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر متراژ ==========
    min_area = request.GET.get('min_area', '')
    if min_area:
        customers = customers.filter(
            Q(max_area__gte=min_area) | Q(min_area__gte=min_area)
        )
        has_filters = True
        filter_count += 1

    max_area = request.GET.get('max_area', '')
    if max_area:
        customers = customers.filter(
            Q(min_area__lte=max_area) | Q(max_area__lte=max_area)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر تعداد اتاق ==========
    min_rooms = request.GET.get('min_rooms', '')
    if min_rooms:
        customers = customers.filter(
            Q(max_rooms__gte=min_rooms) | Q(min_rooms__gte=min_rooms)
        )
        has_filters = True
        filter_count += 1

    max_rooms = request.GET.get('max_rooms', '')
    if max_rooms:
        customers = customers.filter(
            Q(min_rooms__lte=max_rooms) | Q(max_rooms__lte=max_rooms)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر انواع ملک ==========
    property_types = request.GET.getlist('property_types')
    if property_types:
        customers = customers.filter(preferred_property_types__id__in=property_types)
        has_filters = True
        filter_count += 1

    # ========== فیلتر نیازهای خاص ==========
    requirements = request.GET.getlist('requirements')
    if requirements:
        for req in requirements:
            customers = customers.filter(preferred_requirements__id=req)
        has_filters = True
        filter_count += 1

    # ========== فیلتر اولویت ==========
    priority_min = request.GET.get('priority_min', '')
    if priority_min:
        customers = customers.filter(priority__gte=int(priority_min))
        has_filters = True
        filter_count += 1

    priority_max = request.GET.get('priority_max', '')
    if priority_max:
        customers = customers.filter(priority__lte=int(priority_max))
        has_filters = True
        filter_count += 1

    # ========== فیلتر فعال ==========
    is_active = request.GET.get('is_active', '')
    if is_active == '1':
        customers = customers.filter(is_active=True)
        has_filters = True
        filter_count += 1
    elif is_active == '0':
        customers = customers.filter(is_active=False)
        has_filters = True
        filter_count += 1

    # ========== 🆕 فیلترهای جدید ==========
    preferred_min_floor = request.GET.get('preferred_min_floor', '')
    if preferred_min_floor:
        customers = customers.filter(
            Q(preferred_max_floor__gte=preferred_min_floor) |
            Q(preferred_min_floor__gte=preferred_min_floor)
        )
        has_filters = True
        filter_count += 1
    preferred_max_floor = request.GET.get('preferred_max_floor', '')
    if preferred_max_floor:
        customers = customers.filter(
            Q(preferred_min_floor__lte=preferred_max_floor) |
            Q(preferred_max_floor__lte=preferred_max_floor)
        )
        has_filters = True
        filter_count += 1

    preferred_min_total_floors = request.GET.get('preferred_min_total_floors', '')
    if preferred_min_total_floors:
        customers = customers.filter(
            Q(preferred_max_total_floors__gte=preferred_min_total_floors) |
            Q(preferred_min_total_floors__gte=preferred_min_total_floors)
        )
        has_filters = True
        filter_count += 1
    preferred_max_total_floors = request.GET.get('preferred_max_total_floors', '')
    if preferred_max_total_floors:
        customers = customers.filter(
            Q(preferred_min_total_floors__lte=preferred_max_total_floors) |
            Q(preferred_max_total_floors__lte=preferred_max_total_floors)
        )
        has_filters = True
        filter_count += 1

    preferred_min_units_per_floor = request.GET.get('preferred_min_units_per_floor', '')
    if preferred_min_units_per_floor:
        customers = customers.filter(
            Q(preferred_max_units_per_floor__gte=preferred_min_units_per_floor) |
            Q(preferred_min_units_per_floor__gte=preferred_min_units_per_floor)
        )
        has_filters = True
        filter_count += 1
    preferred_max_units_per_floor = request.GET.get('preferred_max_units_per_floor', '')
    if preferred_max_units_per_floor:
        customers = customers.filter(
            Q(preferred_min_units_per_floor__lte=preferred_max_units_per_floor) |
            Q(preferred_max_units_per_floor__lte=preferred_max_units_per_floor)
        )
        has_filters = True
        filter_count += 1

    building_orientations = request.GET.getlist('preferred_building_orientations')
    if building_orientations:
        customers = customers.filter(preferred_building_orientations__id__in=building_orientations)
        has_filters = True
        filter_count += 1

    unit_orientations = request.GET.getlist('preferred_unit_orientations')
    if unit_orientations:
        customers = customers.filter(preferred_unit_orientations__id__in=unit_orientations)
        has_filters = True
        filter_count += 1

    unit_conditions = request.GET.getlist('preferred_unit_conditions')
    if unit_conditions:
        customers = customers.filter(preferred_unit_conditions__id__in=unit_conditions)
        has_filters = True
        filter_count += 1

    need_completion_certificate = request.GET.get('need_completion_certificate', '')
    if need_completion_certificate in ['1', 'true']:
        customers = customers.filter(need_completion_certificate=True)
        has_filters = True
        filter_count += 1
    elif need_completion_certificate in ['0', 'false']:
        customers = customers.filter(need_completion_certificate=False)
        has_filters = True
        filter_count += 1

    need_document = request.GET.get('need_document', '')
    if need_document in ['1', 'true']:
        customers = customers.filter(need_document=True)
        has_filters = True
        filter_count += 1
    elif need_document in ['0', 'false']:
        customers = customers.filter(need_document=False)
        has_filters = True
        filter_count += 1

    document_types = request.GET.getlist('preferred_document_types')
    if document_types:
        customers = customers.filter(preferred_document_types__id__in=document_types)
        has_filters = True
        filter_count += 1

    ownership_document_types = request.GET.getlist('preferred_ownership_document_types')
    if ownership_document_types:
        customers = customers.filter(preferred_ownership_document_types__id__in=ownership_document_types)
        has_filters = True
        filter_count += 1

    preferred_dong_min = request.GET.get('preferred_dong_min', '')
    if preferred_dong_min:
        customers = customers.filter(
            Q(preferred_dong_max__gte=preferred_dong_min) |
            Q(preferred_dong_min__gte=preferred_dong_min)
        )
        has_filters = True
        filter_count += 1
    preferred_dong_max = request.GET.get('preferred_dong_max', '')
    if preferred_dong_max:
        customers = customers.filter(
            Q(preferred_dong_min__lte=preferred_dong_max) |
            Q(preferred_dong_max__lte=preferred_dong_max)
        )
        has_filters = True
        filter_count += 1

    # ========== حذف موارد تکراری ==========
    customers = customers.distinct()

    # ========== مرتب‌سازی ==========
    sort_by = request.GET.get('sort', '-priority')
    allowed_sorts = ['priority', '-priority', 'created_at', '-created_at',
                     'user__first_name', '-user__first_name', 'status', '-status',
                     'display_code', '-display_code']
    if sort_by in allowed_sorts:
        customers = customers.order_by(sort_by)
    else:
        customers = customers.order_by('-priority', '-created_at')

    # ========== صفحه‌بندی ==========
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر مشتری در لیست
    for c in page_obj:
        c.created_at_shamsi = get_shamsi_date(c.created_at)
        c.updated_at_shamsi = get_shamsi_date(c.updated_at)
        c.deleted_at_shamsi = get_shamsi_date(c.deleted_at)

    # ========== آمار ==========
    stats = {
        'total': Customer.objects.all().count(),
        'confirmed': Customer.objects.filter(status="confirmed").count(),
        'assigned': Customer.objects.filter(status="assigned").count(),
        'waiting': Customer.objects.filter(status="waiting").count(),
        'deposit': Customer.objects.filter(status="deposit").count(),
        'contract': Customer.objects.filter(status="contract").count(),
        'cancelled': Customer.objects.filter(status="cancelled").count(),
    }

    sources = Source.objects.filter(is_active=True).order_by('category', 'order', 'name')
    property_types_all = PropertyType.objects.filter(is_active=True).order_by('order', 'name')
    requirements_all = Requirement.objects.filter(is_active=True).order_by('category', 'order', 'name')
    usage_types_all = UsageType.objects.filter(is_active=True).order_by('order', 'name')
    provinces_all = Province.objects.all().order_by('name')

    orientations_all = Orientation.objects.filter(is_active=True).order_by('order', 'name')
    unit_conditions_all = UnitCondition.objects.filter(is_active=True).order_by('order', 'name')
    document_types_all = DocumentType.objects.filter(is_active=True).order_by('order', 'name')
    ownership_document_types_all = OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name')

    context = {
        'customers': page_obj,
        'stats': stats,
        'sources': sources,
        'property_types': property_types_all,
        'requirements': requirements_all,
        'usage_types': usage_types_all,
        'provinces': provinces_all,
        'orientations': orientations_all,
        'unit_conditions': unit_conditions_all,
        'document_types': document_types_all,
        'ownership_document_types': ownership_document_types_all,
        'title': 'لیست مشتریان',
        'userId': request.user.id,
        'this_user': request.user,
        'total_count': customers.count(),
        'sort_by': sort_by,
        'has_filters': has_filters,
        'filter_count': filter_count,

        'filter_display_code': display_code,
        'filter_search': search,
        'filter_customer_type': customer_type,
        'filter_status': status,
        'filter_source': source_id,
        'filter_primary_usage': primary_usage,
        'filter_preferred_usage_types': request.GET.getlist('preferred_usage_types'),
        'filter_is_active': is_active,
        'filter_priority_min': priority_min,
        'filter_priority_max': priority_max,
        'filter_province': province_id,
        'filter_province_name': filter_province_name,
        'filter_city': city_id,
        'filter_city_name': filter_city_name,
        'filter_neighborhood': neighborhood_id,
        'filter_neighborhood_name': filter_neighborhood_name,
        'filter_budget_min': budget_min,
        'filter_budget_max': budget_max,
        'filter_rent_min': rent_min,
        'filter_rent_max': rent_max,
        'filter_mortgage_min': mortgage_min,
        'filter_mortgage_max': mortgage_max,
        'filter_min_area': min_area,
        'filter_max_area': max_area,
        'filter_min_rooms': min_rooms,
        'filter_max_rooms': max_rooms,
        'filter_property_types': request.GET.getlist('property_types'),
        'filter_requirements': request.GET.getlist('requirements'),

        'filter_preferred_min_floor': preferred_min_floor,
        'filter_preferred_max_floor': preferred_max_floor,
        'filter_preferred_min_total_floors': preferred_min_total_floors,
        'filter_preferred_max_total_floors': preferred_max_total_floors,
        'filter_preferred_min_units_per_floor': preferred_min_units_per_floor,
        'filter_preferred_max_units_per_floor': preferred_max_units_per_floor,
        'filter_preferred_building_orientations': request.GET.getlist('preferred_building_orientations'),
        'filter_preferred_unit_orientations': request.GET.getlist('preferred_unit_orientations'),
        'filter_preferred_unit_conditions': request.GET.getlist('preferred_unit_conditions'),
        'filter_need_completion_certificate': need_completion_certificate,
        'filter_need_document': need_document,
        'filter_preferred_document_types': request.GET.getlist('preferred_document_types'),
        'filter_preferred_ownership_document_types': request.GET.getlist('preferred_ownership_document_types'),
        'filter_preferred_dong_min': preferred_dong_min,
        'filter_preferred_dong_max': preferred_dong_max,

        'customer_types': Customer.CustomerType.choices,
        'statuses': Customer.Status.choices,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/customer/expert_customer.html', context)


# ============================================================
# 📋 لیست مشتریان حذف شده
# ============================================================

@login_required
def deactive_customer_list(request):
    """
    نمایش لیست مشتریان حذف شده
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "deactive_customer_list")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    customers = Customer.objects.filter(is_active=False).select_related(
        'user', 'created_by', 'source'
    ).prefetch_related(
        'preferred_cities', 'preferred_neighborhoods',
        'preferred_property_types', 'preferred_requirements',
        'preferred_usage_types',
        'preferred_building_orientations',
        'preferred_unit_orientations',
        'preferred_unit_conditions',
        'preferred_document_types',
        'preferred_ownership_document_types'
    )

    # ========== متغیرهای فیلتر ==========
    has_filters = False
    filter_count = 0

    # ========== جستجوی کد نمایشی ==========
    display_code = request.GET.get('display_code', '').strip()
    if display_code:
        customers = customers.filter(display_code__icontains=display_code)
        has_filters = True
        filter_count += 1

    # ========== جستجوی عمومی ==========
    search = request.GET.get('search', '')
    if search:
        customers = customers.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__mobile__icontains=search) |
            Q(user__email__icontains=search) |
            Q(alternative_phone__icontains=search) |
            Q(company_name__icontains=search) |
            Q(job_title__icontains=search) |
            Q(description__icontains=search)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر نوع مشتری ==========
    customer_type = request.GET.get('customer_type', '')
    if customer_type:
        customers = customers.filter(customer_type=customer_type)
        has_filters = True
        filter_count += 1

    # ========== فیلتر وضعیت ==========
    status = request.GET.get('status', '')
    if status:
        customers = customers.filter(status=status)
        has_filters = True
        filter_count += 1

    # ========== فیلتر منبع ==========
    source_id = request.GET.get('source', '')
    if source_id:
        customers = customers.filter(source_id=source_id)
        has_filters = True
        filter_count += 1

    # ========== فیلتر کاربری سندی ==========
    primary_usage = request.GET.get('primary_usage', '')
    if primary_usage:
        customers = customers.filter(primary_usage_id=primary_usage)
        has_filters = True
        filter_count += 1

    # ========== فیلتر کاربری‌های فرعی ==========
    preferred_usage_types = request.GET.getlist('preferred_usage_types')
    if preferred_usage_types:
        customers = customers.filter(preferred_usage_types__id__in=preferred_usage_types)
        has_filters = True
        filter_count += 1

    # ========== فیلتر استان ==========
    province_id = request.GET.get('province', '')
    filter_province_name = ''
    if province_id:
        customers = customers.filter(preferred_neighborhoods__city__province_id=province_id)
        has_filters = True
        filter_count += 1
        try:
            province = Province.objects.get(id=province_id)
            filter_province_name = province.name
        except:
            pass

    # ========== فیلتر شهرستان ==========
    city_id = request.GET.get('city', '')
    filter_city_name = ''
    if city_id:
        customers = customers.filter(preferred_neighborhoods__city_id=city_id)
        has_filters = True
        filter_count += 1
        try:
            city = City.objects.get(id=city_id)
            filter_city_name = city.name
        except:
            pass

    # ========== فیلتر محله ==========
    neighborhood_id = request.GET.get('neighborhood', '')
    filter_neighborhood_name = ''
    if neighborhood_id:
        customers = customers.filter(preferred_neighborhoods__id=neighborhood_id)
        has_filters = True
        filter_count += 1
        try:
            neighborhood = Neighborhood.objects.get(id=neighborhood_id)
            filter_neighborhood_name = neighborhood.name
        except:
            pass

    # ========== فیلتر بودجه خرید ==========
    budget_min = request.GET.get('budget_min', '')
    if budget_min:
        budget_min = budget_min.replace(',', '')
        customers = customers.filter(
            Q(budget_max__gte=budget_min) | Q(budget_min__gte=budget_min)
        )
        has_filters = True
        filter_count += 1

    budget_max = request.GET.get('budget_max', '')
    if budget_max:
        budget_max = budget_max.replace(',', '')
        customers = customers.filter(
            Q(budget_min__lte=budget_max) | Q(budget_max__lte=budget_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر بودجه اجاره ==========
    rent_min = request.GET.get('rent_min', '')
    if rent_min:
        rent_min = rent_min.replace(',', '')
        customers = customers.filter(
            Q(rent_max__gte=rent_min) | Q(rent_min__gte=rent_min)
        )
        has_filters = True
        filter_count += 1

    rent_max = request.GET.get('rent_max', '')
    if rent_max:
        rent_max = rent_max.replace(',', '')
        customers = customers.filter(
            Q(rent_min__lte=rent_max) | Q(rent_max__lte=rent_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر رهن ==========
    mortgage_min = request.GET.get('mortgage_min', '')
    if mortgage_min:
        mortgage_min = mortgage_min.replace(',', '')
        customers = customers.filter(
            Q(mortgage_max__gte=mortgage_min) | Q(mortgage_min__gte=mortgage_min)
        )
        has_filters = True
        filter_count += 1

    mortgage_max = request.GET.get('mortgage_max', '')
    if mortgage_max:
        mortgage_max = mortgage_max.replace(',', '')
        customers = customers.filter(
            Q(mortgage_min__lte=mortgage_max) | Q(mortgage_max__lte=mortgage_max)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر متراژ ==========
    min_area = request.GET.get('min_area', '')
    if min_area:
        customers = customers.filter(
            Q(max_area__gte=min_area) | Q(min_area__gte=min_area)
        )
        has_filters = True
        filter_count += 1

    max_area = request.GET.get('max_area', '')
    if max_area:
        customers = customers.filter(
            Q(min_area__lte=max_area) | Q(max_area__lte=max_area)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر تعداد اتاق ==========
    min_rooms = request.GET.get('min_rooms', '')
    if min_rooms:
        customers = customers.filter(
            Q(max_rooms__gte=min_rooms) | Q(min_rooms__gte=min_rooms)
        )
        has_filters = True
        filter_count += 1

    max_rooms = request.GET.get('max_rooms', '')
    if max_rooms:
        customers = customers.filter(
            Q(min_rooms__lte=max_rooms) | Q(max_rooms__lte=max_rooms)
        )
        has_filters = True
        filter_count += 1

    # ========== فیلتر انواع ملک ==========
    property_types = request.GET.getlist('property_types')
    if property_types:
        customers = customers.filter(preferred_property_types__id__in=property_types)
        has_filters = True
        filter_count += 1

    # ========== فیلتر نیازهای خاص ==========
    requirements = request.GET.getlist('requirements')
    if requirements:
        for req in requirements:
            customers = customers.filter(preferred_requirements__id=req)
        has_filters = True
        filter_count += 1

    # ========== فیلتر اولویت ==========
    priority_min = request.GET.get('priority_min', '')
    if priority_min:
        customers = customers.filter(priority__gte=int(priority_min))
        has_filters = True
        filter_count += 1

    priority_max = request.GET.get('priority_max', '')
    if priority_max:
        customers = customers.filter(priority__lte=int(priority_max))
        has_filters = True
        filter_count += 1

    # ========== فیلتر فعال ==========
    is_active = request.GET.get('is_active', '')
    if is_active == '1':
        customers = customers.filter(is_active=True)
        has_filters = True
        filter_count += 1
    elif is_active == '0':
        customers = customers.filter(is_active=False)
        has_filters = True
        filter_count += 1

    # ========== 🆕 فیلترهای جدید ==========
    preferred_min_floor = request.GET.get('preferred_min_floor', '')
    if preferred_min_floor:
        customers = customers.filter(
            Q(preferred_max_floor__gte=preferred_min_floor) |
            Q(preferred_min_floor__gte=preferred_min_floor)
        )
        has_filters = True
        filter_count += 1
    preferred_max_floor = request.GET.get('preferred_max_floor', '')
    if preferred_max_floor:
        customers = customers.filter(
            Q(preferred_min_floor__lte=preferred_max_floor) |
            Q(preferred_max_floor__lte=preferred_max_floor)
        )
        has_filters = True
        filter_count += 1

    preferred_min_total_floors = request.GET.get('preferred_min_total_floors', '')
    if preferred_min_total_floors:
        customers = customers.filter(
            Q(preferred_max_total_floors__gte=preferred_min_total_floors) |
            Q(preferred_min_total_floors__gte=preferred_min_total_floors)
        )
        has_filters = True
        filter_count += 1
    preferred_max_total_floors = request.GET.get('preferred_max_total_floors', '')
    if preferred_max_total_floors:
        customers = customers.filter(
            Q(preferred_min_total_floors__lte=preferred_max_total_floors) |
            Q(preferred_max_total_floors__lte=preferred_max_total_floors)
        )
        has_filters = True
        filter_count += 1

    preferred_min_units_per_floor = request.GET.get('preferred_min_units_per_floor', '')
    if preferred_min_units_per_floor:
        customers = customers.filter(
            Q(preferred_max_units_per_floor__gte=preferred_min_units_per_floor) |
            Q(preferred_min_units_per_floor__gte=preferred_min_units_per_floor)
        )
        has_filters = True
        filter_count += 1
    preferred_max_units_per_floor = request.GET.get('preferred_max_units_per_floor', '')
    if preferred_max_units_per_floor:
        customers = customers.filter(
            Q(preferred_min_units_per_floor__lte=preferred_max_units_per_floor) |
            Q(preferred_max_units_per_floor__lte=preferred_max_units_per_floor)
        )
        has_filters = True
        filter_count += 1

    building_orientations = request.GET.getlist('preferred_building_orientations')
    if building_orientations:
        customers = customers.filter(preferred_building_orientations__id__in=building_orientations)
        has_filters = True
        filter_count += 1

    unit_orientations = request.GET.getlist('preferred_unit_orientations')
    if unit_orientations:
        customers = customers.filter(preferred_unit_orientations__id__in=unit_orientations)
        has_filters = True
        filter_count += 1

    unit_conditions = request.GET.getlist('preferred_unit_conditions')
    if unit_conditions:
        customers = customers.filter(preferred_unit_conditions__id__in=unit_conditions)
        has_filters = True
        filter_count += 1

    need_completion_certificate = request.GET.get('need_completion_certificate', '')
    if need_completion_certificate in ['1', 'true']:
        customers = customers.filter(need_completion_certificate=True)
        has_filters = True
        filter_count += 1
    elif need_completion_certificate in ['0', 'false']:
        customers = customers.filter(need_completion_certificate=False)
        has_filters = True
        filter_count += 1

    need_document = request.GET.get('need_document', '')
    if need_document in ['1', 'true']:
        customers = customers.filter(need_document=True)
        has_filters = True
        filter_count += 1
    elif need_document in ['0', 'false']:
        customers = customers.filter(need_document=False)
        has_filters = True
        filter_count += 1

    document_types = request.GET.getlist('preferred_document_types')
    if document_types:
        customers = customers.filter(preferred_document_types__id__in=document_types)
        has_filters = True
        filter_count += 1

    ownership_document_types = request.GET.getlist('preferred_ownership_document_types')
    if ownership_document_types:
        customers = customers.filter(preferred_ownership_document_types__id__in=ownership_document_types)
        has_filters = True
        filter_count += 1

    preferred_dong_min = request.GET.get('preferred_dong_min', '')
    if preferred_dong_min:
        customers = customers.filter(
            Q(preferred_dong_max__gte=preferred_dong_min) |
            Q(preferred_dong_min__gte=preferred_dong_min)
        )
        has_filters = True
        filter_count += 1
    preferred_dong_max = request.GET.get('preferred_dong_max', '')
    if preferred_dong_max:
        customers = customers.filter(
            Q(preferred_dong_min__lte=preferred_dong_max) |
            Q(preferred_dong_max__lte=preferred_dong_max)
        )
        has_filters = True
        filter_count += 1

    # ========== حذف موارد تکراری ==========
    customers = customers.distinct()

    # ========== مرتب‌سازی ==========
    sort_by = request.GET.get('sort', '-priority')
    allowed_sorts = ['priority', '-priority', 'created_at', '-created_at',
                     'user__first_name', '-user__first_name', 'status', '-status',
                     'display_code', '-display_code']
    if sort_by in allowed_sorts:
        customers = customers.order_by(sort_by)
    else:
        customers = customers.order_by('-priority', '-created_at')

    # ========== صفحه‌بندی ==========
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر مشتری در لیست
    for c in page_obj:
        c.created_at_shamsi = get_shamsi_date(c.created_at)
        c.updated_at_shamsi = get_shamsi_date(c.updated_at)
        c.deleted_at_shamsi = get_shamsi_date(c.deleted_at)

    # ========== آمار ==========
    stats = {
        'total': Customer.objects.count(),
        'active': Customer.objects.filter(is_active=True).count(),
        'inactive': Customer.objects.filter(is_active=False).count(),
        'buyers': Customer.objects.filter(customer_type='buyer').count(),
        'tenants': Customer.objects.filter(customer_type='tenant').count(),
        'developers': Customer.objects.filter(customer_type='developer').count(),
        'investors': Customer.objects.filter(customer_type='investor').count(),
        'new': Customer.objects.filter(status='new').count(),
        'in_progress': Customer.objects.filter(status='in_progress').count(),
        'matched': Customer.objects.filter(status='matched').count(),
        'purchased': Customer.objects.filter(status='purchased').count(),
        'rented': Customer.objects.filter(status='rented').count(),
    }

    sources = Source.objects.filter(is_active=True).order_by('category', 'order', 'name')
    property_types_all = PropertyType.objects.filter(is_active=True).order_by('order', 'name')
    requirements_all = Requirement.objects.filter(is_active=True).order_by('category', 'order', 'name')
    usage_types_all = UsageType.objects.filter(is_active=True).order_by('order', 'name')
    provinces_all = Province.objects.all().order_by('name')

    orientations_all = Orientation.objects.filter(is_active=True).order_by('order', 'name')
    unit_conditions_all = UnitCondition.objects.filter(is_active=True).order_by('order', 'name')
    document_types_all = DocumentType.objects.filter(is_active=True).order_by('order', 'name')
    ownership_document_types_all = OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name')

    context = {
        'customers': page_obj,
        'stats': stats,
        'sources': sources,
        'property_types': property_types_all,
        'requirements': requirements_all,
        'usage_types': usage_types_all,
        'provinces': provinces_all,
        'orientations': orientations_all,
        'unit_conditions': unit_conditions_all,
        'document_types': document_types_all,
        'ownership_document_types': ownership_document_types_all,
        'title': 'لیست مشتریان حذف شده',
        'userId': request.user.id,
        'this_user': request.user,
        'total_count': customers.count(),
        'sort_by': sort_by,
        'has_filters': has_filters,
        'filter_count': filter_count,

        'filter_display_code': display_code,
        'filter_search': search,
        'filter_customer_type': customer_type,
        'filter_status': status,
        'filter_source': source_id,
        'filter_primary_usage': primary_usage,
        'filter_preferred_usage_types': request.GET.getlist('preferred_usage_types'),
        'filter_is_active': is_active,
        'filter_priority_min': priority_min,
        'filter_priority_max': priority_max,
        'filter_province': province_id,
        'filter_province_name': filter_province_name,
        'filter_city': city_id,
        'filter_city_name': filter_city_name,
        'filter_neighborhood': neighborhood_id,
        'filter_neighborhood_name': filter_neighborhood_name,
        'filter_budget_min': budget_min,
        'filter_budget_max': budget_max,
        'filter_rent_min': rent_min,
        'filter_rent_max': rent_max,
        'filter_mortgage_min': mortgage_min,
        'filter_mortgage_max': mortgage_max,
        'filter_min_area': min_area,
        'filter_max_area': max_area,
        'filter_min_rooms': min_rooms,
        'filter_max_rooms': max_rooms,
        'filter_property_types': request.GET.getlist('property_types'),
        'filter_requirements': request.GET.getlist('requirements'),

        'filter_preferred_min_floor': preferred_min_floor,
        'filter_preferred_max_floor': preferred_max_floor,
        'filter_preferred_min_total_floors': preferred_min_total_floors,
        'filter_preferred_max_total_floors': preferred_max_total_floors,
        'filter_preferred_min_units_per_floor': preferred_min_units_per_floor,
        'filter_preferred_max_units_per_floor': preferred_max_units_per_floor,
        'filter_preferred_building_orientations': request.GET.getlist('preferred_building_orientations'),
        'filter_preferred_unit_orientations': request.GET.getlist('preferred_unit_orientations'),
        'filter_preferred_unit_conditions': request.GET.getlist('preferred_unit_conditions'),
        'filter_need_completion_certificate': need_completion_certificate,
        'filter_need_document': need_document,
        'filter_preferred_document_types': request.GET.getlist('preferred_document_types'),
        'filter_preferred_ownership_document_types': request.GET.getlist('preferred_ownership_document_types'),
        'filter_preferred_dong_min': preferred_dong_min,
        'filter_preferred_dong_max': preferred_dong_max,

        'customer_types': Customer.CustomerType.choices,
        'statuses': Customer.Status.choices,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/customer/customer_list.html', context)


# ============================================================
# ➕ ثبت مشتری جدید
# ============================================================

@login_required
def customer_create(request):
    """
    ثبت مشتری جدید با پشتیبانی از انواع کاربری و فیلدهای جدید
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "customer_create")

    roles = user.get_roles()
    role_list = []
    for role in roles:
        if role.role.name not in role_list:
            role_list.append(role.role.name)

    if 'admin' in role_list or 'callcenter' in role_list:
        statuses = Customer.Status.choices
    else:
        statuses = [(Customer.Status.NEW, 'در انتظار بررسی')]

    if request.method == 'POST':
        try:
            with transaction.atomic():
                mobile = request.POST.get('mobile', '').strip()
                if not mobile:
                    messages.error(request, 'شماره موبایل الزامی است')
                    return redirect('estate:customer_create')

                user = User.objects.filter(mobile=mobile).first()

                if user:
                    user.first_name = request.POST.get('first_name', '')
                    user.last_name = request.POST.get('last_name', '')
                    user.email = request.POST.get('email', '')
                    user.save()
                else:
                    random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

                    user = User.objects.create_user(
                        username=mobile,
                        mobile=mobile,
                        first_name=request.POST.get('first_name', ''),
                        last_name=request.POST.get('last_name', ''),
                        email=request.POST.get('email', ''),
                        password=random_password
                    )

                    customer_role = Role.objects.get(name="customer")
                    request_user = request.user
                    new_user_role = UserRole(user=user, role=customer_role, assigned_by=request_user)
                    new_user_role.save()

                    if hasattr(user, 'has_role') and not user.has_role('customer'):
                        user.assign_role('customer')

                customer = Customer(user=user)

                customer.customer_type = request.POST.get('customer_type', 'buyer')
                customer.status = request.POST.get('status', 'in_progress')
                customer.priority = int(request.POST.get('priority', 0))

                customer.budget_min = request.POST.get('budget_min') or None
                customer.budget_max = request.POST.get('budget_max') or None

                customer.rent_type = request.POST.get('rent_type', 'rent')
                customer.mortgage_min = request.POST.get('mortgage_min') or None
                customer.mortgage_max = request.POST.get('mortgage_max') or None
                customer.rent_min = request.POST.get('rent_min') or None
                customer.rent_max = request.POST.get('rent_max') or None

                customer.min_area = request.POST.get('min_area') or None
                customer.max_area = request.POST.get('max_area') or None
                customer.min_rooms = request.POST.get('min_rooms') or None
                customer.max_rooms = request.POST.get('max_rooms') or None

                customer.preferred_min_floor = request.POST.get('preferred_min_floor') or None
                customer.preferred_max_floor = request.POST.get('preferred_max_floor') or None
                customer.preferred_min_total_floors = request.POST.get('preferred_min_total_floors') or None
                customer.preferred_max_total_floors = request.POST.get('preferred_max_total_floors') or None
                customer.preferred_min_units_per_floor = request.POST.get('preferred_min_units_per_floor') or None
                customer.preferred_max_units_per_floor = request.POST.get('preferred_max_units_per_floor') or None

                customer.need_completion_certificate = request.POST.get('need_completion_certificate') == 'on'
                customer.need_document = request.POST.get('need_document') == 'on'

                customer.preferred_dong_min = request.POST.get('preferred_dong_min') or None
                customer.preferred_dong_max = request.POST.get('preferred_dong_max') or None

                customer.primary_usage_id = request.POST.get('primary_usage') or None

                source_id = request.POST.get('source')
                if source_id:
                    try:
                        customer.source_id = int(source_id)
                    except:
                        customer.source = None
                else:
                    customer.source = None

                customer.description = request.POST.get('description', '')

                if not customer.created_by:
                    customer.created_by = request.user

                customer.expert = request.user
                customer.supervisor = request.user.referral

                customer.save()

                selected_cities = request.POST.get('selected_cities', '')
                if selected_cities:
                    city_ids = [int(id) for id in selected_cities.split(',') if id]
                    customer.preferred_cities.set(city_ids)
                else:
                    customer.preferred_cities.clear()

                selected_locations_json = request.POST.get('selected_locations', '[]')
                try:
                    selected_locations = json.loads(selected_locations_json)
                    neighborhood_ids = []
                    for loc in selected_locations:
                        if loc.get('neighborhood_id'):
                            neighborhood_ids.append(loc['neighborhood_id'])
                    if neighborhood_ids:
                        customer.preferred_neighborhoods.set(neighborhood_ids)
                    else:
                        customer.preferred_neighborhoods.clear()
                except:
                    customer.preferred_neighborhoods.clear()

                property_types = request.POST.getlist('preferred_property_types')
                if property_types:
                    customer.preferred_property_types.set(property_types)
                else:
                    customer.preferred_property_types.clear()

                preferred_usage_types = request.POST.getlist('preferred_usage_types')
                if preferred_usage_types:
                    customer.preferred_usage_types.set(preferred_usage_types)
                else:
                    customer.preferred_usage_types.clear()

                requirements = request.POST.getlist('preferred_requirements')
                if requirements:
                    customer.preferred_requirements.set(requirements)
                else:
                    customer.preferred_requirements.clear()

                building_orientations = request.POST.getlist('preferred_building_orientations')
                if building_orientations:
                    customer.preferred_building_orientations.set(building_orientations)
                else:
                    customer.preferred_building_orientations.clear()

                unit_orientations = request.POST.getlist('preferred_unit_orientations')
                if unit_orientations:
                    customer.preferred_unit_orientations.set(unit_orientations)
                else:
                    customer.preferred_unit_orientations.clear()

                unit_conditions = request.POST.getlist('preferred_unit_conditions')
                if unit_conditions:
                    customer.preferred_unit_conditions.set(unit_conditions)
                else:
                    customer.preferred_unit_conditions.clear()

                document_types = request.POST.getlist('preferred_document_types')
                if document_types:
                    customer.preferred_document_types.set(document_types)
                else:
                    customer.preferred_document_types.clear()

                ownership_document_types = request.POST.getlist('preferred_ownership_document_types')
                if ownership_document_types:
                    customer.preferred_ownership_document_types.set(ownership_document_types)
                else:
                    customer.preferred_ownership_document_types.clear()

                messages.success(
                    request,
                    f'✅ مشتری "{customer.full_name}" با موفقیت ثبت شد.'
                )

                return redirect('estate:customer_detail', pk=customer.id)

        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f'خطا در ثبت مشتری: {str(e)}')
            return redirect('estate:customer_create')

    # ========== GET ==========
    context = {
        'title': 'ثبت مشتری جدید',
        'is_create': True,
        'userId': request.user.id,
        'this_user': request.user,
        'customer_types': Customer.CustomerType.choices,
        'statuses': statuses,
        'rent_types': Customer.RentType.choices,
        'sources': Source.objects.filter(is_active=True).order_by('category', 'order', 'name'),
        'property_types': PropertyType.objects.filter(is_active=True).order_by('order', 'name'),
        'requirements': Requirement.objects.filter(is_active=True).order_by('category', 'order', 'name'),
        'usage_types': UsageType.objects.filter(is_active=True).order_by('order', 'name'),
        'provinces': Province.objects.all().order_by('name'),
        'orientations': Orientation.objects.filter(is_active=True).order_by('order', 'name'),
        'unit_conditions': UnitCondition.objects.filter(is_active=True).order_by('order', 'name'),
        'document_types': DocumentType.objects.filter(is_active=True).order_by('order', 'name'),
        'ownership_document_types': OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name'),
        'customer': None,
        'customer_preferred_property_types': [],
        'customer_preferred_requirements': [],
        'customer_preferred_usage_types': [],
        'customer_preferred_building_orientations': [],
        'customer_preferred_unit_orientations': [],
        'customer_preferred_unit_conditions': [],
        'customer_preferred_document_types': [],
        'customer_preferred_ownership_document_types': [],
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/customer/customer_form.html', context)

# ============================================================
# ✏️ ویرایش مشتری
# ============================================================
@login_required
def customer_edit(request, pk):
    """
    ویرایش اطلاعات مشتری
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "customer_edit")

    customer = get_object_or_404(Customer, pk=pk)
    if user == customer.user:
        permission = True

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    roles = user.get_roles()
    role_list = []
    for role in roles:
        if role.role.name not in role_list:
            role_list.append(role.role.name)

    if 'admin' in role_list or 'callcenter' in role_list:
        statuses = Customer.Status.choices
    else:
        statuses = [(Customer.Status.NEW, 'در انتظار بررسی')]

    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                user = customer.user
                user.first_name = request.POST.get('first_name', '')
                user.last_name = request.POST.get('last_name', '')
                user.email = request.POST.get('email', '')
                user.save()

                customer.customer_type = request.POST.get('customer_type', 'buyer')
                customer.status = request.POST.get('status', 'in_progress')
                customer.priority = int(request.POST.get('priority', 0))

                customer.budget_min = request.POST.get('budget_min') or None
                customer.budget_max = request.POST.get('budget_max') or None

                customer.rent_type = request.POST.get('rent_type', 'rent')
                customer.mortgage_min = request.POST.get('mortgage_min') or None
                customer.mortgage_max = request.POST.get('mortgage_max') or None
                customer.rent_min = request.POST.get('rent_min') or None
                customer.rent_max = request.POST.get('rent_max') or None

                customer.min_area = request.POST.get('min_area') or None
                customer.max_area = request.POST.get('max_area') or None
                customer.min_rooms = request.POST.get('min_rooms') or None
                customer.max_rooms = request.POST.get('max_rooms') or None

                customer.preferred_min_floor = request.POST.get('preferred_min_floor') or None
                customer.preferred_max_floor = request.POST.get('preferred_max_floor') or None
                customer.preferred_min_total_floors = request.POST.get('preferred_min_total_floors') or None
                customer.preferred_max_total_floors = request.POST.get('preferred_max_total_floors') or None
                customer.preferred_min_units_per_floor = request.POST.get('preferred_min_units_per_floor') or None
                customer.preferred_max_units_per_floor = request.POST.get('preferred_max_units_per_floor') or None

                customer.need_completion_certificate = request.POST.get('need_completion_certificate') == 'on'
                customer.need_document = request.POST.get('need_document') == 'on'

                customer.preferred_dong_min = request.POST.get('preferred_dong_min') or None
                customer.preferred_dong_max = request.POST.get('preferred_dong_max') or None

                customer.primary_usage_id = request.POST.get('primary_usage') or None

                source_id = request.POST.get('source')
                if source_id:
                    try:
                        customer.source_id = int(source_id)
                    except:
                        customer.source = None
                else:
                    customer.source = None

                customer.description = request.POST.get('description', '')
                customer.save()

                selected_cities = request.POST.get('selected_cities', '')
                if selected_cities:
                    city_ids = [int(id) for id in selected_cities.split(',') if id]
                    customer.preferred_cities.set(city_ids)
                else:
                    customer.preferred_cities.clear()

                selected_locations_json = request.POST.get('selected_locations', '[]')
                try:
                    selected_locations = json.loads(selected_locations_json)
                    neighborhood_ids = []
                    for loc in selected_locations:
                        if loc.get('neighborhood_id'):
                            neighborhood_ids.append(loc['neighborhood_id'])
                    if neighborhood_ids:
                        customer.preferred_neighborhoods.set(neighborhood_ids)
                    else:
                        customer.preferred_neighborhoods.clear()
                except:
                    customer.preferred_neighborhoods.clear()

                property_types = request.POST.getlist('preferred_property_types')
                if property_types:
                    customer.preferred_property_types.set(property_types)
                else:
                    customer.preferred_property_types.clear()

                preferred_usage_types = request.POST.getlist('preferred_usage_types')
                if preferred_usage_types:
                    customer.preferred_usage_types.set(preferred_usage_types)
                else:
                    customer.preferred_usage_types.clear()

                requirements = request.POST.getlist('preferred_requirements')
                if requirements:
                    customer.preferred_requirements.set(requirements)
                else:
                    customer.preferred_requirements.clear()

                building_orientations = request.POST.getlist('preferred_building_orientations')
                if building_orientations:
                    customer.preferred_building_orientations.set(building_orientations)
                else:
                    customer.preferred_building_orientations.clear()

                unit_orientations = request.POST.getlist('preferred_unit_orientations')
                if unit_orientations:
                    customer.preferred_unit_orientations.set(unit_orientations)
                else:
                    customer.preferred_unit_orientations.clear()

                unit_conditions = request.POST.getlist('preferred_unit_conditions')
                if unit_conditions:
                    customer.preferred_unit_conditions.set(unit_conditions)
                else:
                    customer.preferred_unit_conditions.clear()

                document_types = request.POST.getlist('preferred_document_types')
                if document_types:
                    customer.preferred_document_types.set(document_types)
                else:
                    customer.preferred_document_types.clear()

                ownership_document_types = request.POST.getlist('preferred_ownership_document_types')
                if ownership_document_types:
                    customer.preferred_ownership_document_types.set(ownership_document_types)
                else:
                    customer.preferred_ownership_document_types.clear()

                messages.success(
                    request,
                    f'✅ اطلاعات مشتری "{customer.full_name}" با موفقیت بروزرسانی شد.'
                )

                return redirect('estate:customer_detail', pk=customer.id)

        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f'خطا در بروزرسانی مشتری: {str(e)}')
            return redirect('estate:customer_edit', pk=pk)

    # ========== GET ==========
    context = {
        'title': f'ویرایش مشتری {customer.full_name}',
        'is_create': False,
        'customer': customer,
        'userId': request.user.id,
        'this_user': request.user,
        'customer_types': Customer.CustomerType.choices,
        'statuses': statuses,
        'rent_types': Customer.RentType.choices,
        'sources': Source.objects.filter(is_active=True).order_by('category', 'order', 'name'),
        'property_types': PropertyType.objects.filter(is_active=True).order_by('order', 'name'),
        'requirements': Requirement.objects.filter(is_active=True).order_by('category', 'order', 'name'),
        'usage_types': UsageType.objects.filter(is_active=True).order_by('order', 'name'),
        'provinces': Province.objects.all().order_by('name'),
        'orientations': Orientation.objects.filter(is_active=True).order_by('order', 'name'),
        'unit_conditions': UnitCondition.objects.filter(is_active=True).order_by('order', 'name'),
        'document_types': DocumentType.objects.filter(is_active=True).order_by('order', 'name'),
        'ownership_document_types': OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name'),
        'customer_preferred_property_types': list(customer.preferred_property_types.values_list('id', flat=True)),
        'customer_preferred_requirements': list(customer.preferred_requirements.values_list('id', flat=True)),
        'customer_preferred_usage_types': list(customer.preferred_usage_types.values_list('id', flat=True)),
        'customer_preferred_building_orientations': list(customer.preferred_building_orientations.values_list('id', flat=True)),
        'customer_preferred_unit_orientations': list(customer.preferred_unit_orientations.values_list('id', flat=True)),
        'customer_preferred_unit_conditions': list(customer.preferred_unit_conditions.values_list('id', flat=True)),
        'customer_preferred_document_types': list(customer.preferred_document_types.values_list('id', flat=True)),
        'customer_preferred_ownership_document_types': list(customer.preferred_ownership_document_types.values_list('id', flat=True)),
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/customer/customer_form.html', context)


# ============================================================
# 👤 جزئیات مشتری
# ============================================================

@login_required
def customer_detail(request, pk):
    """
    نمایش جزئیات کامل مشتری به همراه یادداشت‌ها
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "customer_detail")

    customer = get_object_or_404(Customer, pk=pk)
    if user == customer.user:
        permission = True

    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    customer = get_object_or_404(
        Customer.objects.select_related(
            'user', 'created_by', 'source', 'supervisor', 'expert'
        ).prefetch_related(
            'preferred_cities__province',
            'preferred_neighborhoods__city__province',
            'preferred_property_types',
            'preferred_requirements',
            'preferred_usage_types',
            'preferred_building_orientations',
            'preferred_unit_orientations',
            'preferred_unit_conditions',
            'preferred_document_types',
            'preferred_ownership_document_types'
        ),
        pk=pk,
        is_active=True
    )

    # ✅ اضافه کردن تاریخ شمسی به شیء مشتری
    customer.created_at_shamsi = get_shamsi_datetime(customer.created_at)
    customer.updated_at_shamsi = get_shamsi_datetime(customer.updated_at)
    customer.deleted_at_shamsi = get_shamsi_datetime(customer.deleted_at)
    customer.last_contact_shamsi = get_shamsi_datetime(customer.last_contact)
    if customer.user and customer.user.birth_date:
        customer.user.birth_date_shamsi = get_shamsi_date(customer.user.birth_date)
    else:
        customer.user.birth_date_shamsi = ''

    notes = Note.objects.filter(
        customer=customer,
        is_resolved=False
    ).select_related(
        'created_by',
        'assigned_to',
        'resolved_by'
    ).order_by('-priority', '-created_at')

    # ✅ اضافه کردن تاریخ شمسی به هر یادداشت
    for note in notes:
        note.created_at_shamsi = get_shamsi_datetime(note.created_at)
        note.updated_at_shamsi = get_shamsi_datetime(note.updated_at)
        note.resolved_at_shamsi = get_shamsi_datetime(note.resolved_at)

    requirements_grouped = customer.get_requirements_grouped()
    preferred_usage_types = customer.preferred_usage_types.filter(is_active=True)

    from estate.models import Match
    interactions = {
        'total': customer.total_interactions,
        'matches': Match.objects.filter(customer=customer).count(),
    }

    context = {
        'customer': customer,
        'notes': notes,
        'requirements_grouped': requirements_grouped,
        'preferred_usage_types': preferred_usage_types,
        'interactions': interactions,
        'title': f'جزئیات مشتری - {customer.full_name}',
        'userId': user.id,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'estate/customer/customer_detail.html', context)


# ============================================================
# 🗑️ حذف مشتری (نرم)
# ============================================================

@login_required
def customer_delete(request, pk):
    """
    حذف نرم مشتری
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "customer_delete")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        customer.status = "cancelled"
        customer.save()
        customer_name = customer.full_name
        customer.soft_delete()
        messages.success(
            request,
            f'✅ مشتری "{customer_name}" با موفقیت حذف شد.'
        )
        return redirect('estate:customer_list')

    # ✅ اضافه کردن تاریخ شمسی
    customer.created_at_shamsi = get_shamsi_datetime(customer.created_at)
    customer.deleted_at_shamsi = get_shamsi_datetime(customer.deleted_at)

    context = {
        'customer': customer,
        'title': f'حذف مشتری {customer.full_name}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/customer/customer_delete.html', context)


# ============================================================
# ↩️ بازیابی مشتری
# ============================================================

@login_required
def customer_restore(request, pk):
    """
    بازیابی مشتری حذف شده
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "customer_restore")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        customer.status = "confirmed"
        customer.save()
        customer.restore()
        messages.success(
            request,
            f'✅ مشتری "{customer.full_name}" با موفقیت بازیابی شد.'
        )
        return redirect('estate:deactive_customer_list')

    # ✅ اضافه کردن تاریخ شمسی
    customer.created_at_shamsi = get_shamsi_datetime(customer.created_at)
    customer.deleted_at_shamsi = get_shamsi_datetime(customer.deleted_at)

    context = {
        'customer': customer,
        'title': f'بازیابی مشتری {customer.full_name}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/customer/customer_restore.html', context)


# ============================================================
# 🔄 تغییر وضعیت مشتری (API)
# ============================================================

@login_required
def customer_change_status(request, pk):
    """
    تغییر وضعیت مشتری (API)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    customer = get_object_or_404(Customer, pk=pk)
    new_status = request.POST.get('status')

    if new_status not in dict(Customer.Status.choices):
        return JsonResponse({'error': 'وضعیت نامعتبر'}, status=400)

    customer.status = new_status
    customer.save()

    return JsonResponse({
        'success': True,
        'message': f'وضعیت مشتری به "{customer.get_status_display()}" تغییر یافت',
        'status': customer.status,
        'status_display': customer.get_status_display()
    })


# ============================================================
# 📊 آمار مشتریان (API)
# ============================================================

@login_required
def customer_stats_api(request):
    """
    دریافت آمار مشتریان به صورت JSON
    """
    stats = {
        'total': Customer.objects.count(),
        'active': Customer.objects.filter(is_active=True).count(),
        'by_type': {},
        'by_status': {},
        'by_source': {},
        'by_priority': {},
        'by_usage': {},
        'by_need_completion': {},
        'by_need_document': {},
    }

    for type_choice in Customer.CustomerType.choices:
        count = Customer.objects.filter(customer_type=type_choice[0]).count()
        stats['by_type'][type_choice[0]] = {
            'label': type_choice[1],
            'count': count
        }

    for status_choice in Customer.Status.choices:
        count = Customer.objects.filter(status=status_choice[0]).count()
        stats['by_status'][status_choice[0]] = {
            'label': status_choice[1],
            'count': count
        }

    for source in Source.objects.filter(is_active=True):
        count = Customer.objects.filter(source=source).count()
        if count > 0:
            stats['by_source'][source.name] = {
                'id': str(source.id),
                'color': source.color,
                'count': count
            }

    for priority in range(11):
        count = Customer.objects.filter(priority=priority).count()
        if count > 0:
            stats['by_priority'][priority] = count

    for usage in UsageType.objects.filter(is_active=True):
        count = Customer.objects.filter(preferred_usage_types=usage).count()
        if count > 0:
            stats['by_usage'][usage.code] = {
                'label': usage.name,
                'count': count,
                'color': usage.color,
                'icon': usage.icon
            }

    stats['by_need_completion']['yes'] = Customer.objects.filter(need_completion_certificate=True).count()
    stats['by_need_completion']['no'] = Customer.objects.filter(need_completion_certificate=False).count()

    stats['by_need_document']['yes'] = Customer.objects.filter(need_document=True).count()
    stats['by_need_document']['no'] = Customer.objects.filter(need_document=False).count()

    return JsonResponse(stats)


# ============================================================
# 🔍 جستجوی سریع مشتری (API)
# ============================================================

@login_required
def customer_search_ajax(request):
    """
    جستجوی سریع مشتری برای استفاده در AJAX
    """
    query = request.GET.get('q', '')
    limit = int(request.GET.get('limit', 10))

    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    customers = Customer.objects.select_related('user').filter(
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(user__mobile__icontains=query) |
        Q(user__email__icontains=query)
    )[:limit]

    results = []
    for customer in customers:
        results.append({
            'id': str(customer.id),
            'text': f"{customer.full_name} - {customer.mobile}",
            'full_name': customer.full_name,
            'mobile': customer.mobile,
            'type': customer.get_customer_type_display(),
            'status': customer.get_status_display(),
        })

    return JsonResponse({'results': results})


# ============================================================
# 🔍 API جستجوی شهرها
# ============================================================

@login_required
def search_city_api(request):
    """
    API جستجوی شهرها برای استفاده در فرم مشتری
    """
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    cities = City.objects.select_related('province').filter(
        Q(name__icontains=query) | Q(province__name__icontains=query)
    )[:20]

    results = []
    for city in cities:
        results.append({
            'id': city.id,
            'name': city.name,
            'province_name': city.province.name,
        })

    return JsonResponse({'results': results})


# ============================================================
# 🔍 API جستجوی محله‌ها
# ============================================================

@login_required
def search_neighborhood_api(request):
    """
    API جستجوی محله‌ها برای استفاده در فرم مشتری
    """
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    neighborhoods = Neighborhood.objects.select_related('city__province').filter(
        Q(name__icontains=query) |
        Q(city__name__icontains=query) |
        Q(city__province__name__icontains=query)
    )[:20]

    results = []
    for neighborhood in neighborhoods:
        results.append({
            'id': neighborhood.id,
            'name': neighborhood.name,
            'city_name': neighborhood.city.name,
            'province_name': neighborhood.city.province.name,
        })

    return JsonResponse({'results': results})


# ============================================================
# 📍 دریافت نام شهرها بر اساس ID
# ============================================================

@login_required
def get_cities_by_province(request):
    """
    API دریافت شهرستان‌های یک استان (برای استفاده در فرم‌ها)
    """
    province_id = request.GET.get('province_id')

    if not province_id:
        return JsonResponse({
            'success': False,
            'cities': [],
            'error': 'province_id required'
        })

    try:
        province = Province.objects.filter(id=province_id).first()
        if not province:
            return JsonResponse({
                'success': False,
                'cities': [],
                'error': 'استان مورد نظر یافت نشد'
            })

        cities = City.objects.filter(province_id=province_id).order_by('name')

        data = []
        for city in cities:
            data.append({
                'id': city.id,
                'name': city.name
            })

        return JsonResponse({
            'success': True,
            'cities': data,
            'province_name': province.name
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'cities': [],
            'error': str(e)
        })


# ============================================================
# 📍 دریافت نام شهرها بر اساس ID (برای نمایش تگ‌ها)
# ============================================================

@login_required
def get_city_names_api(request):
    """
    دریافت نام شهرها بر اساس ID برای نمایش تگ‌ها
    """
    ids = request.GET.get('ids', '')
    if not ids:
        return JsonResponse({'cities': []})

    city_ids = [int(id) for id in ids.split(',') if id]
    cities = City.objects.select_related('province').filter(id__in=city_ids)

    results = []
    for city in cities:
        results.append({
            'id': city.id,
            'name': city.name,
            'province_name': city.province.name,
        })

    return JsonResponse({'cities': results})


# ============================================================
# 📍 دریافت نام محله‌ها بر اساس ID
# ============================================================

@login_required
def get_neighborhood_names_api(request):
    """
    دریافت نام محله‌ها بر اساس ID برای نمایش تگ‌ها
    """
    ids = request.GET.get('ids', '')
    if not ids:
        return JsonResponse({'neighborhoods': []})

    neighborhood_ids = [int(id) for id in ids.split(',') if id]
    neighborhoods = Neighborhood.objects.select_related('city__province').filter(id__in=neighborhood_ids)

    results = []
    for neighborhood in neighborhoods:
        results.append({
            'id': neighborhood.id,
            'name': neighborhood.name,
            'city_name': neighborhood.city.name,
            'province_name': neighborhood.city.province.name,
        })

    return JsonResponse({'neighborhoods': results})


# ============================================================
# 📍 API دریافت محله‌های یک شهرستان
# ============================================================

@login_required
def get_neighborhoods_by_city_api(request):
    """
    دریافت محله‌های یک شهرستان
    """
    city_id = request.GET.get('city_id')

    if not city_id:
        return JsonResponse({
            'success': False,
            'error': 'city_id required'
        }, status=400)

    try:
        neighborhoods = Neighborhood.objects.filter(
            city_id=city_id
        ).order_by('name')

        results = []
        for neighborhood in neighborhoods:
            results.append({
                'id': neighborhood.id,
                'name': neighborhood.name,
            })

        return JsonResponse({
            'success': True,
            'neighborhoods': results
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)