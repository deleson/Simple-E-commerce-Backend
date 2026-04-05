class BusinessError(Exception):
    """
    统一的业务异常。

    用法：
        raise BusinessError("店铺名不能为空")
        raise BusinessError("你已经是卖家了")
    """
    pass
