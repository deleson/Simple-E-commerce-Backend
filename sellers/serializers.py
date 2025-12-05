from rest_framework import serializers
from .models import SellerProfile, Wallet, WalletTransaction
from orders.models import OrderItem


class SellerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerProfile
        fields = ['shop_name','shop_description','logo','created_at']
        read_only_fields = ['created_at']





class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['balance', 'total_income', 'updated_at']

class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ['amount', 'type', 'created_at', 'description']


# class SellerOrderItemSerializer(serializers.ModelSerializer):
#     """
#     卖家查看自己卖出的商品项
#     需要显示：所属订单号、收货地址、商品名、数量、金额、下单时间
#     """
#     order_number = serializers.CharField(source='order.order_number', read_only=True)
#     shipping_address = serializers.CharField(source='order.shipping_address', read_only=True)
#     order_created_at = serializers.DateTimeField(source='order.created_at', read_only=True)
#
#     # 支付状态 (从父订单获取)
#     payment_status = serializers.CharField(source='order.status', read_only=True)
#
#     class Meta:
#         model = OrderItem
#         fields = [
#             'id', 'order_number', 'payment_status', 'shipping_address',
#             'product_name', 'product_price', 'quantity', 'order_created_at'
#         ]