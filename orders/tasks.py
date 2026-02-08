import datetime
import logging

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Order
from products.models import ProductSKU


logger = logging.getLogger(__name__)


@shared_task
def cancel_unpaid_orders_task():
    """
    每分钟执行一次：
    检查超过 30 分钟未支付的父订单，自动取消并回滚库存。
    """
    time_threshold = timezone.now() - datetime.timedelta(minutes=30)
    unpaid_orders = Order.objects.filter(
        parent__isnull=True,
        status=Order.OrderStatus.PENDING,
        created_at__lte=time_threshold,
    )

    logger.info("[ORDER_TIMEOUT_CLOSE][SCAN] timeout_order_count=%s", unpaid_orders.count())

    for parent_order in unpaid_orders:
        order_number = parent_order.order_number
        try:
            with transaction.atomic():
                parent_order.status = Order.OrderStatus.CANCELLED
                parent_order.save()

                sub_orders = parent_order.sub_orders.all()
                for sub in sub_orders:
                    sub.status = Order.OrderStatus.CANCELLED
                    sub.save()

                    for item in sub.items.all():
                        ProductSKU.objects.filter(id=item.product.id).update(stock=F('stock') + item.quantity)
                        logger.info(
                            "[ORDER_TIMEOUT_CLOSE][STOCK_ROLLBACK] order_number=%s sku_id=%s rollback_qty=%s",
                            order_number,
                            item.product.id,
                            item.quantity,
                        )

            logger.info("[ORDER_TIMEOUT_CLOSE][SUCCESS] order_number=%s", order_number)

        except Exception as e:
            logger.exception("[ORDER_TIMEOUT_CLOSE][ERROR] order_number=%s error=%s", order_number, e)

    return f"Processed {unpaid_orders.count()} orders."
