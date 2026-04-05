# orders/serializers.py
from rest_framework import serializers
from .models import Order, OrderItem
from cart.models import CartItem
from addresses.models import UserAddress
from common.exceptions import BusinessError
from .services import create_order_from_cart

# 引入工具类
from common.utils.address import build_address_snapshot

class OrderItemSerializer(serializers.ModelSerializer):
    """ 用于显示订单项的Serializer """

    class Meta:
        model = OrderItem
        # 注意：这里的 product 指的是 ProductSKU 外键
        fields = ['product', 'product_name', 'product_price', 'quantity']


class OrderListSerializer(serializers.ModelSerializer):
    """ 用于“读取”所有订单列表的Serializer """

    class Meta:
        model = Order
        fields = ['order_number', 'total_amount', 'status', 'created_at']


class SubOrderSerializer(serializers.ModelSerializer):
    """ 用于在父订单中展示子订单简略信息 """
    seller_name = serializers.CharField(source='seller.username', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['order_number', 'seller_name', 'status', 'items']


class OrderDetailSerializer(serializers.ModelSerializer):
    # 如果是父订单，展示 sub_orders 字段
    sub_orders = SubOrderSerializer(many=True, read_only=True)
    # 如果是子订单，展示 items 字段
    items = OrderItemSerializer(many=True, read_only=True)
    buyer_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Order
        fields = ['order_number','buyer_name','total_amount', 'status', 'shipping_address', 'items', 'sub_orders']


class OrderCreateSerializer(serializers.ModelSerializer):
    address_id = serializers.IntegerField(write_only=True, required=False, help_text="选择地址ID")
    shipping_address = serializers.CharField(write_only=True, required=False, help_text="手动输入地址")

    class Meta:
        model = Order
        fields = ['address_id', 'shipping_address']

    def validate(self, attrs):
        user = self.context['request'].user

        # 1. 检查购物车
        cart_items = CartItem.objects.filter(user=user)
        if not cart_items.exists():
            raise serializers.ValidationError("购物车为空，无法下单。")

        # 2. 检查库存 (SKU)
        for item in cart_items:
            if item.quantity > item.product.stock:
                raise serializers.ValidationError(f"{item.product.name} 库存不足。")

        # 3. 地址处理 (二选一逻辑)
        address_id = attrs.get('address_id')
        manual_address = attrs.get('shipping_address')

        if address_id:
            try:
                addr = UserAddress.objects.get(id=address_id, user=user)
                # 生成快照
                snapshot = build_address_snapshot(addr)

            except UserAddress.DoesNotExist:
                raise serializers.ValidationError({"address_id": "地址不存在。"})
        elif manual_address:
            if len(manual_address) < 5:
                raise serializers.ValidationError({"shipping_address": "地址太短。"})
            snapshot = manual_address
        else:
            raise serializers.ValidationError("请提供收货地址。")

        attrs['final_address_snapshot'] = snapshot
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        address_snapshot = validated_data["final_address_snapshot"]

        try:
            return create_order_from_cart(
                user=user,
                address_snapshot=address_snapshot,
            )
        except BusinessError as e:
            raise serializers.ValidationError({"detail": str(e)})

# class OrderCreateSerializer(serializers.ModelSerializer):
#     """ 用于“创建”订单的Serializer """
#
#     class Meta:
#         model = Order
#         fields = ['shipping_address', ]
#
#     def validate(self, attrs):
#         """
#         在创建订单前，进行业务逻辑验证。
#         """
#         user = self.context['request'].user
#         cart_items = CartItem.objects.filter(user=user)
#
#         # 1. 验证购物车是否为空
#         if not cart_items.exists():
#             raise serializers.ValidationError("Your cart is empty. Cannot create an order")
#
#         # 2. 验证库存是否充足 (针对 SKU)
#         # 注意：这里我们不做 select_for_update 锁定，因为我们采用的是“付款减库存”模式。
#         # 这里只是一个预检查，防止用户明显超卖。
#         for item in cart_items:
#             # item.product 现在对应的是 ProductSKU 模型实例
#             product_sku = item.product
#             if item.quantity > product_sku.stock:
#                 raise serializers.ValidationError({
#                     'cart_items': f"Insufficient stock for {product_sku.name}. Available: {product_sku.stock}, Requested: {item.quantity}."
#                 })
#
#         return attrs
#
#     def create(self, validated_data):
#         user = self.context['request'].user
#         shipping_address = validated_data['shipping_address']
#
#         # 1. 获取购物车项 (关联的是 SKU)
#         cart_items = CartItem.objects.filter(user=user)
#
#         # 2. 计算总金额 (SKU price * quantity)
#         total_amount = sum(item.product.price * item.quantity for item in cart_items)
#
#         # 【核心修正 2】使用事务保证 订单+订单项 创建的原子性
#         with transaction.atomic():
#             # 3. 创建订单
#             order = Order.objects.create(
#                 user=user,
#                 total_amount=total_amount,
#                 shipping_address=shipping_address
#             )
#
#             # 4. 创建订单项
#             for item in cart_items:
#                 # item.product 是 ProductSKU 实例
#                 OrderItem.objects.create(
#                     order=order,
#                     product=item.product,  # 这里外键关联到 ProductSKU
#                     product_name=item.product.name,  # 记录快照：SKU名称
#                     product_price=item.product.price,  # 记录快照：SKU价格
#                     quantity=item.quantity
#                 )
#
#             # 5. 清空购物车
#             cart_items.delete()
#
#         return order

# class OrderItemSerializer(serializers.ModelSerializer):
#     """ 用于显示订单项的Serializer """
#     class Meta:
#         model = OrderItem
#         fields = ['product','product_name', 'product_price', 'quantity']
#
# class OrderListSerializer(serializers.ModelSerializer):
#     """ 用于“读取”所有订单列表的Serializer """
#     class Meta:
#         model = Order
#         fields = ['order_number', 'total_amount', 'status', 'created_at']
#
# class OrderDetailSerializer(serializers.ModelSerializer):
#     """ 用于“读取”订单详情的Serializer """
#     items = OrderItemSerializer(many=True, read_only=True)
#     class Meta:
#         model = Order
#         fields = ['order_number', 'total_amount', 'status', 'shipping_address', 'created_at', 'items']
#
#
#
#
# class OrderCreateSerializer(serializers.ModelSerializer):
#     """ 用于“创建”订单的Serializer """
#     class Meta:
#         model = Order
#         fields = ['shipping_address',] # 创建订单时，前端只需要提供收货地址
#
#     def validate(self,attrs):
#         """
#         在创建订单前，进行业务逻辑验证。
#         """
#         user = self.context['request'].user
#         cart_items = CartItem.objects.filter(user=user)
#
#         # 1.验证购物车是否为空
#         if not cart_items.exists():
#             raise serializers.ValidationError("Your cart is empty. Cannnot create an order")
#
#         # 2.验证库存是否充足
#         for item in cart_items:
#             product = item.product
#             if item.quantity > product.stock:
#                 # 如果任何一件商品请求量大于库存
#                 raise serializers.ValidationError({
#                     'cart_items': f"Insufficient stock for {product.name}. Available: {product.stock}, Requested: {item.quantity}."
#                 })
#
#         # 如果所有的验证通过，返回原始的attrs
#         return attrs
#
#     def create(self, validated_data):
#         user = self.context['request'].user
#         shipping_address = validated_data['shipping_address']
#
#         # 1. 从购物车获取商品
#         cart_items = CartItem.objects.filter(user=user)
#
#         # 2. 计算总金额
#         total_amount = sum(item.product.price * item.quantity for item in cart_items)
#
#         # 3. 创建订单
#         order = Order.objects.create(
#             user=user,
#             total_amount=total_amount,
#             shipping_address=shipping_address
#         )
#
#         # 4. 创建订单项
#         for item in cart_items:
#             OrderItem.objects.create(
#                 order=order,
#                 product=item.product,
#                 product_name=item.product.name, # 记录快照
#                 product_price=item.product.price, # 记录快照
#                 quantity=item.quantity
#             )
#
#         # 5. 清空购物车
#         cart_items.delete()
#
#         return order

# class OrderCreateSerializer(serializers.ModelSerializer):
#     """
#     处理购物车结算，并按卖家自动拆分订单。
#     """
#
#     class Meta:
#         model = OrderGroup  # 注意：现在创建的是父订单
#         fields = ('shipping_address',)  # 前端依然只需要提供收货地址
#
#         def validate(self,attrs):
#             """
#             在创建订单前，进行业务逻辑验证。
#             """
#             user = self.context['request'].user
#             cart_items = CartItem.objects.filter(user=user)
#
#             # 1.验证购物车是否为空
#             if not cart_items.exists():
#                 raise serializers.ValidationError("Your cart is empty. Cannnot create an order")
#
#             # 2.验证库存是否充足
#             for item in cart_items:
#                 product = item.product
#                 if item.quantity > product.stock:
#                     # 如果任何一件商品请求量大于库存
#                     raise serializers.ValidationError({
#                         'cart_items': f"Insufficient stock for {product.name}. Available: {product.stock}, Requested: {item.quantity}."
#                     })
#
#             # 如果所有的验证通过，返回原始的attrs
#             return attrs
#
#
#     @transaction.atomic  # 整个拆单、创单、减库存的过程必须是原子性的
#     def create(self, validated_data):
#         user = self.context['request'].user
#         shipping_address = validated_data['shipping_address']
#         cart_items = CartItem.objects.filter(user=user).select_related('product__seller')
#
#         if not cart_items:
#             raise serializers.ValidationError("Your cart is empty.")
#
#         # --- 1. 库存检查 (保持不变) ---
#         for item in cart_items:
#             if item.quantity > item.product.stock:
#                 raise serializers.ValidationError(f"Insufficient stock for {item.product.name}.")
#
#         # --- 2. 按卖家对购物车项进行分组 ---
#         # sorted() 确保 groupby 能正常工作
#         cart_items_sorted = sorted(cart_items, key=lambda item: item.product.seller.id)
#         items_by_seller = {k: list(v) for k, v in groupby(cart_items_sorted, key=lambda item: item.product.seller)}
#
#         # --- 3. 创建父订单 (OrderGroup) ---
#         overall_total_amount = sum(item.product.price * item.quantity for item in cart_items)
#         order_group = OrderGroup.objects.create(user=user, total_amount=overall_total_amount)
#
#         # --- 4. 为每个卖家创建子订单 (Order) ---
#         for seller, items in items_by_seller.items():
#             seller_total_amount = sum(item.product.price * item.quantity for item in items)
#
#             # 创建子订单，并关联到父订单
#             sub_order = Order.objects.create(
#                 user=user,
#                 order_group=order_group,
#                 total_amount=seller_total_amount,
#                 shipping_address=shipping_address
#                 # 其他字段使用默认值 (e.g., status=PENDING)
#             )
#
#             # --- 5. 创建订单项并扣减库存 (逻辑不变) ---
#             for item in items:
#                 product = item.product
#                 OrderItem.objects.create(
#                     order=sub_order,
#                     product=product,
#                     product_name=product.name,
#                     product_price=product.price,
#                     quantity=item.quantity
#                 )
#                 product.stock -= item.quantity
#                 product.save()
#
#         # --- 6. 清空购物车 (逻辑不变) ---
#         cart_items.delete()
#
#         return order_group  # 返回父订单