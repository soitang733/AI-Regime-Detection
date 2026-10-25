# Sửa bố cục dashboard — 24/10/2026

Phạm vi: kích thước và cách trình bày, theo phản hồi màn hình của người dùng.
Giữ bảng màu be / xanh rêu / vàng đồng; không sửa model, dữ liệu hay kết quả nghiên cứu.

## Thay đổi

- `dashboard/ui.py`: sidebar 248 px, giảm lề nội dung; KPI dùng CSS grid tự đổi 6/3/2 cột
  theo chiều rộng thực tế của vùng nội dung. Bỏ chiều cao cố định, nowrap và ellipsis gây cắt chữ.
  Biểu tượng trợ giúp có không gian riêng. Các cột biểu đồ xếp dọc khi thiếu chỗ.
  KPI gộp trong một dải trắng với vạch phân cách, bỏ viền màu phía trên từng thẻ.
- Bỏ nền nến/lưới trang trí, emoji và chữ in hoa ở tiêu đề nội dung. Giữ nền ấm,
  sidebar xanh rêu, typography phân cấp rõ hơn; bảng sáng có thanh xác suất theo số liệu thật.
- Bảng số liệu có khung cuộn ngang riêng, giữ được toàn bộ K trạng thái trên màn hình nhỏ.
- `dashboard/app.py`: Radar hiển thị bản tóm tắt và bảng xác suất toàn chiều rộng;
  phần giải thích chi tiết và mô hình xu hướng bổ sung nằm trong mục mở rộng.
  Cảnh báo unstable, ngày UTC và xác suất hiện tại/T+1 vẫn được giữ.
- `tests/test_c3_dashboard.py`: đọc từng thẻ KPI từ HTML grid để tiếp tục đối chiếu giá trị
  trực tiếp với B08; không đổi giá trị kỳ vọng.
- `scripts/check_dashboard_layout.py`: kiểm tra trình duyệt thật với BTC/ETH, bốn trang,
  các viewport 1920, 1366, 1280, 1024 và 390 px; đo cắt chữ KPI, tràn ngang và lỗi ứng dụng.

## Bằng chứng

- Bản giao diện mới: 40/40 trường hợp trình duyệt đạt (5 viewport × 2 tài sản × 4 trang).
- 67/67 test dashboard, Radar và nghiên cứu đạt sau thay đổi trình bày cuối cùng.
- Toàn bộ 169/169 test đạt khi chạy một luồng trước bước tinh chỉnh typography/thanh xác suất.
- Manifest core và research vẫn hợp lệ, không có lỗi hash.
- `outputs/metadata/ui_layout_acceptance.json`: kết quả đo từng màn hình/trang/tài sản.
- `outputs/figures/layout_*.png`: ảnh từ dashboard chạy dữ liệu thật.
- `outputs/metadata/ui_pytest.log`: lượt chạy đầu, 168 đạt và một lỗi so sánh chuỗi
  `train_soft_state_shares` với sai khác khoảng 1e-13 giữa hai lần fit.
- `outputs/metadata/ui_pytest_deterministic.log` và XML tương ứng: lượt chạy lại đầy đủ
  với `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`, không sửa bài test đó.

Các báo cáo nghiệm thu Blueprint trước đó ghi nhận UI ở thời điểm trước lần sửa bố cục này.
Hash nguyên bản của `ui.py` vì vậy không còn là điều kiện của lần sửa giao diện hiện tại.
Kiểm tra tính toàn vẹn của core/research vẫn dựa trên manifest của pipeline.

Mở http://127.0.0.1:8501 và tải lại bằng Ctrl+F5 để xem giao diện đang chạy.
Không commit hoặc push.
