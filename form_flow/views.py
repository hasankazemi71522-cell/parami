# form_flow/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db import models as db_models
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from myclass.mydef import views_permissions
from .models import (
    FormInstance, InstanceField, InstanceFieldOption, FormFieldValue
)
from dynamicform.models import FormTemplate, FormInput, FieldOption
from account.models import User, Role, UserRole, Permission, RolePermission

# ============ کتابخانه‌های PDF ============
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from django.conf import settings


# =========================================


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def fix_text(text):
    """تبدیل متن فارسی به شکل قابل نمایش در PDF"""
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except:
        return str(text)


# ==================== فرم‌های در دسترس ====================
@login_required
def available_forms(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "available_forms")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    templates = FormTemplate.objects.filter(is_active=True)
    available_templates = []
    for template in templates:
        if template.user_can_access(user):
            available_templates.append(template)
    context = {
        'templates': available_templates,
        'title': 'فرم‌های در دسترس',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_flow/available_forms.html', context)


# ==================== لیست فرم‌های من ====================
@login_required
def my_forms(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "my_forms")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    instances = FormInstance.objects.filter(
        db_models.Q(created_by=user)
    ).order_by('-started_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        instances = instances.filter(status=status_filter)

    for instance in instances:
        instance.total_fields = instance.fields.filter(is_active=True).count()
        instance.filled_count = instance.field_values.count()
        instance.progress = int(
            (instance.filled_count / instance.total_fields * 100)) if instance.total_fields > 0 else 0

    context = {
        'instances': instances,
        'status_filter': status_filter,
        'status_choices': FormInstance.STATUS_CHOICES,
        'title': 'فرم‌های من',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_flow/my_forms.html', context)


# ==================== وظایف من ====================
@login_required
def my_tasks(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "my_tasks")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    # ✅ اضافه کردن 'rejected_fixed' به لیست وضعیت‌ها
    all_instances = FormInstance.objects.filter(
        status__in=['in_progress', 'waiting', 'overdue', 'rejected_fixed']
    ).order_by('-started_at')

    if user.is_admin:
        instances = all_instances
    else:
        task_instances = []
        for instance in all_instances:
            current_fields = instance.get_fields_by_step(instance.current_step_number)
            has_field_in_current_step = False

            # بررسی اینکه کاربر دسترسی به فیلدهای مرحله فعلی داره
            for field in current_fields:
                if field.is_accessible_by(user):
                    try:
                        fv = FormFieldValue.objects.get(
                            form_instance=instance,
                            instance_field=field
                        )
                        if not fv.value and not fv.file_value and not fv.image_value:
                            has_field_in_current_step = True
                            break
                    except FormFieldValue.DoesNotExist:
                        has_field_in_current_step = True
                        break

            # اگر کاربر دسترسی داشت، فرم رو به لیست اضافه کن
            if has_field_in_current_step:
                task_instances.append(instance.id)

        instances = FormInstance.objects.filter(id__in=task_instances).distinct()

    instances = instances.order_by('-started_at')

    for instance in instances:
        available_fields = instance.get_available_fields(user)
        instance.available_count = len(available_fields)
        step_fields = instance.get_fields_by_step(instance.current_step_number)
        unfilled_count = 0
        for field in step_fields:
            try:
                fv = FormFieldValue.objects.get(
                    form_instance=instance,
                    instance_field=field
                )
                if not fv.value and not fv.file_value and not fv.image_value:
                    unfilled_count += 1
            except FormFieldValue.DoesNotExist:
                unfilled_count += 1
        instance.unfilled_count = unfilled_count
        instance.step_deadline_display = instance.step_deadline
        instance.can_fill_now = instance.current_step_number <= instance.get_max_step()
        instance.has_started = instance.field_values.filter(filled_by=user).exists()

    context = {
        'instances': instances,
        'title': 'وظایف من',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_flow/my_tasks.html', context)


# ==================== ایجاد کپی از فرم نمونه ====================
@login_required
def create_form_instance(request, template_id):
    template = get_object_or_404(FormTemplate, id=template_id, is_active=True)
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "create_form_instance")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')


    if not template.user_can_access(user):
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('form_flow:available_forms')

    if not template.forminput_set.exists():
        messages.error(request, 'این فرم هیچ فیلدی ندارد')
        return redirect('form_flow:available_forms')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                custom_name = request.POST.get('custom_name', '').strip()
                title = request.POST.get('title', template.title)
                description = request.POST.get('description', template.description)

                deadline_hours = request.POST.get('deadline_hours', 24)
                try:
                    deadline_hours = int(deadline_hours)
                    if deadline_hours < 0:
                        deadline_hours = 0
                except (ValueError, TypeError):
                    deadline_hours = 24

                if not custom_name:
                    custom_name = f"{template.title} - {timezone.now().strftime('%Y/%m/%d %H:%M')}"

                instance = FormInstance.objects.create(
                    original_template=template,
                    name=f"{template.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                    title=title,
                    description=description,
                    custom_name=custom_name,
                    deadline_hours=deadline_hours,  # ✅ تغییر
                    created_by=user,
                    assigned_to=user,
                    status='draft',
                    current_step_number=1
                )

                # کپی کردن فیلدها (همون کد قبلی)
                original_fields = template.forminput_set.all().order_by('step_number', 'order')
                for field in original_fields:
                    instance_field = InstanceField.objects.create(
                        form_instance=instance,
                        original_input=field,
                        field_name=field.field_name,
                        field_title=field.field_title,
                        order=field.order,
                        step_number=field.step_number,
                        is_required=field.is_required,
                        placeholder=field.placeholder,
                        help_text=field.help_text,
                        default_value=field.default_value,
                        min_length=field.min_length,
                        max_length=field.max_length,
                        min_value=field.min_value,
                        max_value=field.max_value,
                        max_file_size=field.max_file_size,
                        allowed_extensions=field.allowed_extensions,
                        access_type=field.access_type,
                        is_active=True,
                        field_deadline_hours=0
                    )

                    for role in field.allowed_roles.all():
                        instance_field.allowed_roles.add(role)
                    for user_obj in field.allowed_users.all():
                        instance_field.allowed_users.add(user_obj)
                    for option in field.field_options.all().order_by('order'):
                        InstanceFieldOption.objects.create(
                            instance_field=instance_field,
                            key=option.key,
                            value=option.value,
                            order=option.order,
                            is_active=option.is_active
                        )

                messages.success(request, f'فرم "{custom_name}" با موفقیت ایجاد شد')
                return redirect('form_flow:edit_instance_fields', instance_id=instance.id)

        except Exception as e:
            messages.error(request, f'خطا در ایجاد فرم: {str(e)}')

    context = {
        'template': template,
        'default_deadline_hours': 24,  # ✅ تغییر
        'title': f'ایجاد کپی از: {template.title}',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_flow/create_form_instance.html', context)


# ==================== ویرایش فیلدهای کپی ====================
@login_required
def edit_instance_fields(request, instance_id):
    instance = get_object_or_404(FormInstance, id=instance_id)
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "edit_instance_fields")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    if instance.created_by != user:
        messages.error(request, 'شما اجازه ویرایش این فرم را ندارید')
        return redirect('form_flow:my_forms')

    if instance.status != 'draft':
        messages.error(request, 'این فرم قبلاً شروع شده و قابل ویرایش نیست')
        return redirect('form_flow:fill_form', instance_id=instance.id)

    instance_fields = instance.fields.filter(is_active=True).order_by('step_number', 'order')
    max_step = instance.get_max_step()

    total_hours = instance.deadline_hours
    if total_hours > 0 and max_step > 0:
        hours_per_step = total_hours / max_step
    else:
        hours_per_step = 0

    step_info = {}
    for field in instance_fields:
        if field.step_number not in step_info:
            step_info[field.step_number] = {
                'count': 0,
                'fields': []
            }
        step_info[field.step_number]['count'] += 1
        step_info[field.step_number]['fields'].append(field)
        step_deadlines = instance.step_deadlines or {}
        if str(field.step_number) in step_deadlines:
            step_info[field.step_number]['deadline_hours'] = step_deadlines[str(field.step_number)]
        else:
            step_info[field.step_number]['deadline_hours'] = round(hours_per_step, 1)

    for field in instance_fields:
        step_deadlines = instance.step_deadlines or {}
        if str(field.step_number) in step_deadlines:
            field.default_deadline_hours = step_deadlines[str(field.step_number)]
        else:
            field.default_deadline_hours = round(hours_per_step, 1)

    all_users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')

    for field in instance_fields:
        if field.access_type == 'specific_user':
            field.allowed_users_list = field.allowed_users.all()
        else:
            field.allowed_users_list = []

    if request.method == 'POST':
        if 'start_form' in request.POST:
            instance.start_step(1)
            messages.success(request, 'فرم با موفقیت شروع شد!')
            return redirect('form_flow:fill_form', instance_id=instance.id)

        try:
            with transaction.atomic():
                title = request.POST.get('title')
                description = request.POST.get('description')
                if title:
                    instance.title = title
                if description is not None:
                    instance.description = description
                instance.save()

                # ============================================================
                # ذخیره مهلت زمانی هر مرحله
                # ============================================================
                step_deadlines = {}
                for step_num in step_info.keys():
                    deadline = request.POST.get(f'step_deadline_{step_num}')
                    try:
                        deadline_hours = float(deadline)
                        if deadline_hours > 0:
                            step_deadlines[str(step_num)] = deadline_hours
                    except (ValueError, TypeError):
                        pass
                instance.step_deadlines = step_deadlines
                instance.save()

                # ============================================================
                # ذخیره تغییرات فیلدها (فقط عنوان و کاربران مجاز)
                # ============================================================
                field_ids = request.POST.getlist('field_ids[]')
                field_titles = request.POST.getlist('field_title[]')

                for i, field_id in enumerate(field_ids):
                    try:
                        instance_field = InstanceField.objects.get(id=field_id, form_instance=instance)

                        # ✅ فقط عنوان فیلد قابل تغییره
                        if i < len(field_titles) and field_titles[i]:
                            instance_field.field_title = field_titles[i]

                        # ❌ is_required و is_active رو تغییر نمی‌دیم (همون از نمونه میاد)
                        # instance_field.is_required = ...  <-- حذف شد
                        # instance_field.is_active = ...   <-- حذف شد

                        instance_field.save()

                        # ============================================================
                        # ✅ ذخیره کاربران مجاز برای فیلدهای "شخص خاص"
                        # ============================================================
                        if instance_field.access_type == 'specific_user':
                            instance_field.allowed_users.clear()

                            # دریافت کاربران از select multiple
                            user_ids = request.POST.getlist(f'field_allowed_users_{field_id}')

                            if user_ids:
                                for user_id in user_ids:
                                    user_id = user_id.strip()
                                    if user_id:
                                        try:
                                            user_obj = User.objects.get(id=user_id)
                                            instance_field.allowed_users.add(user_obj)
                                        except User.DoesNotExist:
                                            pass

                    except InstanceField.DoesNotExist:
                        pass

                messages.success(request, 'تغییرات با موفقیت ذخیره شد')
                return redirect('form_flow:edit_instance_fields', instance_id=instance.id)

        except Exception as e:
            messages.error(request, f'خطا در ذخیره تغییرات: {str(e)}')

    context = {
        'instance': instance,
        'instance_fields': instance_fields,
        'step_info': step_info,
        'hours_per_step': round(hours_per_step, 1),
        'max_step': max_step,
        'title': f'ویرایش فرم: {instance.title}',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
        'all_users': all_users,
    }
    return render(request, 'form_flow/edit_instance_fields.html', context)


# ==================== پر کردن فرم ====================
@login_required
def fill_form(request, instance_id):
    instance = get_object_or_404(FormInstance, id=instance_id)
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "fill_form")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    has_access = False
    is_full_access = False

    if user.has_role('admin') or user.is_superuser:
        has_access = True
        is_full_access = True
    else:
        current_fields = instance.get_fields_by_step(instance.current_step_number)
        for field in current_fields:
            if field.is_accessible_by(user):
                has_access = True
                break

    if not has_access:
        messages.error(request, 'شما اجازه پر کردن این فرم را ندارید')
        return redirect('form_flow:my_tasks')

    step_fields = instance.get_fields_by_step(instance.current_step_number)

    available_fields = []
    readonly_fields = []

    for field in step_fields:
        if is_full_access:
            available_fields.append(field)
        else:
            if field.is_accessible_by(user):
                try:
                    fv = FormFieldValue.objects.get(
                        form_instance=instance,
                        instance_field=field
                    )
                    if fv.value or fv.file_value or fv.image_value:
                        field.is_filled = True
                        readonly_fields.append(field)
                    else:
                        available_fields.append(field)
                except FormFieldValue.DoesNotExist:
                    available_fields.append(field)
            else:
                readonly_fields.append(field)

    # ================================================================
    # دریافت مقادیر موجود برای نمایش در فرم
    # ================================================================
    existing_values = {}
    for field in available_fields + readonly_fields:
        try:
            value = FormFieldValue.objects.get(
                form_instance=instance,
                instance_field=field
            )
            if value.value:
                existing_values[field.id] = value.value
            elif value.file_value:
                existing_values[field.id] = value.file_value.url
            elif value.image_value:
                existing_values[field.id] = value.image_value.url
        except FormFieldValue.DoesNotExist:
            pass

    # ================================================================
    # پردازش POST
    # ================================================================
    if request.method == 'POST':
        # اگر دکمه "رفتن به مرحله بعد" کلیک شده
        if 'complete_step' in request.POST:
            # بررسی کنید همه فیلدهای اجباری پر شده‌اند
            all_required_filled = True
            missing_required_fields = []

            for field in step_fields:
                if field.is_required:
                    try:
                        fv = FormFieldValue.objects.get(
                            form_instance=instance,
                            instance_field=field
                        )
                        if not fv.value and not fv.file_value and not fv.image_value:
                            all_required_filled = False
                            missing_required_fields.append(field.field_title)
                    except FormFieldValue.DoesNotExist:
                        all_required_filled = False
                        missing_required_fields.append(field.field_title)

            if all_required_filled:
                instance.complete_step(instance.current_step_number, user)
                if instance.status == 'completed':
                    messages.success(request, '🎉 فرم با موفقیت تکمیل شد!')
                else:
                    messages.success(request, f'✅ مرحله {instance.current_step_number} با موفقیت تکمیل شد')
                return redirect('form_flow:my_tasks')
            else:
                missing_fields_str = '، '.join(missing_required_fields)
                messages.error(request, f'لطفاً فیلدهای اجباری زیر را تکمیل کنید: {missing_fields_str}')
                return redirect('form_flow:fill_form', instance_id=instance.id)

        try:
            with transaction.atomic():
                # ============================================================
                # پر کردن فیلدهای قابل دسترس (هر تعداد که کاربر پر کرده)
                # ============================================================
                for field in available_fields:
                    value = request.POST.get(field.field_name)
                    file_value = request.FILES.get(field.field_name)

                    # اگر فیلد خالی ارسال شده، نادیده بگیر (حتی اگه اجباری باشه)
                    # کاربر می‌تونه بعداً پر کنه
                    if (value is None or value == '') and file_value is None:
                        continue

                    field_value, created = FormFieldValue.objects.get_or_create(
                        form_instance=instance,
                        instance_field=field,
                        defaults={'filled_by': user}
                    )

                    if not created and field_value.filled_by != user:
                        messages.error(request, f'فیلد "{field.field_title}" قبلاً توسط شخص دیگری پر شده است')
                        continue

                    # ذخیره مقدار
                    if file_value:
                        if field.original_input and field.original_input.input.input_type == 'image':
                            field_value.image_value = file_value
                        else:
                            field_value.file_value = file_value
                        field_value.value = None
                    elif value is not None:
                        # حتی اگه خالی باشه، ذخیره می‌کنیم (برای فیلدهای اختیاری)
                        field_value.value = value.strip() if value else ''
                        field_value.file_value = None
                        field_value.image_value = None

                    field_value.filled_by = user
                    field_value.save()

                messages.success(request, 'تغییرات با موفقیت ذخیره شد')
                return redirect('form_flow:fill_form', instance_id=instance.id)

        except Exception as e:
            messages.error(request, f'خطا در ذخیره فرم: {str(e)}')

    # ================================================================
    # محاسبه پیشرفت
    # ================================================================
    progress = instance.get_step_progress()

    # شمارش فیلدهای پر شده (برای نمایش پیشرفت)
    filled_count = 0
    required_filled_count = 0
    required_total_count = 0

    for field in step_fields:
        if field.is_required:
            required_total_count += 1
            try:
                fv = FormFieldValue.objects.get(
                    form_instance=instance,
                    instance_field=field
                )
                if fv.value or fv.file_value or fv.image_value:
                    filled_count += 1
                    required_filled_count += 1
            except FormFieldValue.DoesNotExist:
                pass
        else:
            # فیلدهای اختیاری هم در پیشرفت کلی حساب می‌شوند
            try:
                fv = FormFieldValue.objects.get(
                    form_instance=instance,
                    instance_field=field
                )
                if fv.value or fv.file_value or fv.image_value:
                    filled_count += 1
            except FormFieldValue.DoesNotExist:
                pass

    # ================================================================
    # پیدا کردن فیلدهای اجباری که خالی هستند (برای نمایش هشدار)
    # ================================================================
    empty_required_fields = []
    for field in step_fields:
        if field.is_required:
            try:
                fv = FormFieldValue.objects.get(
                    form_instance=instance,
                    instance_field=field
                )
                if not fv.value and not fv.file_value and not fv.image_value:
                    empty_required_fields.append(field.field_title)
            except FormFieldValue.DoesNotExist:
                empty_required_fields.append(field.field_title)

    step_progress = {
        'filled': filled_count,
        'total': step_fields.count(),
        'percentage': (filled_count / step_fields.count() * 100) if step_fields.count() > 0 else 0,
        'required_filled': required_filled_count,
        'required_total': required_total_count,
        'empty_required_fields': empty_required_fields,
        'all_required_filled': len(empty_required_fields) == 0,
    }

    context = {
        'instance': instance,
        'step_fields': available_fields,
        'readonly_fields': readonly_fields,
        'existing_values': existing_values,
        'progress': progress,
        'step_progress': step_progress,
        'empty_required_fields': empty_required_fields,
        'title': f'پر کردن: {instance.title}',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_flow/fill_form.html', context)


# ==================== جزئیات فرم ====================
@login_required
def form_detail(request, instance_id):
    instance = get_object_or_404(FormInstance, id=instance_id)
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "form_detail")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    has_access = False

    if instance.created_by == user:
        has_access = True
    elif user.is_admin:
        has_access = True
    elif user.has_role('secretary'):
        has_access = True
    else:
        all_fields = instance.fields.filter(is_active=True)
        for field in all_fields:
            if field.is_accessible_by(user):
                has_access = True
                break

    if not has_access:
        messages.error(request, 'شما اجازه مشاهده این فرم را ندارید')
        return redirect('form_flow:my_tasks')

    field_values = instance.field_values.all().select_related('instance_field', 'filled_by')
    step_history = instance.step_history or []
    progress = instance.get_step_progress()


    # ✅ بدون مجوز - هر کسی که به فرم دسترسی داره می‌تونه برگشت بزنه
    # can_reject = True

    can_reject = False

    # 1. ادمین یا سوپر یوزر
    if "reject_form_to_complet" in perimissin_list:
        can_reject = True

    # 3. کاربر مرحله بعد (بررسی‌کننده ذاتی)
    else:
        all_fields = instance.fields.filter(is_active=True)
        for field in all_fields:
            # اگر کاربر به این فیلد دسترسی داره
            if field.is_accessible_by(user):
                can_reject = True
                break

    # ✅ تایید نهایی هم بدون مجوز
    if "approve_form" in perimissin_list:
        can_approve = True
    else:
        can_approve = False

    context = {
        'instance': instance,
        'field_values': field_values,
        'step_history': step_history,
        'progress': progress,
        'can_reject': can_reject,
        'can_approve': can_approve,
        'title': f'جزئیات: {instance.title}',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_flow/form_detail.html', context)

# ==================== تاریخچه فرم ====================
@login_required
def form_history(request, instance_id):
    instance = get_object_or_404(FormInstance, id=instance_id)
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "form_history")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    if instance.created_by != user and instance.assigned_to != user and not user.is_admin:
        messages.error(request, 'شما اجازه مشاهده این فرم را ندارید')
        return redirect('form_flow:my_forms')

    step_history = instance.step_history or []
    field_history = instance.field_values.all().order_by('filled_at')

    context = {
        'instance': instance,
        'step_history': step_history,
        'field_history': field_history,
        'title': f'تاریخچه: {instance.title}',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_flow/form_history.html', context)


# ==================== لغو فرم ====================
@login_required
def cancel_form(request, instance_id):
    instance = get_object_or_404(FormInstance, id=instance_id)
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "cancel_form")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    if instance.created_by != user and not user.is_admin:
        messages.error(request, 'شما اجازه لغو این فرم را ندارید')
        return redirect('form_flow:my_forms')

    if instance.status in ['completed', 'approved', 'rejected']:
        messages.error(request, 'این فرم قابل لغو نیست')
        return redirect('form_flow:form_detail', instance_id=instance.id)

    instance.status = 'canceled'
    instance.save()

    messages.success(request, 'فرم با موفقیت لغو شد')
    return redirect('form_flow:my_forms')


# ==================== حذف فرم ====================
@login_required
def delete_form(request, instance_id):
    instance = get_object_or_404(FormInstance, id=instance_id)
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "delete_form")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    if instance.created_by != user and not user.is_admin:
        messages.error(request, 'شما اجازه حذف این فرم را ندارید')
        return redirect('form_flow:my_forms')

    if instance.status != 'draft':
        messages.error(request, 'فقط فرم‌های پیش‌نویس (قبل از شروع تکمیل) قابل حذف هستند')
        return redirect('form_flow:form_detail', instance_id=instance.id)

    instance.delete()
    messages.success(request, 'فرم با موفقیت حذف شد')
    return redirect('form_flow:my_forms')


# ==================== تایید فرم (ادمین) ====================
@login_required
def approve_form(request, instance_id):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "approve_form")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    instance = get_object_or_404(FormInstance, id=instance_id)

    # ✅ اضافه کردن rejected_fixed
    if instance.status != 'completed' and instance.status != 'rejected_fixed':
        messages.error(request, 'فقط فرم‌های تکمیل شده یا اصلاح شده قابل تایید هستند')
        return redirect('form_flow:form_detail', instance_id=instance.id)

    instance.status = 'approved'
    instance.save()

    messages.success(request, 'فرم با موفقیت تایید شد')
    return redirect('form_flow:form_detail', instance_id=instance.id)


# ==================== رد فرم (ادمین) ====================
@login_required
def reject_form(request, instance_id):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "reject_form")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    instance = get_object_or_404(FormInstance, id=instance_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        instance.status = 'rejected'
        instance.save()

        messages.warning(request, f'فرم رد شد: {reason}')
        return redirect('form_flow:form_detail', instance_id=instance.id)

    context = {
        'instance': instance,
        'title': f'رد فرم: {instance.title}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_flow/reject_form.html', context)


# ==================== API: دریافت تعداد وظایف ====================
@csrf_exempt
@login_required
def api_task_count(request):
    user = request.user

    # ✅ اضافه کردن 'rejected_fixed' به لیست وضعیت‌ها
    all_instances = FormInstance.objects.filter(
        status__in=['in_progress', 'waiting', 'overdue', 'rejected_fixed']
    )

    task_count = 0

    if user.is_admin:
        task_count = all_instances.count()
    else:
        for instance in all_instances:
            current_fields = instance.get_fields_by_step(instance.current_step_number)
            for field in current_fields:
                if field.is_accessible_by(user):
                    try:
                        fv = FormFieldValue.objects.get(
                            form_instance=instance,
                            instance_field=field
                        )
                        if not fv.value and not fv.file_value and not fv.image_value:
                            task_count += 1
                            break
                    except FormFieldValue.DoesNotExist:
                        task_count += 1
                        break

    return JsonResponse({
        'task_count': task_count,
        'has_new_tasks': task_count > 0
    })


# ==================== خروجی PDF با reportlab ====================
@login_required
def form_pdf(request, instance_id):
    """خروجی PDF از فرم (همراه با فیلدهای تکمیل شده و نشده)"""
    instance = get_object_or_404(FormInstance, id=instance_id)
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "form_pdf")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')



    # if instance.created_by != user and instance.assigned_to != user and not user.is_admin:
    #     messages.error(request, 'شما اجازه مشاهده این فرم را ندارید')
    #     return redirect('form_flow:my_forms')

    # ============ دریافت همه فیلدهای فرم (حتی پر نشده) ============
    all_fields = instance.fields.filter(is_active=True).order_by('step_number', 'order')

    # ============ دریافت مقادیر پر شده ============
    field_values = {}
    for fv in instance.field_values.all().select_related('instance_field', 'filled_by'):
        field_values[fv.instance_field_id] = fv

    # ============ دریافت اطلاعات مراحل ============
    max_step = instance.get_max_step()
    step_info = {}

    # ایجاد لیست کامل مراحل (حتی مراحلی که فیلد ندارن)
    for step_num in range(1, max_step + 1):
        step_info[step_num] = {
            'fields': [],
            'all_filled': True,
            'total': 0,
            'filled': 0,
            'is_completed': False,
            'completed_by': None,
            'completed_at': None,
            'started_at': None,
            'duration': None,
            'was_overdue': False
        }

    # پر کردن اطلاعات فیلدها
    for field in all_fields:
        step_num = field.step_number
        if step_num in step_info:
            step_info[step_num]['fields'].append(field)
            step_info[step_num]['total'] += 1

            if field.id in field_values:
                fv = field_values[field.id]
                if fv.value or fv.file_value or fv.image_value:
                    step_info[step_num]['filled'] += 1
                else:
                    step_info[step_num]['all_filled'] = False
            else:
                step_info[step_num]['all_filled'] = False

    # ============ دریافت تاریخچه مراحل ============
    step_history = instance.step_history or []

    # بروزرسانی اطلاعات مراحل از تاریخچه
    for step in step_history:
        step_num = step.get('step_number')
        if step_num in step_info:
            step_info[step_num]['is_completed'] = True
            step_info[step_num]['completed_by'] = step.get('completed_by_name')
            step_info[step_num]['completed_at'] = step.get('completed_at')
            step_info[step_num]['started_at'] = step.get('started_at')
            step_info[step_num]['duration'] = step.get('duration_hours')
            step_info[step_num]['was_overdue'] = step.get('was_overdue', False)
    # ==============================================================

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="form_{instance.id}_{instance.custom_name}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    # ============ فونت فارسی ============
    font_paths = [
        os.path.join(settings.BASE_DIR, 'assets', 'index', 'fonts', 'Vazirmatn-Black.ttf'),
        os.path.join(settings.BASE_DIR, 'assets', 'fonts', 'Vazir.ttf'),
        os.path.join(settings.BASE_DIR, 'assets', 'fonts', 'Vazirmatn-Black.ttf'),
    ]

    font_name = 'Helvetica'
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('Vazir', path))
                font_name = 'Vazir'
                break
            except:
                pass
    # =====================================

    styles = getSampleStyleSheet()

    # ============ استایل‌های راست‌چین ============
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#0d6efd'),
        spaceAfter=12
    )

    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=13,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        alignment=TA_RIGHT  # راست‌چین
    )

    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        alignment=TA_RIGHT,  # راست‌چین
        spaceAfter=3
    )

    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        textColor=colors.HexColor('#6c757d'),
        alignment=TA_RIGHT,  # راست‌چین
        spaceAfter=3
    )

    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        alignment=TA_CENTER,
    )

    status_ok_style = ParagraphStyle(
        'StatusOkStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        textColor=colors.HexColor('#28a745'),
        alignment=TA_RIGHT,  # راست‌چین
        spaceAfter=3
    )

    status_pending_style = ParagraphStyle(
        'StatusPendingStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        textColor=colors.HexColor('#dc3545'),
        alignment=TA_RIGHT,  # راست‌چین
        spaceAfter=3
    )

    elements = []

    # ============ هدر ============
    elements.append(Paragraph(fix_text(instance.title), title_style))
    elements.append(Spacer(1, 6))

    # ============ اطلاعات فرم ============
    info_data = [
        [Paragraph(fix_text("نام فرم:"), label_style),
         Paragraph(fix_text(instance.custom_name or instance.title), normal_style)],
        [Paragraph(fix_text("وضعیت:"), label_style),
         Paragraph(fix_text(instance.get_status_display()), normal_style)],
        [Paragraph(fix_text("ایجاد شده توسط:"), label_style),
         Paragraph(fix_text(instance.created_by.get_full_name() or instance.created_by.username), normal_style)],
        [Paragraph(fix_text("تاریخ ایجاد:"), label_style),
         Paragraph(instance.created_at.strftime('%Y/%m/%d %H:%M'), normal_style)],
        [Paragraph(fix_text("تعداد مراحل:"), label_style),
         Paragraph(str(len(step_info)), normal_style)],
        [Paragraph(fix_text("وضعیت تکمیل:"), label_style),
         Paragraph(fix_text(f"{instance.field_values.count()} از {all_fields.count()} فیلد پر شده"), normal_style)],
    ]

    if instance.completed_at:
        info_data.append([Paragraph(fix_text("تاریخ تکمیل:"), label_style),
                          Paragraph(instance.completed_at.strftime('%Y/%m/%d %H:%M'), normal_style)])

    info_table = Table(info_data, colWidths=[70 * mm, 110 * mm])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    # ============ خط جداکننده ============
    elements.append(Paragraph(fix_text("─────────────────────────────────────────────────────────────"), normal_style))

    # ============ تاریخچه همه مراحل ============
    elements.append(Paragraph(fix_text("تاریخچه مراحل:"), heading_style))
    elements.append(Spacer(1, 4))

    step_data = [
        [fix_text("مرحله"), fix_text("تکمیل شده توسط"),
         fix_text("زمان شروع"), fix_text("زمان تکمیل"),
         fix_text("مدت زمان"), fix_text("وضعیت"), fix_text("پیشرفت")]
    ]

    for step_num, info in sorted(step_info.items()):
        if info['is_completed']:
            duration = info['duration'] or 0
            duration_str = f"{duration:.1f} ساعت" if duration > 0 else "-"
            status = fix_text("تاخیر") if info['was_overdue'] else fix_text("تکمیل")
            completed_by = fix_text(info['completed_by'] or '-')
            completed_at = info['completed_at'][:16] if info['completed_at'] else '-'
            started_at = info['started_at'][:16] if info['started_at'] else '-'
        else:
            duration_str = fix_text("-")
            status = fix_text("🔴 انجام نشده")
            completed_by = fix_text("-")
            completed_at = fix_text("-")
            started_at = fix_text("-")

        total = info['total']
        filled = info['filled']
        progress_str = f"{filled}/{total}" if total > 0 else "-"

        step_data.append([
            fix_text(f"مرحله {step_num}"),
            completed_by,
            started_at,
            completed_at,
            duration_str,
            status,
            progress_str
        ])

    step_table = Table(step_data, colWidths=[35 * mm, 35 * mm, 32 * mm, 32 * mm, 25 * mm, 25 * mm, 20 * mm])
    step_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        # رنگ‌بندی وضعیت
        ('BACKGROUND', (5, 1), (5, -1),
         colors.HexColor('#e8f5e9') if 'تکمیل' in str(step_data[-1][5]) else colors.HexColor('#ffebee')),
    ]))
    elements.append(step_table)
    elements.append(Spacer(1, 10))

    # ============ نمایش همه فیلدها بر اساس مرحله ============
    elements.append(Paragraph(fix_text("لیست کامل فیلدها:"), heading_style))
    elements.append(Spacer(1, 4))

    for step_num, info in sorted(step_info.items()):
        if not info['fields']:
            continue

        # عنوان مرحله
        step_title = fix_text(f"مرحله {step_num}")
        if info['all_filled'] and info['total'] > 0:
            step_title += fix_text(" ✅ (تکمیل شده)")
        elif info['total'] > 0:
            step_title += fix_text(f" ⏳ ({info['filled']}/{info['total']} پر شده)")
        else:
            step_title += fix_text(" (بدون فیلد)")

        elements.append(Paragraph(step_title, heading_style))
        elements.append(Spacer(1, 2))

        # جدول فیلدهای این مرحله
        field_data = [
            [fix_text("فیلد"), fix_text("مقدار"),
             fix_text("تکمیل شده توسط"), fix_text("زمان"), fix_text("وضعیت")]
        ]

        for field in info['fields']:
            if field.id in field_values:
                fv = field_values[field.id]
                value = fv.value or "-"
                if fv.file_value:
                    value = fv.file_value.name.split('/')[-1]
                elif fv.image_value:
                    value = fv.image_value.name.split('/')[-1]

                filled_by = fix_text(fv.filled_by.get_full_name() or fv.filled_by.username) if fv.filled_by else "-"
                filled_at = fv.filled_at.strftime('%Y/%m/%d %H:%M') if fv.filled_at else "-"

                is_filled = bool(fv.value or fv.file_value or fv.image_value)
                status = fix_text("✅ تکمیل") if is_filled else fix_text("⏳ تکمیل نشده")
            else:
                value = fix_text("-")
                filled_by = fix_text("-")
                filled_at = fix_text("-")
                status = fix_text("⏳ تکمیل نشده")

            field_data.append([
                fix_text(field.field_title),
                fix_text(value) if isinstance(value, str) else value,
                filled_by,
                filled_at,
                status
            ])

        field_table = Table(field_data, colWidths=[50 * mm, 50 * mm, 35 * mm, 40 * mm, 30 * mm])
        field_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(field_table)
        elements.append(Spacer(1, 6))

    # ============ امضا ============
    elements.append(Spacer(1, 15))

    signature_data = [
        [fix_text("امضا:"), fix_text("_________________________")],
        [fix_text("تاریخ:"), timezone.now().strftime('%Y/%m/%d %H:%M')],
    ]
    sig_table = Table(signature_data, colWidths=[40 * mm, 80 * mm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(sig_table)

    # ============ فوتر ============
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(
        fix_text(f"تولید شده توسط سیستم مدیریت فرم‌ها - {timezone.now().strftime('%Y/%m/%d %H:%M')}"),
        footer_style
    ))

    doc.build(elements)
    return response