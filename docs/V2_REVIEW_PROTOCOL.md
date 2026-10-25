# Protocol rà soát V2 — 25/10/2026

Phạm vi được người dùng yêu cầu: repository V2 duy nhất; RQ1–RQ5; dashboard giữ phong cách; chạy pipeline, tests và desktop/mobile. Đây là amendment chẩn đoán, không mở grid hoặc thay champion. Protocol M0, confirmation lock và kết quả nghiên cứu trước lượt rà soát được giữ nguyên.

## Quy tắc trước khi chạy

- Ghi SHA-256 của đầu vào và bản kết quả cũ trước tính toán. Không thay source thuật toán, scaler, imputer, labels, model, split hoặc strategy đang khóa.
- NHHMM: kiểm probability/prefix/save-load, objective/optimizer, missingness và covariate shift, state alignment từ train, log score quan sát và proxy-state loss riêng, calibration/số Stress entries theo split. Các phép tính trên test chỉ mô tả kết quả lịch sử đã biết; không chọn model mới từ đó.
- Stability: giữ tất cả failure; phân biệt seed, initializer và rolling-origin development folds. So GMM/K-means cùng K, scaler, feature và ngày validation. Bổ sung đúng 120 fits GMM/K-means cho hai fold development đầu: BTC/ETH × fold0/1 × K2/3/4 × seed0–4 × hai phương pháp, dùng nguyên hyperparameters M4 (GMM diag/n_init1/max_iter500/tol0,001/reg_covar1e-6; K-means n_init10). Ghi registry và hash trước fit; không mở test, không thay champion. Fold2 dùng kết quả M4 đã khóa. MS-AR/MS-GARCH return-only không xếp chung raw likelihood với feature 3 chiều. Không biến ARI thành accuracy.
- Economic meaning: giữ nguyên ngưỡng M0, train-only, bootstrap/block sensitivity và nhãn đã khóa. Bổ sung bảng tổng hợp return/volatility/liquidity, không ép bốn nhãn.
- Portfolio: chiến lược/phí/execution giữ nguyên. Bổ sung CI tuyệt đối Sharpe, drawdown, turnover và chênh lệch với cả B&H/vol-target bằng paired moving blocks (1.000 lần; 14/21/42 ngày; Holm theo asset × strategy × reference cho từng metric/block). Không chọn chiến lược từ CI.
- Tái lập toàn pipeline trong thư mục tạm riêng; checkpoint đã khóa được phép dùng và phải ghi rõ stage nào dùng lại fit. Đối chiếu kết quả số, không coi timestamp/joblib bytes mới là model mới hoặc tái lập độc lập. Không ghi đè cohort đang khóa.
- Git giữ lịch sử V1 và snapshot nguồn/kết quả trước khi dọn bản trùng. Không tạo commit/push mới. Git archive refs giữ snapshot có thể phục hồi; cache không cần lưu. ZIP xuất giao hàng không nằm bên trong repository; snapshot M0 chuyển vào Git object có SHA-256 và hướng dẫn phục hồi.

## Nghiệm thu

Giữ ngưỡng M0: tổng xác suất ≤1e-8; prefix/save-load ≤1e-10; median/min ARI ≥0,80/0,50 và ít nhất hai họ khởi tạo hợp lệ cho pooled claim. Không nới gate để làm đẹp kết quả. Zero test failures/errors/skips; 48 trường hợp UI. T01–T08/F01–F06 và RQ cards có hash, bổ sung diagnostics được chỉ mục riêng. Technical PASSED chỉ khi các kiểm tra thực chạy đạt; Research Confirmation vẫn PENDING, chưa có external replication/prospective sample đủ dài.
