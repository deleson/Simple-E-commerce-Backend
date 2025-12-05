from django.contrib import admin
from .models import SellerProfile, Wallet, WalletTransaction

# Register your models here.
admin.site.register(SellerProfile)


# 定义内联显示类 (这是核心步骤)
class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction

    # 额外选项优化体验：
    extra = 0  # 默认不显示空白的新增行（看起来更整洁）
    readonly_fields = ('created_at',)  # 创建时间只读，防止篡改
    can_delete = False  # (可选) 如果不希望管理员随意删除流水，可以加上这就行
    ordering = ('-created_at',)  # 按时间倒序排列，最新的流水在最上面

    # 如果流水很多，为了性能，可以使用 raw_id_fields
    # raw_id_fields = ('order',)


# 2. 注册 Wallet 模型，并将内联类挂载上去
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    # 列表页显示的字段
    list_display = ('user', 'balance', 'total_income', 'updated_at')

    # 允许通过用户名或邮箱搜索钱包
    search_fields = ('user__username', 'user__email')

    # 关键一步：把流水内联类加到这里
    inlines = [WalletTransactionInline]

    # (可选) 只有超级管理员能修改余额，防止误操作
    # def get_readonly_fields(self, request, obj=None):
    #     if not request.user.is_superuser:
    #         return ('balance', 'total_income')
    #     return ()


# 3. (可选) 如果你也想单独在侧边栏看到“资金流水”入口，可以单独注册它
@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'type', 'amount', 'order', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('wallet__user__username', 'order__order_number')