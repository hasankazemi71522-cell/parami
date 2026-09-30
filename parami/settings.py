import os
from pathlib import Path
import pymysql

pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-your-secret-key-here-change-in-production'

DEBUG = True

ALLOWED_HOSTS = []

# ALLOWED_HOSTS = ['parami.ir', 'www.parami.ir']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_select2',
    'corsheaders',
    'account',
    'estate',
    'site_profile',
    'case_management',
    'transaction',
    'amlak_report',
    'dynamicform',
    'form_flow',
    'reports',
    'common',
    'form_review',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'parami.urls'
AUTH_USER_MODEL = 'account.User'  # ✅ مدل کاربر سفارشی

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'parami.wsgi.application'

# ✅ دیتابیس SQLite (برای شروع)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

#
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'paramiir_data',
#         'USER': 'paramiir_admin',
#         'PASSWORD': '&u69iq?{[9Z3D*ON',
#         'HOST': 'localhost',
#         'PORT': 3306,
#         'OPTIONS': {
#             'unix_socket': '/var/lib/mysql/mysql.sock',  # Path to MySQL socket
#         },
#     }
# }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static_cdn/static_root/'
STATICFILES_DIRS = [BASE_DIR / "assets"]
STATIC_ROOT = "static_cdn/static_root"

MEDIA_URL = '/media_root/'
MEDIA_ROOT = "media_root"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ✅ تنظیمات CORS (در صورت نیاز)
CORS_ALLOW_ALL_ORIGINS = True