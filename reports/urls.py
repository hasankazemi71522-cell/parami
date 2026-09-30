# reports/urls.py

from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # داشبورد
    path('dashboard/', views.report_dashboard, name='dashboard'),

    # آمار کلی
    path('statistics/', views.statistics_report, name='statistics'),

    # گزارش فرم‌ها
    path('forms/', views.form_report, name='form_report'),
    path('forms/<int:form_id>/', views.form_detail_report, name='form_detail_report'),

    # پرکاربردترین فرم‌ها
    path('popular-forms/', views.popular_forms_report, name='popular_forms'),

    # عملکرد کاربران
    path('users/', views.user_performance_report, name='user_performance'),

    # کاربران تاخیردار
    path('top-overdue-users/', views.top_overdue_users_report, name='top_overdue_users'),

    # گزارش تاخیرها
    path('overdue/', views.overdue_report, name='overdue_report'),

    # فرم‌های بدون فعالیت
    path('inactive-forms/', views.inactive_forms_report, name='inactive_forms'),

    # روند تکمیل
    path('completion-trend/', views.completion_trend_report, name='completion_trend'),

    # تحلیل گردش کار
    path('workflow-analysis/', views.workflow_analysis_report, name='workflow_analysis'),

    # پیش‌بینی تکمیل
    path('completion-prediction/', views.completion_prediction_report, name='completion_prediction'),

    # خروجی Excel
    path('export/excel/<str:report_type>/', views.export_excel, name='export_excel'),
]