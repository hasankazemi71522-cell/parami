# case_management/urls.py

from django.urls import path
from . import views

app_name = 'case_management'

urlpatterns = [
    # ----- داشبوردها -----
    path('supervisor/dashboard/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('expert/dashboard/', views.expert_dashboard, name='expert_dashboard'),

    # ----- مدیریت فرآیندها (سرپرست) -----
    path('supervisor/processes/', views.supervisor_process_list, name='supervisor_process_list'),
    path('supervisor/process/<uuid:pk>/', views.supervisor_process_detail, name='supervisor_process_detail'),
    path('supervisor/assign-expert/', views.assign_expert_to_customer, name='assign_expert_to_customer'),
    path('supervisor/process/<uuid:pk>/add-note/', views.supervisor_add_note, name='supervisor_add_note'),
    path('supervisor/process/<uuid:pk>/add-estate-note/', views.supervisor_add_estate_note,
         name='supervisor_add_estate_note'),
    path('supervisor/process/<uuid:pk>/contact/', views.supervisor_add_contact, name='supervisor_add_contact'),

    # ----- مدیریت فرآیندها (کارشناس) -----
    path('expert/process/<uuid:pk>/', views.expert_process_detail, name='expert_process_detail'),
    path('expert/process/<uuid:pk>/contact/', views.expert_make_contact, name='expert_make_contact'),
    path('expert/process/<uuid:pk>/add-note/', views.expert_add_process_note, name='expert_add_process_note'),
    path('expert/process/<uuid:pk>/intro-report/', views.expert_add_intro_report, name='expert_add_intro_report'),
    path('expert/visit/<uuid:process_pk>/create/', views.expert_create_visit, name='expert_create_visit'),
    path('expert/visit/<uuid:pk>/schedule/', views.expert_schedule_visit, name='expert_schedule_visit'),
    path('expert/visit/<uuid:pk>/result/', views.expert_record_visit_result, name='expert_record_visit_result'),
    path('expert/process/<uuid:pk>/add-estate-note/', views.expert_add_estate_note, name='expert_add_estate_note'),
    # ✅ بستن فرآیند توسط کارشناس
    path('expert/process/<uuid:pk>/close/', views.expert_close_process, name='expert_close_process'),

    # ----- کال سنتر -----
    path('callcenter/notes/', views.callcenter_notes_list, name='callcenter_notes_list'),

    # ----- اخطارها (API/JSON) -----
    path('api/alerts/unread-count/', views.unread_alerts_count, name='unread_alerts_count'),
    path('api/alerts/mark-read/<uuid:pk>/', views.mark_alert_read, name='mark_alert_read'),

    # ----- محاسبه تطابق (دستی) -----
    path('expert/calculate-matches/<uuid:customer_id>/', views.calculate_matches_for_customer, name='calculate_matches_for_customer'),
    path('expert/calculate-all-matches/', views.calculate_matches_for_all_expert_customers, name='calculate_matches_for_all'),
    path('supervisor/calculate-matches/<uuid:customer_id>/', views.supervisor_calculate_matches_for_customer, name='supervisor_calculate_matches_for_customer'),
    path('supervisor/calculate-all-matches/', views.supervisor_calculate_all_matches, name='supervisor_calculate_all_matches'),
    path('supervisor/calculate-matches-filtered/', views.supervisor_calculate_matches_for_filtered, name='supervisor_calculate_matches_filtered'),

    # ----- ثبت بازدید مستقیم (AJAX) -----
    path('expert/visit/<uuid:process_pk>/create-direct/', views.expert_create_visit_direct, name='expert_create_visit_direct'),
    path('supervisor/process/<uuid:pk>/add-intro-report/', views.supervisor_add_intro_report, name='supervisor_add_intro_report'),
    path('supervisor/visit/<uuid:process_pk>/create-direct/', views.supervisor_create_visit_direct, name='supervisor_create_visit_direct'),

    # ✅ مدیر جلسه (meetingchair)
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/meeting/result/<uuid:visit_id>/', views.manager_record_meeting_result, name='manager_record_meeting_result'),
    path('manager/visit/<uuid:visit_id>/', views.manager_visit_detail, name='manager_visit_detail'),
    # ====== تاریخچه فرآیندهای بسته‌شده ======
    path('expert/archived-processes/', views.expert_archived_processes, name='expert_archived_processes'),
    path('supervisor/archived-processes/', views.supervisor_archived_processes, name='supervisor_archived_processes'),
]