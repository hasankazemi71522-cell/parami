# case_management/forms.py

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import CustomerProcess, Visit, IntroductionReport

User = get_user_model()

class AssignCustomerForm(forms.Form):
    customer_id = forms.UUIDField(
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    expert_id = forms.IntegerField(
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    priority = forms.IntegerField(
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 10})
    )


class ContactForm(forms.ModelForm):
    class Meta:
        model = CustomerProcess
        fields = []

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.contact_made_at = timezone.now()
        instance.status = CustomerProcess.Status.CONTACTED
        instance.set_intro_deadline()
        if commit:
            instance.save()
        return instance


class IntroReportForm(forms.ModelForm):
    class Meta:
        model = IntroductionReport
        fields = ['property_ref', 'result', 'expert_note']
        widgets = {
            'property_ref': forms.Select(attrs={'class': 'form-select'}),
            'result': forms.Select(attrs={'class': 'form-select'}),
            'expert_note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class VisitCreateForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['property_ref']
        widgets = {
            'property_ref': forms.Select(attrs={'class': 'form-select'}),
        }


class VisitScheduleForm(forms.ModelForm):
    scheduled_time = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )

    class Meta:
        model = Visit
        fields = ['scheduled_time']


class VisitResultForm(forms.ModelForm):
    negotiation_manager = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Visit
        fields = ['visit_result', 'negotiation_requested', 'negotiation_manager']
        widgets = {
            'visit_result': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'negotiation_requested': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        supervisor = kwargs.pop('supervisor', None)
        super().__init__(*args, **kwargs)
        if supervisor:
            self.fields['negotiation_manager'].queryset = User.objects.filter(
                is_active=True,
                user_roles__role__name='supervisor',
                user_roles__is_active=True
            ).distinct()