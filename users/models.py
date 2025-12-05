from django.db import models
from django.contrib.auth.models import AbstractUser

class MyUser(AbstractUser):
    # 你可以在这里添加未来想扩展的字段，比如
    # nickname = models.CharField(max_length=50, blank=True)
    # avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)

    class Meta:
        verbose_name = "用户"
        verbose_name_plural ="用户"
