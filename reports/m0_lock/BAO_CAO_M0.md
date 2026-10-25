# M0 — bổ sung nghiệm thu và khóa baseline/protocol

**Phạm vi kế hoạch đã được người dùng đồng ý; bốn điều kiện nghiệm thu được bổ sung trong PROTOCOL_V2_M0.md. M0 đã thực hiện; chưa sửa source hoặc chạy M1.**

## Bốn điều kiện đã bổ sung

1. **Ngưỡng định lượng:** xác suất, prefix/save-load, metadata, data timing, hội tụ, occupancy, stability, nhãn kinh tế, test và 48 tổ hợp UI. Phân biệt gate kỹ thuật bắt buộc với tiêu chuẩn để được phát biểu model ổn định/có ích.
2. **NHHMM:** có số liệu train về transitions, coverage và số tham số; GO có điều kiện cho pilot, chưa xác nhận khả thi đầy đủ. Có simulation gate, grid pilot, kiểm coverage/rank/regularization, giới hạn diễn giải beta và điều kiện dừng.
3. **Benchmark:** GMM/K-means → MS-AR → online change-point → HDBSCAN → MS-GARCH. Không bỏ benchmark cuối; các specification chưa kiểm phải khóa bằng phụ lục trước khi code nhánh đó.
4. **Hai tầng nghiệm thu:** technical acceptance riêng; independent replication và prospective confirmation riêng. Không gọi pytest do người triển khai chạy là xác nhận nghiên cứu độc lập.

## Kết quả thực tế của M0

| Kiểm tra | Kết quả |
|---|---|
| Snapshot | 357 file, 56.277.208 byte trước nén; ZIP 29.007.443 byte |
| Phục hồi ở mức file | CRC và SHA-256 của toàn bộ 357 thành viên ZIP khớp manifest |
| Dữ liệu baseline | BTC/ETH đến 23/10/2026; mỗi tài sản train/validation/historical test =1.891/630/637 |
| Filtered probabilities đã đọc | Finite; max sai số tổng =8,88e-16 ở cả hai tài sản; không trùng asset/date |
| NHHMM readiness | Có điều kiện; mới kiểm train baseline, chưa fit NHHMM hoặc kiểm simulation |
| Test evidence trước M0 | Log `reports/blueprint_research_review_20261024/pytest.log`: 169 passed, 72,14s; không chạy lại pytest trong M0 chỉ thêm tài liệu |
| Phạm vi thay đổi | Chỉ tạo `reports/m0_lock/`; không đổi runtime config, source, dữ liệu, model, UI hoặc paper |
| Kiểm tra cuối | `lock_manifest.json` ghi kết quả kiểm lại tất cả file baseline và hash hồ sơ đã khóa |

NHHMM: BTC có 19/39/25 lần rời các state trên train; ETH 11/7/15/11. VIX/DXY có raw coverage đủ nhưng funding/OI không đầy đủ, đặc biệt OI ETH chỉ 27,18% train. Số đếm là hard filtered path, không phải latent truth. Chưa chứng minh point-in-time của toàn bộ covariates; M1 xử lý audit đó.

## Cách đọc và sử dụng hồ sơ

- `KE_HOACH_V1_1_KEM_PROTOCOL.md`: bản đọc liền mạch, giữ nội dung phạm vi gốc và bổ sung protocol đã khóa.
- `PROTOCOL_V2_M0.md`: ngưỡng, selection, feasibility, priorities và acceptance gates.
- `baseline_manifest.json` và `baseline.zip`: baseline có full SHA-256; giải nén vào thư mục mới khi cần đối chiếu, không ghi đè project đang làm.
- `feasibility_evidence.json`: ma trận chuyển train, coverage và các phép kiểm xác suất thực chạy.
- `environment.json`: Python/package versions dùng cho audit.
- `lock_manifest.json`: thời điểm khóa, hashes, quyền chuyển milestone và giới hạn của M0.

Bản kế hoạch v1.0 gốc giữ nguyên trạng thái lịch sử “chờ duyệt” để bảo toàn snapshot; trạng thái hiện hành là **scope approved + M0 locked**, được ghi ở bản v1.1 và lock manifest. Không chỉnh sửa v1.0 để giả tạo lịch sử duyệt.

## Những gì chưa được xác nhận

M0 chưa chứng nhận toàn bộ project đạt Blueprint, NHHMM hội tụ, benchmark đầy đủ, model ổn định, chiến lược có lợi nhuận vượt trội, hoặc dữ liệu macro là historical release vintage. Chưa có full clean-room rebuild, external replication hay prospective holdout đủ dài. Các việc này có milestone và gate tương ứng; không tự đánh dấu pass.

Sau khi khóa M0, bước triển khai tiếp theo là M1: data/availability audit và bổ sung nguồn trong phạm vi đã duyệt. Các thay đổi source phải theo protocol và lưu provenance. Nếu cần đổi scope hoặc làm mất tính hợp lệ confirmation, phải nêu amendment và xin duyệt thay đổi scope trước.
