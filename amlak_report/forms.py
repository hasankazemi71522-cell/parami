from django import forms
from estate.models import Customer, Property, Province, City, Source, PropertyType
from case_management.models import CustomerProcess
from transaction.models import Contract, Commission
from django.contrib.auth import get_user_model

User = get_user_model()


class DateRangeForm(forms.Form):
    """فرم بازه تاریخ برای فیلتر گزارشات"""
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='از تاریخ'
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='تا تاریخ'
    )

class CustomerReportFilterForm(forms.Form):
    """فرم فیلتر گزارش مشتریان"""

    # ====== فیلدهای جستجو ======
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'جستجوی نام، موبایل...'})
    )

    # ====== فیلدهای انتخاب ======
    customer_type = forms.ChoiceField(
        choices=[('', 'همه')] + list(Customer.CustomerType.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'همه')] + list(Customer.Status.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    source = forms.ModelChoiceField(
        queryset=Source.objects.filter(is_active=True),
        required=False,
        empty_label='همه منابع',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    has_duplicate = forms.ChoiceField(
        choices=[('', 'همه'), ('yes', 'دارای تکراری'), ('no', 'بدون تکراری')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # ====== فیلدهای مکان ======
    province = forms.ModelChoiceField(
        queryset=Province.objects.all().order_by('name'),
        required=False,
        empty_label='همه استان‌ها',
        widget=forms.Select(attrs={'class': 'form-select province-select'})
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.all().order_by('name'),
        required=False,
        empty_label='همه شهرها',
        widget=forms.Select(attrs={'class': 'form-select city-select'})
    )

    # ====== فیلدهای تاریخ (جداگانه) ======
    date_from_year = forms.ChoiceField(
        required=False,
        choices=[('', 'سال')] + [(str(y), str(y)) for y in range(1400, 1451)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from_month = forms.ChoiceField(
        required=False,
        choices=[('', 'ماه')] + [(str(m), f'{m:02d}') for m in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from_day = forms.ChoiceField(
        required=False,
        choices=[('', 'روز')] + [(str(d), f'{d:02d}') for d in range(1, 32)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_to_year = forms.ChoiceField(
        required=False,
        choices=[('', 'سال')] + [(str(y), str(y)) for y in range(1400, 1451)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_to_month = forms.ChoiceField(
        required=False,
        choices=[('', 'ماه')] + [(str(m), f'{m:02d}') for m in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_to_day = forms.ChoiceField(
        required=False,
        choices=[('', 'روز')] + [(str(d), f'{d:02d}') for d in range(1, 32)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # اگر استانی انتخاب شده، شهرها را بر اساس آن فیلتر کن (برای نمایش در قالب)
        province_id = self.data.get('province') or self.initial.get('province')
        if province_id:
            self.fields['city'].queryset = City.objects.filter(province_id=province_id).order_by('name')


class PropertyReportFilterForm(forms.Form):
    """فرم فیلتر گزارش املاک"""

    # ====== فیلدهای جستجو ======
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'جستجوی عنوان، آدرس...'})
    )

    # ====== فیلدهای انتخاب ======
    property_type = forms.ModelChoiceField(
        queryset=PropertyType.objects.filter(is_active=True),
        required=False,
        empty_label='همه انواع',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'همه')] + list(Property.Status.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    contract_type = forms.ChoiceField(
        choices=[('', 'همه')] + list(Property.ContractType.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    has_duplicate = forms.ChoiceField(
        choices=[('', 'همه'), ('yes', 'دارای تکراری'), ('no', 'بدون تکراری')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # ====== فیلدهای مکان ======
    province = forms.ModelChoiceField(
        queryset=Province.objects.all().order_by('name'),
        required=False,
        empty_label='همه استان‌ها',
        widget=forms.Select(attrs={'class': 'form-select province-select'})
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.all().order_by('name'),
        required=False,
        empty_label='همه شهرها',
        widget=forms.Select(attrs={'class': 'form-select city-select'})
    )

    # ====== فیلدهای تاریخ (جداگانه) ======
    date_from_year = forms.ChoiceField(
        required=False,
        choices=[('', 'سال')] + [(str(y), str(y)) for y in range(1400, 1451)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from_month = forms.ChoiceField(
        required=False,
        choices=[('', 'ماه')] + [(str(m), f'{m:02d}') for m in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from_day = forms.ChoiceField(
        required=False,
        choices=[('', 'روز')] + [(str(d), f'{d:02d}') for d in range(1, 32)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_to_year = forms.ChoiceField(
        required=False,
        choices=[('', 'سال')] + [(str(y), str(y)) for y in range(1400, 1451)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_to_month = forms.ChoiceField(
        required=False,
        choices=[('', 'ماه')] + [(str(m), f'{m:02d}') for m in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_to_day = forms.ChoiceField(
        required=False,
        choices=[('', 'روز')] + [(str(d), f'{d:02d}') for d in range(1, 32)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        province_id = self.data.get('province') or self.initial.get('province')
        if province_id:
            self.fields['city'].queryset = City.objects.filter(province_id=province_id).order_by('name')


class ProcessReportFilterForm(forms.Form):
    """فرم فیلتر گزارش فرآیندها"""

    # ====== فیلدهای جستجو ======
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'جستجوی نام مشتری...'})
    )

    # ====== فیلدهای انتخاب ======
    status = forms.ChoiceField(
        choices=[('', 'همه')] + list(CustomerProcess.Status.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    expert = forms.ModelChoiceField(
        queryset=User.objects.filter(user_roles__role__name='expert', is_active=True).distinct(),
        required=False,
        empty_label='همه کارشناسان',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    supervisor = forms.ModelChoiceField(
        queryset=User.objects.filter(user_roles__role__name='supervisor', is_active=True).distinct(),
        required=False,
        empty_label='همه سرپرستان',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_closed = forms.ChoiceField(
        choices=[('', 'همه'), ('open', 'باز'), ('closed', 'بسته شده')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # ====== فیلدهای تاریخ (جداگانه) ======
    date_from_year = forms.ChoiceField(
        required=False,
        choices=[('', 'سال')] + [(str(y), str(y)) for y in range(1400, 1451)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from_month = forms.ChoiceField(
        required=False,
        choices=[('', 'ماه')] + [(str(m), f'{m:02d}') for m in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from_day = forms.ChoiceField(
        required=False,
        choices=[('', 'روز')] + [(str(d), f'{d:02d}') for d in range(1, 32)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_to_year = forms.ChoiceField(
        required=False,
        choices=[('', 'سال')] + [(str(y), str(y)) for y in range(1400, 1451)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_to_month = forms.ChoiceField(
        required=False,
        choices=[('', 'ماه')] + [(str(m), f'{m:02d}') for m in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_to_day = forms.ChoiceField(
        required=False,
        choices=[('', 'روز')] + [(str(d), f'{d:02d}') for d in range(1, 32)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ContractReportFilterForm(forms.Form):
    """فرم فیلتر گزارش قراردادها"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'جستجوی شماره قرارداد، نام مشتری...'})
    )
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

    # ====== فیلدهای تاریخ (جداگانه) ======
    date_from_year = forms.ChoiceField(
        required=False,
        choices=[('', 'سال')] + [(str(y), str(y)) for y in range(1400, 1451)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from_month = forms.ChoiceField(
        required=False,
        choices=[('', 'ماه')] + [(str(m), f'{m:02d}') for m in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from_day = forms.ChoiceField(
        required=False,
        choices=[('', 'روز')] + [(str(d), f'{d:02d}') for d in range(1, 32)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_to_year = forms.ChoiceField(
        required=False,
        choices=[('', 'سال')] + [(str(y), str(y)) for y in range(1400, 1451)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_to_month = forms.ChoiceField(
        required=False,
        choices=[('', 'ماه')] + [(str(m), f'{m:02d}') for m in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_to_day = forms.ChoiceField(
        required=False,
        choices=[('', 'روز')] + [(str(d), f'{d:02d}') for d in range(1, 32)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class CommissionReportFilterForm(forms.Form):
    """فرم فیلتر گزارش حسابداری"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'جستجوی نام مشتری...'})
    )
    status = forms.ChoiceField(
        choices=[('', 'همه')] + list(Commission.Status.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # ====== فیلدهای تاریخ (جداگانه) ======
    date_from_year = forms.ChoiceField(
        required=False,
        choices=[('', 'سال')] + [(str(y), str(y)) for y in range(1400, 1451)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from_month = forms.ChoiceField(
        required=False,
        choices=[('', 'ماه')] + [(str(m), f'{m:02d}') for m in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from_day = forms.ChoiceField(
        required=False,
        choices=[('', 'روز')] + [(str(d), f'{d:02d}') for d in range(1, 32)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_to_year = forms.ChoiceField(
        required=False,
        choices=[('', 'سال')] + [(str(y), str(y)) for y in range(1400, 1451)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_to_month = forms.ChoiceField(
        required=False,
        choices=[('', 'ماه')] + [(str(m), f'{m:02d}') for m in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_to_day = forms.ChoiceField(
        required=False,
        choices=[('', 'روز')] + [(str(d), f'{d:02d}') for d in range(1, 32)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )