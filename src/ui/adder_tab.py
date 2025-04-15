"""
Tab thêm thành viên vào nhóm/kênh Telegram
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, 
    QMessageBox, QFileDialog, QSpinBox, QProgressBar,
    QComboBox, QTextEdit, QInputDialog
)
from PyQt6.QtCore import Qt

from config import TEMP_DIR
from src.core.telegram_client import TelegramAccountManager
from src.ui.workers import AdderWorker
from src.utils.helpers import load_from_csv
from src.utils.logger import logger


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
        
        # Cập nhật trạng thái nút thêm
        self.update_add_button_state()
    
    def update_add_button_state(self):
        """Cập nhật trạng thái nút thêm thành viên"""
        has_account = self.account_combo.count() > 0
        has_members = len(self.members) > 0
        self.add_btn.setEnabled(has_account and has_members)
    
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
            
            # Cập nhật trạng thái nút thêm
            self.update_add_button_state()
            
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
        phone = account['phone']
        target_group = self.target_input.text().strip()
        limit = self.limit_input.value()
        delay = self.delay_input.value()
        
        if not target_group:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập username hoặc link của nhóm/kênh đích")
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
        
        # Lấy số lượng thành viên cần thêm
        members_to_add = self.members
        if limit > 0 and limit < len(members_to_add):
            members_to_add = members_to_add[:limit]
        
        # Tạo worker thread để thêm thành viên
        self.adder_worker = AdderWorker(
            self.account_manager,
            phone,
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