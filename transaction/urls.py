# transaction/urls.py

from django.urls import path
from . import views

app_name = 'transaction'

urlpatterns = [
    # ==========================================================
    # 📄 واحد قرارداد
    # ==========================================================
    path('contract/dashboard/', views.contract_dashboard, name='contract_dashboard'),
    path('contract/<uuid:pk>/detail/', views.contract_detail, name='contract_detail'),
    path('contract/<uuid:pk>/update/', views.contract_update, name='contract_update'),

    # ==========================================================
    # 💰 واحد حسابداری - مدیریت کمیسیون
    # ==========================================================
    path('commission/dashboard/', views.commission_dashboard, name='commission_dashboard'),
    path('commission/<uuid:pk>/detail/', views.commission_detail, name='commission_detail'),
    path('commission/<uuid:pk>/calculate/', views.commission_calculate, name='commission_calculate'),
    path('commission/<uuid:pk>/pay/', views.commission_pay, name='commission_pay'),
    path('commission/settings/update/', views.commission_settings_update, name='commission_settings_update'),

    # ✅ واریز کمیسیون به کیف پول (روش جدید)
    path('commission/<uuid:pk>/transfer-to-wallet/', views.commission_transfer_to_wallet, name='commission_transfer_to_wallet'),

    # ==========================================================
    # 💳 درخواست برداشت از کیف پول
    # ==========================================================

    # ----- برای کاربران عادی (ثبت درخواست و مشاهده وضعیت) -----
    path('withdrawal/create/', views.withdrawal_request_create, name='withdrawal_request_create'),
    path('withdrawal/my-requests/', views.withdrawal_request_list_user, name='withdrawal_request_list_user'),

    # ----- برای واحد حسابداری (مدیریت درخواست‌ها) -----
    path('withdrawal/admin/list/', views.withdrawal_request_list_admin, name='withdrawal_request_list_admin'),
    path('withdrawal/<uuid:pk>/approve/', views.withdrawal_request_approve, name='withdrawal_request_approve'),
    path('withdrawal/<uuid:pk>/reject/', views.withdrawal_request_reject, name='withdrawal_request_reject'),
    path('withdrawal/<uuid:pk>/pay/', views.withdrawal_request_pay, name='withdrawal_request_pay'),

    # ==========================================================
    # 📞 خدمات پس از فروش
    # ==========================================================
    path('aftersales/dashboard/', views.aftersales_dashboard, name='aftersales_dashboard'),
    path('aftersales/<uuid:pk>/detail/', views.aftersales_detail, name='aftersales_detail'),
    path('aftersales/<uuid:pk>/update/', views.aftersales_update, name='aftersales_update'),
    path('aftersales/archive/', views.aftersales_archive, name='aftersales_archive'),

    # ==========================================================
    # ⚡ AJAX
    # ==========================================================
    path('aftersales/fast-follow-up/', views.aftersales_fast_follow_up, name='aftersales_fast_follow_up'),
]