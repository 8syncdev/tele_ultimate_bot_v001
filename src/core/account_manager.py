"""
Module quản lý tài khoản Telegram
"""
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable

from telethon.sync import TelegramClient
from telethon.errors.rpcerrorlist import PhoneNumberBannedError, SessionPasswordNeededError

from config import TEMP_DIR
from src.utils.logger import logger

class TelegramAccountManager:
    """Quản lý tài khoản Telegram và phiên làm việc"""
    
    def __init__(self):
        """Khởi tạo quản lý tài khoản"""
        self.sessions_dir = TEMP_DIR / 'sessions'
        self.accounts_file = TEMP_DIR / 'accounts.pkl'
        self.accounts: List[Dict[str, Any]] = []
        
        # Tạo thư mục sessions nếu chưa tồn tại
        if not self.sessions_dir.exists():
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Tải danh sách tài khoản nếu có
        self.load_accounts()
    
    def load_accounts(self) -> List[Dict[str, Any]]:
        """Tải danh sách tài khoản từ file"""
        self.accounts = []
        if self.accounts_file.exists():
            try:
                with open(self.accounts_file, 'rb') as f:
                    while True:
                        try:
                            account = pickle.load(f)
                            self.accounts.append({
                                'api_id': account[0],
                                'api_hash': account[1],
                                'phone': account[2]
                            })
                        except EOFError:
                            break
            except Exception as e:
                logger.error(f"Lỗi khi tải danh sách tài khoản: {str(e)}")
        return self.accounts
    
    def save_accounts(self):
        """Lưu danh sách tài khoản vào file"""
        try:
            with open(self.accounts_file, 'wb') as f:
                for account in self.accounts:
                    pickle.dump([
                        account['api_id'],
                        account['api_hash'],
                        account['phone']
                    ], f)
            logger.info("Đã lưu danh sách tài khoản thành công")
        except Exception as e:
            logger.error(f"Lỗi khi lưu danh sách tài khoản: {str(e)}")
    
    def add_account(self, api_id: int, api_hash: str, phone: str) -> Dict[str, Any]:
        """
        Thêm tài khoản mới
        
        Args:
            api_id: API ID từ my.telegram.org
            api_hash: API Hash từ my.telegram.org
            phone: Số điện thoại đăng nhập
        
        Returns:
            Dict chứa thông tin tài khoản đã thêm
        """
        # Kiểm tra nếu tài khoản đã tồn tại
        for account in self.accounts:
            if account['phone'] == phone:
                logger.warning(f"Tài khoản với số điện thoại {phone} đã tồn tại")
                return account
        
        # Thêm tài khoản mới
        account = {'api_id': api_id, 'api_hash': api_hash, 'phone': phone}
        self.accounts.append(account)
        
        # Lưu danh sách tài khoản
        self.save_accounts()
        
        logger.info(f"Đã thêm tài khoản {phone} thành công")
        return account
    
    def remove_account(self, phone: str) -> bool:
        """
        Xóa tài khoản theo số điện thoại
        
        Args:
            phone: Số điện thoại của tài khoản cần xóa
        
        Returns:
            True nếu xóa thành công, False nếu không tìm thấy
        """
        for i, account in enumerate(self.accounts):
            if account['phone'] == phone:
                # Xóa phiên và tài khoản
                session_file = self.sessions_dir / f"{phone}.session"
                if session_file.exists():
                    session_file.unlink()
                
                # Xóa tài khoản khỏi danh sách
                del self.accounts[i]
                
                # Lưu danh sách tài khoản
                self.save_accounts()
                
                logger.info(f"Đã xóa tài khoản {phone} thành công")
                return True
        
        logger.warning(f"Không tìm thấy tài khoản với số điện thoại {phone}")
        return False
    
    def get_client(self, phone: str) -> Optional[TelegramClient]:
        """
        Tạo và trả về đối tượng TelegramClient cho tài khoản
        
        Args:
            phone: Số điện thoại của tài khoản
        
        Returns:
            TelegramClient nếu tạo thành công, None nếu không tìm thấy tài khoản
        """
        account = next((acc for acc in self.accounts if acc['phone'] == phone), None)
        if not account:
            logger.error(f"Không tìm thấy tài khoản với số điện thoại {phone}")
            return None
        
        # Tạo đường dẫn file session
        session_file = self.sessions_dir / phone
        
        # Tạo client
        try:
            client = TelegramClient(
                str(session_file),
                account['api_id'],
                account['api_hash']
            )
            return client
        except Exception as e:
            logger.error(f"Lỗi khi tạo client cho tài khoản {phone}: {str(e)}")
            return None
    
    def authenticate(self, phone: str, code_callback=None, password_callback=None) -> Tuple[bool, Optional[str]]:
        """
        Xác thực tài khoản Telegram
        
        Args:
            phone: Số điện thoại của tài khoản
            code_callback: Hàm callback để lấy mã xác thực
            password_callback: Hàm callback để lấy mật khẩu 2FA nếu có
        
        Returns:
            Tuple (bool, str) - trạng thái xác thực và thông báo lỗi nếu có
        """
        client = self.get_client(phone)
        if not client:
            return False, "Không tìm thấy tài khoản"
        
        try:
            client.connect()
            
            # Nếu đã đăng nhập thì trả về thành công
            if client.is_user_authorized():
                client.disconnect()
                return True, None
            
            # Gửi yêu cầu mã xác thực
            client.send_code_request(phone)
            
            # Lấy mã xác thực từ callback
            if not code_callback:
                code = input(f"Nhập mã xác thực cho {phone}: ")
            else:
                code = code_callback()
            
            # Đăng nhập với mã xác thực
            try:
                client.sign_in(phone, code)
            except SessionPasswordNeededError:
                # Nếu cần mật khẩu 2FA
                if not password_callback:
                    password = input(f"Nhập mật khẩu 2FA cho {phone}: ")
                else:
                    password = password_callback()
                
                client.sign_in(password=password)
            
            client.disconnect()
            return True, None
            
        except PhoneNumberBannedError:
            client.disconnect()
            self.remove_account(phone)
            return False, f"Số điện thoại {phone} đã bị cấm"
            
        except Exception as e:
            client.disconnect()
            return False, str(e) 