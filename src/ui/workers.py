"""
Module worker threads cho tác vụ không đồng bộ
"""
import asyncio
from typing import List, Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal

from src.core.telegram_client import TelegramAccountManager, TelegramScraper, TelegramAdder
from src.utils.logger import logger


class ScraperWorker(QThread):
    """Worker thread cho việc scrape thành viên"""
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, account_manager: TelegramAccountManager, phone: str, target_group: str, limit: int = 0):
        super().__init__()
        self.account_manager = account_manager
        self.phone = phone
        self.target_group = target_group
        self.limit = limit
        self.scraper = TelegramScraper(account_manager)
        self.loop = None
    
    def run(self):
        """Thực hiện scrape thành viên"""
        try:
            # Thiết lập event loop cho thread hiện tại
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            def progress_callback(count):
                if count is not None and isinstance(count, int) and count >= 0:
                    self.progress_signal.emit(count)
                else:
                    logger.warning(f"Nhận được giá trị không hợp lệ từ callback: {count}")
            
            members, error = self.scraper.scrape_members(
                self.phone, 
                self.target_group, 
                self.limit, 
                progress_callback
            )
            
            if error:
                self.error_signal.emit(error)
            else:
                self.finished_signal.emit(members)
                
        except Exception as e:
            logger.error(f"Lỗi ScraperWorker: {str(e)}")
            self.error_signal.emit(str(e))
        finally:
            # Dọn dẹp event loop
            if self.loop:
                self.loop.close()


class AdderWorker(QThread):
    """Worker thread cho việc thêm thành viên"""
    progress_signal = pyqtSignal(int, int, bool, dict, str)
    finished_signal = pyqtSignal(list, list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, account_manager: TelegramAccountManager, phone: str, target_group: str, 
                members: List[Dict[str, Any]], delay: int = 30):
        super().__init__()
        self.account_manager = account_manager
        self.phone = phone
        self.target_group = target_group
        self.members = members
        self.delay = delay
        self.adder = TelegramAdder(account_manager)
        self.loop = None
    
    def run(self):
        """Thực hiện thêm thành viên"""
        try:
            # Thiết lập event loop cho thread hiện tại
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            def progress_callback(current, total, success, member, error_msg=""):
                self.progress_signal.emit(current, total, success, member, error_msg)
            
            success, failed, error = self.adder.add_members(
                self.phone,
                self.target_group,
                self.members,
                self.delay,
                progress_callback
            )
            
            if error:
                self.error_signal.emit(error)
            else:
                self.finished_signal.emit(success, failed)
                
        except Exception as e:
            logger.error(f"Lỗi AdderWorker: {str(e)}")
            self.error_signal.emit(str(e))
        finally:
            # Dọn dẹp event loop
            if self.loop:
                self.loop.close() 