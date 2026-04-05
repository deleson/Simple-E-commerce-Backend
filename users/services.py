from django.contrib.auth.models import Group
from django.db import transaction

from common.exceptions import BusinessError
from sellers.models import SellerProfile, Wallet


def apply_for_seller(*, user, shop_name, shop_description=""):
    """
    处理普通用户申请成为卖家的完整业务流程。

    参数:
        user: 当前登录用户
        shop_name: 店铺名称
        shop_description: 店铺描述，可选

    返回:
        创建成功后的 SellerProfile 实例

    异常:
        BusinessError: 业务校验失败时抛出
    """

    # 1. 检查用户是否已经是卖家
    if hasattr(user, "seller_profile"):
        raise BusinessError("You are already a seller.")

    # 2. 检查店铺名是否为空
    if not shop_name:
        raise BusinessError("Shop name is required.")

    # 3. 检查店铺名是否重复
    if SellerProfile.objects.filter(shop_name=shop_name).exists():
        raise BusinessError("Shop name already taken.")

    # 4. 事务处理：钱包、组、店铺档案要么一起成功，要么一起失败
    with transaction.atomic():
        # 如果用户没有钱包，就创建一个
        if not hasattr(user, "wallet"):
            Wallet.objects.create(user=user)

        # 获取 Seller 组
        seller_group = Group.objects.get(name="Seller")

        # 把用户加入 Seller 组
        user.groups.add(seller_group)

        # 创建店铺档案
        seller_profile = SellerProfile.objects.create(
            user=user,
            shop_name=shop_name,
            shop_description=shop_description,
        )

    return seller_profile
