# Chạy và kiểm chứng Research V2

## Phạm vi và nơi xem

Dashboard chỉ hiển thị bộ kết quả nghiên cứu hiện tại trên cả bốn trang, không có bộ chọn phiên hay giao diện Baseline cũ. Sidebar ghi đúng K của tài sản đang chọn và thời điểm xuất kết quả; không hứa tự động cập nhật mỗi ngày. Nhãn kinh tế không bị ép đủ Bull/Bear/Calm/Stress. Model unstable luôn có cảnh báo; không được hiểu xác suất model là accuracy đã hiệu chuẩn. Artifacts của mô hình đối chứng và dữ liệu gốc vẫn phục vụ kiểm chứng nghiên cứu, không tạo thêm một giao diện cũ trên web.

Source nghiên cứu nằm trong `src/research_v2/`, `outputs/research_v2/`; trang V2 dùng `dashboard/v2_pages.py` và lớp đọc xác minh `dashboard/v2_service.py`. Không ghi nội dung vào `paper/`.

## Môi trường và chạy lại

Trong thư mục project, dùng PowerShell:

```powershell
& "$HOME\.venv\Scripts\Activate.ps1"
python -m pip install -r requirements-v2.txt
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:PYTHONHASHSEED='0'
python scripts/reproduce_v2.py
python -m pytest -q --junitxml=outputs/research_v2/recheck.xml
python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Mở http://127.0.0.1:8501. Không khởi động thêm server nếu port8501 đang được dùng bởi dashboard hiện tại.

`reproduce_v2.py` tạo bản sao tạm, chạy đủ 13 stage, lưu log và so sánh các CSV số liệu trước khi xóa bản sao. Mặc định dùng lại checkpoint fit đã khóa, tính lại data/inference/evaluation/export; không gọi đó là fresh fit. Runner stage `scripts/run_research_v2.py --stage all` hoặc từng stage chỉ dùng trong bản nghiên cứu riêng chưa có confirmation lock; runner từ chối ghi vào cohort đang khóa. Grid HMM/NHHMM dùng checkpoint; không sửa dữ liệu/code rồi dùng lại checkpoint cũ. Input lock yêu cầu một version mới khi đầu vào thay đổi. Batch đầu tiên có lock ghi sau khi chạy, được ghi rõ trong lock, không giả là preregistration trước fit.

Sau khi có `outputs/research_v2/confirmation_lock.json`, chạy tái lập/rebuild trong một bản sao riêng. Thay đổi model/strategy/data rules trong cohort gốc sẽ làm sai hash khóa và cần amendment cùng cohort mới; không tiếp tục gọi dữ liệu đó là prospective confirmation của model cũ.

NHHMM có thể chia4 worker bằng `python -m src.research_v2.nhhmm_run --shards 4 --shard N` với N=0,1,2,3; chỉ đánh giá sau khi đủ990 candidate và có manifest `grid_complete`. Mỗi worker ghi tập candidate riêng; không chạy hai worker cùng shard. Simulation phải pass và hash implementation phải khớp trước real-data fitting.

## Output và giới hạn

- `m1/`: feature matrices, availability/coverage, eligibility và volume drift.
- `m2/`:720 HMM candidates, lựa chọnK, pooled/within-initializer stability, models và probabilities.
- `m2_profiles/`: return/volatility/volume/liquidity profiles, conditional contrasts, block sensitivity và occupancy.
- `m3_simulation/`:20 synthetic recovery runs; không phải chứng nhận dữ liệu thật.
- `m3/`, `m3_evaluation/`:990 NHHMM candidates, failures, coefficients, conditional transitions, filtered/smoothed và predictive comparisons.
- `m4/`, `m4_msgarch/`, `m4_evaluation/`: benchmark development selection và historical OOS diagnostics.
- `m5/`: fixed strategies, fees5/10/20bps, execution scenarios, NAV và uncertainty so volatility targeting.
- `deliverables/`: T01–T08/F01–F06 và RQ result cards cho team viết paper.
- `ui/`: browser acceptance/screenshot; pytest log/XML nằm ở root outputs V2.

Các CI của state profiles điều kiện theo model đã fit, không phản ánh đầy đủ bất định lựa chọn model. NHHMM coefficient event-count screen không phải p-value. Next-state target dùng HMM proxy, không có latent ground truth. MS-GARCH ở đây có recursion variance song song theo observed lagged return; không gọi là mô hình variance phụ thuộc toàn bộ hidden path. HDBSCAN out-of-sample dùng adapter medoid/radius cố định, không giả là native predictive posterior. Change-point là segmentation causal, không phải recurrent regimes hay Bayesian HMM.

Test lịch sử đã được xem. Chưa có prospective confirmation hay tái lập bởi team độc lập. Kết quả không vượt benchmark vẫn được bàn giao. Việc cập nhật nguồn lịch sử không chứng minh dữ liệu macro là historical-release vintage.
