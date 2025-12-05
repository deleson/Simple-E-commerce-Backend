# orders/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 匹配 ws://127.0.0.1:8000/ws/orders/<order_id>/
    re_path(r'ws/orders/(?P<order_id>[\w-]+)/$', consumers.OrderStatusConsumer.as_asgi()),
]