from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone

from .models import Customer, Property, DuplicateCheck, PropertyType, Requirement, UsageType
from .models import Orientation, UnitCondition, DocumentType, OwnershipDocumentType  # 🆕
from account.models import User
from myclass.mydef import views_permissions


# ============================================================
# 🔍 توابع منطق بررسی تکراری (قابل استفاده در ویوهای دیگر)
# ============================================================

def check_customer_duplicate_logic(customer_data, customer_id=None):
    """
    منطق بررسی تکراری مشتری (قابل استفاده در ویوها)
    بر اساس: نوع مشتری، مناطق مورد نظر، بودجه، نوع ملک، نیازها،
    و فیلدهای جدید شامل کاربری‌ها، طبقه، تعداد طبقات، واحد در طبقه،
    جهت‌ها، وضعیت واحد، نیاز به پایان کار/سند، انواع سند، نوع مالکیت سند، دانگ

    Args:
        customer_data: دیکشنری اطلاعات مشتری
        customer_id: شناسه مشتری (اختیاری - برای به‌روزرسانی رکورد)

    Returns:
        dict: شامل اطلاعات تکراری
    """
    customer_type = customer_data.get('customer_type')
    preferred_cities = customer_data.get('preferred_cities', [])
    preferred_neighborhoods = customer_data.get('preferred_neighborhoods', [])
    preferred_property_types = customer_data.get('preferred_property_types', [])
    preferred_requirements = customer_data.get('preferred_requirements', [])
    # 🆕 فیلدهای جدید
    preferred_usage_types = customer_data.get('preferred_usage_types', [])
    preferred_building_orientations = customer_data.get('preferred_building_orientations', [])
    preferred_unit_orientations = customer_data.get('preferred_unit_orientations', [])
    preferred_unit_conditions = customer_data.get('preferred_unit_conditions', [])
    preferred_document_types = customer_data.get('preferred_document_types', [])
    preferred_ownership_document_types = customer_data.get('preferred_ownership_document_types', [])
    primary_usage_id = customer_data.get('primary_usage_id')
    need_completion_certificate = customer_data.get('need_completion_certificate')
    need_document = customer_data.get('need_document')

    budget_min = customer_data.get('budget_min')
    budget_max = customer_data.get('budget_max')
    min_area = customer_data.get('min_area')
    max_area = customer_data.get('max_area')
    min_rooms = customer_data.get('min_rooms')
    max_rooms = customer_data.get('max_rooms')
    # 🆕 محدوده‌های عددی
    preferred_min_floor = customer_data.get('preferred_min_floor')
    preferred_max_floor = customer_data.get('preferred_max_floor')
    preferred_min_total_floors = customer_data.get('preferred_min_total_floors')
    preferred_max_total_floors = customer_data.get('preferred_max_total_floors')
    preferred_min_units_per_floor = customer_data.get('preferred_min_units_per_floor')
    preferred_max_units_per_floor = customer_data.get('preferred_max_units_per_floor')
    preferred_dong_min = customer_data.get('preferred_dong_min')
    preferred_dong_max = customer_data.get('preferred_dong_max')

    if not customer_type and not preferred_cities and not preferred_neighborhoods:
        return {
            'has_duplicate': False,
            'duplicates': [],
            'duplicate_check_id': None,
            'count': 0
        }

    query = Q(is_active=True)

    if customer_type:
        query &= Q(customer_type=customer_type)

    if preferred_cities:
        query &= Q(preferred_cities__in=preferred_cities)
    if preferred_neighborhoods:
        query &= Q(preferred_neighborhoods__in=preferred_neighborhoods)
    if preferred_property_types:
        query &= Q(preferred_property_types__in=preferred_property_types)
    if preferred_requirements:
        query &= Q(preferred_requirements__in=preferred_requirements)
    # 🆕 فیلترهای جدید
    if preferred_usage_types:
        query &= Q(preferred_usage_types__in=preferred_usage_types)
    if preferred_building_orientations:
        query &= Q(preferred_building_orientations__in=preferred_building_orientations)
    if preferred_unit_orientations:
        query &= Q(preferred_unit_orientations__in=preferred_unit_orientations)
    if preferred_unit_conditions:
        query &= Q(preferred_unit_conditions__in=preferred_unit_conditions)
    if preferred_document_types:
        query &= Q(preferred_document_types__in=preferred_document_types)
    if preferred_ownership_document_types:
        query &= Q(preferred_ownership_document_types__in=preferred_ownership_document_types)
    if primary_usage_id:
        query &= Q(primary_usage_id=primary_usage_id)
    if need_completion_certificate is not None:
        query &= Q(need_completion_certificate=need_completion_certificate)
    if need_document is not None:
        query &= Q(need_document=need_document)

    # محدوده‌های عددی
    if budget_min and budget_max:
        try:
            budget_min_int = int(budget_min)
            budget_max_int = int(budget_max)
            range_min = budget_min_int * 0.7
            range_max = budget_max_int * 1.3
            query &= Q(
                Q(budget_min__gte=range_min, budget_min__lte=range_max) |
                Q(budget_max__gte=range_min, budget_max__lte=range_max) |
                Q(budget_min__lte=range_min, budget_max__gte=range_max)
            )
        except (ValueError, TypeError):
            pass

    if min_area and max_area:
        try:
            min_area_float = float(min_area)
            max_area_float = float(max_area)
            range_min = min_area_float * 0.7
            range_max = max_area_float * 1.3
            query &= Q(
                Q(min_area__gte=range_min, min_area__lte=range_max) |
                Q(max_area__gte=range_min, max_area__lte=range_max) |
                Q(min_area__lte=range_min, max_area__gte=range_max)
            )
        except (ValueError, TypeError):
            pass

    if min_rooms and max_rooms:
        try:
            min_rooms_int = int(min_rooms)
            max_rooms_int = int(max_rooms)
            query &= Q(
                Q(min_rooms__gte=min_rooms_int - 1, min_rooms__lte=max_rooms_int + 1) |
                Q(max_rooms__gte=min_rooms_int - 1, max_rooms__lte=max_rooms_int + 1)
            )
        except (ValueError, TypeError):
            pass

    # 🆕 محدوده طبقه
    if preferred_min_floor and preferred_max_floor:
        try:
            min_f = int(preferred_min_floor)
            max_f = int(preferred_max_floor)
            query &= Q(
                Q(preferred_min_floor__gte=min_f - 1, preferred_min_floor__lte=max_f + 1) |
                Q(preferred_max_floor__gte=min_f - 1, preferred_max_floor__lte=max_f + 1)
            )
        except (ValueError, TypeError):
            pass

    # 🆕 محدوده تعداد طبقات ساختمان
    if preferred_min_total_floors and preferred_max_total_floors:
        try:
            min_t = int(preferred_min_total_floors)
            max_t = int(preferred_max_total_floors)
            query &= Q(
                Q(preferred_min_total_floors__gte=min_t - 1, preferred_min_total_floors__lte=max_t + 1) |
                Q(preferred_max_total_floors__gte=min_t - 1, preferred_max_total_floors__lte=max_t + 1)
            )
        except (ValueError, TypeError):
            pass

    # 🆕 محدوده واحد در طبقه
    if preferred_min_units_per_floor and preferred_max_units_per_floor:
        try:
            min_u = int(preferred_min_units_per_floor)
            max_u = int(preferred_max_units_per_floor)
            query &= Q(
                Q(preferred_min_units_per_floor__gte=min_u - 1, preferred_min_units_per_floor__lte=max_u + 1) |
                Q(preferred_max_units_per_floor__gte=min_u - 1, preferred_max_units_per_floor__lte=max_u + 1)
            )
        except (ValueError, TypeError):
            pass

    # 🆕 محدوده دانگ
    if preferred_dong_min and preferred_dong_max:
        try:
            min_d = int(preferred_dong_min)
            max_d = int(preferred_dong_max)
            query &= Q(
                Q(preferred_dong_min__gte=min_d - 1, preferred_dong_min__lte=max_d + 1) |
                Q(preferred_dong_max__gte=min_d - 1, preferred_dong_max__lte=max_d + 1)
            )
        except (ValueError, TypeError):
            pass

    similar_customers = Customer.objects.filter(
        query
    ).exclude(status="new").select_related(
        'user', 'source', 'primary_usage'
    ).prefetch_related(
        'preferred_cities',
        'preferred_neighborhoods',
        'preferred_property_types',
        'preferred_requirements',
        'preferred_usage_types',
        'preferred_building_orientations',
        'preferred_unit_orientations',
        'preferred_unit_conditions',
        'preferred_document_types',
        'preferred_ownership_document_types'
    ).distinct().order_by('-created_at')

    duplicate_results = []
    for dup in similar_customers:
        if customer_id and str(dup.id) == str(customer_id):
            continue

        score = 0
        match_details = {}

        # نوع مشتری
        if customer_type and dup.customer_type == customer_type:
            score += 10
            match_details['نوع مشتری'] = {'match': True, 'score': 10}

        # شهرها
        dup_cities = set(dup.preferred_cities.values_list('id', flat=True))
        new_cities = set([int(c) for c in preferred_cities]) if preferred_cities else set()
        if new_cities and dup_cities:
            common_cities = new_cities & dup_cities
            if common_cities:
                city_score = min(15, len(common_cities) * 5)
                score += city_score
                match_details['شهرها'] = {'match': True, 'score': city_score, 'count': len(common_cities)}

        # محله‌ها
        dup_neighborhoods = set(dup.preferred_neighborhoods.values_list('id', flat=True))
        new_neighborhoods = set([int(n) for n in preferred_neighborhoods]) if preferred_neighborhoods else set()
        if new_neighborhoods and dup_neighborhoods:
            common_neighborhoods = new_neighborhoods & dup_neighborhoods
            if common_neighborhoods:
                neighborhood_score = min(20, len(common_neighborhoods) * 8)
                score += neighborhood_score
                match_details['محله‌ها'] = {'match': True, 'score': neighborhood_score,
                                            'count': len(common_neighborhoods)}

        # نوع ملک
        dup_types = set(dup.preferred_property_types.values_list('id', flat=True))
        new_types = set([int(t) for t in preferred_property_types]) if preferred_property_types else set()
        if new_types and dup_types:
            common_types = new_types & dup_types
            if common_types:
                type_score = min(10, len(common_types) * 5)
                score += type_score
                match_details['نوع ملک'] = {'match': True, 'score': type_score, 'count': len(common_types)}

        # نیازها
        dup_reqs = set(dup.preferred_requirements.values_list('id', flat=True))
        new_reqs = set([int(r) for r in preferred_requirements]) if preferred_requirements else set()
        if new_reqs and dup_reqs:
            common_reqs = new_reqs & dup_reqs
            if common_reqs:
                req_score = min(10, len(common_reqs) * 4)
                score += req_score
                match_details['نیازها'] = {'match': True, 'score': req_score, 'count': len(common_reqs)}

        # 🆕 کاربری‌های فرعی
        dup_usages = set(dup.preferred_usage_types.values_list('id', flat=True))
        new_usages = set([int(u) for u in preferred_usage_types]) if preferred_usage_types else set()
        if new_usages and dup_usages:
            common_usages = new_usages & dup_usages
            if common_usages:
                usage_score = min(10, len(common_usages) * 3)
                score += usage_score
                match_details['کاربری‌ها'] = {'match': True, 'score': usage_score, 'count': len(common_usages)}

        # 🆕 کاربری سندی
        if primary_usage_id and dup.primary_usage_id == int(primary_usage_id):
            score += 8
            match_details['کاربری سندی'] = {'match': True, 'score': 8}

        # 🆕 جهت ساختمان
        dup_build_ori = set(dup.preferred_building_orientations.values_list('id', flat=True))
        new_build_ori = set([int(o) for o in preferred_building_orientations]) if preferred_building_orientations else set()
        if new_build_ori and dup_build_ori:
            common_build_ori = new_build_ori & dup_build_ori
            if common_build_ori:
                ori_score = min(6, len(common_build_ori) * 3)
                score += ori_score
                match_details['جهت ساختمان'] = {'match': True, 'score': ori_score, 'count': len(common_build_ori)}

        # 🆕 جهت واحد
        dup_unit_ori = set(dup.preferred_unit_orientations.values_list('id', flat=True))
        new_unit_ori = set([int(o) for o in preferred_unit_orientations]) if preferred_unit_orientations else set()
        if new_unit_ori and dup_unit_ori:
            common_unit_ori = new_unit_ori & dup_unit_ori
            if common_unit_ori:
                ori_score = min(6, len(common_unit_ori) * 3)
                score += ori_score
                match_details['جهت واحد'] = {'match': True, 'score': ori_score, 'count': len(common_unit_ori)}

        # 🆕 وضعیت واحد
        dup_cond = set(dup.preferred_unit_conditions.values_list('id', flat=True))
        new_cond = set([int(c) for c in preferred_unit_conditions]) if preferred_unit_conditions else set()
        if new_cond and dup_cond:
            common_cond = new_cond & dup_cond
            if common_cond:
                cond_score = min(5, len(common_cond) * 2)
                score += cond_score
                match_details['وضعیت واحد'] = {'match': True, 'score': cond_score, 'count': len(common_cond)}

        # 🆕 انواع سند
        dup_doc = set(dup.preferred_document_types.values_list('id', flat=True))
        new_doc = set([int(d) for d in preferred_document_types]) if preferred_document_types else set()
        if new_doc and dup_doc:
            common_doc = new_doc & dup_doc
            if common_doc:
                doc_score = min(5, len(common_doc) * 2)
                score += doc_score
                match_details['انواع سند'] = {'match': True, 'score': doc_score, 'count': len(common_doc)}

        # 🆕 انواع مالکیت سند
        dup_own_doc = set(dup.preferred_ownership_document_types.values_list('id', flat=True))
        new_own_doc = set([int(o) for o in preferred_ownership_document_types]) if preferred_ownership_document_types else set()
        if new_own_doc and dup_own_doc:
            common_own_doc = new_own_doc & dup_own_doc
            if common_own_doc:
                own_doc_score = min(5, len(common_own_doc) * 2)
                score += own_doc_score
                match_details['نوع مالکیت سند'] = {'match': True, 'score': own_doc_score, 'count': len(common_own_doc)}

        # 🆕 نیاز به پایان کار
        if need_completion_certificate is not None and dup.need_completion_certificate == need_completion_certificate:
            score += 4
            match_details['نیاز به پایان کار'] = {'match': True, 'score': 4}

        # 🆕 نیاز به سند
        if need_document is not None and dup.need_document == need_document:
            score += 4
            match_details['نیاز به سند'] = {'match': True, 'score': 4}

        # بودجه
        if budget_min and budget_max and dup.budget_min and dup.budget_max:
            try:
                if (int(budget_min) >= dup.budget_min * 0.7 and int(budget_min) <= dup.budget_max * 1.3) or \
                        (int(budget_max) >= dup.budget_min * 0.7 and int(budget_max) <= dup.budget_max * 1.3):
                    score += 8
                    match_details['بودجه'] = {'match': True, 'score': 8}
            except (ValueError, TypeError):
                pass

        # متراژ
        if min_area and max_area and dup.min_area and dup.max_area:
            try:
                if (float(min_area) >= dup.min_area * 0.7 and float(min_area) <= dup.max_area * 1.3) or \
                        (float(max_area) >= dup.min_area * 0.7 and float(max_area) <= dup.max_area * 1.3):
                    score += 8
                    match_details['متراژ'] = {'match': True, 'score': 8}
            except (ValueError, TypeError):
                pass

        # 🆕 محدوده طبقه
        if preferred_min_floor and preferred_max_floor and dup.preferred_min_floor and dup.preferred_max_floor:
            try:
                if (int(preferred_min_floor) >= dup.preferred_min_floor - 1 and int(preferred_min_floor) <= dup.preferred_max_floor + 1) or \
                        (int(preferred_max_floor) >= dup.preferred_min_floor - 1 and int(preferred_max_floor) <= dup.preferred_max_floor + 1):
                    score += 5
                    match_details['طبقه'] = {'match': True, 'score': 5}
            except (ValueError, TypeError):
                pass

        # 🆕 محدوده تعداد طبقات ساختمان
        if preferred_min_total_floors and preferred_max_total_floors and dup.preferred_min_total_floors and dup.preferred_max_total_floors:
            try:
                if (int(preferred_min_total_floors) >= dup.preferred_min_total_floors - 1 and int(preferred_min_total_floors) <= dup.preferred_max_total_floors + 1) or \
                        (int(preferred_max_total_floors) >= dup.preferred_min_total_floors - 1 and int(preferred_max_total_floors) <= dup.preferred_max_total_floors + 1):
                    score += 5
                    match_details['تعداد طبقات'] = {'match': True, 'score': 5}
            except (ValueError, TypeError):
                pass

        # 🆕 محدوده واحد در طبقه
        if preferred_min_units_per_floor and preferred_max_units_per_floor and dup.preferred_min_units_per_floor and dup.preferred_max_units_per_floor:
            try:
                if (int(preferred_min_units_per_floor) >= dup.preferred_min_units_per_floor - 1 and int(preferred_min_units_per_floor) <= dup.preferred_max_units_per_floor + 1) or \
                        (int(preferred_max_units_per_floor) >= dup.preferred_min_units_per_floor - 1 and int(preferred_max_units_per_floor) <= dup.preferred_max_units_per_floor + 1):
                    score += 5
                    match_details['واحد در طبقه'] = {'match': True, 'score': 5}
            except (ValueError, TypeError):
                pass

        # 🆕 محدوده دانگ
        if preferred_dong_min and preferred_dong_max and dup.preferred_dong_min and dup.preferred_dong_max:
            try:
                if (int(preferred_dong_min) >= dup.preferred_dong_min - 1 and int(preferred_dong_min) <= dup.preferred_dong_max + 1) or \
                        (int(preferred_dong_max) >= dup.preferred_dong_min - 1 and int(preferred_dong_max) <= dup.preferred_dong_max + 1):
                    score += 5
                    match_details['دانگ'] = {'match': True, 'score': 5}
            except (ValueError, TypeError):
                pass

        if score >= 30:
            duplicate_results.append({
                'id': str(dup.id),
                'full_name': dup.full_name,
                'mobile': dup.user.mobile,
                'customer_type': dup.get_customer_type_display(),
                'status': dup.get_status_display(),
                'created_at': dup.created_at.strftime('%Y/%m/%d'),
                'similarity_score': score,
                'match_details': match_details,
                'budget': dup.get_budget_display(),
                'preferred_areas': dup.get_preferred_areas_display(),
                'property_types': dup.get_property_types_display(),
                'requirements': dup.get_requirements_display(),
                'primary_usage': dup.primary_usage.name if dup.primary_usage else None,
            })

    duplicate_results.sort(key=lambda x: x['similarity_score'], reverse=True)

    duplicate_check_id = None
    if duplicate_results:
        try:
            if customer_id:
                duplicate_check, created = DuplicateCheck.objects.update_or_create(
                    check_type=DuplicateCheck.CheckType.CUSTOMER,
                    check_id=customer_id,
                    defaults={
                        'duplicate_ids': [d['id'] for d in duplicate_results],
                        'duplicate_data': duplicate_results,
                        'similarity_score': duplicate_results[0]['similarity_score'],
                        'match_details': {'total_candidates': len(duplicate_results)},
                        'status': DuplicateCheck.Status.PENDING,
                        'checked_by': None,
                        'checked_at': None,
                        'reviewer_note': None,
                    }
                )
                duplicate_check_id = str(duplicate_check.id)
            else:
                duplicate_check = DuplicateCheck.objects.create(
                    check_type=DuplicateCheck.CheckType.CUSTOMER,
                    check_id=None,
                    duplicate_ids=[d['id'] for d in duplicate_results],
                    duplicate_data=duplicate_results,
                    similarity_score=duplicate_results[0]['similarity_score'],
                    match_details={'total_candidates': len(duplicate_results)}
                )
                duplicate_check_id = str(duplicate_check.id)
        except Exception as e:
            print(f"Error saving duplicate check: {e}")

    return {
        'has_duplicate': len(duplicate_results) > 0,
        'duplicates': duplicate_results,
        'duplicate_check_id': duplicate_check_id,
        'count': len(duplicate_results)
    }


def check_property_duplicate_logic(property_data, property_id=None):
    """
    منطق بررسی تکراری فایل (ملک) (قابل استفاده در ویوها)
    بر اساس: آدرس، موقعیت مکانی، متراژ، نوع ملک، قیمت،
    و فیلدهای جدید شامل کاربری‌ها، واحد در طبقه، جهت‌ها، وضعیت واحد،
    پایان کار، سند، نوع سند، نوع مالکیت سند، دانگ

    Args:
        property_data: دیکشنری اطلاعات ملک
        property_id: شناسه ملک (اختیاری - برای به‌روزرسانی رکورد)

    Returns:
        dict: شامل اطلاعات تکراری
    """
    address = property_data.get('address', '')
    province_id = property_data.get('province_id')
    city_id = property_data.get('city_id')
    neighborhood_id = property_data.get('neighborhood_id')
    property_type_id = property_data.get('property_type_id')
    area = property_data.get('area')
    price = property_data.get('price')
    rent_price = property_data.get('rent_price')
    rooms = property_data.get('rooms')
    contract_type = property_data.get('contract_type')
    # 🆕 فیلدهای جدید
    primary_usage_id = property_data.get('primary_usage_id')
    usage_type_ids = property_data.get('usage_type_ids', [])
    units_per_floor = property_data.get('units_per_floor')
    building_orientation_id = property_data.get('building_orientation_id')
    unit_orientation_id = property_data.get('unit_orientation_id')
    unit_condition_id = property_data.get('unit_condition_id')
    has_completion_certificate = property_data.get('has_completion_certificate')
    has_document = property_data.get('has_document')
    document_type_id = property_data.get('document_type_id')
    ownership_document_type_id = property_data.get('ownership_document_type_id')
    dong = property_data.get('dong')

    if not address and not city_id and not neighborhood_id and not property_type_id:
        return {
            'has_duplicate': False,
            'duplicates': [],
            'duplicate_check_id': None,
            'count': 0
        }

    query = Q(is_active=True)

    if province_id:
        query &= Q(province_id=province_id)
    if city_id:
        query &= Q(city_id=city_id)
    if neighborhood_id:
        query &= Q(neighborhood_id=neighborhood_id)
    if property_type_id:
        query &= Q(property_type_id=property_type_id)
    if contract_type:
        query &= Q(contract_type=contract_type)
    # 🆕 فیلترهای جدید
    if primary_usage_id:
        query &= Q(primary_usage_id=primary_usage_id)
    if usage_type_ids:
        query &= Q(usage_types__in=usage_type_ids)
    if building_orientation_id:
        query &= Q(building_orientation_id=building_orientation_id)
    if unit_orientation_id:
        query &= Q(unit_orientation_id=unit_orientation_id)
    if unit_condition_id:
        query &= Q(unit_condition_id=unit_condition_id)
    if has_completion_certificate is not None:
        query &= Q(has_completion_certificate=has_completion_certificate)
    if has_document is not None:
        query &= Q(has_document=has_document)
    if document_type_id:
        query &= Q(document_type_id=document_type_id)
    if ownership_document_type_id:
        query &= Q(ownership_document_type_id=ownership_document_type_id)

    # محدوده‌های عددی
    if units_per_floor is not None:
        try:
            u = int(units_per_floor)
            query &= Q(units_per_floor__gte=u - 1, units_per_floor__lte=u + 1)
        except (ValueError, TypeError):
            pass

    if dong is not None:
        try:
            d = int(dong)
            query &= Q(dong__gte=d - 1, dong__lte=d + 1)
        except (ValueError, TypeError):
            pass

    if address:
        address_parts = address.split()
        if len(address_parts) > 2:
            for part in address_parts[:3]:
                if len(part) > 3:
                    query &= Q(address__icontains=part)

    similar_properties = Property.objects.filter(
        query
    ).exclude(status="pending").select_related(
        'property_type', 'province', 'city', 'neighborhood', 'owner',
        'primary_usage', 'unit_condition', 'building_orientation',
        'unit_orientation', 'document_type', 'ownership_document_type'
    ).prefetch_related(
        'usage_types', 'requirements'
    ).distinct().order_by('-created_at')

    duplicate_results = []
    for dup in similar_properties:
        if property_id and str(dup.id) == str(property_id):
            continue

        score = 0
        match_details = {}

        # محله (امتیاز بالا)
        if neighborhood_id and dup.neighborhood_id == int(neighborhood_id):
            score += 20
            match_details['محله'] = {'match': True, 'score': 20}
        elif city_id and dup.city_id == int(city_id):
            score += 10
            match_details['شهر'] = {'match': True, 'score': 10}
        elif province_id and dup.province_id == int(province_id):
            score += 5
            match_details['استان'] = {'match': True, 'score': 5}

        # نوع ملک
        if property_type_id and dup.property_type_id == int(property_type_id):
            score += 12
            match_details['نوع ملک'] = {'match': True, 'score': 12}

        # 🆕 کاربری سندی
        if primary_usage_id and dup.primary_usage_id == int(primary_usage_id):
            score += 8
            match_details['کاربری سندی'] = {'match': True, 'score': 8}

        # 🆕 کاربری‌های فرعی
        if usage_type_ids:
            dup_usages = set(dup.usage_types.values_list('id', flat=True))
            new_usages = set([int(u) for u in usage_type_ids])
            common_usages = new_usages & dup_usages
            if common_usages:
                usage_score = min(8, len(common_usages) * 3)
                score += usage_score
                match_details['کاربری‌ها'] = {'match': True, 'score': usage_score, 'count': len(common_usages)}

        # متراژ
        if area and dup.area:
            try:
                area_float = float(area)
                if area_float >= dup.area * 0.8 and area_float <= dup.area * 1.2:
                    score += 12
                    match_details['متراژ'] = {'match': True, 'score': 12}
                elif area_float >= dup.area * 0.6 and area_float <= dup.area * 1.4:
                    score += 5
                    match_details['متراژ'] = {'match': True, 'score': 5}
            except (ValueError, TypeError):
                pass

        # قیمت
        if price and dup.price:
            try:
                price_int = int(price)
                if price_int >= dup.price * 0.7 and price_int <= dup.price * 1.3:
                    score += 12
                    match_details['قیمت'] = {'match': True, 'score': 12}
                elif price_int >= dup.price * 0.5 and price_int <= dup.price * 1.5:
                    score += 5
                    match_details['قیمت'] = {'match': True, 'score': 5}
            except (ValueError, TypeError):
                pass

        # اجاره
        if rent_price and dup.rent_price:
            try:
                rent_int = int(rent_price)
                if rent_int >= dup.rent_price * 0.7 and rent_int <= dup.rent_price * 1.3:
                    score += 12
                    match_details['اجاره'] = {'match': True, 'score': 12}
                elif rent_int >= dup.rent_price * 0.5 and rent_int <= dup.rent_price * 1.5:
                    score += 5
                    match_details['اجاره'] = {'match': True, 'score': 5}
            except (ValueError, TypeError):
                pass

        # تعداد اتاق
        if rooms and dup.rooms is not None:
            try:
                rooms_int = int(rooms)
                if rooms_int == dup.rooms:
                    score += 5
                    match_details['اتاق'] = {'match': True, 'score': 5}
                elif abs(rooms_int - dup.rooms) <= 1:
                    score += 3
                    match_details['اتاق'] = {'match': True, 'score': 3}
            except (ValueError, TypeError):
                pass

        # نوع قرارداد
        if contract_type and dup.contract_type == contract_type:
            score += 5
            match_details['نوع قرارداد'] = {'match': True, 'score': 5}

        # آدرس
        if address and dup.address:
            address_parts_set = set(address.split())
            dup_address_parts_set = set(dup.address.split())
            if address_parts_set and dup_address_parts_set:
                address_similarity = len(address_parts_set & dup_address_parts_set) / max(len(address_parts_set),
                                                                                          len(dup_address_parts_set))
                if address_similarity > 0.7:
                    score += 8
                    match_details['آدرس'] = {'match': True, 'score': 8,
                                             'similarity': round(address_similarity * 100, 0)}
                elif address_similarity > 0.4:
                    score += 4
                    match_details['آدرس'] = {'match': True, 'score': 4,
                                             'similarity': round(address_similarity * 100, 0)}

        # 🆕 واحد در طبقه
        if units_per_floor and dup.units_per_floor is not None:
            try:
                u = int(units_per_floor)
                if u == dup.units_per_floor:
                    score += 5
                    match_details['واحد در طبقه'] = {'match': True, 'score': 5}
                elif abs(u - dup.units_per_floor) <= 1:
                    score += 3
                    match_details['واحد در طبقه'] = {'match': True, 'score': 3}
            except (ValueError, TypeError):
                pass

        # 🆕 جهت ساختمان
        if building_orientation_id and dup.building_orientation_id == int(building_orientation_id):
            score += 4
            match_details['جهت ساختمان'] = {'match': True, 'score': 4}

        # 🆕 جهت واحد
        if unit_orientation_id and dup.unit_orientation_id == int(unit_orientation_id):
            score += 4
            match_details['جهت واحد'] = {'match': True, 'score': 4}

        # 🆕 وضعیت واحد
        if unit_condition_id and dup.unit_condition_id == int(unit_condition_id):
            score += 4
            match_details['وضعیت واحد'] = {'match': True, 'score': 4}

        # 🆕 پایان کار
        if has_completion_certificate is not None and dup.has_completion_certificate == has_completion_certificate:
            score += 3
            match_details['پایان کار'] = {'match': True, 'score': 3}

        # 🆕 سند
        if has_document is not None and dup.has_document == has_document:
            score += 3
            match_details['سند'] = {'match': True, 'score': 3}

        # 🆕 نوع سند
        if document_type_id and dup.document_type_id == int(document_type_id):
            score += 3
            match_details['نوع سند'] = {'match': True, 'score': 3}

        # 🆕 نوع مالکیت سند
        if ownership_document_type_id and dup.ownership_document_type_id == int(ownership_document_type_id):
            score += 3
            match_details['نوع مالکیت سند'] = {'match': True, 'score': 3}

        # 🆕 دانگ
        if dong and dup.dong is not None:
            try:
                d = int(dong)
                if d == dup.dong:
                    score += 4
                    match_details['دانگ'] = {'match': True, 'score': 4}
                elif abs(d - dup.dong) <= 1:
                    score += 2
                    match_details['دانگ'] = {'match': True, 'score': 2}
            except (ValueError, TypeError):
                pass

        if score >= 30:
            duplicate_results.append({
                'id': str(dup.id),
                'title': dup.title or 'بدون عنوان',
                'address': dup.address or '---',
                'property_type': dup.property_type.name if dup.property_type else '---',
                'city': dup.city.name if dup.city else '---',
                'neighborhood': dup.neighborhood.name if dup.neighborhood else '---',
                'area': dup.area,
                'price': dup.formatted_price if dup.price else None,
                'rent': dup.formatted_rent if dup.rent_price else None,
                'contract_type': dup.get_contract_type_display(),
                'status': dup.get_status_display(),
                'owner': dup.owner_name,
                'created_at': dup.created_at.strftime('%Y/%m/%d'),
                'similarity_score': score,
                'match_details': match_details,
                'primary_usage': dup.primary_usage.name if dup.primary_usage else None,
                'unit_condition': dup.unit_condition.name if dup.unit_condition else None,
                'building_orientation': dup.building_orientation.name if dup.building_orientation else None,
                'unit_orientation': dup.unit_orientation.name if dup.unit_orientation else None,
                'dong': dup.dong,
                'has_completion_certificate': dup.has_completion_certificate,
                'has_document': dup.has_document,
            })

    duplicate_results.sort(key=lambda x: x['similarity_score'], reverse=True)

    duplicate_check_id = None
    if duplicate_results:
        try:
            if property_id:
                duplicate_check, created = DuplicateCheck.objects.update_or_create(
                    check_type=DuplicateCheck.CheckType.PROPERTY,
                    check_id=property_id,
                    defaults={
                        'duplicate_ids': [d['id'] for d in duplicate_results],
                        'duplicate_data': duplicate_results,
                        'similarity_score': duplicate_results[0]['similarity_score'],
                        'match_details': {'total_candidates': len(duplicate_results)},
                        'status': DuplicateCheck.Status.PENDING,
                        'checked_by': None,
                        'checked_at': None,
                        'reviewer_note': None,
                    }
                )
                duplicate_check_id = str(duplicate_check.id)
            else:
                duplicate_check = DuplicateCheck.objects.create(
                    check_type=DuplicateCheck.CheckType.PROPERTY,
                    check_id=None,
                    duplicate_ids=[d['id'] for d in duplicate_results],
                    duplicate_data=duplicate_results,
                    similarity_score=duplicate_results[0]['similarity_score'],
                    match_details={'total_candidates': len(duplicate_results)}
                )
                duplicate_check_id = str(duplicate_check.id)
        except Exception as e:
            print(f"Error saving duplicate check: {e}")

    return {
        'has_duplicate': len(duplicate_results) > 0,
        'duplicates': duplicate_results,
        'duplicate_check_id': duplicate_check_id,
        'count': len(duplicate_results)
    }


# ============================================================
# 🔍 APIهای بررسی تکراری (برای فرم‌ها)
# ============================================================

@login_required
def check_customer_duplicate(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "check_duplicate")
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    customer_data = {
        'customer_type': request.POST.get('customer_type'),
        'preferred_cities': request.POST.getlist('preferred_cities[]'),
        'preferred_neighborhoods': request.POST.getlist('preferred_neighborhoods[]'),
        'preferred_property_types': request.POST.getlist('preferred_property_types[]'),
        'preferred_requirements': request.POST.getlist('preferred_requirements[]'),
        'budget_min': request.POST.get('budget_min'),
        'budget_max': request.POST.get('budget_max'),
        'min_area': request.POST.get('min_area'),
        'max_area': request.POST.get('max_area'),
        'min_rooms': request.POST.get('min_rooms'),
        'max_rooms': request.POST.get('max_rooms'),
        # 🆕 فیلدهای جدید
        'primary_usage_id': request.POST.get('primary_usage_id'),
        'preferred_usage_types': request.POST.getlist('preferred_usage_types[]'),
        'preferred_building_orientations': request.POST.getlist('preferred_building_orientations[]'),
        'preferred_unit_orientations': request.POST.getlist('preferred_unit_orientations[]'),
        'preferred_unit_conditions': request.POST.getlist('preferred_unit_conditions[]'),
        'preferred_document_types': request.POST.getlist('preferred_document_types[]'),
        'preferred_ownership_document_types': request.POST.getlist('preferred_ownership_document_types[]'),
        'need_completion_certificate': request.POST.get('need_completion_certificate'),
        'need_document': request.POST.get('need_document'),
        'preferred_min_floor': request.POST.get('preferred_min_floor'),
        'preferred_max_floor': request.POST.get('preferred_max_floor'),
        'preferred_min_total_floors': request.POST.get('preferred_min_total_floors'),
        'preferred_max_total_floors': request.POST.get('preferred_max_total_floors'),
        'preferred_min_units_per_floor': request.POST.get('preferred_min_units_per_floor'),
        'preferred_max_units_per_floor': request.POST.get('preferred_max_units_per_floor'),
        'preferred_dong_min': request.POST.get('preferred_dong_min'),
        'preferred_dong_max': request.POST.get('preferred_dong_max'),
    }

    customer_id = request.POST.get('customer_id')

    result = check_customer_duplicate_logic(customer_data, customer_id)
    return JsonResponse(result)


@login_required
def check_property_duplicate(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "check_duplicate")
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    property_data = {
        'address': request.POST.get('address', ''),
        'province_id': request.POST.get('province_id'),
        'city_id': request.POST.get('city_id'),
        'neighborhood_id': request.POST.get('neighborhood_id'),
        'property_type_id': request.POST.get('property_type_id'),
        'area': request.POST.get('area'),
        'price': request.POST.get('price'),
        'rent_price': request.POST.get('rent_price'),
        'rooms': request.POST.get('rooms'),
        'contract_type': request.POST.get('contract_type'),
        # 🆕 فیلدهای جدید
        'primary_usage_id': request.POST.get('primary_usage_id'),
        'usage_type_ids': request.POST.getlist('usage_type_ids[]'),
        'units_per_floor': request.POST.get('units_per_floor'),
        'building_orientation_id': request.POST.get('building_orientation_id'),
        'unit_orientation_id': request.POST.get('unit_orientation_id'),
        'unit_condition_id': request.POST.get('unit_condition_id'),
        'has_completion_certificate': request.POST.get('has_completion_certificate'),
        'has_document': request.POST.get('has_document'),
        'document_type_id': request.POST.get('document_type_id'),
        'ownership_document_type_id': request.POST.get('ownership_document_type_id'),
        'dong': request.POST.get('dong'),
    }

    property_id = request.POST.get('property_id')

    result = check_property_duplicate_logic(property_data, property_id)
    return JsonResponse(result)


@login_required
def handle_duplicate_check(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "check_duplicate")
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    check_id = request.POST.get('check_id')
    action = request.POST.get('action')
    note = request.POST.get('note', '')

    if not check_id:
        return JsonResponse({'error': 'شناسه بررسی یافت نشد'}, status=400)

    duplicate_check = get_object_or_404(DuplicateCheck, pk=check_id)

    if action == 'confirm':
        duplicate_check.confirm_duplicate(user, note)
        return JsonResponse({
            'success': True,
            'message': 'تکراری بودن تایید شد',
            'status': 'confirmed'
        })
    elif action == 'reject':
        duplicate_check.reject_duplicate(user, note)
        return JsonResponse({
            'success': True,
            'message': 'تکراری بودن رد شد',
            'status': 'rejected'
        })
    elif action == 'false':
        duplicate_check.mark_as_false(user, note)
        return JsonResponse({
            'success': True,
            'message': 'تکراری نیست',
            'status': 'false'
        })
    else:
        return JsonResponse({'error': 'عملیات نامعتبر'}, status=400)


@login_required
def get_duplicate_check_details(request, check_id):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "check_duplicate")
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    duplicate_check = get_object_or_404(DuplicateCheck, pk=check_id)

    return JsonResponse({
        'success': True,
        'data': {
            'id': str(duplicate_check.id),
            'check_type': duplicate_check.get_check_type_display(),
            'status': duplicate_check.get_status_display(),
            'status_code': duplicate_check.status,
            'similarity_score': duplicate_check.similarity_score,
            'duplicates': duplicate_check.duplicate_data,
            'match_details': duplicate_check.match_details,
            'created_at': duplicate_check.created_at.strftime('%Y/%m/%d %H:%M'),
            'checked_at': duplicate_check.checked_at.strftime('%Y/%m/%d %H:%M') if duplicate_check.checked_at else None,
            'checked_by': duplicate_check.checked_by.get_full_name() if duplicate_check.checked_by else None,
            'reviewer_note': duplicate_check.reviewer_note,
        }
    })


# ============================================================
# 🔍 APIهای دریافت تکراری برای مودال‌ها (جدید)
# ============================================================

@login_required
def get_customer_duplicates_ajax(request, customer_id):
    """
    دریافت لیست مشتریان تکراری یک مشتری (API برای مودال)
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "check_duplicate")
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    try:
        customer = get_object_or_404(Customer, pk=customer_id, is_active=True)

        duplicate_check = DuplicateCheck.objects.filter(
            check_type=DuplicateCheck.CheckType.CUSTOMER,
            check_id=str(customer_id)
        ).order_by('-created_at').first()

        if duplicate_check:
            filtered_duplicates = []
            for dup in duplicate_check.duplicate_data:
                if dup.get('id') != str(customer_id):
                    filtered_duplicates.append(dup)

            return JsonResponse({
                'success': True,
                'data': {
                    'duplicates': filtered_duplicates,
                    'similarity_score': duplicate_check.similarity_score,
                    'match_details': duplicate_check.match_details,
                    'status': duplicate_check.get_status_display(),
                    'status_code': duplicate_check.status,
                    'created_at': duplicate_check.created_at.strftime('%Y/%m/%d %H:%M'),
                    'checked_at': duplicate_check.checked_at.strftime(
                        '%Y/%m/%d %H:%M') if duplicate_check.checked_at else None,
                    'checked_by': duplicate_check.checked_by.get_full_name() if duplicate_check.checked_by else None,
                    'reviewer_note': duplicate_check.reviewer_note,
                }
            })
        else:
            # محاسبه مجدد با داده‌های جدید
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
                # 🆕
                'primary_usage_id': str(customer.primary_usage_id) if customer.primary_usage_id else None,
                'preferred_usage_types': list(customer.preferred_usage_types.values_list('id', flat=True)),
                'preferred_building_orientations': list(customer.preferred_building_orientations.values_list('id', flat=True)),
                'preferred_unit_orientations': list(customer.preferred_unit_orientations.values_list('id', flat=True)),
                'preferred_unit_conditions': list(customer.preferred_unit_conditions.values_list('id', flat=True)),
                'preferred_document_types': list(customer.preferred_document_types.values_list('id', flat=True)),
                'preferred_ownership_document_types': list(customer.preferred_ownership_document_types.values_list('id', flat=True)),
                'need_completion_certificate': customer.need_completion_certificate,
                'need_document': customer.need_document,
                'preferred_min_floor': customer.preferred_min_floor,
                'preferred_max_floor': customer.preferred_max_floor,
                'preferred_min_total_floors': customer.preferred_min_total_floors,
                'preferred_max_total_floors': customer.preferred_max_total_floors,
                'preferred_min_units_per_floor': customer.preferred_min_units_per_floor,
                'preferred_max_units_per_floor': customer.preferred_max_units_per_floor,
                'preferred_dong_min': customer.preferred_dong_min,
                'preferred_dong_max': customer.preferred_dong_max,
            }

            duplicate_result = check_customer_duplicate_logic(customer_data, str(customer_id))

            filtered_duplicates = []
            for dup in duplicate_result.get('duplicates', []):
                if dup.get('id') != str(customer_id):
                    filtered_duplicates.append(dup)

            return JsonResponse({
                'success': True,
                'data': {
                    'duplicates': filtered_duplicates,
                    'similarity_score': duplicate_result.get('similarity_score', 0),
                    'status': 'در انتظار بررسی',
                    'status_code': 'pending',
                    'created_at': timezone.now().strftime('%Y/%m/%d %H:%M'),
                }
            })

    except Customer.DoesNotExist:
        return JsonResponse({'error': 'مشتری یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_property_duplicates_ajax(request, property_id):
    """
    دریافت لیست فایل‌های تکراری یک ملک (API برای مودال)
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "check_duplicate")
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    try:
        property_obj = get_object_or_404(Property, pk=property_id, is_active=True)

        duplicate_check = DuplicateCheck.objects.filter(
            check_type=DuplicateCheck.CheckType.PROPERTY,
            check_id=str(property_id)
        ).order_by('-created_at').first()

        if duplicate_check:
            filtered_duplicates = []
            for dup in duplicate_check.duplicate_data:
                if dup.get('id') != str(property_id):
                    filtered_duplicates.append(dup)

            return JsonResponse({
                'success': True,
                'data': {
                    'duplicates': filtered_duplicates,
                    'similarity_score': duplicate_check.similarity_score,
                    'match_details': duplicate_check.match_details,
                    'status': duplicate_check.get_status_display(),
                    'status_code': duplicate_check.status,
                    'created_at': duplicate_check.created_at.strftime('%Y/%m/%d %H:%M'),
                    'checked_at': duplicate_check.checked_at.strftime(
                        '%Y/%m/%d %H:%M') if duplicate_check.checked_at else None,
                    'checked_by': duplicate_check.checked_by.get_full_name() if duplicate_check.checked_by else None,
                    'reviewer_note': duplicate_check.reviewer_note,
                }
            })
        else:
            # محاسبه مجدد با داده‌های جدید
            property_data = {
                'address': property_obj.address or '',
                'province_id': str(property_obj.province_id) if property_obj.province_id else None,
                'city_id': str(property_obj.city_id) if property_obj.city_id else None,
                'neighborhood_id': str(property_obj.neighborhood_id) if property_obj.neighborhood_id else None,
                'property_type_id': str(property_obj.property_type_id) if property_obj.property_type_id else None,
                'area': str(property_obj.area) if property_obj.area else None,
                'price': str(property_obj.price) if property_obj.price else None,
                'rent_price': str(property_obj.rent_price) if property_obj.rent_price else None,
                'rooms': property_obj.rooms,
                'contract_type': property_obj.contract_type,
                # 🆕
                'primary_usage_id': str(property_obj.primary_usage_id) if property_obj.primary_usage_id else None,
                'usage_type_ids': list(property_obj.usage_types.values_list('id', flat=True)),
                'units_per_floor': property_obj.units_per_floor,
                'building_orientation_id': str(property_obj.building_orientation_id) if property_obj.building_orientation_id else None,
                'unit_orientation_id': str(property_obj.unit_orientation_id) if property_obj.unit_orientation_id else None,
                'unit_condition_id': str(property_obj.unit_condition_id) if property_obj.unit_condition_id else None,
                'has_completion_certificate': property_obj.has_completion_certificate,
                'has_document': property_obj.has_document,
                'document_type_id': str(property_obj.document_type_id) if property_obj.document_type_id else None,
                'ownership_document_type_id': str(property_obj.ownership_document_type_id) if property_obj.ownership_document_type_id else None,
                'dong': property_obj.dong,
            }

            duplicate_result = check_property_duplicate_logic(property_data, str(property_id))

            filtered_duplicates = []
            for dup in duplicate_result.get('duplicates', []):
                if dup.get('id') != str(property_id):
                    filtered_duplicates.append(dup)

            return JsonResponse({
                'success': True,
                'data': {
                    'duplicates': filtered_duplicates,
                    'similarity_score': duplicate_result.get('similarity_score', 0),
                    'status': 'در انتظار بررسی',
                    'status_code': 'pending',
                    'created_at': timezone.now().strftime('%Y/%m/%d %H:%M'),
                }
            })

    except Property.DoesNotExist:
        return JsonResponse({'error': 'ملک یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)