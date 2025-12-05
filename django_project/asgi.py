import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings.docker_base')
django.setup() # 显式初始化 Django

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import orders.routing # 我们稍后创建这个路由文件

application = ProtocolTypeRouter({
    # 1. HTTP 请求依然走 Django 的标准视图
    "http": get_asgi_application(),

    # 2. WebSocket 请求走 Channels 的路由
    "websocket": AuthMiddlewareStack(
        URLRouter(
            orders.routing.websocket_urlpatterns
        )
    ),
})