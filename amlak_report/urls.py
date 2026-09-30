from django.urls import path
from . import views

app_name = 'amlak_report'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('customer/', views.customer_report, name='customer_report'),
    path('property/', views.property_report, name='property_report'),
    path('process/', views.process_report, name='process_report'),
    path('contract/', views.contract_report, name='contract_report'),
    path('commission/', views.commission_report, name='commission_report'),
    path('api/status-chart/', views.api_status_chart, name='api_status_chart'),
    path('api/cities/', views.get_cities_by_province, name='get_cities_by_province'),

    # خروجی‌ها
    path('export/customer/', views.export_customer_excel, name='export_customer'),
    path('export/property/', views.export_property_excel, name='export_property'),
    path('export/process/', views.export_process_excel, name='export_process'),
    path('export/contract/', views.export_contract_excel, name='export_contract'),
    path('export/commission/', views.export_commission_excel, name='export_commission'),
]