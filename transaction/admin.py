# transaction/admin.py

from django.contrib import admin
from .models import Contract, CommissionSetting, Commission, AfterSalesService, WithdrawalRequest


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['id', 'contract_number', 'customer_name', 'property_title', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'contract_type']
    search_fields = [
        'contract_number',
        'process__customer__user__first_name',
        'process__customer__user__last_name',
        'process__customer__user__mobile'
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['process', 'customer', 'property_ref', 'source_visit']

    def customer_name(self, obj):
        customer = obj.get_customer()
        return customer.full_name if customer else "---"
    customer_name.short_description = 'نام مشتری'

    def property_title(self, obj):
        prop = obj.get_property()
        return prop.title if prop else "---"
    property_title.short_description = 'ملک'


@admin.register(CommissionSetting)
class CommissionSettingAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'property_register_share', 'customer_register_share',
        'expert_share', 'supervisor_share', 'meeting_manager_share',
        'updated_at', 'updated_by'
    ]
    readonly_fields = ['updated_at']
    raw_id_fields = ['updated_by']

    def has_add_permission(self, request):
        # فقط یک رکورد مجاز است
        return False


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'contract', 'customer_name', 'total_commission',
        'status', 'wallet_transferred_at', 'paid_at'
    ]
    list_filter = ['status', 'created_at', 'paid_at', 'wallet_transferred_at']
    search_fields = [
        'contract__process__customer__user__first_name',
        'contract__process__customer__user__last_name',
        'contract__process__customer__user__mobile'
    ]
    readonly_fields = ['created_at', 'updated_at', 'total_amount', 'total_commission']
    raw_id_fields = ['contract', 'accountant', 'wallet_transferred_by']

    def customer_name(self, obj):
        customer = obj.customer
        return customer.full_name if customer else "---"
    customer_name.short_description = 'مشتری'


@admin.register(AfterSalesService)
class AfterSalesServiceAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'customer_name', 'satisfaction', 'contact_status',
        'contact_date', 'new_referral', 'loyal_customer', 'is_closed'
    ]
    list_filter = ['satisfaction', 'contact_status', 'new_referral', 'loyal_customer', 'is_closed']
    search_fields = [
        'contract__process__customer__user__first_name',
        'contract__process__customer__user__last_name',
        'contract__process__customer__user__mobile'
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['contract', 'handled_by']

    def customer_name(self, obj):
        customer = obj.customer
        return customer.full_name if customer else "---"
    customer_name.short_description = 'نام مشتری'


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'amount', 'status',
        'bank_name', 'created_at', 'reviewed_at'
    ]
    list_filter = ['status', 'created_at', 'reviewed_at']
    search_fields = [
        'user__first_name', 'user__last_name', 'user__mobile',
        'bank_name', 'account_number', 'card_number'
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user', 'reviewed_by']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('user', 'amount', 'status')
        }),
        ('اطلاعات بانکی', {
            'fields': ('bank_name', 'account_number', 'card_number', 'sheba_number')
        }),
        ('بررسی و پرداخت', {
            'fields': ('reviewed_by', 'reviewed_at', 'payment_receipt', 'note')
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        # پس از ایجاد، فیلدهای اصلی را فقط خواندنی می‌کنیم
        if obj:
            return ['user', 'amount', 'bank_name', 'account_number', 'card_number', 'sheba_number', 'created_at', 'updated_at']
        return ['created_at', 'updated_at']