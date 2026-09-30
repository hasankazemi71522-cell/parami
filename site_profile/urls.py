from django.urls import path
from . import views, views_callcenter

app_name = 'site_profile'

urlpatterns = [
    # ====== داشبورد ======
    path('dashboard/', views.dashboard, name='dashboard'),
    path('<int:userId>/profile-settings/', views.profile_settings, name='profile_settings'),
    path('page-404/', views.page_404, name='page_404'),

    # ====== مدیریت کاربران ======
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/edit/<int:user_id>/', views.user_edit, name='user_edit'),
    path('users/delete/<int:user_id>/', views.user_delete, name='user_delete'),
    path('users/detail/<int:user_id>/', views.user_detail, name='user_detail'),

    # ====== مدیریت نقش‌ها ======
    path('roles/', views.role_list, name='role_list'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/edit/<int:role_id>/', views.role_edit, name='role_edit'),
    path('roles/delete/<int:role_id>/', views.role_delete, name='role_delete'),
    path('roles/permissions/<int:role_id>/', views.role_permissions, name='role_permissions'),

    # ====== مدیریت مجوزها ======
    path('permissions/', views.permission_list, name='permission_list'),
    path('permissions/create/', views.permission_create, name='permission_create'),
    path('permissions/delete/<int:permission_id>/', views.permission_delete, name='permission_delete'),

    path('permissions/export/', views.export_permissions_excel, name='export_permissions'),
    path('permissions/import/', views.import_permissions_excel, name='import_permissions'),
    path('permissions/template/', views.download_permissions_template, name='download_permissions_template'),

    # ============================================================
    # 👥 مدیریت کارشناسان (کال سنتر)
    # ============================================================
    path('workflow/experts/manage/', views_callcenter.manage_experts_callcenter, name='manage_experts_callcenter'),
    path('workflow/experts/assign/', views_callcenter.assign_expert_to_supervisor, name='assign_expert_to_supervisor'),
    path('workflow/experts/transfer/', views_callcenter.transfer_expert, name='transfer_expert'),
    path('workflow/experts/remove/', views_callcenter.remove_expert_from_supervisor, name='remove_expert_from_supervisor'),
    path('workflow/experts/supervisor/<int:supervisor_id>/', views_callcenter.get_supervisor_experts, name='get_supervisor_experts'),
    path('workflow/experts/edit-capacity/', views_callcenter.edit_expert_capacity, name='edit_expert_capacity'),
    path('workflow/experts/remove-ajax/', views_callcenter.remove_expert_from_supervisor_ajax, name='remove_expert_from_supervisor_ajax'),

    # ============================================================
    # 📋 مدیریت مشتریان بدون سرپرست (کال سنتر)
    # ============================================================
    path('workflow/customers/', views_callcenter.customers_without_supervisor, name='customers_without_supervisor'),
    path('workflow/customer/assign-supervisor/', views_callcenter.assign_supervisor_to_customer, name='assign_supervisor_to_customer'),
    path('workflow/customer/edit-supervisor/', views_callcenter.edit_customer_supervisor, name='edit_customer_supervisor'),

    # ============================================================
    # 🏠 مدیریت فایل‌ها (املاک) بدون سرپرست (کال سنتر)
    # ============================================================
    path('workflow/properties/', views_callcenter.properties_without_supervisor, name='properties_without_supervisor'),
    path('workflow/property/assign-supervisor/', views_callcenter.assign_supervisor_to_property, name='assign_supervisor_to_property'),
    path('workflow/property/edit-supervisor/', views_callcenter.edit_property_supervisor, name='edit_property_supervisor'),

    # ============================================================
    # 📝 مدیریت یادداشت‌ها (کال سنتر) - API
    # ============================================================
    path('api/note/customer/<uuid:customer_id>/', views_callcenter.add_note_to_customer, name='add_note_to_customer'),
    path('api/note/property/<uuid:property_id>/', views_callcenter.add_note_to_property, name='add_note_to_property'),
    path('api/notes/<str:target_type>/<uuid:target_id>/', views_callcenter.get_notes, name='get_notes'),
    path('api/note/resolve/<uuid:note_id>/', views_callcenter.resolve_note, name='resolve_note'),

    path('confirm-property/', views_callcenter.confirm_property, name='confirm_property'),
    path('delete-property/', views_callcenter.delete_property, name='delete_property'),

# در urls.py
    path('confirm-customer/', views_callcenter.confirm_customer, name='confirm_customer'),
    path('delete-customer/', views_callcenter.delete_customer, name='delete_customer'),
]