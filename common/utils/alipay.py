from django.conf import settings
from alipay import AliPay


def build_alipay_client():
    return AliPay(
        appid=settings.ALIPAY_CONFIG["APPID"],
        app_notify_url=None,
        app_private_key_string=settings.ALIPAY_CONFIG["APP_PRIVATE_KEY_STRING"],
        alipay_public_key_string=settings.ALIPAY_CONFIG["ALIPAY_PUBLIC_KEY_STRING"],
        sign_type=settings.ALIPAY_CONFIG["SIGN_TYPE"],
        debug=settings.ALIPAY_CONFIG["DEBUG"],
    )
