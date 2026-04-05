from django.contrib.auth import get_user_model
from django.db import transaction

from common.exceptions import BusinessError
from orders.models import Order, OrderItem
from .models import SeckillEvent
from .signal_utils import mute_elasticsearch_signals_only

User = get_user_model()


def create_seckill_order(*, user_id, event_id, address_snapshot):
    """
    创建秒杀订单的核心业务逻辑。
    """

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise BusinessError("用户不存在。")

    try:
        event = SeckillEvent.objects.select_related("sku__spu__seller").get(id=event_id)
    except SeckillEvent.DoesNotExist:
        raise BusinessError("秒杀活动不存在。")

    sku = event.sku

    with mute_elasticsearch_signals_only():
        with transaction.atomic():
            parent_order = Order.objects.create(
                user=user,
                total_amount=sku.price,
                shipping_address=address_snapshot,
                status=Order.OrderStatus.PENDING,
            )

            sub_order = Order.objects.create(
                parent=parent_order,
                user=user,
                seller=sku.spu.seller,
                total_amount=sku.price,
                shipping_address=address_snapshot,
                status=Order.OrderStatus.PENDING,
            )

            OrderItem.objects.create(
                order=sub_order,
                product=sku,
                product_name=f"{sku.spu.name} {sku.name} (秒杀)",
                product_price=sku.price,
                quantity=1,
            )

    return parent_order
