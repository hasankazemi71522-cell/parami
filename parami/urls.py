"""
URL configuration for parami project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', views.home_page, name='home_page'),
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/login/', permanent=False)),
    path('contact', views.contact_us, name='contact'),
    path('rules', views.rules_page, name='rules'),
    path('about_us', views.about_us, name='about_us'),
    path('cooperate', views.cooperate, name='cooperate'),
    path('privacy/', views.privacy, name='privacy'),
    path('search-file/', views.search_file, name='search_file'),
    path('property/<uuid:property_id>/', views.property_detail, name='property_detail'),
    path('', include('account.urls')),
    path('estate/', include('estate.urls')),
    path('', include('site_profile.urls')),
    path('', include('case_management.urls')),
    path('', include('transaction.urls')),
    path('reports/', include('amlak_report.urls')),
    path('dynamic-form/', include('dynamicform.urls', namespace='dynamic_form')),
    path('form_flow/', include('form_flow.urls', namespace='form_flow')),
    path('form_reports/', include('reports.urls', namespace='reports')),
    path('review/', include('form_review.urls', namespace='form_review')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
