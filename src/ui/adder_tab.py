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

from src.config import MEMBERS_DIR
from src.core.telegram_client import TelegramAccountManager
from src.ui.workers import AdderWorker, CSVAdderWorker
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
        limit_layout.addWidget(QLabel("Giới hạn:"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 10000)
        self.limit_spin.setValue(0)
        self.limit_spin.setSpecialValueText("Không giới hạn")
        limit_layout.addWidget(self.limit_spin)
        
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Thời gian chờ (giây):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(30, 300)
        self.delay_spin.setValue(60)
        delay_layout.addWidget(self.delay_spin)
        
        options_layout.addLayout(limit_layout)
        options_layout.addLayout(delay_layout)
        
        # Thêm nút thêm từ CSV trực tiếp
        direct_csv_layout = QHBoxLayout()
        direct_csv_layout.addWidget(QLabel("Thêm trực tiếp từ CSV:"))
        self.add_from_csv_btn = QPushButton("Thêm từ CSV")
        self.add_from_csv_btn.clicked.connect(self.add_from_csv)
        direct_csv_layout.addWidget(self.add_from_csv_btn)
        
        members_layout.addLayout(options_layout)
        members_layout.addLayout(direct_csv_layout)
        
        # Danh sách thành viên
        self.members_list = QListWidget()
        members_layout.addWidget(self.members_list)
        
        members_group.setLayout(members_layout)
        layout.addWidget(members_group)
        
        # Nút thêm thành viên
        buttons_layout = QHBoxLayout()
        self.add_btn = QPushButton("Thêm thành viên")
        self.add_btn.clicked.connect(self.add_members)
        self.add_btn.setEnabled(False)
        buttons_layout.addWidget(self.add_btn)
        
        layout.addLayout(buttons_layout)
        
        # Hiển thị kết quả
        results_group = QGroupBox("Kết quả")
        results_layout = QVBoxLayout()
        
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Sẵn sàng")
        progress_layout.addWidget(self.status_label)
        
        results_layout.addLayout(progress_layout)
        
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
    
    def browse_load_path(self):
        """Chọn file CSV chứa danh sách thành viên"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file CSV chứa danh sách thành viên",
            str(MEMBERS_DIR),
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
                user_id = member.get('user_id', member.get('id', ''))
                item_text = f"{username} - {user_id}"
                
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
    
    def update_add_button_state(self):
        """Cập nhật trạng thái nút thêm"""
        has_account = self.account_combo.count() > 0
        has_members = len(self.members) > 0 or bool(self.load_path_input.text().strip())
        target_valid = bool(self.target_input.text().strip())
        
        self.add_btn.setEnabled(has_account and has_members and target_valid)
        self.add_from_csv_btn.setEnabled(has_account and target_valid)
    
    def add_members(self):
        """Thêm thành viên vào nhóm/kênh"""
        if not self.members:
            QMessageBox.warning(self, "Lỗi", "Không có dữ liệu thành viên để thêm")
            return
        
        # Lấy thông tin tài khoản và nhóm đích
        current_idx = self.account_combo.currentIndex()
        if current_idx < 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn tài khoản")
            return
        
        account = self.account_combo.currentData()
        phone = account['phone']
        
        target_group = self.target_input.text().strip()
        if not target_group:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập username hoặc link của nhóm/kênh đích")
            return
        
        # Lấy giới hạn và thời gian chờ
        limit = self.limit_spin.value()
        if limit > 0 and limit < len(self.members):
            self.members = self.members[:limit]
        
        delay = self.delay_spin.value()
        
        # Cập nhật giao diện
        self.add_btn.setEnabled(False)
        self.add_from_csv_btn.setEnabled(False)
        self.results_text.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Đang thêm thành viên...")
        
        # Tạo worker thread
        self.worker = AdderWorker(
            self.account_manager,
            phone,
            target_group,
            self.members,
            delay
        )
        
        # Kết nối signals
        self.worker.progress_signal.connect(self.adding_progress)
        self.worker.finished_signal.connect(self.adding_finished)
        self.worker.error_signal.connect(self.adding_error)
        
        # Bắt đầu thread
        self.worker.start()
    
    def add_from_csv(self):
        """Thêm thành viên trực tiếp từ file CSV"""
        # Lấy đường dẫn file CSV
        file_path = self.load_path_input.text().strip()
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Chọn file CSV chứa danh sách thành viên",
                str(MEMBERS_DIR),
                "CSV Files (*.csv)"
            )
            
            if not file_path:
                return
            
            self.load_path_input.setText(file_path)
        
        # Lấy thông tin tài khoản và nhóm đích
        current_idx = self.account_combo.currentIndex()
        if current_idx < 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn tài khoản")
            return
        
        account = self.account_combo.currentData()
        phone = account['phone']
        
        target_group = self.target_input.text().strip()
        if not target_group:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập username hoặc link của nhóm/kênh đích")
            return
        
        # Lấy thời gian chờ
        delay = self.delay_spin.value()
        
        # Cập nhật giao diện
        self.add_btn.setEnabled(False)
        self.add_from_csv_btn.setEnabled(False)
        self.results_text.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Đang thêm thành viên từ CSV...")
        
        # Tạo worker thread
        self.csv_worker = CSVAdderWorker(
            self.account_manager,
            phone,
            target_group,
            file_path,
            delay
        )
        
        # Kết nối signals
        self.csv_worker.progress_signal.connect(self.adding_progress)
        self.csv_worker.finished_signal.connect(self.csv_adding_finished)
        self.csv_worker.error_signal.connect(self.adding_error)
        
        # Bắt đầu thread
        self.csv_worker.start()
    
    def adding_progress(self, current, total, success, member, error_msg=""):
        """Cập nhật tiến trình thêm thành viên"""
        # Cập nhật progress bar
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        
        # Cập nhật status
        self.status_label.setText(f"Đang thêm: {current}/{total} ({progress}%)")
        
        # Cập nhật log
        log_text = f"[{current}/{total}] "
        if success:
            log_text += f"Đã thêm thành công: {member.get('username', member.get('id', 'Unknown'))}"
        else:
            log_text += f"Thêm thất bại: {member.get('username', member.get('id', 'Unknown'))} - {error_msg}"
        
        self.results_text.append(log_text)
        # Cuộn xuống dưới để hiển thị log mới nhất
        self.results_text.verticalScrollBar().setValue(self.results_text.verticalScrollBar().maximum())
    
    def adding_finished(self, success, failed):
        """Xử lý khi thêm thành viên hoàn tất"""
        self.status_label.setText("Hoàn tất!")
        self.progress_bar.setValue(100)
        
        success_count = len(success)
        failed_count = len(failed)
        
        summary = f"\n=== KẾT QUẢ ===\n"
        summary += f"Tổng số: {success_count + failed_count}\n"
        summary += f"Thành công: {success_count}\n"
        summary += f"Thất bại: {failed_count}\n"
        
        self.results_text.append(summary)
        
        # Thông báo kết quả
        QMessageBox.information(
            self,
            "Thành công",
            f"Đã thêm {success_count} thành viên, {failed_count} thất bại"
        )
        
        # Cập nhật giao diện
        self.add_btn.setEnabled(True)
        self.add_from_csv_btn.setEnabled(True)
    
    def csv_adding_finished(self, success_count, failed_count):
        """Xử lý khi thêm thành viên từ CSV hoàn tất"""
        self.status_label.setText("Hoàn tất!")
        self.progress_bar.setValue(100)
        
        summary = f"\n=== KẾT QUẢ ===\n"
        summary += f"Tổng số: {success_count + failed_count}\n"
        summary += f"Thành công: {success_count}\n"
        summary += f"Thất bại: {failed_count}\n"
        
        self.results_text.append(summary)
        
        # Thông báo kết quả
        QMessageBox.information(
            self,
            "Thành công",
            f"Đã thêm {success_count} thành viên, {failed_count} thất bại"
        )
        
        # Cập nhật giao diện
        self.add_btn.setEnabled(True)
        self.add_from_csv_btn.setEnabled(True)
    
    def adding_error(self, error):
        """Xử lý khi có lỗi"""
        self.status_label.setText(f"Lỗi: {error}")
        
        self.results_text.append(f"\n!!! LỖI: {error}")
        
        # Thông báo lỗi
        QMessageBox.critical(self, "Lỗi", f"Thêm thành viên thất bại: {error}")
        
        # Cập nhật giao diện
        self.add_btn.setEnabled(True)
        self.add_from_csv_btn.setEnabled(True) 