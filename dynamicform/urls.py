from django.urls import path
from . import views

app_name = 'dynamicform'

urlpatterns = [
    # ==================== مدیریت فرم‌ها ====================
    path('form-templates/', views.form_template_list, name='form_template_list'),
    path('form-templates/create/', views.form_template_create, name='form_template_create'),
    path('form-templates/edit/<int:form_id>/', views.form_template_edit, name='form_template_edit'),
    path('form-templates/delete/<int:form_id>/', views.form_template_delete, name='form_template_delete'),
    path('form-templates/preview/<int:form_id>/', views.form_template_preview, name='form_template_preview'),
]