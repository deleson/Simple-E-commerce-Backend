from celery import shared_task
from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.utils import timezone
from django_redis import get_redis_connection
import contextlib
import logging

from orders.models import Order, OrderItem
from .models import SeckillEvent, SeckillDeductionRecord


User = get_user_model()
logger = logging.getLogger(__name__)


class RecoverableSeckillError(Exception):
    """可恢复异常：适合重试 + 可能触发补偿。"""


class SeckillEventEndedError(Exception):
    """活动已结束。"""


class SeckillEventDeletedError(Exception):
    """活动已删除。"""


@contextlib.contextmanager
def mute_elasticsearch_signals_only():
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


def _compensate_redis_stock(event: SeckillEvent) -> bool:
    """回补 redis 预扣库存，且不超过活动上限。"""
    redis_conn = get_redis_connection("seckill")
    stock_key = f'seckill_stock_{event.id}'

    lua_script = """
        local max_stock = tonumber(ARGV[1])
        local current = tonumber(redis.call('get', KEYS[1]) or '0')
        if current >= max_stock then
            return current
        end

        local val = redis.call('incr', KEYS[1])
        if val > max_stock then
            redis.call('set', KEYS[1], max_stock)
            return max_stock
        end
        return val
    """
    redis_conn.eval(lua_script, 1, stock_key, event.seckill_stock)
    return True


def _handle_dead_letter(record: SeckillDeductionRecord, reason: str, payload: dict):
    record.status = SeckillDeductionRecord.Status.DEAD
    record.failure_reason = reason[:500]
    record.payload = payload
    record.save(update_fields=['status', 'failure_reason', 'payload', 'updated_at'])
    logger.error("[SECKILL_DEAD_LETTER] request=%s reason=%s payload=%s", record.request_id, reason, payload)


@shared_task(bind=True, max_retries=5)
def create_seckill_order_task(self, user_id, event_id, address_snapshot, request_id=None):
    payload = {'user_id': user_id, 'event_id': event_id}
    record, _ = SeckillDeductionRecord.objects.get_or_create(
        request_id=request_id or str(self.request.id),
        defaults={
            'user_id': user_id,
            'event_id': event_id,
            'status': SeckillDeductionRecord.Status.PENDING,
            'payload': payload,
        },
    )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist as exc:
        # 用户数据异常，无回补价值（账号已不存在）
        msg = f"User not found: {user_id}"
        _handle_dead_letter(record, msg, payload)
        raise SeckillEventDeletedError(msg) from exc

    try:
        event = SeckillEvent.objects.get(id=event_id)
    except SeckillEvent.DoesNotExist as exc:
        # 活动已删除：不做 Redis 回补（避免重新创建孤儿 key），直接告警。
        msg = f"Event deleted: {event_id}"
        _handle_dead_letter(record, msg, payload)
        raise SeckillEventDeletedError(msg) from exc

    now = timezone.now()
    if now > event.end_time:
        # 活动已结束：执行回补，避免有效库存被错误吞掉。
        if not record.is_compensated:
            _compensate_redis_stock(event)
            record.is_compensated = True
            record.compensate_count += 1
            record.save(update_fields=['is_compensated', 'compensate_count', 'updated_at'])

        msg = f"Event ended: {event_id}"
        _handle_dead_letter(record, msg, payload)
        raise SeckillEventEndedError(msg)

    try:
        with mute_elasticsearch_signals_only():
            with transaction.atomic():
                sku = event.sku
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

        record.status = SeckillDeductionRecord.Status.SUCCESS
        record.failure_reason = ''
        record.payload = payload
        record.save(update_fields=['status', 'failure_reason', 'payload', 'updated_at'])
        return f"Seckill Order Created: {order.order_number}"

    except RecoverableSeckillError as exc:
        reason = f"recoverable_error: {exc}"
        record.failure_reason = reason[:500]
        record.payload = payload
        record.save(update_fields=['failure_reason', 'payload', 'updated_at'])

        if self.request.retries >= self.max_retries:
            if not record.is_compensated:
                _compensate_redis_stock(event)
                record.is_compensated = True
                record.compensate_count += 1
            _handle_dead_letter(record, reason, payload)
            record.save(update_fields=['is_compensated', 'compensate_count', 'updated_at'])
            return f"Failed permanently: {reason}"

        raise self.retry(exc=exc, countdown=3)

    except Exception as exc:
        # 全部当可恢复异常处理：先补偿，再重试/死信
        reason = f"recoverable_error: {exc}"
        logger.warning("Error creating seckill order request=%s user=%s event=%s err=%s",
                       record.request_id, user_id, event_id, exc)

        if not record.is_compensated:
            _compensate_redis_stock(event)
            record.is_compensated = True
            record.compensate_count += 1

        record.failure_reason = reason[:500]
        record.payload = payload
        record.save(update_fields=['is_compensated', 'compensate_count', 'failure_reason', 'payload', 'updated_at'])

        if self.request.retries >= self.max_retries:
            _handle_dead_letter(record, reason, payload)
            return f"Failed permanently: {reason}"

        raise self.retry(exc=exc, countdown=3)
