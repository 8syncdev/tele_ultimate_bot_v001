"""
Cấu hình chính của ứng dụng
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

# Thư mục gốc của dự án
BASE_DIR = Path(__file__).parent.parent

# Thư mục chứa dữ liệu tạm thời
TEMP_DIR = BASE_DIR / "temp"

# Thư mục chứa file thành viên đã đào
MEMBERS_DIR = TEMP_DIR / "members"

# Tạo thư mục temp và members nếu chưa tồn tại
if not TEMP_DIR.exists():
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
if not MEMBERS_DIR.exists():
    MEMBERS_DIR.mkdir(parents=True, exist_ok=True)

# Các thông tin cấu hình Telegram API
TELEGRAM_API_ID = os.getenv("API_ID", "")
TELEGRAM_API_HASH = os.getenv("API_HASH", "")
TELEGRAM_PHONE = os.getenv("PHONE_NUMBER", "")

# Số lượng thành viên mặc định để scrape
DEFAULT_MEMBER_LIMIT = 1000

# Độ trễ mặc định giữa các lần thêm thành viên (giây)
DEFAULT_ADD_DELAY = 30

# Tên mặc định của file chứa thành viên đã đào
DEFAULT_MEMBERS_FILE = "members.csv"

# Các trường dữ liệu cho file CSV thành viên
MEMBER_CSV_FIELDS = ['username', 'user_id', 'access_hash', 'first_name', 'last_name', 'group', 'group_id', 'status']



