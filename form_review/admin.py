from django.contrib import admin
from .models import Rejection, RejectionReply


class RejectionReplyInline(admin.TabularInline):
    model = RejectionReply
    extra = 0
    fields = ('user', 'text', 'reply_type', 'attachment', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Rejection)
class RejectionAdmin(admin.ModelAdmin):
    list_display = ('form_instance', 'level', 'rejected_by', 'assigned_to', 'status', 'created_at')
    list_filter = ('level', 'status', 'created_at')
    search_fields = ('form_instance__title', 'reason', 'rejected_by__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RejectionReplyInline]
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('form_instance', 'level', 'instance_field', 'step_number', 'reason')
        }),
        ('کاربران', {
            'fields': ('rejected_by', 'assigned_to')
        }),
        ('وضعیت و زمان', {
            'fields': ('status', 'deadline_hours', 'deadline_at', 'parent', 'created_at', 'updated_at')
        }),
    )


@admin.register(RejectionReply)
class RejectionReplyAdmin(admin.ModelAdmin):
    list_display = ('rejection', 'user', 'reply_type', 'created_at')
    list_filter = ('reply_type', 'created_at')
    search_fields = ('text', 'user__username')
    readonly_fields = ('created_at',)