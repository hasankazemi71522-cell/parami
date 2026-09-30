# estate/utils_match.py

from decimal import Decimal
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone
from .models import Customer, Property, Match


class MatchCalculator:
    """
    موتور محاسبه تطابق بین مشتری و ملک
    با پشتیبانی از فیلدهای جدید (کاربری‌ها، جهت‌ها، وضعیت واحد، سند، دانگ، پیش‌خریدار و پیش‌فروش)
    """

    WEIGHTS = {
        'location': 18,
        'price': 13,
        'area': 7,
        'rooms': 7,
        'requirements': 10,
        'property_type': 7,
        'contract': 3,
        'rent': 2,
        'ownership': 1,
        'primary_usage': 5,
        'usage_types': 5,
        'floor': 3,
        'total_floors': 2,
        'units_per_floor': 2,
        'building_orientation': 2,
        'unit_orientation': 2,
        'unit_condition': 3,
        'completion_certificate': 2,
        'document': 2,
        'document_type': 1,
        'ownership_document_type': 1,
        'dong': 2,
    }

    @classmethod
    def calculate_full_match(cls, customer, property_obj):
        scores = {
            'location': cls._calc_location(customer, property_obj),
            'price': cls._calc_price(customer, property_obj),
            'area': cls._calc_area(customer, property_obj),
            'rooms': cls._calc_rooms(customer, property_obj),
            'requirements': cls._calc_requirements(customer, property_obj),
            'property_type': cls._calc_property_type(customer, property_obj),
            'contract': cls._calc_contract(customer, property_obj),
            'rent': cls._calc_rent(customer, property_obj),
            'ownership': cls._calc_ownership(customer, property_obj),
            # 🆕 فیلدهای جدید
            'primary_usage': cls._calc_primary_usage(customer, property_obj),
            'usage_types': cls._calc_usage_types(customer, property_obj),
            'floor': cls._calc_floor(customer, property_obj),
            'total_floors': cls._calc_total_floors(customer, property_obj),
            'units_per_floor': cls._calc_units_per_floor(customer, property_obj),
            'building_orientation': cls._calc_building_orientation(customer, property_obj),
            'unit_orientation': cls._calc_unit_orientation(customer, property_obj),
            'unit_condition': cls._calc_unit_condition(customer, property_obj),
            'completion_certificate': cls._calc_completion_certificate(customer, property_obj),
            'document': cls._calc_document(customer, property_obj),
            'document_type': cls._calc_document_type(customer, property_obj),
            'ownership_document_type': cls._calc_ownership_document_type(customer, property_obj),
            'dong': cls._calc_dong(customer, property_obj),
        }

        total = 0
        for key, score in scores.items():
            weight = cls.WEIGHTS.get(key, 0)
            total += (score * weight) / 100

        total = min(round(total), 100)

        return {
            'total': total,
            'location': scores['location'],
            'price': scores['price'],
            'area': scores['area'],
            'rooms': scores['rooms'],
            'requirements': scores['requirements'],
            'property_type': scores['property_type'],
            'contract': scores['contract'],
            'rent': scores['rent'],
            'ownership': scores['ownership'],
            # 🆕
            'primary_usage': scores['primary_usage'],
            'usage_types': scores['usage_types'],
            'floor': scores['floor'],
            'total_floors': scores['total_floors'],
            'units_per_floor': scores['units_per_floor'],
            'building_orientation': scores['building_orientation'],
            'unit_orientation': scores['unit_orientation'],
            'unit_condition': scores['unit_condition'],
            'completion_certificate': scores['completion_certificate'],
            'document': scores['document'],
            'document_type': scores['document_type'],
            'ownership_document_type': scores['ownership_document_type'],
            'dong': scores['dong'],
            'details': {
                'customer': {
                    'id': str(customer.id),
                    'name': customer.full_name,
                    'type': customer.customer_type,
                },
                'property': {
                    'id': str(property_obj.id),
                    'title': property_obj.title,
                    'price': str(property_obj.price),
                    'area': property_obj.area,
                },
                'calculated_at': timezone.now().isoformat(),
            }
        }

    # ==========================================================
    # 🔧 متدهای محاسبه (موجود)
    # ==========================================================

    @staticmethod
    def _calc_location(customer, property_obj):
        if not customer.preferred_cities.exists() and not customer.preferred_neighborhoods.exists():
            return 0
        if property_obj.neighborhood is None and property_obj.city is None and property_obj.province is None:
            return 0
        if property_obj.neighborhood and customer.preferred_neighborhoods.filter(id=property_obj.neighborhood.id).exists():
            return 100
        if property_obj.city and customer.preferred_cities.filter(id=property_obj.city.id).exists():
            return 80
        if property_obj.province and customer.preferred_cities.filter(province_id=property_obj.province.id).exists():
            return 50
        return 0

    @staticmethod
    def _calc_price(customer, property_obj):
        if customer.customer_type not in ['buyer', 'pre_buyer', 'investor', 'all']:
            return 0
        if property_obj.price is None:
            return 0
        price = property_obj.price
        if isinstance(price, str):
            try:
                price = Decimal(price)
            except:
                return 0
        if not customer.budget_min and not customer.budget_max:
            return 0
        budget_min = customer.budget_min or 0
        budget_max = customer.budget_max or float('inf')
        lower_bound = budget_min * Decimal('0.85') if customer.budget_min else 0
        upper_bound = budget_max * Decimal('1.15') if customer.budget_max else float('inf')
        if lower_bound <= price <= upper_bound:
            return 100
        if price < lower_bound:
            diff = ((lower_bound - price) / lower_bound) * 100 if lower_bound > 0 else 100
            if diff <= 10:
                return 70
            elif diff <= 20:
                return 50
            elif diff <= 30:
                return 30
            return 10
        else:
            diff = ((price - upper_bound) / upper_bound) * 100 if upper_bound != float('inf') else 100
            if diff <= 10:
                return 70
            elif diff <= 20:
                return 50
            elif diff <= 30:
                return 30
            return 10

    @staticmethod
    def _calc_area(customer, property_obj):
        if property_obj.area is None:
            return 0
        area = property_obj.area
        if isinstance(area, str):
            try:
                area = float(area)
            except:
                return 0
        if not customer.min_area and not customer.max_area:
            return 0
        min_area = customer.min_area or 0
        max_area = customer.max_area or float('inf')
        lower_bound = min_area * 0.85 if customer.min_area else 0
        upper_bound = max_area * 1.15 if customer.max_area else float('inf')
        if lower_bound <= area <= upper_bound:
            return 100
        if area < lower_bound:
            diff = ((lower_bound - area) / lower_bound) * 100 if lower_bound > 0 else 100
            if diff <= 10:
                return 70
            elif diff <= 20:
                return 50
            elif diff <= 30:
                return 30
            return 10
        else:
            diff = ((area - upper_bound) / upper_bound) * 100 if upper_bound != float('inf') else 100
            if diff <= 10:
                return 70
            elif diff <= 20:
                return 50
            elif diff <= 30:
                return 30
            return 10

    @staticmethod
    def _calc_rooms(customer, property_obj):
        if not customer.min_rooms and not customer.max_rooms:
            return 0
        if customer.min_rooms and customer.max_rooms:
            if customer.min_rooms <= property_obj.rooms <= customer.max_rooms:
                return 100
            elif property_obj.rooms < customer.min_rooms:
                diff = customer.min_rooms - property_obj.rooms
                return 70 if diff == 1 else 40 if diff == 2 else 20
            else:
                diff = property_obj.rooms - customer.max_rooms
                return 70 if diff == 1 else 40 if diff == 2 else 20
        if customer.min_rooms:
            return 100 if property_obj.rooms >= customer.min_rooms else 50
        if customer.max_rooms:
            return 100 if property_obj.rooms <= customer.max_rooms else 50
        return 0

    @staticmethod
    def _calc_requirements(customer, property_obj):
        customer_reqs = set(customer.preferred_requirements.filter(is_active=True).values_list('id', flat=True))
        property_reqs = set(property_obj.requirements.filter(is_active=True).values_list('id', flat=True))
        if not customer_reqs:
            return 0
        if not property_reqs:
            return 0
        overlap = customer_reqs.intersection(property_reqs)
        return int((len(overlap) / len(customer_reqs)) * 100)

    @staticmethod
    def _calc_property_type(customer, property_obj):
        if not customer.preferred_property_types.exists():
            return 0
        if property_obj.property_type is None:
            return 0
        if customer.preferred_property_types.filter(id=property_obj.property_type.id).exists():
            return 100
        return 0

    @staticmethod
    def _calc_contract(customer, property_obj):
        """
        محاسبه امتیاز تطابق بر اساس نوع مشتری و نوع قرارداد
        پشتیبانی از گزینه‌های جدید: PRE_BUYER و PRE_SALE
        """
        customer_type = customer.customer_type
        if not customer_type:
            return 0
        contract = property_obj.contract_type
        if not contract:
            return 0

        # خریدار: فروش، پیش‌فروش، هر دو (فروش و اجاره) و مشارکت (اختیاری)
        if customer_type == 'buyer':
            if contract in ['sale', 'pre_sale', 'both']:
                return 100
            elif contract == 'rent':
                return 50  # ممکن است به اجاره هم علاقه داشته باشد
            else:
                return 0

        # پیش‌خریدار: پیش‌فروش، فروش، هر دو
        elif customer_type == 'pre_buyer':
            if contract in ['pre_sale', 'sale', 'both']:
                return 100
            elif contract == 'rent':
                return 50
            else:
                return 0

        # مستاجر
        elif customer_type == 'tenant':
            if contract in ['rent', 'both']:
                return 100
            elif contract in ['sale', 'pre_sale']:
                return 50  # ممکن است خرید هم کند
            else:
                return 0

        # سازنده
        elif customer_type == 'developer':
            if contract in ['sale', 'partnership', 'both']:
                return 100
            elif contract in ['pre_sale', 'investment']:
                return 50
            else:
                return 0

        # سرمایه‌گذار
        elif customer_type == 'investor':
            if contract in ['sale', 'investment', 'partnership', 'pre_sale']:
                return 100
            elif contract == 'both':
                return 50
            else:
                return 0

        # همه موارد
        elif customer_type == 'all':
            return 100

        return 0

    @staticmethod
    def _calc_rent(customer, property_obj):
        if customer.customer_type not in ['tenant', 'all']:
            return 0
        scores = []
        total = 0
        if customer.mortgage_min and customer.mortgage_max:
            total += 1
            if property_obj.mortgage_price:
                if customer.mortgage_min <= property_obj.mortgage_price <= customer.mortgage_max:
                    scores.append(100)
                else:
                    scores.append(50)
            else:
                scores.append(0)
        if customer.rent_min and customer.rent_max:
            total += 1
            if property_obj.rent_price:
                if customer.rent_min <= property_obj.rent_price <= customer.rent_max:
                    scores.append(100)
                else:
                    scores.append(50)
            else:
                scores.append(0)
        if total == 0:
            return 0
        return int(sum(scores) / total)

    @staticmethod
    def _calc_ownership(customer, property_obj):
        customer_type = customer.customer_type
        ownership = property_obj.ownership_type
        if not customer_type or not ownership:
            return 0
        if customer_type == 'buyer':
            return 100 if ownership in ['owner', 'lawyer'] else 50
        if customer_type == 'pre_buyer':
            return 100 if ownership in ['owner', 'lawyer'] else 50
        if customer_type == 'tenant':
            return 100 if ownership == 'tenant' else 50
        if customer_type == 'developer':
            return 100 if ownership in ['owner', 'manager'] else 50
        if customer_type in ['investor', 'all']:
            return 100
        return 0

    # ==========================================================
    # 🆕 متدهای محاسبه برای فیلدهای جدید
    # ==========================================================

    @staticmethod
    def _calc_primary_usage(customer, property_obj):
        """کاربری سندی اصلی"""
        if not customer.primary_usage:
            return 0
        if not property_obj.primary_usage:
            return 0
        return 100 if customer.primary_usage.id == property_obj.primary_usage.id else 0

    @staticmethod
    def _calc_usage_types(customer, property_obj):
        """کاربری‌های فرعی (کاربردهای ملک)"""
        customer_usages = set(customer.preferred_usage_types.filter(is_active=True).values_list('id', flat=True))
        property_usages = set(property_obj.usage_types.filter(is_active=True).values_list('id', flat=True))
        if not customer_usages:
            return 0
        if not property_usages:
            return 0
        overlap = customer_usages.intersection(property_usages)
        return int((len(overlap) / len(customer_usages)) * 100)

    @staticmethod
    def _calc_floor(customer, property_obj):
        """طبقه (محدوده مورد نظر مشتری)"""
        if not customer.preferred_min_floor and not customer.preferred_max_floor:
            return 0
        if property_obj.floor is None:
            return 0
        try:
            floor = int(property_obj.floor)
        except (ValueError, TypeError):
            return 0
        min_floor = customer.preferred_min_floor or 0
        max_floor = customer.preferred_max_floor or float('inf')
        if min_floor <= floor <= max_floor:
            return 100
        if floor < min_floor:
            diff = min_floor - floor
            return 70 if diff == 1 else 40 if diff <= 3 else 20
        else:
            diff = floor - max_floor
            return 70 if diff == 1 else 40 if diff <= 3 else 20

    @staticmethod
    def _calc_total_floors(customer, property_obj):
        """تعداد طبقات ساختمان (محدوده مورد نظر مشتری)"""
        if not customer.preferred_min_total_floors and not customer.preferred_max_total_floors:
            return 0
        if property_obj.total_floors is None:
            return 0
        total = property_obj.total_floors
        min_total = customer.preferred_min_total_floors or 0
        max_total = customer.preferred_max_total_floors or float('inf')
        if min_total <= total <= max_total:
            return 100
        if total < min_total:
            diff = min_total - total
            return 70 if diff == 1 else 40 if diff <= 3 else 20
        else:
            diff = total - max_total
            return 70 if diff == 1 else 40 if diff <= 3 else 20

    @staticmethod
    def _calc_units_per_floor(customer, property_obj):
        """تعداد واحد در طبقه (محدوده مورد نظر مشتری)"""
        if not customer.preferred_min_units_per_floor and not customer.preferred_max_units_per_floor:
            return 0
        if property_obj.units_per_floor is None:
            return 0
        units = property_obj.units_per_floor
        min_units = customer.preferred_min_units_per_floor or 0
        max_units = customer.preferred_max_units_per_floor or float('inf')
        if min_units <= units <= max_units:
            return 100
        if units < min_units:
            diff = min_units - units
            return 70 if diff == 1 else 40 if diff <= 3 else 20
        else:
            diff = units - max_units
            return 70 if diff == 1 else 40 if diff <= 3 else 20

    @staticmethod
    def _calc_building_orientation(customer, property_obj):
        """جهت ساختمان"""
        if not customer.preferred_building_orientations.exists():
            return 0
        if not property_obj.building_orientation:
            return 0
        return 100 if customer.preferred_building_orientations.filter(
            id=property_obj.building_orientation.id
        ).exists() else 0

    @staticmethod
    def _calc_unit_orientation(customer, property_obj):
        """جهت واحد"""
        if not customer.preferred_unit_orientations.exists():
            return 0
        if not property_obj.unit_orientation:
            return 0
        return 100 if customer.preferred_unit_orientations.filter(
            id=property_obj.unit_orientation.id
        ).exists() else 0

    @staticmethod
    def _calc_unit_condition(customer, property_obj):
        """وضعیت واحد"""
        if not customer.preferred_unit_conditions.exists():
            return 0
        if not property_obj.unit_condition:
            return 0
        return 100 if customer.preferred_unit_conditions.filter(
            id=property_obj.unit_condition.id
        ).exists() else 0

    @staticmethod
    def _calc_completion_certificate(customer, property_obj):
        """نیاز به پایان کار"""
        if not customer.need_completion_certificate:
            return 0
        return 100 if property_obj.has_completion_certificate else 0

    @staticmethod
    def _calc_document(customer, property_obj):
        """نیاز به سند"""
        if not customer.need_document:
            return 0
        return 100 if property_obj.has_document else 0

    @staticmethod
    def _calc_document_type(customer, property_obj):
        """نوع سند"""
        if not customer.preferred_document_types.exists():
            return 0
        if not property_obj.document_type:
            return 0
        return 100 if customer.preferred_document_types.filter(
            id=property_obj.document_type.id
        ).exists() else 0

    @staticmethod
    def _calc_ownership_document_type(customer, property_obj):
        """نوع مالکیت سند"""
        if not customer.preferred_ownership_document_types.exists():
            return 0
        if not property_obj.ownership_document_type:
            return 0
        return 100 if customer.preferred_ownership_document_types.filter(
            id=property_obj.ownership_document_type.id
        ).exists() else 0

    @staticmethod
    def _calc_dong(customer, property_obj):
        """میزان دانگ (محدوده مورد نظر مشتری)"""
        if not customer.preferred_dong_min and not customer.preferred_dong_max:
            return 0
        if property_obj.dong is None:
            return 0
        dong = property_obj.dong
        min_dong = customer.preferred_dong_min or 0
        max_dong = customer.preferred_dong_max or float('inf')
        if min_dong <= dong <= max_dong:
            return 100
        if dong < min_dong:
            diff = min_dong - dong
            return 70 if diff == 1 else 40 if diff <= 2 else 20
        else:
            diff = dong - max_dong
            return 70 if diff == 1 else 40 if diff <= 2 else 20


class MatchManager:
    """
    مدیریت تطابق‌ها - با قابلیت فراخوانی دستی
    """

    @staticmethod
    def create_or_update_match(customer, property_obj, created_by=None):
        """
        ایجاد یا به‌روزرسانی یک تطابق خاص
        - اگر رکورد جدید باشد → با introduction_status = PENDING
        - اگر رکورد موجود باشد → فقط امتیازها به‌روز می‌شوند و introduction_status تغییر نمی‌کند
        """
        match_data = MatchCalculator.calculate_full_match(customer, property_obj)

        match, created = Match.objects.get_or_create(
            customer=customer,
            property_ref=property_obj,
            defaults={
                'match_score': match_data['total'],
                'score_location': match_data['location'],
                'score_price': match_data['price'],
                'score_area': match_data['area'],
                'score_rooms': match_data['rooms'],
                'score_requirements': match_data['requirements'],
                'score_property_type': match_data['property_type'],
                'score_contract': match_data['contract'],
                'score_rent': match_data['rent'],
                'score_ownership': match_data['ownership'],
                'match_details': match_data['details'],
                'match_type': Match.MatchType.AUTO,
                'introduction_status': Match.IntroductionStatus.PENDING,
                'introduction_confirmed': False,
            }
        )

        if not created:
            match.match_score = match_data['total']
            match.score_location = match_data['location']
            match.score_price = match_data['price']
            match.score_area = match_data['area']
            match.score_rooms = match_data['rooms']
            match.score_requirements = match_data['requirements']
            match.score_property_type = match_data['property_type']
            match.score_contract = match_data['contract']
            match.score_rent = match_data['rent']
            match.score_ownership = match_data['ownership']
            match.match_details = match_data['details']
            match.match_type = Match.MatchType.AUTO
            match.save(update_fields=[
                'match_score', 'score_location', 'score_price', 'score_area',
                'score_rooms', 'score_requirements', 'score_property_type',
                'score_contract', 'score_rent', 'score_ownership',
                'match_details', 'match_type'
            ])

        if created and created_by:
            match.created_by = created_by
            match.save(update_fields=['created_by'])

        return match, created

    @staticmethod
    def calculate_and_save_matches_for_customer(customer, min_score=50, created_by=None, remove_low=True):
        """
        محاسبه و ذخیره تطابق‌های یک مشتری با تمام املاک تایید شده (CONFIRMED)
        فقط املاکی که وضعیت CONFIRMED دارند در نظر گرفته می‌شوند
        """
        properties = Property.objects.filter(
            is_active=True,
            is_visible=True,
            status=Property.Status.CONFIRMED
        )

        saved_count = 0
        updated_count = 0
        deleted_count = 0

        with transaction.atomic():
            for property_obj in properties:
                match_data = MatchCalculator.calculate_full_match(customer, property_obj)
                score = match_data['total']

                if score >= min_score:
                    match, created = MatchManager.create_or_update_match(
                        customer, property_obj, created_by
                    )
                    if created:
                        saved_count += 1
                    else:
                        updated_count += 1
                else:
                    if remove_low:
                        deleted, _ = Match.objects.filter(
                            customer=customer,
                            property_ref=property_obj
                        ).delete()
                        deleted_count += deleted

        return {
            'saved': saved_count,
            'updated': updated_count,
            'deleted': deleted_count,
            'total_checked': properties.count(),
        }

    @staticmethod
    def calculate_and_save_matches_for_property(property_obj, min_score=50, created_by=None, remove_low=True):
        """
        محاسبه و ذخیره تطابق‌های یک ملک با تمام مشتریان تایید شده (CONFIRMED)
        فقط مشتریانی که وضعیت CONFIRMED دارند در نظر گرفته می‌شوند
        """
        if property_obj.status != Property.Status.CONFIRMED:
            return {
                'saved': 0,
                'updated': 0,
                'deleted': 0,
                'total_checked': 0,
                'message': 'فایل تایید نشده است، تطابق محاسبه نشد.'
            }

        customers = Customer.objects.filter(
            is_active=True,
            status=Customer.Status.CONFIRMED
        )

        saved_count = 0
        updated_count = 0
        deleted_count = 0

        with transaction.atomic():
            for customer in customers:
                match_data = MatchCalculator.calculate_full_match(customer, property_obj)
                score = match_data['total']

                if score >= min_score:
                    match, created = MatchManager.create_or_update_match(
                        customer, property_obj, created_by
                    )
                    if created:
                        saved_count += 1
                    else:
                        updated_count += 1
                else:
                    if remove_low:
                        deleted, _ = Match.objects.filter(
                            customer=customer,
                            property_ref=property_obj
                        ).delete()
                        deleted_count += deleted

        return {
            'saved': saved_count,
            'updated': updated_count,
            'deleted': deleted_count,
            'total_checked': customers.count(),
        }

    @staticmethod
    def get_best_matches_for_customer(customer, limit=10, min_score=50):
        return Match.objects.filter(
            customer=customer,
            match_score__gte=min_score
        ).order_by('-match_score')[:limit]

    @staticmethod
    def get_best_matches_for_property(property_obj, limit=10, min_score=50):
        return Match.objects.filter(
            property_ref=property_obj,
            match_score__gte=min_score
        ).order_by('-match_score')[:limit]

    @staticmethod
    def get_match_statistics(customer):
        matches = Match.objects.filter(customer=customer)
        return {
            'total': matches.count(),
            'high_match': matches.filter(match_score__gte=70).count(),
            'good_match': matches.filter(match_score__range=(50, 69)).count(),
            'low_match': matches.filter(match_score__lt=50).count(),
            'avg_score': matches.aggregate(avg=Avg('match_score')).get('avg', 0) or 0,
            'pending': matches.filter(status=Match.Status.PENDING).count(),
            'interested': matches.filter(status=Match.Status.INTERESTED).count(),
            'converted': matches.filter(status=Match.Status.CONVERTED).count(),
            'rejected': matches.filter(status=Match.Status.REJECTED).count(),
        }