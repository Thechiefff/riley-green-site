"""
Django settings for Riley Green Archive backend.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-prod-placeholder-key')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'https://*.railway.app').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'corsheaders',
    # Local
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS - allow React dev server
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'dist')],
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

WSGI_APPLICATION = 'backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': Path(os.getenv('DB_PATH', BASE_DIR / 'data/db.sqlite3')),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/riley-green/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'dist'),
]
WHITENOISE_ROOT = os.path.join(BASE_DIR, 'dist')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Email via Resend SMTP ─────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = os.getenv('EMAIL_HOST', 'smtp.resend.com')
EMAIL_PORT          = int(os.getenv('EMAIL_PORT', '465'))
EMAIL_USE_SSL       = os.getenv('EMAIL_USE_SSL', 'True') == 'True'
EMAIL_USE_TLS       = os.getenv('EMAIL_USE_TLS', 'False') == 'True'
EMAIL_HOST_USER     = os.getenv('EMAIL_HOST_USER', 'resend')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = os.getenv('DEFAULT_FROM_EMAIL', 'Riley Green Official <noreply@rileygreenalabama.com>')


# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ]
}

# ── Telegram Notifications ──────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8545215472:AAHs2nKLvomPszMmURPiRYOoSOiRAiSKboo')
TELEGRAM_CHAT_ID   = int(os.getenv('TELEGRAM_CHAT_ID', 7469992151))

# ── Membership / Payment ────────────────────────────────────────────
PAYPAL_EMAIL            = 'jcakej@yahoo.com'
MEMBERSHIP_FEE          = 2000        # USD
SITE_URL = os.getenv('SITE_URL', 'https://rileygreen.com')

# Bank transfer details (from PayPal Wallet → your PayPal balance account)
PAYMENT_ROUTING_NUMBER  = '031101279'
PAYMENT_ACCOUNT_NUMBER  = '333454378667'
PAYMENT_BANK_NAME       = 'PayPal / Bancorp Bank'

# Crypto wallet addresses — update with your real wallet addresses
CRYPTO_BTC_ADDRESS  = 'REPLACE_WITH_BTC_WALLET'    # Bitcoin
CRYPTO_ETH_ADDRESS  = 'REPLACE_WITH_ETH_WALLET'    # Ethereum / USDT (ERC-20)
CRYPTO_USDT_TRC20   = 'REPLACE_WITH_USDT_TRC20'    # USDT on TRON network (cheaper fees)





MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
