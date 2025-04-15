"""
Điểm khởi chạy chính của ứng dụng Telegram Ultimate Bot
Cung cấp giao diện người dùng để tương tác với các chức năng
"""
import sys
import os
from pathlib import Path

# Thêm thư mục gốc vào sys.path để import các module
sys.path.append(str(Path(__file__).parent.parent))

from src.config import BASE_DIR
from src.ui.app import start_application

if __name__ == "__main__":
    # Khởi chạy ứng dụng
    start_application() 