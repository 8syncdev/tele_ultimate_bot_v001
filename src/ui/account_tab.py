"""
Tab quản lý tài khoản Telegram
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, 
    QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal

from src.core.telegram_client import TelegramAccountManager
from src.utils.logger import logger


class AccountTab(QWidget):
    """Tab quản lý tài khoản Telegram"""
    
    def __init__(self, account_manager: TelegramAccountManager, update_signal: QObject):
        super().__init__()
        self.account_manager = account_manager
        self.update_signal = update_signal
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
        
        # Phát tín hiệu cập nhật cho các tab khác
        self.update_signal.update_signal.emit()
        
        # Hiển thị thông báo
        QMessageBox.information(self, "Thành công", f"Đã thêm tài khoản {phone} thành công")
        
        # Nhắc người dùng xác thực
        reply = QMessageBox.question(
            self, 
            "Xác thực", 
            f"Bạn có muốn xác thực tài khoản {phone} ngay bây giờ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.authenticate_account(phone)
    
    def authenticate_account(self, specific_phone=None):
        """
        Xác thực tài khoản đã chọn
        
        Args:
            specific_phone: Số điện thoại cụ thể nếu muốn xác thực trực tiếp
        """
        if specific_phone:
            # Tìm tài khoản theo số điện thoại
            account = next((acc for acc in self.account_manager.accounts if acc['phone'] == specific_phone), None)
            if not account:
                QMessageBox.warning(self, "Lỗi", f"Không tìm thấy tài khoản {specific_phone}")
                return
            phone = specific_phone
        else:
            # Lấy tài khoản đã chọn trong danh sách
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
                
                # Phát tín hiệu cập nhật cho các tab khác
                self.update_signal.update_signal.emit()
                
                QMessageBox.information(self, "Thành công", f"Đã xóa tài khoản {phone} thành công")
            else:
                QMessageBox.warning(self, "Lỗi", f"Không thể xóa tài khoản {phone}") 