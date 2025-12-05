from django.db import models
import uuid

# Create your models here.
class Payment(models.Model):
    class PaymentStatus(models.TextChoices):
        SUCCESS = 'SUCCESS', '成功'
        FAILED = 'FAILED', '失败'

    # 交易类型
    class PaymentType(models.TextChoices):
        PAYMENT = 'PAYMENT', '支付'
        REFUND = 'REFUND', '退款'

    order = models.OneToOneField('orders.Order',on_delete=models.CASCADE,related_name='payment')
    amount = models.DecimalField(max_digits=10,decimal_places=2)
    status = models.CharField(max_length=20,choices=PaymentStatus.choices)
    transaction_id = models.CharField(max_length=100, unique=True, verbose_name="支付平台交易号")
    created_at = models.DateTimeField(auto_now_add=True)

    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.PAYMENT,
                                    verbose_name="交易类型")




    class Meta:
        verbose_name = "支付单"
        verbose_name_plural="支付清单"

    def __str__(self):
        # 显示：[退款] 200.00元 - 订单号: xxx
        return f"[{self.get_payment_type_display()}] {self.amount}元 - 订单号: {self.order.order_number}"
