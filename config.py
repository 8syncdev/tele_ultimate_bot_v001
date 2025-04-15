"""
Cấu hình chính của ứng dụng
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

# Thư mục gốc của dự án
BASE_DIR = Path(__file__).parent

# Thư mục chứa dữ liệu tạm thời
TEMP_DIR = BASE_DIR / "temp"

# Tạo thư mục temp nếu chưa tồn tại
if not TEMP_DIR.exists():
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Các thông tin cấu hình Telegram API
TELEGRAM_API_ID = os.getenv("API_ID", "")
TELEGRAM_API_HASH = os.getenv("API_HASH", "")
TELEGRAM_PHONE = os.getenv("PHONE_NUMBER", "")

# Số lượng thành viên mặc định để scrape
DEFAULT_MEMBER_LIMIT = 1000

# Độ trễ mặc định giữa các lần thêm thành viên (giây)
DEFAULT_ADD_DELAY = 30



