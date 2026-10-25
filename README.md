# Crypto Market Regime Radar — V2

Nhận diện trạng thái BTC/ETH theo xác suất bằng Gaussian HMM và NHHMM; đối chứng GMM, K-means, MS-AR, online change-point, HDBSCAN và MS-GARCH. Đây là sản phẩm nghiên cứu theo Research Blueprint 02, không phải dự báo giá hoặc khuyến nghị đầu tư.

Repository chỉ có một dashboard và một bộ kết quả V2 hiện hành. Các module C1/C2/C3 còn được V2 sử dụng là dependency; lịch sử các phiên bản cũ được giữ trong Git.

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

- [Báo cáo nghiên cứu](paper/research_report.md) và [báo cáo rà soát V2](reports/v2_review/BAO_CAO_RASOAT_V2.md).
- T01–T08, F01–F06 cho BTC/ETH: `outputs/research_v2/deliverables/`.
- Chẩn đoán bổ sung: `outputs/research_v2/review/`; báo cáo replay: `outputs/research_v2/reproduction/result.json`.
- Tests/log/XML và nghiệm thu: `outputs/research_v2/acceptance_*`, `technical_acceptance.json`, `ui/acceptance.json`.
- [Protocol rà soát](docs/V2_REVIEW_PROTOCOL.md), [protocol M0](reports/m0_lock/PROTOCOL_V2_M0.md), `outputs/research_v2/confirmation_lock.json`.
