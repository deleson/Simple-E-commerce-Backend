from django.contrib import admin
from .models import Order, OrderItem


# 1. 定义内联类 (OrderItemInline)
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0  # 默认不显示多余的空白行，界面更清爽

    # 定义你希望在表格里看到的字段
    # 注意：'get_seller' 是下面定义的函数名
    fields = ('product', 'product_name', 'product_price', 'quantity', 'get_seller')

    # 自定义显示的字段必须设为只读（因为它是算出来的，不能改）
    readonly_fields = ('get_seller',)

    # 自定义方法：获取卖家用户名
    def get_seller(self, obj):
        # obj 是当前的 OrderItem 对象
        # 我们需要顺藤摸瓜：OrderItem -> Product (SKU) -> SPU -> Seller (User)
        try:
            if obj.product and obj.product.spu:
                return obj.product.spu.seller.username
        except AttributeError:
            return "-"
        return "-"

    # 设置列标题
    get_seller.short_description = "所属卖家"


# 2. 注册主模型 (Order)，并把内联挂载进去
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number','parent', 'total_amount', 'status', 'created_at')
    readonly_fields = ('order_number', 'created_at', 'updated_at')

    # 关键步骤：挂载内联
    inlines = [OrderItemInline]


# 3. 关于 OrderItem 单独注册
# 通常有了内联后，就不需要单独注册 OrderItem 了。
# 除非你想在侧边栏单独搜索所有订单项，否则建议删掉下面这段，保持后台整洁。
@admin.register(OrderItem)
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = (['order','seller'])

    def seller(self,obj):
        return f"{obj.product.spu.seller.username}"


