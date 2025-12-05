from django.shortcuts import render
from rest_framework import viewsets,permissions
from .models import UserAddress
from .serializers import UserAddressSerializer
from users.permissions import IsOwnerOrReadOnly

# Create your views here.


class UserAddressViewSet(viewsets.ModelViewSet):
    """
    收货地址管理视图
    """
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated,IsOwnerOrReadOnly]

    def get_queryset(self):
        #只能看到自己的地址
        return UserAddress.objects.filter(user=self.request.user)

    def perform_create(self,serializer):
        # 如果前端传入is_default = True，先把用户其他地址设为False
        if serializer.validated_data.get('is_default'):
            UserAddress.objects.filter(user=self.request.user,is_default=True).update(is_default=False)

        # 保存并管理当前用户
        serializer.save(user=self.request.user)

    def perform_update(self,serializer):
        # 更新时也要处理互斥逻辑
        if serializer.validated_data.get('is_default'):
            UserAddress.objects.filter(user=self.request.user, is_default=True).update(is_default=False)

        # 保存并管理当前用户
        serializer.save()