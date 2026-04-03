# payment/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from orders.models import Order
from products.models import ProductSKU
from sellers.models import WalletTransaction
from .models import Payment

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.http import HttpResponse

# 引入工具类
from common.utils.alipay import build_alipay_client
from common.utils.ws import push_order_status


def payment_success_view(request):
    # 简单的 http .响应，实际项目中这里应该是一个渲染的前端页面
    return HttpResponse("<h1>支付成功！</h1><p>感谢您的购买，我们正在处理您的订单。</p>")



# 把 Django 的 csrf_exempt 装饰器，应用到类视图（APIView）的 dispatch() 方法上，从而让这个类视图完全跳过 CSRF 校验。

@method_decorator(csrf_exempt, name='dispatch')
class AlipayWebhookView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data.dict()
        signature = data.pop("sign", None)

        # 初始化支付宝SDK
        alipay = build_alipay_client()

        # 验签
        success = alipay.verify(data, signature)
        if success and data.get("trade_status") in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            # 获取父订单号
            order_number = data.get('out_trade_no')
            print(f"this is {order_number}")

            try:
                # 在事务开始前就获取订单，获取父订单
                parent_order = Order.objects.get(order_number=order_number)

                # 只有待支付的订单才需要处理
                if parent_order.status == Order.OrderStatus.PENDING:
                    with transaction.atomic():



                        # A 更新父订单
                        parent_order.status = Order.OrderStatus.PAID
                        parent_order.save()

                        # B 处理所有子订单（级联更新）
                        # 获取所有关联的子订单
                        sub_orders = parent_order.sub_orders.all()

                        for sub in sub_orders:
                            # 1.更新子订单状态
                            sub.status = Order.OrderStatus.PAID
                            sub.save()


                            # 资金结算：给卖家钱包打钱
                            # 检查该子订单是否有卖家，且卖家是否有钱包
                            if sub.seller and hasattr(sub.seller, 'wallet'):
                                seller_wallet = sub.seller.wallet
                                income_amount = sub.total_amount

                                # 增加余额 (原子操作推荐使用 F 表达式，或者因为我们在 transaction.atomic 里，直接加也可以)
                                # 这里为了简单直观，直接加
                                seller_wallet.balance += income_amount
                                seller_wallet.total_income += income_amount
                                seller_wallet.save()

                                # 记录流水
                                WalletTransaction.objects.create(
                                    wallet=seller_wallet,
                                    amount=income_amount,
                                    type=WalletTransaction.TransactionType.ORDER_INCOME,
                                    order=sub,
                                    description=f"订单 {sub.order_number} 结算收入"
                                )



                        # C 创建支付记录，并填入所有必填字段
                        Payment.objects.create(
                            order=parent_order,
                            amount=data.get('total_amount'),  # 从支付宝数据获取真实支付金额
                            status=Payment.PaymentStatus.SUCCESS,
                            transaction_id=f"PAYMENT_{data.get('trade_no')}",  # 使用支付宝的交易号
                            payment_type = Payment.PaymentType.PAYMENT
                        )
                # 如果订单不是PENDING状态（比如已经处理过），也应该告诉支付宝成功了

                # 【核心新增】向 WebSocket 推送消息
                push_order_status(parent_order.order_number, "PAID", "支付成功")



            except Order.DoesNotExist:
                # 订单不存在，可能是伪造的请求，直接返回 failure
                return Response("failure")
            except Exception as e:
                # 捕获所有其他可能的异常，并记录日志
                # 在生产环境中，这里应该用 logging 模块记录详细错误
                print(f"--- [Webhook Error] 处理订单 {order_number} 时发生未知错误: {e}")
                return Response("failure")

            # 只要验签成功，且订单状态不再是 PENDING (说明已处理或正在处理)，都应返回 success
            return Response("success")

        return Response("failure")

