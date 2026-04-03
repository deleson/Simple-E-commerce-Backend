def get_seckill_stock_key(event_id):
    return f"seckill_stock_{event_id}"


def get_order_ws_group(order_number):
    return f"order_{order_number}"
