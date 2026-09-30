# estate/urls.py

from django.urls import path
from . import views_location, views_customer, views_property, views_duplicate

app_name = 'estate'

urlpatterns = [
    # ============================================================
    # 📍 مدیریت مکان (استان، شهرستان، محله)
    # ============================================================
    path('provinces/', views_location.province_list, name='province_list'),
    path('provinces/create/', views_location.province_create, name='province_create'),
    path('provinces/<int:pk>/edit/', views_location.province_edit, name='province_edit'),
    path('provinces/<int:pk>/delete/', views_location.province_delete, name='province_delete'),

    path('cities/', views_location.city_list, name='city_list'),
    path('cities/create/', views_location.city_create, name='city_create'),
    path('cities/<int:pk>/edit/', views_location.city_edit, name='city_edit'),
    path('cities/<int:pk>/delete/', views_location.city_delete, name='city_delete'),

    path('neighborhoods/', views_location.neighborhood_list, name='neighborhood_list'),
    path('neighborhoods/create/', views_location.neighborhood_create, name='neighborhood_create'),
    path('neighborhoods/<int:pk>/edit/', views_location.neighborhood_edit, name='neighborhood_edit'),
    path('neighborhoods/<int:pk>/delete/', views_location.neighborhood_delete, name='neighborhood_delete'),

    # واردات و صادرات مکان
    path('import/', views_location.location_import, name='location_import'),
    path('import/confirm/', views_location.location_import_confirm, name='location_import_confirm'),
    path('export/template/', views_location.location_export_template, name='location_export_template'),

    # ============================================================
    # 📍 APIهای مکان (برای فرم‌ها)
    # ============================================================
    path('api/cities-by-province/', views_location.get_cities_by_province, name='api_cities_by_province'),

    # ============================================================
    # 👤 مدیریت مشتریان
    # ============================================================
    path('customers/', views_customer.customer_list, name='customer_list'),
    path('my_create_customer/', views_customer.my_create_customer, name='my_create_customer'),
    path('expert_customer/', views_customer.expert_customer, name='expert_customer'),
    path('deactive_customer_list/', views_customer.deactive_customer_list, name='deactive_customer_list'),
    path('customers/create/', views_customer.customer_create, name='customer_create'),
    path('customers/<uuid:pk>/', views_customer.customer_detail, name='customer_detail'),
    path('customers/<uuid:pk>/edit/', views_customer.customer_edit, name='customer_edit'),
    path('customers/<uuid:pk>/delete/', views_customer.customer_delete, name='customer_delete'),
    path('customers/<uuid:pk>/restore/', views_customer.customer_restore, name='customer_restore'),
    path('customers/<uuid:pk>/change-status/', views_customer.customer_change_status, name='customer_change_status'),

    # ============================================================
    # 🔍 APIهای جستجوی مشتری
    # ============================================================
    path('api/search-city/', views_customer.search_city_api, name='search_city_api'),
    path('api/search-neighborhood/', views_customer.search_neighborhood_api, name='search_neighborhood_api'),
    path('api/get-city-names/', views_customer.get_city_names_api, name='get_city_names_api'),
    path('api/get-neighborhood-names/', views_customer.get_neighborhood_names_api, name='get_neighborhood_names_api'),
    path('api/neighborhoods-by-city/', views_customer.get_neighborhoods_by_city_api, name='api_neighborhoods_by_city'),

    # ============================================================
    # 📊 APIهای آماری مشتری
    # ============================================================
    path('api/customer-stats/', views_customer.customer_stats_api, name='customer_stats_api'),
    path('api/customer-search/', views_customer.customer_search_ajax, name='customer_search_ajax'),

    # ============================================================
    # 🏠 مدیریت املاک
    # ============================================================
    path('properties/', views_property.property_list, name='property_list'),
    path('my_create_property/', views_property.my_create_property, name='my_create_property'),
    path('expert_property/', views_property.expert_property, name='expert_property'),
    path('properties/deactive', views_property.deactive_property_list, name='deactive_property_list'),
    path('properties/create/', views_property.property_create, name='property_create'),
    path('properties/<uuid:pk>/', views_property.property_detail, name='property_detail'),
    path('properties/<uuid:pk>/edit/', views_property.property_edit, name='property_edit'),
    path('properties/<uuid:pk>/delete/', views_property.property_delete, name='property_delete'),
    path('properties/<uuid:pk>/restore/', views_property.property_restore, name='property_restore'),

    # ============================================================
    # 🖼️ مدیریت تصاویر و ویدئوهای ملک (API)
    # ============================================================
    path('api/property/image/<int:pk>/delete/', views_property.property_image_delete, name='property_image_delete'),
    path('api/property/image/<int:pk>/set-main/', views_property.property_image_set_main, name='property_image_set_main'),
    path('api/property/video/<int:pk>/delete/', views_property.property_video_delete, name='property_video_delete'),

    # ============================================================
    # 📊 APIهای آماری و جستجوی املاک
    # ============================================================
    path('api/property/stats/', views_property.property_stats_api, name='property_stats_api'),
    path('api/property/search/', views_property.property_search_ajax, name='property_search_ajax'),

    # ============================================================
    # 🔄 API محاسبه تطابق ملک
    # ============================================================
    path('api/property/<uuid:pk>/calculate-matches/',
         views_property.calculate_matches_for_property,
         name='property_calculate_matches'),

    # ============================================================
    # 🔍 بررسی تکراری (Duplicate Check)
    # ============================================================
    path('api/check-customer-duplicate/', views_duplicate.check_customer_duplicate, name='check_customer_duplicate'),
    path('api/check-property-duplicate/', views_duplicate.check_property_duplicate, name='check_property_duplicate'),
    path('api/handle-duplicate-check/', views_duplicate.handle_duplicate_check, name='handle_duplicate_check'),
    path('api/duplicate-check/<str:check_id>/', views_duplicate.get_duplicate_check_details,
         name='get_duplicate_check_details'),
    path('api/duplicate-check/customer/<uuid:customer_id>/',
         views_duplicate.get_customer_duplicates_ajax,
         name='get_customer_duplicates_ajax'),
    path('api/duplicate-check/property/<uuid:property_id>/',
         views_duplicate.get_property_duplicates_ajax,
         name='get_property_duplicates_ajax'),
]