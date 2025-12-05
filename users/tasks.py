from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_password_reset_email_task(subject, message, recipient_list, from_email=None):
    # 如果没有传 from_email，就用 settings 里的默认值
    if from_email is None:
        from_email = settings.EMAIL_HOST_USER

    print(f"{from_email} 正在尝试发送邮件给: {recipient_list}")
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        return "发送成功"
    except Exception as e:
        # 这里的 print 会显示在 Celery 的黑窗口里
        print(f"发送失败！！！错误原因: {e}")
        return f"发送失败: {e}"