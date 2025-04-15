"""
Module quản lý kết nối và phiên làm việc với Telegram.
Đây là module gom các submodule để truy cập dễ dàng.
"""
from src.core.account_manager import TelegramAccountManager
from src.core.member_scraper import TelegramScraper
from src.core.member_adder import TelegramAdder
from src.core.telegram_utils import (
    random_sleep,
    DEFAULT_SMALL_DELAY,
    DEFAULT_MEDIUM_DELAY,
    DEFAULT_LONG_DELAY
)

__all__ = [
    'TelegramAccountManager',
    'TelegramScraper',
    'TelegramAdder',
    'random_sleep',
    'DEFAULT_SMALL_DELAY',
    'DEFAULT_MEDIUM_DELAY',
    'DEFAULT_LONG_DELAY'
] 