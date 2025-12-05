# seckill/admin.py
from django.contrib import admin
from django.core.cache import cache
from .models import SeckillEvent


@admin.register(SeckillEvent)
class SeckillEventAdmin(admin.ModelAdmin):
    list_display = ('id','title', 'sku', 'seckill_stock', 'start_time')

