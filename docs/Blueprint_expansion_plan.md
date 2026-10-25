# Hoàn thiện theo Research Blueprint 02

Được người dùng cho phép chủ động thu thập thêm dữ liệu, bổ sung phân tích và
điều chỉnh khi có lý do kỹ thuật. Không commit/push, giữ phong cách dashboard cũ.

| Khoảng trống | Công việc triển khai | Ranh giới khoa học |
|---|---|---|
| Chỉ đặt tên theo volatility | Nhãn kinh tế dựa trên mean return, volatility và left-tail; moving-block bootstrap train | Không ép đủ 4 tên; giữ ID và nhãn gốc, công bố độ bất định và điều kiện model cố định |
| HMM nhạy với khởi tạo | Thử khởi tạo có cấu trúc K=2..5, nhiều seeds; khóa lựa chọn theo validation | Kết quả mới là nghiên cứu sau khi test cũ đã được quan sát; không xóa baseline |
| Thiếu benchmark clustering | Bổ sung KMeans cùng train/validation/test và đánh giá persistence/ARI | Không so inertia với HMM likelihood hoặc gọi clustering accuracy |
| RQ3 chưa thực hiện | Logistic dự báo proxy chuyển sang High-Risk với dữ liệu as-of; baseline prevalence | Đây không phải NHHMM hoặc bằng chứng nhân quả; tránh leakage nhãn t+1 qua split |
| Dữ liệu mở rộng chậm | Thu thập thêm từ nguồn chính thức, nối lịch sử, ghi log lỗi/coverage/độ trễ | Không ghi đè lịch sử hoặc thay dữ liệu lỗi bằng số giả; không dùng biến stale vô hạn |
| Thiếu volatility targeting | Benchmark quy tắc cố định với cùng ngày/fees/execution, paired block uncertainty | Không chọn threshold trên test; B08/NAV cũ giữ làm baseline |
| Diễn giải và sản phẩm | Hiện nhãn nghiên cứu có provenance, evidence, drivers, heatmap và kết quả mới | Phân biệt model label, diễn giải train và dự báo state; giữ cảnh báo unstable |
| Thiếu bài nghiên cứu | Tạo paper có RQ1..5, phương pháp, bảng thực, kết quả âm và giới hạn | Không báo toàn bộ blueprint là đã chứng minh; thống kê post-hoc ghi rõ |

Đường dẫn làm việc: `local-demo-20261024/AI-Regime-Detection-main`. Bản nền nằm
ở `outputs/archive/pre_blueprint_expansion_20261024.zip`; kiểm toán ban đầu nằm
ở `outputs/metadata/blueprint_baseline_audit.json`. Tách cấu hình nghiên cứu khỏi
config lõi để bảo toàn scaler/split/model đã khóa và so sánh công bằng.
