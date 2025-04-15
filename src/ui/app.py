"""
Module chính xử lý giao diện người dùng của ứng dụng
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, 
    QPushButton, QLineEdit, QLabel, QSpinBox, QTextEdit, QMessageBox,
    QFileDialog, QHBoxLayout, QGroupBox, QListWidget, QListWidgetItem,
    QProgressBar, QComboBox, QCheckBox, QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap

from config import BASE_DIR, TEMP_DIR, TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE
from src.core.telegram_client import TelegramAccountManager, TelegramScraper, TelegramAdder
from src.utils.helpers import save_to_csv, load_from_csv, ensure_dir
from src.utils.logger import logger
from src.ui.main_window import MainWindow


class ScraperWorker(QThread):
    """Worker thread cho việc scrape thành viên"""
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, account_manager, phone: str, target_group: str, limit: int = 0):
        super().__init__()
        self.account_manager = account_manager
        self.phone = phone
        self.target_group = target_group
        self.limit = limit
        self.scraper = TelegramScraper(account_manager)
    
    def run(self):
        """Thực hiện scrape thành viên"""
        try:
            def progress_callback(count):
                self.progress_signal.emit(count)
            
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
            self.error_signal.emit(str(e))


class AdderWorker(QThread):
    """Worker thread cho việc thêm thành viên"""
    progress_signal = pyqtSignal(int, int, bool, dict, str)
    finished_signal = pyqtSignal(list, list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, account_manager, phone: str, target_group: str, members: List[Dict[str, Any]], delay: int = 30):
        super().__init__()
        self.account_manager = account_manager
        self.phone = phone
        self.target_group = target_group
        self.members = members
        self.delay = delay
        self.adder = TelegramAdder(account_manager)
    
    def run(self):
        """Thực hiện thêm thành viên"""
        try:
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
            self.error_signal.emit(str(e))


class AccountTab(QWidget):
    """Tab quản lý tài khoản Telegram"""
    
    def __init__(self, account_manager: TelegramAccountManager):
        super().__init__()
        self.account_manager = account_manager
        self.setup_ui()
        self.load_accounts()
    
    def setup_ui(self):
        """Thiết lập giao diện người dùng cho tab tài khoản"""
        layout = QVBoxLayout()
        
        # Form nhập tài khoản mới
        form_group = QGroupBox("Thêm tài khoản Telegram mới")
        form_layout = QVBoxLayout()
        
        # Input API ID
        api_id_layout = QHBoxLayout()
        api_id_layout.addWidget(QLabel("API ID:"))
        self.api_id_input = QLineEdit()
        self.api_id_input.setPlaceholderText("Nhập API ID từ my.telegram.org")
        api_id_layout.addWidget(self.api_id_input)
        form_layout.addLayout(api_id_layout)
        
        # Input API Hash
        api_hash_layout = QHBoxLayout()
        api_hash_layout.addWidget(QLabel("API Hash:"))
        self.api_hash_input = QLineEdit()
        self.api_hash_input.setPlaceholderText("Nhập API Hash từ my.telegram.org")
        api_hash_layout.addWidget(self.api_hash_input)
        form_layout.addLayout(api_hash_layout)
        
        # Input số điện thoại
        phone_layout = QHBoxLayout()
        phone_layout.addWidget(QLabel("Số điện thoại:"))
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Định dạng: +84123456789")
        phone_layout.addWidget(self.phone_input)
        form_layout.addLayout(phone_layout)
        
        # Nút thêm tài khoản
        self.add_btn = QPushButton("Thêm tài khoản")
        self.add_btn.clicked.connect(self.add_account)
        form_layout.addWidget(self.add_btn)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Danh sách tài khoản hiện có
        accounts_group = QGroupBox("Danh sách tài khoản")
        accounts_layout = QVBoxLayout()
        
        self.accounts_list = QListWidget()
        accounts_layout.addWidget(self.accounts_list)
        
        # Các nút xác thực và xóa tài khoản
        btn_layout = QHBoxLayout()
        self.auth_btn = QPushButton("Xác thực tài khoản")
        self.auth_btn.clicked.connect(self.authenticate_account)
        btn_layout.addWidget(self.auth_btn)
        
        self.delete_btn = QPushButton("Xóa tài khoản")
        self.delete_btn.clicked.connect(self.delete_account)
        btn_layout.addWidget(self.delete_btn)
        
        accounts_layout.addLayout(btn_layout)
        accounts_group.setLayout(accounts_layout)
        layout.addWidget(accounts_group)
        
        self.setLayout(layout)
    
    def load_accounts(self):
        """Tải danh sách tài khoản vào list widget"""
        self.accounts_list.clear()
        accounts = self.account_manager.load_accounts()
        
        for account in accounts:
            item_text = f"{account['phone']} (API ID: {account['api_id']})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, account)
            self.accounts_list.addItem(item)
    
    def add_account(self):
        """Thêm tài khoản mới"""
        api_id = self.api_id_input.text().strip()
        api_hash = self.api_hash_input.text().strip()
        phone = self.phone_input.text().strip()
        
        if not api_id or not api_hash or not phone:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin tài khoản")
            return
        
        try:
            api_id = int(api_id)
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "API ID phải là số nguyên")
            return
        
        account = self.account_manager.add_account(api_id, api_hash, phone)
        
        # Xóa input sau khi thêm thành công
        self.api_id_input.clear()
        self.api_hash_input.clear()
        self.phone_input.clear()
        
        # Cập nhật danh sách tài khoản
        self.load_accounts()
        
        # Hiển thị thông báo
        QMessageBox.information(self, "Thành công", f"Đã thêm tài khoản {phone} thành công")
    
    def authenticate_account(self):
        """Xác thực tài khoản đã chọn"""
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn tài khoản để xác thực")
            return
        
        account = selected_items[0].data(Qt.ItemDataRole.UserRole)
        phone = account['phone']
        
        # Hàm callback để lấy mã xác thực
        def code_callback():
            code, ok = QInputDialog.getText(self, "Xác thực", f"Nhập mã xác thực cho {phone}:")
            if ok and code.strip():
                return code.strip()
            return ""
        
        # Hàm callback để lấy mật khẩu 2FA nếu có
        def password_callback():
            password, ok = QInputDialog.getText(self, "Xác thực 2FA", f"Nhập mật khẩu 2FA cho {phone}:", QLineEdit.EchoMode.Password)
            if ok and password.strip():
                return password.strip()
            return ""
        
        # Thực hiện xác thực
        success, error = self.account_manager.authenticate(phone, code_callback, password_callback)
        
        if success:
            QMessageBox.information(self, "Thành công", f"Đã xác thực tài khoản {phone} thành công")
        else:
            QMessageBox.warning(self, "Lỗi", f"Xác thực thất bại: {error}")
    
    def delete_account(self):
        """Xóa tài khoản đã chọn"""
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn tài khoản để xóa")
            return
        
        account = selected_items[0].data(Qt.ItemDataRole.UserRole)
        phone = account['phone']
        
        # Hiển thị hộp thoại xác nhận
        reply = QMessageBox.question(
            self, 
            "Xác nhận xóa", 
            f"Bạn có chắc chắn muốn xóa tài khoản {phone}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.account_manager.remove_account(phone)
            if success:
                # Cập nhật danh sách tài khoản
                self.load_accounts()
                QMessageBox.information(self, "Thành công", f"Đã xóa tài khoản {phone} thành công")
            else:
                QMessageBox.warning(self, "Lỗi", f"Không thể xóa tài khoản {phone}")


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
    
    def start_scraping(self):
        """Bắt đầu scrape thành viên"""
        if self.account_combo.count() == 0:
            QMessageBox.warning(self, "Lỗi", "Không có tài khoản nào. Vui lòng thêm tài khoản trước.")
            return
        
        # Lấy thông tin input
        account = self.account_combo.currentData()
        target_group = self.target_input.text().strip()
        limit = self.limit_input.value()
        
        if not target_group:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập username hoặc link của nhóm/kênh")
            return
        
        # Tạo worker thread để scrape
        self.scraper_worker = ScraperWorker(
            self.account_manager,
            account['phone'],
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
            str(TEMP_DIR / "members.csv"),
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
            file_path = str(TEMP_DIR / "members.csv")
            self.export_path_input.setText(file_path)
        
        # Xuất ra CSV
        try:
            headers = ['id', 'access_hash', 'username', 'first_name', 'last_name', 'status', 'group', 'group_id']
            save_to_csv(file_path, self.members, headers)
            
            QMessageBox.information(
                self, 
                "Thành công", 
                f"Đã xuất {len(self.members)} thành viên ra file {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất file CSV: {str(e)}")


class AdderTab(QWidget):
    """Tab thêm thành viên vào nhóm/kênh Telegram"""
    
    def __init__(self, account_manager: TelegramAccountManager):
        super().__init__()
        self.account_manager = account_manager
        self.members = []
        self.setup_ui()
        self.load_accounts()
    
    def setup_ui(self):
        """Thiết lập giao diện người dùng cho tab thêm thành viên"""
        layout = QVBoxLayout()
        
        # Chọn tài khoản
        account_group = QGroupBox("Chọn tài khoản để thêm thành viên")
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("Tài khoản:"))
        self.account_combo = QComboBox()
        account_layout.addWidget(self.account_combo)
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)
        
        # Nhập thông tin nhóm/kênh đích
        target_group = QGroupBox("Thông tin nhóm/kênh đích")
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Username/Link:"))
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Nhập username (không có @) hoặc link t.me/...")
        target_layout.addWidget(self.target_input)
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)
        
        # Tải danh sách thành viên từ file CSV
        members_group = QGroupBox("Danh sách thành viên")
        members_layout = QVBoxLayout()
        
        load_layout = QHBoxLayout()
        self.load_path_input = QLineEdit()
        self.load_path_input.setPlaceholderText("Đường dẫn file CSV chứa danh sách thành viên")
        load_layout.addWidget(self.load_path_input)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_load_path)
        load_layout.addWidget(self.browse_btn)
        
        self.load_btn = QPushButton("Tải danh sách")
        self.load_btn.clicked.connect(self.load_members)
        load_layout.addWidget(self.load_btn)
        
        members_layout.addLayout(load_layout)
        
        # Limit và delay
        options_layout = QHBoxLayout()
        
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(QLabel("Số lượng thêm:"))
        self.limit_input = QSpinBox()
        self.limit_input.setRange(0, 10000)
        self.limit_input.setValue(0)
        self.limit_input.setSpecialValueText("Tất cả")
        limit_layout.addWidget(self.limit_input)
        options_layout.addLayout(limit_layout)
        
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Độ trễ (giây):"))
        self.delay_input = QSpinBox()
        self.delay_input.setRange(5, 300)
        self.delay_input.setValue(30)
        delay_layout.addWidget(self.delay_input)
        options_layout.addLayout(delay_layout)
        
        members_layout.addLayout(options_layout)
        
        # Danh sách thành viên đã tải
        self.members_list = QListWidget()
        members_layout.addWidget(self.members_list)
        
        members_group.setLayout(members_layout)
        layout.addWidget(members_group)
        
        # Nút thêm và tiến trình
        add_layout = QVBoxLayout()
        self.add_btn = QPushButton("Thêm thành viên")
        self.add_btn.clicked.connect(self.start_adding)
        add_layout.addWidget(self.add_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        add_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Sẵn sàng")
        add_layout.addWidget(self.status_label)
        
        layout.addLayout(add_layout)
        
        # Kết quả thêm thành viên
        results_group = QGroupBox("Kết quả thêm thành viên")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        self.setLayout(layout)
    
    def load_accounts(self):
        """Tải danh sách tài khoản vào combo box"""
        self.account_combo.clear()
        accounts = self.account_manager.load_accounts()
        
        for account in accounts:
            self.account_combo.addItem(account['phone'], account)
    
    def browse_load_path(self):
        """Chọn file CSV chứa danh sách thành viên"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file CSV chứa danh sách thành viên",
            str(TEMP_DIR),
            "CSV Files (*.csv)"
        )
        
        if path:
            self.load_path_input.setText(path)
    
    def load_members(self):
        """Tải danh sách thành viên từ file CSV"""
        file_path = self.load_path_input.text().strip()
        if not file_path:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file CSV chứa danh sách thành viên")
            return
        
        try:
            self.members = load_from_csv(file_path)
            
            # Hiển thị danh sách thành viên
            self.members_list.clear()
            for member in self.members:
                username = member.get('username', '') or "No username"
                name = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip() or "No name"
                item_text = f"{username} - {name}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, member)
                self.members_list.addItem(item)
            
            # Hiển thị thông báo
            QMessageBox.information(
                self, 
                "Thành công", 
                f"Đã tải {len(self.members)} thành viên từ file {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải file CSV: {str(e)}")
    
    def start_adding(self):
        """Bắt đầu thêm thành viên"""
        if self.account_combo.count() == 0:
            QMessageBox.warning(self, "Lỗi", "Không có tài khoản nào. Vui lòng thêm tài khoản trước.")
            return
        
        if not self.members:
            QMessageBox.warning(self, "Lỗi", "Không có danh sách thành viên. Vui lòng tải danh sách trước.")
            return
        
        # Lấy thông tin input
        account = self.account_combo.currentData()
        target_group = self.target_input.text().strip()
        limit = self.limit_input.value()
        delay = self.delay_input.value()
        
        if not target_group:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập username hoặc link của nhóm/kênh đích")
            return
        
        # Lấy số lượng thành viên cần thêm
        members_to_add = self.members
        if limit > 0 and limit < len(members_to_add):
            members_to_add = members_to_add[:limit]
        
        # Tạo worker thread để thêm thành viên
        self.adder_worker = AdderWorker(
            self.account_manager,
            account['phone'],
            target_group,
            members_to_add,
            delay
        )
        
        # Kết nối signals
        self.adder_worker.progress_signal.connect(self.update_progress)
        self.adder_worker.finished_signal.connect(self.adding_finished)
        self.adder_worker.error_signal.connect(self.adding_error)
        
        # Cập nhật UI
        self.add_btn.setEnabled(False)
        self.status_label.setText("Đang thêm thành viên...")
        self.progress_bar.setValue(0)
        self.results_text.clear()
        
        # Bắt đầu worker
        self.adder_worker.start()
    
    def update_progress(self, current, total, success, member, error_msg=""):
        """Cập nhật tiến trình thêm thành viên"""
        percent = min(100, int(current * 100 / total))
        self.progress_bar.setValue(percent)
        
        # Cập nhật status
        self.status_label.setText(f"Đang thêm: {current}/{total} thành viên")
        
        # Thêm kết quả vào text box
        username = member.get('username', '') or member.get('id', '')
        if success:
            result = f"✅ Đã thêm thành công: {username}\n"
        else:
            result = f"❌ Không thể thêm: {username} - Lỗi: {error_msg}\n"
        
        self.results_text.append(result)
        # Cuộn xuống cuối
        self.results_text.verticalScrollBar().setValue(
            self.results_text.verticalScrollBar().maximum()
        )
    
    def adding_finished(self, success, failed):
        """Xử lý khi thêm thành viên hoàn tất"""
        self.add_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Hoàn tất! Thành công: {len(success)}, Thất bại: {len(failed)}")
        
        # Thêm tổng kết vào text box
        summary = f"\n=== KẾT QUẢ ===\n"
        summary += f"Tổng số thành viên: {len(success) + len(failed)}\n"
        summary += f"Thành công: {len(success)}\n"
        summary += f"Thất bại: {len(failed)}\n"
        
        self.results_text.append(summary)
        
        # Hiển thị thông báo
        QMessageBox.information(
            self, 
            "Thành công", 
            f"Đã hoàn tất việc thêm thành viên!\nThành công: {len(success)}, Thất bại: {len(failed)}"
        )
    
    def adding_error(self, error):
        """Xử lý khi có lỗi"""
        self.add_btn.setEnabled(True)
        self.status_label.setText(f"Lỗi: {error}")
        
        # Thêm lỗi vào text box
        self.results_text.append(f"\n❌ LỖI: {error}\n")
        
        # Hiển thị thông báo
        QMessageBox.critical(self, "Lỗi", f"Thêm thành viên thất bại: {error}")


def start_application():
    """Khởi chạy ứng dụng"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 