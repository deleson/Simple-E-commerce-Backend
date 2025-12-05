# sellers/views.py
from .models import WalletTransaction
from .serializers import SellerProfileSerializer, WalletSerializer, \
    WalletTransactionSerializer

from orders.models import OrderItem

from rest_framework import generics, permissions
from users.permissions import IsSellerUser
from orders.models import Order
from orders.serializers import OrderDetailSerializer

# 1. 管理店铺信息的视图
class SellerProfileView(generics.RetrieveUpdateAPIView):
    """
    获取或更新自己的店铺信息
    """
    permission_classes = [permissions.IsAuthenticated, IsSellerUser]
    serializer_class = SellerProfileSerializer

    def get_object(self):
        # 直接返回当前用户的 profile
        return self.request.user.seller_profile

# # 2. 查看销售记录的视图 (核心功能)
# class SellerOrderListView(generics.ListAPIView):
#     """
#     列出所有包含自己商品的订单项
#     """
#     permission_classes = [permissions.IsAuthenticated, IsSellerUser]
#     serializer_class = SellerOrderItemSerializer
#
#     def get_queryset(self):
#         # 关键查询逻辑：
#         # 1. 从 OrderItem 表查询
#         # 2. 关联 product (SKU) -> spu -> seller
#         # 3. 筛选 seller 是当前用户
#         return OrderItem.objects.filter(product__spu__seller=self.request.user).select_related('order').order_by('-order__created_at')

class SellerOrderListView(generics.ListAPIView):
    """
    卖家视图：只看属于自己店铺的【子订单】。
    """
    permission_classes = [permissions.IsAuthenticated, IsSellerUser]
    serializer_class = OrderDetailSerializer

    def get_queryset(self):
        # 【优化后】
        return Order.objects.filter(
            seller=self.request.user,
            parent__isnull=False
        ).select_related(
            'user'  # 优化：一次性查出买家信息
        ).prefetch_related(
            'items__product__spu' # 深度优化：一次性查出 Items -> SKU -> SPU (为了显示商品全名)
        ).order_by('-created_at')

class SellerOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    允许卖家查看、修改(如发货状态)、删除(逻辑删除)单个子订单
    """
    permission_classes = [permissions.IsAuthenticated, IsSellerUser]
    serializer_class = OrderDetailSerializer
    lookup_field = 'order_number'  # 告诉 DRF 使用 order_number 字段进行对象查找

    def get_queryset(self):
        # 卖家只能操作自己的子订单，且没被自己删掉的
        return Order.objects.filter(
            seller=self.request.user,
            parent__isnull=False,
            is_deleted_by_seller=False
        )

    def perform_destroy(self, instance):
        """
        卖家删除逻辑：标记为卖家已删除
        """
        instance.is_deleted_by_seller = True
        instance.save()




# 查看钱包余额
class SellerWalletView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSellerUser]
    serializer_class = WalletSerializer

    def get_object(self):
        # 确保获取的是当前用户的钱包
        # 如果没有钱包(比如老数据)，这里可能会报错，生产环境建议加 try-except 或 get_or_create
        return self.request.user.wallet

# 查看资金流水
class SellerTransactionListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSellerUser]
    serializer_class = WalletTransactionSerializer

    def get_queryset(self):
        return WalletTransaction.objects.filter(wallet__user=self.request.user).order_by('-created_at')