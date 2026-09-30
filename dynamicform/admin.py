from django.contrib import admin
from django.utils.html import format_html
from .models import InputTemplate, FormTemplate, FormInput


@admin.register(InputTemplate)
class InputTemplateAdmin(admin.ModelAdmin):
    list_display = ['colored_type', 'css_class', 'wrapper_class', 'is_active']
    list_editable = ['css_class', 'wrapper_class', 'is_active']
    list_filter = ['input_type', 'is_active']
    search_fields = ['input_type', 'css_class']
    ordering = ['input_type']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('input_type',)
        }),
        ('تنظیمات استایل', {
            'fields': ('css_class', 'wrapper_class'),
            'classes': ('wide',),
        }),
        ('وضعیت', {
            'fields': ('is_active',),
        }),
    )

    def colored_type(self, obj):
        colors = {
            'text': 'blue',
            'textarea': 'purple',
            'number': 'green',
            'email': 'orange',
            'phone': 'teal',
            'date': 'red',
            'datetime': 'pink',
            'time': 'cyan',
            'select': 'brown',
            'checkbox': 'lime',
            'radio': 'olive',
            'file': 'gray',
            'image': 'indigo',
            'url': 'navy',
            'color': 'magenta',
            'password': 'darkred',
        }
        color = colors.get(obj.input_type, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_input_type_display()
        )

    colored_type.short_description = 'نوع اینپوت'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['input_type']
        return []


class FormInputInline(admin.TabularInline):
    model = FormInput
    extra = 1
    fields = [
        'input', 'field_name', 'field_title', 'order',
        'is_required', 'placeholder', 'help_text', 'default_value',
        'options', 'min_length', 'max_length', 'min_value', 'max_value',
        'max_file_size', 'allowed_extensions',
        'access_type'
    ]
    filter_horizontal = ['allowed_roles', 'allowed_users']


@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'name', 'get_allowed_roles_display', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'allowed_roles']
    search_fields = ['title', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [FormInputInline]

    fieldsets = (
        ('اطلاعات اصلی فرم', {
            'fields': ('name', 'title', 'description')
        }),
        ('دسترسی به فرم (چه نقش‌هایی می‌توانند از این فرم استفاده کنند؟)', {
            'fields': ('allowed_roles',),
            'description': 'نقش‌های مورد نظر را انتخاب کنید. اگر هیچ نقشی انتخاب نشود، همه کاربران می‌توانند از فرم استفاده کنند.',
            'classes': ('wide',),
        }),
        ('وضعیت', {
            'fields': ('is_active', 'created_by')
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    filter_horizontal = ['allowed_roles']

    def get_allowed_roles_display(self, obj):
        """نمایش نقش‌های مجاز در لیست"""
        roles = obj.allowed_roles.all()
        if not roles:
            return 'همه کاربران'
        return ', '.join([role.title for role in roles])

    get_allowed_roles_display.short_description = 'نقش‌های مجاز'