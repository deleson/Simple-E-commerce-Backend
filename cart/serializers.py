from rest_framework import serializers
from .models import CartItem
# from products.serializers import ProductReadSerializer, ProductSKUSerializer
from products.serializers import  ProductSKUSerializer  # 我们需要复用ProductSerializer来显示商品信息




class CartItemSerializer(serializers.ModelSerializer):
    # 使用 SKU 的序列化器
    product = ProductSKUSerializer(read_only=True)
    sub_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'quantity', 'sub_total')

    def get_sub_total(self, obj):
        return obj.product.price * obj.quantity


class CartItemAddSerializer(serializers.ModelSerializer):
    # 前端传入的是 SKU 的 ID
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = CartItem
        fields = ('id', 'product_id', 'quantity')

    def create(self, validated_data):
        user = self.context['request'].user
        product_id = validated_data.get('product_id')
        quantity = validated_data.get('quantity')

        # 这里查询的是 ProductSKU
        # 简单处理：如果不存在会报错，DRF会自动处理成400或500
        cart_item, created = CartItem.objects.get_or_create(
            user=user,
            product_id=product_id,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return cart_item

    def to_representation(self, instance):
        """
        在创建/更新成功后，调用此方法生成返回给前端的 JSON。
        我们这里直接复用 CartItemSerializer，这样返回的数据格式就和 GET 列表时一样了。
        """
        serializer = CartItemSerializer(instance, context=self.context)
        return serializer.data