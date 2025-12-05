# seckill/management/commands/return_seckill_stock.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F

from products.models import ProductSKU
from seckill.models import SeckillEvent
from django_redis import get_redis_connection


class Command(BaseCommand):
    help = '【活动结束】将 Redis 中未卖完的秒杀库存归还给主商品表 SKU'

    def add_arguments(self, parser):
        parser.add_argument('event_id', type=int, help='秒杀活动ID')

    def handle(self, *args, **options):
        event_id = options['event_id']

        try:
            event = SeckillEvent.objects.get(id=event_id)

            # 1. 连接 Redis (注意：使用专门存库存的那个连接别名，比如 "seckill" 或 "default")
            # 务必确认和你 views.py 里用的是同一个库！
            conn = get_redis_connection("seckill")
            cache_key = f'seckill_stock_{event_id}'

            # 2. 从 Redis 获取最准确的剩余库存
            redis_stock_raw = conn.get(cache_key)

            if redis_stock_raw is None:
                self.stdout.write(
                    self.style.WARNING(f"Redis 中找不到 Key: {cache_key}，无法归还库存。可能已过期或未预热。"))
                return

            # Redis 取出来是 bytes，转成 int
            try:
                remaining_stock = int(redis_stock_raw)
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Redis 数据异常: {redis_stock_raw}"))
                return

            self.stdout.write(f"Redis 中剩余库存: {remaining_stock}")

            # 3. 开始归还逻辑
            with transaction.atomic():
                if remaining_stock > 0:
                    # 1. 加回主表 SKU (使用 update)
                    # 注意：使用 event.sku_id 直接获取外键ID，避免多一次查询 event.sku 对象
                    ProductSKU.objects.filter(id=event.sku_id).update(
                        stock=F('stock') + remaining_stock
                    )

                    self.stdout.write(self.style.SUCCESS(f"已将 {remaining_stock} 件库存归还至 SKU ID: {event.sku_id}"))
                else:
                    self.stdout.write("Redis 库存为 0，无需归还。")

                # 2. 清空秒杀表 (使用 update)
                # 同样使用 filter(id=...).update(...)
                SeckillEvent.objects.filter(id=event.id).update(seckill_stock=0)

                # 3. 清理 Redis
                conn.delete(cache_key)
                self.stdout.write(self.style.SUCCESS(f"已清理 Redis Key: {cache_key}"))

        except SeckillEvent.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"找不到 ID 为 {event_id} 的秒杀活动"))