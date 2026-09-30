# dynamicform/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import PermissionDenied

from myclass.mydef import views_permissions
from .models import FormTemplate, FormInput, InputTemplate, FieldOption
from account.models import Role, User


# ==================== لیست نمونه فرم‌ها ====================
@login_required
def form_template_list(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "form_template_list")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    """لیست همه نمونه فرم‌ها"""
    form_templates = FormTemplate.objects.all().order_by('-created_at')

    context = {
        'form_templates': form_templates,
        'title': 'لیست نمونه فرم‌ها',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'dynamicform/form_template_list.html', context)


# ==================== پیش‌نمایش نمونه فرم ====================
@login_required
def form_template_preview(request, form_id):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "form_template_preview")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    """نمایش پیش‌نمایش نمونه فرم"""
    form_template = get_object_or_404(FormTemplate, id=form_id, is_active=True)
    form_inputs = form_template.forminput_set.all().order_by('step_number', 'order')

    context = {
        'form_template': form_template,
        'form_inputs': form_inputs,
        'title': f'پیش‌نمایش: {form_template.title}',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'dynamicform/form_template_preview.html', context)


# ==================== ایجاد نمونه فرم جدید ====================
@login_required
def form_template_create(request):
    """ایجاد نمونه فرم جدید"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "form_template_create")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    input_templates = InputTemplate.objects.filter(is_active=True)
    roles = Role.objects.filter(is_active=True)

    if request.method == 'POST':
        name = request.POST.get('name')
        title = request.POST.get('title')
        description = request.POST.get('description')
        is_active = request.POST.get('is_active') == 'on'
        selected_roles = request.POST.getlist('allowed_roles[]')

        if not name or not title:
            messages.error(request, 'نام و عنوان فرم الزامی است')
            return render(request, 'dynamicform/form_template_create.html', {
                'input_templates': input_templates,
                'roles': roles,
                'form_data': request.POST,
                'userId': request.user.id,
                'this_user': request.user,
            })

        if FormTemplate.objects.filter(name=name).exists():
            messages.error(request, f'فرمی با نام "{name}" قبلاً تعریف شده است')
            return render(request, 'dynamicform/form_template_create.html', {
                'input_templates': input_templates,
                'roles': roles,
                'form_data': request.POST,
                'userId': request.user.id,
                'this_user': request.user,
            })

        try:
            with transaction.atomic():
                # ایجاد فرم نمونه
                form_template = FormTemplate.objects.create(
                    name=name,
                    title=title,
                    description=description,
                    is_active=is_active,
                    created_by=request.user
                )

                # اختصاص نقش‌های مجاز برای فرم
                for role_id in selected_roles:
                    try:
                        role = Role.objects.get(id=role_id)
                        form_template.allowed_roles.add(role)
                    except Role.DoesNotExist:
                        pass

                # دریافت فیلدهای فرم
                field_names = request.POST.getlist('field_name[]')
                field_titles = request.POST.getlist('field_title[]')
                field_inputs_post = request.POST.getlist('field_input[]')
                field_orders = request.POST.getlist('field_order[]')
                field_placeholders = request.POST.getlist('field_placeholder[]')
                field_help_texts = request.POST.getlist('field_help_text[]')
                field_access_types = request.POST.getlist('field_access_type[]')
                field_steps = request.POST.getlist('field_step[]')

                for i in range(len(field_names)):
                    if field_names[i] and field_titles[i] and field_inputs_post[i]:
                        try:
                            input_template = InputTemplate.objects.get(id=field_inputs_post[i])
                            step_number = int(field_steps[i]) if i < len(field_steps) and field_steps[i] else 1

                            is_required = request.POST.get(f'field_required_{i + 1}') == 'on'

                            # ایجاد فیلد
                            form_input = FormInput.objects.create(
                                form=form_template,
                                input=input_template,
                                field_name=field_names[i],
                                field_title=field_titles[i],
                                order=field_orders[i] if field_orders[i] else i,
                                step_number=step_number,
                                is_required=is_required,
                                placeholder=field_placeholders[i] if i < len(field_placeholders) else '',
                                help_text=field_help_texts[i] if i < len(field_help_texts) else '',
                                access_type=field_access_types[i] if i < len(field_access_types) else 'all',
                            )

                            # ============ ذخیره گزینه‌های این فیلد ============
                            field_index = i + 1
                            option_keys = request.POST.getlist(f'option_key_{field_index}[]')
                            option_values = request.POST.getlist(f'option_value_{field_index}[]')

                            for j in range(len(option_keys)):
                                if option_keys[j] and option_values[j]:
                                    FieldOption.objects.create(
                                        form_input=form_input,
                                        key=option_keys[j].strip(),
                                        value=option_values[j].strip(),
                                        order=j
                                    )
                            # ====================================================

                            # اختصاص نقش‌های مجاز برای فیلد
                            field_allowed_roles = request.POST.getlist(f'field_allowed_roles_{field_index}[]')
                            for role_id in field_allowed_roles:
                                try:
                                    role = Role.objects.get(id=role_id)
                                    form_input.allowed_roles.add(role)
                                except Role.DoesNotExist:
                                    pass

                        except InputTemplate.DoesNotExist:
                            pass

                messages.success(request, f'فرم "{form_template.title}" با موفقیت ایجاد شد')
                return redirect('dynamicform:form_template_list')

        except Exception as e:
            messages.error(request, f'خطا در ایجاد فرم: {str(e)}')

    context = {
        'input_templates': input_templates,
        'roles': roles,
        'title': 'ایجاد نمونه فرم جدید',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'dynamicform/form_template_create.html', context)


# ==================== ویرایش نمونه فرم ====================
@login_required
def form_template_edit(request, form_id):
    """ویرایش نمونه فرم"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "form_template_edit")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')

    form_template = get_object_or_404(FormTemplate, id=form_id)
    input_templates = InputTemplate.objects.filter(is_active=True)
    roles = Role.objects.filter(is_active=True)

    form_inputs = form_template.forminput_set.all().order_by('step_number', 'order')
    selected_roles = form_template.allowed_roles.values_list('id', flat=True)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        is_active = request.POST.get('is_active') == 'on'
        selected_roles_post = request.POST.getlist('allowed_roles[]')

        field_names = request.POST.getlist('field_name[]')
        field_titles = request.POST.getlist('field_title[]')
        field_inputs_post = request.POST.getlist('field_input[]')
        field_orders = request.POST.getlist('field_order[]')
        field_placeholders = request.POST.getlist('field_placeholder[]')
        field_help_texts = request.POST.getlist('field_help_text[]')
        field_access_types = request.POST.getlist('field_access_type[]')
        field_steps = request.POST.getlist('field_step[]')

        if not title:
            messages.error(request, 'عنوان فرم الزامی است')
            return render(request, 'dynamicform/form_template_edit.html', {
                'form_template': form_template,
                'input_templates': input_templates,
                'roles': roles,
                'form_inputs': form_inputs,
                'selected_roles': list(selected_roles),
                'userId': request.user.id,
                'this_user': request.user,
            })

        try:
            with transaction.atomic():
                # بروزرسانی فرم
                form_template.title = title
                form_template.description = description
                form_template.is_active = is_active
                form_template.save()

                # بروزرسانی نقش‌های مجاز فرم
                form_template.allowed_roles.clear()
                for role_id in selected_roles_post:
                    try:
                        role = Role.objects.get(id=role_id)
                        form_template.allowed_roles.add(role)
                    except Role.DoesNotExist:
                        pass

                # ============ حذف فیلدهای قبلی ============
                old_form_inputs = form_template.forminput_set.all()
                for old_input in old_form_inputs:
                    # حذف گزینه‌های مرتبط
                    old_input.field_options.all().delete()
                old_form_inputs.delete()
                # ========================================

                # ایجاد فیلدهای جدید
                for i in range(len(field_names)):
                    if field_names[i] and field_titles[i] and field_inputs_post[i]:
                        try:
                            input_template = InputTemplate.objects.get(id=field_inputs_post[i])
                            step_number = int(field_steps[i]) if i < len(field_steps) and field_steps[i] else 1

                            is_required = request.POST.get(f'field_required_{i + 1}') == 'on'

                            form_input = FormInput.objects.create(
                                form=form_template,
                                input=input_template,
                                field_name=field_names[i],
                                field_title=field_titles[i],
                                order=field_orders[i] if field_orders[i] else i,
                                step_number=step_number,
                                is_required=is_required,
                                placeholder=field_placeholders[i] if i < len(field_placeholders) else '',
                                help_text=field_help_texts[i] if i < len(field_help_texts) else '',
                                access_type=field_access_types[i] if i < len(field_access_types) else 'all',
                            )

                            # ============ ذخیره گزینه‌های این فیلد ============
                            field_index = i + 1
                            option_keys = request.POST.getlist(f'option_key_{field_index}[]')
                            option_values = request.POST.getlist(f'option_value_{field_index}[]')

                            for j in range(len(option_keys)):
                                if option_keys[j] and option_values[j]:
                                    FieldOption.objects.create(
                                        form_input=form_input,
                                        key=option_keys[j].strip(),
                                        value=option_values[j].strip(),
                                        order=j
                                    )
                            # ====================================================

                            # اختصاص نقش‌های مجاز برای فیلد
                            field_allowed_roles = request.POST.getlist(f'field_allowed_roles_{field_index}[]')
                            for role_id in field_allowed_roles:
                                try:
                                    role = Role.objects.get(id=role_id)
                                    form_input.allowed_roles.add(role)
                                except Role.DoesNotExist:
                                    pass

                        except InputTemplate.DoesNotExist:
                            pass

                messages.success(request, f'فرم "{form_template.title}" با موفقیت بروزرسانی شد')
                return redirect('dynamicform:form_template_list')

        except Exception as e:
            messages.error(request, f'خطا در بروزرسانی فرم: {str(e)}')

    context = {
        'form_template': form_template,
        'input_templates': input_templates,
        'roles': roles,
        'form_inputs': form_inputs,
        'selected_roles': list(selected_roles),
        'title': 'ویرایش نمونه فرم',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'dynamicform/form_template_edit.html', context)


# ==================== حذف نمونه فرم ====================
@login_required
def form_template_delete(request, form_id):
    """حذف نمونه فرم"""
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "form_template_delete")

    if permission is False:
        messages.error(request, 'شما اجازه استفاده از این فرم را ندارید')
        return redirect('site_profile:page_404')
    form_template = get_object_or_404(FormTemplate, id=form_id)

    if request.method == 'POST':
        form_template.delete()
        messages.success(request, f'فرم "{form_template.title}" با موفقیت حذف شد')
        return redirect('dynamicform:form_template_list')

    context = {
        'form_template': form_template,
        'title': 'حذف فرم',
        'userId': request.user.id,
        'this_user': request.user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'dynamicform/form_template_delete.html', context)