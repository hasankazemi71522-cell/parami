# case_management/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta

from account.models import User
from estate.models import Customer, Property, Match, Note
from .models import (
    CustomerProcess, IntroductionReport, Visit,
    ProcessLog, SupervisorAlert, ProcessNote
)
from .forms import (
    AssignCustomerForm, ContactForm, IntroReportForm,
    VisitCreateForm, VisitScheduleForm, VisitResultForm
)
from myclass.mydef import views_permissions
from myclass.mydef import to_shamsi_date, to_shamsi_datetime
from estate.utils_match import MatchManager
from .utils import jalali_to_gregorian, gregorian_to_jalali


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
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


# ============================================================
# 🔧 توابع کمکی
# ============================================================

def is_process_closed(process):
    """بررسی بسته بودن فرآیند (فقط وضعیت‌های نهایی)"""
    return process.status in [
        CustomerProcess.Status.CLOSED_SUCCESS,
        CustomerProcess.Status.CLOSED_FAIL,
        CustomerProcess.Status.CANCELLED,
        CustomerProcess.Status.CONVERTED,
        CustomerProcess.Status.SENT_TO_ACCOUNTING,
    ]


def is_process_in_contract(process):
    """بررسی اینکه فرآیند در واحد قرارداد است"""
    return process.status == CustomerProcess.Status.CONTRACT_PENDING


def is_process_in_accounting(process):
    """بررسی اینکه فرآیند به حسابداری ارسال شده است"""
    return process.status == CustomerProcess.Status.SENT_TO_ACCOUNTING


def get_active_processes_count(expert):
    """دریافت تعداد فرآیندهای فعال یک کارشناس (منهای بسته‌شده)"""
    return CustomerProcess.objects.filter(
        expert=expert
    ).exclude(
        status__in=[
            CustomerProcess.Status.CLOSED_SUCCESS,
            CustomerProcess.Status.CLOSED_FAIL,
            CustomerProcess.Status.CANCELLED,
            CustomerProcess.Status.CONVERTED,
            CustomerProcess.Status.SENT_TO_ACCOUNTING,
        ]
    ).count()


def is_expert_available(expert):
    """بررسی در دسترس بودن کارشناس بر اساس ظرفیت"""
    active_count = get_active_processes_count(expert)
    return active_count < expert.max_concurrent


# ============================================================
# 📊 داشبورد سرپرست
# ============================================================

@login_required
def supervisor_dashboard(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "supervisor_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    # ====== آمار کلی ======
    total_processes = CustomerProcess.objects.filter(supervisor=user).count()

    active_processes = CustomerProcess.objects.filter(
        supervisor=user
    ).exclude(
        status__in=[
            CustomerProcess.Status.CLOSED_SUCCESS,
            CustomerProcess.Status.CLOSED_FAIL,
            CustomerProcess.Status.CANCELLED,
            CustomerProcess.Status.CONVERTED,
            CustomerProcess.Status.SENT_TO_ACCOUNTING,
        ]
    ).count()

    contract_pending = CustomerProcess.objects.filter(
        supervisor=user,
        status=CustomerProcess.Status.CONTRACT_PENDING
    ).count()

    in_accounting = CustomerProcess.objects.filter(
        supervisor=user,
        status=CustomerProcess.Status.SENT_TO_ACCOUNTING
    ).count()

    closed_success = CustomerProcess.objects.filter(
        supervisor=user,
        status=CustomerProcess.Status.CLOSED_SUCCESS
    ).count()

    closed_fail = CustomerProcess.objects.filter(
        supervisor=user,
        status=CustomerProcess.Status.CLOSED_FAIL
    ).count()

    unread_alerts = SupervisorAlert.objects.filter(
        process__supervisor=user,
        is_read=False
    ).count()

    # ====== کارشناسان زیرمجموعه ======
    experts = User.objects.filter(
        referral=user,
        is_active=True,
        user_roles__role__name='expert',
        user_roles__is_active=True
    ).distinct().order_by('first_name', 'last_name')

    expert_stats = []
    for expert in experts:
        processes = CustomerProcess.objects.filter(supervisor=user, expert=expert)

        active_count = processes.exclude(
            status__in=[
                CustomerProcess.Status.CLOSED_SUCCESS,
                CustomerProcess.Status.CLOSED_FAIL,
                CustomerProcess.Status.CANCELLED,
                CustomerProcess.Status.CONVERTED,
                CustomerProcess.Status.SENT_TO_ACCOUNTING,
            ]
        ).count()

        is_available = active_count < expert.max_concurrent

        contract_pending_count = processes.filter(
            status=CustomerProcess.Status.CONTRACT_PENDING
        ).count()

        pending_intro_total = Match.objects.filter(
            customer__processes__expert=expert,
            customer__processes__supervisor=user,
            match_score__gte=50,
            introduction_status=Match.IntroductionStatus.PENDING
        ).count()

        expert_stats.append({
            'expert': expert,
            'total': processes.count(),
            'active': active_count,
            'max_capacity': expert.max_concurrent,
            'is_available': is_available,
            'contract_pending': contract_pending_count,
            'success': processes.filter(
                status=CustomerProcess.Status.CLOSED_SUCCESS
            ).count(),
            'contact_pending': processes.filter(
                status__in=[
                    CustomerProcess.Status.ASSIGNED,
                    CustomerProcess.Status.CONTACT_PENDING
                ]
            ).count(),
            'pending_intro_count': pending_intro_total,
        })

    # ====== مشتریان ======
    customers_without_expert = Customer.objects.filter(
        supervisor=user,
        expert__isnull=True,
        is_active=True,
        status__in=[Customer.Status.CONFIRMED, Customer.Status.NEW]
    ).select_related('user', 'source').order_by('-created_at')

    customers_with_expert = Customer.objects.filter(
        supervisor=user,
        expert__isnull=False,
        is_active=True,
        status__in=[Customer.Status.CONFIRMED, Customer.Status.NEW]
    ).select_related('user', 'source', 'expert').order_by('-created_at')

    # ✅ اضافه کردن تاریخ شمسی به مشتریان
    for c in customers_without_expert:
        c.created_at_shamsi = get_shamsi_date(c.created_at)
    for c in customers_with_expert:
        c.created_at_shamsi = get_shamsi_date(c.created_at)

    recent_alerts = SupervisorAlert.objects.filter(
        process__supervisor=user
    ).order_by('-created_at')[:10]

    # ✅ اضافه کردن تاریخ شمسی به اخطارها
    for alert in recent_alerts:
        alert.created_at_shamsi = get_shamsi_datetime(alert.created_at)

    context = {
        'title': 'داشبورد سرپرست',
        'total_processes': total_processes,
        'active_processes': active_processes,
        'contract_pending': contract_pending,
        'in_accounting': in_accounting,
        'closed_success': closed_success,
        'closed_fail': closed_fail,
        'unread_alerts': unread_alerts,
        'expert_stats': expert_stats,
        'customers_without_expert': customers_without_expert,
        'customers_with_expert': customers_with_expert,
        'experts': experts,
        'recent_alerts': recent_alerts,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'case_management/supervisor_dashboard.html', context)


# ============================================================
# 🎯 اختصاص کارشناس به مشتری (توسط سرپرست)
# ============================================================

@login_required
def assign_expert_to_customer(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "supervisor_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    if request.method != 'POST':
        messages.error(request, 'روش نامعتبر')
        return redirect('case_management:supervisor_dashboard')

    customer_id = request.POST.get('customer_id')
    expert_id = request.POST.get('expert_id')

    if not customer_id or not expert_id:
        messages.error(request, 'لطفاً مشتری و کارشناس را انتخاب کنید')
        return redirect('case_management:supervisor_dashboard')

    try:
        with transaction.atomic():
            customer = Customer.objects.get(
                id=customer_id,
                supervisor=user,
                is_active=True
            )

            if customer.status in [Customer.Status.IN_MEETING, Customer.Status.CONTRACT]:
                messages.error(request, 'این مشتری در حال حاضر در جلسه یا قرارداد است و قابل انتساب نیست.')
                return redirect('case_management:supervisor_dashboard')

            expert = User.objects.get(
                id=expert_id,
                referral=user,
                is_active=True,
                user_roles__role__name='expert',
                user_roles__is_active=True
            )

            active_count = get_active_processes_count(expert)
            if active_count >= expert.max_concurrent:
                messages.error(
                    request,
                    f'کارشناس {expert.get_full_name()} در حال حاضر ظرفیت کامل دارد. '
                    f'({active_count}/{expert.max_concurrent} پرونده فعال)'
                )
                return redirect('case_management:supervisor_dashboard')

            existing_process = CustomerProcess.objects.filter(
                customer=customer,
                supervisor=user
            ).exclude(
                status__in=[
                    CustomerProcess.Status.CLOSED_SUCCESS,
                    CustomerProcess.Status.CLOSED_FAIL,
                    CustomerProcess.Status.CANCELLED,
                    CustomerProcess.Status.CONVERTED,
                    CustomerProcess.Status.SENT_TO_ACCOUNTING,
                ]
            ).first()

            if existing_process and is_process_closed(existing_process):
                messages.error(request, 'این فرآیند قبلاً بسته شده است و قابل تغییر نیست.')
                return redirect('case_management:supervisor_dashboard')

            old_expert_name = existing_process.expert.get_full_name() if existing_process and existing_process.expert else 'بدون کارشناس'

            if existing_process:
                existing_process.expert = expert
                now = timezone.now()

                if not existing_process.contact_made_at:
                    existing_process.contact_deadline = now + timedelta(hours=24)
                    if existing_process.status not in [CustomerProcess.Status.ASSIGNED,
                                                       CustomerProcess.Status.CONTACT_PENDING]:
                        existing_process.status = CustomerProcess.Status.ASSIGNED

                elif existing_process.contact_made_at and not existing_process.introduction_completed_at:
                    existing_process.intro_deadline = now + timedelta(hours=24)
                    if existing_process.status not in [CustomerProcess.Status.CONTACTED,
                                                       CustomerProcess.Status.INTRO_PENDING]:
                        existing_process.status = CustomerProcess.Status.CONTACTED

                elif existing_process.status in [CustomerProcess.Status.VISIT_DONE, CustomerProcess.Status.NEGOTIATION]:
                    last_visit = existing_process.visits.filter(status=Visit.Status.DONE).first()
                    if last_visit and not last_visit.visit_result:
                        existing_process.visit_result_deadline = now + timedelta(hours=24)
                        if existing_process.status == CustomerProcess.Status.NEGOTIATION:
                            existing_process.status = CustomerProcess.Status.VISIT_DONE

                existing_process.save()

                ProcessLog.objects.create(
                    process=existing_process,
                    action=ProcessLog.ActionType.STATUS_CHANGE,
                    description=f"کارشناس توسط سرپرست {user.get_full_name()} از {old_expert_name} به {expert.get_full_name()} تغییر یافت. مهلت‌های انجام‌نشده بازنشانی شد.",
                    performed_by=user,
                    new_value=existing_process.status
                )

                messages.success(
                    request,
                    f'کارشناس مشتری {customer.full_name} با موفقیت از {old_expert_name} به {expert.get_full_name()} تغییر یافت و مهلت‌های انجام‌نشده بازنشانی شد.'
                )

            else:
                process = CustomerProcess.objects.create(
                    customer=customer,
                    expert=expert,
                    supervisor=user,
                    status=CustomerProcess.Status.ASSIGNED,
                    contact_deadline=timezone.now() + timedelta(hours=24)
                )

                ProcessLog.objects.create(
                    process=process,
                    action=ProcessLog.ActionType.STATUS_CHANGE,
                    description=f"فرآیند جدید توسط سرپرست {user.get_full_name()} با کارشناس {expert.get_full_name()} ایجاد شد",
                    performed_by=user,
                    new_value=CustomerProcess.Status.ASSIGNED
                )

                messages.success(
                    request,
                    f'فرآیند جدید برای مشتری {customer.full_name} با کارشناس {expert.get_full_name()} ایجاد شد'
                )

            customer.expert = expert
            customer.save(update_fields=['expert'])

    except Customer.DoesNotExist:
        messages.error(request, 'مشتری مورد نظر یافت نشد یا زیرمجموعه شما نیست')
    except User.DoesNotExist:
        messages.error(request, 'کارشناس مورد نظر یافت نشد یا زیرمجموعه شما نیست')
    except Exception as e:
        messages.error(request, f'خطا: {str(e)}')

    return redirect('case_management:supervisor_dashboard')


# ============================================================
# 👤 لیست فرآیندهای سرپرست
# ============================================================

@login_required
def supervisor_process_list(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "supervisor_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    processes = CustomerProcess.objects.filter(
        supervisor=user
    ).exclude(
        status__in=[
            CustomerProcess.Status.CLOSED_SUCCESS,
            CustomerProcess.Status.CLOSED_FAIL,
            CustomerProcess.Status.CANCELLED,
            CustomerProcess.Status.CONVERTED,
            CustomerProcess.Status.SENT_TO_ACCOUNTING,
        ]
    ).select_related(
        'customer', 'customer__user', 'expert', 'supervisor'
    ).prefetch_related(
        'visits', 'introduction_reports'
    ).annotate(
        pending_intro_count=Count(
            'customer__matches',
            filter=Q(
                customer__matches__match_score__gte=50,
                customer__matches__introduction_status=Match.IntroductionStatus.PENDING
            ),
            distinct=True
        )
    ).order_by('-assigned_at')

    status_filter = request.GET.get('status', '')
    if status_filter:
        processes = processes.filter(status=status_filter)

    expert_filter = request.GET.get('expert', '')
    if expert_filter:
        processes = processes.filter(expert_id=expert_filter)

    date_from = request.GET.get('date_from', '')
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            processes = processes.filter(assigned_at__date__gte=date_from_obj)
        except:
            pass

    date_to = request.GET.get('date_to', '')
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            processes = processes.filter(assigned_at__date__lte=date_to_obj)
        except:
            pass

    search = request.GET.get('search', '')
    if search:
        processes = processes.filter(
            Q(customer__user__first_name__icontains=search) |
            Q(customer__user__last_name__icontains=search) |
            Q(customer__user__mobile__icontains=search) |
            Q(expert__first_name__icontains=search) |
            Q(expert__last_name__icontains=search)
        )

    experts = User.objects.filter(
        referral=user,
        is_active=True,
        user_roles__role__name='expert',
        user_roles__is_active=True
    ).distinct().order_by('first_name', 'last_name')

    paginator = Paginator(processes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر فرآیند
    for p in page_obj:
        p.assigned_at_shamsi = get_shamsi_datetime(p.assigned_at)
        p.contact_deadline_shamsi = get_shamsi_datetime(p.contact_deadline)
        p.intro_deadline_shamsi = get_shamsi_datetime(p.intro_deadline)
        p.visit_result_deadline_shamsi = get_shamsi_datetime(p.visit_result_deadline)
        p.closed_at_shamsi = get_shamsi_datetime(p.closed_at)

    process_statuses = CustomerProcess.Status.choices

    context = {
        'title': 'لیست فرآیندها',
        'processes': page_obj,
        'experts': experts,
        'status_filter': status_filter,
        'expert_filter': expert_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        'process_statuses': process_statuses,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'case_management/supervisor_process_list.html', context)


# ============================================================
# 📋 جزئیات فرآیند (سرپرست)
# ============================================================

@login_required
def supervisor_process_detail(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "supervisor_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    process = get_object_or_404(
        CustomerProcess,
        pk=pk,
        supervisor=user
    )

    # ✅ اضافه کردن تاریخ شمسی به فرآیند
    process.assigned_at_shamsi = get_shamsi_datetime(process.assigned_at)
    process.contact_made_at_shamsi = get_shamsi_datetime(process.contact_made_at)
    process.introduction_completed_at_shamsi = get_shamsi_datetime(process.introduction_completed_at)
    process.contact_deadline_shamsi = get_shamsi_datetime(process.contact_deadline)
    process.intro_deadline_shamsi = get_shamsi_datetime(process.intro_deadline)
    process.visit_result_deadline_shamsi = get_shamsi_datetime(process.visit_result_deadline)
    process.closed_at_shamsi = get_shamsi_datetime(process.closed_at)
    process.created_at_shamsi = get_shamsi_datetime(process.created_at)

    contact_notes = process.notes.filter(
        note_type=ProcessNote.NoteType.CONTACT_REPORT
    ).order_by('-created_at')

    # ✅ اضافه کردن تاریخ شمسی به نت‌ها
    for note in contact_notes:
        note.created_at_shamsi = get_shamsi_datetime(note.created_at)

    estate_notes = process.customer.notes.all().order_by('-created_at')

    # ✅ اضافه کردن تاریخ شمسی به یادداشت‌ها
    for note in estate_notes:
        note.created_at_shamsi = get_shamsi_datetime(note.created_at)

    all_matches = Match.objects.filter(
        customer=process.customer,
        match_score__gte=50
    ).select_related('property_ref').order_by('-match_score')

    pending_matches = all_matches.filter(
        introduction_status=Match.IntroductionStatus.PENDING
    )
    reported_matches = all_matches.exclude(
        introduction_status=Match.IntroductionStatus.PENDING
    ).order_by('-introduction_status', '-match_score')

    ordered_matches = list(pending_matches) + list(reported_matches)

    intro_reports = process.introduction_reports.all().order_by('-created_at')
    intro_reported_ids = list(intro_reports.values_list('property_ref_id', flat=True))

    # ✅ اضافه کردن تاریخ شمسی به گزارش‌های معرفی
    for report in intro_reports:
        report.created_at_shamsi = get_shamsi_datetime(report.created_at)
        report.follow_up_date_shamsi = get_shamsi_datetime(report.follow_up_date)

    follow_up_alerts = intro_reports.filter(
        follow_up_date__lte=timezone.now(),
        result__in=['pending', 'fail']
    ).select_related('property_ref').order_by('follow_up_date')

    total_matches = all_matches.count()
    reported_count = intro_reports.count()
    pending_intro = total_matches - reported_count
    intro_complete = (pending_intro <= 0)

    contact_deadline_passed = process.is_contact_deadline_passed
    intro_deadline_passed = process.is_intro_deadline_passed
    last_visit = process.visits.filter(status=Visit.Status.DONE).first()

    # ✅ اضافه کردن تاریخ شمسی به بازدیدها
    visits = process.visits.all().order_by('-created_at')
    for visit in visits:
        visit.scheduled_time_shamsi = get_shamsi_datetime(visit.scheduled_time)
        visit.confirmed_at_shamsi = get_shamsi_datetime(visit.confirmed_at)
        visit.done_at_shamsi = get_shamsi_datetime(visit.done_at)
        visit.created_at_shamsi = get_shamsi_datetime(visit.created_at)
        visit.meeting_held_at_shamsi = get_shamsi_datetime(visit.meeting_held_at)

    # ✅ اضافه کردن تاریخ شمسی به لاگ‌ها
    logs = process.logs.all().order_by('-created_at')[:50]
    for log in logs:
        log.created_at_shamsi = get_shamsi_datetime(log.created_at)

    # ✅ اضافه کردن تاریخ شمسی به اخطارها
    alerts = process.alerts.all().order_by('-created_at')
    for alert in alerts:
        alert.created_at_shamsi = get_shamsi_datetime(alert.created_at)

    supervisors = User.objects.filter(
        is_active=True,
        user_roles__role__name='supervisor',
        user_roles__is_active=True
    ).distinct().order_by('first_name', 'last_name')

    context = {
        'title': f'جزئیات فرآیند - {process.customer.full_name}',
        'process': process,
        'is_closed': is_process_closed(process),
        'is_in_contract': is_process_in_contract(process),
        'is_in_accounting': is_process_in_accounting(process),
        'contact_notes': contact_notes,
        'estate_notes': estate_notes,
        'visits': visits,
        'all_matches': ordered_matches,
        'pending_matches': pending_matches,
        'reported_matches': reported_matches,
        'intro_reports': intro_reports,
        'follow_up_alerts': follow_up_alerts,
        'logs': logs,
        'alerts': alerts,
        'total_matches': total_matches,
        'reported_count': reported_count,
        'pending_intro': pending_intro,
        'intro_complete': intro_complete,
        'intro_reported_ids': intro_reported_ids,
        'contact_deadline_passed': contact_deadline_passed,
        'intro_deadline_passed': intro_deadline_passed,
        'last_visit': last_visit,
        'supervisors': supervisors,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'case_management/supervisor_process_detail.html', context)


# ============================================================
# 📝 اقدامات سرپرست (با بررسی بسته بودن)
# ============================================================

@login_required
def supervisor_add_note(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "supervisor_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    process = get_object_or_404(
        CustomerProcess,
        pk=pk,
        supervisor=user
    )

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    note_type = request.POST.get('note_type', 'general')
    target = request.POST.get('target', 'public')
    content = request.POST.get('content', '').strip()

    if not content:
        return JsonResponse({'error': 'متن نت نمی‌تواند خالی باشد'}, status=400)

    try:
        note = ProcessNote.objects.create(
            process=process,
            note_type=note_type,
            target=target,
            content=content,
            created_by=user
        )

        ProcessLog.objects.create(
            process=process,
            action=ProcessLog.ActionType.STATUS_CHANGE,
            description=f"نت توسط سرپرست {user.get_full_name()} ثبت شد",
            performed_by=user,
            new_value=process.status
        )

        return JsonResponse({
            'success': True,
            'message': 'نت با موفقیت ثبت شد',
            'note_id': str(note.id),
            'created_at': get_shamsi_datetime(note.created_at)  # ✅
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def supervisor_add_contact(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "supervisor_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    process = get_object_or_404(
        CustomerProcess,
        pk=pk,
        supervisor=user
    )

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    report_text = request.POST.get('report_text', '').strip()
    target = request.POST.get('target', 'public')

    if not report_text:
        return JsonResponse({'error': 'لطفاً گزارش تماس را وارد کنید'}, status=400)

    try:
        note = ProcessNote.objects.create(
            process=process,
            note_type=ProcessNote.NoteType.CONTACT_REPORT,
            target=target,
            content=report_text,
            created_by=user
        )

        ProcessLog.objects.create(
            process=process,
            action=ProcessLog.ActionType.CONTACT_MADE,
            description=f"تماس توسط سرپرست {user.get_full_name()} ثبت شد",
            performed_by=user,
            new_value=process.status
        )

        return JsonResponse({
            'success': True,
            'message': 'تماس با موفقیت ثبت شد'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def supervisor_add_estate_note(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "supervisor_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    process = get_object_or_404(CustomerProcess, pk=pk, supervisor=user)

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    note_type = request.POST.get('note_type', 'general')
    priority = request.POST.get('priority', 'medium')

    if not title or not content:
        return JsonResponse({'error': 'عنوان و متن یادداشت الزامی است'}, status=400)

    try:
        note = Note.objects.create(
            customer=process.customer,
            note_type=note_type,
            priority=priority,
            title=title,
            content=content,
            created_by=user,
        )

        ProcessLog.objects.create(
            process=process,
            action=ProcessLog.ActionType.STATUS_CHANGE,
            description=f"یادداشت عمومی '{title}' توسط سرپرست ثبت شد",
            performed_by=user,
            new_value=process.status
        )

        return JsonResponse({
            'success': True,
            'message': 'یادداشت با موفقیت ثبت شد'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def supervisor_add_intro_report(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "supervisor_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    process = get_object_or_404(
        CustomerProcess,
        pk=pk,
        supervisor=user
    )

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    property_id = request.POST.get('property_id')
    result = request.POST.get('result')
    expert_note = request.POST.get('expert_note', '')
    follow_up_date_str = request.POST.get('follow_up_date', '')

    if not property_id or not result:
        return JsonResponse({'error': 'لطفاً فایل و نتیجه را انتخاب کنید'}, status=400)

    try:
        with transaction.atomic():
            property_obj = Property.objects.get(id=property_id, is_active=True)

            if property_obj.status in [Property.Status.IN_MEETING, Property.Status.CONTRACT]:
                return JsonResponse({'error': 'این فایل در حال حاضر در جلسه یا قرارداد است و قابل معرفی نیست.'},
                                    status=400)

            follow_up_date = None
            if follow_up_date_str:
                try:
                    follow_up_date = jalali_to_gregorian(follow_up_date_str)
                except ValueError as e:
                    return JsonResponse({'error': str(e)}, status=400)

            report = IntroductionReport.objects.create(
                process=process,
                property_ref=property_obj,
                result=result,
                expert_note=expert_note,
                follow_up_date=follow_up_date
            )

            match = Match.objects.filter(
                customer=process.customer,
                property_ref=property_obj
            ).first()

            if match:
                if result == 'success':
                    match.introduction_status = Match.IntroductionStatus.SUCCESS
                elif result == 'fail':
                    match.introduction_status = Match.IntroductionStatus.FAIL
                elif result == 'pending':
                    match.introduction_status = Match.IntroductionStatus.PENDING
                match.save(update_fields=['introduction_status'])

            total_matches = Match.objects.filter(
                customer=process.customer,
                match_score__gte=50
            ).count()
            reported_count = process.introduction_reports.count()

            if reported_count >= total_matches and total_matches > 0:
                process.status = CustomerProcess.Status.INTRODUCED
                process.introduction_completed_at = timezone.now()
                process.save()
                ProcessLog.objects.create(
                    process=process,
                    action=ProcessLog.ActionType.INTRO_REPORTED,
                    description=f"همه گزارش‌های معرفی ({reported_count} مورد) تکمیل شد (توسط سرپرست)",
                    performed_by=user,
                    new_value=CustomerProcess.Status.INTRODUCED
                )

            return JsonResponse({
                'success': True,
                'message': 'گزارش معرفی با موفقیت ثبت شد',
                'reported_count': reported_count,
                'total_matches': total_matches,
                'intro_complete': reported_count >= total_matches
            })

    except Property.DoesNotExist:
        return JsonResponse({'error': 'فایل مورد نظر یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def supervisor_create_visit_direct(request, process_pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "supervisor_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    process = get_object_or_404(
        CustomerProcess,
        pk=process_pk,
        supervisor=user
    )

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    property_id = request.POST.get('property_id')
    scheduled_time_str = request.POST.get('scheduled_time')

    if not property_id:
        return JsonResponse({'error': 'لطفاً فایل را انتخاب کنید'}, status=400)

    if not scheduled_time_str:
        return JsonResponse({'error': 'لطفاً تاریخ و زمان بازدید را مشخص کنید'}, status=400)

    try:
        scheduled_time = jalali_to_gregorian(scheduled_time_str)
        if scheduled_time < timezone.now():
            return JsonResponse({'error': 'زمان بازدید باید در آینده باشد'}, status=400)

        property_obj = Property.objects.get(id=property_id, is_active=True)

        if property_obj.status in [Property.Status.IN_MEETING, Property.Status.CONTRACT]:
            return JsonResponse({'error': 'این فایل در حال حاضر در جلسه یا قرارداد است و قابل برنامه‌ریزی نیست.'},
                                status=400)

        with transaction.atomic():
            existing = Visit.objects.filter(
                process=process,
                property_ref=property_obj
            ).exclude(status=Visit.Status.CANCELLED).exists()

            visit = Visit.objects.create(
                process=process,
                property_ref=property_obj,
                status=Visit.Status.SCHEDULED,
                scheduled_time=scheduled_time
            )

            process.status = CustomerProcess.Status.VISIT_SCHEDULED
            process.save()

            ProcessLog.objects.create(
                process=process,
                action=ProcessLog.ActionType.VISIT_SCHEDULED,
                description=f"زمان بازدید {property_obj.title} برای {gregorian_to_jalali(scheduled_time)} برنامه‌ریزی شد (توسط سرپرست)",
                performed_by=user,
                new_value=CustomerProcess.Status.VISIT_SCHEDULED
            )

            return JsonResponse({
                'success': True,
                'message': 'بازدید با موفقیت ثبت شد',
                'visit_id': str(visit.id)
            })

    except Property.DoesNotExist:
        return JsonResponse({'error': 'فایل مورد نظر یافت نشد'}, status=404)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# 🔄 محاسبه تطابق (سرپرست)
# ============================================================

@login_required
def supervisor_calculate_matches_for_customer(request, customer_id):
    user = request.user

    customer = get_object_or_404(Customer, id=customer_id, supervisor=user)

    if customer.status in [Customer.Status.IN_MEETING, Customer.Status.CONTRACT]:
        messages.warning(request, 'این مشتری در حال حاضر در جلسه یا قرارداد است و تطابق محاسبه نمی‌شود.')
        return redirect(request.META.get('HTTP_REFERER', 'case_management:supervisor_dashboard'))

    result = MatchManager.calculate_and_save_matches_for_customer(
        customer=customer,
        min_score=50,
        created_by=user,
        remove_low=True
    )

    messages.success(
        request,
        f'تطابق‌های مشتری {customer.full_name} به‌روزرسانی شد. '
        f'({result["saved"]} مورد جدید، {result["updated"]} مورد به‌روزرسانی، {result["deleted"]} مورد حذف)'
    )
    return redirect(request.META.get('HTTP_REFERER', 'case_management:supervisor_dashboard'))


@login_required
def supervisor_calculate_all_matches(request):
    user = request.user

    customers = Customer.objects.filter(
        supervisor=user,
        is_active=True,
        status__in=[Customer.Status.CONFIRMED, Customer.Status.NEW]
    ).distinct()

    total_saved = 0
    total_updated = 0
    total_deleted = 0

    for customer in customers:
        result = MatchManager.calculate_and_save_matches_for_customer(
            customer=customer,
            min_score=50,
            created_by=user,
            remove_low=True
        )
        total_saved += result['saved']
        total_updated += result['updated']
        total_deleted += result['deleted']

    messages.success(
        request,
        f'تطابق‌های همه مشتریان فعال شما به‌روزرسانی شد. '
        f'{total_saved} مورد جدید، {total_updated} مورد به‌روزرسانی، {total_deleted} مورد حذف.'
    )
    return redirect('case_management:supervisor_dashboard')


@login_required
def supervisor_calculate_matches_for_filtered(request):
    user = request.user

    status_filter = request.GET.get('status', '')
    expert_filter = request.GET.get('expert', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '')

    customers = Customer.objects.filter(
        processes__supervisor=user,
        is_active=True,
        status__in=[Customer.Status.CONFIRMED, Customer.Status.NEW]
    ).distinct()

    if status_filter:
        customers = customers.filter(processes__status=status_filter)
    if expert_filter:
        customers = customers.filter(processes__expert_id=expert_filter)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            customers = customers.filter(processes__assigned_at__date__gte=date_from_obj)
        except:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            customers = customers.filter(processes__assigned_at__date__lte=date_to_obj)
        except:
            pass
    if search:
        customers = customers.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__mobile__icontains=search)
        )

    total_saved = 0
    total_updated = 0
    total_deleted = 0

    for customer in customers:
        result = MatchManager.calculate_and_save_matches_for_customer(
            customer=customer,
            min_score=50,
            created_by=user,
            remove_low=True
        )
        total_saved += result['saved']
        total_updated += result['updated']
        total_deleted += result['deleted']

    messages.success(
        request,
        f'تطابق‌های {customers.count()} مشتری در لیست فعلی به‌روزرسانی شد. '
        f'{total_saved} مورد جدید، {total_updated} مورد به‌روزرسانی، {total_deleted} مورد حذف.'
    )
    return redirect(request.META.get('HTTP_REFERER', 'case_management:supervisor_process_list'))


# ============================================================
# 📊 داشبورد کارشناس
# ============================================================

@login_required
def expert_dashboard(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    processes = CustomerProcess.objects.filter(
        expert=user
    ).exclude(
        status__in=[
            CustomerProcess.Status.CLOSED_SUCCESS,
            CustomerProcess.Status.CLOSED_FAIL,
            CustomerProcess.Status.CANCELLED,
            CustomerProcess.Status.CONVERTED,
            CustomerProcess.Status.SENT_TO_ACCOUNTING,
        ]
    ).select_related(
        'customer', 'customer__user', 'supervisor'
    ).prefetch_related(
        'visits', 'introduction_reports'
    ).annotate(
        pending_intro_count=Count(
            'customer__matches',
            filter=Q(
                customer__matches__match_score__gte=50,
                customer__matches__introduction_status=Match.IntroductionStatus.PENDING
            ),
            distinct=True
        )
    ).order_by('-customer__priority', '-assigned_at')

    status_filter = request.GET.get('status', '')
    if status_filter:
        processes = processes.filter(status=status_filter)

    search = request.GET.get('search', '')
    if search:
        processes = processes.filter(
            Q(customer__user__first_name__icontains=search) |
            Q(customer__user__last_name__icontains=search) |
            Q(customer__user__mobile__icontains=search)
        )

    paginator = Paginator(processes, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر فرآیند
    for p in page_obj:
        p.assigned_at_shamsi = get_shamsi_datetime(p.assigned_at)
        p.contact_deadline_shamsi = get_shamsi_datetime(p.contact_deadline)
        p.intro_deadline_shamsi = get_shamsi_datetime(p.intro_deadline)
        p.visit_result_deadline_shamsi = get_shamsi_datetime(p.visit_result_deadline)
        p.closed_at_shamsi = get_shamsi_datetime(p.closed_at)

    active_count = get_active_processes_count(user)
    is_available = active_count < user.max_concurrent

    contract_pending_count = CustomerProcess.objects.filter(
        expert=user,
        status=CustomerProcess.Status.CONTRACT_PENDING
    ).count()

    stats = {
        'total': processes.count(),
        'assigned': processes.filter(status=CustomerProcess.Status.ASSIGNED).count(),
        'contacted': processes.filter(status=CustomerProcess.Status.CONTACTED).count(),
        'introduced': processes.filter(status=CustomerProcess.Status.INTRODUCED).count(),
        'visit_pending': processes.filter(status=CustomerProcess.Status.VISIT_PENDING).count(),
        'visit_scheduled': processes.filter(status=CustomerProcess.Status.VISIT_SCHEDULED).count(),
        'visit_done': processes.filter(status=CustomerProcess.Status.VISIT_DONE).count(),
        'negotiation': processes.filter(status=CustomerProcess.Status.NEGOTIATION).count(),
        'contract_pending': contract_pending_count,
        'active_count': active_count,
        'max_capacity': user.max_concurrent,
        'is_available': is_available,
    }

    process_statuses = CustomerProcess.Status.choices

    context = {
        'title': 'داشبورد کارشناس',
        'processes': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'search': search,
        'process_statuses': process_statuses,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'case_management/expert_dashboard.html', context)


# ============================================================
# 📋 جزئیات فرآیند (کارشناس)
# ============================================================

@login_required
def expert_process_detail(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    process = get_object_or_404(
        CustomerProcess,
        pk=pk,
        expert=user
    )

    # ✅ اضافه کردن تاریخ شمسی به فرآیند
    process.assigned_at_shamsi = get_shamsi_datetime(process.assigned_at)
    process.contact_made_at_shamsi = get_shamsi_datetime(process.contact_made_at)
    process.introduction_completed_at_shamsi = get_shamsi_datetime(process.introduction_completed_at)
    process.contact_deadline_shamsi = get_shamsi_datetime(process.contact_deadline)
    process.intro_deadline_shamsi = get_shamsi_datetime(process.intro_deadline)
    process.visit_result_deadline_shamsi = get_shamsi_datetime(process.visit_result_deadline)
    process.closed_at_shamsi = get_shamsi_datetime(process.closed_at)
    process.created_at_shamsi = get_shamsi_datetime(process.created_at)

    contact_notes = process.notes.filter(
        note_type=ProcessNote.NoteType.CONTACT_REPORT
    ).order_by('-created_at')

    for note in contact_notes:
        note.created_at_shamsi = get_shamsi_datetime(note.created_at)

    estate_notes = process.customer.notes.all().order_by('-created_at')

    for note in estate_notes:
        note.created_at_shamsi = get_shamsi_datetime(note.created_at)

    all_matches = Match.objects.filter(
        customer=process.customer,
        match_score__gte=50
    ).select_related('property_ref').order_by('-match_score')

    pending_matches = all_matches.filter(
        introduction_status=Match.IntroductionStatus.PENDING
    )
    reported_matches = all_matches.exclude(
        introduction_status=Match.IntroductionStatus.PENDING
    ).order_by('-introduction_status', '-match_score')

    ordered_matches = list(pending_matches) + list(reported_matches)

    intro_reports = process.introduction_reports.all().order_by('-created_at')
    intro_reported_ids = list(intro_reports.values_list('property_ref_id', flat=True))

    for report in intro_reports:
        report.created_at_shamsi = get_shamsi_datetime(report.created_at)
        report.follow_up_date_shamsi = get_shamsi_datetime(report.follow_up_date)

    follow_up_alerts = intro_reports.filter(
        follow_up_date__lte=timezone.now(),
        result__in=['pending', 'fail']
    ).select_related('property_ref').order_by('follow_up_date')

    total_matches = all_matches.count()
    reported_count = intro_reports.count()
    pending_intro = total_matches - reported_count
    intro_complete = (pending_intro <= 0)

    contact_deadline_passed = process.is_contact_deadline_passed
    intro_deadline_passed = process.is_intro_deadline_passed
    last_visit = process.visits.filter(status=Visit.Status.DONE).first()

    visits = process.visits.all().order_by('-created_at')
    for visit in visits:
        visit.scheduled_time_shamsi = get_shamsi_datetime(visit.scheduled_time)
        visit.confirmed_at_shamsi = get_shamsi_datetime(visit.confirmed_at)
        visit.done_at_shamsi = get_shamsi_datetime(visit.done_at)
        visit.created_at_shamsi = get_shamsi_datetime(visit.created_at)
        visit.meeting_held_at_shamsi = get_shamsi_datetime(visit.meeting_held_at)

    logs = process.logs.all().order_by('-created_at')[:50]
    for log in logs:
        log.created_at_shamsi = get_shamsi_datetime(log.created_at)

    supervisors = User.objects.filter(
        is_active=True,
        user_roles__role__name='supervisor',
        user_roles__is_active=True
    ).distinct().order_by('first_name', 'last_name')

    managers = User.objects.filter(
        user_roles__role__name='meetingchair',
        user_roles__is_active=True,
        is_active=True
    ).distinct()

    context = {
        'title': f'جزئیات فرآیند - {process.customer.full_name}',
        'process': process,
        'is_closed': is_process_closed(process),
        'is_in_contract': is_process_in_contract(process),
        'is_in_accounting': is_process_in_accounting(process),
        'contact_notes': contact_notes,
        'estate_notes': estate_notes,
        'visits': visits,
        'all_matches': ordered_matches,
        'pending_matches': pending_matches,
        'reported_matches': reported_matches,
        'intro_reports': intro_reports,
        'follow_up_alerts': follow_up_alerts,
        'logs': logs,
        'total_matches': total_matches,
        'reported_count': reported_count,
        'pending_intro': pending_intro,
        'intro_complete': intro_complete,
        'intro_reported_ids': intro_reported_ids,
        'contact_deadline_passed': contact_deadline_passed,
        'intro_deadline_passed': intro_deadline_passed,
        'last_visit': last_visit,
        'supervisors': supervisors,
        'this_user': user,
        'managers': managers,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'case_management/expert_process_detail.html', context)


# ============================================================
# 📞 اقدامات کارشناس (با بررسی بسته بودن)
# ============================================================

@login_required
def expert_make_contact(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    process = get_object_or_404(
        CustomerProcess,
        pk=pk,
        expert=user
    )

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    if process.status not in [CustomerProcess.Status.ASSIGNED, CustomerProcess.Status.CONTACT_PENDING,
                              CustomerProcess.Status.CONTACTED]:
        return JsonResponse({'error': 'وضعیت فرآیند اجازه ثبت تماس را نمی‌دهد'}, status=400)

    report_text = request.POST.get('report_text', '').strip()
    target = request.POST.get('target', 'public')

    if not report_text:
        return JsonResponse({'error': 'لطفاً گزارش تماس را وارد کنید'}, status=400)

    try:
        with transaction.atomic():
            ProcessNote.objects.create(
                process=process,
                note_type=ProcessNote.NoteType.CONTACT_REPORT,
                target=target,
                content=report_text,
                created_by=user
            )

            if process.status in [CustomerProcess.Status.ASSIGNED, CustomerProcess.Status.CONTACT_PENDING]:
                process.status = CustomerProcess.Status.CONTACTED
                process.contact_made_at = timezone.now()
                process.set_intro_deadline()
                process.save()

                ProcessLog.objects.create(
                    process=process,
                    action=ProcessLog.ActionType.CONTACT_MADE,
                    description=f"تماس اولیه با مشتری توسط کارشناس {user.get_full_name()} ثبت شد",
                    performed_by=user,
                    new_value=CustomerProcess.Status.CONTACTED
                )
            else:
                ProcessLog.objects.create(
                    process=process,
                    action=ProcessLog.ActionType.CONTACT_MADE,
                    description=f"تماس مجدد با مشتری توسط کارشناس {user.get_full_name()} ثبت شد",
                    performed_by=user,
                    new_value=process.status
                )

            target_display = {
                'public': 'عمومی',
                'supervisor': 'سرپرست',
                'callcenter': 'کال سنتر'
            }.get(target, 'عمومی')

            return JsonResponse({
                'success': True,
                'message': f'تماس با موفقیت ثبت شد (مخاطب: {target_display})',
                'new_status': process.get_status_display(),
                'intro_deadline': get_shamsi_datetime(process.intro_deadline) if process.intro_deadline else None,
                'is_first_contact': process.contact_made_at is not None
            })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def expert_add_process_note(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    process = get_object_or_404(
        CustomerProcess,
        pk=pk,
        expert=user
    )

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    note_type = request.POST.get('note_type', 'general')
    content = request.POST.get('content', '').strip()

    if not content:
        return JsonResponse({'error': 'متن نت نمی‌تواند خالی باشد'}, status=400)

    try:
        note = ProcessNote.objects.create(
            process=process,
            note_type=note_type,
            content=content,
            created_by=user
        )

        return JsonResponse({
            'success': True,
            'message': 'نت با موفقیت ثبت شد',
            'note_id': str(note.id),
            'created_at': get_shamsi_datetime(note.created_at)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def expert_add_intro_report(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    process = get_object_or_404(
        CustomerProcess,
        pk=pk,
        expert=user
    )

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    property_id = request.POST.get('property_id')
    result = request.POST.get('result')
    expert_note = request.POST.get('expert_note', '')
    follow_up_date_str = request.POST.get('follow_up_date', '')

    if not property_id or not result:
        return JsonResponse({'error': 'لطفاً فایل و نتیجه را انتخاب کنید'}, status=400)

    try:
        with transaction.atomic():
            property_obj = Property.objects.get(id=property_id, is_active=True)

            if property_obj.status in [Property.Status.IN_MEETING, Property.Status.CONTRACT]:
                return JsonResponse({'error': 'این فایل در حال حاضر در جلسه یا قرارداد است و قابل معرفی نیست.'},
                                    status=400)

            follow_up_date = None
            if follow_up_date_str:
                try:
                    follow_up_date = jalali_to_gregorian(follow_up_date_str)
                except ValueError as e:
                    return JsonResponse({'error': str(e)}, status=400)

            report = IntroductionReport.objects.create(
                process=process,
                property_ref=property_obj,
                result=result,
                expert_note=expert_note,
                follow_up_date=follow_up_date
            )

            match = Match.objects.filter(
                customer=process.customer,
                property_ref=property_obj
            ).first()

            if match:
                if result == 'success':
                    match.introduction_status = Match.IntroductionStatus.SUCCESS
                elif result == 'fail':
                    match.introduction_status = Match.IntroductionStatus.FAIL
                elif result == 'pending':
                    match.introduction_status = Match.IntroductionStatus.PENDING
                match.save(update_fields=['introduction_status'])

            total_matches = Match.objects.filter(
                customer=process.customer,
                match_score__gte=50
            ).count()
            reported_count = process.introduction_reports.count()

            if reported_count >= total_matches and total_matches > 0:
                process.status = CustomerProcess.Status.INTRODUCED
                process.introduction_completed_at = timezone.now()
                process.save()
                ProcessLog.objects.create(
                    process=process,
                    action=ProcessLog.ActionType.INTRO_REPORTED,
                    description=f"همه گزارش‌های معرفی ({reported_count} مورد) تکمیل شد",
                    performed_by=user,
                    new_value=CustomerProcess.Status.INTRODUCED
                )

            return JsonResponse({
                'success': True,
                'message': 'گزارش معرفی با موفقیت ثبت شد',
                'reported_count': reported_count,
                'total_matches': total_matches,
                'intro_complete': reported_count >= total_matches
            })

    except Property.DoesNotExist:
        return JsonResponse({'error': 'فایل مورد نظر یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def expert_add_estate_note(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    process = get_object_or_404(CustomerProcess, pk=pk, expert=user)

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    note_type = request.POST.get('note_type', 'general')
    priority = request.POST.get('priority', 'medium')

    if not title or not content:
        return JsonResponse({'error': 'عنوان و متن یادداشت الزامی است'}, status=400)

    try:
        note = Note.objects.create(
            customer=process.customer,
            note_type=note_type,
            priority=priority,
            title=title,
            content=content,
            created_by=user,
        )

        ProcessLog.objects.create(
            process=process,
            action=ProcessLog.ActionType.STATUS_CHANGE,
            description=f"یادداشت عمومی '{title}' توسط کارشناس ثبت شد",
            performed_by=user,
            new_value=process.status
        )

        return JsonResponse({
            'success': True,
            'message': 'یادداشت با موفقیت ثبت شد'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# 🏠 مدیریت بازدید (کارشناس) - با بررسی بسته بودن
# ============================================================

@login_required
def expert_create_visit(request, process_pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    process = get_object_or_404(
        CustomerProcess,
        pk=process_pk,
        expert=user
    )

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    property_id = request.POST.get('property_id')
    if not property_id:
        return JsonResponse({'error': 'لطفاً فایل مورد نظر را انتخاب کنید'}, status=400)

    try:
        property_obj = Property.objects.get(id=property_id, is_active=True)

        if property_obj.status in [Property.Status.IN_MEETING, Property.Status.CONTRACT]:
            return JsonResponse({'error': 'این فایل در حال حاضر در جلسه یا قرارداد است و قابل برنامه‌ریزی نیست.'},
                                status=400)

        existing = Visit.objects.filter(
            process=process,
            property_ref=property_obj
        ).exclude(
            status=Visit.Status.CANCELLED
        ).exists()

        if existing:
            return JsonResponse({'error': 'قبلاً بازدید برای این فایل ثبت شده است'}, status=400)

        with transaction.atomic():
            visit = Visit.objects.create(
                process=process,
                property_ref=property_obj,
                status=Visit.Status.REQUESTED
            )

            process.status = CustomerProcess.Status.VISIT_PENDING
            process.save()

            ProcessLog.objects.create(
                process=process,
                action=ProcessLog.ActionType.VISIT_REQUESTED,
                description=f"درخواست بازدید برای {property_obj.title} توسط کارشناس ثبت شد",
                performed_by=user,
                new_value=CustomerProcess.Status.VISIT_PENDING
            )

            return JsonResponse({
                'success': True,
                'message': 'درخواست بازدید با موفقیت ثبت شد',
                'visit_id': str(visit.id),
                'status': visit.get_status_display()
            })

    except Property.DoesNotExist:
        return JsonResponse({'error': 'فایل مورد نظر یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def expert_create_visit_direct(request, process_pk):
    user = request.user

    process = get_object_or_404(
        CustomerProcess,
        pk=process_pk,
        expert=user
    )

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    property_id = request.POST.get('property_id')
    scheduled_time_str = request.POST.get('scheduled_time')

    if not property_id:
        return JsonResponse({'error': 'لطفاً فایل را انتخاب کنید'}, status=400)

    if not scheduled_time_str:
        return JsonResponse({'error': 'لطفاً تاریخ و زمان بازدید را مشخص کنید'}, status=400)

    try:
        scheduled_time = jalali_to_gregorian(scheduled_time_str)
        if scheduled_time < timezone.now():
            return JsonResponse({'error': 'زمان بازدید باید در آینده باشد'}, status=400)

        property_obj = Property.objects.get(id=property_id, is_active=True)

        if property_obj.status in [Property.Status.IN_MEETING, Property.Status.CONTRACT]:
            return JsonResponse({'error': 'این فایل در حال حاضر در جلسه یا قرارداد است و قابل برنامه‌ریزی نیست.'},
                                status=400)

        with transaction.atomic():
            existing = Visit.objects.filter(
                process=process,
                property_ref=property_obj
            ).exclude(status=Visit.Status.CANCELLED).exists()

            visit = Visit.objects.create(
                process=process,
                property_ref=property_obj,
                status=Visit.Status.SCHEDULED,
                scheduled_time=scheduled_time
            )

            process.status = CustomerProcess.Status.VISIT_SCHEDULED
            process.save()

            ProcessLog.objects.create(
                process=process,
                action=ProcessLog.ActionType.VISIT_SCHEDULED,
                description=f"زمان بازدید {property_obj.title} برای {gregorian_to_jalali(scheduled_time)} برنامه‌ریزی شد",
                performed_by=user,
                new_value=CustomerProcess.Status.VISIT_SCHEDULED
            )

            return JsonResponse({
                'success': True,
                'message': 'بازدید با موفقیت ثبت شد',
                'visit_id': str(visit.id)
            })

    except Property.DoesNotExist:
        return JsonResponse({'error': 'فایل مورد نظر یافت نشد'}, status=404)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def expert_schedule_visit(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    visit = get_object_or_404(
        Visit,
        pk=pk,
        process__expert=user
    )

    if is_process_closed(visit.process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    scheduled_time_str = request.POST.get('scheduled_time')
    if not scheduled_time_str:
        return JsonResponse({'error': 'لطفاً زمان بازدید را مشخص کنید'}, status=400)

    try:
        scheduled_time = jalali_to_gregorian(scheduled_time_str)
        if scheduled_time < timezone.now():
            return JsonResponse({'error': 'زمان بازدید باید در آینده باشد'}, status=400)

        with transaction.atomic():
            visit.scheduled_time = scheduled_time
            visit.status = Visit.Status.SCHEDULED
            visit.save()

            visit.process.status = CustomerProcess.Status.VISIT_SCHEDULED
            visit.process.save()

            ProcessLog.objects.create(
                process=visit.process,
                action=ProcessLog.ActionType.VISIT_SCHEDULED,
                description=f"زمان بازدید {visit.property_ref.title} برای {gregorian_to_jalali(scheduled_time)} برنامه‌ریزی شد",
                performed_by=user,
                new_value=CustomerProcess.Status.VISIT_SCHEDULED
            )

            return JsonResponse({
                'success': True,
                'message': 'زمان بازدید با موفقیت ثبت شد',
                'scheduled_time': gregorian_to_jalali(scheduled_time)
            })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def expert_record_visit_result(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    visit = get_object_or_404(
        Visit,
        pk=pk,
        process__expert=user
    )

    if is_process_closed(visit.process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    visit_result = request.POST.get('visit_result')
    negotiation_requested = request.POST.get('negotiation_requested') == 'true'
    negotiation_manager_id = request.POST.get('negotiation_manager')

    if not visit_result:
        return JsonResponse({'error': 'لطفاً نتیجه بازدید را وارد کنید'}, status=400)

    try:
        with transaction.atomic():
            visit.visit_result = visit_result
            visit.negotiation_requested = negotiation_requested
            visit.status = Visit.Status.DONE
            visit.done_at = timezone.now()

            if negotiation_manager_id:
                try:
                    manager = User.objects.get(id=negotiation_manager_id)
                    visit.negotiation_manager = manager
                except User.DoesNotExist:
                    pass

            visit.save()
            visit.process.set_visit_result_deadline(visit.done_at)

            if negotiation_requested:
                visit.process.status = CustomerProcess.Status.NEGOTIATION
                ProcessLog.objects.create(
                    process=visit.process,
                    action=ProcessLog.ActionType.NEGOTIATION_REQUESTED,
                    description=f"پس از بازدید {visit.property_ref.title}، درخواست جلسه مذاکره ثبت شد",
                    performed_by=user,
                    new_value=CustomerProcess.Status.NEGOTIATION
                )
            else:
                visit.process.status = CustomerProcess.Status.VISIT_DONE

            visit.process.save()

            return JsonResponse({
                'success': True,
                'message': 'نتیجه بازدید با موفقیت ثبت شد',
                'status': visit.process.get_status_display(),
                'negotiation_requested': negotiation_requested
            })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# 🔄 محاسبه تطابق (کارشناس)
# ============================================================

@login_required
def calculate_matches_for_customer(request, customer_id):
    user = request.user

    customer = get_object_or_404(Customer, id=customer_id)

    if customer.status in [Customer.Status.IN_MEETING, Customer.Status.CONTRACT]:
        messages.warning(request, 'این مشتری در حال حاضر در جلسه یا قرارداد است و تطابق محاسبه نمی‌شود.')
        return redirect('case_management:expert_dashboard')

    if not CustomerProcess.objects.filter(customer=customer, expert=user).exists():
        messages.error(request, 'شما دسترسی به این مشتری ندارید.')
        return redirect('case_management:expert_dashboard')

    result = MatchManager.calculate_and_save_matches_for_customer(
        customer=customer,
        min_score=50,
        created_by=user,
        remove_low=True
    )

    messages.success(
        request,
        f'تطابق‌های مشتری {customer.full_name} به‌روزرسانی شد. '
        f'({result["saved"]} مورد جدید، {result["updated"]} مورد به‌روزرسانی، {result["deleted"]} مورد حذف)'
    )
    return redirect(request.META.get('HTTP_REFERER', 'case_management:expert_dashboard'))


@login_required
def calculate_matches_for_all_expert_customers(request):
    user = request.user

    customers = Customer.objects.filter(
        processes__expert=user,
        is_active=True,
        status__in=[Customer.Status.CONFIRMED, Customer.Status.NEW]
    ).distinct()

    total_saved = 0
    total_updated = 0
    total_deleted = 0

    for customer in customers:
        result = MatchManager.calculate_and_save_matches_for_customer(
            customer=customer,
            min_score=50,
            created_by=user,
            remove_low=True
        )
        total_saved += result['saved']
        total_updated += result['updated']
        total_deleted += result['deleted']

    messages.success(
        request,
        f'تطابق‌های همه مشتریان فعال شما به‌روزرسانی شد. '
        f'{total_saved} مورد جدید، {total_updated} مورد به‌روزرسانی، {total_deleted} مورد حذف.'
    )
    return redirect('case_management:expert_dashboard')


# ============================================================
# 🎯 کال سنتر - لیست نت‌ها
# ============================================================

@login_required
def callcenter_notes_list(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "show_expert_note"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    notes = ProcessNote.objects.filter(
        target='callcenter',
        is_confirmed=False
    ).select_related(
        'process',
        'process__customer',
        'process__customer__user',
        'created_by'
    ).order_by('-created_at')

    search = request.GET.get('search', '')
    if search:
        notes = notes.filter(
            Q(process__customer__user__first_name__icontains=search) |
            Q(process__customer__user__last_name__icontains=search) |
            Q(process__customer__user__mobile__icontains=search)
        )

    paginator = Paginator(notes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر نت
    for note in page_obj:
        note.created_at_shamsi = get_shamsi_datetime(note.created_at)

    stats = {
        'total': notes.count(),
        'contact_reports': notes.filter(note_type='contact_report').count(),
        'important': notes.filter(note_type='important').count(),
        'general': notes.filter(note_type='general').count(),
    }

    context = {
        'title': 'نت‌های ارسال‌شده به کال سنتر',
        'notes': page_obj,
        'stats': stats,
        'search': search,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }

    if is_ajax(request):
        if request.GET.get('i') == "confirmed_note":
            noteId = request.GET.get('noteId')
            this_note = ProcessNote.objects.get(pk=noteId)
            this_note.is_confirmed = True
            this_note.confirmed_at = timezone.now()
            this_note.confirmed_by = user
            this_note.save()
            data = {
                "msg": "نت با موفقیت تایید گردید",
            }
            return JsonResponse(data)

    return render(request, 'case_management/callcenter_notes_list.html', context)


# ============================================================
# 🚨 API اخطارها
# ============================================================

@login_required
def unread_alerts_count(request):
    user = request.user

    count = SupervisorAlert.objects.filter(
        process__supervisor=user,
        is_read=False
    ).count()

    return JsonResponse({
        'success': True,
        'count': count
    })


@login_required
def mark_alert_read(request, pk):
    user = request.user

    alert = get_object_or_404(
        SupervisorAlert,
        pk=pk,
        process__supervisor=user
    )

    alert.is_read = True
    alert.read_at = timezone.now()
    alert.save()

    return JsonResponse({
        'success': True,
        'message': 'اخطار با موفقیت خوانده شد'
    })


# ============================================================
# 📊 داشبورد مدیر جلسه
# ============================================================

@login_required
def manager_dashboard(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "manager_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    now = timezone.now()

    meetings = Visit.objects.filter(
        negotiation_manager=user
    ).select_related(
        'process', 'process__customer', 'process__customer__user',
        'process__expert', 'property_ref'
    ).order_by('scheduled_time')

    upcoming_meetings = meetings.filter(
        scheduled_time__gte=now,
        status__in=[Visit.Status.SCHEDULED, Visit.Status.CONFIRMED]
    )

    held_meetings = meetings.filter(
        meeting_status='held',
        status=Visit.Status.DONE
    ).order_by('-meeting_held_at')

    pending_result_meetings = meetings.filter(
        status=Visit.Status.DONE,
        meeting_status='pending',
        meeting_result__isnull=True
    )

    # ✅ اضافه کردن تاریخ شمسی به جلسات
    for m in upcoming_meetings:
        m.scheduled_time_shamsi = get_shamsi_datetime(m.scheduled_time)
    for m in held_meetings:
        m.scheduled_time_shamsi = get_shamsi_datetime(m.scheduled_time)
        m.meeting_held_at_shamsi = get_shamsi_datetime(m.meeting_held_at)
    for m in pending_result_meetings:
        m.scheduled_time_shamsi = get_shamsi_datetime(m.scheduled_time)
        m.done_at_shamsi = get_shamsi_datetime(m.done_at)

    context = {
        'title': 'داشبورد مدیر جلسات',
        'upcoming_meetings': upcoming_meetings,
        'held_meetings': held_meetings,
        'pending_result_meetings': pending_result_meetings,
        'total_meetings': meetings.count(),
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'case_management/manager_dashboard.html', context)


# ============================================================
# 📝 ثبت نتیجه جلسه توسط مدیر جلسه
# ============================================================

@login_required
def manager_record_meeting_result(request, visit_id):
    if not is_ajax(request):
        return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'})

    try:
        visit = Visit.objects.get(pk=visit_id, negotiation_manager=request.user)

        meeting_result = request.POST.get('meeting_result')
        meeting_note = request.POST.get('meeting_note', '')
        meeting_status = request.POST.get('meeting_status', 'held')
        send_to_contract = request.POST.get('send_to_contract') == 'on'

        if not meeting_result:
            return JsonResponse({'success': False, 'error': 'لطفاً نتیجه جلسه را وارد کنید'})

        visit.meeting_result = meeting_result
        visit.meeting_note = meeting_note
        visit.meeting_status = meeting_status
        visit.meeting_held_at = timezone.now()
        visit.meeting_result_confirmed = True
        visit.save()

        process = visit.process

        if send_to_contract:
            process.status = CustomerProcess.Status.CONTRACT_PENDING
            process.final_result = f"جلسه مذاکره برگزار شد. نتیجه: {meeting_result} - ارسال به واحد قرارداد"
            process.save()

            process.customer.status = Customer.Status.IN_MEETING
            process.customer.save(update_fields=['status'])

            if visit.property_ref:
                visit.property_ref.status = Property.Status.IN_MEETING
                visit.property_ref.save(update_fields=['status'])

            ProcessLog.objects.create(
                process=process,
                action=ProcessLog.ActionType.NEGOTIATION_REQUESTED,
                description=f"نتیجه جلسه توسط مدیر جلسه {request.user.get_full_name()} ثبت شد و به واحد قرارداد ارسال گردید",
                performed_by=request.user
            )

            return JsonResponse({
                'success': True,
                'message': '✅ نتیجه جلسه ثبت شد و به واحد قرارداد ارسال گردید. مشتری و فایل در وضعیت در انتظار قرارداد قرار گرفتند.',
                'status': 'contract_pending'
            })

        else:
            process.status = CustomerProcess.Status.NEGOTIATION
            process.final_result = f"جلسه مذاکره برگزار شد. نتیجه: {meeting_result} - نیاز به پیگیری مجدد"
            process.save()

            ProcessLog.objects.create(
                process=process,
                action=ProcessLog.ActionType.NEGOTIATION_REQUESTED,
                description=f"نتیجه جلسه توسط مدیر جلسه {request.user.get_full_name()} ثبت شد (نیاز به پیگیری مجدد)",
                performed_by=request.user
            )

            return JsonResponse({
                'success': True,
                'message': '⚠️ نتیجه جلسه ثبت شد. برای ادامه، کارشناس یا سرپرست باید اقدام بعدی را انجام دهد.',
                'status': 'negotiation'
            })

    except Visit.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'جلسه یافت نشد'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================================
# 📋 مشاهده جزئیات جلسه (مدیر جلسه و دیگر نقش‌ها)
# ============================================================

@login_required
def manager_visit_detail(request, visit_id):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )

    visit = get_object_or_404(Visit, id=visit_id)

    has_access = False

    if user.is_superuser:
        has_access = True
    elif visit.negotiation_manager == user:
        has_access = True
    elif user.user_roles.filter(role__name='contract_officer', is_active=True).exists():
        has_access = True
    elif user.user_roles.filter(role__name='accountant', is_active=True).exists():
        has_access = True
    elif user.user_roles.filter(role__name='admin', is_active=True).exists():
        has_access = True

    if not has_access:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    process = visit.process
    customer = process.customer
    property_obj = visit.property_ref

    # ✅ اضافه کردن تاریخ شمسی به فرآیند
    process.assigned_at_shamsi = get_shamsi_datetime(process.assigned_at)
    process.contact_made_at_shamsi = get_shamsi_datetime(process.contact_made_at)
    process.introduction_completed_at_shamsi = get_shamsi_datetime(process.introduction_completed_at)
    process.contact_deadline_shamsi = get_shamsi_datetime(process.contact_deadline)
    process.intro_deadline_shamsi = get_shamsi_datetime(process.intro_deadline)
    process.closed_at_shamsi = get_shamsi_datetime(process.closed_at)
    process.created_at_shamsi = get_shamsi_datetime(process.created_at)

    # ✅ اضافه کردن تاریخ شمسی به بازدید
    visit.scheduled_time_shamsi = get_shamsi_datetime(visit.scheduled_time)
    visit.confirmed_at_shamsi = get_shamsi_datetime(visit.confirmed_at)
    visit.done_at_shamsi = get_shamsi_datetime(visit.done_at)
    visit.meeting_held_at_shamsi = get_shamsi_datetime(visit.meeting_held_at)
    visit.created_at_shamsi = get_shamsi_datetime(visit.created_at)

    contact_notes = process.notes.filter(
        note_type=ProcessNote.NoteType.CONTACT_REPORT
    ).order_by('-created_at')

    for note in contact_notes:
        note.created_at_shamsi = get_shamsi_datetime(note.created_at)

    estate_notes = customer.notes.all().order_by('-created_at')

    for note in estate_notes:
        note.created_at_shamsi = get_shamsi_datetime(note.created_at)

    all_matches = Match.objects.filter(
        customer=customer,
        match_score__gte=50
    ).select_related('property_ref').order_by('-match_score')

    pending_matches = all_matches.filter(
        introduction_status=Match.IntroductionStatus.PENDING
    )
    reported_matches = all_matches.exclude(
        introduction_status=Match.IntroductionStatus.PENDING
    ).order_by('-introduction_status', '-match_score')

    ordered_matches = list(pending_matches) + list(reported_matches)

    intro_reports = process.introduction_reports.all().order_by('-created_at')
    intro_reported_ids = list(intro_reports.values_list('property_ref_id', flat=True))

    for report in intro_reports:
        report.created_at_shamsi = get_shamsi_datetime(report.created_at)
        report.follow_up_date_shamsi = get_shamsi_datetime(report.follow_up_date)

    follow_up_alerts = intro_reports.filter(
        follow_up_date__lte=timezone.now(),
        result__in=['pending', 'fail']
    ).select_related('property_ref').order_by('follow_up_date')

    total_matches = all_matches.count()
    reported_count = intro_reports.count()
    pending_intro = total_matches - reported_count
    intro_complete = (pending_intro <= 0)

    other_visits = process.visits.exclude(id=visit.id).order_by('-created_at')

    for v in other_visits:
        v.scheduled_time_shamsi = get_shamsi_datetime(v.scheduled_time)
        v.done_at_shamsi = get_shamsi_datetime(v.done_at)
        v.created_at_shamsi = get_shamsi_datetime(v.created_at)

    logs = process.logs.all().order_by('-created_at')[:50]
    for log in logs:
        log.created_at_shamsi = get_shamsi_datetime(log.created_at)

    alerts = process.alerts.all().order_by('-created_at')
    for alert in alerts:
        alert.created_at_shamsi = get_shamsi_datetime(alert.created_at)

    context = {
        'title': f'جزئیات جلسه - {property_obj.title}',
        'visit': visit,
        'process': process,
        'customer': customer,
        'property': property_obj,
        'contact_notes': contact_notes,
        'estate_notes': estate_notes,
        'all_matches': ordered_matches,
        'pending_matches': pending_matches,
        'reported_matches': reported_matches,
        'intro_reports': intro_reports,
        'follow_up_alerts': follow_up_alerts,
        'logs': logs,
        'alerts': alerts,
        'other_visits': other_visits,
        'total_matches': total_matches,
        'reported_count': reported_count,
        'pending_intro': pending_intro,
        'intro_complete': intro_complete,
        'intro_reported_ids': intro_reported_ids,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'case_management/manager_visit_detail.html', context)


# ============================================================
# 📝 ثبت تبدیل به قرارداد یا کنسل کردن فرآیند (کارشناس)
# ============================================================

@login_required
def expert_close_process(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )
    if not permission:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)

    process = get_object_or_404(
        CustomerProcess,
        pk=pk,
        expert=user
    )

    if is_process_closed(process):
        return JsonResponse({'error': 'این فرآیند قبلاً بسته شده است و قابل ویرایش نیست.'}, status=403)

    if process.status == CustomerProcess.Status.CONTRACT_PENDING:
        messages.warning(request, 'این فرآیند در مرحله‌ی تنظیم قرارداد است. لطفاً ابتدا توسط واحد قرارداد تکمیل شود.')
        return redirect('case_management:expert_process_detail', pk=process.id)

    if request.method != 'POST':
        return JsonResponse({'error': 'روش نامعتبر'}, status=405)

    action = request.POST.get('action')
    close_reason = request.POST.get('close_reason')
    close_note = request.POST.get('close_note', '').strip()

    if not action:
        return JsonResponse({'error': 'لطفاً نوع اقدام را انتخاب کنید'}, status=400)

    try:
        with transaction.atomic():
            if action == 'convert':
                process.status = CustomerProcess.Status.CONVERTED
                process.is_successful = True
                process.final_result = f"تبدیل به قرارداد شد. {close_note}"
                ProcessLog.objects.create(
                    process=process,
                    action=ProcessLog.ActionType.PROCESS_CLOSED,
                    description=f"فرآیند توسط کارشناس {user.get_full_name()} به قرارداد تبدیل شد",
                    performed_by=user,
                    new_value=CustomerProcess.Status.CONVERTED
                )
            elif action == 'cancel':
                process.status = CustomerProcess.Status.CLOSED_FAIL
                process.is_successful = False
                process.final_result = f"کنسل شد. دلیل: {dict(CustomerProcess.CloseReason.choices).get(close_reason, 'سایر')} - {close_note}"
                ProcessLog.objects.create(
                    process=process,
                    action=ProcessLog.ActionType.PROCESS_CLOSED,
                    description=f"فرآیند توسط کارشناس {user.get_full_name()} کنسل شد",
                    performed_by=user,
                    new_value=CustomerProcess.Status.CLOSED_FAIL
                )
            else:
                return JsonResponse({'error': 'اقدام نامعتبر'}, status=400)

            process.close_reason = close_reason
            process.close_note = close_note
            process.closed_by = user
            process.closed_at = timezone.now()
            process.save()

            return JsonResponse({
                'success': True,
                'message': 'عملیات با موفقیت ثبت شد',
                'new_status': process.get_status_display()
            })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# 📜 تاریخچه فرآیندهای بسته‌شده (کارشناس)
# ============================================================

@login_required
def expert_archived_processes(request):
    """نمایش فرآیندهای بسته‌شده برای کارشناس"""
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "expert_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    base_archived = CustomerProcess.objects.filter(
        expert=user,
        status__in=[
            CustomerProcess.Status.CLOSED_SUCCESS,
            CustomerProcess.Status.CLOSED_FAIL,
            CustomerProcess.Status.CANCELLED,
            CustomerProcess.Status.CONVERTED,
            CustomerProcess.Status.SENT_TO_ACCOUNTING,
        ]
    )

    stats = {
        'total': base_archived.count(),
        'success': base_archived.filter(status=CustomerProcess.Status.CLOSED_SUCCESS).count(),
        'fail': base_archived.filter(status=CustomerProcess.Status.CLOSED_FAIL).count(),
        'cancelled': base_archived.filter(status=CustomerProcess.Status.CANCELLED).count(),
        'converted': base_archived.filter(status=CustomerProcess.Status.CONVERTED).count(),
        'sent_to_accounting': base_archived.filter(status=CustomerProcess.Status.SENT_TO_ACCOUNTING).count(),
    }

    archived_processes = base_archived.select_related(
        'customer', 'customer__user', 'supervisor'
    ).prefetch_related(
        'visits', 'introduction_reports', 'contract'
    ).order_by('-closed_at')

    search = request.GET.get('search', '').strip()
    if search:
        archived_processes = archived_processes.filter(
            Q(customer__user__first_name__icontains=search) |
            Q(customer__user__last_name__icontains=search) |
            Q(customer__user__mobile__icontains=search)
        )

    status_filter = request.GET.get('status', '').strip()
    valid_statuses = ['closed_success', 'closed_fail', 'cancelled', 'converted', 'sent_to_accounting']
    if status_filter and status_filter in valid_statuses:
        archived_processes = archived_processes.filter(status=status_filter)
    elif status_filter:
        messages.warning(request, 'وضعیت انتخاب‌شده نامعتبر است. لطفاً یکی از وضعیت‌های بسته‌شده را انتخاب کنید.')

    paginator = Paginator(archived_processes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر فرآیند
    for p in page_obj:
        p.assigned_at_shamsi = get_shamsi_datetime(p.assigned_at)
        p.closed_at_shamsi = get_shamsi_datetime(p.closed_at)
        p.contact_made_at_shamsi = get_shamsi_datetime(p.contact_made_at)
        p.contact_deadline_shamsi = get_shamsi_datetime(p.contact_deadline)
        p.introduction_completed_at_shamsi = get_shamsi_datetime(p.introduction_completed_at)

    process_statuses = CustomerProcess.Status.choices

    context = {
        'title': 'تاریخچه فرآیندهای بسته‌شده',
        'processes': page_obj,
        'stats': stats,
        'search': search,
        'status_filter': status_filter,
        'process_statuses': process_statuses,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'case_management/expert_archived_processes.html', context)


# ============================================================
# 📜 تاریخچه فرآیندهای بسته‌شده (سرپرست)
# ============================================================

@login_required
def supervisor_archived_processes(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "supervisor_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    archived_processes = CustomerProcess.objects.filter(
        supervisor=user,
        status__in=[
            CustomerProcess.Status.CLOSED_SUCCESS,
            CustomerProcess.Status.CLOSED_FAIL,
            CustomerProcess.Status.CANCELLED,
            CustomerProcess.Status.CONVERTED,
            CustomerProcess.Status.SENT_TO_ACCOUNTING,
        ]
    ).select_related(
        'customer', 'customer__user', 'expert', 'supervisor'
    ).prefetch_related(
        'visits', 'introduction_reports', 'contract'
    ).order_by('-closed_at')

    search = request.GET.get('search', '')
    if search:
        archived_processes = archived_processes.filter(
            Q(customer__user__first_name__icontains=search) |
            Q(customer__user__last_name__icontains=search) |
            Q(customer__user__mobile__icontains=search) |
            Q(expert__first_name__icontains=search) |
            Q(expert__last_name__icontains=search)
        )

    status_filter = request.GET.get('status', '')
    if status_filter:
        archived_processes = archived_processes.filter(status=status_filter)

    expert_filter = request.GET.get('expert', '')
    if expert_filter:
        archived_processes = archived_processes.filter(expert_id=expert_filter)

    paginator = Paginator(archived_processes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ اضافه کردن تاریخ شمسی به هر فرآیند
    for p in page_obj:
        p.assigned_at_shamsi = get_shamsi_datetime(p.assigned_at)
        p.closed_at_shamsi = get_shamsi_datetime(p.closed_at)
        p.contact_made_at_shamsi = get_shamsi_datetime(p.contact_made_at)
        p.introduction_completed_at_shamsi = get_shamsi_datetime(p.introduction_completed_at)

    experts = User.objects.filter(
        referral=user,
        is_active=True,
        user_roles__role__name='expert',
        user_roles__is_active=True
    ).distinct().order_by('first_name', 'last_name')

    stats = {
        'total': archived_processes.count(),
        'success': archived_processes.filter(status=CustomerProcess.Status.CLOSED_SUCCESS).count(),
        'fail': archived_processes.filter(status=CustomerProcess.Status.CLOSED_FAIL).count(),
        'cancelled': archived_processes.filter(status=CustomerProcess.Status.CANCELLED).count(),
        'converted': archived_processes.filter(status=CustomerProcess.Status.CONVERTED).count(),
        'sent_to_accounting': archived_processes.filter(status=CustomerProcess.Status.SENT_TO_ACCOUNTING).count(),
    }

    process_statuses = CustomerProcess.Status.choices

    context = {
        'title': 'تاریخچه فرآیندهای بسته‌شده تیم',
        'processes': page_obj,
        'stats': stats,
        'search': search,
        'status_filter': status_filter,
        'expert_filter': expert_filter,
        'experts': experts,
        'process_statuses': process_statuses,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'case_management/supervisor_archived_processes.html', context)