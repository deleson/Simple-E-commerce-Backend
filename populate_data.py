import os
import django
import random

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings.base')
django.setup()

from django.contrib.auth import get_user_model

from products.models import Category, ProductSPU, ProductSKU
from django.db import transaction


User = get_user_model()

def populate(n=100):
    print(f"开始生成 {n} 条商品数据...")

    # 1. 确保有个卖家
    seller, _ = User.objects.get_or_create(username="seller_A")

    # 2. 确保有个分类
    category, _ = Category.objects.get_or_create(name="服装")

    # 3. 批量创建商品
    with transaction.atomic():
        for i in range(n):
            # 创建 SPU
            spu = ProductSPU.objects.create(
                name=f"批量测试商品 {i}",
                description="这是一个用于测试性能的商品数据",
                category=category,
                seller=seller
            )

            # 每个 SPU 创建 2 个 SKU
            ProductSKU.objects.create(
                spu=spu,
                name=f"规格 A-{i}",
                specifications={"type": "A"},
                price=100.00,
                stock=999,
                image=None
            )
            ProductSKU.objects.create(
                spu=spu,
                name=f"规格 B-{i}",
                specifications={"type": "B"},
                price=200.00,
                stock=999,
                image=None
            )

    print(f"成功生成 {n} 个 SPU 和 {n * 2} 个 SKU！")


if __name__ == '__main__':
    populate(5)  # 先生成 50 个试试，觉得不够可以改成 200