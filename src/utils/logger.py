"""
Module quản lý việc ghi log của ứng dụng
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import TEMP_DIR

# Các mức độ log
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

class TelegramLogger:
    """Lớp quản lý việc ghi log cho ứng dụng Telegram"""
    
    def __init__(self, log_level: str = 'INFO', log_file: Optional[str] = None):
        """
        Khởi tạo logger
        
        Args:
            log_level: Mức độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Đường dẫn file log. Nếu None, sẽ tạo file log theo ngày trong thư mục logs
        """
        self.log_level = LOG_LEVELS.get(log_level, logging.INFO)
        
        # Tạo thư mục logs nếu chưa tồn tại
        self.logs_dir = TEMP_DIR / 'logs'
        if not self.logs_dir.exists():
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Tạo file log theo ngày nếu không có file log được chỉ định
        if log_file is None:
            today = datetime.now().strftime('%Y-%m-%d')
            self.log_file = self.logs_dir / f'telegram_bot_{today}.log'
        else:
            self.log_file = Path(log_file)
        
        # Cấu hình logger
        self.logger = logging.getLogger('telegram_bot')
        self.logger.setLevel(self.log_level)
        
        # Xóa handlers cũ nếu có
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Tạo file handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(self.log_level)
        
        # Tạo console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        
        # Tạo formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Thêm handlers vào logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str):
        """Ghi log debug"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Ghi log info"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Ghi log warning"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Ghi log error"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """Ghi log critical"""
        self.logger.critical(message)

# Tạo instance mặc định của logger
logger = TelegramLogger() 