# orders/views.py
from django.db.models import Prefetch
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from common.exceptions import BusinessError
from .services import refund_sub_order
from .models import Order
from .serializers import OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer
from users.permissions import IsCustomerUser, IsOwnerOrReadOnly
from django.conf import settings

# 引入工具类
from common.utils.alipay import build_alipay_client


class OrderViewSet(viewsets.ModelViewSet):

    lookup_field = 'order_number'  # 告诉 DRF 使用 order_number 字段进行对象查找

    def get_permissions(self):
        # 根据不同的操作应用不同的权限
        if self.action == 'create':
            # 创建订单需要是 'Customer'
            return [permissions.IsAuthenticated(),IsCustomerUser()]

        # 对于详情查看(retrieve)、支付(pay)、更新(update)、删除(destroy)等
        # 针对单个订单的操作，需要是订单的所有者
        return [permissions.IsAuthenticated(),IsOwnerOrReadOnly()]

    def get_queryset(self):
        user = self.request.user

        # 1. 定义子订单的预取逻辑：查子订单的同时，select_related 它的卖家
        sub_orders_prefetch = Prefetch(
            'sub_orders',
            queryset=Order.objects.select_related('seller', 'user')
        )

        queryset = Order.objects.filter(
            user=user,
            is_deleted_by_buyer=False
        ).select_related(
            'seller', 'user'  # 优化父订单自己的外键
        ).prefetch_related(
            'items',  # 优化父订单的 items
            sub_orders_prefetch,  # 【核心修正】使用定义好的深度预取对象
            'sub_orders__items'  # 优化子订单下的 items
        ).order_by('-created_at')

        if self.action == 'list':
            return queryset.filter(parent__isnull=True)

        return queryset


    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        elif self.action == "retrieve":
            return OrderDetailSerializer
        return OrderListSerializer


    # 【新功能】使用 @action 装饰器创建一个自定义的路由
    @action(detail=True, methods=['post'])
    def pay(self, request, order_number=None):
        """
        处理订单支付的自定义动作。
        """
        order = self.get_object() # 获取当前订单实例


        # 检查是否为父定单
        if order.parent:
             return Response(
                 {'error': 'You cannot pay for a sub-order directly. Please pay the parent order.'},
                 status=status.HTTP_400_BAD_REQUEST
             )


        # 1. 检查订单状态是否为“待支付”
        if order.status != Order.OrderStatus.PENDING:
            return Response(
                {'error': 'This order cannot be paid for.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 初始化支付宝 SDK
        alipay = build_alipay_client()

        # 生成电脑网站支付页面 URL 的参数部分
        payment_params = alipay.api_alipay_trade_page_pay(
            out_trade_no=str(order.order_number),
            total_amount=float(order.total_amount),
            subject=f"电商平台订单 - {order.order_number}",
            return_url=f"{settings.SITE_DOMAIN}/api/payment/success/",  # 同步回调地址
            notify_url=f"{settings.PUBLIC_DOMAIN.strip()}/api/payment/webhook/"  # 异步通知地址 (必须是公网)
        )

        # 完整的支付网关 URL
        payment_url = settings.ALIPAY_CONFIG['ALIPAY_GATEWAY_URL'] + "?" + payment_params

        return Response({'payment_url': payment_url}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def refund(self, request, order_number=None):
        """
        子订单退款接口
        """
        sub_order = self.get_object()

        try:
            response = refund_sub_order(sub_order=sub_order)
            return Response(
                {"message":"refund correct","alipay_response":response},
                status=status.HTTP_200_OK,
            )


        except BusinessError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": f"系统错误: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        #创建订单时自动关联当前用户
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        """
        【核心逻辑】重写删除行为
        当前端发送 DELETE 请求时，DRF 会调用这个方法。
        原生的行为是 instance.delete() (物理删除)，
        我们将其改为更新标记位。
        """
        instance.is_deleted_by_buyer = True
        instance.save()

        if instance.sub_orders.exists():
            instance.sub_orders.update(is_deleted_by_buyer=True)