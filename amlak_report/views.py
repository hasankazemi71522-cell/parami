from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
import jdatetime

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta

from account.models import User
from estate.models import Customer, Property, Province, City, Source, Match, DuplicateCheck
from case_management.models import CustomerProcess, Visit, SupervisorAlert
from transaction.models import Contract, Commission, WithdrawalRequest

from .forms import (
    CustomerReportFilterForm, PropertyReportFilterForm,
    ProcessReportFilterForm, ContractReportFilterForm,
    CommissionReportFilterForm
)
from .utils import (
    get_dashboard_stats, get_status_chart_data, get_expert_performance,
    get_supervisor_stats, get_monthly_stats, get_contract_type_stats,
    get_commission_stats, export_to_excel
)
from myclass.mydef import views_permissions
from django.http import JsonResponse
from estate.models import City



@login_required
def get_cities_by_province(request):
    """دریافت شهرهای یک استان (برای وابسته کردن در قالب)"""
    province_id = request.GET.get('province_id')
    if province_id:
        cities = City.objects.filter(province_id=province_id).order_by('name').values('id', 'name')
        return JsonResponse({'cities': list(cities)}, safe=False)
    return JsonResponse({'cities': []}, safe=False)



@login_required
def dashboard(request):
    """داشبورد اصلی گزارشات"""
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "amlak_report"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    stats = get_dashboard_stats()
    chart_data = get_status_chart_data()
    monthly_data = get_monthly_stats()
    expert_performance = get_expert_performance()[:10]
    contract_types = get_contract_type_stats()

    context = {
        'title': 'داشبورد گزارشات',
        'stats': stats,
        'chart_data': chart_data,
        'monthly_data': monthly_data,
        'expert_performance': expert_performance,
        'contract_types': contract_types,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'amlak_report/dashboard.html', context)


@login_required
def customer_report(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "amlak_report_customer"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    form = CustomerReportFilterForm(request.GET or None)

    queryset = Customer.objects.filter(is_active=True).select_related(
        'user', 'created_by', 'source', 'supervisor', 'expert'
    ).prefetch_related(
        'preferred_cities', 'preferred_neighborhoods', 'preferred_property_types'
    )

    # ====== اعمال فیلترها ======
    if form.is_valid():
        data = form.cleaned_data

        if data.get('customer_type'):
            queryset = queryset.filter(customer_type=data['customer_type'])

        if data.get('status'):
            queryset = queryset.filter(status=data['status'])

        if data.get('source'):
            queryset = queryset.filter(source=data['source'])

        # فیلتر بر اساس استان
        province = data.get('province')
        if province:
            queryset = queryset.filter(preferred_cities__province=province)

        # فیلتر بر اساس شهر
        city = data.get('city')
        if city:
            queryset = queryset.filter(preferred_cities=city)

        # فیلتر تاریخ از (شمسی)
        date_from_year = data.get('date_from_year')
        date_from_month = data.get('date_from_month')
        date_from_day = data.get('date_from_day')
        if date_from_year and date_from_month and date_from_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_from_year),
                    int(date_from_month),
                    int(date_from_day)
                ).togregorian()
                queryset = queryset.filter(created_at__date__gte=gregorian_date)
            except:
                pass

        # فیلتر تاریخ تا (شمسی)
        date_to_year = data.get('date_to_year')
        date_to_month = data.get('date_to_month')
        date_to_day = data.get('date_to_day')
        if date_to_year and date_to_month and date_to_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_to_year),
                    int(date_to_month),
                    int(date_to_day)
                ).togregorian()
                queryset = queryset.filter(created_at__date__lte=gregorian_date)
            except:
                pass

        if data.get('search'):
            search = data['search']
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__mobile__icontains=search) |
                Q(user__email__icontains=search)
            )

        duplicate_filter = data.get('has_duplicate')
        if duplicate_filter == 'yes':
            duplicate_ids = DuplicateCheck.objects.filter(
                check_type='customer',
                status=DuplicateCheck.Status.CONFIRMED
            ).values_list('check_id', flat=True)
            queryset = queryset.filter(id__in=duplicate_ids)
        elif duplicate_filter == 'no':
            duplicate_ids = DuplicateCheck.objects.filter(
                check_type='customer',
                status=DuplicateCheck.Status.CONFIRMED
            ).values_list('check_id', flat=True)
            queryset = queryset.exclude(id__in=duplicate_ids)

    # ====== آمار کلی (بدون فیلتر) ======
    base_customers = Customer.objects.filter(is_active=True)

    stats = {
        'total': base_customers.count(),
        'with_supervisor': base_customers.filter(supervisor__isnull=False).count(),
        'without_supervisor': base_customers.filter(supervisor__isnull=True).count(),
        'status_new': base_customers.filter(status=Customer.Status.NEW).count(),
        'status_confirmed': base_customers.filter(status=Customer.Status.CONFIRMED).count(),
        'status_in_meeting': base_customers.filter(status=Customer.Status.IN_MEETING).count(),
        'status_contract': base_customers.filter(status=Customer.Status.CONTRACT).count(),
        # ✅ جدا کردن فرآیند باز و بسته
        'has_active_process': base_customers.filter(
            processes__status__in=[
                CustomerProcess.Status.ASSIGNED,
                CustomerProcess.Status.CONTACTED,
                CustomerProcess.Status.INTRODUCED,
                CustomerProcess.Status.VISIT_SCHEDULED,
                CustomerProcess.Status.VISIT_DONE,
                CustomerProcess.Status.NEGOTIATION,
                CustomerProcess.Status.CONTRACT_PENDING,
            ]
        ).distinct().count(),
        'has_closed_process': base_customers.filter(
            processes__status__in=[
                CustomerProcess.Status.CLOSED_SUCCESS,
                CustomerProcess.Status.CLOSED_FAIL,
                CustomerProcess.Status.CANCELLED,
                CustomerProcess.Status.CONVERTED,
                CustomerProcess.Status.SENT_TO_ACCOUNTING,
            ]
        ).distinct().count(),
    }

    # صفحه‌بندی
    paginator = Paginator(queryset, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # لیست استان‌ها برای فرم (برای وابسته کردن شهرها)
    provinces = Province.objects.all().order_by('name')

    context = {
        'title': 'گزارش مشتریان',
        'form': form,
        'customers': page_obj,
        'stats': stats,
        'provinces': provinces,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'amlak_report/customer_report.html', context)

@login_required
def property_report(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "amlak_report_property"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    form = PropertyReportFilterForm(request.GET or None)

    queryset = Property.objects.filter(is_active=True).select_related(
        'property_type', 'province', 'city', 'neighborhood',
        'owner', 'created_by', 'supervisor', 'expert'
    ).prefetch_related('usage_types', 'requirements')

    # ====== اعمال فیلترها ======
    if form.is_valid():
        data = form.cleaned_data

        if data.get('property_type'):
            queryset = queryset.filter(property_type=data['property_type'])

        if data.get('status'):
            queryset = queryset.filter(status=data['status'])

        if data.get('contract_type'):
            queryset = queryset.filter(contract_type=data['contract_type'])

        province = data.get('province')
        if province:
            queryset = queryset.filter(city__province=province)

        city = data.get('city')
        if city:
            queryset = queryset.filter(city=city)

        # فیلتر تاریخ از (شمسی)
        date_from_year = data.get('date_from_year')
        date_from_month = data.get('date_from_month')
        date_from_day = data.get('date_from_day')
        if date_from_year and date_from_month and date_from_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_from_year),
                    int(date_from_month),
                    int(date_from_day)
                ).togregorian()
                queryset = queryset.filter(created_at__date__gte=gregorian_date)
            except:
                pass

        date_to_year = data.get('date_to_year')
        date_to_month = data.get('date_to_month')
        date_to_day = data.get('date_to_day')
        if date_to_year and date_to_month and date_to_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_to_year),
                    int(date_to_month),
                    int(date_to_day)
                ).togregorian()
                queryset = queryset.filter(created_at__date__lte=gregorian_date)
            except:
                pass

        if data.get('search'):
            search = data['search']
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(address__icontains=search) |
                Q(owner__first_name__icontains=search) |
                Q(owner__last_name__icontains=search)
            )

        duplicate_filter = data.get('has_duplicate')
        if duplicate_filter == 'yes':
            duplicate_ids = DuplicateCheck.objects.filter(
                check_type='property',
                status=DuplicateCheck.Status.CONFIRMED
            ).values_list('check_id', flat=True)
            queryset = queryset.filter(id__in=duplicate_ids)
        elif duplicate_filter == 'no':
            duplicate_ids = DuplicateCheck.objects.filter(
                check_type='property',
                status=DuplicateCheck.Status.CONFIRMED
            ).values_list('check_id', flat=True)
            queryset = queryset.exclude(id__in=duplicate_ids)

    # ====== آمار کلی (بدون فیلتر) ======
    base_properties = Property.objects.filter(is_active=True)

    # محاسبه املاک دارای فرآیند (از طریق IntroductionReport)
    from case_management.models import IntroductionReport, CustomerProcess

    # املاکی که حداقل یک گزارش معرفی در فرآیند فعال دارند
    active_process_property_ids = IntroductionReport.objects.filter(
        process__status__in=[
            CustomerProcess.Status.ASSIGNED,
            CustomerProcess.Status.CONTACTED,
            CustomerProcess.Status.INTRODUCED,
            CustomerProcess.Status.VISIT_SCHEDULED,
            CustomerProcess.Status.VISIT_DONE,
            CustomerProcess.Status.NEGOTIATION,
            CustomerProcess.Status.CONTRACT_PENDING,
        ]
    ).values_list('property_ref_id', flat=True).distinct()

    # املاکی که حداقل یک گزارش معرفی در فرآیند بسته دارند
    closed_process_property_ids = IntroductionReport.objects.filter(
        process__status__in=[
            CustomerProcess.Status.CLOSED_SUCCESS,
            CustomerProcess.Status.CLOSED_FAIL,
            CustomerProcess.Status.CANCELLED,
            CustomerProcess.Status.CONVERTED,
            CustomerProcess.Status.SENT_TO_ACCOUNTING,
        ]
    ).values_list('property_ref_id', flat=True).distinct()

    stats = {
        'total': base_properties.count(),
        'with_supervisor': base_properties.filter(supervisor__isnull=False).count(),
        'without_supervisor': base_properties.filter(supervisor__isnull=True).count(),
        'status_pending': base_properties.filter(status=Property.Status.PENDING).count(),
        'status_confirmed': base_properties.filter(status=Property.Status.CONFIRMED).count(),
        'status_in_meeting': base_properties.filter(status=Property.Status.IN_MEETING).count(),
        'status_contract': base_properties.filter(status=Property.Status.CONTRACT).count(),
        'has_active_process': base_properties.filter(id__in=active_process_property_ids).count(),
        'has_closed_process': base_properties.filter(id__in=closed_process_property_ids).count(),
    }

    # صفحه‌بندی
    paginator = Paginator(queryset, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'title': 'گزارش املاک',
        'form': form,
        'properties': page_obj,
        'stats': stats,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'amlak_report/property_report.html', context)

@login_required
def process_report(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "amlak_report_process"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    form = ProcessReportFilterForm(request.GET or None)

    queryset = CustomerProcess.objects.select_related(
        'customer', 'customer__user', 'expert', 'supervisor'
    ).prefetch_related('visits', 'introduction_reports')

    # ====== اعمال فیلترها ======
    if form.is_valid():
        data = form.cleaned_data

        if data.get('status'):
            queryset = queryset.filter(status=data['status'])

        if data.get('expert'):
            queryset = queryset.filter(expert=data['expert'])

        if data.get('supervisor'):
            queryset = queryset.filter(supervisor=data['supervisor'])

        # فیلتر تاریخ از (شمسی)
        date_from_year = data.get('date_from_year')
        date_from_month = data.get('date_from_month')
        date_from_day = data.get('date_from_day')
        if date_from_year and date_from_month and date_from_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_from_year),
                    int(date_from_month),
                    int(date_from_day)
                ).togregorian()
                queryset = queryset.filter(assigned_at__date__gte=gregorian_date)
            except:
                pass

        date_to_year = data.get('date_to_year')
        date_to_month = data.get('date_to_month')
        date_to_day = data.get('date_to_day')
        if date_to_year and date_to_month and date_to_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_to_year),
                    int(date_to_month),
                    int(date_to_day)
                ).togregorian()
                queryset = queryset.filter(assigned_at__date__lte=gregorian_date)
            except:
                pass

        if data.get('search'):
            search = data['search']
            queryset = queryset.filter(
                Q(customer__user__first_name__icontains=search) |
                Q(customer__user__last_name__icontains=search) |
                Q(customer__user__mobile__icontains=search)
            )

        is_closed = data.get('is_closed')
        if is_closed == 'open':
            queryset = queryset.exclude(
                status__in=[
                    CustomerProcess.Status.CLOSED_SUCCESS,
                    CustomerProcess.Status.CLOSED_FAIL,
                    CustomerProcess.Status.CANCELLED,
                    CustomerProcess.Status.CONVERTED,
                    CustomerProcess.Status.SENT_TO_ACCOUNTING
                ]
            )
        elif is_closed == 'closed':
            queryset = queryset.filter(
                status__in=[
                    CustomerProcess.Status.CLOSED_SUCCESS,
                    CustomerProcess.Status.CLOSED_FAIL,
                    CustomerProcess.Status.CANCELLED,
                    CustomerProcess.Status.CONVERTED,
                    CustomerProcess.Status.SENT_TO_ACCOUNTING
                ]
            )

    # ====== آمار کلی (بدون فیلتر) ======
    base_processes = CustomerProcess.objects.all()

    # وضعیت‌های باز
    active_statuses = [
        CustomerProcess.Status.ASSIGNED,
        CustomerProcess.Status.CONTACTED,
        CustomerProcess.Status.INTRODUCED,
        CustomerProcess.Status.VISIT_SCHEDULED,
        CustomerProcess.Status.VISIT_DONE,
        CustomerProcess.Status.NEGOTIATION,
        CustomerProcess.Status.CONTRACT_PENDING,
    ]
    # وضعیت‌های بسته
    closed_statuses = [
        CustomerProcess.Status.CLOSED_SUCCESS,
        CustomerProcess.Status.CLOSED_FAIL,
        CustomerProcess.Status.CANCELLED,
        CustomerProcess.Status.CONVERTED,
        CustomerProcess.Status.SENT_TO_ACCOUNTING,
    ]

    stats = {
        'total': base_processes.count(),
        'active': base_processes.filter(status__in=active_statuses).count(),
        'closed': base_processes.filter(status__in=closed_statuses).count(),
        'closed_success': base_processes.filter(status=CustomerProcess.Status.CLOSED_SUCCESS).count(),
        'closed_fail': base_processes.filter(status=CustomerProcess.Status.CLOSED_FAIL).count(),
        'cancelled': base_processes.filter(status=CustomerProcess.Status.CANCELLED).count(),
        'converted': base_processes.filter(status=CustomerProcess.Status.CONVERTED).count(),
        'contract_pending': base_processes.filter(status=CustomerProcess.Status.CONTRACT_PENDING).count(),
        'sent_to_accounting': base_processes.filter(status=CustomerProcess.Status.SENT_TO_ACCOUNTING).count(),
        'negotiation': base_processes.filter(status=CustomerProcess.Status.NEGOTIATION).count(),
        'visit_scheduled': base_processes.filter(status=CustomerProcess.Status.VISIT_SCHEDULED).count(),
        'missed_contact': base_processes.filter(missed_contact_reported=True).count(),
        'missed_intro': base_processes.filter(missed_intro_reported=True).count(),
    }

    # صفحه‌بندی
    paginator = Paginator(queryset, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'title': 'گزارش فرآیندها',
        'form': form,
        'processes': page_obj,
        'stats': stats,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'amlak_report/process_report.html', context)

@login_required
def contract_report(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "amlak_report_contract"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    form = ContractReportFilterForm(request.GET or None)

    queryset = Contract.objects.select_related(
        'customer', 'customer__user', 'property_ref',
        'process__expert', 'process__supervisor',
        'contract_officer'
    )

    # ====== اعمال فیلترها ======
    if form.is_valid():
        data = form.cleaned_data

        if data.get('status'):
            queryset = queryset.filter(status=data['status'])

        if data.get('contract_type'):
            queryset = queryset.filter(contract_type=data['contract_type'])

        # فیلتر تاریخ از (شمسی)
        date_from_year = data.get('date_from_year')
        date_from_month = data.get('date_from_month')
        date_from_day = data.get('date_from_day')
        if date_from_year and date_from_month and date_from_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_from_year),
                    int(date_from_month),
                    int(date_from_day)
                ).togregorian()
                queryset = queryset.filter(created_at__date__gte=gregorian_date)
            except:
                pass

        date_to_year = data.get('date_to_year')
        date_to_month = data.get('date_to_month')
        date_to_day = data.get('date_to_day')
        if date_to_year and date_to_month and date_to_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_to_year),
                    int(date_to_month),
                    int(date_to_day)
                ).togregorian()
                queryset = queryset.filter(created_at__date__lte=gregorian_date)
            except:
                pass

        if data.get('search'):
            search = data['search']
            queryset = queryset.filter(
                Q(contract_number__icontains=search) |
                Q(customer__user__first_name__icontains=search) |
                Q(customer__user__last_name__icontains=search) |
                Q(customer__user__mobile__icontains=search)
            )

    # ====== آمار کلی (بدون فیلتر) ======
    base_contracts = Contract.objects.all()

    stats = {
        'total': base_contracts.count(),
        'pending': base_contracts.filter(status=Contract.Status.PENDING).count(),
        'completed': base_contracts.filter(status=Contract.Status.COMPLETED).count(),
        'cancelled': base_contracts.filter(status=Contract.Status.CANCELLED).count(),
        'sale': base_contracts.filter(contract_type='sale').count(),
        'rent': base_contracts.filter(contract_type='rent').count(),
        'partnership': base_contracts.filter(contract_type='partnership').count(),
        'investment': base_contracts.filter(contract_type='investment').count(),
        'total_amount': base_contracts.aggregate(Sum('final_amount'))['final_amount__sum'] or 0,
        'avg_amount': base_contracts.aggregate(Avg('final_amount'))['final_amount__avg'] or 0,
    }

    # صفحه‌بندی
    paginator = Paginator(queryset, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'title': 'گزارش قراردادها',
        'form': form,
        'contracts': page_obj,
        'stats': stats,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'amlak_report/contract_report.html', context)

@login_required
def commission_report(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "amlak_report_commission"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    form = CommissionReportFilterForm(request.GET or None)

    queryset = Commission.objects.select_related(
        'contract', 'contract__customer', 'contract__customer__user',
        'contract__property_ref', 'accountant'
    )

    # ====== اعمال فیلترها ======
    if form.is_valid():
        data = form.cleaned_data

        if data.get('status'):
            queryset = queryset.filter(status=data['status'])

        # فیلتر تاریخ از (شمسی)
        date_from_year = data.get('date_from_year')
        date_from_month = data.get('date_from_month')
        date_from_day = data.get('date_from_day')
        if date_from_year and date_from_month and date_from_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_from_year),
                    int(date_from_month),
                    int(date_from_day)
                ).togregorian()
                queryset = queryset.filter(created_at__date__gte=gregorian_date)
            except:
                pass

        date_to_year = data.get('date_to_year')
        date_to_month = data.get('date_to_month')
        date_to_day = data.get('date_to_day')
        if date_to_year and date_to_month and date_to_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_to_year),
                    int(date_to_month),
                    int(date_to_day)
                ).togregorian()
                queryset = queryset.filter(created_at__date__lte=gregorian_date)
            except:
                pass

        if data.get('search'):
            search = data['search']
            queryset = queryset.filter(
                Q(contract__customer__user__first_name__icontains=search) |
                Q(contract__customer__user__last_name__icontains=search) |
                Q(contract__customer__user__mobile__icontains=search)
            )

    # ====== آمار کلی ======
    base_commissions = Commission.objects.all()

    stats = {
        'total': base_commissions.count(),
        'pending': base_commissions.filter(status=Commission.Status.PENDING).count(),
        'calculated': base_commissions.filter(status=Commission.Status.CALCULATED).count(),
        'wallet_transferred': base_commissions.filter(status=Commission.Status.WALLET_TRANSFERRED).count(),
        'paid': base_commissions.filter(status=Commission.Status.PAID).count(),
        'partial_paid': base_commissions.filter(status=Commission.Status.PARTIAL_PAID).count(),
    }

    commission_stats = {
        'total': base_commissions.aggregate(Sum('total_commission'))['total_commission__sum'] or 0,
        'paid': base_commissions.filter(status=Commission.Status.PAID).aggregate(Sum('total_commission'))['total_commission__sum'] or 0,
        'pending': base_commissions.filter(status=Commission.Status.PENDING).aggregate(Sum('total_commission'))['total_commission__sum'] or 0,
        'calculated': base_commissions.filter(status=Commission.Status.CALCULATED).aggregate(Sum('total_commission'))['total_commission__sum'] or 0,
        'wallet_transferred': base_commissions.filter(status=Commission.Status.WALLET_TRANSFERRED).aggregate(Sum('total_commission'))['total_commission__sum'] or 0,
    }

    # صفحه‌بندی
    paginator = Paginator(queryset, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'title': 'گزارش حسابداری',
        'form': form,
        'commissions': page_obj,
        'stats': stats,
        'commission_stats': commission_stats,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'amlak_report/commission_report.html', context)


@login_required
def export_customer_excel(request):
    """
    خروجی Excel از گزارش مشتریان با اعمال فیلترهای جاری
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "amlak_report_customer"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    # ====== دریافت کوئری‌ست با فیلترهای مشابه customer_report ======
    form = CustomerReportFilterForm(request.GET or None)

    queryset = Customer.objects.filter(is_active=True).select_related(
        'user', 'created_by', 'source', 'supervisor', 'expert'
    ).prefetch_related(
        'preferred_cities', 'preferred_neighborhoods', 'preferred_property_types'
    )

    # ====== اعمال فیلترها (همان منطق customer_report) ======
    if form.is_valid():
        data = form.cleaned_data

        if data.get('customer_type'):
            queryset = queryset.filter(customer_type=data['customer_type'])

        if data.get('status'):
            queryset = queryset.filter(status=data['status'])

        if data.get('source'):
            queryset = queryset.filter(source=data['source'])

        province = data.get('province')
        if province:
            queryset = queryset.filter(preferred_cities__province=province)

        city = data.get('city')
        if city:
            queryset = queryset.filter(preferred_cities=city)

        # فیلتر تاریخ از (شمسی)
        date_from_year = data.get('date_from_year')
        date_from_month = data.get('date_from_month')
        date_from_day = data.get('date_from_day')
        if date_from_year and date_from_month and date_from_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_from_year),
                    int(date_from_month),
                    int(date_from_day)
                ).togregorian()
                queryset = queryset.filter(created_at__date__gte=gregorian_date)
            except:
                pass

        date_to_year = data.get('date_to_year')
        date_to_month = data.get('date_to_month')
        date_to_day = data.get('date_to_day')
        if date_to_year and date_to_month and date_to_day:
            try:
                gregorian_date = jdatetime.date(
                    int(date_to_year),
                    int(date_to_month),
                    int(date_to_day)
                ).togregorian()
                queryset = queryset.filter(created_at__date__lte=gregorian_date)
            except:
                pass

        if data.get('search'):
            search = data['search']
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__mobile__icontains=search) |
                Q(user__email__icontains=search)
            )

        duplicate_filter = data.get('has_duplicate')
        if duplicate_filter == 'yes':
            duplicate_ids = DuplicateCheck.objects.filter(
                check_type='customer',
                status=DuplicateCheck.Status.CONFIRMED
            ).values_list('check_id', flat=True)
            queryset = queryset.filter(id__in=duplicate_ids)
        elif duplicate_filter == 'no':
            duplicate_ids = DuplicateCheck.objects.filter(
                check_type='customer',
                status=DuplicateCheck.Status.CONFIRMED
            ).values_list('check_id', flat=True)
            queryset = queryset.exclude(id__in=duplicate_ids)

    # ====== ساخت فایل Excel ======
    wb = Workbook()
    ws = wb.active
    ws.title = 'گزارش مشتریان'

    # ====== تعریف هدرها ======
    headers = [
        'ردیف',
        'نام و نام خانوادگی',
        'نام کاربری',
        'موبایل',
        'ایمیل',
        'نوع مشتری',
        'وضعیت',
        'منبع',
        'سرپرست',
        'کارشناس',
        'تاریخ ثبت',
    ]
    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=11)

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # ====== پر کردن داده‌ها ======
    row_num = 2
    for idx, customer in enumerate(queryset, 1):
        ws.cell(row=row_num, column=1, value=idx)
        ws.cell(row=row_num, column=2, value=customer.full_name)
        ws.cell(row=row_num, column=3, value=customer.user.username if customer.user else '')
        ws.cell(row=row_num, column=4, value=customer.mobile or '')
        ws.cell(row=row_num, column=5, value=customer.user.email if customer.user else '')
        ws.cell(row=row_num, column=6, value=customer.get_customer_type_display())
        ws.cell(row=row_num, column=7, value=customer.get_status_display())
        ws.cell(row=row_num, column=8, value=customer.source_name or '')
        ws.cell(row=row_num, column=9, value=customer.supervisor.get_full_name() if customer.supervisor else '')
        ws.cell(row=row_num, column=10, value=customer.expert.get_full_name() if customer.expert else '')
        ws.cell(row=row_num, column=11, value=customer.created_at.strftime('%Y/%m/%d %H:%M') if customer.created_at else '')

        # تنظیم alignment برای همه سلول‌های این ردیف
        for col in range(1, len(headers) + 1):
            ws.cell(row=row_num, column=col).alignment = Alignment(horizontal='center', vertical='center')

        row_num += 1

    # ====== تنظیم عرض ستون‌ها ======
    column_widths = {
        'A': 6,   # ردیف
        'B': 25,  # نام
        'C': 18,  # نام کاربری
        'D': 15,  # موبایل
        'E': 25,  # ایمیل
        'F': 15,  # نوع مشتری
        'G': 18,  # وضعیت
        'H': 18,  # منبع
        'I': 20,  # سرپرست
        'J': 20,  # کارشناس
        'K': 20,  # تاریخ ثبت
    }

    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    # ====== تنظیم ارتفاع ردیف‌ها ======
    ws.row_dimensions[1].height = 30
    for row in range(2, row_num):
        ws.row_dimensions[row].height = 25

    # ====== ایجاد پاسخ HTTP ======
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=گزارش_مشتریان_{timezone.now().strftime("%Y%m%d")}.xlsx'
    wb.save(response)

    return response


@login_required
def export_property_excel(request):
    """خروجی Excel از گزارش املاک"""
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "amlak_report_property"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    form = PropertyReportFilterForm(request.GET or None)

    queryset = Property.objects.filter(is_active=True).select_related(
        'property_type', 'province', 'city', 'neighborhood',
        'owner', 'created_by', 'supervisor', 'expert'
    )

    # اعمال فیلترها (همان منطق property_report)
    if form.is_valid():
        data = form.cleaned_data
        if data.get('property_type'):
            queryset = queryset.filter(property_type=data['property_type'])
        if data.get('status'):
            queryset = queryset.filter(status=data['status'])
        if data.get('contract_type'):
            queryset = queryset.filter(contract_type=data['contract_type'])
        province = data.get('province')
        if province:
            queryset = queryset.filter(city__province=province)
        city = data.get('city')
        if city:
            queryset = queryset.filter(city=city)
        # تاریخ‌ها و جستجو و تکراری‌ها (مشابه قبل)
        # ... (کد فیلتر تاریخ و جستجو و تکراری مشابه customer_report)

    # ====== ساخت فایل Excel ======
    wb = Workbook()
    ws = wb.active
    ws.title = 'گزارش املاک'

    headers = [
        'ردیف', 'عنوان', 'نوع ملک', 'استان', 'شهر', 'محله',
        'وضعیت', 'نوع قرارداد', 'قیمت (تومان)', 'مالک',
        'سرپرست', 'کارشناس', 'تاریخ ثبت'
    ]
    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=11)

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    row_num = 2
    for idx, prop in enumerate(queryset, 1):
        ws.cell(row=row_num, column=1, value=idx)
        ws.cell(row=row_num, column=2, value=prop.title or '')
        ws.cell(row=row_num, column=3, value=prop.property_type.name if prop.property_type else '')
        ws.cell(row=row_num, column=4, value=prop.province.name if prop.province else '')
        ws.cell(row=row_num, column=5, value=prop.city.name if prop.city else '')
        ws.cell(row=row_num, column=6, value=prop.neighborhood.name if prop.neighborhood else '')
        ws.cell(row=row_num, column=7, value=prop.get_status_display())
        ws.cell(row=row_num, column=8, value=prop.get_contract_type_display())
        ws.cell(row=row_num, column=9, value=int(prop.price) if prop.price else 0)
        ws.cell(row=row_num, column=10, value=prop.owner.get_full_name() if prop.owner else '')
        ws.cell(row=row_num, column=11, value=prop.supervisor.get_full_name() if prop.supervisor else '')
        ws.cell(row=row_num, column=12, value=prop.expert.get_full_name() if prop.expert else '')
        ws.cell(row=row_num, column=13, value=prop.created_at.strftime('%Y/%m/%d %H:%M') if prop.created_at else '')

        for col in range(1, len(headers) + 1):
            ws.cell(row=row_num, column=col).alignment = Alignment(horizontal='center', vertical='center')
        row_num += 1

    # تنظیم عرض ستون‌ها
    column_widths = {'A': 6, 'B': 25, 'C': 18, 'D': 15, 'E': 15, 'F': 18,
                     'G': 18, 'H': 18, 'I': 20, 'J': 20, 'K': 20, 'L': 20, 'M': 20}
    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=گزارش_املاک_{timezone.now().strftime("%Y%m%d")}.xlsx'
    wb.save(response)
    return response


@login_required
def export_process_excel(request):
    """خروجی Excel از گزارش فرآیندها"""
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "amlak_report_process"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    form = ProcessReportFilterForm(request.GET or None)
    queryset = CustomerProcess.objects.select_related(
        'customer', 'customer__user', 'expert', 'supervisor'
    )

    # اعمال فیلترها (همان منطق process_report)
    if form.is_valid():
        data = form.cleaned_data
        if data.get('status'):
            queryset = queryset.filter(status=data['status'])
        if data.get('expert'):
            queryset = queryset.filter(expert=data['expert'])
        if data.get('supervisor'):
            queryset = queryset.filter(supervisor=data['supervisor'])
        # فیلتر تاریخ‌ها و جستجو (مشابه قبل)
        # ... (کد فیلتر تاریخ و جستجو مشابه process_report)

    # ====== ساخت فایل Excel ======
    wb = Workbook()
    ws = wb.active
    ws.title = 'گزارش فرآیندها'

    headers = [
        'ردیف', 'مشتری', 'موبایل', 'کارشناس', 'سرپرست',
        'وضعیت', 'تاریخ انتساب', 'مهلت تماس', 'نتیجه نهایی',
        'تاریخ بسته شدن'
    ]
    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=11)

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    row_num = 2
    for idx, process in enumerate(queryset, 1):
        ws.cell(row=row_num, column=1, value=idx)
        ws.cell(row=row_num, column=2, value=process.customer.full_name)
        ws.cell(row=row_num, column=3, value=process.customer.mobile or '')
        ws.cell(row=row_num, column=4, value=process.expert.get_full_name() if process.expert else '')
        ws.cell(row=row_num, column=5, value=process.supervisor.get_full_name() if process.supervisor else '')
        ws.cell(row=row_num, column=6, value=process.get_status_display())
        ws.cell(row=row_num, column=7, value=process.assigned_at.strftime('%Y/%m/%d %H:%M') if process.assigned_at else '')
        ws.cell(row=row_num, column=8, value=process.contact_deadline.strftime('%Y/%m/%d %H:%M') if process.contact_deadline else '')
        ws.cell(row=row_num, column=9, value=process.final_result or '')
        ws.cell(row=row_num, column=10, value=process.closed_at.strftime('%Y/%m/%d %H:%M') if process.closed_at else '')

        for col in range(1, len(headers) + 1):
            ws.cell(row=row_num, column=col).alignment = Alignment(horizontal='center', vertical='center')
        row_num += 1

    # تنظیم عرض ستون‌ها
    column_widths = {'A': 6, 'B': 25, 'C': 15, 'D': 20, 'E': 20,
                     'F': 18, 'G': 20, 'H': 20, 'I': 30, 'J': 20}
    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=گزارش_فرآیندها_{timezone.now().strftime("%Y%m%d")}.xlsx'
    wb.save(response)
    return response


@login_required
def export_contract_excel(request):
    """خروجی Excel از گزارش قراردادها"""
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "amlak_report_contract"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    form = ContractReportFilterForm(request.GET or None)
    queryset = Contract.objects.select_related(
        'customer', 'customer__user', 'property_ref',
        'process__expert', 'process__supervisor'
    )

    # اعمال فیلترها (همان منطق contract_report)
    if form.is_valid():
        data = form.cleaned_data
        if data.get('status'):
            queryset = queryset.filter(status=data['status'])
        if data.get('contract_type'):
            queryset = queryset.filter(contract_type=data['contract_type'])
        # فیلتر تاریخ‌ها و جستجو (مشابه قبل)
        # ... (کد فیلتر تاریخ و جستجو مشابه contract_report)

    # ====== ساخت فایل Excel ======
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = 'گزارش قراردادها'

    headers = [
        'ردیف', 'شماره قرارداد', 'مشتری', 'موبایل', 'ملک',
        'نوع قرارداد', 'وضعیت', 'مبلغ نهایی (تومان)',
        'کارشناس', 'سرپرست', 'تاریخ ایجاد', 'تاریخ تکمیل'
    ]
    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=11)

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    row_num = 2
    for idx, contract in enumerate(queryset, 1):
        ws.cell(row=row_num, column=1, value=idx)
        ws.cell(row=row_num, column=2, value=contract.contract_number or '')
        ws.cell(row=row_num, column=3, value=contract.customer_name)
        ws.cell(row=row_num, column=4, value=contract.customer.mobile if contract.customer else '')
        ws.cell(row=row_num, column=5, value=contract.property_title)
        ws.cell(row=row_num, column=6, value=contract.get_contract_type_display())
        ws.cell(row=row_num, column=7, value=contract.get_status_display())
        ws.cell(row=row_num, column=8, value=int(contract.final_amount) if contract.final_amount else 0)
        ws.cell(row=row_num, column=9, value=contract.expert.get_full_name() if contract.expert else '')
        ws.cell(row=row_num, column=10, value=contract.supervisor.get_full_name() if contract.supervisor else '')
        ws.cell(row=row_num, column=11, value=contract.created_at.strftime('%Y/%m/%d %H:%M') if contract.created_at else '')
        ws.cell(row=row_num, column=12, value=contract.finalization_date.strftime('%Y/%m/%d %H:%M') if contract.finalization_date else '')

        for col in range(1, len(headers) + 1):
            ws.cell(row=row_num, column=col).alignment = Alignment(horizontal='center', vertical='center')
        row_num += 1

    column_widths = {'A': 6, 'B': 20, 'C': 25, 'D': 15, 'E': 25,
                     'F': 15, 'G': 18, 'H': 20, 'I': 20, 'J': 20, 'K': 20, 'L': 20}
    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=گزارش_قراردادها_{timezone.now().strftime("%Y%m%d")}.xlsx'
    wb.save(response)
    return response


@login_required
def export_commission_excel(request):
    """خروجی Excel از گزارش حسابداری"""
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "amlak_report_commission"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    form = CommissionReportFilterForm(request.GET or None)
    queryset = Commission.objects.select_related(
        'contract', 'contract__customer', 'contract__customer__user',
        'contract__property_ref', 'accountant'
    )

    # اعمال فیلترها (همان منطق commission_report)
    if form.is_valid():
        data = form.cleaned_data
        if data.get('status'):
            queryset = queryset.filter(status=data['status'])
        # فیلتر تاریخ‌ها و جستجو (مشابه قبل)
        # ... (کد فیلتر تاریخ و جستجو مشابه commission_report)

    # ====== ساخت فایل Excel ======
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = 'گزارش حسابداری'

    headers = [
        'ردیف', 'مشتری', 'موبایل', 'ملک',
        'مبلغ کل معامله (تومان)', 'مبلغ کمیسیون (تومان)',
        'وضعیت', 'حسابدار', 'تاریخ ایجاد'
    ]
    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=11)

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    row_num = 2
    for idx, commission in enumerate(queryset, 1):
        ws.cell(row=row_num, column=1, value=idx)
        ws.cell(row=row_num, column=2, value=commission.contract.customer.full_name if commission.contract.customer else '')
        ws.cell(row=row_num, column=3, value=commission.contract.customer.mobile if commission.contract.customer else '')
        ws.cell(row=row_num, column=4, value=commission.contract.property_title)
        ws.cell(row=row_num, column=5, value=int(commission.total_amount) if commission.total_amount else 0)
        ws.cell(row=row_num, column=6, value=int(commission.total_commission) if commission.total_commission else 0)
        ws.cell(row=row_num, column=7, value=commission.get_status_display())
        ws.cell(row=row_num, column=8, value=commission.accountant.get_full_name() if commission.accountant else '')
        ws.cell(row=row_num, column=9, value=commission.created_at.strftime('%Y/%m/%d %H:%M') if commission.created_at else '')

        for col in range(1, len(headers) + 1):
            ws.cell(row=row_num, column=col).alignment = Alignment(horizontal='center', vertical='center')
        row_num += 1

    column_widths = {'A': 6, 'B': 25, 'C': 15, 'D': 25, 'E': 20, 'F': 20, 'G': 18, 'H': 20, 'I': 20}
    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=گزارش_حسابداری_{timezone.now().strftime("%Y%m%d")}.xlsx'
    wb.save(response)
    return response


@login_required
def api_status_chart(request):
    """API برای نمودار وضعیت‌ها (برای AJAX)"""
    data = get_status_chart_data()
    return JsonResponse(data)