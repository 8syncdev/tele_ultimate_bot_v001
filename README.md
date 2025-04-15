# Telegram Ultimate Bot

Ứng dụng quản lý và tự động hóa các tác vụ Telegram, bao gồm:
- Scrape thành viên từ nhóm/kênh Telegram
- Thêm thành viên vào nhóm/kênh của bạn
- Giao diện người dùng đồ họa thân thiện

## Tính năng

- **Quản lý tài khoản Telegram**: Thêm, xóa và xác thực tài khoản Telegram
- **Scrape thành viên**: Lấy danh sách thành viên từ nhóm/kênh công khai hoặc riêng tư
- **Thêm thành viên**: Thêm thành viên vào nhóm/kênh của bạn
- **Xuất CSV**: Lưu danh sách thành viên vào file CSV
- **Hiển thị tiến trình thời gian thực**: Theo dõi tiến trình đào và thêm thành viên

## Cài đặt

### Yêu cầu hệ thống
- Python 3.7+
- Các thư viện Python trong file requirements.txt

### Cài đặt từ mã nguồn

1. Clone repository:
```
git clone https://github.com/username/tele_ultimate_bot.git
cd tele_ultimate_bot
```

2. Tạo và kích hoạt môi trường ảo:
```
python -m venv venv
source venv/bin/activate  # Trên Linux/Mac
venv\Scripts\activate     # Trên Windows
```

3. Cài đặt các gói phụ thuộc:
```
pip install -r requirements.txt
```

## Sử dụng

### Khởi động ứng dụng

```
python src/main.py
```

### Hướng dẫn sử dụng

#### 1. Thêm tài khoản Telegram

1. Truy cập [my.telegram.org](https://my.telegram.org/auth) để tạo ứng dụng và lấy API_ID và API_HASH
2. Chọn tab "Tài khoản" trong ứng dụng
3. Nhập API_ID, API_HASH và số điện thoại Telegram của bạn
4. Nhấn "Thêm tài khoản"
5. Chọn tài khoản trong danh sách và nhấn "Xác thực tài khoản" để đăng nhập

#### 2. Scrape thành viên

1. Chọn tab "Scrape thành viên"
2. Chọn tài khoản Telegram từ danh sách
3. Nhập username hoặc link của nhóm/kênh cần scrape
4. Đặt số lượng thành viên cần scrape (hoặc để 0 để lấy tất cả)
5. Nhấn "Scrape thành viên"
6. Sau khi hoàn tất, bạn có thể xuất danh sách thành viên ra file CSV

#### 3. Thêm thành viên

1. Chọn tab "Thêm thành viên"
2. Chọn tài khoản Telegram từ danh sách
3. Nhập username hoặc link của nhóm/kênh đích
4. Tải danh sách thành viên từ file CSV
5. Đặt số lượng thành viên cần thêm và độ trễ giữa các lần thêm
6. Nhấn "Thêm thành viên"

## Lưu ý

- Việc sử dụng ứng dụng này để spam hoặc quấy rối người dùng Telegram là vi phạm điều khoản dịch vụ của Telegram.
- Tài khoản Telegram của bạn có thể bị cấm nếu thực hiện quá nhiều hành động trong thời gian ngắn.
- Sử dụng ứng dụng này một cách có trách nhiệm và tuân thủ các điều khoản dịch vụ của Telegram.

## Giấy phép

Dự án này được phát hành dưới giấy phép MIT. Xem file LICENSE để biết thêm chi tiết. 