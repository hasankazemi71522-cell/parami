# transaction/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import jdatetime
from decimal import Decimal

from .models import Contract, Commission, CommissionSetting, AfterSalesService, WithdrawalRequest


# ============================================================
# 📄 فرم بروزرسانی قرارداد
# ============================================================

class ContractUpdateForm(forms.ModelForm):
    """
    فرم بروزرسانی قرارداد با فیلدهای جداگانه تاریخ شمسی
    تاریخ‌ها در دیتابیس به صورت میلادی ذخیره می‌شوند
    """

    # تاریخ امضای مشتری
    customer_sign_year = forms.IntegerField(
        required=False,
        min_value=1300,
        max_value=1450,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'سال'}),
        label='سال امضای مشتری'
    )
    customer_sign_month = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ماه'}),
        label='ماه امضای مشتری'
    )
    customer_sign_day = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=31,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'روز'}),
        label='روز امضای مشتری'
    )
    customer_sign_hour = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=23,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ساعت'}),
        label='ساعت امضای مشتری'
    )
    customer_sign_minute = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=59,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'دقیقه'}),
        label='دقیقه امضای مشتری'
    )

    # تاریخ امضای طرف دیگر
    other_sign_year = forms.IntegerField(
        required=False,
        min_value=1300,
        max_value=1450,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'سال'}),
        label='سال امضای طرف دیگر'
    )
    other_sign_month = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ماه'}),
        label='ماه امضای طرف دیگر'
    )
    other_sign_day = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=31,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'روز'}),
        label='روز امضای طرف دیگر'
    )
    other_sign_hour = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=23,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ساعت'}),
        label='ساعت امضای طرف دیگر'
    )
    other_sign_minute = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=59,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'دقیقه'}),
        label='دقیقه امضای طرف دیگر'
    )

    # تاریخ پایان اجاره
    rent_end_year = forms.IntegerField(
        required=False,
        min_value=1300,
        max_value=1450,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'سال'}),
        label='سال پایان اجاره'
    )
    rent_end_month = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ماه'}),
        label='ماه پایان اجاره'
    )
    rent_end_day = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=31,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'روز'}),
        label='روز پایان اجاره'
    )
    rent_end_hour = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=23,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ساعت'}),
        label='ساعت پایان اجاره'
    )
    rent_end_minute = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=59,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'دقیقه'}),
        label='دقیقه پایان اجاره'
    )

    class Meta:
        model = Contract
        fields = [
            'status',
            'contract_number',
            'is_confidential',
            'signature_date_customer',
            'signature_date_other',
            'draft_file',
            'signed_file',
            'supporting_documents',
            'review_notes',
            'contract_notes',
            'contract_type',
            'final_amount',
            'rent_amount',
            'mortgage_amount',
            'rent_end_date',
            'commission_amount',
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
            'is_confidential': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'signature_date_customer': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'signature_date_other': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'draft_file': forms.FileInput(attrs={'class': 'form-control'}),
            'signed_file': forms.FileInput(attrs={'class': 'form-control'}),
            'supporting_documents': forms.FileInput(attrs={'class': 'form-control'}),
            'review_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contract_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contract_type': forms.Select(attrs={'class': 'form-select'}),
            'final_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'rent_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'mortgage_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'rent_end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'commission_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self._populate_jalali_fields('signature_date_customer', 'customer_sign')
            self._populate_jalali_fields('signature_date_other', 'other_sign')
            self._populate_jalali_fields('rent_end_date', 'rent_end')

    def _populate_jalali_fields(self, field_name, prefix):
        value = getattr(self.instance, field_name, None)
        if value:
            if timezone.is_aware(value):
                value = timezone.make_naive(value)

            try:
                jd = jdatetime.date.fromgregorian(
                    year=value.year,
                    month=value.month,
                    day=value.day
                )
                self.initial[f'{prefix}_year'] = jd.year
                self.initial[f'{prefix}_month'] = jd.month
                self.initial[f'{prefix}_day'] = jd.day
                self.initial[f'{prefix}_hour'] = value.hour
                self.initial[f'{prefix}_minute'] = value.minute
            except Exception:
                pass

    def _jalali_to_gregorian(self, year, month, day, hour=0, minute=0):
        if not all([year, month, day]):
            return None

        try:
            gregorian_date = jdatetime.date(year, month, day).togregorian()
            result = timezone.datetime(
                gregorian_date.year,
                gregorian_date.month,
                gregorian_date.day,
                hour or 0,
                minute or 0
            )
            return timezone.make_aware(result) if timezone.is_naive(result) else result
        except Exception:
            return None

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')

        customer_date = self._jalali_to_gregorian(
            cleaned_data.get('customer_sign_year'),
            cleaned_data.get('customer_sign_month'),
            cleaned_data.get('customer_sign_day'),
            cleaned_data.get('customer_sign_hour') or 0,
            cleaned_data.get('customer_sign_minute') or 0
        )
        if customer_date:
            cleaned_data['signature_date_customer'] = customer_date

        other_date = self._jalali_to_gregorian(
            cleaned_data.get('other_sign_year'),
            cleaned_data.get('other_sign_month'),
            cleaned_data.get('other_sign_day'),
            cleaned_data.get('other_sign_hour') or 0,
            cleaned_data.get('other_sign_minute') or 0
        )
        if other_date:
            cleaned_data['signature_date_other'] = other_date

        rent_end = self._jalali_to_gregorian(
            cleaned_data.get('rent_end_year'),
            cleaned_data.get('rent_end_month'),
            cleaned_data.get('rent_end_day'),
            cleaned_data.get('rent_end_hour') or 0,
            cleaned_data.get('rent_end_minute') or 0
        )
        if rent_end:
            cleaned_data['rent_end_date'] = rent_end

        contract_type = cleaned_data.get('contract_type')
        final_amount = cleaned_data.get('final_amount')

        if contract_type == 'rent':
            if not cleaned_data.get('rent_amount') and not cleaned_data.get('mortgage_amount'):
                self.add_error('rent_amount', 'برای قرارداد اجاره، حداقل مبلغ اجاره یا رهن باید وارد شود.')
            if not cleaned_data.get('rent_end_date'):
                self.add_error('rent_end_year', 'تاریخ پایان اجاره الزامی است.')

        elif contract_type in ['sale', 'partnership', 'investment']:
            if not final_amount:
                self.add_error('final_amount', 'مبلغ نهایی قرارداد الزامی است.')

        if status == Contract.Status.COMPLETED:
            if not contract_type:
                self.add_error('contract_type', 'برای تکمیل قرارداد، نوع قرارداد الزامی است.')
            if not final_amount:
                self.add_error('final_amount', 'برای تکمیل قرارداد، مبلغ نهایی الزامی است.')
            if not cleaned_data.get('signature_date_customer'):
                self.add_error('customer_sign_year', 'برای تکمیل قرارداد، تاریخ امضای مشتری الزامی است.')
            if not cleaned_data.get('signed_file'):
                self.add_error('signed_file', 'برای تکمیل قرارداد، بارگذاری فایل امضاشده الزامی است.')

        return cleaned_data


# ============================================================
# 💰 فرم محاسبه کمیسیون (اصلاح شده - فقط اعداد صحیح)
# ============================================================

class CommissionCalculateForm(forms.ModelForm):
    class Meta:
        model = Commission
        fields = [
            'property_register_share',
            'customer_register_share',
            'expert_share',
            'supervisor_share',
            'meeting_manager_share'
        ]
        widgets = {
            'property_register_share': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'
            }),
            'customer_register_share': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'
            }),
            'expert_share': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'
            }),
            'supervisor_share': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'
            }),
            'meeting_manager_share': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        total = 0

        for field in self.Meta.fields:
            value = cleaned_data.get(field)
            if value is not None:
                # اگر مقدار اعشار داشت، خطا بده
                if isinstance(value, float) and not value.is_integer():
                    self.add_error(field, 'درصد باید عدد صحیح باشد.')
                # تبدیل به عدد صحیح
                cleaned_data[field] = int(value)
                total += int(value)

        if total > 100:
            raise ValidationError('مجموع درصدها نباید از ۱۰۰ بیشتر شود.')
        if total < 0:
            raise ValidationError('مجموع درصدها نباید منفی باشد.')

        return cleaned_data


# ============================================================
# 💳 فرم ثبت پرداخت کمیسیون (روش مستقیم - قدیمی)
# ============================================================

class CommissionPayForm(forms.Form):
    PAYMENT_CHOICES = [
        ('full', 'تسویه کامل'),
        ('partial', 'تسویه ناقص'),
    ]

    payment_type = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='نوع تسویه'
    )
    payment_receipt = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label='فایل رسید پرداخت'
    )
    payment_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='یادداشت پرداخت'
    )


# ============================================================
# ⚙️ فرم تنظیمات کمیسیون (اصلاح شده - فقط اعداد صحیح)
# ============================================================

class CommissionSettingsForm(forms.ModelForm):
    class Meta:
        model = CommissionSetting
        fields = [
            'property_register_share',
            'customer_register_share',
            'expert_share',
            'supervisor_share',
            'meeting_manager_share',
            'note'
        ]
        widgets = {
            'property_register_share': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'
            }),
            'customer_register_share': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'
            }),
            'expert_share': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'
            }),
            'supervisor_share': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'
            }),
            'meeting_manager_share': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'
            }),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        total = 0

        for field in ['property_register_share', 'customer_register_share', 'expert_share', 'supervisor_share', 'meeting_manager_share']:
            value = cleaned_data.get(field)
            if value is not None:
                # اگر مقدار اعشار داشت، خطا بده
                if isinstance(value, float) and not value.is_integer():
                    self.add_error(field, 'درصد باید عدد صحیح باشد.')
                # تبدیل به عدد صحیح
                cleaned_data[field] = int(value)
                total += int(value)

        if total > 100:
            raise ValidationError('مجموع درصدها نباید از ۱۰۰ بیشتر شود.')
        if total < 0:
            raise ValidationError('مجموع درصدها نباید منفی باشد.')

        return cleaned_data


# ============================================================
# 📞 فرم خدمات پس از فروش
# ============================================================

class AfterSalesForm(forms.ModelForm):
    class Meta:
        model = AfterSalesService
        fields = [
            'contact_status',
            'satisfaction',
            'satisfaction_owner',
            'feedback',
            'feedback_owner',
            'new_referral',
            'referral_details',
            'loyal_customer',
            'notes',
            'next_follow_up_date',
            'is_closed'
        ]
        widgets = {
            'contact_status': forms.Select(attrs={'class': 'form-select'}),
            'satisfaction': forms.Select(attrs={'class': 'form-select'}),
            'satisfaction_owner': forms.Select(attrs={'class': 'form-select'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'feedback_owner': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'referral_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'next_follow_up_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local'
            }),
            'new_referral': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'loyal_customer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_closed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_closed = cleaned_data.get('is_closed')

        if is_closed:
            if not cleaned_data.get('satisfaction') or cleaned_data.get('satisfaction') == AfterSalesService.Satisfaction.NOT_CONTACTED:
                self.add_error('satisfaction', 'برای بستن پرونده، ثبت رضایت مشتری الزامی است.')
            if not cleaned_data.get('satisfaction_owner') or cleaned_data.get('satisfaction_owner') == AfterSalesService.Satisfaction.NOT_CONTACTED:
                self.add_error('satisfaction_owner', 'برای بستن پرونده، ثبت رضایت مالک فایل الزامی است.')

        return cleaned_data


# ============================================================
# 💳 فرم‌های درخواست برداشت
# ============================================================

class WithdrawalRequestForm(forms.ModelForm):
    class Meta:
        model = WithdrawalRequest
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1000',
                'step': '1000',
                'placeholder': 'مبلغ به تومان'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            balance = self.user.wallet or 0
            self.fields['amount'].label = f'مبلغ درخواستی (تومان) - موجودی: {balance:,} تومان'

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if not self.user:
            raise ValidationError('کاربر مشخص نیست.')

        balance = self.user.wallet or 0
        if amount > balance:
            raise ValidationError(f'موجودی کیف پول شما ({balance:,} تومان) کافی نیست.')

        if amount < 1000:
            raise ValidationError('حداقل مبلغ برداشت ۱,۰۰۰ تومان است.')

        return amount


class WithdrawalApproveForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        initial=True,
        widget=forms.HiddenInput()
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'یادداشت (اختیاری)'
        }),
        label='یادداشت'
    )


class WithdrawalRejectForm(forms.Form):
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'لطفاً دلیل رد درخواست را وارد کنید...'
        }),
        label='دلیل رد'
    )


# ============================================================
# 📋 فرم‌های کمکی (فیلتر و جستجو)
# ============================================================

class ContractFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[('', 'همه')] + list(Contract.Status.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    contract_type = forms.ChoiceField(
        choices=[('', 'همه')] + list(Contract.CONTRACT_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'جستجو...'})
    )


class CommissionFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[('', 'همه')] + list(Commission.Status.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )