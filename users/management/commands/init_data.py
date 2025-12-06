import os
import random
import uuid
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group  # 引入 Group
from django.db import transaction

# 引入所有业务模型
from products.models import Category, ProductSPU, ProductSKU
from sellers.models import SellerProfile, Wallet
from addresses.models import UserAddress
from orders.models import Order, OrderItem
from reviews.models import Review
from seckill.models import SeckillEvent

User = get_user_model()


class Command(BaseCommand):
    help = '初始化全套系统数据 (多商家、买家、商品、订单、评论、秒杀)'

    def handle(self, *args, **options):
        self.stdout.write("🚀 开始全量数据初始化...")

        # ==========================================
        # 0. 初始化角色组 (Customer & Seller)
        # ==========================================
        customer_group, _ = Group.objects.get_or_create(name='Customer')
        seller_group, _ = Group.objects.get_or_create(name='Seller')
        self.stdout.write(self.style.SUCCESS(f'✅ 角色组已就绪: Customer, Seller'))

        # ==========================================
        # 1. 超级管理员
        # ==========================================
        admin_username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        if not User.objects.filter(username=admin_username).exists():
            User.objects.create_superuser(
                admin_username,
                os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com'),
                os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123456')
            )
            self.stdout.write(self.style.SUCCESS(f'✅ 管理员已创建: {admin_username}'))

        # ==========================================
        # 2. 创建多个卖家 (拥有双重身份)
        # ==========================================
        sellers = []
        seller_names = ['Apple官方店', '小米旗舰店', 'Nike直营', '优衣库', '极客工坊']

        for i, shop_name in enumerate(seller_names):
            username = f"seller_{i + 1}"
            if not User.objects.filter(username=username).exists():
                with transaction.atomic():
                    user = User.objects.create_user(username, f'{username}@test.com', 'password123')

                    # 【核心修改】卖家同时加入 Seller 和 Customer 组
                    user.groups.add(seller_group, customer_group)

                    # 创建店铺和钱包
                    SellerProfile.objects.create(user=user, shop_name=shop_name,
                                                 shop_description=f"{shop_name} - 品质保证")
                    Wallet.objects.create(user=user)
                    sellers.append(user)
                    self.stdout.write(f"   - 创建卖家: {shop_name} ({username}) [已分配 Seller+Customer 组]")
            else:
                sellers.append(User.objects.get(username=username))

        self.stdout.write(self.style.SUCCESS(f'✅ {len(sellers)} 个卖家账号就绪'))

        # ==========================================
        # 3. 创建多个买家 (仅 Customer)
        # ==========================================
        buyers = []
        for i in range(10):  # 10个买家
            username = f"buyer_{i + 1}"
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username, f'{username}@test.com', 'password123')

                # 【核心修改】买家加入 Customer 组
                user.groups.add(customer_group)

                # 为每个买家创建地址
                UserAddress.objects.create(
                    user=user,
                    signer_name=f"用户{i + 1}",
                    signer_mobile=f"1380013800{i}",
                    province="上海市", city="上海市", district="浦东新区",
                    address=f"张江高科路 {random.randint(1, 999)} 号",
                    is_default=True
                )
                buyers.append(user)
            else:
                buyers.append(User.objects.get(username=username))

        self.stdout.write(self.style.SUCCESS(f'✅ {len(buyers)} 个买家账号及地址就绪'))

        # ==========================================
        # 4. 商品分类与 SKU 生成 (保持不变)
        # ==========================================
        category_names = ["手机通讯", "电脑办公", "男装女装", "运动户外", "图书音像"]
        categories = []
        for name in category_names:
            cat, _ = Category.objects.get_or_create(name=name)
            categories.append(cat)

        TARGET_SPU = 50
        current_spu = ProductSPU.objects.count()
        if current_spu < TARGET_SPU:
            self.stdout.write(f"正在生成商品数据...")
            adj = ["新款", "热销", "限量", "经典", "高配"]
            noun = ["手机", "电脑", "跑鞋", "外套", "键盘"]

            with transaction.atomic():
                for i in range(TARGET_SPU - current_spu):
                    seller = random.choice(sellers)
                    spu = ProductSPU.objects.create(
                        name=f"{seller.seller_profile.shop_name}-{random.choice(adj)}{random.choice(noun)} {i}",
                        description="自动生成的测试商品",
                        category=random.choice(categories),
                        seller=seller
                    )
                    ProductSKU.objects.create(spu=spu, name="标准版", price=Decimal(random.randint(50, 1000)),
                                              stock=100, specifications={"type": "std"})
                    ProductSKU.objects.create(spu=spu, name="豪华版", price=Decimal(random.randint(1001, 2000)),
                                              stock=50, specifications={"type": "pro"})

        all_skus = list(ProductSKU.objects.all())
        self.stdout.write(self.style.SUCCESS(f'✅ 商品库就绪 (SPU: {ProductSPU.objects.count()}, SKU: {len(all_skus)})'))

        # ==========================================
        # 5. 模拟历史订单 (保持不变)
        # ==========================================
        if Order.objects.count() < 20:
            self.stdout.write("正在模拟历史交易订单...")
            with transaction.atomic():
                for _ in range(20):
                    buyer = random.choice(buyers)
                    address = buyer.addresses.first()
                    if not address: continue
                    address_snapshot = f"{address.signer_name} {address.signer_mobile} {address.address}"

                    selected_skus = random.sample(all_skus, random.randint(1, 3))
                    seller_groups = {}
                    grand_total = Decimal(0)

                    for sku in selected_skus:
                        seller = sku.spu.seller
                        if seller not in seller_groups:
                            seller_groups[seller] = []
                        qty = random.randint(1, 3)
                        seller_groups[seller].append((sku, qty))
                        grand_total += sku.price * qty

                    parent_order = Order.objects.create(
                        user=buyer,
                        total_amount=grand_total,
                        shipping_address=address_snapshot,
                        status=Order.OrderStatus.PAID
                    )

                    for seller, items in seller_groups.items():
                        sub_total = sum(s.price * q for s, q in items)
                        sub_order = Order.objects.create(
                            parent=parent_order,
                            user=buyer,
                            seller=seller,
                            total_amount=sub_total,
                            shipping_address=address_snapshot,
                            status=Order.OrderStatus.PAID
                        )

                        for sku, qty in items:
                            OrderItem.objects.create(
                                order=sub_order,
                                product=sku,
                                product_name=f"{sku.spu.name} {sku.name}",
                                product_price=sku.price,
                                quantity=qty
                            )
                            if random.choice([True, False]):
                                try:
                                    # 【核心修复】使用 try-except 捕获重复评论错误
                                    Review.objects.create(
                                        user=buyer,
                                        product=sku,
                                        rating=random.randint(3, 5),
                                        comment=f"不错，是正品！(订单号 {sub_order.order_number})"
                                    )
                                except Exception:
                                    # 如果报错(比如该用户已经评过该商品)，直接跳过，不中断脚本
                                    pass

            self.stdout.write(self.style.SUCCESS(f'✅ 历史订单与评论模拟完成'))

        # ==========================================
        # 6. 创建秒杀活动 (保持不变)
        # ==========================================
        if not SeckillEvent.objects.exists():
            target_sku = random.choice(all_skus)
            SeckillEvent.objects.create(
                sku=target_sku,
                title=f"限时抢购 - {target_sku.spu.name}",
                seckill_stock=10,
                start_time=timezone.now(),
                end_time=timezone.now() + timedelta(hours=24)
            )
            self.stdout.write(self.style.SUCCESS(f'✅ 秒杀活动已创建'))

        self.stdout.write(self.style.SUCCESS('🎉🎉🎉 全套演示数据初始化完成！'))