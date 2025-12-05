# """
# Django settings for django_project project.
# Refactored using django-environ.
# """
from datetime import timedelta
from pathlib import Path
from celery.schedules import crontab
import os
import mimetypes
import environ  # 引入 django-environ

# 【Windows 修复】强制修正 JS 文件的 MIME 类型
mimetypes.add_type("application/javascript", ".js", True)

# ==========================================
# 1. 基础路径配置 & 环境变量初始化
# ==========================================
# 假设你的目录结构是: root/backend/django_project/settings/docker_base.py
# 所以需要 3 层 parent 回到 root (包含 manage.py 的目录)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 初始化 Env 对象，并设置【默认值】
# 这里定义的默认值会在找不到环境变量时生效
env = environ.Env(
    # 基础
    DEBUG=(bool, True),  # 智能转换：'False', '0', 'off' 都会转为 Python 的 False

    # 中间件主机
    REDIS_HOST=(str, '127.0.0.1'),
    ES_HOST=(str, '127.0.0.1'),

    # 域名
    PUBLIC_DOMAIN=(str, 'https://duane-nonauriferous-laithly.ngrok-free.dev'),
)

# 尝试读取 .env 文件 (开发环境神器)
# 如果文件不存在，会自动跳过，不报错
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# ==========================================
# 2. 基础安全配置
# ==========================================
SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG')

ALLOWED_HOSTS = [
    '*',
    '127.0.0.1',
    'localhost',
    'backend',
    'duane-nonauriferous-laithly.ngrok-free.dev',
]

# ==========================================
# 3. 应用注册 (INSTALLED_APPS)
# ==========================================
INSTALLED_APPS = [
    'daphne',  # ASGI Server 必须放第一位
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 第三方库
    'debug_toolbar',
    'rest_framework',
    'django_filters',
    'drf_spectacular',
    'corsheaders',
    'django_elasticsearch_dsl',
    'django_elasticsearch_dsl_drf',
    'channels',
    'django_celery_beat',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    # 自定义 App
    "users",
    "products",
    "cart",
    "orders",
    "reviews",
    "payment",
    "sellers",
    "addresses",
    "seckill.apps.SeckillConfig",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'django_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'django_project.wsgi.application'
ASGI_APPLICATION = 'django_project.asgi.application'

# ==========================================
# 4. 环境变量获取 (辅助变量)
# ==========================================
DB_HOST = env('DB_HOST')
REDIS_HOST = env('REDIS_HOST')
ES_HOST = env('ES_HOST')

SITE_DOMAIN = env('SITE_DOMAIN')
PUBLIC_DOMAIN = env('PUBLIC_DOMAIN')

# ==========================================
# 5. 数据库配置
# ==========================================
# 智能端口逻辑：
# 1. 优先读取环境变量 DB_PORT
# 2. 如果没传，且 DB_HOST 是 127.0.0.1，默认用 33061 (本地开发)
# 3. 否则默认用 3306 (Docker)
_default_db_port = 33061 if DB_HOST == '127.0.0.1' else 3306

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': DB_HOST,
        'PORT': env.int('DB_PORT', default=_default_db_port),  # 强制转 int
        'OPTIONS': {'init_command': "SET sql_mode='STRICT_TRANS_TABLES'", 'charset': 'utf8mb4'},
        'CONN_MAX_AGE': 60,
    }
}

# ==========================================
# 6. Redis & 缓存配置
# ==========================================
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/1",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"}
    },
    "seckill": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/2",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"}
    },
}
CACHE_TTL = 60 * 15

# ==========================================
# 7. Celery 配置
# ==========================================
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:6379/0'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:6379/0'
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_ENABLE_UTC = True

CELERY_BEAT_SCHEDULE = {
    'cancel-unpaid-orders-every-minute': {
        'task': 'orders.tasks.cancel_unpaid_orders_task',
        'schedule': crontab(minute='*/1'),
    },
}

# ==========================================
# 8. Elasticsearch 配置
# ==========================================
ELASTICSEARCH_DSL = {
    'default': {
        'hosts': f'http://{ES_HOST}:9200'
    },
}
# 生产环境开启信号同步（秒杀模块已手动 mute，这里开启没问题）
ELASTICSEARCH_DSL_SIGNAL_PROCESSOR = 'django_elasticsearch_dsl.signals.CelerySignalProcessor'

# ==========================================
# 9. Django Channels
# ==========================================
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, 6379)],
        },
    },
}


# ==========================================
# 10. 支付宝配置
# ==========================================
def read_key_file(file_path):
    """安全读取密钥文件，文件不存在时返回空字符串"""
    try:
        with open(file_path) as f:
            return f.read()
    except FileNotFoundError:
        return ""


ALIPAY_CONFIG = {
    'APPID': env('ALIPAY_APPID'),
    'APP_PRIVATE_KEY_STRING': read_key_file(BASE_DIR / 'keys/app_private_key.pem'),
    'ALIPAY_PUBLIC_KEY_STRING': read_key_file(BASE_DIR / 'keys/alipay_public_key.pem'),
    'SIGN_TYPE': 'RSA2',
    'DEBUG': env.bool('ALIPAY_DEBUG'),  # 智能布尔转换
    'ALIPAY_GATEWAY_URL': 'https://openapi-sandbox.dl.alipaydev.com/gateway.do',
}

# ==========================================
# 11. 邮件配置
# ==========================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.qq.com'
EMAIL_PORT = env.int('EMAIL_PORT')  # 自动转 int
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL')  # 自动转 bool
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS')

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ==========================================
# 12. 认证与权限
# ==========================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    # ...
]

LANGUAGE_CODE = 'en-us'
AUTH_USER_MODEL = 'users.MyUser'
TIME_ZONE = 'Asia/Shanghai'
USE_TZ = True
USE_I18N = True

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': [
        'drf_orjson_renderer.renderers.ORJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=3600),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ==========================================
# 13. 静态文件
# ==========================================
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SPECTACULAR_SETTINGS = {
    'TITLE': 'Django 电商平台 API 文档',
    'DESCRIPTION': 'B2B2C 多商户电商平台后端 API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

INTERNAL_IPS = ['127.0.0.1', '::1']
DATA_UPLOAD_MAX_NUMBER_FIELDS = 50000