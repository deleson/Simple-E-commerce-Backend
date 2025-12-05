# django_project/__init__.py

# 【关键】从 celery_app 导入，而不是 .celery
from .celery_app import app as celery_app

__all__ = ('celery_app',)