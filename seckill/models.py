# seckill/models.py
from django.db import models
from products.models import ProductSKU


class SeckillEvent(models.Model):
    sku = models.ForeignKey(ProductSKU, on_delete=models.CASCADE, verbose_name="秒杀商品")
    title = models.CharField(max_length=100, verbose_name="活动名称")
    # 秒杀库存单独存放，不直接用 SKU 的普通库存
    seckill_stock = models.PositiveIntegerField(default=0, verbose_name="秒杀库存")
    start_time = models.DateTimeField(verbose_name="开始时间")
    end_time = models.DateTimeField(verbose_name="结束时间")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.sku.name}"