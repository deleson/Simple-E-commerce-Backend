# seckill/tasks.py
from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save,post_delete, m2m_changed
import contextlib


from orders.models import Order, OrderItem
from .models import SeckillEvent
from products.models import ProductSKU


User = get_user_model()






# 信号全删除
# @contextlib.contextmanager
# def mute_signals(signal):
#     """
#     强力静音上下文管理器：暂时废掉某个信号的所有接收器
#     """
#     # 1. 把所有接收器保存起来
#     receivers = signal.receivers
#     print(f"this is {receivers}")
#     # 2. 清空接收器列表 (拔掉网线)
#     signal.receivers = []
#     try:
#         yield
#     finally:
#         # 3. 恢复接收器 (插回网线)
#         signal.receivers = receivers


@contextlib.contextmanager
def mute_elasticsearch_signals_only():
    """
    【静音】
    根据日志分析，精准剔除 CelerySignalProcessor，
    保留其他所有信号（如 Redis 同步、日志记录等）。
    """
    # 需要处理的信号列表
    signals_to_mute = [post_save, post_delete, m2m_changed]

    # 备份字典：{signal: [原接收器列表]}
    backups = {}

    for signal in signals_to_mute:
        # 1. 备份原列表
        backups[signal] = signal.receivers

        # 2. 过滤：构建一个新列表
        new_receivers = []
        for item in signal.receivers:
            # item 结构: (lookup_key, receiver_ref, weak_boolean)
            receiver_ref = item[1]

            # 获取接收器的字符串表示 (例如: <weakref ... 'CelerySignalProcessor'>)
            receiver_str = str(receiver_ref)

            # 【核心判断】如果是 ES 的处理器，就跳过（剔除）
            if 'CelerySignalProcessor' in receiver_str or 'RealTimeSignalProcessor' in receiver_str:
                continue

            # 其他无辜的接收器，保留
            new_receivers.append(item)

        # 3. 偷梁换柱
        signal.receivers = new_receivers

    try:
        yield
    finally:
        # 4. 恢复现场
        for signal, original_receivers in backups.items():
            signal.receivers = original_receivers




@shared_task(bind=True, max_retries=5)
def create_seckill_order_task(self, user_id, event_id, address_snapshot):
    # ... (前置查询 user/event/sku 代码保持不变) ...
    try:
        user = User.objects.get(id=user_id)
        event = SeckillEvent.objects.get(id=event_id)
        sku = event.sku
    except (User.DoesNotExist, SeckillEvent.DoesNotExist):
        return "Data error"

    try:
        # 【核心修改】使用 mute_signals 包裹整个事务
        # 在这个 with 块里，post_save 信号彻底失效，谁也收不到通知
        with mute_elasticsearch_signals_only():

            with transaction.atomic():
                # 1. 创建订单 (此时绝对不会触发 ES 更新)
                order = Order.objects.create(
                    user=user,
                    total_amount=sku.price,
                    shipping_address=address_snapshot,
                    status=Order.OrderStatus.PENDING
                )

                sub_order = Order.objects.create(
                    parent=order,
                    user=user,
                    seller=sku.spu.seller,
                    total_amount=sku.price,
                    shipping_address=address_snapshot,
                    status=Order.OrderStatus.PENDING
                )

                OrderItem.objects.create(
                    order=sub_order,
                    product=sku,
                    product_name=f"{sku.spu.name} {sku.name} (秒杀)",
                    product_price=sku.price,
                    quantity=1
                )

                # # 2. 扣减库存
                # SeckillEvent.objects.filter(id=event_id).update(seckill_stock=F('seckill_stock') - 1)
                #
                # affected_rows = ProductSKU.objects.filter(id=sku.id, stock__gt=0).update(stock=F('stock') - 1)
                #
                # if affected_rows == 0:
                #     raise Exception(f"Failed: Real stock empty for SKU {sku.id}")

        return f"Seckill Order Created: {order.order_number}"

    except Exception as e:
        print(f"Error creating seckill order: {e}")
        if "Lock wait timeout" in str(e):
            raise self.retry(exc=e, countdown=3)
        return f"Failed: {e}"





