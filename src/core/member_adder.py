"""
Module xử lý việc thêm thành viên vào nhóm/kênh Telegram
"""
import random
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable, Union

from telethon import errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest
from telethon.tl.types import InputPeerChannel, InputPeerUser

from src.core.account_manager import TelegramAccountManager
from src.core.telegram_utils import random_sleep, DEFAULT_SMALL_DELAY, DEFAULT_LONG_DELAY
from src.utils.logger import logger
from src.config import MEMBERS_DIR, DEFAULT_ADD_DELAY, MEMBER_CSV_FIELDS

class TelegramAdder:
    """Lớp xử lý việc thêm thành viên vào nhóm/kênh Telegram"""
    
    def __init__(self, account_manager: TelegramAccountManager):
        """
        Khởi tạo adder
        
        Args:
            account_manager: Đối tượng quản lý tài khoản
        """
        self.account_manager = account_manager
        
    def load_members_from_csv(self, csv_file: str) -> List[Dict[str, Any]]:
        """
        Đọc danh sách thành viên từ file CSV
        
        Args:
            csv_file: Đường dẫn đến file CSV
        
        Returns:
            Danh sách thành viên
        """
        members = []
        
        # Kiểm tra xem đường dẫn là tuyệt đối hay tương đối
        csv_path = Path(csv_file)
        if not csv_path.is_absolute():
            # Nếu không chỉ định đường dẫn đầy đủ, giả sử nằm trong thư mục members
            csv_path = MEMBERS_DIR / csv_file
        
        try:
            with open(csv_path, 'r', encoding='UTF-8') as f:
                reader = csv.reader(f, delimiter=',', lineterminator='\n')
                # Bỏ qua header
                header = next(reader)
                
                # Xác định chỉ số các cột
                username_idx = header.index('username') if 'username' in header else 0
                user_id_idx = header.index('user_id') if 'user_id' in header else 1
                access_hash_idx = header.index('access_hash') if 'access_hash' in header else 2
                group_idx = header.index('group') if 'group' in header else 3
                group_id_idx = header.index('group_id') if 'group_id' in header else 4
                
                for row in reader:
                    if len(row) >= 3:  # Cần ít nhất username, id và access_hash
                        member = {
                            'username': row[username_idx],
                            'id': int(row[user_id_idx]),
                            'access_hash': int(row[access_hash_idx]),
                        }
                        
                        # Thêm các trường tùy chọn nếu có
                        if len(row) > group_idx:
                            member['group'] = row[group_idx]
                        if len(row) > group_id_idx:
                            member['group_id'] = row[group_id_idx]
                            
                        members.append(member)
            
            logger.info(f"Đã đọc {len(members)} thành viên từ file {csv_path}")
            return members
            
        except Exception as e:
            logger.error(f"Lỗi khi đọc file CSV {csv_path}: {str(e)}")
            return []
    
    def add_members(self, phone: str, target_group: str, members: List[Dict[str, Any]], 
                   delay: int = DEFAULT_ADD_DELAY, callback: Callable = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
        """
        Thêm danh sách thành viên vào nhóm/kênh
        
        Args:
            phone: Số điện thoại tài khoản dùng để thêm thành viên
            target_group: Username hoặc link của nhóm/kênh đích
            members: Danh sách thành viên cần thêm
            delay: Thời gian chờ cơ bản giữa các lần thêm (giây)
            callback: Hàm callback để cập nhật tiến trình
        
        Returns:
            Tuple (success, failed, error) - Danh sách thành viên đã thêm thành công, thất bại và thông báo lỗi nếu có
        """
        client = self.account_manager.get_client(phone)
        if not client:
            return [], [], "Không tìm thấy tài khoản"
        
        success_members = []
        failed_members = []
        
        try:
            # Kết nối tới Telegram
            client.connect()
            
            # Kiểm tra xác thực
            if not client.is_user_authorized():
                return [], [], "Tài khoản chưa được xác thực"
            
            # Chuẩn hóa target_group
            if target_group.startswith('https://t.me/'):
                target_group = target_group.split('https://t.me/')[1]
            elif target_group.startswith('t.me/'):
                target_group = target_group.split('t.me/')[1]
            
            # Lấy thông tin entity của nhóm/kênh đích
            target_entity = client.get_entity(target_group)
            target_input_entity = InputPeerChannel(target_entity.id, target_entity.access_hash)
            
            # Tham gia vào nhóm/kênh đích trước
            try:
                client(JoinChannelRequest(target_entity))
                logger.info(f"Đã tham gia nhóm/kênh {target_group}")
            except:
                # Có thể đã tham gia trước đó
                pass
            
            # Thêm từng thành viên vào nhóm/kênh
            for i, member in enumerate(members):
                try:
                    # Lấy thông tin user
                    user = None
                    
                    if member.get('username'):
                        try:
                            user = client.get_input_entity(member['username'])
                        except Exception as e:
                            logger.warning(f"Không thể tìm thấy user với username {member['username']}: {str(e)}")
                    
                    if not user:
                        try:
                            user = InputPeerUser(member['id'], member['access_hash'])
                        except Exception as e:
                            logger.error(f"Lỗi khi tạo InputPeerUser cho {member.get('username', member['id'])}: {str(e)}")
                            if callback:
                                callback(i + 1, len(members), False, member, str(e))
                            failed_members.append(member)
                            continue
                    
                    # Thêm vào nhóm/kênh
                    client(InviteToChannelRequest(target_input_entity, [user]))
                    
                    # Cập nhật danh sách thành công
                    success_members.append(member)
                    
                    # Cập nhật callback nếu có
                    if callback:
                        callback(i + 1, len(members), True, member)
                    
                    # Chờ ngẫu nhiên để tránh bị giới hạn hoặc ban
                    if i > 0 and i % 10 == 0:
                        # Sau mỗi 10 thành viên, nghỉ dài hơn
                        logger.info(f"Đã thêm {i} thành viên, nghỉ dài để tránh bị ban...")
                        # Delay dài hơn sau mỗi 10 thành viên (2-5 phút)
                        random_sleep(120, 300)
                    else:
                        # Delay ngẫu nhiên dựa trên tham số delay (±30%)
                        random_delay = delay * random.uniform(0.7, 1.3)
                        random_sleep(max(random_delay, 15), random_delay + 15)
                    
                except errors.FloodWaitError as e:
                    # Bị giới hạn, cần chờ
                    logger.warning(f"Bị giới hạn, cần chờ {e.seconds} giây")
                    if callback:
                        callback(i + 1, len(members), False, member, f"Bị giới hạn, cần chờ {e.seconds} giây")
                    
                    failed_members.append(member)
                    
                    # Chờ theo yêu cầu của Telegram
                    random_sleep(e.seconds, e.seconds + 10)
                    
                    # Thêm thời gian nghỉ bổ sung sau khi nhận FloodWaitError
                    random_sleep(60, 120)
                    
                except errors.UserPrivacyRestrictedError:
                    # Người dùng có cài đặt quyền riêng tư hạn chế
                    logger.warning(f"Không thể thêm {member.get('username', member['id'])} do cài đặt quyền riêng tư")
                    if callback:
                        callback(i + 1, len(members), False, member, "Cài đặt quyền riêng tư hạn chế")
                    
                    failed_members.append(member)
                    
                    # Nghỉ một khoảng thời gian ngắn
                    random_sleep(DEFAULT_SMALL_DELAY)
                    
                except Exception as e:
                    # Lỗi khác
                    logger.error(f"Lỗi khi thêm {member.get('username', member['id'])}: {str(e)}")
                    if callback:
                        callback(i + 1, len(members), False, member, str(e))
                    
                    failed_members.append(member)
                    
                    # Nghỉ một khoảng thời gian ngắn
                    random_sleep(DEFAULT_SMALL_DELAY)
                
                # Nếu số lượng lỗi liên tiếp quá nhiều, dừng để tránh bị ban
                consecutive_failures = 0
                if len(failed_members) >= 5 and all(m == failed_members[-5:] for m in members[i-4:i+1]):
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        logger.warning("Quá nhiều lỗi liên tiếp, tạm dừng 30 phút để tránh bị ban...")
                        random_sleep(1800, 2400)  # 30-40 phút
                        consecutive_failures = 0
            
            # Ngắt kết nối
            client.disconnect()
            
            return success_members, failed_members, None
            
        except Exception as e:
            if client:
                client.disconnect()
            return success_members, failed_members, str(e)
            
    def add_members_from_csv(self, phone: str, target_group: str, csv_file: str, 
                            delay: int = DEFAULT_ADD_DELAY, callback: Callable = None) -> Tuple[int, int, Optional[str]]:
        """
        Thêm thành viên vào nhóm/kênh từ file CSV
        
        Args:
            phone: Số điện thoại tài khoản dùng để thêm thành viên
            target_group: Username hoặc link của nhóm/kênh đích
            csv_file: Đường dẫn đến file CSV chứa danh sách thành viên
            delay: Thời gian chờ cơ bản giữa các lần thêm (giây)
            callback: Hàm callback để cập nhật tiến trình
            
        Returns:
            Tuple (success_count, failed_count, error) - Số lượng thành viên thêm thành công, thất bại và thông báo lỗi nếu có
        """
        # Đọc danh sách thành viên từ file CSV
        members = self.load_members_from_csv(csv_file)
        
        if not members:
            return 0, 0, f"Không tìm thấy thành viên trong file {csv_file}"
        
        # Thêm thành viên vào nhóm/kênh
        success, failed, error = self.add_members(phone, target_group, members, delay, callback)
        
        return len(success), len(failed), error 