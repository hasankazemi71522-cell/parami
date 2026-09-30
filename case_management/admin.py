# case_management/admin.py

from django.contrib import admin
from .models import CustomerProcess, IntroductionReport, Visit, ProcessLog, SupervisorAlert


@admin.register(CustomerProcess)
class CustomerProcessAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'expert', 'supervisor', 'status', 'assigned_at', 'contact_deadline']
    list_filter = ['status', 'assigned_at', 'supervisor']
    search_fields = ['customer__user__first_name', 'customer__user__last_name', 'expert__username']
    readonly_fields = ['assigned_at', 'contact_deadline', 'intro_deadline', 'visit_result_deadline']
    raw_id_fields = ['customer', 'expert', 'supervisor']


@admin.register(IntroductionReport)
class IntroductionReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'process', 'property_ref', 'result', 'created_at']
    list_filter = ['result', 'created_at']
    search_fields = ['process__customer__user__first_name', 'property_ref__title']


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ['id', 'process', 'property_ref', 'status', 'scheduled_time', 'done_at', 'negotiation_requested']
    list_filter = ['status', 'scheduled_time', 'negotiation_requested']
    search_fields = ['process__customer__user__first_name', 'property_ref__title']


@admin.register(ProcessLog)
class ProcessLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'process', 'action', 'performed_by', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['process__customer__user__first_name']


@admin.register(SupervisorAlert)
class SupervisorAlertAdmin(admin.ModelAdmin):
    list_display = ['id', 'process', 'alert_type', 'is_read', 'created_at']
    list_filter = ['alert_type', 'is_read', 'created_at']