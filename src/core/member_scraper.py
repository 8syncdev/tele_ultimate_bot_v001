"""
Module xử lý việc scrape thành viên từ nhóm/kênh Telegram
"""
from typing import List, Dict, Any, Optional, Tuple, Callable
import time
import csv
from pathlib import Path

from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch, InputPeerChannel
from telethon.errors import FloodWaitError

from src.core.account_manager import TelegramAccountManager
from src.core.telegram_utils import random_sleep, DEFAULT_SMALL_DELAY, DEFAULT_MEDIUM_DELAY
from src.utils.logger import logger
from src.config import MEMBERS_DIR, MEMBER_CSV_FIELDS, DEFAULT_MEMBERS_FILE

class TelegramScraper:
    """Lớp xử lý việc scrape thành viên từ các nhóm/kênh Telegram"""
    
    def __init__(self, account_manager: TelegramAccountManager):
        """
        Khởi tạo scraper
        
        Args:
            account_manager: Đối tượng quản lý tài khoản
        """
        self.account_manager = account_manager
        self.members_dir = MEMBERS_DIR
        
        # Tạo thư mục members nếu chưa tồn tại
        if not self.members_dir.exists():
            self.members_dir.mkdir(parents=True, exist_ok=True)
    
    def scrape_members(self, phone: str, target_group: str, limit: int = 0, 
                      callback: Callable[[int], None] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Lấy danh sách thành viên từ nhóm/kênh
        
        Args:
            phone: Số điện thoại tài khoản dùng để scrape
            target_group: Username hoặc link của nhóm/kênh (t.me/...)
            limit: Giới hạn số lượng thành viên (0 = không giới hạn)
            callback: Hàm callback để cập nhật tiến trình
        
        Returns:
            Tuple (members, error) - Danh sách thành viên đã scrape và thông báo lỗi nếu có
        """
        if not isinstance(limit, int):
            return [], f"Giới hạn phải là số nguyên, nhận được: {type(limit)}"
            
        client = self.account_manager.get_client(phone)
        if not client:
            return [], "Không tìm thấy tài khoản"
        
        members = []
        all_participants = []
        
        try:
            # Kết nối tới Telegram
            client.connect()
            
            # Kiểm tra xác thực
            if not client.is_user_authorized():
                return [], "Tài khoản chưa được xác thực"
            
            # Chuẩn hóa target_group
            if target_group.startswith('https://t.me/'):
                target_group = target_group.split('https://t.me/')[1]
            elif target_group.startswith('t.me/'):
                target_group = target_group.split('t.me/')[1]
            
            # Lấy thông tin entity của nhóm/kênh
            entity = client.get_entity(target_group)
            
            # Thiết lập giới hạn lấy thành viên
            max_members = 100000  # Giá trị mặc định đủ lớn
            if limit > 0:
                max_members = limit
            
            # Lấy danh sách thành viên
            batch_count = 0
            total_found = 0
            
            # Chữ cái để tìm kiếm thành viên
            search_letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 
                             'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 
                             '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '_', ' ']
            
            # Set lưu ID đã scrape để tránh trùng lặp
            scraped_ids = set()
            
            for letter in search_letters:
                if total_found >= max_members:
                    break
                
                try:
                    participants = client(GetParticipantsRequest(
                        channel=entity,
                        filter=ChannelParticipantsSearch(letter),
                        offset=0,
                        limit=200,  # Lấy số lượng lớn hơn cho mỗi chữ cái
                        hash=0
                    ))
                    
                    if not participants.users:
                        continue
                    
                    # Thêm người dùng mới vào danh sách
                    new_count = 0
                    for user in participants.users:
                        if user.id not in scraped_ids and not user.bot:
                            all_participants.append(user)
                            scraped_ids.add(user.id)
                            new_count += 1
                    
                    if new_count > 0:
                        total_found = len(all_participants)
                        logger.info(f"Đã tìm thêm {new_count} thành viên với từ khóa '{letter}', tổng: {total_found}")
                        
                        # Gọi callback nếu có
                        if callback:
                            callback(total_found)
                    
                    # Kiểm tra giới hạn
                    if limit > 0 and total_found >= limit:
                        logger.info(f"Đã đạt giới hạn {limit} thành viên, dừng scrape")
                        break
                    
                    # Nghỉ ngắn giữa các lần tìm kiếm để tránh FloodWaitError
                    random_sleep(0.5, 1.5)
                
                except FloodWaitError as e:
                    wait_time = e.seconds
                    logger.warning(f"Đã bị giới hạn bởi Telegram, đợi {wait_time} giây")
                    if callback:
                        callback(total_found)  # Cập nhật tiến trình trước khi đợi
                    time.sleep(wait_time)
                    continue
                    
                except Exception as e:
                    logger.error(f"Lỗi khi scrape với từ khóa '{letter}': {str(e)}")
                    # Tiếp tục với từ khóa tiếp theo
                    continue
            
            # Giới hạn số lượng thành viên theo limit
            if limit > 0 and len(all_participants) > limit:
                all_participants = all_participants[:limit]
            
            logger.info(f"Đã scrape tổng cộng {len(all_participants)} thành viên")
            
            # Chuyển đổi danh sách thành viên sang định dạng cần thiết
            for user in all_participants:
                user_data = {
                    'username': user.username if user.username else "",
                    'user_id': user.id,
                    'access_hash': user.access_hash,
                    'first_name': user.first_name if hasattr(user, 'first_name') else "",
                    'last_name': user.last_name if hasattr(user, 'last_name') else "",
                    'status': str(user.status.__class__.__name__) if user.status else "Unknown",
                    'group': entity.title,
                    'group_id': entity.id
                }
                members.append(user_data)
            
            # Lưu danh sách thành viên vào file csv
            self._save_members_to_csv(members, entity.title)
            
            # Ngắt kết nối
            client.disconnect()
            
            return members, None
            
        except Exception as e:
            logger.error(f"Lỗi scrape members: {str(e)}")
            if client:
                client.disconnect()
            return [], str(e)
            
    def _save_members_to_csv(self, members: List[Dict[str, Any]], group_name: str) -> str:
        """
        Lưu danh sách thành viên vào file CSV
        
        Args:
            members: Danh sách thành viên
            group_name: Tên nhóm/kênh
        
        Returns:
            Đường dẫn đến file CSV đã lưu
        """
        # Tạo tên file an toàn từ tên nhóm (loại bỏ ký tự đặc biệt)
        safe_group_name = "".join(c for c in group_name if c.isalnum() or c in [' ', '_']).strip()
        safe_group_name = safe_group_name.replace(' ', '_')
        
        # Nếu tên file quá dài, cắt ngắn lại
        if len(safe_group_name) > 50:
            safe_group_name = safe_group_name[:50]
        
        # Nếu tên nhóm rỗng, sử dụng tên mặc định
        if not safe_group_name:
            safe_group_name = DEFAULT_MEMBERS_FILE.split('.')[0]
            
        # Đường dẫn tới file CSV
        csv_path = self.members_dir / f"{safe_group_name}.csv"
        
        # Lưu vào file CSV
        with open(csv_path, 'w', encoding='UTF-8', newline='') as f:
            writer = csv.writer(f, delimiter=',', lineterminator='\n')
            # Ghi header
            writer.writerow(MEMBER_CSV_FIELDS)
            
            # Ghi dữ liệu
            for member in members:
                # Chuẩn bị dữ liệu theo thứ tự các trường
                row = [
                    member.get('username', ''),
                    member.get('user_id', ''),
                    member.get('access_hash', ''),
                    member.get('group', ''),
                    member.get('group_id', ''),
                    member.get('status', '')
                ]
                writer.writerow(row)
                
        logger.info(f"Đã lưu {len(members)} thành viên vào file {csv_path}")
        return str(csv_path) 