# orders/views.py
import uuid
from django.db.models import Prefetch

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
# 【关键】引入数据库事务
from django.db import transaction

from .models import Order
from .serializers import OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer
# 引入支付模型
from payment.models import Payment
from users.permissions import IsCustomerUser, IsOwnerOrReadOnly

# 引入支付宝
from django.conf import settings
from alipay import AliPay

from sellers.models import WalletTransaction
from products.models import ProductSKU


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
        alipay = AliPay(
            appid=settings.ALIPAY_CONFIG['APPID'],
            app_notify_url=None,
            app_private_key_string=settings.ALIPAY_CONFIG['APP_PRIVATE_KEY_STRING'],
            alipay_public_key_string=settings.ALIPAY_CONFIG['ALIPAY_PUBLIC_KEY_STRING'],
            sign_type=settings.ALIPAY_CONFIG['SIGN_TYPE'],
            debug=settings.ALIPAY_CONFIG['DEBUG']
        )

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
        用户对某个子订单发起退款 -> 支付宝退钱 -> 扣除卖家余额 -> 恢复库存
        """
        # 1.获取想要退款的子订单
        sub_order = self.get_object()

        # 检查是否合法：必须是子订单，且已支付
        if not sub_order.parent:
            return Response({'error': '只能对子订单发起退款申请。'}, status=status.HTTP_400_BAD_REQUEST)

        if sub_order.status != Order.OrderStatus.PAID:
            return Response({'error': '只有已支付的订单才能退款。'}, status=status.HTTP_400_BAD_REQUEST)

        # 2.初始化支付宝SDK
        alipay = AliPay(
            appid=settings.ALIPAY_CONFIG['APPID'],
            app_notify_url=None,
            app_private_key_string=settings.ALIPAY_CONFIG['APP_PRIVATE_KEY_STRING'],
            alipay_public_key_string=settings.ALIPAY_CONFIG['ALIPAY_PUBLIC_KEY_STRING'],
            sign_type=settings.ALIPAY_CONFIG['SIGN_TYPE'],
            debug=settings.ALIPAY_CONFIG['DEBUG']
        )

        # 3.发起支付宝退款请求
        # 这是一个同步调用，支付宝会直接返回结果
        refund_request_no = str(uuid.uuid4())  # 本次退款操作的唯一流水号

        try:
            response = alipay.api_alipay_trade_refund(
                out_trade_no=str(sub_order.parent.order_number),
                refund_amount = float(sub_order.total_amount),
                out_request_no=refund_request_no,
                refund_reason = f"Refund for sub-order{sub_order.order_number}"
            )

            # 4. 处理支付宝响应
            # code='10000' 代表接口调用成功，fund_change='Y' 代表资金确实发生了变动
            if response.get('code') == '10000' and response.get('fund_change') == 'Y':

                with transaction.atomic():
                    # A. 更新子订单状态
                    sub_order.status = Order.OrderStatus.REFUNDED
                    sub_order.save()

                    # B. 库存回滚 (加回去)
                    # 使用 select_for_update 锁定商品行，保证并发安全
                    for item in sub_order.items.all():
                        try:
                            product_sku = ProductSKU.objects.select_for_update().get(id=item.product.id)
                            product_sku.stock += item.quantity
                            product_sku.save()
                        except ProductSKU.DoesNotExist:
                            continue  # 商品如果被删了就不处理库存了

                    # C. 卖家资金扣除
                    if hasattr(sub_order.seller, 'wallet'):
                        wallet = sub_order.seller.wallet
                        refund_money = sub_order.total_amount

                        # 直接扣减余额 (允许变负，或者你可以加逻辑判断 check balance >= refund_money)
                        wallet.balance -= refund_money
                        wallet.total_income -= refund_money
                        wallet.save()

                        # 记录退款流水
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            amount=-refund_money,  # 负数表示支出
                            type=WalletTransaction.TransactionType.REFUND,
                            order=sub_order,
                            description=f"订单退款：{sub_order.order_number}"
                        )

                    # 记录这是针对子订单的退款
                    Payment.objects.create(
                        order=sub_order,  # 关联到子订单
                        amount=sub_order.total_amount,
                        status=Payment.PaymentStatus.SUCCESS,
                        payment_type=Payment.PaymentType.REFUND,  # 标记为退款
                        # 支付宝退款接口通常不返回新的 trade_no，而是沿用原支付的 trade_no
                        # 或者返回一个本次操作的 refund_id。
                        # 这里为了唯一性，我们可以存 "REFUND_" + 支付宝返回的流水号，或者直接存我们的 refund_request_no
                        transaction_id=f"REFUND_{sub_order.order_number}"
                    )

                return Response({'message': '退款成功', 'alipay_response': response}, status=status.HTTP_200_OK)

            else:
                # 支付宝拒绝了退款 (可能是余额不足、超过退款期限等)
                error_msg = response.get('sub_msg', 'Alipay refund failed')
                return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': f"系统错误: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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