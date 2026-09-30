# transaction/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from django.db import transaction as db_transaction

from account.models import User
from estate.models import Customer, Property
from case_management.models import CustomerProcess, Visit, ProcessLog
from .models import Contract, CommissionSetting, Commission, AfterSalesService, WithdrawalRequest
from .forms import (
    ContractUpdateForm, CommissionCalculateForm, CommissionPayForm,
    CommissionSettingsForm, AfterSalesForm, WithdrawalRequestForm,
    WithdrawalApproveForm
)
from myclass.mydef import views_permissions
from django.db.models import F
from django.db import transaction


def is_ajax(request):
    """بررسی اینکه درخواست AJAX است"""
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


# ============================================================
# 📄 واحد قرارداد - ویوها (دست نخورده)
# ============================================================

@login_required
def contract_dashboard(request):
    """
    داشبورد واحد قرارداد - مشاهده و مدیریت قراردادها
    دسترسی: contract_officer
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "contract_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    pending_contracts = Contract.objects.filter(
        status=Contract.Status.PENDING
    ).select_related(
        'customer', 'customer__user', 'property_ref',
        'process__expert', 'process__supervisor', 'source_visit',
    ).order_by('-created_at')

    in_progress_contracts = Contract.objects.filter(
        status__in=[
            Contract.Status.DOCUMENTS_REVIEWED,
            Contract.Status.CONTRACT_DRAFTED,
            Contract.Status.SIGNED_BY_CUSTOMER,
            Contract.Status.SIGNED_BY_OTHER
        ]
    ).select_related(
        'customer', 'customer__user', 'property_ref',
        'process__expert', 'process__supervisor', 'source_visit',
    ).order_by('-updated_at')

    completed_contracts = Contract.objects.filter(
        status=Contract.Status.COMPLETED
    ).select_related(
        'customer', 'customer__user', 'property_ref',
        'process__expert', 'process__supervisor', 'source_visit',
    ).order_by('-finalization_date')

    stats = {
        'pending': pending_contracts.count(),
        'in_progress': in_progress_contracts.count(),
        'completed': completed_contracts.count(),
        'total': Contract.objects.count(),
    }

    context = {
        'title': 'داشبورد واحد قرارداد',
        'pending_contracts': pending_contracts,
        'in_progress_contracts': in_progress_contracts,
        'completed_contracts': completed_contracts,
        'stats': stats,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/contract_dashboard.html', context)


@login_required
def contract_detail(request, pk):
    """
    مشاهده جزئیات یک قرارداد
    دسترسی: contract_officer
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "contract_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    contract = get_object_or_404(
        Contract.objects.select_related(
            'customer', 'customer__user', 'property_ref',
            'process__expert', 'process__supervisor', 'source_visit',
            'source_visit__property_ref', 'commission', 'aftersales',
        ),
        pk=pk
    )

    customer = contract.customer
    property_obj = contract.property_ref
    source_visit = contract.source_visit

    if not customer and contract.process:
        customer = contract.process.customer
    if not property_obj and contract.process:
        if source_visit and source_visit.property_ref:
            property_obj = source_visit.property_ref
        else:
            last_visit = contract.process.visits.filter(
                property_ref__isnull=False
            ).order_by('-created_at').first()
            if last_visit:
                property_obj = last_visit.property_ref

    expert = contract.process.expert if contract.process else None
    supervisor = contract.process.supervisor if contract.process else None

    if source_visit and source_visit.negotiation_manager:
        last_visit = source_visit
    elif contract.process:
        last_visit = contract.process.visits.filter(
            negotiation_manager__isnull=False
        ).order_by('-created_at').first()
    else:
        last_visit = None

    commission = getattr(contract, 'commission', None)
    aftersales = getattr(contract, 'aftersales', None)

    context = {
        'title': f'جزئیات قرارداد - {customer.full_name if customer else "نامشخص"}',
        'contract': contract,
        'process': contract.process,
        'customer': customer,
        'property_obj': property_obj,
        'source_visit': source_visit,
        'expert': expert,
        'supervisor': supervisor,
        'last_visit': last_visit,
        'commission': commission,
        'aftersales': aftersales,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/contract_detail.html', context)


@login_required
def contract_update(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "contract_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    contract = get_object_or_404(Contract, pk=pk)

    if request.method == 'POST':
        form = ContractUpdateForm(request.POST, request.FILES, instance=contract)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.contract_officer = user

            if contract.status == Contract.Status.COMPLETED:
                if not contract.finalization_date:
                    contract.finalization_date = timezone.now()
                if not contract.is_ready_for_completion():
                    messages.warning(
                        request,
                        'لطفاً تمام فیلدهای الزامی (نوع قرارداد، مبلغ، امضا و فایل) را پر کنید.'
                    )
                    return redirect('transaction:contract_update', pk=contract.id)

            contract.save()

            # ✅ ایجاد کمیسیون (بدون محاسبه سهم‌ها)
            if contract.status == Contract.Status.COMPLETED and not hasattr(contract, 'commission'):
                from .models import CommissionSetting
                settings = CommissionSetting.get_default_settings()

                transaction_amount = contract.get_total_transaction_amount()

                # تعیین مبلغ کل کمیسیون
                if contract.commission_amount:
                    total_commission = contract.commission_amount
                else:
                    total_percent = (
                        settings.property_register_share +
                        settings.customer_register_share +
                        settings.expert_share +
                        settings.supervisor_share +
                        settings.meeting_manager_share
                    )
                    total_commission = int((total_percent / 100) * float(transaction_amount))

                # ✅ ایجاد کمیسیون با سهم‌های صفر و وضعیت PENDING
                Commission.objects.create(
                    contract=contract,
                    total_amount=transaction_amount,
                    total_commission=total_commission,
                    property_register_share=settings.property_register_share,
                    customer_register_share=settings.customer_register_share,
                    expert_share=settings.expert_share,
                    supervisor_share=settings.supervisor_share,
                    meeting_manager_share=settings.meeting_manager_share,
                    status=Commission.Status.PENDING,
                )

                messages.success(
                    request,
                    f'✅ قرارداد تکمیل شد و به واحد حسابداری ارسال گردید. '
                    f'مبلغ کمیسیون: {total_commission:,} تومان'
                )
            else:
                messages.success(request, 'قرارداد با موفقیت بروزرسانی شد')

            return redirect('transaction:contract_detail', pk=contract.id)
        else:
            messages.error(request, 'خطا در بروزرسانی قرارداد. لطفاً فرم را بررسی کنید.')
    else:
        form = ContractUpdateForm(instance=contract)

    context = {
        'title': f'بروزرسانی قرارداد - {contract.customer.full_name if contract.customer else "نامشخص"}',
        'form': form,
        'contract': contract,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/contract_update.html', context)


# ============================================================
# 💰 واحد حسابداری - ویوها (اصلاح شده)
# ============================================================

@login_required
def commission_dashboard(request):
    """
    داشبورد واحد حسابداری - مدیریت کمیسیون‌ها
    دسترسی: accountant
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    # ====== دریافت کمیسیون‌ها ======
    pending_commissions = Commission.objects.filter(
        status=Commission.Status.PENDING
    ).select_related(
        'contract',
        'contract__customer',
        'contract__customer__user',
        'contract__property_ref',
        'contract__source_visit',
        'contract__process__expert',
        'contract__process__supervisor',
    ).order_by('-created_at')

    calculated_commissions = Commission.objects.filter(
        status=Commission.Status.CALCULATED
    ).select_related(
        'contract',
        'contract__customer',
        'contract__customer__user',
        'contract__property_ref',
        'contract__source_visit',
        'accountant',
    ).order_by('-updated_at')

    # ✅ وضعیت جدید: واریز شده به کیف پول
    wallet_transferred_commissions = Commission.objects.filter(
        status=Commission.Status.WALLET_TRANSFERRED
    ).select_related(
        'contract',
        'contract__customer',
        'contract__property_ref',
        'wallet_transferred_by',
    ).order_by('-wallet_transferred_at')

    paid_commissions = Commission.objects.filter(
        status=Commission.Status.PAID
    ).select_related(
        'contract',
        'contract__customer',
        'contract__property_ref',
        'accountant',
    ).order_by('-paid_at')

    settings = CommissionSetting.get_default_settings()

    # ====== آمار ======
    stats = {
        'pending': pending_commissions.count(),
        'calculated': calculated_commissions.count(),
        'wallet_transferred': wallet_transferred_commissions.count(),
        'paid': paid_commissions.count(),
        'total_commission_pending': sum([c.total_commission for c in pending_commissions]),
        'total_commission_calculated': sum([c.total_commission for c in calculated_commissions]),
        'total_commission_transferred': sum([c.total_commission for c in wallet_transferred_commissions]),
        'total_commission_paid': sum([c.total_commission for c in paid_commissions]),
    }

    context = {
        'title': 'داشبورد واحد حسابداری',
        'pending_commissions': pending_commissions,
        'calculated_commissions': calculated_commissions,
        'wallet_transferred_commissions': wallet_transferred_commissions,
        'paid_commissions': paid_commissions,
        'settings': settings,
        'stats': stats,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/commission_dashboard.html', context)


@login_required
def commission_detail(request, pk):
    """
    مشاهده جزئیات کمیسیون
    دسترسی: accountant
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    commission = get_object_or_404(
        Commission.objects.select_related(
            'contract', 'contract__customer', 'contract__customer__user',
            'contract__property_ref', 'contract__process__expert',
            'contract__process__supervisor', 'accountant',
            'wallet_transferred_by',
        ),
        pk=pk
    )

    # ====== دریافت سهم‌ها ======
    shares = None
    if commission.status != Commission.Status.PENDING:
        shares = commission.get_shares_dict()

    # ====== بررسی امکان انتقال به کیف پول ======
    can_transfer_to_wallet = (
        commission.status == Commission.Status.CALCULATED and
        commission.total_commission > 0
    )

    # ====== بررسی امکان پرداخت مستقیم (برای روش قدیمی) ======
    can_pay_directly = (
        commission.status in [Commission.Status.CALCULATED, Commission.Status.PARTIAL_PAID] and
        commission.status != Commission.Status.PAID
    )

    context = {
        'title': f'جزئیات کمیسیون - {commission.customer.full_name if commission.customer else "نامشخص"}',
        'commission': commission,
        'shares': shares,
        'can_transfer_to_wallet': can_transfer_to_wallet,
        'can_pay_directly': can_pay_directly,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/commission_detail.html', context)

@login_required
def commission_calculate(request, pk):
    """
    محاسبه کمیسیون برای یک قرارداد
    دسترسی: accountant
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    commission = get_object_or_404(Commission, pk=pk)

    if commission.status != Commission.Status.PENDING:
        messages.warning(request, 'این کمیسیون قبلاً محاسبه شده است.')
        return redirect('transaction:commission_detail', pk=commission.id)

    # ============================================================
    # ✅ دریافت اطلاعات گیرنده‌ها از قرارداد
    # ============================================================
    contract = commission.contract
    shares = {
        'property_register': {
            'recipient': contract.property_ref.created_by if contract.property_ref else None,
        },
        'customer_register': {
            'recipient': contract.customer.created_by if contract.customer else None,
        },
        'expert': {
            'recipient': contract.expert,
        },
        'supervisor': {
            'recipient': contract.supervisor,
        },
        'meeting_manager': {
            'recipient': contract.process.visits.filter(
                negotiation_manager__isnull=False
            ).order_by('-created_at').first().negotiation_manager if contract.process.visits.filter(negotiation_manager__isnull=False).exists() else None,
        },
    }

    if request.method == 'POST':
        form = CommissionCalculateForm(request.POST, instance=commission)
        if form.is_valid():
            commission = form.save(commit=False)
            result = commission.calculate_commission(accountant=user)
            if result:
                messages.success(
                    request,
                    f'✅ کمیسیون با موفقیت محاسبه شد. مبلغ کل: {commission.total_commission:,} تومان'
                )
                return redirect('transaction:commission_detail', pk=commission.id)
            else:
                messages.error(
                    request,
                    'امکان محاسبه کمیسیون وجود ندارد. مبلغ کل معامله صفر است.'
                )
        else:
            messages.error(request, 'خطا در محاسبه کمیسیون. لطفاً فرم را بررسی کنید.')
    else:
        settings = CommissionSetting.get_default_settings()
        initial_data = {
            'property_register_share': settings.property_register_share,
            'customer_register_share': settings.customer_register_share,
            'expert_share': settings.expert_share,
            'supervisor_share': settings.supervisor_share,
            'meeting_manager_share': settings.meeting_manager_share,
        }
        form = CommissionCalculateForm(instance=commission, initial=initial_data)

    context = {
        'title': f'محاسبه کمیسیون - {commission.customer.full_name if commission.customer else "نامشخص"}',
        'form': form,
        'commission': commission,
        'shares': shares,  # ✅ ارسال به قالب
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/commission_calculate.html', context)


# ============================================================
# ✅ ویو جدید: واریز سهم‌ها به کیف پول گیرندگان
# ============================================================

@login_required
def commission_transfer_to_wallet(request, pk):
    """
    واریز مستقیم سهم‌های کمیسیون به کیف پول گیرندگان
    (همه منطق در ویو انجام می‌شود)
    دسترسی: accountant
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    commission = get_object_or_404(Commission, pk=pk)

    # ============================================================
    # ✅ بررسی وضعیت کمیسیون
    # ============================================================
    if commission.status == Commission.Status.WALLET_TRANSFERRED:
        messages.warning(request, 'این کمیسیون قبلاً به کیف پول‌ها واریز شده است.')
        return redirect('transaction:commission_detail', pk=commission.id)

    if commission.status != Commission.Status.CALCULATED:
        messages.warning(request, 'ابتدا باید کمیسیون را محاسبه کنید.')
        return redirect('transaction:commission_calculate', pk=commission.id)

    # ============================================================
    # ✅ دریافت لیست گیرندگان (مستقیماً از فیلدهای مدل)
    # ============================================================
    recipients = []
    errors = []

    # 1. ثبت‌کننده فایل
    if commission.contract.property_ref and commission.contract.property_ref.created_by:
        recipients.append({
            'user': commission.contract.property_ref.created_by,
            'amount': commission.property_register_amount,
            'role': 'ثبت‌کننده فایل'
        })
    else:
        errors.append('ثبت‌کننده فایل مشخص نیست.')

    # 2. ثبت‌کننده مشتری
    if commission.contract.customer and commission.contract.customer.created_by:
        recipients.append({
            'user': commission.contract.customer.created_by,
            'amount': commission.customer_register_amount,
            'role': 'ثبت‌کننده مشتری'
        })
    else:
        errors.append('ثبت‌کننده مشتری مشخص نیست.')

    # 3. کارشناس
    if commission.contract.expert:
        recipients.append({
            'user': commission.contract.expert,
            'amount': commission.expert_amount,
            'role': 'کارشناس'
        })
    else:
        errors.append('کارشناس مشخص نیست.')

    # 4. سرپرست
    if commission.contract.supervisor:
        recipients.append({
            'user': commission.contract.supervisor,
            'amount': commission.supervisor_amount,
            'role': 'سرپرست'
        })
    else:
        errors.append('سرپرست مشخص نیست.')

    # 5. مدیر جلسه
    meeting_manager = commission._get_meeting_manager()
    if meeting_manager:
        recipients.append({
            'user': meeting_manager,
            'amount': commission.meeting_manager_amount,
            'role': 'مدیر جلسه'
        })
    else:
        errors.append('مدیر جلسه مشخص نیست.')

    # ============================================================
    # ✅ بررسی وجود گیرنده
    # ============================================================
    if not recipients:
        error_msg = 'هیچ گیرنده معتبری برای واریز وجود ندارد. موارد زیر را بررسی کنید:\n' + '\n'.join(errors)
        messages.error(request, error_msg)
        return redirect('transaction:commission_detail', pk=commission.id)

    # اگر برخی گیرنده‌ها مشخص نباشند، هشدار می‌دهیم اما ادامه می‌دهیم
    if errors:
        messages.warning(request, '⚠️ برخی گیرنده‌ها مشخص نیستند:\n' + '\n'.join(errors))

    # ============================================================
    # ✅ واریز به کیف پول
    # ============================================================

    transferred_details = []
    total_transferred = 0

    with transaction.atomic():
        for item in recipients:
            recipient_user = item['user']
            amount = item['amount']
            role = item['role']

            # ✅ به‌روزرسانی مستقیم با update (دور زدن سیگنال‌ها)
            User.objects.filter(id=recipient_user.id).update(wallet=F('wallet') + amount)

            # خواندن مقدار جدید از دیتابیس
            recipient_user.refresh_from_db()

            total_transferred += amount
            transferred_details.append(
                f"{role}: {recipient_user.get_full_name()} (+{amount:,} تومان) - موجودی جدید: {recipient_user.wallet:,}"
            )

        # بروزرسانی وضعیت کمیسیون
        commission.status = Commission.Status.WALLET_TRANSFERRED
        commission.wallet_transferred_at = timezone.now()
        commission.wallet_transferred_by = user
        commission.save(update_fields=['status', 'wallet_transferred_at', 'wallet_transferred_by'])

    # پیام موفقیت
    messages.success(
        request,
        f'✅ سهم‌های کمیسیون با موفقیت به کیف پول گیرندگان واریز شد.\n'
        f'مبلغ کل: {commission.total_commission:,} تومان\n'
        f'گیرندگان:\n' + '\n'.join(transferred_details)
    )

    # ثبت لاگ
    if commission.contract and commission.contract.process:
        ProcessLog.objects.create(
            process=commission.contract.process,
            action=ProcessLog.ActionType.PROCESS_CLOSED,
            description=f'واریز کمیسیون به کیف پول توسط {user.get_full_name()} - مبلغ {commission.total_commission:,} تومان',
            performed_by=user,
            new_value='wallet_transferred'
        )


    return redirect('transaction:commission_detail', pk=commission.id)


@login_required
def commission_pay(request, pk):
    """
    ثبت پرداخت مستقیم کمیسیون (روش قدیمی - برای تسویه نقدی)
    دسترسی: accountant
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    commission = get_object_or_404(Commission, pk=pk)

    if commission.status == Commission.Status.PAID:
        messages.warning(request, 'این کمیسیون قبلاً تسویه کامل شده است.')
        return redirect('transaction:commission_detail', pk=commission.id)

    if commission.status == Commission.Status.PENDING:
        messages.warning(request, 'لطفاً ابتدا کمیسیون را محاسبه کنید.')
        return redirect('transaction:commission_calculate', pk=commission.id)

    # اگر قبلاً به کیف پول واریز شده، پرداخت مستقیم مجاز نیست
    if commission.status == Commission.Status.WALLET_TRANSFERRED:
        messages.warning(
            request,
            'این کمیسیون قبلاً به کیف پول واریز شده است. برای تسویه نقدی، '
            'لطفاً از بخش درخواست‌های برداشت استفاده کنید.'
        )
        return redirect('transaction:commission_detail', pk=commission.id)

    if request.method == 'POST':
        form = CommissionPayForm(request.POST, request.FILES)
        if form.is_valid():
            payment_type = form.cleaned_data.get('payment_type')
            payment_notes = form.cleaned_data.get('payment_notes')

            if payment_type == 'full':
                commission.mark_as_paid(
                    accountant=user,
                    receipt=request.FILES.get('payment_receipt'),
                    notes=payment_notes
                )
                messages.success(
                    request,
                    f'✅ کمیسیون با مبلغ {commission.total_commission:,} تومان تسویه کامل شد.'
                )
            else:
                commission.mark_as_partial_paid(notes=payment_notes)
                messages.warning(request, '⚠️ کمیسیون به‌صورت ناقص تسویه شد.')

            return redirect('transaction:commission_detail', pk=commission.id)
        else:
            messages.error(request, 'خطا در ثبت پرداخت. لطفاً فرم را بررسی کنید.')
    else:
        form = CommissionPayForm()

    context = {
        'title': f'ثبت پرداخت کمیسیون - {commission.customer.full_name if commission.customer else "نامشخص"}',
        'form': form,
        'commission': commission,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/commission_pay.html', context)


@login_required
def commission_settings_update(request):
    """
    بروزرسانی تنظیمات درصدهای کمیسیون
    دسترسی: accountant
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_settings"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    settings = CommissionSetting.get_default_settings()

    if request.method == 'POST':
        form = CommissionSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            settings = form.save(commit=False)
            settings.updated_by = user
            settings.save()
            messages.success(request, 'تنظیمات کمیسیون با موفقیت بروزرسانی شد.')
            return redirect('transaction:commission_dashboard')
        else:
            messages.error(request, 'خطا در بروزرسانی تنظیمات. لطفاً فرم را بررسی کنید.')
    else:
        form = CommissionSettingsForm(instance=settings)

    context = {
        'title': 'تنظیمات کمیسیون',
        'form': form,
        'settings': settings,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/commission_settings.html', context)


# ============================================================
# 💳 درخواست برداشت از کیف پول - ویوها
# ============================================================

# transaction/views.py

@login_required
def withdrawal_request_create(request):
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_settings"
    )
    current_balance = user.wallet or 0

    if request.method == 'POST':
        form = WithdrawalRequestForm(request.POST, user=user)
        if form.is_valid():
            amount = form.cleaned_data['amount']

            if amount > current_balance:
                messages.error(request, 'موجودی کیف پول شما کافی نیست.')
                return redirect('transaction:withdrawal_request_create')

            # ✅ کسر مبلغ از کیف پول در زمان ثبت درخواست
            from django.db import transaction
            with transaction.atomic():
                # کسر از کیف پول
                user.wallet = user.wallet - amount
                user.save(update_fields=['wallet'])

                # ثبت درخواست
                withdrawal = form.save(commit=False)
                withdrawal.user = user
                withdrawal.bank_name = user.bank_name or ''
                withdrawal.account_number = user.bank_account_number or ''
                withdrawal.card_number = user.bank_card_number or ''
                withdrawal.sheba_number = user.bank_sheba_number or ''
                withdrawal.status = WithdrawalRequest.Status.PENDING  # وضعیت در انتظار
                withdrawal.save()

            messages.success(
                request,
                f'✅ درخواست برداشت به مبلغ {amount:,} تومان با موفقیت ثبت شد و از کیف پول کسر گردید. '
                'در انتظار تأیید واحد حسابداری.'
            )
            return redirect('transaction:withdrawal_request_list_user')
    else:
        form = WithdrawalRequestForm(user=user)

    context = {
        'title': 'ثبت درخواست برداشت',
        'form': form,
        'current_balance': user.wallet or 0,  # موجودی جدید بعد از کسر
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/withdrawal_request_create.html', context)


@login_required
def withdrawal_request_list_user(request):
    """
    لیست درخواست‌های برداشت کاربر جاری
    """
    user = request.user
    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_settings"
    )

    requests = WithdrawalRequest.objects.filter(
        user=user
    ).order_by('-created_at')

    paginator = Paginator(requests, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'title': 'درخواست‌های برداشت من',
        'requests': page_obj,
        'current_balance': user.wallet or 0,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/withdrawal_request_list_user.html', context)


@login_required
def withdrawal_request_list_admin(request):
    """
    لیست تمام درخواست‌های برداشت برای واحد حسابداری
    دسترسی: accountant
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    pending_requests = WithdrawalRequest.objects.filter(
        status=WithdrawalRequest.Status.PENDING
    ).select_related('user').order_by('-created_at')

    approved_requests = WithdrawalRequest.objects.filter(
        status=WithdrawalRequest.Status.APPROVED
    ).select_related('user', 'reviewed_by').order_by('-reviewed_at')

    paid_requests = WithdrawalRequest.objects.filter(
        status=WithdrawalRequest.Status.PAID
    ).select_related('user', 'reviewed_by').order_by('-updated_at')

    rejected_requests = WithdrawalRequest.objects.filter(
        status=WithdrawalRequest.Status.REJECTED
    ).select_related('user', 'reviewed_by').order_by('-reviewed_at')

    stats = {
        'pending': pending_requests.count(),
        'approved': approved_requests.count(),
        'paid': paid_requests.count(),
        'rejected': rejected_requests.count(),
        'total_pending_amount': sum([r.amount for r in pending_requests]),
        'total_approved_amount': sum([r.amount for r in approved_requests]),
        'total_paid_amount': sum([r.amount for r in paid_requests]),
    }

    context = {
        'title': 'مدیریت درخواست‌های برداشت',
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'paid_requests': paid_requests,
        'rejected_requests': rejected_requests,
        'stats': stats,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/withdrawal_request_list_admin.html', context)

@login_required
def withdrawal_request_approve(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    withdrawal = get_object_or_404(
        WithdrawalRequest.objects.select_related('user'),
        pk=pk,
        status=WithdrawalRequest.Status.PENDING
    )

    if request.method == 'POST':
        # ✅ فقط تایید (بدون فرم)
        try:
            with db_transaction.atomic():
                withdrawal.approve(reviewer=user)
                messages.success(
                    request,
                    f'✅ درخواست برداشت {withdrawal.user.get_full_name()} به مبلغ '
                    f'{withdrawal.amount:,} تومان تایید شد.'
                )

                # ثبت لاگ
                ProcessLog.objects.create(
                    process=None,
                    action=ProcessLog.ActionType.PROCESS_CLOSED,
                    description=f'برداشت از کیف پول {withdrawal.user.get_full_name()} به مبلغ {withdrawal.amount:,} تومان - تایید توسط {user.get_full_name()}',
                    performed_by=user,
                    new_value='withdrawal_approved'
                )

                return redirect('transaction:withdrawal_request_list_admin')

        except Exception as e:
            messages.error(request, f'خطا: {str(e)}')

    context = {
        'title': f'تایید درخواست برداشت - {withdrawal.user.get_full_name()}',
        'withdrawal': withdrawal,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/withdrawal_request_approve.html', context)


@login_required
def withdrawal_request_reject(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    withdrawal = get_object_or_404(
        WithdrawalRequest.objects.select_related('user'),
        pk=pk,
        status=WithdrawalRequest.Status.PENDING
    )

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'لطفاً دلیل رد درخواست را وارد کنید.')
            return redirect('transaction:withdrawal_request_reject', pk=withdrawal.id)

        try:
            with db_transaction.atomic():
                # ✅ برگشت مبلغ به کیف پول
                user_obj = withdrawal.user
                user_obj.wallet = (user_obj.wallet or 0) + withdrawal.amount
                user_obj.save(update_fields=['wallet'])

                # رد درخواست
                withdrawal.reject(reviewer=user, reason=reason)

                messages.warning(
                    request,
                    f'⚠️ درخواست برداشت {withdrawal.user.get_full_name()} به مبلغ '
                    f'{withdrawal.amount:,} تومان رد شد. مبلغ به کیف پول برگشت داده شد. دلیل: {reason}'
                )

                return redirect('transaction:withdrawal_request_list_admin')

        except Exception as e:
            messages.error(request, f'خطا: {str(e)}')

    context = {
        'title': f'رد درخواست برداشت - {withdrawal.user.get_full_name()}',
        'withdrawal': withdrawal,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/withdrawal_request_reject.html', context)


@login_required
def withdrawal_request_pay(request, pk):
    """
    ثبت پرداخت نهایی درخواست برداشت (بارگذاری رسید)
    دسترسی: accountant
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "commission_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    withdrawal = get_object_or_404(
        WithdrawalRequest.objects.select_related('user'),
        pk=pk,
        status=WithdrawalRequest.Status.APPROVED
    )

    if request.method == 'POST':
        receipt = request.FILES.get('payment_receipt')
        note = request.POST.get('note', '').strip()

        if not receipt:
            messages.error(request, 'لطفاً فایل رسید پرداخت را بارگذاری کنید.')
            return redirect('transaction:withdrawal_request_pay', pk=withdrawal.id)

        withdrawal.mark_as_paid(receipt=receipt, note=note)

        messages.success(
            request,
            f'✅ پرداخت درخواست برداشت {withdrawal.user.get_full_name()} به مبلغ '
            f'{withdrawal.amount:,} تومان ثبت شد.'
        )

        return redirect('transaction:withdrawal_request_list_admin')

    context = {
        'title': f'ثبت پرداخت برداشت - {withdrawal.user.get_full_name()}',
        'withdrawal': withdrawal,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/withdrawal_request_pay.html', context)


# ============================================================
# 📞 خدمات پس از فروش - ویوها (دست نخورده)
# ============================================================
# transaction/views.py

@login_required
def aftersales_dashboard(request):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "aftersales_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    pending_services = AfterSalesService.objects.filter(
        contact_status=AfterSalesService.ContactStatus.PENDING
    ).select_related(
        'contract', 'contract__customer', 'contract__customer__user',
        'contract__property_ref', 'contract__source_visit',
        'contract__process',  # ✅ اضافه شد
    ).order_by('-created_at')

    follow_up_services = AfterSalesService.objects.filter(
        contact_status=AfterSalesService.ContactStatus.FOLLOW_UP
    ).select_related(
        'contract', 'contract__customer', 'contract__property_ref',
        'contract__process',  # ✅ اضافه شد
    ).order_by('next_follow_up_date')

    contacted_services = AfterSalesService.objects.filter(
        contact_status=AfterSalesService.ContactStatus.CONTACTED
    ).select_related(
        'contract', 'contract__customer',
        'contract__process',  # ✅ اضافه شد
    ).order_by('-contact_date')

    closed_services = AfterSalesService.objects.filter(
        is_closed=True
    ).select_related(
        'contract', 'contract__customer',
        'contract__process',  # ✅ اضافه شد
    ).order_by('-closed_at')

    stats = {
        'pending': pending_services.count(),
        'follow_up': follow_up_services.count(),
        'contacted': contacted_services.count(),
        'closed': closed_services.count(),
        'satisfied': AfterSalesService.objects.filter(
            satisfaction=AfterSalesService.Satisfaction.SATISFIED
        ).count(),
        'unsatisfied': AfterSalesService.objects.filter(
            satisfaction=AfterSalesService.Satisfaction.UNSATISFIED
        ).count(),
        'satisfied_owner': AfterSalesService.objects.filter(
            satisfaction_owner=AfterSalesService.Satisfaction.SATISFIED
        ).count(),
        'unsatisfied_owner': AfterSalesService.objects.filter(
            satisfaction_owner=AfterSalesService.Satisfaction.UNSATISFIED
        ).count(),
        'new_referrals': AfterSalesService.objects.filter(new_referral=True).count(),
        'loyal_customers': AfterSalesService.objects.filter(loyal_customer=True).count(),
    }

    context = {
        'title': 'داشبورد خدمات پس از فروش',
        'pending_services': pending_services,
        'follow_up_services': follow_up_services,
        'contacted_services': contacted_services,
        'closed_services': closed_services,
        'stats': stats,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/aftersales_dashboard.html', context)


@login_required
def aftersales_detail(request, pk):
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "aftersales_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    aftersales = get_object_or_404(
        AfterSalesService.objects.select_related(
            'contract', 'contract__customer', 'contract__customer__user',
            'contract__property_ref', 'handled_by',
            'contract__process',  # ✅ اضافه شد
        ),
        pk=pk
    )

    # دریافت اطلاعات مالک فایل
    property_owner = aftersales.property_owner

    context = {
        'title': f'جزئیات خدمات پس از فروش - {aftersales.customer.full_name if aftersales.customer else "نامشخص"}',
        'aftersales': aftersales,
        'property_owner': property_owner,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/aftersales_detail.html', context)


# transaction/views.py

@login_required
def aftersales_update(request, pk):
    """
    بروزرسانی خدمات پس از فروش (ثبت تماس، پیگیری و ...)
    دسترسی: callcenter
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "aftersales_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    aftersales = get_object_or_404(AfterSalesService, pk=pk)

    if request.method == 'POST':
        form = AfterSalesForm(request.POST, instance=aftersales)
        if form.is_valid():
            aftersales = form.save(commit=False)
            aftersales.handled_by = user

            # ✅ اگر وضعیت تماس به CONTACTED تغییر کرد و تاریخ تماس خالی بود، تاریخ را ثبت کن
            if aftersales.contact_status == AfterSalesService.ContactStatus.CONTACTED:
                if not aftersales.contact_date:
                    aftersales.contact_date = timezone.now()
                # اگر کاربر وضعیت را به CONTACTED تغییر داد، پرونده را باز در نظر بگیرید
                aftersales.is_closed = False

            # ✅ اگر وضعیت تماس به CLOSED تغییر کرد، تاریخ بسته شدن را ثبت کن
            elif aftersales.contact_status == AfterSalesService.ContactStatus.CLOSED:
                aftersales.is_closed = True
                if not aftersales.closed_at:
                    aftersales.closed_at = timezone.now()
                # برای بسته شدن، اگر تاریخ تماس خالی بود، زمان حال را ثبت کن
                if not aftersales.contact_date:
                    aftersales.contact_date = timezone.now()

            # ✅ اگر وضعیت FOLLOW_UP است، پرونده باز بماند
            elif aftersales.contact_status == AfterSalesService.ContactStatus.FOLLOW_UP:
                aftersales.is_closed = False

            aftersales.save()
            messages.success(request, 'خدمات پس از فروش با موفقیت بروزرسانی شد.')
            return redirect('transaction:aftersales_detail', pk=aftersales.id)
        else:
            messages.error(request, 'خطا در بروزرسانی. لطفاً فرم را بررسی کنید.')
    else:
        form = AfterSalesForm(instance=aftersales)

    context = {
        'title': f'بروزرسانی خدمات پس از فروش - {aftersales.customer.full_name if aftersales.customer else "نامشخص"}',
        'form': form,
        'aftersales': aftersales,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/aftersales_update.html', context)


# ============================================================
# 📂 آرشیو خدمات پس از فروش (تماس گرفته شده و بسته شده)
# ============================================================

@login_required
def aftersales_archive(request):
    """
    نمایش لیست پرونده‌های تماس گرفته شده و بسته شده (آرشیو)
    دسترسی: callcenter
    """
    user = request.user

    permission, perimissin_list, perimissin_group = views_permissions(
        user, "aftersales_dashboard"
    )
    if not permission:
        messages.error(request, 'شما دسترسی به این بخش را ندارید')
        return redirect('site_profile:page_404')

    # دریافت پرونده‌های تماس گرفته شده (به جز بسته شده‌ها)
    contacted_services = AfterSalesService.objects.filter(
        contact_status__in=[
            AfterSalesService.ContactStatus.CONTACTED,
            AfterSalesService.ContactStatus.FOLLOW_UP
        ],
        is_closed=False
    ).select_related(
        'contract', 'contract__customer', 'contract__customer__user',
        'contract__property_ref', 'handled_by',
        'contract__process',
    ).order_by('-contact_date')

    # دریافت پرونده‌های بسته شده
    closed_services = AfterSalesService.objects.filter(
        is_closed=True
    ).select_related(
        'contract', 'contract__customer', 'contract__customer__user',
        'contract__property_ref', 'handled_by',
        'contract__process',
    ).order_by('-closed_at')

    # فیلتر بر اساس جستجو
    search = request.GET.get('search', '')
    if search:
        contacted_services = contacted_services.filter(
            Q(contract__customer__user__first_name__icontains=search) |
            Q(contract__customer__user__last_name__icontains=search) |
            Q(contract__customer__user__mobile__icontains=search) |
            Q(contract__property_ref__title__icontains=search)
        )
        closed_services = closed_services.filter(
            Q(contract__customer__user__first_name__icontains=search) |
            Q(contract__customer__user__last_name__icontains=search) |
            Q(contract__customer__user__mobile__icontains=search) |
            Q(contract__property_ref__title__icontains=search)
        )

    # صفحه‌بندی
    contacted_paginator = Paginator(contacted_services, 15)
    contacted_page = request.GET.get('contacted_page')
    contacted_page_obj = contacted_paginator.get_page(contacted_page)

    closed_paginator = Paginator(closed_services, 15)
    closed_page = request.GET.get('closed_page')
    closed_page_obj = closed_paginator.get_page(closed_page)

    stats = {
        'total_contacted': contacted_services.count(),
        'total_closed': closed_services.count(),
        'total_all': AfterSalesService.objects.count(),
    }

    context = {
        'title': 'آرشیو خدمات پس از فروش',
        'contacted_services': contacted_page_obj,
        'closed_services': closed_page_obj,
        'stats': stats,
        'search': search,
        'this_user': user,
        'perimissin_list': perimissin_list,
        'perimissin_group': perimissin_group,
    }
    return render(request, 'transaction/aftersales_archive.html', context)


@login_required
def aftersales_fast_follow_up(request):
    if not is_ajax(request):
        return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'})

    aftersales_id = request.POST.get('aftersales_id')
    if not aftersales_id:
        return JsonResponse({'success': False, 'error': 'شناسه خدمات پس از فروش ارسال نشده است'})

    try:
        aftersales = AfterSalesService.objects.get(pk=aftersales_id)
        aftersales.contact_status = AfterSalesService.ContactStatus.CONTACTED
        aftersales.contact_date = timezone.now()
        aftersales.save()
        return JsonResponse({
            'success': True,
            'message': 'پیگیری با موفقیت ثبت شد.',
            'contact_date': aftersales.contact_date.strftime('%Y/%m/%d %H:%M')
        })
    except AfterSalesService.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'خدمات پس از فروش یافت نشد'})