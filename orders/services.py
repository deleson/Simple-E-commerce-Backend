import uuid

from common.utils.alipay import build_alipay_client
from payment.models import Payment
from sellers.models import WalletTransaction

from collections import defaultdict
from django.db import transaction
from common.exceptions import BusinessError
from cart.models import CartItem
from products.models import ProductSKU
from .models import Order, OrderItem


def create_order_from_cart(*, user, address_snapshot):
    """
    从当前用户购物车创建订单。

    参数:
        user: 当前登录用户
        address_snapshot: 已经处理好的收货地址快照字符串

    返回:
        创建成功后的父订单 Order 实例

    异常:
        BusinessError: 业务执行过程中的错误
    """

    # 1. 获取购物车，并预加载商品 -> SPU -> 卖家
    cart_items = CartItem.objects.filter(user=user).select_related("product__spu__seller")

    # 理论上 serializer.validate 已经校验过了，这里作为最后一道保护
    if not cart_items.exists():
        raise BusinessError("购物车为空，无法下单。")

    # 2. 按卖家分组
    seller_groups = defaultdict(list)
    for item in cart_items:
        seller = item.product.spu.seller
        seller_groups[seller].append(item)

    # 3. 计算总金额
    grand_total = sum(item.product.price * item.quantity for item in cart_items)

    # 4. 事务内创建父订单、子订单、订单项，并扣库存
    with transaction.atomic():
        # 创建父订单
        parent_order = Order.objects.create(
            user=user,
            parent=None,
            seller=None,
            total_amount=grand_total,
            shipping_address=address_snapshot,
            status=Order.OrderStatus.PENDING,
        )

        # 为每个卖家创建一个子订单
        for seller, items in seller_groups.items():
            sub_total = sum(item.product.price * item.quantity for item in items)

            sub_order = Order.objects.create(
                user=user,
                parent=parent_order,
                seller=seller,
                total_amount=sub_total,
                shipping_address=address_snapshot,
                status=Order.OrderStatus.PENDING,
            )

            # 为子订单创建订单项，并扣减库存
            for item in items:
                try:
                    product_sku = ProductSKU.objects.select_for_update().get(id=item.product.id)
                except ProductSKU.DoesNotExist:
                    raise BusinessError(f"商品 {item.product.name} 已下架，请移除后重试。")

                if item.quantity > product_sku.stock:
                    raise BusinessError(
                        f"商品 {product_sku.name} 库存不足，仅剩 {product_sku.stock} 件。"
                    )

                product_sku.stock -= item.quantity
                product_sku.save()

                OrderItem.objects.create(
                    order=sub_order,
                    product=item.product,
                    product_name=f"{item.product.spu.name} {item.product.name}",
                    product_price=item.product.price,
                    quantity=item.quantity,
                )

        # 清空购物车
        cart_items.delete()

    return parent_order



def refund_sub_order(*, sub_order):
    """
    对子订单发起退款。

    参数:
        sub_order: 要退款的子订单实例

    返回:
        支付宝退款响应结果

    异常:
        BusinessError: 业务校验失败或退款失败时抛出
    """

    # 1. 校验必须是子订单
    if not sub_order.parent:
        raise BusinessError("只能对子订单发起退款申请。")

    # 2. 校验订单状态
    if sub_order.status != Order.OrderStatus.PAID:
        raise BusinessError("只有已支付的订单才能退款。")

    # 3. 初始化支付宝客户端
    alipay = build_alipay_client()

    # 4. 发起退款请求
    refund_request_no = str(uuid.uuid4())

    try:
        response = alipay.api_alipay_trade_refund(
            out_trade_no=str(sub_order.parent.order_number),
            refund_amount=float(sub_order.total_amount),
            out_request_no=refund_request_no,
            refund_reason=f"Refund for sub-order{sub_order.order_number}",
        )
    except Exception as e:
        raise BusinessError(f"系统错误: {str(e)}")

    # 5. 判断支付宝是否退款成功
    if not (response.get("code") == "10000" and response.get("fund_change") == "Y"):
        error_msg = response.get("sub_msg", "Alipay refund failed")
        raise BusinessError(error_msg)

    # 6. 本地事务处理：更新订单、回滚库存、扣减钱包、记录流水
    with transaction.atomic():
        # 更新子订单状态
        sub_order.status = Order.OrderStatus.REFUNDED
        sub_order.save()

        # 回滚库存
        for item in sub_order.items.all():
            try:
                product_sku = ProductSKU.objects.select_for_update().get(id=item.product.id)
                product_sku.stock += item.quantity
                product_sku.save()
            except ProductSKU.DoesNotExist:
                continue

        # 扣减卖家钱包
        if hasattr(sub_order.seller, "wallet"):
            wallet = sub_order.seller.wallet
            refund_money = sub_order.total_amount

            wallet.balance -= refund_money
            wallet.total_income -= refund_money
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                amount=-refund_money,
                type=WalletTransaction.TransactionType.REFUND,
                order=sub_order,
                description=f"订单退款：{sub_order.order_number}",
            )

        # 创建退款支付记录
        Payment.objects.create(
            order=sub_order,
            amount=sub_order.total_amount,
            status=Payment.PaymentStatus.SUCCESS,
            payment_type=Payment.PaymentType.REFUND,
            transaction_id=f"REFUND_{sub_order.order_number}",
        )

    return response
