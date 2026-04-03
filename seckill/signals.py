# # seckill/signals.py


from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_redis import get_redis_connection  # <-- 引入这个
from django.db import transaction
from .models import SeckillEvent
from products.models import ProductSKU

# 引入工具类
from common.utils.redis_key import get_seckill_stock_key


# @receiver(post_save, sender=SeckillEvent)
# def seckill_event_post_save(sender, instance, created, **kwargs):
#     """
#     使用原生连接同步库存，确保 Key 没有前缀，Value 没有乱码
#     """
#     # 1. 获取原生 Redis 连接 (必须和 views.py 里用的别名一致)
#     conn = get_redis_connection("seckill")
#
#     # 2. 这里的 Key 就是纯粹的字符串，不会被自动加 :1: 前缀
#     cache_key = f'seckill_stock_{instance.id}'
#
#     # 3. 使用原生 set，存进去的就是纯数字字符串
#     conn.set(cache_key, instance.seckill_stock)
#
#     print(f"--- [Signal] 原生库存同步完成: {cache_key} = {instance.seckill_stock} ---")


# @receiver(post_delete, sender=SeckillEvent)
# def seckill_event_post_delete(sender, instance, **kwargs):
#     conn = get_redis_connection("seckill")
#     cache_key = f'seckill_stock_{instance.id}'
#
#     conn.delete(cache_key)
#     print(f"--- [Signal] 原生库存 Key 已清理: {cache_key} ---")

@receiver(post_save, sender=SeckillEvent)
def seckill_event_post_save(sender, instance, created, **kwargs):
    """
    1. 库存预热：写入 Redis
    2. 库存预扣：如果是新创建的活动，直接从 SKU 主表扣除库存
    """
    # 1. 同步 Redis (保持不变)
    conn = get_redis_connection("seckill")
    cache_key = get_seckill_stock_key(instance.id)
    conn.set(cache_key, instance.seckill_stock)
    print(f"--- [Signal] Redis 预热完成: {cache_key} = {instance.seckill_stock} ---")

    # 2. 【核心新增】预扣主表库存
    # 仅在“新建”活动时触发，防止修改活动名称时重复扣库存
    if created:
        try:
            with transaction.atomic():
                # 锁定 SKU 行
                sku = ProductSKU.objects.select_for_update().get(id=instance.sku.id)

                if sku.stock < instance.seckill_stock:
                    # 如果主表库存不够，抛出异常回滚，导致活动创建失败
                    raise ValueError(f"主表库存不足！剩余: {sku.stock}, 需要: {instance.seckill_stock}")

                # 扣除库存 (冻结)
                sku.stock -= instance.seckill_stock
                sku.save()

                print(f"--- [Signal] 主表库存已预扣: SKU {sku.id} 减少了 {instance.seckill_stock} ---")

        except Exception as e:
            # 这里抛出异常会让 Admin 界面显示错误信息，并回滚 SeckillEvent 的创建
            raise e


@receiver(post_delete, sender=SeckillEvent)
def seckill_event_post_delete(sender, instance, **kwargs):
    """
    当活动被删除时：
    1. 清理 Redis 里的缓存 Key
    2. 【核心修正】将剩余的秒杀库存归还给主表 (SKU)
    """
    # 1. 清理 Redis
    conn = get_redis_connection("seckill")
    cache_key = get_seckill_stock_key(instance.id)

    conn.delete(cache_key)

    # 2. 归还库存
    if instance.seckill_stock > 0:
        try:
            # 使用 F 表达式原子更新，把钱(库存)还给 SKU
            # 注意：这里我们通过 instance.sku.id 来定位，
            # 只要 SKU 没被物理删除，这个 ID 就是有效的。
            ProductSKU.objects.filter(id=instance.sku.id).update(
                stock=F('stock') + instance.seckill_stock
            )
            print(f"--- [Signal] 活动删除: 已归还 {instance.seckill_stock} 件库存给 SKU {instance.sku.id} ---")
        except Exception as e:
            # 打印错误日志，防止因 SKU 不存在等原因导致报错
            print(f"--- [Signal Error] 归还库存失败: {e} ---")

    print(f"--- [Signal] Redis Key 已清理: {cache_key} ---")

