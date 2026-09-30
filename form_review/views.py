from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from myclass.mydef import views_permissions
from form_flow.models import FormInstance, FormFieldValue, InstanceField
from account.models import User
from .models import Rejection, RejectionReply


def is_admin(user):
    return user.is_admin or user.is_superuser


# ================================================================
# ویو: فرم‌های در انتظار بررسی
# ================================================================
@login_required
def pending_reviews(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "pending_reviews")

    # ✅ اگر مجوز نداشت، باز هم دسترسی بده (عمومی)
    if permission is False:
        messages.error(request, 'شما اجازه مشاهده این صفحه را ندارید')
        return redirect('site_profile:page_404')

    instances = FormInstance.objects.filter(
        status__in=['completed', 'rejected_fixed']
    ).exclude(status='approved').order_by('-updated_at')

    filtered_instances = []
    for instance in instances:
        filtered_instances.append(instance)

    context = {
        'instances': filtered_instances,
        'title': 'فرم‌های در انتظار بررسی',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_review/pending_reviews.html', context)


# ================================================================
# ویو: برگشت فرم
# ================================================================
@login_required
def reject_form(request, instance_id):
    instance = get_object_or_404(FormInstance, id=instance_id)
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "reject_form_to_complet")

    if permission is False:
        messages.error(request, 'شما اجازه مشاهده این صفحه را ندارید')
        return redirect('site_profile:page_404')

    # ============================================================
    # ✅ بررسی مجوز برگشت
    # ============================================================
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

    # can_reject = True

    if not can_reject:
        messages.error(request,
                       'شما اجازه برگشت این فرم را ندارید. فقط کاربران مرحله بعد یا بررسی‌کنندگان می‌توانند برگشت بزنند.')
        return redirect('form_flow:form_detail', instance_id=instance.id)

    # بررسی دسترسی به فرم
    # has_access = False
    # if instance.created_by == user:
    #     has_access = True
    # elif user.is_admin:
    #     has_access = True
    # else:
    #     all_fields = instance.fields.filter(is_active=True)
    #     for field in all_fields:
    #         if field.is_accessible_by(user):
    #             has_access = True
    #             break
    #
    # if not has_access:
    #     messages.error(request, 'شما اجازه دسترسی به این فرم را ندارید')
    #     return redirect('site_profile:page_404')

    if instance.status in ['approved', 'canceled']:
        messages.error(request, 'این فرم قابل برگشت نیست')
        return redirect('form_flow:form_detail', instance_id=instance.id)

    fields = instance.fields.filter(is_active=True).order_by('step_number', 'order')
    steps = instance.get_all_steps_info()

    # تشخیص خودکار کاربران مسئول اصلاح
    def get_assigned_users(level, field_id=None, step_number=None):
        assigned_users = []

        if level == 'field' and field_id:
            try:
                fv = FormFieldValue.objects.filter(
                    form_instance=instance,
                    instance_field_id=field_id
                ).first()
                if fv and fv.filled_by:
                    assigned_users.append(fv.filled_by)
            except:
                pass
            if not assigned_users and instance.created_by:
                assigned_users.append(instance.created_by)

        elif level == 'step' and step_number:
            step_fields = instance.fields.filter(step_number=step_number, is_active=True)
            for field in step_fields:
                try:
                    fv = FormFieldValue.objects.filter(
                        form_instance=instance,
                        instance_field=field
                    ).first()
                    if fv and fv.filled_by and fv.filled_by not in assigned_users:
                        assigned_users.append(fv.filled_by)
                except:
                    pass
            if not assigned_users and instance.created_by:
                assigned_users.append(instance.created_by)

        else:
            if instance.created_by:
                assigned_users.append(instance.created_by)
            all_field_values = instance.field_values.select_related('filled_by')
            for fv in all_field_values:
                if fv.filled_by and fv.filled_by not in assigned_users:
                    assigned_users.append(fv.filled_by)

        return assigned_users

    if request.method == 'POST':
        level = request.POST.get('level')
        reason = request.POST.get('reason')
        field_id = request.POST.get('field_id')
        step_number = request.POST.get('step_number')
        deadline_hours = request.POST.get('deadline_hours', 48)

        if not reason:
            messages.error(request, 'لطفاً دلیل برگشت را وارد کنید')
            return render(request, 'form_review/reject_form.html', {
                'instance': instance,
                'fields': fields,
                'steps': steps,
                'title': f'برگشت فرم: {instance.title}',
                'userId': user.id,
                'this_user': user,
                "perimissin_list": perimissin_list,
                "perimissin_group": perimissin_group,
            })

        try:
            with transaction.atomic():
                assigned_users = get_assigned_users(level, field_id, step_number)

                if not assigned_users:
                    assigned_users = [instance.created_by] if instance.created_by else []

                for assigned_user in assigned_users:
                    rejection = Rejection.objects.create(
                        form_instance=instance,
                        level=level,
                        reason=reason,
                        rejected_by=user,
                        assigned_to=assigned_user,
                        deadline_hours=int(deadline_hours) if deadline_hours else 48,
                        deadline_at=timezone.now() + timedelta(hours=int(deadline_hours) if deadline_hours else 48),
                        instance_field_id=field_id if level == 'field' else None,
                        step_number=step_number if level == 'step' else None,
                    )

                instance.status = 'rejected'
                instance.is_rejected = True
                instance.rejected_at = timezone.now()
                instance.rejected_by = user
                instance.rejection_reason = reason
                instance.rejection_level = level
                instance.total_rejections = Rejection.objects.filter(form_instance=instance).count()
                instance.save()

                user_names = [u.get_full_name() or u.username for u in assigned_users]
                messages.success(
                    request,
                    f'فرم "{instance.title}" با موفقیت برگشت داده شد. '
                    f'کاربران مسئول اصلاح: {", ".join(user_names)}'
                )
                return redirect('form_flow:form_detail', instance_id=instance.id)

        except Exception as e:
            messages.error(request, f'خطا در برگشت فرم: {str(e)}')

    # نمایش پیش‌نمایش کاربران مسئول اصلاح
    field_assigned_users = {}
    for field in fields:
        try:
            fv = FormFieldValue.objects.filter(
                form_instance=instance,
                instance_field=field
            ).first()
            if fv and fv.filled_by:
                field_assigned_users[field.id] = fv.filled_by
            else:
                field_assigned_users[field.id] = instance.created_by
        except:
            field_assigned_users[field.id] = instance.created_by

    step_assigned_users = {}
    for step_num in steps.keys():
        step_fields = instance.fields.filter(step_number=step_num, is_active=True)
        users = []
        for field in step_fields:
            try:
                fv = FormFieldValue.objects.filter(
                    form_instance=instance,
                    instance_field=field
                ).first()
                if fv and fv.filled_by and fv.filled_by not in users:
                    users.append(fv.filled_by)
            except:
                pass
        if not users and instance.created_by:
            users.append(instance.created_by)
        step_assigned_users[step_num] = users

    context = {
        'instance': instance,
        'fields': fields,
        'steps': steps,
        'field_assigned_users': field_assigned_users,
        'step_assigned_users': step_assigned_users,
        'title': f'برگشت فرم: {instance.title}',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_review/reject_form.html', context)


# ================================================================
# ویو: فرم‌های برگشتی من
# ================================================================
@login_required
def my_rejected_forms(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(user, "my_rejected_forms")

    # ✅ اگر مجوز نداشت، باز هم دسترسی بده (عمومی)
    if permission is False:
        messages.error(request, 'شما اجازه مشاهده این صفحه را ندارید')
        return redirect('site_profile:page_404')

    rejections = Rejection.objects.filter(
        assigned_to=user,
        status__in=['pending', 'responded']
    ).select_related('form_instance').order_by('-created_at')

    instances = {}
    for rejection in rejections:
        if rejection.form_instance.id not in instances:
            instances[rejection.form_instance.id] = {
                'instance': rejection.form_instance,
                'rejections': []
            }
        instances[rejection.form_instance.id]['rejections'].append(rejection)

    context = {
        'instances': instances.values(),
        'title': 'فرم‌های برگشتی من',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_review/my_rejected_forms.html', context)


# ================================================================
# ویو: اصلاح فرم برگشتی
# ================================================================
@login_required
def fix_rejected_form(request, rejection_id):
    rejection = get_object_or_404(Rejection, id=rejection_id)
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "fix_rejected_form")

    # ✅ اگر مجوز نداشت، باز هم دسترسی بده (عمومی)
    if permission is False:
        messages.error(request, 'شما اجازه اصلاح فرم برگشتی را ندارید')
        return redirect('site_profile:page_404')

    # if rejection.assigned_to != user and not user.is_admin:
    #     messages.error(request, 'شما اجازه اصلاح این فرم برگشتی را ندارید')
    #     return redirect('form_review:my_rejected_forms')

    instance = rejection.form_instance

    fields_to_fix = []
    if rejection.level == 'field' and rejection.instance_field:
        fields_to_fix = [rejection.instance_field]
    elif rejection.level == 'step' and rejection.step_number:
        fields_to_fix = instance.fields.filter(
            step_number=rejection.step_number,
            is_active=True
        )
    else:
        fields_to_fix = instance.fields.filter(is_active=True)

    existing_values = {}
    for field in fields_to_fix:
        try:
            fv = FormFieldValue.objects.get(
                form_instance=instance,
                instance_field=field
            )
            if fv.value:
                existing_values[field.id] = fv.value
            elif fv.file_value:
                existing_values[field.id] = fv.file_value.url
            elif fv.image_value:
                existing_values[field.id] = fv.image_value.url
        except FormFieldValue.DoesNotExist:
            pass

    replies = rejection.replies.all()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                for field in fields_to_fix:
                    value = request.POST.get(field.field_name)
                    file_value = request.FILES.get(field.field_name)

                    if value is None and file_value is None:
                        continue

                    field_value, created = FormFieldValue.objects.get_or_create(
                        form_instance=instance,
                        instance_field=field
                    )

                    if file_value:
                        if field.original_input and field.original_input.input.input_type == 'image':
                            field_value.image_value = file_value
                        else:
                            field_value.file_value = file_value
                        field_value.value = None
                    elif value is not None:
                        field_value.value = value.strip() if value else ''
                        field_value.file_value = None
                        field_value.image_value = None

                    field_value.filled_by = user
                    field_value.save()

                RejectionReply.objects.create(
                    rejection=rejection,
                    user=user,
                    text=request.POST.get('fix_comment', 'فرم اصلاح شد'),
                    reply_type='fix'
                )

                rejection.status = 'fixed'
                rejection.save()

                instance.status = 'rejected_fixed'
                instance.is_rejected = False
                instance.save()

                messages.success(request, 'فرم با موفقیت اصلاح شد و دوباره برای بررسی ارسال شد')
                return redirect('form_review:my_rejected_forms')

        except Exception as e:
            messages.error(request, f'خطا در اصلاح فرم: {str(e)}')

    context = {
        'rejection': rejection,
        'instance': instance,
        'fields_to_fix': fields_to_fix,
        'existing_values': existing_values,
        'replies': replies,
        'title': f'اصلاح فرم برگشتی: {instance.title}',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_review/fix_rejected_form.html', context)


# ================================================================
# ویو: پاسخ به برگشت
# ================================================================
@login_required
def reply_to_rejection(request, rejection_id):
    rejection = get_object_or_404(Rejection, id=rejection_id)
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "reply_to_rejection")

    # ✅ اگر مجوز نداشت، باز هم دسترسی بده (عمومی)
    if permission is False:
        messages.error(request, 'شما اجازه پاسخ به برگشت را ندارید')
        return redirect('site_profile:page_404')

    # if rejection.assigned_to != user and not user.is_admin:
    #     messages.error(request, 'شما اجازه پاسخ به این برگشت را ندارید')
    #     return redirect('form_review:my_rejected_forms')

    if request.method == 'POST':
        text = request.POST.get('text')
        reply_type = request.POST.get('reply_type', 'response')
        attachment = request.FILES.get('attachment')

        if not text:
            messages.error(request, 'لطفاً متن پاسخ را وارد کنید')
            return redirect('form_review:fix_rejected_form', rejection_id=rejection.id)

        try:
            with transaction.atomic():
                reply = RejectionReply.objects.create(
                    rejection=rejection,
                    user=user,
                    text=text,
                    reply_type=reply_type,
                    attachment=attachment
                )

                if reply_type == 'approve':
                    rejection.status = 'approved'
                    rejection.form_instance.status = 'approved'
                    rejection.form_instance.save()
                    messages.success(request, 'فرم تایید شد')
                elif reply_type == 'reject_again':
                    rejection.status = 'rejected_again'
                    rejection.form_instance.status = 'rejected'
                    rejection.form_instance.is_rejected = True
                    rejection.form_instance.save()
                    messages.warning(request, 'فرم دوباره برگشت خورد')
                else:
                    rejection.status = 'responded'
                    rejection.save()
                    messages.success(request, 'پاسخ شما ثبت شد')

                rejection.save()
                return redirect('form_review:fix_rejected_form', rejection_id=rejection.id)

        except Exception as e:
            messages.error(request, f'خطا در ثبت پاسخ: {str(e)}')

    return redirect('form_review:fix_rejected_form', rejection_id=rejection.id)


# ================================================================
# ویو: تاریخچه بررسی
# ================================================================
@login_required
def review_history(request, instance_id):
    instance = get_object_or_404(FormInstance, id=instance_id)
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "review_history")

    # ✅ اگر مجوز نداشت، باز هم دسترسی بده (عمومی)
    if permission is False:
        messages.error(request, 'شما اجازه مشاهده تاریخچه را ندارید')
        return redirect('site_profile:page_404')

    if instance.created_by != user and not user.is_admin:
        has_access = False
        all_fields = instance.fields.filter(is_active=True)
        for field in all_fields:
            if field.is_accessible_by(user):
                has_access = True
                break

        if not has_access:
            messages.error(request, 'شما اجازه مشاهده تاریخچه این فرم را ندارید')
            return redirect('form_review:my_rejected_forms')

    rejections = instance.rejections.all().prefetch_related('replies', 'rejected_by', 'assigned_to')

    context = {
        'instance': instance,
        'rejections': rejections,
        'title': f'تاریخچه بررسی: {instance.title}',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_review/review_history.html', context)


# ================================================================
# ویو: جزئیات برگشت
# ================================================================
@login_required
def review_detail(request, rejection_id):
    rejection = get_object_or_404(Rejection, id=rejection_id)
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(user, "review_detail")

    # ✅ اگر مجوز نداشت، باز هم دسترسی بده (عمومی)
    if permission is False:
        messages.error(request, 'شما اجازه مشاهده این برگشت را ندارید')
        return redirect('site_profile:page_404')

    instance = rejection.form_instance
    # has_access = False

    # if instance.created_by == user:
    #     has_access = True
    # elif user.is_admin:
    #     has_access = True
    # else:
    #     all_fields = instance.fields.filter(is_active=True)
    #     for field in all_fields:
    #         if field.is_accessible_by(user):
    #             has_access = True
    #             break
    #
    # if not has_access:
    #     messages.error(request, 'شما اجازه مشاهده این برگشت را ندارید')
    #     return redirect('site_profile:page_404')

    replies = rejection.replies.all()

    fixed_values = []
    if rejection.status in ['fixed', 'approved']:
        fixed_values = instance.field_values.filter(
            instance_field__in=instance.fields.filter(is_active=True)
        ).select_related('instance_field', 'filled_by')

    context = {
        'rejection': rejection,
        'replies': replies,
        'fixed_values': fixed_values,
        'title': f'جزئیات برگشت: {instance.title}',
        'userId': user.id,
        'this_user': user,
        "perimissin_list": perimissin_list,
        "perimissin_group": perimissin_group,
    }
    return render(request, 'form_review/review_detail.html', context)