"""
Tab scrape thành viên từ nhóm/kênh Telegram
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, 
    QMessageBox, QFileDialog, QSpinBox, QProgressBar,
    QComboBox, QInputDialog
)
from PyQt6.QtCore import Qt

from src.config import TEMP_DIR, MEMBERS_DIR, MEMBER_CSV_FIELDS
from src.core.telegram_client import TelegramAccountManager
from src.ui.workers import ScraperWorker
from src.utils.helpers import save_to_csv
from src.utils.logger import logger


class ScraperTab(QWidget):
    """Tab scrape thành viên từ nhóm/kênh Telegram"""
    
    def __init__(self, account_manager: TelegramAccountManager):
        super().__init__()
        self.account_manager = account_manager
        self.members = []
        self.setup_ui()
        self.load_accounts()
    
    def setup_ui(self):
        """Thiết lập giao diện người dùng cho tab scrape"""
        layout = QVBoxLayout()
        
        # Chọn tài khoản
        account_group = QGroupBox("Chọn tài khoản để scrape")
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("Tài khoản:"))
        self.account_combo = QComboBox()
        account_layout.addWidget(self.account_combo)
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)
        
        # Nhập thông tin nhóm/kênh
        group_group = QGroupBox("Thông tin nhóm/kênh")
        group_layout = QVBoxLayout()
        
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Username/Link:"))
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Nhập username (không có @) hoặc link t.me/...")
        target_layout.addWidget(self.target_input)
        group_layout.addLayout(target_layout)
        
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(QLabel("Số lượng thành viên:"))
        self.limit_input = QSpinBox()
        self.limit_input.setRange(0, 100000)
        self.limit_input.setValue(1000)
        self.limit_input.setSpecialValueText("Không giới hạn")
        limit_layout.addWidget(self.limit_input)
        group_layout.addLayout(limit_layout)
        
        group_group.setLayout(group_layout)
        layout.addWidget(group_group)
        
        # Nút scrape và tiến trình
        scrape_layout = QVBoxLayout()
        self.scrape_btn = QPushButton("Scrape thành viên")
        self.scrape_btn.clicked.connect(self.start_scraping)
        scrape_layout.addWidget(self.scrape_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        scrape_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Sẵn sàng")
        scrape_layout.addWidget(self.status_label)
        
        layout.addLayout(scrape_layout)
        
        # Danh sách thành viên đã scrape
        members_group = QGroupBox("Danh sách thành viên")
        members_layout = QVBoxLayout()
        
        self.members_list = QListWidget()
        members_layout.addWidget(self.members_list)
        
        # Nút xuất danh sách thành CSV
        export_layout = QHBoxLayout()
        self.export_btn = QPushButton("Xuất danh sách (CSV)")
        self.export_btn.clicked.connect(self.export_members)
        export_layout.addWidget(self.export_btn)
        
        self.export_path_input = QLineEdit()
        self.export_path_input.setPlaceholderText("Đường dẫn file CSV")
        export_layout.addWidget(self.export_path_input)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_export_path)
        export_layout.addWidget(self.browse_btn)
        
        members_layout.addLayout(export_layout)
        members_group.setLayout(members_layout)
        layout.addWidget(members_group)
        
        self.setLayout(layout)
    
    def load_accounts(self):
        """Tải danh sách tài khoản vào combo box"""
        self.account_combo.clear()
        accounts = self.account_manager.load_accounts()
        
        for account in accounts:
            self.account_combo.addItem(account['phone'], account)
        
        # Cập nhật trạng thái nút scrape
        self.scrape_btn.setEnabled(self.account_combo.count() > 0)
    
    def check_account_authorized(self, phone: str) -> bool:
        """
        Kiểm tra xem tài khoản đã được xác thực chưa
        
        Args:
            phone: Số điện thoại tài khoản cần kiểm tra
            
        Returns:
            True nếu tài khoản đã xác thực, False nếu chưa
        """
        client = self.account_manager.get_client(phone)
        if not client:
            return False
        
        try:
            client.connect()
            authorized = client.is_user_authorized()
            client.disconnect()
            return authorized
        except Exception as e:
            logger.error(f"Lỗi kiểm tra xác thực: {str(e)}")
            return False
    
    def authenticate_account(self, phone: str) -> bool:
        """
        Xác thực tài khoản Telegram
        
        Args:
            phone: Số điện thoại của tài khoản
            
        Returns:
            True nếu xác thực thành công, False nếu thất bại
        """
        # Hàm callback để lấy mã xác thực
        def code_callback():
            code, ok = QInputDialog.getText(self, "Xác thực", f"Nhập mã xác thực cho {phone}:")
            if ok and code.strip():
                return code.strip()
            return ""
        
        # Hàm callback để lấy mật khẩu 2FA nếu có
        def password_callback():
            password, ok = QInputDialog.getText(
                self, "Xác thực 2FA", f"Nhập mật khẩu 2FA cho {phone}:", 
                QLineEdit.EchoMode.Password
            )
            if ok and password.strip():
                return password.strip()
            return ""
        
        # Thực hiện xác thực
        success, error = self.account_manager.authenticate(phone, code_callback, password_callback)
        
        if success:
            QMessageBox.information(self, "Thành công", f"Đã xác thực tài khoản {phone} thành công")
            return True
        else:
            QMessageBox.warning(self, "Lỗi", f"Xác thực thất bại: {error}")
            return False
    
    def start_scraping(self):
        """Bắt đầu scrape thành viên"""
        if self.account_combo.count() == 0:
            QMessageBox.warning(self, "Lỗi", "Không có tài khoản nào. Vui lòng thêm tài khoản trước.")
            return
        
        # Lấy thông tin input
        account = self.account_combo.currentData()
        phone = account['phone']
        target_group = self.target_input.text().strip()
        limit = self.limit_input.value()
        
        if not target_group:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập username hoặc link của nhóm/kênh")
            return
        
        # Kiểm tra xác thực tài khoản
        if not self.check_account_authorized(phone):
            reply = QMessageBox.question(
                self, 
                "Cần xác thực", 
                f"Tài khoản {phone} chưa được xác thực. Bạn có muốn xác thực ngay bây giờ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if not self.authenticate_account(phone):
                    return  # Nếu xác thực thất bại, dừng lại
            else:
                return  # Nếu không xác thực, dừng lại
        
        # Tạo worker thread để scrape
        self.scraper_worker = ScraperWorker(
            self.account_manager,
            phone,
            target_group,
            limit
        )
        
        # Kết nối signals
        self.scraper_worker.progress_signal.connect(self.update_progress)
        self.scraper_worker.finished_signal.connect(self.scraping_finished)
        self.scraper_worker.error_signal.connect(self.scraping_error)
        
        # Cập nhật UI
        self.scrape_btn.setEnabled(False)
        self.status_label.setText("Đang scrape thành viên...")
        self.members_list.clear()
        self.progress_bar.setValue(0)
        
        # Bắt đầu worker
        self.scraper_worker.start()
    
    def update_progress(self, count):
        """Cập nhật tiến trình"""
        self.status_label.setText(f"Đã scrape được {count} thành viên")
        # Nếu có limit thì cập nhật progress bar theo phần trăm
        if self.limit_input.value() > 0:
            percent = min(100, int(count * 100 / self.limit_input.value()))
            self.progress_bar.setValue(percent)
    
    def scraping_finished(self, members):
        """Xử lý khi scrape hoàn tất"""
        self.members = members
        self.status_label.setText(f"Hoàn tất! Đã scrape được {len(members)} thành viên")
        self.progress_bar.setValue(100)
        self.scrape_btn.setEnabled(True)
        
        # Hiển thị danh sách thành viên
        self.members_list.clear()
        for member in members:
            username = member['username'] or "No username"
            name = f"{member['first_name']} {member['last_name']}".strip() or "No name"
            item_text = f"{username} - {name} ({member['status']})"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, member)
            self.members_list.addItem(item)
        
        # Hiển thị thông báo
        QMessageBox.information(self, "Thành công", f"Đã scrape được {len(members)} thành viên")
    
    def scraping_error(self, error):
        """Xử lý khi có lỗi"""
        self.status_label.setText(f"Lỗi: {error}")
        self.scrape_btn.setEnabled(True)
        QMessageBox.critical(self, "Lỗi", f"Scrape thất bại: {error}")
    
    def browse_export_path(self):
        """Chọn đường dẫn file xuất CSV"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Chọn vị trí lưu file CSV",
            str(MEMBERS_DIR / "members.csv"),
            "CSV Files (*.csv)"
        )
        
        if path:
            self.export_path_input.setText(path)
    
    def export_members(self):
        """Xuất danh sách thành viên ra file CSV"""
        if not self.members:
            QMessageBox.warning(self, "Lỗi", "Không có dữ liệu thành viên để xuất")
            return
        
        # Lấy đường dẫn file
        file_path = self.export_path_input.text().strip()
        if not file_path:
            file_path = str(MEMBERS_DIR / "members.csv")
            self.export_path_input.setText(file_path)
        
        # Xuất ra CSV
        try:
            # Sử dụng các trường từ cấu hình
            save_to_csv(file_path, self.members, MEMBER_CSV_FIELDS)
            
            QMessageBox.information(
                self, 
                "Thành công", 
                f"Đã xuất {len(self.members)} thành viên ra file {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất file CSV: {str(e)}") 