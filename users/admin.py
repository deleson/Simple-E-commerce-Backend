from django.contrib import admin
from .models import MyUser
# 1. 引入 Django 自带的 UserAdmin
from django.contrib.auth.admin import UserAdmin

from sellers.models import SellerProfile


# 假如你有内联模型（比如之前的 Profile）
class SellerProfileInline(admin.StackedInline):
    model = SellerProfile  # 假设你之前定义的
    can_delete = False


# 3. 重新注册，但是要继承 UserAdmin！
@admin.register(MyUser)
class CustomUserAdmin(UserAdmin):  # <--- 关键点：继承 UserAdmin，而不是 ModelAdmin

    # 把你的内联加进去
    inlines = [SellerProfileInline]

    # 如果你想修改列表显示的字段，可以在 UserAdmin.list_display 基础上增加
    # UserAdmin.list_display 默认是 ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_display = UserAdmin.list_display + ('id', 'is_active')
