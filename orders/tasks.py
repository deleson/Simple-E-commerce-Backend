from celery import shared_task
from django.utils import timezone
from django.db import transaction
import datetime

from django.db.models import F
from .models import Order
from products.models import ProductSKU

@shared_task
def cancel_unpaid_orders_task():
    """
    每分钟执行一次：
    检查超过 30 分钟未支付的父订单，自动取消并回滚库存。
    """
    # 1. 确定时间阈值 (当前时间 - 30分钟)
    # 为了测试方便，你可以把 minutes=30 改成 minutes=1
    time_threshold = timezone.now() - datetime.timedelta(minutes=30)
    # 2.查询超时的父订单
    # 条件：父订单（parent=None） & 状态是待支付 & 创建时间早于阈值
    unpaid_orders = Order.objects.filter(
        parent__isnull=True,
        status=Order.OrderStatus.PENDING,
        created_at__lte=time_threshold
    )

    print(f"--- [Cron] 扫描到 {unpaid_orders.count()} 个超时订单 ---")

    for parent_order in unpaid_orders:
        try:
            with transaction.atomic():
                # 标记父订单为已取消
                parent_order.status = Order.OrderStatus.CANCELLED
                parent_order.save()

                # 处理所有关联的子订单
                sub_orders = parent_order.sub_orders.all()
                for sub in sub_orders:
                    sub.status = Order.OrderStatus.CANCELLED
                    sub.save()

                    # 遍历该子订单的所有商品，把库存加回去

                    for item in sub.items.all():
                        # 使用 F 表达式原子更新，更加安全高效
                        ProductSKU.objects.filter(id=item.product.id).update(stock=F('stock') + item.quantity)

                        print(f"库存回滚: SKU id{item.product.id} + {item.quantity}")

            print(f"订单{parent_order.order_number}已自动取消")

        except Exception as e:
            print(f"取消订单{parent_order.order_number} 失败:{str(e)}")

    return f"Processed {unpaid_orders.count()} orders."