from django.db import models
from django.conf import settings #方便引用自定义的User模型

# Create your models here.

class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='cart_items')
    # product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey('products.ProductSKU', on_delete=models.CASCADE, related_name='cart_items')  # <--- 新代码

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        # 确保同一个用户对同一个商品只有一个购物车记录
        unique_together = ('user','product')


        verbose_name = "购物单"
        verbose_name_plural = "购物车"

    def __str__(self):
        return f"{self.quantity} of {self.product.name} for {self.user.username}"