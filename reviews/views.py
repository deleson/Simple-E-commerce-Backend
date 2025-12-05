from rest_framework import viewsets, permissions
from .models import Review
from .serializers import ReviewSerializer, ReviewCreateSerializer
from .permissions import HasPurchaseProductPermission
from users.permissions import IsOwnerOrReadOnly
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()

    def get_serializer_class(self):
        # 根据动作选择不同的Serializer
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer

    def get_permissions(self):
        # print("ssssssssssssssssssssssss")
        # print(f"so this {self.action}")
        # 根据动作设置不同的权限
        if self.action == 'create':
            # 只有购买过的用户才能创建评论
            return [permissions.IsAuthenticated(), HasPurchaseProductPermission()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # 修改或删除，需要是该评论的所有者
            return [IsOwnerOrReadOnly()]
        # 列表和详情页，任何人都可以查看
        return [permissions.AllowAny()]

    def get_queryset(self):
        # 确保只返回当前URL指定的商品的评论
        product_id = self.kwargs.get('product_pk')
        if product_id:
            return Review.objects.filter(product_id=product_id)
        return super().get_queryset()

    def perform_create(self, serializer):
        # 自动设置评论的作者和关联的商品
        product_id = self.kwargs.get('product_pk')
        serializer.save(user=self.request.user, product_id=product_id)