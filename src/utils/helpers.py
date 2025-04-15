"""
Các hàm tiện ích chung cho ứng dụng
"""
import os
import csv
import datetime
from pathlib import Path
from typing import List, Dict, Any, Union

def clear_screen():
    """Xóa màn hình console"""
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def ensure_dir(dir_path: Union[str, Path]):
    """Đảm bảo thư mục tồn tại, nếu không thì tạo mới"""
    path = Path(dir_path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    return path

def save_to_csv(file_path: str, data: List[Dict[str, Any]], headers: List[str]):
    """Lưu dữ liệu vào file CSV"""
    with open(file_path, 'w', encoding='UTF-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def load_from_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    Đọc dữ liệu từ file CSV và chuyển đổi các trường số và boolean sang kiểu dữ liệu phù hợp
    
    Args:
        file_path: Đường dẫn đến file CSV cần đọc
        
    Returns:
        Danh sách các bản ghi từ file CSV với kiểu dữ liệu đã được chuyển đổi
    """
    result = []
    try:
        with open(file_path, 'r', encoding='UTF-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Chuyển đổi các trường numeric
                processed_row = {}
                for key, value in row.items():
                    if key in ['user_id', 'id'] and value:
                        try:
                            processed_row[key] = int(value)
                        except (ValueError, TypeError):
                            processed_row[key] = value
                    elif key == 'access_hash' and value:
                        try:
                            processed_row[key] = int(value)
                        except (ValueError, TypeError):
                            processed_row[key] = value
                    elif key == 'group_id' and value:
                        try:
                            processed_row[key] = int(value)
                        except (ValueError, TypeError):
                            processed_row[key] = value
                    else:
                        processed_row[key] = value
                
                result.append(processed_row)
    except FileNotFoundError:
        pass
    return result

def get_current_datetime() -> datetime.datetime:
    """Trả về ngày giờ hiện tại"""
    return datetime.datetime.now()

def format_datetime(dt: datetime.datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format đối tượng datetime thành chuỗi"""
    return dt.strftime(format_str)

def get_files_in_directory(directory: Union[str, Path], extension: str = None) -> List[Path]:
    """Lấy danh sách các file trong thư mục với phần mở rộng cụ thể"""
    path = Path(directory)
    if not extension:
        return list(path.iterdir())
    return list(path.glob(f"*.{extension}")) 