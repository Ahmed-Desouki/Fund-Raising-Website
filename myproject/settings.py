"""
Django settings for myproject project.
"""

from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'main',
    'projects',
    'chatbot',
]

AUTHENTICATION_BACKENDS = [
    'main.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',  # fallback, e.g. for admin login
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'myproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'myproject.wsgi.application'


# Database

# Put DATABASE_URL=postgresql://user:password@host:5432/dbname in .env to use PostgreSQL
# (e.g. the connection string from Neon). Without it the project uses a local SQLite file.
DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    _db = urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _db.path.lstrip('/'),
            'USER': unquote(_db.username or ''),
            'PASSWORD': unquote(_db.password or ''),
            'HOST': _db.hostname,
            'PORT': _db.port or 5432,
            # Carries query options such as sslmode=require, which hosted databases need
            'OPTIONS': dict(parse_qsl(_db.query)),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization

LANGUAGE_CODE = 'en'

# The site is available in English and Arabic; the visitor picks with the switch in the header
from django.utils.translation import gettext_lazy as _
LANGUAGES = [
    ('en', _('English')),
    ('ar', _('Arabic')),
]
LOCALE_PATHS = [BASE_DIR / 'locale']
FORMAT_MODULE_PATH = ['myproject.formats']
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_TZ = True


# Static & media files

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Email (console backend prints emails to your terminal instead of sending them — fine for dev)

# Email. With EMAIL_HOST_USER / EMAIL_HOST_PASSWORD in .env, emails are really sent over SMTP
# to the person who registers; without them they're printed in the runserver terminal.
# Defaults are for Gmail (EMAIL_HOST_PASSWORD is a Gmail App Password, not the account password).
# Any other SMTP service works by changing EMAIL_HOST / EMAIL_PORT, e.g. Brevo:
#   EMAIL_HOST=smtp-relay.brevo.com  EMAIL_PORT=587  EMAIL_FROM=you@yourdomain.com
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='').replace(' ', '')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=EMAIL_PORT == 465, cast=bool)
EMAIL_USE_TLS = not EMAIL_USE_SSL
EMAIL_TIMEOUT = 20

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'main.email.ReadableConsoleEmailBackend'

# The address emails come from. Gmail requires it to be the Gmail account itself;
# services like Brevo log in with one user and send from a verified address.
EMAIL_FROM = config('EMAIL_FROM', default=EMAIL_HOST_USER or 'noreply@fundraiser.local')
DEFAULT_FROM_EMAIL = f'Fundraiser <{EMAIL_FROM}>'


# Auth redirects

LOGIN_URL = 'auth_page'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'auth_page'


# Cookie security
# Flip these to True once you're serving over HTTPS in production

SESSION_COOKIE_HTTPONLY = True

# Serving the site for real (DEBUG=False) means HTTPS: cookies only over HTTPS, redirect http -> https.
# Set SECURE_SSL_REDIRECT=False in .env if the host already handles that.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=3600, cast=int)
    SECURE_CONTENT_TYPE_NOSNIFF = True
CSRF_COOKIE_HTTPONLY = False  # JS needs to read this cookie to send the X-CSRFToken header

# Governs the expiry window for both account-activation links and (later) password-reset links
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24  # 24 hours, in seconds


# Help chatbot (Google Gemini, free tier). Without a key the widget still shows but replies that it's unavailable.
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
# Tried in order; later ones are used when an earlier one is overloaded or rate limited
GEMINI_MODELS = config('GEMINI_MODELS', default='gemini-3.8-flash,gemini-flash-latest,gemini-flash-lite-latest', cast=Csv())
