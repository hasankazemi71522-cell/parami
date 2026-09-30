# estate/views_location.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q

from myclass.mydef import views_permissions
from .models import Province, City, Neighborhood
from .forms_location import ProvinceForm, CityForm, NeighborhoodForm, LocationImportForm
from .utils_location import (
    read_excel_file, validate_location_excel,
    process_location_data, generate_excel_template
)


# ============================================================
# 📍 مدیریت استان‌ها
# ============================================================

@login_required
def province_list(request):
    """لیست استان‌ها"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    provinces = Province.objects.all().order_by('name')

    # جستجو
    search = request.GET.get('search', '')
    if search:
        provinces = provinces.filter(name__icontains=search)

    # صفحه‌بندی
    paginator = Paginator(provinces, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'provinces': page_obj,
        'title': 'لیست استان‌ها',
        'userId': request.user.id,
        'this_user': request.user,
        'total_count': provinces.count(),
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/province_list.html', context)


@login_required
def province_create(request):
    """ایجاد استان جدید"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    if request.method == 'POST':
        form = ProvinceForm(request.POST)
        if form.is_valid():
            province = form.save()
            messages.success(request, f'استان "{province.name}" با موفقیت ایجاد شد.')
            return redirect('estate:province_list')
    else:
        form = ProvinceForm()

    context = {
        'form': form,
        'title': 'ایجاد استان جدید',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/province_create.html', context)


@login_required
def province_edit(request, pk):
    """ویرایش استان"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    province = get_object_or_404(Province, pk=pk)

    if request.method == 'POST':
        form = ProvinceForm(request.POST, instance=province)
        if form.is_valid():
            form.save()
            messages.success(request, f'استان "{province.name}" با موفقیت ویرایش شد.')
            return redirect('estate:province_list')
    else:
        form = ProvinceForm(instance=province)

    context = {
        'form': form,
        'province': province,
        'title': f'ویرایش استان {province.name}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/province_edit.html', context)


@login_required
def province_delete(request, pk):
    """حذف استان"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    province = get_object_or_404(Province, pk=pk)

    if request.method == 'POST':
        province_name = province.name
        province.delete()
        messages.success(request, f'استان "{province_name}" با موفقیت حذف شد.')
        return redirect('estate:province_list')

    context = {
        'province': province,
        'title': f'حذف استان {province.name}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/province_delete.html', context)


# ============================================================
# 📍 مدیریت شهرستان‌ها
# ============================================================

@login_required
def city_list(request):
    """لیست شهرستان‌ها"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    cities = City.objects.all().select_related('province').order_by('province__name', 'name')

    # فیلتر بر اساس استان
    province_id = request.GET.get('province')
    if province_id:
        cities = cities.filter(province_id=province_id)

    # جستجو
    search = request.GET.get('search', '')
    if search:
        cities = cities.filter(Q(name__icontains=search) | Q(province__name__icontains=search))

    # صفحه‌بندی
    paginator = Paginator(cities, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    provinces = Province.objects.all().order_by('name')

    context = {
        'cities': page_obj,
        'provinces': provinces,
        'selected_province': province_id,
        'title': 'لیست شهرستان‌ها',
        'userId': request.user.id,
        'this_user': request.user,
        'total_count': cities.count(),
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/city_list.html', context)


@login_required
def city_create(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    """ایجاد شهرستان جدید"""
    if request.method == 'POST':
        form = CityForm(request.POST)
        if form.is_valid():
            city = form.save()
            messages.success(request, f'شهرستان "{city.name}" با موفقیت ایجاد شد.')
            return redirect('estate:city_list')
    else:
        form = CityForm()

    context = {
        'form': form,
        'title': 'ایجاد شهرستان جدید',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/city_create.html', context)


@login_required
def city_edit(request, pk):
    """ویرایش شهرستان"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    city = get_object_or_404(City, pk=pk)

    if request.method == 'POST':
        form = CityForm(request.POST, instance=city)
        if form.is_valid():
            form.save()
            messages.success(request, f'شهرستان "{city.name}" با موفقیت ویرایش شد.')
            return redirect('estate:city_list')
    else:
        form = CityForm(instance=city)

    context = {
        'form': form,
        'city': city,
        'title': f'ویرایش شهرستان {city.name}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/city_edit.html', context)


@login_required
def city_delete(request, pk):
    """حذف شهرستان"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    city = get_object_or_404(City, pk=pk)

    if request.method == 'POST':
        city_name = city.name
        city.delete()
        messages.success(request, f'شهرستان "{city_name}" با موفقیت حذف شد.')
        return redirect('estate:city_list')

    context = {
        'city': city,
        'title': f'حذف شهرستان {city.name}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/city_delete.html', context)


# ============================================================
# 📍 مدیریت محله‌ها
# ============================================================

@login_required
def neighborhood_list(request):
    """لیست محله‌ها"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    neighborhoods = Neighborhood.objects.all().select_related('city__province').order_by('city__province__name',
                                                                                         'city__name', 'name')

    # فیلتر بر اساس استان
    province_id = request.GET.get('province')
    if province_id:
        neighborhoods = neighborhoods.filter(city__province_id=province_id)

    # فیلتر بر اساس شهرستان
    city_id = request.GET.get('city')
    if city_id:
        neighborhoods = neighborhoods.filter(city_id=city_id)

    # جستجو
    search = request.GET.get('search', '')
    if search:
        neighborhoods = neighborhoods.filter(
            Q(name__icontains=search) |
            Q(city__name__icontains=search) |
            Q(city__province__name__icontains=search)
        )

    # صفحه‌بندی
    paginator = Paginator(neighborhoods, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    provinces = Province.objects.all().order_by('name')
    cities = City.objects.all().select_related('province').order_by('name')

    context = {
        'neighborhoods': page_obj,
        'provinces': provinces,
        'cities': cities,
        'selected_province': province_id,
        'selected_city': city_id,
        'title': 'لیست محله‌ها',
        'userId': request.user.id,
        'this_user': request.user,
        'total_count': neighborhoods.count(),
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/neighborhood_list.html', context)


@login_required
def neighborhood_create(request):
    """ایجاد محله جدید"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    if request.method == 'POST':
        form = NeighborhoodForm(request.POST)
        if form.is_valid():
            neighborhood = form.save()
            messages.success(request, f'محله "{neighborhood.name}" با موفقیت ایجاد شد.')
            return redirect('estate:neighborhood_list')
    else:
        form = NeighborhoodForm()

    context = {
        'form': form,
        'title': 'ایجاد محله جدید',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/neighborhood_create.html', context)


@login_required
def neighborhood_edit(request, pk):
    """ویرایش محله"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    neighborhood = get_object_or_404(Neighborhood, pk=pk)

    if request.method == 'POST':
        form = NeighborhoodForm(request.POST, instance=neighborhood)
        if form.is_valid():
            form.save()
            messages.success(request, f'محله "{neighborhood.name}" با موفقیت ویرایش شد.')
            return redirect('estate:neighborhood_list')
    else:
        form = NeighborhoodForm(instance=neighborhood)

    context = {
        'form': form,
        'neighborhood': neighborhood,
        'title': f'ویرایش محله {neighborhood.name}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/neighborhood_edit.html', context)


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
        # بررسی وجود استان
        province = Province.objects.filter(id=province_id).first()
        if not province:
            return JsonResponse({
                'success': False,
                'cities': [],
                'error': 'استان مورد نظر یافت نشد'
            })

        # دریافت شهرستان‌ها
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


@login_required
def neighborhood_delete(request, pk):
    """حذف محله"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    neighborhood = get_object_or_404(Neighborhood, pk=pk)

    if request.method == 'POST':
        neighborhood_name = neighborhood.name
        neighborhood.delete()
        messages.success(request, f'محله "{neighborhood_name}" با موفقیت حذف شد.')
        return redirect('estate:neighborhood_list')

    context = {
        'neighborhood': neighborhood,
        'title': f'حذف محله {neighborhood.name}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/neighborhood_delete.html', context)


# ============================================================
# 📥 آپلود اکسل (واردات انبوه)
# ============================================================

@login_required
def location_import(request):
    """
    آپلود فایل اکسل برای واردات انبوه استان‌ها، شهرستان‌ها و محله‌ها
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    if request.method == 'POST':
        form = LocationImportForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                file = request.FILES['file']
                overwrite = form.cleaned_data.get('overwrite', False)

                # خواندن فایل اکسل
                df = read_excel_file(file)

                # اعتبارسنجی
                df = validate_location_excel(df)

                # پردازش داده‌ها
                data = process_location_data(df)

                # ذخیره در session برای مرحله بعد
                request.session['import_data'] = data
                request.session['overwrite'] = overwrite

                # محاسبه آمار
                total_cities = 0
                total_neighborhoods = 0

                for province_data in data.values():
                    total_cities += len(province_data['cities'])
                    for city_data in province_data['cities'].values():
                        total_neighborhoods += len(city_data['neighborhoods'])

                # نمایش پیش‌نمایش
                return render(request, 'estate/location/location_import_preview.html', {
                    'data': data,
                    'total_provinces': len(data),
                    'total_cities': total_cities,
                    'total_neighborhoods': total_neighborhoods,
                    'title': 'پیش‌نمایش واردات',
                    'userId': request.user.id,
                    'this_user': request.user,
                })

            except Exception as e:
                messages.error(request, f'خطا در خواندن فایل: {str(e)}')
                return redirect('estate:location_import')
        else:
            messages.error(request, 'فرم معتبر نیست. لطفاً یک فایل اکسل معتبر انتخاب کنید.')
    else:
        form = LocationImportForm()

    context = {
        'form': form,
        'title': 'واردات انبوه مکان‌ها',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'estate/location/location_import.html', context)


@login_required
def location_import_confirm(request):
    """
    تأیید و ذخیره نهایی داده‌های وارد شده از اکسل
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    if request.method != 'POST':
        return redirect('estate:location_import')

    data = request.session.get('import_data')
    overwrite = request.session.get('overwrite', False)

    if not data:
        messages.error(request, 'داده‌ای برای واردات وجود ندارد.')
        return redirect('estate:location_import')

    try:
        with transaction.atomic():
            stats = {
                'provinces_created': 0,
                'provinces_updated': 0,
                'cities_created': 0,
                'cities_updated': 0,
                'neighborhoods_created': 0,
                'neighborhoods_updated': 0,
            }

            for province_name, province_data in data.items():
                # ایجاد یا بروزرسانی استان
                province, created = Province.objects.get_or_create(
                    name=province_name,
                    defaults={'code': ''}
                )
                if created:
                    stats['provinces_created'] += 1
                else:
                    stats['provinces_updated'] += 1

                # ایجاد یا بروزرسانی شهرستان‌ها
                for city_name, city_data in province_data['cities'].items():
                    city, created = City.objects.get_or_create(
                        name=city_name,
                        province=province
                    )
                    if created:
                        stats['cities_created'] += 1
                    else:
                        stats['cities_updated'] += 1

                    # ایجاد یا بروزرسانی محله‌ها
                    for neighborhood_name in city_data['neighborhoods']:
                        if neighborhood_name and neighborhood_name.strip():
                            neighborhood, created = Neighborhood.objects.get_or_create(
                                name=neighborhood_name.strip(),
                                city=city
                            )
                            if created:
                                stats['neighborhoods_created'] += 1
                            else:
                                stats['neighborhoods_updated'] += 1

        # پاک کردن session
        if 'import_data' in request.session:
            del request.session['import_data']
        if 'overwrite' in request.session:
            del request.session['overwrite']

        messages.success(
            request,
            f'✅ واردات با موفقیت انجام شد!\n'
            f'استان‌ها: {stats["provinces_created"]} ایجاد، {stats["provinces_updated"]} بروزرسانی\n'
            f'شهرستان‌ها: {stats["cities_created"]} ایجاد، {stats["cities_updated"]} بروزرسانی\n'
            f'محله‌ها: {stats["neighborhoods_created"]} ایجاد، {stats["neighborhoods_updated"]} بروزرسانی'
        )

        return redirect('estate:province_list')

    except Exception as e:
        messages.error(request, f'خطا در ذخیره داده‌ها: {str(e)}')
        return redirect('estate:location_import')


@login_required
def location_export_template(request):
    """
    دانلود فایل اکسل نمونه
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "state_city")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    wb = generate_excel_template()

    # ایجاد پاسخ HTTP با فایل اکسل
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=template_makan.xlsx'

    wb.save(response)
    return response
