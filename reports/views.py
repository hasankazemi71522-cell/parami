# reports/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.db.models import Count, Q, Avg, Sum, F, Max, Min
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse
from form_flow.models import FormInstance, FormFieldValue, InstanceField
from dynamicform.models import FormTemplate, FormInput
from account.models import User, UserRole, Role

import json
import xlsxwriter
from io import BytesIO
from collections import defaultdict

from myclass.mydef import views_permissions


# ==================== ۱. داشبورد گزارش‌گیری ====================
@login_required
def report_dashboard(request):
    """داشبورد اصلی گزارش‌گیری"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "report_dashboard")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    total_forms = FormInstance.objects.count()
    completed_forms = FormInstance.objects.filter(status='completed').count()
    in_progress_forms = FormInstance.objects.filter(status='in_progress').count()
    overdue_forms = FormInstance.objects.filter(status='overdue').count()
    approved_forms = FormInstance.objects.filter(status='approved').count()
    rejected_forms = FormInstance.objects.filter(status='rejected').count()

    overdue_instances = FormInstance.objects.filter(
        status__in=['overdue', 'in_progress']
    ).order_by('-started_at')[:10]

    user_performance = User.objects.annotate(
        completed_count=Count('created_forms', filter=Q(created_forms__status='completed'))
    ).filter(completed_count__gt=0).order_by('-completed_count')[:10]

    context = {
        'title': 'داشبورد گزارش‌گیری',
        'total_forms': total_forms,
        'completed_forms': completed_forms,
        'in_progress_forms': in_progress_forms,
        'overdue_forms': overdue_forms,
        'approved_forms': approved_forms,
        'rejected_forms': rejected_forms,
        'overdue_instances': overdue_instances,
        'user_performance': user_performance,
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'reports/dashboard.html', context)


# ==================== ۲. آمار کلی سیستم ====================
@login_required
def statistics_report(request):
    """گزارش آمار کلی سیستم"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "statistics_report")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    total_forms = FormInstance.objects.count()
    total_templates = FormTemplate.objects.filter(is_active=True).count()
    total_users = User.objects.filter(is_active=True).count()
    total_roles = Role.objects.filter(is_active=True).count()

    status_stats = {}
    for status, label in FormInstance.STATUS_CHOICES:
        status_stats[label] = FormInstance.objects.filter(status=status).count()

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    recent_forms = FormInstance.objects.filter(created_at__gte=thirty_days_ago).count()
    daily_avg = recent_forms / 30 if recent_forms > 0 else 0

    context = {
        'title': 'آمار کلی سیستم',
        'total_forms': total_forms,
        'total_templates': total_templates,
        'total_users': total_users,
        'total_roles': total_roles,
        'status_stats': status_stats,
        'recent_forms': recent_forms,
        'daily_avg': round(daily_avg, 1),
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'reports/statistics.html', context)


# ==================== ۳. گزارش فرم‌ها ====================
@login_required
def form_report(request):
    """گزارش فرم‌ها با فیلترهای مختلف"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "form_report")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    template_filter = request.GET.get('template', '')
    user_filter = request.GET.get('user', '')

    all_forms = FormInstance.objects.all()
    total_all = all_forms.count()
    completed_all = all_forms.filter(status='completed').count()
    overdue_all = all_forms.filter(status='overdue').count()
    in_progress_all = all_forms.filter(status='in_progress').count()

    forms = FormInstance.objects.all().order_by('-started_at')

    if status_filter:
        forms = forms.filter(status=status_filter)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            forms = forms.filter(created_at__date__gte=date_from_obj)
        except:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            forms = forms.filter(created_at__date__lte=date_to_obj)
        except:
            pass

    if template_filter:
        forms = forms.filter(original_template_id=template_filter)

    if user_filter:
        forms = forms.filter(created_by_id=user_filter)

    total_count = forms.count()
    completed_count = forms.filter(status='completed').count()
    overdue_count = forms.filter(status='overdue').count()
    in_progress_count = forms.filter(status='in_progress').count()

    templates = FormTemplate.objects.filter(is_active=True)
    users = User.objects.filter(is_active=True)

    context = {
        'title': 'گزارش فرم‌ها',
        'forms': forms,
        'templates': templates,
        'users': users,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'template_filter': template_filter,
        'user_filter': user_filter,
        'total_all': total_all,
        'completed_all': completed_all,
        'overdue_all': overdue_all,
        'in_progress_all': in_progress_all,
        'total_count': total_count,
        'completed_count': completed_count,
        'overdue_count': overdue_count,
        'in_progress_count': in_progress_count,
        'status_choices': FormInstance.STATUS_CHOICES,
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'reports/form_report.html', context)


# ==================== ۴. جزئیات یک فرم ====================
@login_required
def form_detail_report(request, form_id):
    """گزارش جزئیات یک فرم خاص"""
    instance = get_object_or_404(FormInstance, id=form_id)
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "form_detail_report")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    field_values = instance.field_values.all().select_related('instance_field', 'filled_by')
    step_history = instance.step_history or []

    context = {
        'title': f'جزئیات فرم: {instance.title}',
        'instance': instance,
        'field_values': field_values,
        'step_history': step_history,
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'reports/form_detail_report.html', context)


# ==================== ۵. عملکرد کاربران ====================
@login_required
def user_performance_report(request):
    """گزارش عملکرد کاربران"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "user_performance_report")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    users_data = User.objects.filter(is_active=True).annotate(
        total_forms=Count('created_forms'),
        completed_forms=Count('created_forms', filter=Q(created_forms__status='completed')),
        approved_forms=Count('created_forms', filter=Q(created_forms__status='approved')),
        rejected_forms=Count('created_forms', filter=Q(created_forms__status='rejected')),
        overdue_forms=Count('created_forms', filter=Q(created_forms__status='overdue')),
        in_progress_forms=Count('created_forms', filter=Q(created_forms__status='in_progress')),
    ).filter(total_forms__gt=0).order_by('-total_forms')

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            users_data = users_data.filter(created_forms__created_at__date__gte=date_from_obj)
        except:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            users_data = users_data.filter(created_forms__created_at__date__lte=date_to_obj)
        except:
            pass

    for u in users_data:
        u.completion_rate = round((u.completed_forms / u.total_forms * 100), 1) if u.total_forms > 0 else 0

    top_users = users_data[:10]

    context = {
        'title': 'عملکرد کاربران',
        'users': users_data,
        'top_users': top_users,
        'date_from': date_from,
        'date_to': date_to,
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'reports/user_performance.html', context)


# ==================== ۶. پرکاربردترین فرم‌ها ====================
@login_required
def popular_forms_report(request):
    """گزارش پرکاربردترین فرم‌های نمونه"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "popular_forms_report")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    templates = FormTemplate.objects.filter(is_active=True).annotate(
        instance_count=Count('instances'),
        completed_count=Count('instances', filter=Q(instances__status='completed')),
        in_progress_count=Count('instances', filter=Q(instances__status='in_progress')),
        overdue_count=Count('instances', filter=Q(instances__status='overdue')),
    ).order_by('-instance_count')

    for template in templates:
        completed_instances = template.instances.filter(status='completed')
        if completed_instances.exists():
            total_duration = 0
            count = 0
            for instance in completed_instances:
                if instance.completed_at and instance.started_at:
                    duration = (instance.completed_at - instance.started_at).total_seconds() / 3600
                    total_duration += duration
                    count += 1
            template.avg_completion_hours = round(total_duration / count, 1) if count > 0 else 0
        else:
            template.avg_completion_hours = 0

    context = {
        'title': 'پرکاربردترین فرم‌ها',
        'templates': templates,
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'reports/popular_forms.html', context)


# ==================== ۷. گزارش تاخیرها ====================
@login_required
def overdue_report(request):
    """گزارش فرم‌های تاخیردار (کل فرم + هر فیلد)"""
    user = request.user
    now = timezone.now()
    permission, perimissin_list, perimissin_group = views_permissions(user, "overdue_report")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    def calculate_delay(deadline_date):
        """محاسبه میزان تاخیر به صورت خوانا"""
        if not deadline_date:
            return 0, "0 ساعت"
        if now <= deadline_date:
            return 0, "0 ساعت"

        delay_seconds = (now - deadline_date).total_seconds()
        delay_hours = delay_seconds / 3600

        if delay_hours < 1:
            delay_minutes = int(delay_seconds / 60)
            return delay_hours, f"{delay_minutes} دقیقه"
        elif delay_hours < 24:
            return delay_hours, f"{delay_hours:.1f} ساعت"
        else:
            delay_days = delay_hours / 24
            remaining_hours = delay_hours % 24
            if remaining_hours < 1:
                return delay_hours, f"{int(delay_days)} روز"
            else:
                return delay_hours, f"{int(delay_days)} روز و {int(remaining_hours)} ساعت"

    # ============================================================
    # 1️⃣ فرم‌های تاخیردار (کل فرم)
    # ============================================================
    all_forms = FormInstance.objects.filter(
        status__in=['overdue', 'in_progress', 'waiting']
    ).order_by('step_deadline')

    form_overdue_list = []
    field_overdue_list = []

    for form in all_forms:
        if form.deadline_hours > 0:
            deadline_date = form.started_at + timedelta(hours=form.deadline_hours)
            if now > deadline_date:
                form.deadline_date = deadline_date
                form.overdue_type = 'form'
                form.delay_hours, form.delay_display = calculate_delay(deadline_date)
                form_overdue_list.append(form)

        # ============================================================
        # 2️⃣ فیلدهای تاخیردار (هر فیلد)
        # ============================================================
        current_fields = form.get_fields_by_step(form.current_step_number)

        for field in current_fields:
            try:
                fv = FormFieldValue.objects.get(
                    form_instance=form,
                    instance_field=field
                )
                is_filled = bool(fv.value or fv.file_value or fv.image_value)
            except FormFieldValue.DoesNotExist:
                is_filled = False

            if not is_filled:
                field_deadline = None

                # ✅ اولویت ۱: مهلت اختصاصی فیلد (به ساعت)
                if field.field_deadline_hours > 0 and form.step_started_at:
                    field_deadline = form.step_started_at + timedelta(hours=field.field_deadline_hours)

                # ✅ اولویت ۲: مهلت مرحله
                elif form.step_deadline:
                    field_deadline = form.step_deadline

                # ✅ اولویت ۳: مهلت کل فرم (تقسیم بر تعداد مراحل)
                elif form.deadline_hours > 0:
                    max_step = form.get_max_step()
                    if max_step > 0:
                        hours_per_step = form.deadline_hours / max_step
                        if form.step_started_at:
                            field_deadline = form.step_started_at + timedelta(hours=hours_per_step)

                if field_deadline and now > field_deadline:
                    delay_hours, delay_display = calculate_delay(field_deadline)

                    # دریافت کاربران/نقش‌های مجاز برای این فیلد
                    assigned_users = []
                    assigned_roles = []

                    if field.access_type == 'specific_user':
                        assigned_users = field.allowed_users.all()
                    elif field.access_type == 'specific_role':
                        assigned_roles = field.allowed_roles.all()

                    field_overdue_list.append({
                        'form': form,
                        'field': field,
                        'deadline': field_deadline,
                        'delay_hours': delay_hours,
                        'delay_display': delay_display,
                        'assigned_users': assigned_users,
                        'assigned_roles': assigned_roles,
                        'step_number': field.step_number,
                        'field_title': field.field_title,
                        'form_title': form.custom_name or form.title,
                        'form_id': form.id,
                    })

    # ============================================================
    # 3️⃣ مرتب‌سازی بر اساس میزان تاخیر (بیشترین تاخیر اول)
    # ============================================================
    form_overdue_list.sort(key=lambda x: x.delay_hours, reverse=True)
    field_overdue_list.sort(key=lambda x: x['delay_hours'], reverse=True)

    # ============================================================
    # 4️⃣ آمار کلی
    # ============================================================
    total_overdue = len(form_overdue_list) + len(field_overdue_list)

    # میانگین تاخیر فرم‌ها
    avg_form_delay = 0
    if form_overdue_list:
        avg_form_delay = sum(f.delay_hours for f in form_overdue_list) / len(form_overdue_list)

    # میانگین تاخیر فیلدها
    avg_field_delay = 0
    if field_overdue_list:
        avg_field_delay = sum(f['delay_hours'] for f in field_overdue_list) / len(field_overdue_list)

    # بیشترین تاخیر
    max_form_delay = max([f.delay_hours for f in form_overdue_list]) if form_overdue_list else 0
    max_field_delay = max([f['delay_hours'] for f in field_overdue_list]) if field_overdue_list else 0

    context = {
        'title': 'گزارش تاخیرها',
        'form_overdue_list': form_overdue_list,
        'field_overdue_list': field_overdue_list,
        'total_overdue': total_overdue,
        'total_form_overdue': len(form_overdue_list),
        'total_field_overdue': len(field_overdue_list),
        'avg_form_delay': round(avg_form_delay, 1),
        'avg_field_delay': round(avg_field_delay, 1),
        'max_form_delay': max_form_delay,
        'max_field_delay': max_field_delay,
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }

    return render(request, 'reports/overdue_report.html', context)


# ==================== ۸. کاربران با بیشترین تاخیر ====================
@login_required
def top_overdue_users_report(request):
    """گزارش کاربرانی که بیشترین تاخیر را دارند"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "top_overdue_users_report")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    users_with_overdue = User.objects.annotate(
        total_forms=Count('created_forms'),
        overdue_forms=Count('created_forms', filter=Q(created_forms__status='overdue')),
        in_progress_forms=Count('created_forms', filter=Q(created_forms__status='in_progress')),
    ).filter(
        Q(overdue_forms__gt=0) | Q(in_progress_forms__gt=0)
    ).order_by('-overdue_forms')

    for u in users_with_overdue:
        u.overdue_rate = round((u.overdue_forms / u.total_forms * 100), 1) if u.total_forms > 0 else 0

    context = {
        'title': 'کاربران با بیشترین تاخیر',
        'users': users_with_overdue,
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'reports/top_overdue_users.html', context)


# ==================== ۹. فرم‌های بدون فعالیت ====================
@login_required
def inactive_forms_report(request):
    """گزارش فرم‌هایی که مدت طولانی بدون فعالیت مانده‌اند"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "inactive_forms_report")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    days = request.GET.get('days', 7)
    try:
        days = int(days)
    except:
        days = 7

    now = timezone.now()
    cutoff_date = now - timedelta(days=days)

    inactive_forms = FormInstance.objects.filter(
        status__in=['in_progress', 'waiting'],
        updated_at__lt=cutoff_date
    ).order_by('updated_at')

    context = {
        'title': f'فرم‌های بدون فعالیت (بیش از {days} روز)',
        'inactive_forms': inactive_forms,
        'days': days,
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'reports/inactive_forms.html', context)


# ==================== ۱۰. روند تکمیل ====================
@login_required
def completion_trend_report(request):
    """گزارش روند تکمیل فرم‌ها"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "completion_trend_report")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    period = request.GET.get('period', 'daily')

    now = timezone.now()
    start_date = now - timedelta(days=30)

    if period == 'daily':
        trunc_date = TruncDate('created_at')
        date_format = '%Y-%m-%d'
        label = 'روزانه'
    elif period == 'weekly':
        trunc_date = TruncWeek('created_at')
        date_format = '%Y-%W'
        label = 'هفتگی'
    else:
        trunc_date = TruncMonth('created_at')
        date_format = '%Y-%m'
        label = 'ماهانه'

    created_data = FormInstance.objects.filter(
        created_at__gte=start_date
    ).annotate(
        period=trunc_date
    ).values('period').annotate(
        count=Count('id')
    ).order_by('period')

    completed_data = FormInstance.objects.filter(
        created_at__gte=start_date,
        status='completed'
    ).annotate(
        period=trunc_date
    ).values('period').annotate(
        count=Count('id')
    ).order_by('period')

    combined_data = []
    periods = set()

    for item in created_data:
        periods.add(item['period'])
    for item in completed_data:
        periods.add(item['period'])

    for period in sorted(periods):
        created_count = next((item['count'] for item in created_data if item['period'] == period), 0)
        completed_count = next((item['count'] for item in completed_data if item['period'] == period), 0)
        combined_data.append({
            'period': period.strftime(date_format) if period else '-',
            'created': created_count,
            'completed': completed_count,
            'rate': round((completed_count / created_count * 100), 1) if created_count > 0 else 0
        })

    context = {
        'title': 'روند تکمیل فرم‌ها',
        'data': combined_data,
        'period': period,
        'period_label': label,
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'reports/completion_trend.html', context)


# ==================== ۱۱. تحلیل گردش کار ====================
@login_required
def workflow_analysis_report(request):
    """گزارش تحلیل گردش کار - بررسی تاخیر در هر مرحله"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "workflow_analysis_report")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    completed_forms = FormInstance.objects.filter(status='completed')

    step_stats = defaultdict(lambda: {
        'count': 0,
        'total_duration': 0,
        'overdue_count': 0,
        'field_count': 0
    })

    for form in completed_forms:
        step_history = form.step_history or []
        for step in step_history:
            step_num = step.get('step_number', 0)
            duration = step.get('duration_hours', 0)
            was_overdue = step.get('was_overdue', False)

            step_stats[step_num]['count'] += 1
            step_stats[step_num]['total_duration'] += duration
            if was_overdue:
                step_stats[step_num]['overdue_count'] += 1

            fields = form.fields.filter(step_number=step_num)
            step_stats[step_num]['field_count'] = fields.count()

    step_data = []
    for step_num, stats in sorted(step_stats.items()):
        avg_duration = round(stats['total_duration'] / stats['count'], 1) if stats['count'] > 0 else 0
        overdue_rate = round((stats['overdue_count'] / stats['count'] * 100), 1) if stats['count'] > 0 else 0
        step_data.append({
            'step_number': step_num,
            'count': stats['count'],
            'avg_duration': avg_duration,
            'overdue_count': stats['overdue_count'],
            'overdue_rate': overdue_rate,
            'field_count': stats['field_count'],
        })

    context = {
        'title': 'تحلیل گردش کار',
        'step_data': step_data,
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'reports/workflow_analysis.html', context)


# ==================== ۱۲. پیش‌بینی تکمیل ====================
@login_required
def completion_prediction_report(request):
    """گزارش پیش‌بینی تکمیل فرم‌ها بر اساس داده‌های گذشته"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "completion_prediction_report")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    completed_forms = FormInstance.objects.filter(status='completed')

    total_duration = 0
    count = 0
    for form in completed_forms:
        if form.completed_at and form.started_at:
            duration = (form.completed_at - form.started_at).total_seconds() / 3600
            total_duration += duration
            count += 1

    avg_completion_hours = round(total_duration / count, 1) if count > 0 else 0

    in_progress_forms = FormInstance.objects.filter(
        status__in=['in_progress', 'waiting']
    ).order_by('started_at')

    for form in in_progress_forms:
        if avg_completion_hours > 0:
            predicted_completion = form.started_at + timedelta(hours=avg_completion_hours)
            form.predicted_completion = predicted_completion
            form.is_predicted_overdue = timezone.now() > predicted_completion
        else:
            form.predicted_completion = None
            form.is_predicted_overdue = False

    context = {
        'title': 'پیش‌بینی تکمیل فرم‌ها',
        'in_progress_forms': in_progress_forms,
        'avg_completion_hours': avg_completion_hours,
        'total_forms_analyzed': count,
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'reports/completion_prediction.html', context)


# ==================== ۱۳. خروجی Excel ====================
@login_required
def export_excel(request, report_type):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "export_excel")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    """خروجی Excel از گزارش‌ها"""
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('گزارش')

    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#0d6efd',
        'font_color': 'white',
        'border': 1,
        'align': 'center'
    })

    cell_format = workbook.add_format({
        'border': 1,
        'align': 'center'
    })

    if report_type == 'forms':
        forms = FormInstance.objects.all().order_by('-started_at')
        headers = ['شناسه', 'عنوان فرم', 'وضعیت', 'مرحله فعلی', 'ایجاد شده توسط', 'تاریخ ایجاد']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        for row, form in enumerate(forms, start=1):
            worksheet.write(row, 0, form.id, cell_format)
            worksheet.write(row, 1, form.title, cell_format)
            worksheet.write(row, 2, form.get_status_display(), cell_format)
            worksheet.write(row, 3, form.current_step_number, cell_format)
            worksheet.write(row, 4, form.created_by.get_full_name() if form.created_by else '-', cell_format)
            worksheet.write(row, 5, form.created_at.strftime('%Y/%m/%d %H:%M'), cell_format)

    elif report_type == 'users':
        users = User.objects.annotate(
            total_forms=Count('created_forms'),
            completed_forms=Count('created_forms', filter=Q(created_forms__status='completed'))
        ).filter(total_forms__gt=0).order_by('-total_forms')

        headers = ['نام کاربر', 'ایمیل', 'تعداد کل فرم‌ها', 'تکمیل شده', 'درصد تکمیل']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        for row, u in enumerate(users, start=1):
            completion_rate = (u.completed_forms / u.total_forms * 100) if u.total_forms > 0 else 0
            worksheet.write(row, 0, u.get_full_name() or u.username, cell_format)
            worksheet.write(row, 1, u.email or '-', cell_format)
            worksheet.write(row, 2, u.total_forms, cell_format)
            worksheet.write(row, 3, u.completed_forms, cell_format)
            worksheet.write(row, 4, f'{completion_rate:.1f}%', cell_format)

    workbook.close()

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=report_{report_type}_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
    return response