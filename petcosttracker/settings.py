"""
Django settings for petcosttracker project.
"""

from pathlib import Path
import os
import sys
import dj_database_url
from dotenv import load_dotenv

# 1. Сначала загружаем переменные окружения
load_dotenv()

# 2. Определяем, находимся ли мы на Render
IS_RENDER = os.environ.get('RENDER', False)
IS_PRODUCTION = os.environ.get('DATABASE_URL') is not None or IS_RENDER

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-xj02_h0kn%5kelh$35_sln_zo8s!kg!%#)y3(9+mbda9xu*ypk')

# ЕДИНСТВЕННОЕ определение DEBUG
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true' if IS_PRODUCTION else True

# Разрешенные хосты для продакшена
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.onrender.com',    # Для Render.com
    '.railway.app',     # Для Railway.app
    '.herokuapp.com',   # Для Heroku
]

# Дополнительные хосты из переменной окружения
if os.environ.get('ALLOWED_HOSTS'):
    ALLOWED_HOSTS.extend(os.environ.get('ALLOWED_HOSTS').split(','))

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'pets',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Для обслуживания статических файлов
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'petcosttracker.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),  # Исправлено на os.path.join
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Кастомный контекстный процессор для debug
                'petcosttracker.context_processors.debug_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'petcosttracker.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Используем PostgreSQL на продакшене если указана переменная DATABASE_URL
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        ssl_require=True if IS_PRODUCTION else False
    )

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ru-ru'  # Изменено на русский
TIME_ZONE = 'Europe/Moscow'  # Изменено на московское время
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

# Папка, где collectstatic соберет все статические файлы
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Дополнительные папки со статикой
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Использование WhiteNoise для обслуживания статических файлов
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (если будут загружаться файлы)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Настройки аутентификации
LOGIN_URL = '/pets/accounts/login/'
LOGIN_REDIRECT_URL = 'pets:home'
LOGOUT_REDIRECT_URL = 'pets:home'
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Безопасность для продакшена
if not DEBUG:
    # HTTPS настройки
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 год
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Другие настройки безопасности
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
else:
    # Для разработки разрешаем HTTP
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Логирование для отладки
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        # Уберите или закомментируйте handler 'file' для Render
        # 'file': {
        #     'class': 'logging.FileHandler',
        #     'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
        #     'formatter': 'verbose',
        # },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],  # Убрали 'file' здесь
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'pets': {
            'handlers': ['console'],  # Убрали 'file' здесь
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Пользовательские настройки приложения
MAX_PETS_PER_USER = 50
MAX_EXPENSES_PER_PET = 1000
DEFAULT_CURRENCY = 'RUB'

# Дополнительные настройки для продакшена
if IS_PRODUCTION:
    # Настройки для Render
    CSRF_TRUSTED_ORIGINS = [
        'https://pet-cost-tracker.onrender.com',
        'https://*.onrender.com',
    ]