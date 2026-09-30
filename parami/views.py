from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db.models import Q, Count
from django.utils import timezone
from account.models import User
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from estate.models import Property, Customer, Province, City, Neighborhood, PropertyType, Requirement
from transaction.models import Contract, CommissionSetting, AfterSalesService
from django.shortcuts import get_object_or_404

user = get_user_model()


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def home_page(request):
    if request.user.is_authenticated:
        this_user = request.user
    else:
        this_user = "none"

    # آمار کلی (می‌تواند شامل همه فایل‌ها باشد یا فقط تأییدشده‌ها - بنا به سلیقه)
    total_properties = Property.objects.filter(
        is_active=True, is_visible=True, status=Property.Status.CONFIRMED
    ).count()
    total_customers = Customer.objects.filter(is_active=True).count()
    total_contracts = Contract.objects.filter(status=Contract.Status.COMPLETED).count()

    # مشتریان امروز
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    today_customers = Customer.objects.filter(
        is_active=True,
        created_at__range=(today_start, today_end)
    ).count()

    # ====== دریافت لیست فایل‌های تأییدشده برای نمایش در صفحه اصلی ======
    properties = Property.objects.filter(
        is_active=True,
        is_visible=True,
        status=Property.Status.CONFIRMED  # <-- فقط تایید شده
    ).select_related(
        'property_type', 'province', 'city', 'neighborhood', 'owner'
    ).order_by('-created_at')[:9]

    # ====== دریافت لیست استان‌ها برای جستجو ======
    provinces = Province.objects.all().order_by('name')

    # ====== پاسخ به درخواست‌های AJAX ======
    if is_ajax(request):
        action = request.GET.get('i')
        if action == 'show_state':
            state_list = list(Province.objects.values_list('name', flat=True).order_by('name'))
            return JsonResponse({'state_list': state_list})
        elif action == 'show_city':
            file_state = request.GET.get('file_state')
            cities = City.objects.filter(province__name=file_state).values_list('name', flat=True).order_by('name')
            return JsonResponse({'city_list': list(cities)})
        elif action == 'show_areas':
            return JsonResponse({'areas': []})

    # ====== جستجوی سریع (اگر پارامترها ارسال شده باشند) ======
    search_results = None
    if request.GET.get('file_state') or request.GET.get('file_city') or request.GET.get('file_apply'):
        file_state = request.GET.get('file_state')
        file_city = request.GET.get('file_city')
        file_apply = request.GET.get('file_apply')

        search_results = Property.objects.filter(
            is_active=True,
            is_visible=True,
            status=Property.Status.CONFIRMED  # <-- فقط تایید شده
        )

        if file_state and file_state != 'همه استان ها':
            search_results = search_results.filter(province__name=file_state)
        if file_city and file_city != 'همه شهرها':
            search_results = search_results.filter(city__name=file_city)
        if file_apply and file_apply != 'همه موارد':
            contract_map = {
                'فروشنده': 'sale',
                'موجر': 'rent',
                'مشارکت مالک': 'partnership',
                'معاوضه': 'both',
                'پیش فروش': 'investment',
            }
            if file_apply in contract_map:
                search_results = search_results.filter(contract_type=contract_map[file_apply])

        search_results = search_results.select_related(
            'property_type', 'province', 'city', 'neighborhood', 'owner'
        ).order_by('-created_at')[:20]

    # ====== لیست نوع قراردادها ======
    contract_choices = Property.ContractType.choices
    selected_contract = request.GET.get('file_apply', '')

    context = {
        "title": "پارامی | مدیریت املاک هوشمند",
        "this_user": this_user,
        "total_properties": total_properties,
        "total_customers": total_customers,
        "total_contracts": total_contracts,
        "today_customers": today_customers,
        "properties": properties,
        "search_results": search_results,
        "provinces": provinces,
        "contract_choices": contract_choices,
        "selected_contract": selected_contract,
    }
    return render(request, "home_page.html", context)


def contact_us(request):
    if request.user.is_authenticated:
        this_user = request.user
    else:
        this_user = "none"
    context = {
        "title": "تماس با ما | پارامی",
        "this_user": this_user,
    }
    return render(request, "contact_us.html", context)


def rules_page(request):
    if request.user.is_authenticated:
        this_user = request.user
    else:
        this_user = "none"
    context = {
        "title": "قوانین | پارامی",
        "this_user": this_user,
    }
    return render(request, "rules_page.html", context)


def privacy(request):
    if request.user.is_authenticated:
        this_user = request.user
    else:
        this_user = "none"
    context = {
        "title": "حریم خصوصی | پارمی",
        "this_user": this_user,
    }
    return render(request, "privacy.html", context)


def about_us(request):
    if request.user.is_authenticated:
        this_user = request.user
    else:
        this_user = "none"
    context = {
        "title": "درباره ما | پارامی",
        "this_user": this_user,
    }
    return render(request, "about_us.html", context)

def cooperate(request):
    """
    صفحه همکاری با ما - نمایش آمار واقعی از دیتابیس
    """
    if request.user.is_authenticated:
        this_user = request.user
    else:
        this_user = "none"

    # ===== دریافت آمار واقعی از دیتابیس =====

    # ۱. تعداد نیروهای فعال (کاربرانی که نقش expert، supervisor یا meetingchair دارند)
    active_staff = User.objects.filter(
        is_active=True,
        user_roles__is_active=True,
        user_roles__role__name__in=['expert', 'supervisor', 'meetingchair']
    ).distinct().count()

    # ۲. تعداد فایل‌های فعال
    total_properties = Property.objects.filter(is_active=True).count()

    # ۳. تعداد مشتریان فعال
    total_customers = Customer.objects.filter(is_active=True).count()

    # ۴. درصد رضایت مشتریان (از خدمات پس از فروش)
    total_aftersales = AfterSalesService.objects.count()

    if total_aftersales > 0:
        satisfied_count = AfterSalesService.objects.filter(
            satisfaction=AfterSalesService.Satisfaction.SATISFIED
        ).count()
        satisfaction_rate = round((satisfied_count / total_aftersales) * 100)
    else:
        satisfaction_rate = 0  # اگر هیچ خدماتی ثبت نشده باشد

    # ===== ساخت context =====
    context = {
        "title": "همکاری با ما | پارمی",
        "this_user": this_user,
        # ✅ آمار واقعی
        "active_staff": active_staff,
        "total_properties": total_properties,
        "total_customers": total_customers,
        "satisfaction_rate": satisfaction_rate,
    }
    return render(request, "cooperate.html", context)

def clean_param(value):
    if value in [None, '', 'None', 'null', 'undefined']:
        return None
    return value


def to_int(value):
    value = clean_param(value)
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def to_float(value):
    value = clean_param(value)
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def search_file(request):
    this_user = request.user if request.user.is_authenticated else "none"

    # ===== دریافت فیلترها =====
    # عمومی
    search = clean_param(request.GET.get('search'))

    # مکان
    province = clean_param(request.GET.get('province'))
    city = clean_param(request.GET.get('city'))
    neighborhood = clean_param(request.GET.get('neighborhood'))

    # نوع ملک و قرارداد
    property_type = clean_param(request.GET.get('property_type'))
    contract_type = clean_param(request.GET.get('contract_type'))

    # قیمت‌ها
    min_price = to_int(request.GET.get('min_price'))
    max_price = to_int(request.GET.get('max_price'))
    min_mortgage = to_int(request.GET.get('min_mortgage'))
    max_mortgage = to_int(request.GET.get('max_mortgage'))
    min_rent = to_int(request.GET.get('min_rent'))
    max_rent = to_int(request.GET.get('max_rent'))

    # مشخصات فیزیکی
    min_area = to_float(request.GET.get('min_area'))
    max_area = to_float(request.GET.get('max_area'))
    rooms = clean_param(request.GET.get('rooms'))
    built_year_min = to_int(request.GET.get('built_year_min'))
    built_year_max = to_int(request.GET.get('built_year_max'))
    parking_type = clean_param(request.GET.get('parking_type'))
    has_elevator = clean_param(request.GET.get('has_elevator'))

    # وضعیت و ویژه
    status = clean_param(request.GET.get('status'))
    is_featured = clean_param(request.GET.get('is_featured'))

    # مرتب‌سازی
    sort_by = clean_param(request.GET.get('sort', '-created_at'))

    # ===== کوئری پایه =====
    properties = Property.objects.filter(
        is_active=True,
        is_visible=True,
        status=Property.Status.CONFIRMED
    ).select_related(
        'province', 'city', 'neighborhood', 'property_type'
    ).prefetch_related('images')

    # ===== اعمال فیلترها =====
    # جستجوی عمومی در عنوان، آدرس، توضیحات
    if search:
        properties = properties.filter(
            Q(title__icontains=search) |
            Q(address__icontains=search) |
            Q(short_description__icontains=search) |
            Q(description__icontains=search)
        )

    # مکان
    if province:
        properties = properties.filter(province_id=province)
    if city:
        properties = properties.filter(city_id=city)
    if neighborhood:
        properties = properties.filter(neighborhood_id=neighborhood)

    # نوع ملک و قرارداد
    if property_type:
        properties = properties.filter(property_type_id=property_type)
    if contract_type:
        properties = properties.filter(contract_type=contract_type)

    # قیمت فروش
    if min_price is not None:
        properties = properties.filter(price__gte=min_price)
    if max_price is not None:
        properties = properties.filter(price__lte=max_price)

    # رهن
    if min_mortgage is not None:
        properties = properties.filter(mortgage_price__gte=min_mortgage)
    if max_mortgage is not None:
        properties = properties.filter(mortgage_price__lte=max_mortgage)

    # اجاره
    if min_rent is not None:
        properties = properties.filter(rent_price__gte=min_rent)
    if max_rent is not None:
        properties = properties.filter(rent_price__lte=max_rent)

    # متراژ
    if min_area is not None:
        properties = properties.filter(area__gte=min_area)
    if max_area is not None:
        properties = properties.filter(area__lte=max_area)

    # اتاق
    if rooms:
        if rooms == '5':
            properties = properties.filter(rooms__gte=5)
        else:
            try:
                properties = properties.filter(rooms=int(rooms))
            except ValueError:
                pass

    # سال ساخت
    if built_year_min is not None:
        properties = properties.filter(built_year__gte=built_year_min)
    if built_year_max is not None:
        properties = properties.filter(built_year__lte=built_year_max)

    # پارکینگ
    if parking_type:
        properties = properties.filter(parking_type=parking_type)

    # آسانسور
    if has_elevator == 'True':
        properties = properties.filter(requirements__code='ELEVATOR')

    # ویژه
    if is_featured == 'True':
        properties = properties.filter(is_featured=True)

    # ===== مرتب‌سازی =====
    sort_fields = {
        'created_at': 'created_at',
        '-created_at': '-created_at',
        'price': 'price',
        '-price': '-price',
        'area': 'area',
        '-area': '-area',
        'title': 'title',
        '-title': '-title',
    }
    if sort_by in sort_fields:
        properties = properties.order_by(sort_fields[sort_by])
    else:
        properties = properties.order_by('-created_at')

    # ===== صفحه‌بندی =====
    paginator = Paginator(properties, 15)  # تعداد ۱۵ در هر صفحه
    page_obj = paginator.get_page(request.GET.get('page'))

    # ===== داده‌های dropdown =====
    provinces = Province.objects.all().order_by('name')
    cities = City.objects.all().order_by('name')
    neighborhoods = Neighborhood.objects.all().order_by('name')
    property_types = PropertyType.objects.filter(is_active=True).order_by('name')
    contract_choices = Property.ContractType.choices
    parking_choices = Property.ParkingType.choices
    status_choices = Property.Status.choices
    requirements = Requirement.objects.filter(is_active=True).order_by('category', 'name')

    # ===== بررسی وجود فیلترهای فعال =====
    has_filters = any([
        search, province, city, neighborhood, property_type, contract_type,
        min_price, max_price, min_mortgage, max_mortgage, min_rent, max_rent,
        min_area, max_area, rooms, built_year_min, built_year_max,
        parking_type, has_elevator, status, is_featured
    ])

    # ===== AJAX =====
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        action = request.GET.get('i')
        if action == 'show_city':
            province_id = request.GET.get('province_id')
            cities_list = City.objects.filter(province_id=province_id).values('id', 'name')
            return JsonResponse({'cities': list(cities_list)})
        elif action == 'show_neighborhood':
            city_id = request.GET.get('city_id')
            neighborhoods_list = Neighborhood.objects.filter(city_id=city_id).values('id', 'name')
            return JsonResponse({'neighborhoods': list(neighborhoods_list)})

    # ===== context =====
    context = {
        'title': 'مدیریت فایل‌ها | پارمی',
        'this_user': this_user,
        'properties': page_obj,
        'total_count': properties.count(),
        'provinces': provinces,
        'cities': cities,
        'neighborhoods': neighborhoods,
        'property_types': property_types,
        'contract_choices': contract_choices,
        'parking_choices': parking_choices,
        'status_choices': status_choices,
        'requirements': requirements,
        'filter_search': search,
        'filter_province': province,
        'filter_city': city,
        'filter_neighborhood': neighborhood,
        'filter_property_type': property_type,
        'filter_contract_type': contract_type,
        'filter_min_price': request.GET.get('min_price'),
        'filter_max_price': request.GET.get('max_price'),
        'filter_min_mortgage': request.GET.get('min_mortgage'),
        'filter_max_mortgage': request.GET.get('max_mortgage'),
        'filter_min_rent': request.GET.get('min_rent'),
        'filter_max_rent': request.GET.get('max_rent'),
        'filter_min_area': request.GET.get('min_area'),
        'filter_max_area': request.GET.get('max_area'),
        'filter_rooms': rooms,
        'filter_built_year_min': request.GET.get('built_year_min'),
        'filter_built_year_max': request.GET.get('built_year_max'),
        'filter_parking_type': parking_type,
        'filter_has_elevator': has_elevator,
        'filter_status': status,
        'filter_is_featured': is_featured,
        'sort_by': sort_by,
        'has_filters': has_filters,
    }
    return render(request, 'search_file.html', context)


def property_detail(request, property_id):
    if request.user.is_authenticated:
        this_user = request.user
    else:
        this_user = "none"

    # فقط فایل تأییدشده قابل مشاهده است
    property_obj = get_object_or_404(
        Property.objects.select_related(
            'property_type', 'province', 'city', 'neighborhood',
            'owner', 'created_by', 'supervisor', 'expert'
        ).prefetch_related(
            'images', 'videos', 'requirements', 'matches'
        ),
        id=property_id,
        is_active=True,
        is_visible=True,
        status=Property.Status.CONFIRMED  # <-- فقط تایید شده
    )

    # افزایش بازدید
    property_obj.views_count += 1
    property_obj.save(update_fields=['views_count'])

    # املاک مشابه (همگی تأییدشده)
    similar_properties = Property.objects.filter(
        is_active=True,
        is_visible=True,
        status=Property.Status.CONFIRMED,
        property_type=property_obj.property_type,
        city=property_obj.city
    ).exclude(id=property_obj.id).order_by('-created_at')[:4]

    main_image = property_obj.get_main_image()
    other_images = property_obj.images.exclude(id=main_image.id) if main_image else property_obj.images.all()

    context = {
        'title': f'{property_obj.title} | پارامی',
        'this_user': this_user,
        'property': property_obj,
        'main_image': main_image,
        'other_images': other_images,
        'similar_properties': similar_properties,
        'contract_type_display': property_obj.get_contract_type_display(),
        'status_display': property_obj.get_status_display(),
        'ownership_display': property_obj.get_ownership_type_display(),
        'furnishing_display': property_obj.get_furnishing_status_display(),
        'parking_display': property_obj.get_parking_type_display(),
        'latitude': property_obj.latitude,
        'longitude': property_obj.longitude,
    }
    return render(request, 'property_detail.html', context)