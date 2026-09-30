# estate/views_property.py
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db import transaction, models
from django.db.models import Q, Count, Avg
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
import json
import random
import string

from account.models import User, Role, UserRole
from case_management.utils import jalali_to_gregorian
from myclass.mydef import views_permissions
from .models import (
    Province, City, Neighborhood, PropertyType, UsageType,
    Requirement, Customer, Property, PropertyImage, PropertyVideo,
    Match, Note,
    Orientation, UnitCondition, DocumentType, OwnershipDocumentType
)
from .utils_match import MatchManager
from myclass.mydef import to_shamsi_date, to_shamsi_datetime


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


def is_ajax(request):
    """بررسی اینکه درخواست AJAX است"""
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.headers.get('accept') == 'application/json'
    )


def convert_to_embed_link(link):
    """
    تبدیل لینک ویدئو به فرمت embed
    """
    link = link.strip()
    if not link:
        return link
    if link.startswith('<script') or link.startswith('<iframe'):
        return link
    if 'embed' in link:
        return link

    # آپارات
    if 'aparat.com' in link:
        video_id = None
        if '/v/' in link:
            video_id = link.split('/v/')[-1].split('/')[0].split('?')[0]
        elif 'aparat.com/' in link:
            parts = link.split('/')
            for part in parts:
                if part and len(part) > 5 and not part.startswith('www'):
                    video_id = part.split('?')[0]
                    break
        if video_id:
            return f'https://www.aparat.com/embed/{video_id}'
        return link

    # یوتیوب
    if 'youtube.com/watch?v=' in link:
        video_id = link.split('watch?v=')[-1].split('&')[0]
        return f'https://www.youtube.com/embed/{video_id}'
    if 'youtu.be/' in link:
        video_id = link.split('youtu.be/')[-1].split('/')[0].split('?')[0]
        return f'https://www.youtube.com/embed/{video_id}'

    return link


# ============================================================
# 📋 لیست املاک
# ============================================================

@login_required
def property_list(request):
    """
    لیست همه املاک با جستجو و فیلتر کامل
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "property_list")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    roles = user.get_roles()
    role_list = []
    for role in roles:
        if role.role.name not in role_list:
            role_list.append(role.role.name)

    is_admin_or_callcenter = 'admin' in role_list or 'callcenter' in role_list

    if "show_all_customer_property" in perimissin_list:
        properties = Property.objects.filter(is_active=True).select_related(
            'property_type', 'province', 'city', 'neighborhood',
            'owner', 'created_by', 'primary_usage', 'unit_condition',
            'building_orientation', 'unit_orientation',
            'document_type', 'ownership_document_type',
            'expert', 'supervisor'
        ).prefetch_related(
            'requirements', 'images', 'videos', 'usage_types'
        )
    else:
        properties = Property.objects.filter(is_active=True, status="confirmed").select_related(
            'property_type', 'province', 'city', 'neighborhood',
            'owner', 'created_by', 'primary_usage', 'unit_condition',
            'building_orientation', 'unit_orientation',
            'document_type', 'ownership_document_type',
            'expert', 'supervisor'
        ).prefetch_related(
            'requirements', 'images', 'videos', 'usage_types'
        )

    has_filters = False
    filter_count = 0

    # ---------- جستجوی کد نمایشی ----------
    display_code = request.GET.get('display_code', '').strip()
    if display_code:
        properties = properties.filter(display_code__icontains=display_code)
        has_filters = True
        filter_count += 1

    # ---------- جستجوی عمومی ----------
    search = request.GET.get('search', '')
    if search:
        properties = properties.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(address__icontains=search)
        )
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع ملک ----------
    property_type = request.GET.get('property_type', '')
    if property_type:
        properties = properties.filter(property_type_id=property_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر کاربری سندی (اصلی) ----------
    primary_usage = request.GET.get('primary_usage', '')
    if primary_usage:
        properties = properties.filter(primary_usage_id=primary_usage)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر کاربری‌های فرعی ----------
    usage_type = request.GET.get('usage_type', '')
    if usage_type:
        properties = properties.filter(usage_types__id=usage_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر وضعیت ----------
    status = request.GET.get('status', '')
    if status:
        properties = properties.filter(status=status)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع قرارداد ----------
    contract_type = request.GET.get('contract_type', '')
    if contract_type:
        properties = properties.filter(contract_type=contract_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر استان ----------
    province_id = request.GET.get('province', '')
    if province_id:
        properties = properties.filter(province_id=province_id)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر شهرستان ----------
    city_id = request.GET.get('city', '')
    filter_city_name = ''
    if city_id:
        properties = properties.filter(city_id=city_id)
        has_filters = True
        filter_count += 1
        try:
            city = City.objects.get(id=city_id)
            filter_city_name = city.name
        except City.DoesNotExist:
            pass

    # ---------- فیلتر محله (چندگزینه‌ای) ----------
    neighborhoods = request.GET.getlist('neighborhoods')
    if neighborhoods:
        properties = properties.filter(neighborhood_id__in=neighborhoods)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر قیمت ----------
    price_min = request.GET.get('price_min', '')
    if price_min:
        price_min = price_min.replace(',', '')
        properties = properties.filter(price__gte=price_min)
        has_filters = True
        filter_count += 1

    price_max = request.GET.get('price_max', '')
    if price_max:
        price_max = price_max.replace(',', '')
        properties = properties.filter(price__lte=price_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر رهن ----------
    mortgage_min = request.GET.get('mortgage_min', '')
    if mortgage_min:
        mortgage_min = mortgage_min.replace(',', '')
        properties = properties.filter(mortgage_price__gte=mortgage_min)
        has_filters = True
        filter_count += 1

    mortgage_max = request.GET.get('mortgage_max', '')
    if mortgage_max:
        mortgage_max = mortgage_max.replace(',', '')
        properties = properties.filter(mortgage_price__lte=mortgage_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر اجاره ----------
    rent_min = request.GET.get('rent_min', '')
    if rent_min:
        rent_min = rent_min.replace(',', '')
        properties = properties.filter(rent_price__gte=rent_min)
        has_filters = True
        filter_count += 1

    rent_max = request.GET.get('rent_max', '')
    if rent_max:
        rent_max = rent_max.replace(',', '')
        properties = properties.filter(rent_price__lte=rent_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر متراژ ----------
    area_min = request.GET.get('area_min', '')
    if area_min:
        properties = properties.filter(area__gte=area_min)
        has_filters = True
        filter_count += 1

    area_max = request.GET.get('area_max', '')
    if area_max:
        properties = properties.filter(area__lte=area_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر قابل مشاهده ----------
    is_visible = request.GET.get('is_visible', '')
    if is_visible == '1':
        properties = properties.filter(is_visible=True)
        has_filters = True
        filter_count += 1
    elif is_visible == '0':
        properties = properties.filter(is_visible=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر ویژه ----------
    is_featured = request.GET.get('is_featured', '')
    if is_featured == '1':
        properties = properties.filter(is_featured=True)
        has_filters = True
        filter_count += 1
    elif is_featured == '0':
        properties = properties.filter(is_featured=False)
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
            properties = properties.filter(created_at__date__gte=date_from.date())
            has_filters = True
            filter_count += 1
        except ValueError:
            messages.warning(request, f'تاریخ شروع نامعتبر است: {date_from_str}')

    if date_to_str:
        try:
            date_to = jalali_to_gregorian(date_to_str)
            # برای اینکه کل روز تا رو بگیره، 23:59:59 رو در نظر می‌گیریم
            date_to = date_to.replace(hour=23, minute=59, second=59)
            properties = properties.filter(created_at__lte=date_to)
            has_filters = True
            filter_count += 1
        except ValueError:
            messages.warning(request, f'تاریخ پایان نامعتبر است: {date_to_str}')

    # ---------- فیلترهای مدیریتی ----------
    expert_filter = ''
    supervisor_filter = ''
    created_by_filter = ''

    if is_admin_or_callcenter:
        expert_filter = request.GET.get('expert', '')
        if expert_filter:
            properties = properties.filter(expert_id=expert_filter)
            has_filters = True
            filter_count += 1

        supervisor_filter = request.GET.get('supervisor', '')
        if supervisor_filter:
            properties = properties.filter(supervisor_id=supervisor_filter)
            has_filters = True
            filter_count += 1

        created_by_filter = request.GET.get('created_by', '')
        if created_by_filter:
            properties = properties.filter(created_by_id=created_by_filter)
            has_filters = True
            filter_count += 1

    # ---------- فیلتر امکانات ملک ----------
    requirements = request.GET.getlist('requirements')
    if requirements:
        for req in requirements:
            properties = properties.filter(requirements__id=req)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر تعداد اتاق ----------
    rooms_min = request.GET.get('rooms_min', '')
    if rooms_min:
        properties = properties.filter(rooms__gte=rooms_min)
        has_filters = True
        filter_count += 1

    rooms_max = request.GET.get('rooms_max', '')
    if rooms_max:
        properties = properties.filter(rooms__lte=rooms_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر تعداد کل طبقات ----------
    total_floors_min = request.GET.get('total_floors_min', '')
    if total_floors_min:
        properties = properties.filter(total_floors__gte=total_floors_min)
        has_filters = True
        filter_count += 1

    total_floors_max = request.GET.get('total_floors_max', '')
    if total_floors_max:
        properties = properties.filter(total_floors__lte=total_floors_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر سال ساخت ----------
    built_year_min = request.GET.get('built_year_min', '')
    if built_year_min:
        properties = properties.filter(built_year__gte=built_year_min)
        has_filters = True
        filter_count += 1

    built_year_max = request.GET.get('built_year_max', '')
    if built_year_max:
        properties = properties.filter(built_year__lte=built_year_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر پارکینگ ----------
    parking_type = request.GET.get('parking_type', '')
    if parking_type:
        properties = properties.filter(parking_type=parking_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوساز ----------
    is_new_building = request.GET.get('is_new_building', '')
    if is_new_building == '1':
        properties = properties.filter(is_new_building=True)
        has_filters = True
        filter_count += 1
    elif is_new_building == '0':
        properties = properties.filter(is_new_building=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر تعداد واحد در طبقه ----------
    units_per_floor_min = request.GET.get('units_per_floor_min', '')
    if units_per_floor_min:
        properties = properties.filter(units_per_floor__gte=units_per_floor_min)
        has_filters = True
        filter_count += 1
    units_per_floor_max = request.GET.get('units_per_floor_max', '')
    if units_per_floor_max:
        properties = properties.filter(units_per_floor__lte=units_per_floor_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر جهت ساختمان ----------
    building_orientation = request.GET.get('building_orientation', '')
    if building_orientation:
        properties = properties.filter(building_orientation_id=building_orientation)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر جهت واحد ----------
    unit_orientation = request.GET.get('unit_orientation', '')
    if unit_orientation:
        properties = properties.filter(unit_orientation_id=unit_orientation)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر وضعیت واحد ----------
    unit_condition = request.GET.get('unit_condition', '')
    if unit_condition:
        properties = properties.filter(unit_condition_id=unit_condition)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر دارای پایان کار ----------
    has_completion_certificate = request.GET.get('has_completion_certificate', '')
    if has_completion_certificate == '1':
        properties = properties.filter(has_completion_certificate=True)
        has_filters = True
        filter_count += 1
    elif has_completion_certificate == '0':
        properties = properties.filter(has_completion_certificate=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر دارای سند ----------
    has_document = request.GET.get('has_document', '')
    if has_document == '1':
        properties = properties.filter(has_document=True)
        has_filters = True
        filter_count += 1
    elif has_document == '0':
        properties = properties.filter(has_document=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع سند ----------
    document_type = request.GET.get('document_type', '')
    if document_type:
        properties = properties.filter(document_type_id=document_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع مالکیت سند ----------
    ownership_document_type = request.GET.get('ownership_document_type', '')
    if ownership_document_type:
        properties = properties.filter(ownership_document_type_id=ownership_document_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر میزان دانگ ----------
    dong_min = request.GET.get('dong_min', '')
    if dong_min:
        properties = properties.filter(dong__gte=dong_min)
        has_filters = True
        filter_count += 1
    dong_max = request.GET.get('dong_max', '')
    if dong_max:
        properties = properties.filter(dong__lte=dong_max)
        has_filters = True
        filter_count += 1

    # ---------- حذف موارد تکراری ----------
    properties = properties.distinct()

    # ---------- مرتب‌سازی ----------
    sort_by = request.GET.get('sort', '-created_at')
    allowed_sorts = [
        'created_at', '-created_at', 'price', '-price',
        'area', '-area', 'title', '-title', 'status', '-status',
        'display_code', '-display_code'
    ]
    if sort_by in allowed_sorts:
        properties = properties.order_by(sort_by)
    else:
        properties = properties.order_by('-created_at')

    # ---------- صفحه‌بندی ----------
    paginator = Paginator(properties, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر ملک در لیست
    for prop in page_obj:
        prop.created_at_shamsi = get_shamsi_date(prop.created_at)
        prop.updated_at_shamsi = get_shamsi_date(prop.updated_at)
        prop.published_at_shamsi = get_shamsi_date(prop.published_at)

    # ---------- داده‌های فیلتر ----------
    provinces = Province.objects.all().order_by('name')
    property_types = PropertyType.objects.filter(is_active=True).order_by('name')
    usage_types = UsageType.objects.filter(is_active=True).order_by('order', 'name')
    requirements_all = Requirement.objects.filter(is_active=True).order_by('category', 'name')
    orientations = Orientation.objects.filter(is_active=True).order_by('order', 'name')
    unit_conditions = UnitCondition.objects.filter(is_active=True).order_by('order', 'name')
    document_types = DocumentType.objects.filter(is_active=True).order_by('order', 'name')
    ownership_document_types = OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name')

    # ---------- لیست کارشناسان، سرپرستان و ثبت‌کنندگان ----------
    experts = []
    supervisors = []
    creators = []

    if is_admin_or_callcenter:
        experts = User.objects.filter(
            properties_experted__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

        supervisors = User.objects.filter(
            properties_supervised__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

        creators = User.objects.filter(
            properties_created__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

    # ---------- آمار ----------
    property_count = Property.objects.all()
    stats = {
        'total': property_count.count(),
        'pending': property_count.filter(status='pending').count(),
        'confirmed': property_count.filter(status='confirmed').count(),
        'deposit': property_count.filter(status='deposit').count(),
        'contract': property_count.filter(status='contract').count(),
        'cancelled': property_count.filter(status='cancelled').count(),
    }

    context = {
        'properties': page_obj,
        'stats': stats,
        'provinces': provinces,
        'property_types': property_types,
        'usage_types': usage_types,
        'requirements': requirements_all,
        'orientations': orientations,
        'unit_conditions': unit_conditions,
        'document_types': document_types,
        'ownership_document_types': ownership_document_types,
        'experts': experts,
        'supervisors': supervisors,
        'creators': creators,
        'title': 'لیست املاک',
        'userId': request.user.id,
        'this_user': request.user,
        'total_count': properties.count(),
        'has_filters': has_filters,
        'filter_count': filter_count,
        'sort_by': sort_by,
        'filter_display_code': display_code,
        'filter_search': search,
        'filter_property_type': property_type,
        'filter_primary_usage': primary_usage,
        'filter_usage_type': usage_type,
        'filter_status': status,
        'filter_contract_type': contract_type,
        'filter_province': province_id,
        'filter_price_min': price_min,
        'filter_price_max': price_max,
        'filter_area_min': area_min,
        'filter_area_max': area_max,
        'filter_is_visible': is_visible,
        'filter_city': city_id,
        'filter_city_name': filter_city_name,
        'filter_neighborhoods': [int(n) for n in neighborhoods] if neighborhoods else [],
        'filter_mortgage_min': mortgage_min,
        'filter_mortgage_max': mortgage_max,
        'filter_rent_min': rent_min,
        'filter_rent_max': rent_max,
        'filter_requirements': [int(r) for r in requirements] if requirements else [],
        'filter_rooms_min': rooms_min,
        'filter_rooms_max': rooms_max,
        'filter_total_floors_min': total_floors_min,
        'filter_total_floors_max': total_floors_max,
        'filter_built_year_min': built_year_min,
        'filter_built_year_max': built_year_max,
        'filter_parking_type': parking_type,
        'filter_is_new_building': is_new_building,
        'filter_is_featured': is_featured,
        'filter_expert': expert_filter,
        'filter_supervisor': supervisor_filter,
        'filter_created_by': created_by_filter,
        'filter_units_per_floor_min': units_per_floor_min,
        'filter_units_per_floor_max': units_per_floor_max,
        'filter_building_orientation': building_orientation,
        'filter_unit_orientation': unit_orientation,
        'filter_unit_condition': unit_condition,
        'filter_has_completion_certificate': has_completion_certificate,
        'filter_has_document': has_document,
        'filter_document_type': document_type,
        'filter_ownership_document_type': ownership_document_type,
        'filter_dong_min': dong_min,
        'filter_dong_max': dong_max,
        # ✅ فیلتر بازه تاریخ ثبت
        'filter_date_from': date_from_str,
        'filter_date_to': date_to_str,
        'status_choices': Property.Status.choices,
        'contract_choices': Property.ContractType.choices,
        'parking_choices': Property.ParkingType.choices,
        'ownership_choices': Property.OwnershipType.choices,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/property/property_list.html', context)


# ============================================================
# 📋 لیست فایل های ثبتی من
# ============================================================

@login_required
def my_create_property(request):
    """
    لیست همه املاک ثبت‌شده توسط کاربر جاری
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "property_list")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    roles = user.get_roles()
    role_list = []
    for role in roles:
        if role.role.name not in role_list:
            role_list.append(role.role.name)

    is_admin_or_callcenter = 'admin' in role_list or 'callcenter' in role_list

    properties = Property.objects.filter(created_by=request.user).select_related(
        'property_type', 'province', 'city', 'neighborhood',
        'owner', 'created_by', 'primary_usage', 'unit_condition',
        'building_orientation', 'unit_orientation',
        'document_type', 'ownership_document_type',
        'expert', 'supervisor'
    ).prefetch_related(
        'requirements', 'images', 'videos', 'usage_types'
    )

    has_filters = False
    filter_count = 0

    # ---------- جستجوی کد نمایشی ----------
    display_code = request.GET.get('display_code', '').strip()
    if display_code:
        properties = properties.filter(display_code__icontains=display_code)
        has_filters = True
        filter_count += 1

    # ---------- جستجوی عمومی ----------
    search = request.GET.get('search', '')
    if search:
        properties = properties.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(address__icontains=search)
        )
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع ملک ----------
    property_type = request.GET.get('property_type', '')
    if property_type:
        properties = properties.filter(property_type_id=property_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر کاربری سندی (اصلی) ----------
    primary_usage = request.GET.get('primary_usage', '')
    if primary_usage:
        properties = properties.filter(primary_usage_id=primary_usage)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر کاربری‌های فرعی ----------
    usage_type = request.GET.get('usage_type', '')
    if usage_type:
        properties = properties.filter(usage_types__id=usage_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر وضعیت ----------
    status = request.GET.get('status', '')
    if status:
        properties = properties.filter(status=status)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع قرارداد ----------
    contract_type = request.GET.get('contract_type', '')
    if contract_type:
        properties = properties.filter(contract_type=contract_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر استان ----------
    province_id = request.GET.get('province', '')
    if province_id:
        properties = properties.filter(province_id=province_id)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر شهرستان ----------
    city_id = request.GET.get('city', '')
    filter_city_name = ''
    if city_id:
        properties = properties.filter(city_id=city_id)
        has_filters = True
        filter_count += 1
        try:
            city = City.objects.get(id=city_id)
            filter_city_name = city.name
        except City.DoesNotExist:
            pass

    # ---------- فیلتر محله (چندگزینه‌ای) ----------
    neighborhoods = request.GET.getlist('neighborhoods')
    if neighborhoods:
        properties = properties.filter(neighborhood_id__in=neighborhoods)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر قیمت ----------
    price_min = request.GET.get('price_min', '')
    if price_min:
        price_min = price_min.replace(',', '')
        properties = properties.filter(price__gte=price_min)
        has_filters = True
        filter_count += 1

    price_max = request.GET.get('price_max', '')
    if price_max:
        price_max = price_max.replace(',', '')
        properties = properties.filter(price__lte=price_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر رهن ----------
    mortgage_min = request.GET.get('mortgage_min', '')
    if mortgage_min:
        mortgage_min = mortgage_min.replace(',', '')
        properties = properties.filter(mortgage_price__gte=mortgage_min)
        has_filters = True
        filter_count += 1

    mortgage_max = request.GET.get('mortgage_max', '')
    if mortgage_max:
        mortgage_max = mortgage_max.replace(',', '')
        properties = properties.filter(mortgage_price__lte=mortgage_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر اجاره ----------
    rent_min = request.GET.get('rent_min', '')
    if rent_min:
        rent_min = rent_min.replace(',', '')
        properties = properties.filter(rent_price__gte=rent_min)
        has_filters = True
        filter_count += 1

    rent_max = request.GET.get('rent_max', '')
    if rent_max:
        rent_max = rent_max.replace(',', '')
        properties = properties.filter(rent_price__lte=rent_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر متراژ ----------
    area_min = request.GET.get('area_min', '')
    if area_min:
        properties = properties.filter(area__gte=area_min)
        has_filters = True
        filter_count += 1

    area_max = request.GET.get('area_max', '')
    if area_max:
        properties = properties.filter(area__lte=area_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر قابل مشاهده ----------
    is_visible = request.GET.get('is_visible', '')
    if is_visible == '1':
        properties = properties.filter(is_visible=True)
        has_filters = True
        filter_count += 1
    elif is_visible == '0':
        properties = properties.filter(is_visible=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر ویژه ----------
    is_featured = request.GET.get('is_featured', '')
    if is_featured == '1':
        properties = properties.filter(is_featured=True)
        has_filters = True
        filter_count += 1
    elif is_featured == '0':
        properties = properties.filter(is_featured=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلترهای مدیریتی ----------
    expert_filter = ''
    supervisor_filter = ''
    created_by_filter = ''

    if is_admin_or_callcenter:
        expert_filter = request.GET.get('expert', '')
        if expert_filter:
            properties = properties.filter(expert_id=expert_filter)
            has_filters = True
            filter_count += 1

        supervisor_filter = request.GET.get('supervisor', '')
        if supervisor_filter:
            properties = properties.filter(supervisor_id=supervisor_filter)
            has_filters = True
            filter_count += 1

        created_by_filter = request.GET.get('created_by', '')
        if created_by_filter:
            properties = properties.filter(created_by_id=created_by_filter)
            has_filters = True
            filter_count += 1

    # ---------- فیلتر امکانات ملک ----------
    requirements = request.GET.getlist('requirements')
    if requirements:
        for req in requirements:
            properties = properties.filter(requirements__id=req)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر تعداد اتاق ----------
    rooms_min = request.GET.get('rooms_min', '')
    if rooms_min:
        properties = properties.filter(rooms__gte=rooms_min)
        has_filters = True
        filter_count += 1

    rooms_max = request.GET.get('rooms_max', '')
    if rooms_max:
        properties = properties.filter(rooms__lte=rooms_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر تعداد کل طبقات ----------
    total_floors_min = request.GET.get('total_floors_min', '')
    if total_floors_min:
        properties = properties.filter(total_floors__gte=total_floors_min)
        has_filters = True
        filter_count += 1

    total_floors_max = request.GET.get('total_floors_max', '')
    if total_floors_max:
        properties = properties.filter(total_floors__lte=total_floors_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر سال ساخت ----------
    built_year_min = request.GET.get('built_year_min', '')
    if built_year_min:
        properties = properties.filter(built_year__gte=built_year_min)
        has_filters = True
        filter_count += 1

    built_year_max = request.GET.get('built_year_max', '')
    if built_year_max:
        properties = properties.filter(built_year__lte=built_year_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر پارکینگ ----------
    parking_type = request.GET.get('parking_type', '')
    if parking_type:
        properties = properties.filter(parking_type=parking_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوساز ----------
    is_new_building = request.GET.get('is_new_building', '')
    if is_new_building == '1':
        properties = properties.filter(is_new_building=True)
        has_filters = True
        filter_count += 1
    elif is_new_building == '0':
        properties = properties.filter(is_new_building=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر تعداد واحد در طبقه ----------
    units_per_floor_min = request.GET.get('units_per_floor_min', '')
    if units_per_floor_min:
        properties = properties.filter(units_per_floor__gte=units_per_floor_min)
        has_filters = True
        filter_count += 1
    units_per_floor_max = request.GET.get('units_per_floor_max', '')
    if units_per_floor_max:
        properties = properties.filter(units_per_floor__lte=units_per_floor_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر جهت ساختمان ----------
    building_orientation = request.GET.get('building_orientation', '')
    if building_orientation:
        properties = properties.filter(building_orientation_id=building_orientation)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر جهت واحد ----------
    unit_orientation = request.GET.get('unit_orientation', '')
    if unit_orientation:
        properties = properties.filter(unit_orientation_id=unit_orientation)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر وضعیت واحد ----------
    unit_condition = request.GET.get('unit_condition', '')
    if unit_condition:
        properties = properties.filter(unit_condition_id=unit_condition)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر دارای پایان کار ----------
    has_completion_certificate = request.GET.get('has_completion_certificate', '')
    if has_completion_certificate == '1':
        properties = properties.filter(has_completion_certificate=True)
        has_filters = True
        filter_count += 1
    elif has_completion_certificate == '0':
        properties = properties.filter(has_completion_certificate=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر دارای سند ----------
    has_document = request.GET.get('has_document', '')
    if has_document == '1':
        properties = properties.filter(has_document=True)
        has_filters = True
        filter_count += 1
    elif has_document == '0':
        properties = properties.filter(has_document=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع سند ----------
    document_type = request.GET.get('document_type', '')
    if document_type:
        properties = properties.filter(document_type_id=document_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع مالکیت سند ----------
    ownership_document_type = request.GET.get('ownership_document_type', '')
    if ownership_document_type:
        properties = properties.filter(ownership_document_type_id=ownership_document_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر میزان دانگ ----------
    dong_min = request.GET.get('dong_min', '')
    if dong_min:
        properties = properties.filter(dong__gte=dong_min)
        has_filters = True
        filter_count += 1
    dong_max = request.GET.get('dong_max', '')
    if dong_max:
        properties = properties.filter(dong__lte=dong_max)
        has_filters = True
        filter_count += 1

    # ---------- حذف موارد تکراری ----------
    properties = properties.distinct()

    # ---------- آمار ----------
    user_properties = Property.objects.filter(created_by=request.user)
    stats = {
        'total': user_properties.count(),
        'pending': user_properties.filter(status='pending').count(),
        'confirmed': user_properties.filter(status='confirmed').count(),
        'deposit': user_properties.filter(status='deposit').count(),
        'contract': user_properties.filter(status='contract').count(),
        'cancelled': user_properties.filter(status='cancelled').count(),
    }

    # ---------- مرتب‌سازی ----------
    sort_by = request.GET.get('sort', '-created_at')
    allowed_sorts = [
        'created_at', '-created_at', 'price', '-price',
        'area', '-area', 'title', '-title', 'status', '-status',
        'display_code', '-display_code'
    ]
    if sort_by in allowed_sorts:
        properties = properties.order_by(sort_by)
    else:
        properties = properties.order_by('-created_at')

    # ---------- صفحه‌بندی ----------
    paginator = Paginator(properties, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر ملک در لیست
    for prop in page_obj:
        prop.created_at_shamsi = get_shamsi_date(prop.created_at)
        prop.updated_at_shamsi = get_shamsi_date(prop.updated_at)
        prop.published_at_shamsi = get_shamsi_date(prop.published_at)

    # ---------- داده‌های فیلتر ----------
    provinces = Province.objects.all().order_by('name')
    property_types = PropertyType.objects.filter(is_active=True).order_by('name')
    usage_types = UsageType.objects.filter(is_active=True).order_by('order', 'name')
    requirements_all = Requirement.objects.filter(is_active=True).order_by('category', 'name')
    orientations = Orientation.objects.filter(is_active=True).order_by('order', 'name')
    unit_conditions = UnitCondition.objects.filter(is_active=True).order_by('order', 'name')
    document_types = DocumentType.objects.filter(is_active=True).order_by('order', 'name')
    ownership_document_types = OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name')

    # ---------- لیست‌های مدیریتی ----------
    experts = []
    supervisors = []
    creators = []

    if is_admin_or_callcenter:
        experts = User.objects.filter(
            properties_experted__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

        supervisors = User.objects.filter(
            properties_supervised__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

        creators = User.objects.filter(
            properties_created__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

    context = {
        'properties': page_obj,
        'stats': stats,
        'provinces': provinces,
        'property_types': property_types,
        'usage_types': usage_types,
        'requirements': requirements_all,
        'orientations': orientations,
        'unit_conditions': unit_conditions,
        'document_types': document_types,
        'ownership_document_types': ownership_document_types,
        'experts': experts,
        'supervisors': supervisors,
        'creators': creators,
        'title': 'لیست املاک',
        'userId': request.user.id,
        'this_user': request.user,
        'total_count': properties.count(),
        'has_filters': has_filters,
        'filter_count': filter_count,
        'sort_by': sort_by,
        'filter_display_code': display_code,
        'filter_search': search,
        'filter_property_type': property_type,
        'filter_primary_usage': primary_usage,
        'filter_usage_type': usage_type,
        'filter_status': status,
        'filter_contract_type': contract_type,
        'filter_province': province_id,
        'filter_price_min': price_min,
        'filter_price_max': price_max,
        'filter_area_min': area_min,
        'filter_area_max': area_max,
        'filter_is_visible': is_visible,
        'filter_city': city_id,
        'filter_city_name': filter_city_name,
        'filter_neighborhoods': [int(n) for n in neighborhoods] if neighborhoods else [],
        'filter_mortgage_min': mortgage_min,
        'filter_mortgage_max': mortgage_max,
        'filter_rent_min': rent_min,
        'filter_rent_max': rent_max,
        'filter_requirements': [int(r) for r in requirements] if requirements else [],
        'filter_rooms_min': rooms_min,
        'filter_rooms_max': rooms_max,
        'filter_total_floors_min': total_floors_min,
        'filter_total_floors_max': total_floors_max,
        'filter_built_year_min': built_year_min,
        'filter_built_year_max': built_year_max,
        'filter_parking_type': parking_type,
        'filter_is_new_building': is_new_building,
        'filter_is_featured': is_featured,
        'filter_expert': expert_filter,
        'filter_supervisor': supervisor_filter,
        'filter_created_by': created_by_filter,
        'filter_units_per_floor_min': units_per_floor_min,
        'filter_units_per_floor_max': units_per_floor_max,
        'filter_building_orientation': building_orientation,
        'filter_unit_orientation': unit_orientation,
        'filter_unit_condition': unit_condition,
        'filter_has_completion_certificate': has_completion_certificate,
        'filter_has_document': has_document,
        'filter_document_type': document_type,
        'filter_ownership_document_type': ownership_document_type,
        'filter_dong_min': dong_min,
        'filter_dong_max': dong_max,
        'status_choices': Property.Status.choices,
        'contract_choices': Property.ContractType.choices,
        'parking_choices': Property.ParkingType.choices,
        'ownership_choices': Property.OwnershipType.choices,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/property/my_create_property.html', context)


# ============================================================
# 📋 لیست فایل های کارشناس
# ============================================================

@login_required
def expert_property(request):
    """
    لیست همه املاک کارشناس جاری
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "property_list")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    roles = user.get_roles()
    role_list = []
    for role in roles:
        if role.role.name not in role_list:
            role_list.append(role.role.name)

    is_admin_or_callcenter = 'admin' in role_list or 'callcenter' in role_list

    properties = Property.objects.filter(expert=request.user).select_related(
        'property_type', 'province', 'city', 'neighborhood',
        'owner', 'created_by', 'primary_usage', 'unit_condition',
        'building_orientation', 'unit_orientation',
        'document_type', 'ownership_document_type',
        'expert', 'supervisor'
    ).prefetch_related(
        'requirements', 'images', 'videos', 'usage_types'
    )

    has_filters = False
    filter_count = 0

    # ---------- جستجوی کد نمایشی ----------
    display_code = request.GET.get('display_code', '').strip()
    if display_code:
        properties = properties.filter(display_code__icontains=display_code)
        has_filters = True
        filter_count += 1

    # ---------- جستجوی عمومی ----------
    search = request.GET.get('search', '')
    if search:
        properties = properties.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(address__icontains=search)
        )
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع ملک ----------
    property_type = request.GET.get('property_type', '')
    if property_type:
        properties = properties.filter(property_type_id=property_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر کاربری سندی (اصلی) ----------
    primary_usage = request.GET.get('primary_usage', '')
    if primary_usage:
        properties = properties.filter(primary_usage_id=primary_usage)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر کاربری‌های فرعی ----------
    usage_type = request.GET.get('usage_type', '')
    if usage_type:
        properties = properties.filter(usage_types__id=usage_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر وضعیت ----------
    status = request.GET.get('status', '')
    if status:
        properties = properties.filter(status=status)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع قرارداد ----------
    contract_type = request.GET.get('contract_type', '')
    if contract_type:
        properties = properties.filter(contract_type=contract_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر استان ----------
    province_id = request.GET.get('province', '')
    if province_id:
        properties = properties.filter(province_id=province_id)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر شهرستان ----------
    city_id = request.GET.get('city', '')
    filter_city_name = ''
    if city_id:
        properties = properties.filter(city_id=city_id)
        has_filters = True
        filter_count += 1
        try:
            city = City.objects.get(id=city_id)
            filter_city_name = city.name
        except City.DoesNotExist:
            pass

    # ---------- فیلتر محله (چندگزینه‌ای) ----------
    neighborhoods = request.GET.getlist('neighborhoods')
    if neighborhoods:
        properties = properties.filter(neighborhood_id__in=neighborhoods)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر قیمت ----------
    price_min = request.GET.get('price_min', '')
    if price_min:
        price_min = price_min.replace(',', '')
        properties = properties.filter(price__gte=price_min)
        has_filters = True
        filter_count += 1

    price_max = request.GET.get('price_max', '')
    if price_max:
        price_max = price_max.replace(',', '')
        properties = properties.filter(price__lte=price_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر رهن ----------
    mortgage_min = request.GET.get('mortgage_min', '')
    if mortgage_min:
        mortgage_min = mortgage_min.replace(',', '')
        properties = properties.filter(mortgage_price__gte=mortgage_min)
        has_filters = True
        filter_count += 1

    mortgage_max = request.GET.get('mortgage_max', '')
    if mortgage_max:
        mortgage_max = mortgage_max.replace(',', '')
        properties = properties.filter(mortgage_price__lte=mortgage_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر اجاره ----------
    rent_min = request.GET.get('rent_min', '')
    if rent_min:
        rent_min = rent_min.replace(',', '')
        properties = properties.filter(rent_price__gte=rent_min)
        has_filters = True
        filter_count += 1

    rent_max = request.GET.get('rent_max', '')
    if rent_max:
        rent_max = rent_max.replace(',', '')
        properties = properties.filter(rent_price__lte=rent_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر متراژ ----------
    area_min = request.GET.get('area_min', '')
    if area_min:
        properties = properties.filter(area__gte=area_min)
        has_filters = True
        filter_count += 1

    area_max = request.GET.get('area_max', '')
    if area_max:
        properties = properties.filter(area__lte=area_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر قابل مشاهده ----------
    is_visible = request.GET.get('is_visible', '')
    if is_visible == '1':
        properties = properties.filter(is_visible=True)
        has_filters = True
        filter_count += 1
    elif is_visible == '0':
        properties = properties.filter(is_visible=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر ویژه ----------
    is_featured = request.GET.get('is_featured', '')
    if is_featured == '1':
        properties = properties.filter(is_featured=True)
        has_filters = True
        filter_count += 1
    elif is_featured == '0':
        properties = properties.filter(is_featured=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلترهای مدیریتی ----------
    expert_filter = ''
    supervisor_filter = ''
    created_by_filter = ''

    if is_admin_or_callcenter:
        expert_filter = request.GET.get('expert', '')
        if expert_filter:
            properties = properties.filter(expert_id=expert_filter)
            has_filters = True
            filter_count += 1

        supervisor_filter = request.GET.get('supervisor', '')
        if supervisor_filter:
            properties = properties.filter(supervisor_id=supervisor_filter)
            has_filters = True
            filter_count += 1

        created_by_filter = request.GET.get('created_by', '')
        if created_by_filter:
            properties = properties.filter(created_by_id=created_by_filter)
            has_filters = True
            filter_count += 1

    # ---------- فیلتر امکانات ملک ----------
    requirements = request.GET.getlist('requirements')
    if requirements:
        for req in requirements:
            properties = properties.filter(requirements__id=req)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر تعداد اتاق ----------
    rooms_min = request.GET.get('rooms_min', '')
    if rooms_min:
        properties = properties.filter(rooms__gte=rooms_min)
        has_filters = True
        filter_count += 1

    rooms_max = request.GET.get('rooms_max', '')
    if rooms_max:
        properties = properties.filter(rooms__lte=rooms_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر تعداد کل طبقات ----------
    total_floors_min = request.GET.get('total_floors_min', '')
    if total_floors_min:
        properties = properties.filter(total_floors__gte=total_floors_min)
        has_filters = True
        filter_count += 1

    total_floors_max = request.GET.get('total_floors_max', '')
    if total_floors_max:
        properties = properties.filter(total_floors__lte=total_floors_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر سال ساخت ----------
    built_year_min = request.GET.get('built_year_min', '')
    if built_year_min:
        properties = properties.filter(built_year__gte=built_year_min)
        has_filters = True
        filter_count += 1

    built_year_max = request.GET.get('built_year_max', '')
    if built_year_max:
        properties = properties.filter(built_year__lte=built_year_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر پارکینگ ----------
    parking_type = request.GET.get('parking_type', '')
    if parking_type:
        properties = properties.filter(parking_type=parking_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوساز ----------
    is_new_building = request.GET.get('is_new_building', '')
    if is_new_building == '1':
        properties = properties.filter(is_new_building=True)
        has_filters = True
        filter_count += 1
    elif is_new_building == '0':
        properties = properties.filter(is_new_building=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر تعداد واحد در طبقه ----------
    units_per_floor_min = request.GET.get('units_per_floor_min', '')
    if units_per_floor_min:
        properties = properties.filter(units_per_floor__gte=units_per_floor_min)
        has_filters = True
        filter_count += 1
    units_per_floor_max = request.GET.get('units_per_floor_max', '')
    if units_per_floor_max:
        properties = properties.filter(units_per_floor__lte=units_per_floor_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر جهت ساختمان ----------
    building_orientation = request.GET.get('building_orientation', '')
    if building_orientation:
        properties = properties.filter(building_orientation_id=building_orientation)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر جهت واحد ----------
    unit_orientation = request.GET.get('unit_orientation', '')
    if unit_orientation:
        properties = properties.filter(unit_orientation_id=unit_orientation)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر وضعیت واحد ----------
    unit_condition = request.GET.get('unit_condition', '')
    if unit_condition:
        properties = properties.filter(unit_condition_id=unit_condition)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر دارای پایان کار ----------
    has_completion_certificate = request.GET.get('has_completion_certificate', '')
    if has_completion_certificate == '1':
        properties = properties.filter(has_completion_certificate=True)
        has_filters = True
        filter_count += 1
    elif has_completion_certificate == '0':
        properties = properties.filter(has_completion_certificate=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر دارای سند ----------
    has_document = request.GET.get('has_document', '')
    if has_document == '1':
        properties = properties.filter(has_document=True)
        has_filters = True
        filter_count += 1
    elif has_document == '0':
        properties = properties.filter(has_document=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع سند ----------
    document_type = request.GET.get('document_type', '')
    if document_type:
        properties = properties.filter(document_type_id=document_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع مالکیت سند ----------
    ownership_document_type = request.GET.get('ownership_document_type', '')
    if ownership_document_type:
        properties = properties.filter(ownership_document_type_id=ownership_document_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر میزان دانگ ----------
    dong_min = request.GET.get('dong_min', '')
    if dong_min:
        properties = properties.filter(dong__gte=dong_min)
        has_filters = True
        filter_count += 1
    dong_max = request.GET.get('dong_max', '')
    if dong_max:
        properties = properties.filter(dong__lte=dong_max)
        has_filters = True
        filter_count += 1

    # ---------- حذف موارد تکراری ----------
    properties = properties.distinct()

    # ---------- آمار ----------
    expert_properties = Property.objects.filter(expert=request.user)
    stats = {
        'total': expert_properties.count(),
        'pending': expert_properties.filter(status='pending').count(),
        'confirmed': expert_properties.filter(status='confirmed').count(),
        'deposit': expert_properties.filter(status='deposit').count(),
        'contract': expert_properties.filter(status='contract').count(),
        'cancelled': expert_properties.filter(status='cancelled').count(),
    }

    # ---------- مرتب‌سازی ----------
    sort_by = request.GET.get('sort', '-created_at')
    allowed_sorts = [
        'created_at', '-created_at', 'price', '-price',
        'area', '-area', 'title', '-title', 'status', '-status',
        'display_code', '-display_code'
    ]
    if sort_by in allowed_sorts:
        properties = properties.order_by(sort_by)
    else:
        properties = properties.order_by('-created_at')

    # ---------- صفحه‌بندی ----------
    paginator = Paginator(properties, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر ملک در لیست
    for prop in page_obj:
        prop.created_at_shamsi = get_shamsi_date(prop.created_at)
        prop.updated_at_shamsi = get_shamsi_date(prop.updated_at)
        prop.published_at_shamsi = get_shamsi_date(prop.published_at)

    # ---------- داده‌های فیلتر ----------
    provinces = Province.objects.all().order_by('name')
    property_types = PropertyType.objects.filter(is_active=True).order_by('name')
    usage_types = UsageType.objects.filter(is_active=True).order_by('order', 'name')
    requirements_all = Requirement.objects.filter(is_active=True).order_by('category', 'name')
    orientations = Orientation.objects.filter(is_active=True).order_by('order', 'name')
    unit_conditions = UnitCondition.objects.filter(is_active=True).order_by('order', 'name')
    document_types = DocumentType.objects.filter(is_active=True).order_by('order', 'name')
    ownership_document_types = OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name')

    # ---------- لیست‌های مدیریتی ----------
    experts = []
    supervisors = []
    creators = []

    if is_admin_or_callcenter:
        experts = User.objects.filter(
            properties_experted__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

        supervisors = User.objects.filter(
            properties_supervised__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

        creators = User.objects.filter(
            properties_created__isnull=False,
            is_active=True
        ).distinct().order_by('first_name', 'last_name')

    context = {
        'properties': page_obj,
        'stats': stats,
        'provinces': provinces,
        'property_types': property_types,
        'usage_types': usage_types,
        'requirements': requirements_all,
        'orientations': orientations,
        'unit_conditions': unit_conditions,
        'document_types': document_types,
        'ownership_document_types': ownership_document_types,
        'experts': experts,
        'supervisors': supervisors,
        'creators': creators,
        'title': 'لیست املاک',
        'userId': request.user.id,
        'this_user': request.user,
        'total_count': properties.count(),
        'has_filters': has_filters,
        'filter_count': filter_count,
        'sort_by': sort_by,
        'filter_display_code': display_code,
        'filter_search': search,
        'filter_property_type': property_type,
        'filter_primary_usage': primary_usage,
        'filter_usage_type': usage_type,
        'filter_status': status,
        'filter_contract_type': contract_type,
        'filter_province': province_id,
        'filter_price_min': price_min,
        'filter_price_max': price_max,
        'filter_area_min': area_min,
        'filter_area_max': area_max,
        'filter_is_visible': is_visible,
        'filter_city': city_id,
        'filter_city_name': filter_city_name,
        'filter_neighborhoods': [int(n) for n in neighborhoods] if neighborhoods else [],
        'filter_mortgage_min': mortgage_min,
        'filter_mortgage_max': mortgage_max,
        'filter_rent_min': rent_min,
        'filter_rent_max': rent_max,
        'filter_requirements': [int(r) for r in requirements] if requirements else [],
        'filter_rooms_min': rooms_min,
        'filter_rooms_max': rooms_max,
        'filter_total_floors_min': total_floors_min,
        'filter_total_floors_max': total_floors_max,
        'filter_built_year_min': built_year_min,
        'filter_built_year_max': built_year_max,
        'filter_parking_type': parking_type,
        'filter_is_new_building': is_new_building,
        'filter_is_featured': is_featured,
        'filter_expert': expert_filter,
        'filter_supervisor': supervisor_filter,
        'filter_created_by': created_by_filter,
        'filter_units_per_floor_min': units_per_floor_min,
        'filter_units_per_floor_max': units_per_floor_max,
        'filter_building_orientation': building_orientation,
        'filter_unit_orientation': unit_orientation,
        'filter_unit_condition': unit_condition,
        'filter_has_completion_certificate': has_completion_certificate,
        'filter_has_document': has_document,
        'filter_document_type': document_type,
        'filter_ownership_document_type': ownership_document_type,
        'filter_dong_min': dong_min,
        'filter_dong_max': dong_max,
        'status_choices': Property.Status.choices,
        'contract_choices': Property.ContractType.choices,
        'parking_choices': Property.ParkingType.choices,
        'ownership_choices': Property.OwnershipType.choices,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/property/expert_property.html', context)


# ============================================================
# 📋 لیست املاک غیرفعال
# ============================================================

@login_required
def deactive_property_list(request):
    """
    لیست املاک حذف شده با جستجو و فیلتر
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "deactive_property_list")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    properties = Property.objects.filter(is_active=False).select_related(
        'property_type', 'province', 'city', 'neighborhood',
        'owner', 'created_by', 'primary_usage', 'unit_condition',
        'building_orientation', 'unit_orientation',
        'document_type', 'ownership_document_type'
    ).prefetch_related(
        'requirements', 'images', 'videos', 'usage_types'
    )

    has_filters = False
    filter_count = 0

    # ---------- جستجوی کد نمایشی ----------
    display_code = request.GET.get('display_code', '').strip()
    if display_code:
        properties = properties.filter(display_code__icontains=display_code)
        has_filters = True
        filter_count += 1

    # ---------- جستجوی عمومی ----------
    search = request.GET.get('search', '')
    if search:
        properties = properties.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(address__icontains=search)
        )
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع ملک ----------
    property_type = request.GET.get('property_type', '')
    if property_type:
        properties = properties.filter(property_type_id=property_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر کاربری سندی ----------
    primary_usage = request.GET.get('primary_usage', '')
    if primary_usage:
        properties = properties.filter(primary_usage_id=primary_usage)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر کاربری‌های فرعی ----------
    usage_type = request.GET.get('usage_type', '')
    if usage_type:
        properties = properties.filter(usage_types__id=usage_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر وضعیت ----------
    status = request.GET.get('status', '')
    if status:
        properties = properties.filter(status=status)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر نوع قرارداد ----------
    contract_type = request.GET.get('contract_type', '')
    if contract_type:
        properties = properties.filter(contract_type=contract_type)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر استان ----------
    province_id = request.GET.get('province', '')
    if province_id:
        properties = properties.filter(province_id=province_id)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر قیمت ----------
    price_min = request.GET.get('price_min', '')
    if price_min:
        price_min = price_min.replace(',', '')
        properties = properties.filter(price__gte=price_min)
        has_filters = True
        filter_count += 1

    price_max = request.GET.get('price_max', '')
    if price_max:
        price_max = price_max.replace(',', '')
        properties = properties.filter(price__lte=price_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر متراژ ----------
    area_min = request.GET.get('area_min', '')
    if area_min:
        properties = properties.filter(area__gte=area_min)
        has_filters = True
        filter_count += 1

    area_max = request.GET.get('area_max', '')
    if area_max:
        properties = properties.filter(area__lte=area_max)
        has_filters = True
        filter_count += 1

    # ---------- فیلتر قابل مشاهده ----------
    is_visible = request.GET.get('is_visible', '')
    if is_visible == '1':
        properties = properties.filter(is_visible=True)
        has_filters = True
        filter_count += 1
    elif is_visible == '0':
        properties = properties.filter(is_visible=False)
        has_filters = True
        filter_count += 1

    # ---------- فیلترهای جدید ----------
    units_per_floor_min = request.GET.get('units_per_floor_min', '')
    if units_per_floor_min:
        properties = properties.filter(units_per_floor__gte=units_per_floor_min)
        has_filters = True
        filter_count += 1
    units_per_floor_max = request.GET.get('units_per_floor_max', '')
    if units_per_floor_max:
        properties = properties.filter(units_per_floor__lte=units_per_floor_max)
        has_filters = True
        filter_count += 1

    building_orientation = request.GET.get('building_orientation', '')
    if building_orientation:
        properties = properties.filter(building_orientation_id=building_orientation)
        has_filters = True
        filter_count += 1

    unit_orientation = request.GET.get('unit_orientation', '')
    if unit_orientation:
        properties = properties.filter(unit_orientation_id=unit_orientation)
        has_filters = True
        filter_count += 1

    unit_condition = request.GET.get('unit_condition', '')
    if unit_condition:
        properties = properties.filter(unit_condition_id=unit_condition)
        has_filters = True
        filter_count += 1

    has_completion_certificate = request.GET.get('has_completion_certificate', '')
    if has_completion_certificate == '1':
        properties = properties.filter(has_completion_certificate=True)
        has_filters = True
        filter_count += 1
    elif has_completion_certificate == '0':
        properties = properties.filter(has_completion_certificate=False)
        has_filters = True
        filter_count += 1

    has_document = request.GET.get('has_document', '')
    if has_document == '1':
        properties = properties.filter(has_document=True)
        has_filters = True
        filter_count += 1
    elif has_document == '0':
        properties = properties.filter(has_document=False)
        has_filters = True
        filter_count += 1

    document_type = request.GET.get('document_type', '')
    if document_type:
        properties = properties.filter(document_type_id=document_type)
        has_filters = True
        filter_count += 1

    ownership_document_type = request.GET.get('ownership_document_type', '')
    if ownership_document_type:
        properties = properties.filter(ownership_document_type_id=ownership_document_type)
        has_filters = True
        filter_count += 1

    dong_min = request.GET.get('dong_min', '')
    if dong_min:
        properties = properties.filter(dong__gte=dong_min)
        has_filters = True
        filter_count += 1
    dong_max = request.GET.get('dong_max', '')
    if dong_max:
        properties = properties.filter(dong__lte=dong_max)
        has_filters = True
        filter_count += 1

    # ---------- حذف موارد تکراری ----------
    properties = properties.distinct()

    # ---------- مرتب‌سازی ----------
    sort_by = request.GET.get('sort', '-created_at')
    allowed_sorts = [
        'created_at', '-created_at', 'price', '-price',
        'area', '-area', 'title', '-title', 'status', '-status',
        'display_code', '-display_code'
    ]
    if sort_by in allowed_sorts:
        properties = properties.order_by(sort_by)
    else:
        properties = properties.order_by('-created_at')

    # ---------- صفحه‌بندی ----------
    paginator = Paginator(properties, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر ملک در لیست
    for prop in page_obj:
        prop.created_at_shamsi = get_shamsi_date(prop.created_at)
        prop.updated_at_shamsi = get_shamsi_date(prop.updated_at)
        prop.deleted_at_shamsi = get_shamsi_date(prop.deleted_at)

    # ---------- داده‌های فیلتر ----------
    provinces = Province.objects.all().order_by('name')
    property_types = PropertyType.objects.filter(is_active=True).order_by('name')
    usage_types = UsageType.objects.filter(is_active=True).order_by('order', 'name')
    requirements_all = Requirement.objects.filter(is_active=True).order_by('category', 'name')
    orientations = Orientation.objects.filter(is_active=True).order_by('order', 'name')
    unit_conditions = UnitCondition.objects.filter(is_active=True).order_by('order', 'name')
    document_types = DocumentType.objects.filter(is_active=True).order_by('order', 'name')
    ownership_document_types = OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name')

    # ---------- آمار ----------
    property_count = Property.objects.all()
    stats = {
        'total': property_count.count(),
        'pending': property_count.filter(status='pending').count(),
        'confirmed': property_count.filter(status='confirmed').count(),
        'deposit': property_count.filter(status='deposit').count(),
        'contract': property_count.filter(status='contract').count(),
        'cancelled': property_count.filter(status='cancelled').count(),
    }

    context = {
        'properties': page_obj,
        'stats': stats,
        'provinces': provinces,
        'property_types': property_types,
        'usage_types': usage_types,
        'requirements': requirements_all,
        'orientations': orientations,
        'unit_conditions': unit_conditions,
        'document_types': document_types,
        'ownership_document_types': ownership_document_types,
        'title': 'لیست املاک غیرفعال',
        'userId': request.user.id,
        'this_user': request.user,
        'total_count': properties.count(),
        'has_filters': has_filters,
        'filter_count': filter_count,
        'sort_by': sort_by,
        'filter_display_code': display_code,
        'filter_search': search,
        'filter_property_type': property_type,
        'filter_primary_usage': primary_usage,
        'filter_usage_type': usage_type,
        'filter_status': status,
        'filter_contract_type': contract_type,
        'filter_province': province_id,
        'filter_price_min': price_min,
        'filter_price_max': price_max,
        'filter_area_min': area_min,
        'filter_area_max': area_max,
        'filter_is_visible': is_visible,
        'filter_units_per_floor_min': units_per_floor_min,
        'filter_units_per_floor_max': units_per_floor_max,
        'filter_building_orientation': building_orientation,
        'filter_unit_orientation': unit_orientation,
        'filter_unit_condition': unit_condition,
        'filter_has_completion_certificate': has_completion_certificate,
        'filter_has_document': has_document,
        'filter_document_type': document_type,
        'filter_ownership_document_type': ownership_document_type,
        'filter_dong_min': dong_min,
        'filter_dong_max': dong_max,
        'status_choices': Property.Status.choices,
        'contract_choices': Property.ContractType.choices,
        'parking_choices': Property.ParkingType.choices,
        'ownership_choices': Property.OwnershipType.choices,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/property/property_list.html', context)


# ============================================================
# ➕ ثبت ملک جدید
# ============================================================

@login_required
def property_create(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "property_create")
    roles = user.get_roles()
    role_list = []
    for role in roles:
        if role.role.name not in role_list:
            role_list.append(role.role.name)

    if 'admin' in role_list or 'callcenter' in role_list:
        statuses = Property.Status.choices
    else:
        statuses = [(Property.Status.PENDING, 'در انتظار بررسی')]

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # ====== اطلاعات پایه ======
                title = request.POST.get('title', '').strip()
                property_type_id = request.POST.get('property_type')
                status = request.POST.get('status', 'pending')
                contract_type = request.POST.get('contract_type', 'sale')

                # ====== کاربری ======
                primary_usage_id = request.POST.get('primary_usage') or None
                usage_type_ids = request.POST.getlist('usage_types')

                # ====== قیمت‌ها ======
                price = request.POST.get('price') or None
                price_per_meter = request.POST.get('price_per_meter') or None
                rent_price = request.POST.get('rent_price') or None
                mortgage_price = request.POST.get('mortgage_price') or None
                is_price_negotiable = request.POST.get('is_price_negotiable') == 'on'
                is_rent_negotiable = request.POST.get('is_rent_negotiable') == 'on'
                is_rent_convertible = request.POST.get('is_rent_convertible') == 'on'

                # ✅ اعتبارسنجی شرطی بر اساس نوع قرارداد
                if not contract_type:
                    raise ValueError('لطفاً نوع قرارداد را انتخاب کنید')

                if contract_type in ['sale', 'pre_sale']:
                    if not price or float(price) <= 0:
                        raise ValueError('برای فایل فروش، قیمت کل الزامی است')
                elif contract_type == 'rent':
                    if (not rent_price or float(rent_price) <= 0) and (not mortgage_price or float(mortgage_price) <= 0):
                        raise ValueError('برای فایل اجاره، حداقل یکی از مبالغ اجاره یا رهن الزامی است')
                elif contract_type == 'both':
                    if not price or float(price) <= 0:
                        raise ValueError('برای فایل فروش و اجاره، قیمت کل الزامی است')
                    if (not rent_price or float(rent_price) <= 0) and (not mortgage_price or float(mortgage_price) <= 0):
                        raise ValueError('برای فایل اجاره، حداقل یکی از مبالغ اجاره یا رهن الزامی است')

                # ====== مشخصات فیزیکی ======
                area = request.POST.get('area') or None
                rooms = request.POST.get('rooms', 0)
                floor = request.POST.get('floor', '').strip()
                total_floors = request.POST.get('total_floors') or None
                units_per_floor = request.POST.get('units_per_floor') or None
                built_year = request.POST.get('built_year') or None
                is_new_building = request.POST.get('is_new_building') == 'on'
                parking_type = request.POST.get('parking_type', 'none')
                ownership_type = request.POST.get('ownership_type', 'owner')

                # فیلدهای جدید
                unit_condition_id = request.POST.get('unit_condition') or None
                building_orientation_id = request.POST.get('building_orientation') or None
                unit_orientation_id = request.POST.get('unit_orientation') or None
                has_completion_certificate = request.POST.get('has_completion_certificate') == 'on'
                has_document = request.POST.get('has_document') == 'on'
                document_type_id = request.POST.get('document_type') or None
                ownership_document_type_id = request.POST.get('ownership_document_type') or None
                dong = request.POST.get('dong') or None

                # ====== موقعیت مکانی ======
                province_id = request.POST.get('province') or None
                city_id = request.POST.get('city') or None
                neighborhood_id = request.POST.get('neighborhood') or None
                address = request.POST.get('address', '').strip() or None
                latitude = request.POST.get('latitude') or None
                longitude = request.POST.get('longitude') or None

                # ====== توضیحات ======
                description = request.POST.get('description', '').strip() or None

                # ====== مالک ======
                owner_mobile = request.POST.get('owner_mobile', '').strip()
                owner_first_name = request.POST.get('owner_first_name', '').strip()
                owner_last_name = request.POST.get('owner_last_name', '').strip()

                if not owner_mobile or len(owner_mobile) < 11:
                    raise ValueError('شماره موبایل مالک معتبر نیست (حداقل ۱۱ رقم)')
                if not owner_first_name or not owner_last_name:
                    raise ValueError('نام و نام خانوادگی مالک الزامی است')

                owner_user = User.objects.filter(mobile=owner_mobile).first()
                if not owner_user:
                    random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                    owner_user = User.objects.create_user(
                        username=owner_mobile,
                        mobile=owner_mobile,
                        first_name=owner_first_name,
                        last_name=owner_last_name,
                        password=random_password
                    )
                    customer_role = Role.objects.get(name="customer")
                    new_user_role = UserRole(user=owner_user, role=customer_role, assigned_by=user)
                    new_user_role.save()
                else:
                    if owner_first_name:
                        owner_user.first_name = owner_first_name
                    if owner_last_name:
                        owner_user.last_name = owner_last_name
                    owner_user.save()

                # ====== ساخت ملک ======
                if not property_type_id:
                    default_type = PropertyType.objects.first()
                    property_type_id = default_type.id if default_type else None

                if request.user.referral is None:
                    supervisor = None
                else:
                    supervisor = request.user.referral

                # دریافت تصویر نما
                showcase_image = request.FILES.get('showcase_image')

                property_obj = Property.objects.create(
                    title=title or 'ملک بدون عنوان',
                    property_type_id=property_type_id,
                    primary_usage_id=primary_usage_id,
                    status=status,
                    contract_type=contract_type,
                    price=price or 0,
                    price_per_meter=price_per_meter or None,
                    is_price_negotiable=is_price_negotiable,
                    rent_price=rent_price,
                    mortgage_price=mortgage_price,
                    is_rent_negotiable=is_rent_negotiable,
                    is_rent_convertible=is_rent_convertible,
                    area=area or 0,
                    rooms=rooms or 0,
                    floor=floor,
                    total_floors=total_floors,
                    units_per_floor=units_per_floor,
                    built_year=built_year,
                    is_new_building=is_new_building,
                    parking_type=parking_type,
                    ownership_type=ownership_type,
                    unit_condition_id=unit_condition_id,
                    building_orientation_id=building_orientation_id,
                    unit_orientation_id=unit_orientation_id,
                    has_completion_certificate=has_completion_certificate,
                    has_document=has_document,
                    document_type_id=document_type_id,
                    ownership_document_type_id=ownership_document_type_id,
                    dong=dong,
                    showcase_image=showcase_image,
                    province_id=province_id,
                    city_id=city_id,
                    neighborhood_id=neighborhood_id,
                    address=address,
                    latitude=latitude,
                    longitude=longitude,
                    description=description,
                    owner=owner_user,
                    created_by=request.user,
                    expert=request.user,
                    supervisor=supervisor,
                    is_visible=request.POST.get('is_visible') == 'on',
                    is_featured=request.POST.get('is_featured') == 'on',
                    published_at=timezone.now() if request.POST.get('is_visible') == 'on' else None,
                )

                # ====== کاربری‌های فرعی ======
                if usage_type_ids:
                    property_obj.usage_types.set(usage_type_ids)

                # ====== امکانات ======
                requirements = request.POST.getlist('requirements')
                if requirements:
                    property_obj.requirements.set(requirements)

                # ====== تصاویر ======
                images = request.FILES.getlist('images')
                for i, image in enumerate(images):
                    PropertyImage.objects.create(
                        property_ref=property_obj,
                        image=image,
                        order=i,
                        is_main=(i == 0)
                    )

                # ====== ویدئوهای آپلودی ======
                videos = request.FILES.getlist('videos')
                for i, video in enumerate(videos):
                    PropertyVideo.objects.create(
                        property_ref=property_obj,
                        video_type='upload',
                        video_file=video,
                        order=i,
                        is_main=(i == 0)
                    )

                # ====== پاسخ ======
                if is_ajax(request):
                    return JsonResponse({
                        'success': True,
                        'message': 'ملک با موفقیت ثبت شد.',
                        'redirect_url': reverse('estate:property_detail', kwargs={'pk': property_obj.id})
                    })

                messages.success(request, 'ملک با موفقیت ثبت شد.')
                if 'customer' not in role_list:
                    return redirect('estate:property_list')
                else:
                    return redirect('site_profile:dashboard')

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            if is_ajax(request):
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)
            messages.error(request, f'خطا در ثبت ملک: {error_msg}')
            return redirect('estate:property_create')

    # ========== GET ==========
    context = {
        'title': 'ثبت ملک جدید',
        'is_create': True,
        'userId': request.user.id,
        'this_user': request.user,
        'provinces': Province.objects.all().order_by('name'),
        'property_types': PropertyType.objects.filter(is_active=True).order_by('name'),
        'usage_types': UsageType.objects.filter(is_active=True).order_by('order', 'name'),
        'requirements': Requirement.objects.filter(is_active=True).order_by('category', 'name'),
        'orientations': Orientation.objects.filter(is_active=True).order_by('order', 'name'),
        'unit_conditions': UnitCondition.objects.filter(is_active=True).order_by('order', 'name'),
        'document_types': DocumentType.objects.filter(is_active=True).order_by('order', 'name'),
        'ownership_document_types': OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name'),
        'status_choices': statuses,
        'contract_choices': Property.ContractType.choices,
        'parking_choices': Property.ParkingType.choices,
        'ownership_choices': Property.OwnershipType.choices,
        'selected_requirements': [],
        'selected_usage_types': [],
        'selected_primary_usage': None,
        'selected_locations_json': '[]',
        'owner_mobile': '',
        'owner_first_name': '',
        'owner_last_name': '',
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/property/property_form.html', context)


@login_required
def property_edit(request, pk):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "property_edit")

    property_obj = get_object_or_404(Property, pk=pk)

    if user == property_obj.created_by and property_obj.status == "pending":
        permission = True

    if not permission:
        if is_ajax(request):
            return JsonResponse({'success': False, 'error': 'شما دسترسی به این بخش را ندارید'}, status=403)
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    roles = user.get_roles()
    role_list = []
    for role in roles:
        if role.role.name not in role_list:
            role_list.append(role.role.name)

    if 'admin' in role_list or 'callcenter' in role_list:
        statuses = Property.Status.choices
    else:
        statuses = [(Property.Status.PENDING, 'در انتظار بررسی')]

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # ====== اطلاعات پایه ======
                title = request.POST.get('title', '').strip()
                property_type_id = request.POST.get('property_type')
                status = request.POST.get('status', 'pending')
                contract_type = request.POST.get('contract_type', 'sale')

                # ====== کاربری ======
                primary_usage_id = request.POST.get('primary_usage') or None
                usage_type_ids = request.POST.getlist('usage_types')

                # ====== قیمت‌ها ======
                price = request.POST.get('price') or None
                price_per_meter = request.POST.get('price_per_meter') or None
                rent_price = request.POST.get('rent_price') or None
                mortgage_price = request.POST.get('mortgage_price') or None
                is_price_negotiable = request.POST.get('is_price_negotiable') == 'on'
                is_rent_negotiable = request.POST.get('is_rent_negotiable') == 'on'
                is_rent_convertible = request.POST.get('is_rent_convertible') == 'on'

                # ✅ اعتبارسنجی شرطی
                if not contract_type:
                    raise ValueError('لطفاً نوع قرارداد را انتخاب کنید')

                if contract_type in ['sale', 'pre_sale']:
                    if not price or float(price) <= 0:
                        raise ValueError('برای فایل فروش، قیمت کل الزامی است')
                elif contract_type == 'rent':
                    if (not rent_price or float(rent_price) <= 0) and (not mortgage_price or float(mortgage_price) <= 0):
                        raise ValueError('برای فایل اجاره، حداقل یکی از مبالغ اجاره یا رهن الزامی است')
                elif contract_type == 'both':
                    if not price or float(price) <= 0:
                        raise ValueError('برای فایل فروش و اجاره، قیمت کل الزامی است')
                    if (not rent_price or float(rent_price) <= 0) and (not mortgage_price or float(mortgage_price) <= 0):
                        raise ValueError('برای فایل اجاره، حداقل یکی از مبالغ اجاره یا رهن الزامی است')

                # ====== مشخصات فیزیکی ======
                area = request.POST.get('area') or None
                rooms = request.POST.get('rooms', 0)
                floor = request.POST.get('floor', '').strip()
                total_floors = request.POST.get('total_floors') or None
                units_per_floor = request.POST.get('units_per_floor') or None
                built_year = request.POST.get('built_year') or None
                is_new_building = request.POST.get('is_new_building') == 'on'
                parking_type = request.POST.get('parking_type', 'none')
                ownership_type = request.POST.get('ownership_type', 'owner')

                # فیلدهای جدید
                unit_condition_id = request.POST.get('unit_condition') or None
                building_orientation_id = request.POST.get('building_orientation') or None
                unit_orientation_id = request.POST.get('unit_orientation') or None
                has_completion_certificate = request.POST.get('has_completion_certificate') == 'on'
                has_document = request.POST.get('has_document') == 'on'
                document_type_id = request.POST.get('document_type') or None
                ownership_document_type_id = request.POST.get('ownership_document_type') or None
                dong = request.POST.get('dong') or None

                # ====== موقعیت مکانی ======
                province_id = request.POST.get('province') or None
                city_id = request.POST.get('city') or None
                neighborhood_id = request.POST.get('neighborhood') or None
                address = request.POST.get('address', '').strip() or None
                latitude = request.POST.get('latitude') or None
                longitude = request.POST.get('longitude') or None

                # ====== توضیحات ======
                description = request.POST.get('description', '').strip() or None

                # ====== مالک ======
                owner_mobile = request.POST.get('owner_mobile', '').strip()
                owner_first_name = request.POST.get('owner_first_name', '').strip()
                owner_last_name = request.POST.get('owner_last_name', '').strip()

                if owner_mobile and len(owner_mobile) >= 11:
                    owner_user = User.objects.filter(mobile=owner_mobile).first()
                    if not owner_user:
                        random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                        owner_user = User.objects.create_user(
                            username=owner_mobile,
                            mobile=owner_mobile,
                            first_name=owner_first_name,
                            last_name=owner_last_name,
                            password=random_password
                        )
                    else:
                        if owner_first_name:
                            owner_user.first_name = owner_first_name
                        if owner_last_name:
                            owner_user.last_name = owner_last_name
                        owner_user.save()
                    property_obj.owner = owner_user

                # ====== اعمال تغییرات روی شیء ======
                property_obj.title = title or 'ملک بدون عنوان'
                property_obj.property_type_id = property_type_id
                property_obj.status = status
                property_obj.contract_type = contract_type
                property_obj.primary_usage_id = primary_usage_id
                property_obj.price = price or 0
                property_obj.price_per_meter = price_per_meter or None
                property_obj.is_price_negotiable = is_price_negotiable
                property_obj.rent_price = rent_price
                property_obj.mortgage_price = mortgage_price
                property_obj.is_rent_negotiable = is_rent_negotiable
                property_obj.is_rent_convertible = is_rent_convertible
                property_obj.area = area or 0
                property_obj.rooms = rooms or 0
                property_obj.floor = floor
                property_obj.total_floors = total_floors
                property_obj.units_per_floor = units_per_floor
                property_obj.built_year = built_year
                property_obj.is_new_building = is_new_building
                property_obj.parking_type = parking_type
                property_obj.ownership_type = ownership_type
                property_obj.unit_condition_id = unit_condition_id
                property_obj.building_orientation_id = building_orientation_id
                property_obj.unit_orientation_id = unit_orientation_id
                property_obj.has_completion_certificate = has_completion_certificate
                property_obj.has_document = has_document
                property_obj.document_type_id = document_type_id
                property_obj.ownership_document_type_id = ownership_document_type_id
                property_obj.dong = dong
                property_obj.province_id = province_id
                property_obj.city_id = city_id
                property_obj.neighborhood_id = neighborhood_id
                property_obj.address = address
                property_obj.latitude = latitude
                property_obj.longitude = longitude
                property_obj.description = description

                # ====== وضعیت نمایش ======
                property_obj.is_visible = request.POST.get('is_visible') == 'on'
                property_obj.is_featured = request.POST.get('is_featured') == 'on'

                # مدیریت تصویر نما
                if request.POST.get('remove_showcase_image') == 'on':
                    if property_obj.showcase_image:
                        property_obj.showcase_image.delete(save=False)
                        property_obj.showcase_image = None

                new_showcase_image = request.FILES.get('showcase_image')
                if new_showcase_image:
                    if property_obj.showcase_image:
                        property_obj.showcase_image.delete(save=False)
                    property_obj.showcase_image = new_showcase_image

                property_obj.save()

                # ====== کاربری‌های فرعی ======
                if usage_type_ids:
                    property_obj.usage_types.set(usage_type_ids)
                else:
                    property_obj.usage_types.clear()

                # ====== امکانات ======
                requirements = request.POST.getlist('requirements')
                property_obj.requirements.set(requirements)

                # ====== تصاویر جدید ======
                new_images = request.FILES.getlist('images')
                for i, image in enumerate(new_images):
                    PropertyImage.objects.create(
                        property_ref=property_obj,
                        image=image,
                        order=property_obj.images.count() + i,
                        is_main=(i == 0 and not property_obj.images.filter(is_main=True).exists())
                    )

                # ====== ویدئوهای جدید ======
                new_videos = request.FILES.getlist('videos')
                for i, video in enumerate(new_videos):
                    PropertyVideo.objects.create(
                        property_ref=property_obj,
                        video_type='upload',
                        video_file=video,
                        order=property_obj.videos.count() + i,
                        is_main=(i == 0 and not property_obj.videos.filter(is_main=True).exists())
                    )

                # ====== پاسخ ======
                if is_ajax(request):
                    return JsonResponse({
                        'success': True,
                        'message': 'ملک با موفقیت ویرایش شد.',
                        'redirect_url': reverse('estate:property_detail', kwargs={'pk': property_obj.id})
                    })

                messages.success(request, f'ملک "{property_obj.title}" با موفقیت ویرایش شد.')
                if 'customer' not in role_list:
                    return redirect('estate:property_list')
                else:
                    return redirect('site_profile:dashboard')

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            if is_ajax(request):
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)
            messages.error(request, f'خطا در ویرایش ملک: {error_msg}')

    # ========== GET ==========
    selected_locations = []
    if property_obj.neighborhood:
        selected_locations.append({
            'province_id': property_obj.province.id if property_obj.province else None,
            'province_name': property_obj.province.name if property_obj.province else '',
            'city_id': property_obj.city.id if property_obj.city else None,
            'city_name': property_obj.city.name if property_obj.city else '',
            'neighborhood_id': property_obj.neighborhood.id,
            'neighborhood_name': property_obj.neighborhood.name,
        })

    owner_mobile = property_obj.owner.mobile if property_obj.owner else ''
    owner_first_name = property_obj.owner.first_name if property_obj.owner else ''
    owner_last_name = property_obj.owner.last_name if property_obj.owner else ''

    if "admin" in request.user.get_role_names() or "callcenter" in request.user.get_role_names():
        status_choices = Property.Status.choices
    else:
        status_choices = [(Property.Status.PENDING, Property.Status.PENDING.label)]

    context = {
        'property': property_obj,
        'title': f'ویرایش ملک {property_obj.title}',
        'is_create': False,
        'userId': request.user.id,
        'this_user': request.user,
        'provinces': Province.objects.all().order_by('name'),
        'property_types': PropertyType.objects.filter(is_active=True).order_by('name'),
        'usage_types': UsageType.objects.filter(is_active=True).order_by('order', 'name'),
        'requirements': Requirement.objects.filter(is_active=True).order_by('category', 'name'),
        'orientations': Orientation.objects.filter(is_active=True).order_by('order', 'name'),
        'unit_conditions': UnitCondition.objects.filter(is_active=True).order_by('order', 'name'),
        'document_types': DocumentType.objects.filter(is_active=True).order_by('order', 'name'),
        'ownership_document_types': OwnershipDocumentType.objects.filter(is_active=True).order_by('order', 'name'),
        'status_choices': status_choices,
        'contract_choices': Property.ContractType.choices,
        'parking_choices': Property.ParkingType.choices,
        'ownership_choices': Property.OwnershipType.choices,
        'selected_requirements': list(property_obj.requirements.values_list('id', flat=True)),
        'selected_usage_types': list(property_obj.usage_types.values_list('id', flat=True)),
        'selected_primary_usage': property_obj.primary_usage_id,
        'selected_locations_json': json.dumps(selected_locations, ensure_ascii=False),
        'owner_mobile': owner_mobile,
        'owner_first_name': owner_first_name,
        'owner_last_name': owner_last_name,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/property/property_form.html', context)


# ============================================================
# 👤 جزئیات ملک
# ============================================================

@login_required
def property_detail(request, pk):
    """
    نمایش جزئیات کامل ملک به همراه یادداشت‌ها و تطابق‌ها
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "property_detail")
    property_obj = get_object_or_404(Property, pk=pk)

    if user == property_obj.owner:
        permission = True

    if not permission:
        messages.error(request, 'شما اجازه استفاده از این بخش را ندارید')
        return redirect('site_profile:page_404')

    property_obj = get_object_or_404(
        Property.objects.select_related(
            'property_type', 'province', 'city', 'neighborhood',
            'owner', 'created_by', 'supervisor', 'expert', 'primary_usage',
            'unit_condition', 'building_orientation', 'unit_orientation',
            'document_type', 'ownership_document_type'
        ).prefetch_related(
            'images', 'videos', 'requirements', 'usage_types'
        ),
        pk=pk,
        is_active=True
    )

    # ✅ اضافه کردن تاریخ شمسی به شیء ملک
    property_obj.created_at_shamsi = get_shamsi_datetime(property_obj.created_at)
    property_obj.updated_at_shamsi = get_shamsi_datetime(property_obj.updated_at)
    property_obj.published_at_shamsi = get_shamsi_date(property_obj.published_at)
    property_obj.deleted_at_shamsi = get_shamsi_datetime(property_obj.deleted_at)

    # ====== دریافت تصاویر و ویدئوها ======
    images = property_obj.images.all().order_by('order')
    videos = property_obj.videos.all().order_by('order')

    # ====== دریافت یادداشت‌های فایل ======
    from estate.models import Note
    notes = Note.objects.filter(
        property_ref=property_obj,
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

    # ====== دریافت تطابق‌ها ======
    from estate.models import Match
    top_matches = Match.objects.filter(
        property_ref=property_obj,
        status__in=[Match.Status.PENDING, Match.Status.REVIEWED, Match.Status.SENT, Match.Status.INTERESTED]
    ).select_related('customer__user').order_by('-match_score')[:10]

    # ✅ اضافه کردن تاریخ شمسی به هر تطابق
    for match in top_matches:
        match.created_at_shamsi = get_shamsi_datetime(match.created_at)
        match.sent_at_shamsi = get_shamsi_datetime(match.sent_at)
        match.viewed_at_shamsi = get_shamsi_datetime(match.viewed_at)
        match.reviewed_at_shamsi = get_shamsi_datetime(match.reviewed_at)

    match_stats = Match.objects.filter(property_ref=property_obj).aggregate(
        avg=models.Avg('match_score'),
        count=models.Count('id')
    )

    total_customers = Customer.objects.filter(is_active=True).count()

    context = {
        'property': property_obj,
        'images': images,
        'videos': videos,
        'notes': notes,
        'top_matches': top_matches,
        'match_stats': {
            'avg': match_stats['avg'] or 0,
            'count': match_stats['count'] or 0,
        },
        'total_customers': total_customers,
        'title': f'جزئیات ملک - {property_obj.title}',
        'userId': user.id,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'estate/property/property_detail.html', context)


# ============================================================
# 🗑️ حذف و بازیابی
# ============================================================

@login_required
def property_delete(request, pk):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "property_delete")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    property_obj = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        property_obj.status = "cancelled"
        property_obj.save()
        property_obj.soft_delete()
        messages.success(request, f'ملک "{property_obj.title}" با موفقیت حذف شد.')
        return redirect('estate:property_list')

    # ✅ اضافه کردن تاریخ شمسی
    property_obj.created_at_shamsi = get_shamsi_datetime(property_obj.created_at)
    property_obj.deleted_at_shamsi = get_shamsi_datetime(property_obj.deleted_at)

    context = {
        'property': property_obj,
        'title': f'حذف ملک {property_obj.title}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/property/property_delete.html', context)


@login_required
def property_restore(request, pk):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "property_restore")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    property_obj = get_object_or_404(Property, pk=pk)

    if request.method == 'POST':
        property_obj.status = "confirmed"
        property_obj.save()
        property_obj.restore()
        messages.success(request, f'ملک "{property_obj.title}" با موفقیت بازیابی شد.')
        return redirect('estate:deactive_property_list')

    # ✅ اضافه کردن تاریخ شمسی
    property_obj.created_at_shamsi = get_shamsi_datetime(property_obj.created_at)
    property_obj.deleted_at_shamsi = get_shamsi_datetime(property_obj.deleted_at)

    context = {
        'property': property_obj,
        'title': f'بازیابی ملک {property_obj.title}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/property/property_restore.html', context)


# ============================================================
# 🔄 محاسبه تطابق ملک (API)
# ============================================================

@require_POST
@login_required
def calculate_matches_for_property(request, pk):
    try:
        property_obj = get_object_or_404(Property, pk=pk)
        results = MatchManager.update_all_matches_for_property(
            property_obj,
            created_by=request.user,
            min_score=0
        )

        total_matches = len(results)
        high_matches = sum(1 for m, _ in results if m.match_score >= 70)
        good_matches = sum(1 for m, _ in results if 50 <= m.match_score < 70)
        low_matches = sum(1 for m, _ in results if m.match_score < 50)

        return JsonResponse({
            'success': True,
            'message': f'تطابق برای {total_matches} مشتری محاسبه شد. '
                       f'({high_matches} عالی، {good_matches} خوب، {low_matches} ضعیف)',
            'total': total_matches,
            'high': high_matches,
            'good': good_matches,
            'low': low_matches
        })

    except Property.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'ملک مورد نظر یافت نشد'
        }, status=404)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================
# 🖼️ مدیریت تصاویر (API)
# ============================================================

@login_required
def property_image_delete(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    image = get_object_or_404(PropertyImage, pk=pk)

    if image.is_main:
        next_image = PropertyImage.objects.filter(
            property_ref=image.property_ref
        ).exclude(id=image.id).order_by('order').first()
        if next_image:
            next_image.is_main = True
            next_image.save()

    image.delete()

    return JsonResponse({
        'success': True,
        'message': 'تصویر با موفقیت حذف شد'
    })


@login_required
def property_image_set_main(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    image = get_object_or_404(PropertyImage, pk=pk)
    PropertyImage.objects.filter(property_ref=image.property_ref).update(is_main=False)
    image.is_main = True
    image.save()

    return JsonResponse({
        'success': True,
        'message': 'تصویر اصلی با موفقیت تنظیم شد'
    })


# ============================================================
# 🎬 مدیریت ویدئوها (API)
# ============================================================

@login_required
def property_video_delete(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    video = get_object_or_404(PropertyVideo, pk=pk)

    if video.is_main:
        next_video = PropertyVideo.objects.filter(
            property_ref=video.property_ref
        ).exclude(id=video.id).order_by('order').first()
        if next_video:
            next_video.is_main = True
            next_video.save()

    video.delete()

    return JsonResponse({
        'success': True,
        'message': 'ویدئو با موفقیت حذف شد'
    })


# ============================================================
# 📊 APIها
# ============================================================

@login_required
def property_stats_api(request):
    stats = {
        'total': Property.objects.count(),
        'by_status': {},
        'by_contract': {},
        'by_type': {},
        'by_usage': {},
        'by_primary_usage': {},
        'by_unit_condition': {},
        'by_has_completion': {},
        'by_has_document': {},
        'by_dong': {},
    }

    for status in Property.Status.choices:
        count = Property.objects.filter(status=status[0]).count()
        stats['by_status'][status[0]] = {'label': status[1], 'count': count}

    for contract in Property.ContractType.choices:
        count = Property.objects.filter(contract_type=contract[0]).count()
        stats['by_contract'][contract[0]] = {'label': contract[1], 'count': count}

    for p_type in PropertyType.objects.filter(is_active=True):
        count = Property.objects.filter(property_type=p_type).count()
        stats['by_type'][p_type.code] = {'label': p_type.name, 'count': count}

    for usage in UsageType.objects.filter(is_active=True):
        count = Property.objects.filter(usage_types=usage).count()
        if count > 0:
            stats['by_usage'][usage.code] = {
                'label': usage.name,
                'count': count,
                'color': usage.color
            }

    for usage in UsageType.objects.filter(is_active=True):
        count = Property.objects.filter(primary_usage=usage).count()
        if count > 0:
            stats['by_primary_usage'][usage.code] = {
                'label': usage.name,
                'count': count,
                'color': usage.color
            }

    for cond in UnitCondition.objects.filter(is_active=True):
        count = Property.objects.filter(unit_condition=cond).count()
        if count > 0:
            stats['by_unit_condition'][cond.code] = {
                'label': cond.name,
                'count': count
            }

    stats['by_has_completion']['yes'] = Property.objects.filter(has_completion_certificate=True).count()
    stats['by_has_completion']['no'] = Property.objects.filter(has_completion_certificate=False).count()

    stats['by_has_document']['yes'] = Property.objects.filter(has_document=True).count()
    stats['by_has_document']['no'] = Property.objects.filter(has_document=False).count()

    for dong_value in range(1, 7):
        count = Property.objects.filter(dong=dong_value).count()
        if count > 0:
            stats['by_dong'][str(dong_value)] = count

    return JsonResponse(stats)


@login_required
def property_search_ajax(request):
    query = request.GET.get('q', '')
    limit = int(request.GET.get('limit', 10))

    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    properties = Property.objects.filter(
        Q(title__icontains=query) |
        Q(address__icontains=query)
    ).select_related(
        'property_type', 'city', 'neighborhood', 'primary_usage',
        'unit_condition'
    )[:limit]

    results = [{
        'id': str(p.id),
        'text': f"{p.title} - {p.property_type.name} - {p.formatted_price}",
        'title': p.title,
        'price': p.formatted_price,
        'type': p.property_type.name,
        'primary_usage': p.primary_usage.name if p.primary_usage else '',
        'unit_condition': p.unit_condition.name if p.unit_condition else '',
        'location': p.full_location,
        'area': p.area,
        'status': p.get_status_display(),
    } for p in properties]

    return JsonResponse({'results': results})