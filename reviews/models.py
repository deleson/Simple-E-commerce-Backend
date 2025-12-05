from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='reviews')
    # product = models.ForeignKey('products.Product',on_delete=models.CASCADE,related_name='reviews')
    product = models.ForeignKey('products.ProductSKU', on_delete=models.CASCADE, related_name='reviews')  # <--- 新代码


    #评分，限制1到5之间
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1),MaxValueValidator(5)]
    )

    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 同一个用户对同一个商品只能评论一次
        unique_together = ('user','product')
        ordering = ['-created_at']  #m默认按创建时间倒序
        verbose_name = "评论"
        verbose_name_plural = "评论"

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"

