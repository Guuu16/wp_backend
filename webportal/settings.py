"""
Django settings for webportal project.

Generated by 'django-admin startproject' using Django 3.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import datetime
from pathlib import Path
import sys, os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-d9*dd8a(0pq-93u1#osc*ejn%*)oht5su-#gft@9dske2ss=s^'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

sys.path.insert(0, os.path.join(BASE_DIR, "apps"))
# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.jenkinsServer',
    "apps.bugzila",
    "apps.machine",
    "apps.loginAndLogout",
    "apps.performance",
    "django_crontab",
    "rest_framework"
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "utils.crsf_middleware.NotUseCsrfTokenMiddlewareMixin"
]
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema'
}
ROOT_URLCONF = 'webportal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [str(BASE_DIR) + "/templates", ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'libraries': {
                'staticfiles': 'django.templatetags.static'
            }
        },
    },
]

WSGI_APPLICATION = 'webportal.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '10.240.216.23',  # 数据库主机
        'PORT': 3306,  # 数据库端口
        'USER': 'root',  # 数据库用户名
        'PASSWORD': '123456',  # 数据库用户密码
        'NAME': 'web_por'  # 数据库名字
    }
}

JENKINS_URL = "http://10.240.203.48:8080/"

CACHES = {
    "default": {
        # 应用 django-redis 库的 RedisCache 缓存类
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://10.240.216.23:49162",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 100
            }
            # 如果 redis 设置了密码，那么这里需要设置对应的密码，如果redis没有设置密码，那么这里也不设置
            # "PASSWORD": "123456",
        }
    }
}
NEVER_REDIS_TIMEOUT = 365 * 24 * 60 * 60
# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

USE_I18N = True

USE_L10N = True

USE_TZ = False
TIME_ZONE = 'Asia/Shanghai'
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static').replace('\\', '/'),
)

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRONJOBS = [

    ('*/30 * * * *', 'apps.bugzila.bugzila_server.test_crontab.bugs_redis', f'>> {BASE_DIR}/crontab.log'),
    ('*/30 * * * *', 'apps.bugzila.bugzila_server.test_crontab.pa_qtester_redis', f'>> {BASE_DIR}/crontab.log'),
    ('*/3 * * * *', 'apps.jenkinsServer.jenkins_server.tasks.sync_jenkins_jobs', f'>> {BASE_DIR}/crontab.log'),
    ('*/2 * * * *', 'apps.jenkinsServer.jenkins_server.tasks.poll_task_state', f'>> {BASE_DIR}/crontab.log'),
    ('*/5 * * * *', 'apps.machine.machine_operation.task.set_MachinePowerStatus', f'>> {BASE_DIR}/crontab.log'),
    ('00 02 * * *', 'apps.bugzila.bugzila_server.test_crontab.get_all_workmate', f'>> {BASE_DIR}/crontab.log'),
]

SESSION_COOKIE_AGE = 60 * 60 * 24 * 365 * 10  # 和token 設置一樣的
AUTH_LDAP_SERVER_URI = 'ldap://10.64.0.101:389'  # ldap服务器地址及端口
JWT_AUTH = {
    'JWT_EXPIRATION_DELTA': datetime.timedelta(seconds=60 * 60 * 24 * 365 * 10),  # 设置token有效时间
    'JWT_ALLOW_REFRESH': True,
}
BUG_CREATE_TIME = "2022-04-01T00:00:00Z"
SEARCH_PLATFORM = ['Genoa', 'EGS', 'Hakuba']
SEARCH_ITEM = ["manual", "auto", "qtester"]
SEARCH_PRODUCT = ["BMC", 'BIOS', 'CMM', 'CMM_BLUE', 'EMS', 'IMM2', 'IMM2_BLUE', 'IMM3', 'LXPM', 'LXPM4',
                  'PSOC', 'SEP', 'SMM', 'SMM2', 'TMM', 'Translation', 'TSM', 'uEFI', 'UEFI2', 'UEFI3', 'UEFI3_BLUE',
                  'UEFI4', 'UEFI5', 'UEFI6', 'Z_AMI', 'z_Avocent_SW', 'z_Compal_FW', 'z_Emerson_SW', 'z_IEC_FW',
                  'z_Pegatron_SW', 'z_USI_FW', 'z_Wistron_SW', 'Broadcom', 'Intel_Network', 'RHEL', 'CentOS',
                  'System_ECAT', 'z_USI_HW', 'LXCE_OneCLI', 'FPGA', 'LSI_RAID']

CORE_FW = {
    "xcc": ["lish3", "duyh4", 'gongqr1', 'lida1', 'zhangyx57'],
    "uefi": ['wangzl16']
}

LDAP_USER = "fw_bbfv"
LDAP_PASSWORD = "company@0522"

NEXUS = {
    'ip': '10.240.203.48:8081',
    'username': 'auto',
    'password': 'companyxcc'
}
# web portal allowed file type
ALLOWED_EXTENSIONS = ['uxz', 'upd', 'xml', 'zip']

# JENKINS UPDATE JOB SERVER
JENKINS_JOB_URL = "http://10.240.203.213:8001/update"

# manual_machine_url_list
MANUAL_MACHINE_LIS = ['https://companybeijing.sharepoint.com/sites/BBFVServerManagement/Lists/Genoa',
                      'https://companybeijing.sharepoint.com/sites/BBFVServerManagement/Lists/EGS',
                      'https://companybeijing.sharepoint.com/sites/BBFVServerManagement/Lists/Edge%20Servers',
                      'https://companybeijing.sharepoint.com/sites/BBFVServerManagement/Lists/WhitleyCPX6AMD',
                      'https://companybeijing.sharepoint.com/sites/BBFVServerManagement/Lists/Entry11']

# backdoor server
BACKDOOR_SERVER = {
    "ip": "10.240.218.90",
    'user': "bbfv",
    'password': 'FW2020bbfv'}

CELERY_BROKER_URL = 'redis://10.240.216.23:49162/0'
CELERY_RESULT_BACKEND = 'redis://10.240.216.23:49162/1'
CELERY_TIMEZONE = 'Asia/Shanghai'

WEEKDAYS = {
    0: "Mon",
    1: "Tue",
    2: "Wed",
    3: "Thu",
    4: "Fri",
    5: "Sat",
    6: "Sun"
}
