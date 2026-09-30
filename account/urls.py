# account/urls.py

from django.urls import path
from . import views

app_name = 'account'

urlpatterns = [
    path('login/', views.login_page, name='login'),
    path('login-pass/', views.login_pass, name='login_pass'),
    path('register/', views.register, name='register'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),  # <-- اینجا
    path('logout/', views.logout_user, name='logout'),
]