import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


GOOGLE_CREDENTIALS_FILE = os.path.join(BASE_DIR, 'Config/client_secret.json')
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

SECRET_KEY = 'django-insecure-w-wfq_hlw8rteq7$pne*n0c6li3hxbw%x5jm_jy*3*oqi3p05$'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "debug_toolbar",

    'main',
    "main_menu",
    'monitoring',
    'control',
    'service',
    'user',
    'zip',
    'departure',
    'application',
    'mail',


]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = 'MsServiceControl.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'MsServiceControl.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'MShomeDEV',
        'USER': 'homePIZ',
        'PASSWORD': 'dudecomeon222',
        'HOST': 'localhost',
        'PORT': '5433',

    }
}

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

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Asia/Yekaterinburg'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = (BASE_DIR / 'static',)
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = 'media/'

MEDIA_ROOT = BASE_DIR / 'media'

INTERNAL_IPS = [
    # ...
    "127.0.0.1",
    # ...
]

AUTH_USER_MODEL = 'user.MsUser'
LOGIN_URL = '/user/login/'
LOGIN_REDIRECT_URL = '/'

ALLOWED_DEPARTMENT = {'to_monitoring': ["monitoring", "all", "admin"],
                      'to_control': ["control", "all", "admin"],
                      'to_service': ["service", "all", "admin"],
                      'to_zip': ["service", "all", "admin"]

                      }
