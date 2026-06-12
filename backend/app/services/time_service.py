from datetime import datetime


def now_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_time() -> str:
    return datetime.now().strftime("%H:%M:%S")
