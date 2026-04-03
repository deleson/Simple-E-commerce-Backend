# orders/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

# 引入工具类
from common.utils.redis_key import get_order_ws_group


class OrderStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 从 URL 中获取订单号 (例如: ws/orders/ORDER_UUID/)
        self.order_id = self.scope['url_route']['kwargs']['order_id']

        # 定义组名 (每个订单一个组)
        self.room_group_name = get_order_ws_group(self.order_id)


        # 将当前连接加入到这个组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # 接受连接
        await self.accept()

    async def disconnect(self, close_code):
        # 断开连接时，从组中移除
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # 接收来自 Channel Layer 的消息 (由 Webhook 发送)
    async def order_status_update(self, event):
        message = event['message']
        status = event['status']

        # 将消息发送给前端 WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'status': status
        }))