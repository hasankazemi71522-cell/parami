# estate/forms_location.py

from django import forms
from django.core.validators import FileExtensionValidator
from .models import Province, City, Neighborhood


class ProvinceForm(forms.ModelForm):
    """فرم استان"""

    class Meta:
        model = Province
        fields = ['name', 'code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام استان را وارد کنید'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'کد استان (اختیاری)'
            }),
        }


class CityForm(forms.ModelForm):
    """فرم شهرستان"""

    class Meta:
        model = City
        fields = ['name', 'province', 'code', 'center_latitude', 'center_longitude']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام شهرستان را وارد کنید'
            }),
            'province': forms.Select(attrs={
                'class': 'form-select'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'کد شهرستان (اختیاری)'
            }),
            'center_latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'عرض جغرافیایی (اختیاری)',
                'step': '0.0000001'
            }),
            'center_longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'طول جغرافیایی (اختیاری)',
                'step': '0.0000001'
            }),
        }


class NeighborhoodForm(forms.ModelForm):
    """
    فرم محله با سلکت استان و شهرستان جداگانه
    """

    # فیلد استان (برای نمایش در فرم)
    province = forms.ModelChoiceField(
        queryset=Province.objects.all().order_by('name'),
        label='استان',
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_province',
        })
    )

    # فیلد شهرستان (برای نمایش در فرم)
    city = forms.ModelChoiceField(
        queryset=City.objects.all().order_by('name'),  # همه شهرستان‌ها برای اعتبارسنجی
        label='شهرستان',
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_city',
        })
    )

    class Meta:
        model = Neighborhood
        fields = ['name', 'city', 'center_latitude', 'center_longitude']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام محله را وارد کنید'
            }),
            'center_latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'عرض جغرافیایی (اختیاری)',
                'step': '0.0000001'
            }),
            'center_longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'طول جغرافیایی (اختیاری)',
                'step': '0.0000001'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ اگر در حالت ویرایش هستیم (instance وجود دارد)
        if self.instance and self.instance.pk:
            # تنظیم استان بر اساس شهرستان موجود
            self.fields['province'].initial = self.instance.city.province.id

            # تنظیم شهرستان فعلی
            self.fields['city'].initial = self.instance.city.id

            # ✅ برای نمایش در سلکت، فقط شهرستان‌های همان استان را نشان بده
            self.fields['city'].queryset = City.objects.filter(
                province=self.instance.city.province
            ).order_by('name')
        else:
            # ✅ در حالت ایجاد جدید، همه شهرستان‌ها را نشان بده (برای اعتبارسنجی)
            self.fields['city'].queryset = City.objects.all().order_by('name')

            # تنظیم استان پیش‌فرض (اختیاری)
            # self.fields['province'].initial = None


class LocationImportForm(forms.Form):
    """
    فرم آپلود فایل اکسل برای واردات انبوه استان‌ها، شهرستان‌ها و محله‌ها
    """
    file = forms.FileField(
        label='فایل اکسل',
        validators=[FileExtensionValidator(['xlsx', 'xls'], message='فایل باید با فرمت اکسل (.xlsx یا .xls) باشد')],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls'
        })
    )

    overwrite = forms.BooleanField(
        required=False,
        label='رونویسی اطلاعات موجود؟',
        help_text='اگر فعال باشد، استان‌ها و شهرستان‌های تکراری بروزرسانی می‌شوند',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )