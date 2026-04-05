import contextlib

from django.db.models.signals import post_save, post_delete, m2m_changed


@contextlib.contextmanager
def mute_elasticsearch_signals_only():
    """
    只静音 Elasticsearch 相关信号处理器，
    保留其他信号接收器（例如 Redis 同步等）。
    """
    signals_to_mute = [post_save, post_delete, m2m_changed]
    backups = {}

    for signal in signals_to_mute:
        backups[signal] = signal.receivers

        new_receivers = []
        for item in signal.receivers:
            receiver_ref = item[1]
            receiver_str = str(receiver_ref)

            if "CelerySignalProcessor" in receiver_str or "RealTimeSignalProcessor" in receiver_str:
                continue

            new_receivers.append(item)

        signal.receivers = new_receivers

    try:
        yield
    finally:
        for signal, original_receivers in backups.items():
            signal.receivers = original_receivers
