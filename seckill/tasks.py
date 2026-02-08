# seckill/tasks.py
import contextlib
import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save

from orders.models import Order, OrderItem
from .models import SeckillEvent


logger = logging.getLogger(__name__)
User = get_user_model()


@contextlib.contextmanager
def mute_elasticsearch_signals_only():
    """
    根据日志分析，精准剔除 CelerySignalProcessor，保留其他信号。
    """
    signals_to_mute = [post_save, post_delete, m2m_changed]
    backups = {}

    for signal in signals_to_mute:
        backups[signal] = signal.receivers
        new_receivers = []
        for item in signal.receivers:
            receiver_ref = item[1]
            receiver_str = str(receiver_ref)
            if 'CelerySignalProcessor' in receiver_str or 'RealTimeSignalProcessor' in receiver_str:
                continue
            new_receivers.append(item)
        signal.receivers = new_receivers

    try:
        yield
    finally:
        for signal, original_receivers in backups.items():
            signal.receivers = original_receivers


@shared_task(bind=True, max_retries=5)
def create_seckill_order_task(self, user_id, event_id, address_snapshot):
    try:
        user = User.objects.get(id=user_id)
        event = SeckillEvent.objects.get(id=event_id)
        sku = event.sku
    except (User.DoesNotExist, SeckillEvent.DoesNotExist):
        logger.warning(
            "[SECKILL_CREATE_ORDER][DATA_ERROR] user_id=%s event_id=%s",
            user_id,
            event_id,
        )
        return "Data error"

    try:
        with mute_elasticsearch_signals_only():
            with transaction.atomic():
                order = Order.objects.create(
                    user=user,
                    total_amount=sku.price,
                    shipping_address=address_snapshot,
                    status=Order.OrderStatus.PENDING,
                )

                sub_order = Order.objects.create(
                    parent=order,
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

        logger.info(
            "[SECKILL_CREATE_ORDER][SUCCESS] event_id=%s user_id=%s sku_id=%s order_number=%s",
            event_id,
            user_id,
            sku.id,
            order.order_number,
        )
        return f"Seckill Order Created: {order.order_number}"

    except Exception as e:
        logger.exception(
            "[SECKILL_CREATE_ORDER][ERROR] event_id=%s user_id=%s sku_id=%s error=%s",
            event_id,
            user_id,
            sku.id,
            e,
        )
        if "Lock wait timeout" in str(e):
            raise self.retry(exc=e, countdown=3)
        return f"Failed: {e}"
