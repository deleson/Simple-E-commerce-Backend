from django.db import transaction

from common.exceptions import BusinessError
from common.utils.ws import push_order_status
from orders.models import Order
from sellers.models import WalletTransaction
from .models import Payment


def handle_alipay_payment_callback(*, data):
    """
    处理支付宝支付成功后的本地业务更新。

    参数:
        data: 支付宝回调验签成功后的数据字典

    返回:
        parent_order: 对应的父订单实例

    异常:
        BusinessError: 业务失败时抛出
    """
    order_number = data.get("out_trade_no")

    if not order_number:
        raise BusinessError("缺少订单号")

    try:
        parent_order = Order.objects.get(order_number=order_number)
    except Order.DoesNotExist:
        raise BusinessError("订单不存在")

    # 只有待支付订单才执行一次真正的状态推进
    if parent_order.status == Order.OrderStatus.PENDING:
        with transaction.atomic():
            # 1. 更新父订单
            parent_order.status = Order.OrderStatus.PAID
            parent_order.save()

            # 2. 更新所有子订单并给卖家钱包入账
            sub_orders = parent_order.sub_orders.all()

            for sub in sub_orders:
                sub.status = Order.OrderStatus.PAID
                sub.save()

                if sub.seller and hasattr(sub.seller, "wallet"):
                    seller_wallet = sub.seller.wallet
                    income_amount = sub.total_amount

                    seller_wallet.balance += income_amount
                    seller_wallet.total_income += income_amount
                    seller_wallet.save()

                    WalletTransaction.objects.create(
                        wallet=seller_wallet,
                        amount=income_amount,
                        type=WalletTransaction.TransactionType.ORDER_INCOME,
                        order=sub,
                        description=f"订单 {sub.order_number} 结算收入",
                    )

            # 3. 创建支付记录
            Payment.objects.create(
                order=parent_order,
                amount=data.get("total_amount"),
                status=Payment.PaymentStatus.SUCCESS,
                transaction_id=f"PAYMENT_{data.get('trade_no')}",
                payment_type=Payment.PaymentType.PAYMENT,
            )

    # 4. 推送支付成功消息
    push_order_status(parent_order.order_number, "PAID", "支付成功")

    return parent_order
