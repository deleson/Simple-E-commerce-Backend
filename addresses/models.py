from django.db import models
from django.conf import settings

# Create your models here.

class UserAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses',
                             verbose_name="所属用户")

    # 收货人信息
    signer_name     = models.CharField(max_length=100,verbose_name="收货人姓名")
    signer_mobile   = models.CharField(max_length=11,verbose_name="收货人手机号")

    # 地址详情
    province = models.CharField(max_length=100,verbose_name="省")
    city     = models.CharField(max_length=100,verbose_name="市")
    district = models.CharField(max_length=100, verbose_name="区/县")
    address  = models.CharField(max_length=200, verbose_name="详细地址")

    # 默认地址标记
    is_default = models.BooleanField(default=False,verbose_name="是否默认")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        verbose_name = "收货地址"
        verbose_name_plural = verbose_name
        ordering = ['-is_default', '-updated_at']  # 默认地址排最前

    def __str__(self):
        return f"{self.signer_name} - {self.province}{self.city}{self.district}{self.address}"

