# Crypto Market Regime Radar — V2

Nhận diện trạng thái BTC/ETH theo xác suất bằng Gaussian HMM và NHHMM; đối chứng GMM, K-means, MS-AR, online change-point, HDBSCAN và MS-GARCH. Đây là sản phẩm nghiên cứu theo Research Blueprint 02, không phải dự báo giá hoặc khuyến nghị đầu tư.

Repository chỉ có một dashboard và một bộ kết quả hiện tại. Các module C1/C2/C3 còn được V2 sử dụng là dependency, không phải một bản ứng dụng V1 khác. Lịch sử source V1 nằm trong Git; snapshot nguồn/kết quả trước dọn dẹp nằm ở `refs/archive/*`. Xem [khôi phục lịch sử](docs/V2_HISTORY.md).

Theo lựa chọn của người dùng,28 file tài liệu/công cụ/ZIP cũ và12 thư mục cache được giữ lại; danh sách ở `reports/v2_review/cleanup.json`. Chúng là tài liệu lưu giữ, không phải entrypoint hoặc kết quả hiện hành.

## Chạy local

Môi trường đã nghiệm thu: Python 3.12. Dùng môi trường ảo dùng chung:

```powershell
& "$HOME\.venv\Scripts\Activate.ps1"
python -m pip install -r requirements-dev.txt
python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Mở http://127.0.0.1:8501. Dữ liệu đang khóa đến **23/10/2026 UTC**, không phải realtime. Nếu thiếu artifacts, không tạo dữ liệu giả: phục hồi snapshot Git/gói bàn giao có hash hoặc thực hiện tái tạo theo [runbook](docs/V2_RUNBOOK.md).

## Kiểm chứng và tái lập

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:PYTHONHASHSEED='0'
python scripts/reproduce_v2.py
python -m src.research_v2.review
python -m src.research_v2.rolling_benchmarks
python -m pytest -q -p no:cacheprovider --junitxml=outputs/research_v2/acceptance_pytest_final.xml
python scripts/check_v2_layout.py
python -m src.research_v2.acceptance
```

`reproduce_v2.py` chạy đủ 13 stage trong bản sao tạm, dùng lại checkpoint fit đã đăng ký và tính lại data/inference/evaluation/tables/figures. Script so sánh số liệu với bản khóa, lưu log và xóa bản sao. Đây là technical replay cục bộ, **không phải huấn luyện lại từ đầu hoặc tái lập độc lập**. Không chạy fit trực tiếp lên cohort có confirmation lock. Muốn fresh fit phải tạo một bản nghiên cứu riêng, giữ protocol/input hashes và không sử dụng test để lựa chọn.

## Kết quả và nơi xem

| Câu hỏi | Bằng chứng chính | Giới hạn |
|---|---|---|
| RQ1 — số state | T02: 720 HMM candidates, K2–4 chính/K5 sensitivity, 3 development folds | K được chọn bằng validation, không ép K4 |
| RQ2 — ý nghĩa kinh tế | T03: return, volatility, volume, Amihud; train bootstrap; block14/21/42 | Chỉ gán Bull/Bear/Calm/Stress khi vượt ngưỡng đã khóa |
| RQ3 — chuyển regime | T05: NHHMM thật, 990 candidates, dynamic transitions, beta/seed dispersion, predictive comparisons | Proxy target từ HMM; rất ít Stress entries; macro vintage chưa xác minh |
| RQ4 — ổn định/benchmark | T07/T08: seed, initializer, folds, matched-K/features/dates; 120 fits rolling đối chứng bổ sung | Không so raw LL khác feature space; không mặc định HMM tốt hơn |
| RQ5 — giá trị kinh tế | T06: 4 chiến lược, phí5/10/20bps, 3 execution scenarios, paired bootstrap | Historical exploratory; CI điều kiện theo model/tín hiệu cố định |

- [Báo cáo rà soát và thay đổi](reports/v2_review/BAO_CAO_RASOAT_V2.md).
- T01–T08, F01–F06 cho BTC/ETH: `outputs/research_v2/deliverables/`.
- Chẩn đoán bổ sung: `outputs/research_v2/review/`; báo cáo replay: `outputs/research_v2/reproduction/result.json`.
- Tests/log/XML và nghiệm thu: `outputs/research_v2/acceptance_*`, `technical_acceptance.json`, `ui/acceptance.json`.
- [Protocol rà soát](docs/V2_REVIEW_PROTOCOL.md), [protocol M0](reports/m0_lock/PROTOCOL_V2_M0.md), `confirmation_lock.json`.

## Dashboard

Giao diện dùng phong cách research terminal xanh rêu–kem–vàng đồng. Header và sidebar đồng bộ BTC/ETH; chỉ V2. Overview có Radar, current/T+1, price overlay và giải thích log emission/prior. History có các tab Historical Regimes, Economic Profiles, Transition Analysis và Market Drivers. Comparison trực quan hóa lựa chọn K, matched-sample stability và rolling windows; Portfolio giữ các kết quả sau phí và conditional CI. Cuối mỗi trang có tải T01–T08, F01–F06 và báo cáo. Xem [báo cáo thiết kế và ảnh trước/sau](reports/terminal_design/BAO_CAO_THIET_KE.md).

Market-studio bổ sung ticker/sparkline và họa tiết nến từ OHLC thật, cùng lựa chọn biểu đồ nến. Cảnh báo dài được thu trong “Chất lượng mô hình & phạm vi dữ liệu”; badge UNSTABLE và ngày snapshot vẫn hiện. Phần ĐỌC TÍN HIỆU và các tab nghiên cứu giữ diễn giải RQ1–RQ5, không biến xác suất regime thành dự báo giá.

Dashboard trình bày kết quả trực tiếp tại đúng output: Radar cho current/T+1; Economic Profiles và Drivers cho RQ2/RQ3; Model Selection và Stability cho RQ1/RQ4; Portfolio cho RQ5 theo phí/scenario đang chọn. Kết luận nghiên cứu nằm cạnh bảng/biểu đồ liên quan, không lặp lại thành một banner diễn giải ở đầu trang.

Overview có Radar, toàn bộ K state thật, xác suất filtered hiện tại, T+1, High-Risk, ngày/as-of và giải thích mô hình. Với HMM: `q[t+1] = alpha[t] @ P`; NHHMM: `q[t+1] = alpha[t] @ P(z[t])`, chỉ dùng covariates có sẵn tại t. Forecast là xác suất trạng thái, không phải xác suất giá tăng.

Regime History mặc định filtered; smoothed chỉ để nhìn lại với cảnh báo hindsight. Model Comparison so BTC/ETH theo thống kê/nhãn riêng từng model, không đồng nhất State 0 giữa hai tài sản. Portfolio giữ nguyên kết quả sau phí, gồm cả trường hợp kém benchmark. Model chưa đủ ổn định luôn có cảnh báo; cơ chế `require_stable`/`acknowledge_unstable` được giữ.

Biểu đồ có thanh công cụ Zoom/Pan, nút +/− và đặt lại góc nhìn. Kéo chọn một vùng hoặc cuộn chuột trên vùng vẽ để zoom; nhấp đúp/Reset axes để trở về khung ban đầu. Các nút vẫn hiện trên mobile. Zoom chỉ đổi góc nhìn, không thay khoảng mẫu hoặc tính lại kết quả nghiên cứu.

## Ranh giới nghiệm thu

**Technical PASSED** chỉ nói implementation, schema, thời gian, xác suất, artifact, tests và UI đã qua kiểm tra thực chạy. **Research Confirmation PENDING**: test lịch sử đã được xem; chưa có tái lập bởi team độc lập hoặc prospective sample đủ dài/sự kiện. Không dùng kết quả khám phá để tuyên bố model hữu ích cho giao dịch thật. Team khác viết nội dung học thuật từ các bảng/hình và RQ result cards.
