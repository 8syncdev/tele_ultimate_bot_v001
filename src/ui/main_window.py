"""
Cửa sổ chính của ứng dụng Telegram Ultimate Bot
"""
from PyQt6.QtWidgets import QMainWindow, QTabWidget
from PyQt6.QtCore import pyqtSignal, QObject

from src.core.telegram_client import TelegramAccountManager
from src.ui.account_tab import AccountTab
from src.ui.scraper_tab import ScraperTab
from src.ui.adder_tab import AdderTab
from src.utils.logger import logger


class AccountUpdateSignal(QObject):
    """Class trung gian để phát tín hiệu cập nhật tài khoản"""
    update_signal = pyqtSignal()


class MainWindow(QMainWindow):
    """Cửa sổ chính của ứng dụng"""
    
    def __init__(self):
        super().__init__()
        # Tạo signal cập nhật tài khoản
        self.account_update_signal = AccountUpdateSignal()
        
        # Khởi tạo tài khoản manager
        self.account_manager = TelegramAccountManager()
        
        # Thiết lập UI
        self.setup_ui()
        
        # Kết nối signal cập nhật tài khoản đến các tab
        self.connect_account_update_signal()
    
    def setup_ui(self):
        """Thiết lập giao diện người dùng cho cửa sổ chính"""
        self.setWindowTitle("Telegram Ultimate Bot")
        self.setMinimumSize(800, 600)
        
        # Tạo tab widget
        self.tab_widget = QTabWidget()
        
        # Tạo các tab
        self.account_tab = AccountTab(self.account_manager, self.account_update_signal)
        self.scraper_tab = ScraperTab(self.account_manager)
        self.adder_tab = AdderTab(self.account_manager)
        
        # Thêm các tab vào tab widget
        self.tab_widget.addTab(self.account_tab, "Tài khoản")
        self.tab_widget.addTab(self.scraper_tab, "Scrape thành viên")
        self.tab_widget.addTab(self.adder_tab, "Thêm thành viên")
        
        # Đặt tab widget là widget trung tâm
        self.setCentralWidget(self.tab_widget)
    
    def connect_account_update_signal(self):
        """Kết nối tín hiệu cập nhật tài khoản đến các tab"""
        self.account_update_signal.update_signal.connect(self.scraper_tab.load_accounts)
        self.account_update_signal.update_signal.connect(self.adder_tab.load_accounts) 