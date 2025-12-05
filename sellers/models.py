# sellers/models.py
from django.db import models
from django.conf import settings

class SellerProfile(models.Model):
    # 一对一关联到用户，一个用户只能开一个店
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller_profile')
    shop_name = models.CharField(max_length=100, unique=True, verbose_name="店铺名称")
    shop_description = models.TextField(blank=True, null=True, verbose_name="店铺简介")
    # 简单的Logo字段，实际生产可以用云存储
    logo = models.ImageField(upload_to='shop_logos/', blank=True, null=True, verbose_name="店铺Logo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "店铺详情"
        verbose_name_plural ="店铺详情"

    def __str__(self):
        return self.shop_name


class Wallet(models.Model):
    """
    卖家虚拟钱包
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet',
                                verbose_name="所属卖家")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="可用余额")
    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="累计收入")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "商家钱包"
        verbose_name_plural ="商家钱包"

    def __str__(self):
        return f"{self.user.username} - 余额: {self.balance}"


class WalletTransaction(models.Model):
    """
    资金流水记录
    """

    class TransactionType(models.TextChoices):
        ORDER_INCOME = 'INCOME', '订单收入'
        WITHDRAW = 'WITHDRAW', '提现支出'
        REFUND = 'REFUND', '退款扣除'

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions', verbose_name="所属钱包")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="变动金额")
    type = models.CharField(max_length=20, choices=TransactionType.choices, verbose_name="交易类型")

    # 关联具体的子订单 (如果是收入/退款)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='wallet_transactions', verbose_name="关联订单")

    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        verbose_name = "商家流水"
        verbose_name_plural ="商家流水"

    def __str__(self):
        return f"[{self.get_type_display()}] {self.amount}"