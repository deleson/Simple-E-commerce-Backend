import uuid  # 用于生成唯一的订单号
from django.db import models
from django.conf import settings



class Order(models.Model):
    class OrderStatus(models.TextChoices):
        PENDING = 'PENDING', '待支付'
        PAID = 'PAID', '已支付'
        SHIPPED = 'SHIPPED', '已发货'
        COMPLETED = 'COMPLETED', '已完成'
        CANCELLED = 'CANCELLED', '已取消'
        REFUNDED = 'REFUNDED', '已退款'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')


    # 父订单关联
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_orders', # 如果为空，说明它是父订单；如果有值，说明它是子订单
                               verbose_name="父订单")

    # 卖家关联
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, # 父订单此字段可以为空（或指向平台），子订单必须指向具体卖家
                               related_name='sold_orders', verbose_name="卖家")

    order_number = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)    # 使用UUID作为订单号，比自增ID更安全
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    shipping_address = models.TextField()  # 简化处理，直接用文本字段
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 【新增】逻辑删除标记
    # 默认为 False (未删除/可见)
    is_deleted_by_buyer = models.BooleanField(default=False, verbose_name="买家已删除")
    is_deleted_by_seller = models.BooleanField(default=False, verbose_name="卖家已删除")


    class Meta:
        verbose_name = "订单"
        verbose_name_plural="订单列表"

    def __str__(self):
        return f"Order {self.order_number} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # product = models.ForeignKey('products.Product', on_delete=models.PROTECT)  # 商品被删除时，保护订单项
    product = models.ForeignKey('products.ProductSKU', on_delete=models.PROTECT)  #

    # 记录下单时的快照信息
    product_name = models.CharField(max_length=200)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    class Meta:
        verbose_name = "订单项"
        verbose_name_plural="订单项列表"

    def __str__(self):
        return f"{self.quantity} of {self.product_name}"