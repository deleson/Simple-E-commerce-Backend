from django.contrib import admin
from .models import UserAddress
# Register your models here.
@admin.register(UserAddress)
class UserAdressAdmin(admin.ModelAdmin):
    list_display = ['id','user', 'signer_name', 'signer_mobile','full_region']

    def full_region(self, obj):
        return f"{obj.province}{obj.city}{obj.district}"

    full_region.short_description = "省市区/县"