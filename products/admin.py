from django.contrib import admin
from .models import Category,ProductSKU,ProductSPU

# Register your models here.
# admin.site.register(Category)
# admin.site.register(ProductSKU)
# admin.site.register(ProductSPU)

# products/admin.py
from django.contrib import admin
from .models import Category, ProductSPU, ProductSKU

# 让SKU可以在SPU的编辑页面内联添加和编辑
class ProductSKUInline(admin.TabularInline):
    model = ProductSKU
    extra = 1 # 默认显示一个空的SKU表单

@admin.register(ProductSPU)
class ProductSPUAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'category', 'seller', 'created_at')
    list_filter = ('category', 'seller')
    search_fields = ('name', 'description')
    readonly_fields = ('id',)
    inlines = [ProductSKUInline] # 在SPU页面内嵌SKU的管理

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

# 我们也可以单独注册SKU模型，方便全局搜索和管理
@admin.register(ProductSKU)
class ProductSKUAdmin(admin.ModelAdmin):
    list_display = ('id','__str__', 'price', 'stock')
    list_filter = ('spu__category',)
    readonly_fields = ('id',)
    search_fields = ('name', 'spu__name')