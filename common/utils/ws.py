from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from common.utils.redis_key import get_order_ws_group


def push_order_status(order_number, status, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        get_order_ws_group(order_number),
        {
            "type": "order_status_update",
            "message": message,
            "status": status,
        }
    )
