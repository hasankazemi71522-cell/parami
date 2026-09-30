# form_flow/urls.py

from django.urls import path
from . import views

app_name = 'form_flow'

urlpatterns = [
    path('available/', views.available_forms, name='available_forms'),
    path('my-forms/', views.my_forms, name='my_forms'),
    path('create/<int:template_id>/', views.create_form_instance, name='create_form_instance'),
    path('edit-fields/<int:instance_id>/', views.edit_instance_fields, name='edit_instance_fields'),
    path('fill/<int:instance_id>/', views.fill_form, name='fill_form'),
    path('detail/<int:instance_id>/', views.form_detail, name='form_detail'),
    path('history/<int:instance_id>/', views.form_history, name='form_history'),
    path('cancel/<int:instance_id>/', views.cancel_form, name='cancel_form'),
    path('delete/<int:instance_id>/', views.delete_form, name='delete_form'),
    path('approve/<int:instance_id>/', views.approve_form, name='approve_form'),
    path('reject/<int:instance_id>/', views.reject_form, name='reject_form'),
    path('my-tasks/', views.my_tasks, name='my_tasks'),
    path('api/task-count/', views.api_task_count, name='api_task_count'),
    path('pdf/<int:instance_id>/', views.form_pdf, name='form_pdf'),
]