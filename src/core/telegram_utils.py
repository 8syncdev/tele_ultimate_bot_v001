"""
Chứa các hàm tiện ích cho module Telegram
"""
import random
import time
from typing import Tuple, Union
from src.utils.logger import logger

# Khoảng thời gian nghỉ mặc định (giây)
DEFAULT_SMALL_DELAY = (1, 3)  # Nghỉ ngắn khi scrape
DEFAULT_MEDIUM_DELAY = (10, 30)  # Nghỉ trung bình giữa các batch
DEFAULT_LONG_DELAY = (30, 60)  # Nghỉ dài giữa các lần thêm thành viên

def random_sleep(min_seconds: Union[int, float, Tuple[int, int]], max_seconds: Union[int, float] = None) -> None:
    """
    Nghỉ một khoảng thời gian ngẫu nhiên
    
    Args:
        min_seconds: Thời gian nghỉ tối thiểu hoặc tuple (min, max)
        max_seconds: Thời gian nghỉ tối đa (không cần nếu min_seconds là tuple)
    """
    if isinstance(min_seconds, tuple) and len(min_seconds) == 2:
        min_seconds, max_seconds = min_seconds

    seconds = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Nghỉ {seconds:.2f} giây")
    time.sleep(seconds) 