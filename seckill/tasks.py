# seckill/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model




from common.exceptions import BusinessError
from .services import create_seckill_order


User = get_user_model()






@shared_task(bind=True, max_retries=5)
def create_seckill_order_task(self, user_id, event_id, address_snapshot):
    try:
        order = create_seckill_order(
            user_id=user_id,
            event_id=event_id,
            address_snapshot=address_snapshot,
        )
        return f"Seckill Order Created: {order.order_number}"

    except BusinessError as e:
        return f"Failed: {str(e)}"

    except Exception as e:
        print(f"Error creating seckill order: {e}")
        if "Lock wait timeout" in str(e):
            raise self.retry(exc=e, countdown=3)
        return f"Failed: {e}"

