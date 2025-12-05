from rest_framework import permissions
from orders.models import Order

class HasPurchaseProductPermission(permissions.BasePermission):
    """
    自定义权限，只允许购买过该商品的用户进行评论。
    """
    message = 'You must purchase this product to be able to review it.'

    def has_permission(self, request, view):

        #1.首先，用户必须是登录状态
        if not request.user.is_authenticated:
            return False

        #2.从URL中获取即将被评论的商品ID
        # 我们约定URL格式会是 /api/products/<product_pk>/reviews/
        product_id = view.kwargs.get('product_pk')
        if not product_id:
            return False    # 如果URL中没有product_pk则禁止

        #3.检查是否存在一个“已支付”的订单
        # 属于当前用户，并且订单项包含了这个商品
        # .exists()是一个高效的查询，只返回True或False，不获取实际对象。
        has_purchased = Order.objects.filter(
            user = request.user,
            status__in = [
                Order.OrderStatus.PAID,
                Order.OrderStatus.SHIPPED,
                Order.OrderStatus.COMPLETED,
            ],
            items__product_id=product_id
        ).exists()

        return has_purchased






