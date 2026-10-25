# Đối chiếu trước khi bổ sung Market Regime Radar

Nguồn: `02_crypto_market_regime_detection.md` và `tài liệu team code (2).docx` (quy ước chung,
phạm vi C2, quy tắc nhãn kinh tế và bàn giao C2 → C3).

| Blueprint | Quy định team | Code trước thay đổi | Thiếu hoặc dễ hiểu sai | Cách xử lý |
|---|---|---|---|---|
| Bull/Bear/Calm/Stress | K=2,3,4; nhãn từ train, không ép K=4 | BTC K=3, ETH K=4; Low-Vol/High-Vol/State ID | Người dùng có thể nghĩ thiếu class | Giữ label_map, giải thích nhãn mô tả và chưa chứng minh Bull/Bear/Stress |
| Xác suất từng regime | Filtered, tổng bằng 1, đúng K | CSV đủ K; Overview chỉ nổi bật state thắng và High-Risk | Chưa thấy toàn bộ phân phối | Thêm bảng K state hiện tại và T+1, nguồn metadata + CSV đã xác minh |
| Xác suất chuyển regime | α_t @ P; HMM đồng nhất | C2 lưu P và High-Risk T+1; UI có ma trận tĩnh | Chưa có phân phối T+1 đầy đủ | Nhân vector filtered với transition_matrix; đối chiếu cột High-Risk T+1 có sẵn |
| Drivers | RQ3/NHHMM không bắt buộc; không giả hệ số | Có features mở rộng; chưa hồi quy drivers | Không thể giải thích nhân quả macro | Giải thích ba feature lõi + chain; hiện quan sát và thống kê train, nêu giới hạn |
| Lịch sử xác suất | Filtered mặc định; smoothed hindsight | Có màu giá và chế độ smoothed | Thiếu biểu đồ xác suất chọn từng state | Thêm biểu đồ xác suất theo bộ lọc ngày/giai đoạn và state |
| BTC/ETH comparison | Hai HMM độc lập, ID không tương đương | Có dải lịch sử và bảng HMM/GMM | Thiếu bảng snapshot BTC/ETH | Bảng ngày, K, nhãn, P(state), High-Risk hiện tại/T+1, ổn định |
| Ứng dụng tài chính | Filtered cho t+1, phí giả định, không tune test | Có kiểm as_of, backtest và B08 thật | Không chứng minh chiến lược vượt benchmark | Giữ nguyên strategy/NAV/kết luận và các cảnh báo |
| Thời gian dữ liệu | Nến UTC đã đóng, as_of riêng | Sidebar có ngày dữ liệu | Có thể nhầm forecast với realtime | Nêu ngày nến, as_of UTC, ngày mục tiêu và độ mới rõ ràng |
| Chất lượng mô hình | require_stable và acknowledge_unstable | Reader giữ cả hai cơ chế | Tag nhỏ chưa diễn giải đầy đủ | Cảnh báo unstable có ARI trong Radar, không nới chính sách |

Không sửa C1/C2, cấu hình, artifacts, thuật toán hoặc backtest. Giữ nguyên `ui.py`,
theme, menu và bố cục biểu đồ cũ; chỉ thêm nội dung trong các card hiện có.

Công thức đúng: α_t(k)=P(S_t=k | X_{1:t}); q_{t+1}=α_t P.
q tích phân qua mọi state hiện tại; không chỉ lấy hàng P của state có argmax.
Đây là dự báo state trước khi có quan sát ngày t+1, không phải dự báo giá hoặc
xác suất sinh lời. Persistence p_kk là xác suất ở lại nếu biết S_t=k;
q_{t+1}(k) là xác suất biên và có thể khác p_kk.

K=5 và danh sách thuật toán benchmark là hướng mở rộng; tài liệu team giới hạn
MVP ở HMM/GMM. Điểm theo blueprint rộng không thay thế điểm nghiệm thu MVP.
