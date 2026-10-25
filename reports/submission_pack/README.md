# Kiểm kê và bàn giao bộ B/H V2

| Hạng mục | Trạng thái trước | Xử lý |
| --- | --- | --- |
| B01 thống kê mô tả | Đã có, đủ SD/kurtosis và split | Giữ nguyên |
| B02 thông tin mẫu | Đã có nguồn, gap và train/validation/test | Giữ nguyên |
| B03–B05 | Chỉ có output C2 cũ hoặc T02–T04 V2 | Xuất bản chuẩn V2, không fit lại |
| B06 drivers | Có T05 NHHMM nhưng Stress events dưới ngưỡng | Không xuất B06; không tạo SE/p-value giả |
| B07 HMM vs GMM | T07/T08 phân tán ở nhiều bảng | Tổng hợp cùng K/features/sample, thêm flips/stability/OOS LL |
| B08 portfolio | T06 có nhiều phí/scenario | Xuất baseline close-to-close 10 bps |
| H01 | Đã có | Giữ nguyên |
| H02–H05 | Đã có F01/F02/F04/F05 | Ánh xạ/copy nguyên ảnh V2 |
| H06 | Có ảnh nghiệm thu Streamlit thật | Dùng ảnh 1440 px đã nghiệm thu |
| Dashboard | Bốn trang đã hoạt động, đọc artifact V2 | Giữ kiến trúc; thêm tải bảng B đã hash-verify |

`scripts/build_submission_pack.py` tái tạo bộ này từ artifact V2 đã khóa và không gọi hàm fit. Manifest SHA-256 nằm tại `outputs/metadata/submission_pack_manifest.json`.

Hạn chế chưa giải quyết: HMM vẫn unstable; không đủ bằng chứng Bull/Bear; NHHMM chưa vượt HMM ngoài mẫu; chỉ hai Stress-entry proxy events trên historical test mỗi tài sản; Research Confirmation vẫn PENDING.
