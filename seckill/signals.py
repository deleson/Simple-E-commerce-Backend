# # seckill/signals.py
import logging

from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_redis import get_redis_connection

from products.models import ProductSKU
from .models import SeckillEvent


logger = logging.getLogger(__name__)


@receiver(post_save, sender=SeckillEvent)
def seckill_event_post_save(sender, instance, created, **kwargs):
    """
    1. 库存预热：写入 Redis
    2. 库存预扣：如果是新创建的活动，直接从 SKU 主表扣除库存
    """
    conn = get_redis_connection("seckill")
    cache_key = f'seckill_stock_{instance.id}'
    conn.set(cache_key, instance.seckill_stock)
    logger.info(
        "[SECKILL_EVENT][CACHE_WARMED] event_id=%s sku_id=%s cache_key=%s stock=%s",
        instance.id,
        instance.sku.id,
        cache_key,
        instance.seckill_stock,
    )

    if created:
        try:
            with transaction.atomic():
                sku = ProductSKU.objects.select_for_update().get(id=instance.sku.id)

                if sku.stock < instance.seckill_stock:
                    raise ValueError(f"主表库存不足！剩余: {sku.stock}, 需要: {instance.seckill_stock}")

                sku.stock -= instance.seckill_stock
                sku.save()

                logger.info(
                    "[SECKILL_EVENT][SKU_STOCK_RESERVED] event_id=%s sku_id=%s reserved_qty=%s",
                    instance.id,
                    sku.id,
                    instance.seckill_stock,
                )

        except Exception as e:
            logger.exception(
                "[SECKILL_EVENT][RESERVE_ERROR] event_id=%s sku_id=%s error=%s",
                instance.id,
                instance.sku.id,
                e,
            )
            raise


@receiver(post_delete, sender=SeckillEvent)
def seckill_event_post_delete(sender, instance, **kwargs):
    """
    当活动被删除时：
    1. 清理 Redis 里的缓存 Key
    2. 将剩余的秒杀库存归还给主表 (SKU)
    """
    conn = get_redis_connection("seckill")
    cache_key = f'seckill_stock_{instance.id}'
    conn.delete(cache_key)

    if instance.seckill_stock > 0:
        try:
            ProductSKU.objects.filter(id=instance.sku.id).update(
                stock=F('stock') + instance.seckill_stock
            )
            logger.info(
                "[SECKILL_EVENT][SKU_STOCK_RETURNED] event_id=%s sku_id=%s return_qty=%s",
                instance.id,
                instance.sku.id,
                instance.seckill_stock,
            )
        except Exception as e:
            logger.exception(
                "[SECKILL_EVENT][STOCK_RETURN_ERROR] event_id=%s sku_id=%s error=%s",
                instance.id,
                instance.sku.id,
                e,
            )

    logger.info("[SECKILL_EVENT][CACHE_CLEARED] event_id=%s cache_key=%s", instance.id, cache_key)
