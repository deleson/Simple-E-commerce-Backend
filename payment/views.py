# payment/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from alipay import AliPay
from orders.models import Order
from products.models import ProductSKU
from sellers.models import WalletTransaction
from .models import Payment

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.http import HttpResponse


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
        alipay = AliPay(
            appid=settings.ALIPAY_CONFIG['APPID'],
            app_notify_url=None,
            app_private_key_string=settings.ALIPAY_CONFIG['APP_PRIVATE_KEY_STRING'],
            alipay_public_key_string=settings.ALIPAY_CONFIG['ALIPAY_PUBLIC_KEY_STRING'],
            sign_type=settings.ALIPAY_CONFIG['SIGN_TYPE'],
            debug=settings.ALIPAY_CONFIG['DEBUG']
        )

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

                            #  因为改成下单减库存，所以下面全删掉了
                            # # 遍历订单项 (这里不需要加锁，因为订单项本身不会变)
                            # for item in sub.items.all():
                            #
                            #
                            #     # 使用 product_id 重新查询 ProductSKU 表，并加上排他锁 (select_for_update)
                            #     # 这行代码执行后，直到事务结束前，其他人都不能修改这件商品的库存
                            #     try:
                            #         product_sku = ProductSKU.objects.select_for_update().get(id=item.product.id)
                            #     except ProductSKU.DoesNotExist:
                            #         # 极端情况：商品被删除了
                            #         raise Exception(f"Product {item.product_name} not found during payment.")
                            #
                            #     # 2. 检查库存 (这是基于最新、已锁定的数据检查，绝对安全)
                            #     if item.quantity > product_sku.stock:
                            #         # 抛出异常会触发事务回滚，之前的订单状态更新也会撤销
                            #         raise Exception(f"Insufficient stock for {product_sku.name}")
                            #         # 3. 扣减库存
                            #         product_sku.stock -= item.quantity
                            #         product_sku.save()


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
                channel_layer = get_channel_layer()
                # 发送给父订单的监听者
                async_to_sync(channel_layer.group_send)(
                    f"order_{parent_order.order_number}",  # 组名
                    {
                        "type": "order_status_update",  # 对应 Consumer 中的方法名
                        "message": "支付成功",
                        "status": "PAID"
                    }
                )



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

