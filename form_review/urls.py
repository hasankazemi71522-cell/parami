# form_review/urls.py

from django.urls import path
from . import views

app_name = 'form_review'

urlpatterns = [
    # فرم‌های در انتظار بررسی
    path('pending/', views.pending_reviews, name='pending_reviews'),

    # برگشت فرم
    path('reject/<int:instance_id>/', views.reject_form, name='reject_form'),

    # فرم‌های برگشتی من
    path('my-rejected/', views.my_rejected_forms, name='my_rejected_forms'),

    # اصلاح فرم برگشتی
    path('fix/<int:rejection_id>/', views.fix_rejected_form, name='fix_rejected_form'),

    # پاسخ به برگشت
    path('reply/<int:rejection_id>/', views.reply_to_rejection, name='reply_to_rejection'),

    # تاریخچه بررسی
    path('history/<int:instance_id>/', views.review_history, name='review_history'),

    # ✅ جزئیات برگشت
    path('detail/<int:rejection_id>/', views.review_detail, name='review_detail'),
]