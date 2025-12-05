from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=100,unique=True,verbose_name="分类名称")
    description = models.TextField(blank=True,null=True,verbose_name="分类描述")

    class Meta:
        verbose_name = "商品种类"
        verbose_name_plural="商品种类"

    def __str__(self):
        return self.name

class ProductSPU(models.Model):
    """
    SPU (Standard Product Unit) - 标准化产品单元
    代表一类商品，与具体规格（颜色、尺码）无关。
    """
    name = models.CharField(max_length=200, verbose_name="商品SPU名称")
    description = models.TextField(verbose_name="商品描述")
    category = models.ForeignKey(Category, related_name='spus', on_delete=models.SET_NULL, null=True, verbose_name="所属分类")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='spus', verbose_name="所属卖家")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="上架时间")

    class Meta:
        verbose_name = "商品SPU"
        verbose_name_plural="商品SPU"

    def __str__(self):
        return self.name

class ProductSKU(models.Model):
    """
    SKU (Stock Keeping Unit) - 库存量单位
    代表一个具体的可售卖商品规格，价格和库存与SKU绑定。
    """
    spu = models.ForeignKey(ProductSPU, on_delete=models.CASCADE, related_name='skus', verbose_name="所属SPU")
    name = models.CharField(max_length=200, verbose_name="商品SKU名称", help_text="例如：红色 L码")
    specifications = models.JSONField(default=dict, verbose_name="规格参数", help_text="例如：{'颜色': '红色', '尺码': 'L'}")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="价格")
    stock = models.PositiveIntegerField(default=0, verbose_name="库存")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="SKU图片")


    class Meta:
        verbose_name = "商品SKU"
        verbose_name_plural="商品SKU"

    def __str__(self):
        return f"{self.spu.name} - {self.name}"



# class Product(models.Model):
#
#     seller = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#     )
#     name = models.CharField(max_length=200,verbose_name="商品名称")
#     description = models.TextField(verbose_name="商品详情")
#     price = models.DecimalField(max_digits=10,decimal_places=2,verbose_name="价格")
#     stock = models.PositiveIntegerField(default=0,verbose_name="库存")
#     image = models.ImageField(upload_to='products/',blank=True,null=True,verbose_name="商品图片")
#     category = models.ForeignKey(Category,related_name='products',on_delete=models.SET_NULL,null=True,verbose_name="所属分类")
#     created_at = models.DateTimeField(auto_now_add=True,verbose_name="上架时间")
#
#     def __str__(self):
#         return self.name
