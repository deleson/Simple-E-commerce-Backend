# django_project/celery.py
import os
from celery import Celery

# 设置默认的 Django settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings.docker_base')

# 创建 Celery 应用实例
app = Celery('django_project')

# 从 Django settings 中加载配置，所有 Celery 配置项都必须以 CELERY_ 开头
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现各个 App 下的 tasks.py 文件
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')