from django.db import models
from products.models import ProductSKU


class SeckillEvent(models.Model):
    sku = models.ForeignKey(ProductSKU, on_delete=models.CASCADE, verbose_name="秒杀商品")
    title = models.CharField(max_length=100, verbose_name="活动名称")
    seckill_stock = models.PositiveIntegerField(default=0, verbose_name="秒杀库存")
    start_time = models.DateTimeField(verbose_name="开始时间")
    end_time = models.DateTimeField(verbose_name="结束时间")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.sku.name}"


class SeckillDeductionRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', '待处理'
        SUCCESS = 'SUCCESS', '成功'
        FAILED = 'FAILED', '失败'
        DEAD = 'DEAD', '死信'

    request_id = models.CharField(max_length=64, unique=True, verbose_name='请求ID')
    user_id = models.PositiveIntegerField(verbose_name='用户ID')
    event_id = models.PositiveIntegerField(verbose_name='活动ID')

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    is_compensated = models.BooleanField(default=False)
    compensate_count = models.PositiveIntegerField(default=0)

    failure_reason = models.CharField(max_length=500, blank=True, default='')
    payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '秒杀扣减流水'
        verbose_name_plural = '秒杀扣减流水'

    def __str__(self):
        return f"{self.request_id} - {self.status}"
