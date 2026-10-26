# Wyckoff Crypto Radar 1.0

Web app Flask phân tích các cặp Binance Spot USDT theo một số quy tắc heuristic lấy cảm hứng từ Wyckoff. Chạy trên Windows, giao diện responsive và có PWA shell để thêm vào màn hình chính iPhone.

## Chức năng
- Lấy danh sách cặp Spot USDT từ Binance public API.
- Chọn Top 100 theo khối lượng giao dịch 24 giờ tính bằng USDT.
- Quét khung 15m, 1h, 4h, 1d.
- Phát hiện sơ bộ Spring, SOS, LPS, UTAD, SOW, vùng đi ngang và xu hướng.
- Wyckoff Score 0–100 là điểm quy tắc, KHÔNG phải xác suất thắng.
- Hiển thị bảng lọc và biểu đồ nến đơn giản, hỗ trợ màn hình điện thoại.
- Không cần Binance API key; không đặt lệnh mua/bán.

## Yêu cầu
- Windows 10/11
- Python 3.11 hoặc mới hơn
- Internet để gọi Binance API

## Chạy lần đầu
1. Giải nén ZIP vào thư mục dễ tìm, ví dụ `C:\Wyckoff_Crypto_Radar`.
2. Cài Python từ https://www.python.org/downloads/windows/ nếu máy chưa có. Khi cài, tích `Add python.exe to PATH`.
3. Nhấp đúp `run_windows.bat`.
4. Chờ cài thư viện và mở trình duyệt tại `http://127.0.0.1:5000`.
5. Nhấn `Quét thị trường`.

Lần chạy đầu cần Internet để cài Flask/Requests. Những lần sau vẫn cần Internet để lấy dữ liệu thị trường.

## Dùng trên iPhone
PWA cần HTTPS để cài đặt như ứng dụng. `http://127.0.0.1:5000` trên máy Windows không thể dùng làm địa chỉ trên iPhone.
- Cách dễ nhất: triển khai app lên máy chủ có HTTPS (VPS hoặc nền tảng hosting Python), sau đó mở URL HTTPS trên Safari iPhone.
- Trên Safari: Share → Add to Home Screen.
- Chỉ dùng trong mạng LAN là chưa đủ cho PWA cài đặt nếu không có HTTPS; ngoại lệ localhost chỉ áp dụng trên chính thiết bị đó.
- Không mở cổng router ra Internet trực tiếp nếu chưa biết cách bảo mật máy chủ.

## API routes
- `GET /api/health`
- `GET /api/scan?interval=1h`
- `GET /api/chart/BTCUSDT?interval=1h`

## Logic phân tích hiện tại
- Tải 100 nến OHLCV; bỏ nến cuối có thể chưa đóng.
- Dùng vùng giá gần đây và khối lượng trung bình để gắn nhãn sơ bộ.
- Spring: xuyên đáy tham chiếu rồi đóng trở lại trên vùng đáy.
- SOS: đóng vượt đỉnh tham chiếu, volume cao hơn mức nền.
- UTAD/SOW: dấu hiệu phá đỉnh thất bại hoặc phá đáy kèm volume.
- Hỗ trợ/kháng cự lấy từ vùng nến gần đây; mục tiêu 2R chỉ là minh họa toán học.

Đây là bản nền tảng MVP. Các cấu trúc Wyckoff cần xác nhận theo bối cảnh A–E, xu hướng khung lớn và kiểm tra thủ công. Không nên sử dụng như hệ thống tín hiệu giao dịch tự động nếu chưa backtest.

## Khắc phục lỗi
- `ModuleNotFoundError`: chạy lại `run_windows.bat` để cài requirements.
- Lỗi Binance/HTTP 451/403/429: thử lại sau, kiểm tra kết nối hoặc giới hạn truy cập vùng mạng; không spam nút quét.
- Port 5000 bận: đóng app khác dùng port này hoặc đổi `port=5000` ở cuối `app.py`.
- Web chạy nhưng không có coin: kiểm tra Internet, thử khung 1h và xem thông báo trên giao diện.

## Bảo mật
Không có API key hoặc chức năng đặt lệnh. Không nên thêm khóa API giao dịch vào bản này. Nếu triển khai public, cần bổ sung giới hạn truy cập, logging, cache phù hợp và cấu hình máy chủ production (ví dụ Waitress/Gunicorn thay cho Flask dev server).
