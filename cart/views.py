from rest_framework import viewsets, permissions
from .models import CartItem
from .serializers import CartItemSerializer, CartItemAddSerializer
from users.permissions import IsCustomerUser
class CartItemViewSet(viewsets.ModelViewSet):
    """
    一个处理购物车所有操作 (CRUD) 的ViewSet。
    """
    queryset = CartItem.objects.all()
    permission_classes = [IsCustomerUser]
    def get_serializer_class(self):
        # 根据不同的action（动作），使用不同的serializer
        if self.action == 'create':
            return CartItemAddSerializer
        return CartItemSerializer

    def get_queryset(self):
        # 只返回当前登录用户的购物车项
        return self.queryset.filter(user=self.request.user)#.select_related('product', 'product__spu')

    def perform_create(self, serializer):
        # 在创建对象时，不需要前端传入user，而是直接使用当前请求的用户
        serializer.save(user=self.request.user)