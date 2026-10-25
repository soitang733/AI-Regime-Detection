# Nghiệm thu AI Market Regime Radar

> Biên bản giai đoạn Radar ban đầu, trước đợt mở rộng Blueprint được người dùng cho phép.
> Số test/hash và trạng thái RQ3 ở đây thuộc lần chạy cũ; xem
> `Blueprint_completion.md`, `project_completion.json` và `research_manifest.json` cho bản mới.

Ngày xác minh: 24/10/2026. Đánh giá trên bản local đang chạy, không phải xác nhận
của bên thứ ba. Không commit hoặc push trong đợt này.

## Đối chiếu đặc tả

Xem [bảng đối chiếu trước sửa](Regime_radar_review.md). Đã đọc Blueprint 02 và
`tài liệu team code (2).docx`, rà soát C2 run/selection/inference/reports/handoff/
stability và C3 app/ui/result_service/backtest/backtest_run.

Blueprint định hướng Bull/Bear/Calm/Stress; team yêu cầu K=2,3,4 và gán nhãn từ
train. Hai yêu cầu không có nghĩa phải xuất bốn class cố định. Giữ model thực tế:
BTC K=3, ETH K=4, label_map Low-Vol/High-Vol/State ID. RQ3, NHHMM, K=5 và
volatility targeting không phải điều kiện bắt buộc của MVP theo tài liệu team.

## Nội dung đã hoàn thiện

- Overview: card AI Market Regime Radar với asset, K, ngày nến, as_of UTC,
  state có xác suất lớn nhất, toàn bộ phân phối hiện tại/T+1 và High-Risk.
- Cảnh báo unstable có Median ARI và giải thích xác suất có điều kiện theo model,
  chưa phản ánh bất định giữa các nghiệm. Khi dữ liệu chậm có cảnh báo riêng.
- Giải thích ba features, quan sát ngày cuối và hồ sơ train, phân biệt mô tả
  thống kê với tác động nhân quả của drivers chưa kiểm định.
- Regime History: thêm đường xác suất cho các state được chọn; tôn trọng bộ lọc
  ngày/giai đoạn và chế độ filtered/smoothed. Bảng thống kê B04/B05 ghi rõ phạm vi
  toàn giai đoạn, không giả là tính lại trên slider ngày.
- BTC/ETH: snapshot, High-Risk hiện tại/T+1, độ ổn định; mở rộng xem thống kê train
  và từng ma trận chuyển. State ID thuộc riêng mỗi tài sản.
- Giữ theme, màu, menu và các biểu đồ cũ; không thay chiến lược/NAV hoặc lựa chọn model.

## Công thức và thời gian

`alpha_t(k) = P(S_t=k | X_1:t)` lấy từ CSV filtered qua reader C2 đã kiểm chứng.
State hiện tại là argmax của vector này. `q_(t+1) = alpha_t @ P`, với P từ
metadata của HMM đã học. Đây là tổng có trọng số qua **mọi** state hiện tại,
không chỉ một hàng của P. Forecast High-Risk được đối chiếu với
`prob_high_risk_next_day` đã xuất bởi C2, sai khác sẽ bị từ chối.

Cả hai cột có tổng bằng 1 trước làm tròn; không thêm state hoặc đặt sàn xác suất.
T+1 là phân phối state trước khi có quan sát ngày kế tiếp, không phải dự báo giá,
xác suất sinh lời hoặc xác suất đã hiệu chuẩn. P là ma trận đồng nhất, không
phụ thuộc macro. p_kk khác xác suất biên q_(t+1)(k).

Dữ liệu thực tại nghiệm thu: nến **23/10/2026 UTC**, có sẵn lúc
**24/10/2026 00:00 UTC**, forecast cho state ngày **24/10/2026 UTC**.
Không gọi đây là báo giá realtime.

## File thay đổi trong đợt Radar

| File | Lý do |
|---|---|
| `dashboard/app.py` | Thêm Radar, lịch sử xác suất, thống kê và so sánh BTC/ETH |
| `dashboard/regime_radar.py` | Chiếu vector T+1, kiểm xác suất, thời gian và metadata; không fit/relabel |
| `tests/test_regime_radar.py` | 17 trường hợp cho hai tài sản, mixture forecast, hindsight, metadata và UI |
| `docs/Regime_radar_review.md` | Bảng đối chiếu hai tài liệu và giải pháp trước sửa |
| `docs/Regime_radar_acceptance.md` | Kết quả và giới hạn của lần nghiệm thu này |
| `README.md` | Cách mở và đọc các phần mới |

Không chỉnh `dashboard/ui.py`, `.streamlit/config.toml`, C1/C2, config backtest,
model artifacts hay dữ liệu nghiên cứu trong đợt Radar. Hash đối chiếu **92 file**
được bảo vệ không có thay đổi; ui.py/theme còn trùng byte với ZIP gốc.

## Bằng chứng thực chạy

Lệnh: `python scripts/verify_c2.py`.

- **127 passed trong 42,57 giây**, không failure/error/skip. Bao gồm 110 test hiện
  có và 17 test Radar; giữ đủ danh tính 47/55 trường hợp lịch sử.
- Kiểm trực tiếp metadata/likelihood/artifacts bằng thư viện, dependency lock,
  pip check và kiểm đầu vào không đổi trong lúc nghiệm thu: passed.
- Chrome thực: BTC/ETH × Overview, Regime History, Model Comparison,
  Portfolio & Risk = **8/8** trang, không exception; đã chụp ảnh.
- Tổng xác suất hiện tại và T+1 của cả hai tài sản bằng 1; số dòng và nhãn trùng K
  và metadata; kiểm prefix filtering với model cố định vẫn đạt.
- Snapshot từ chối smoothed/hindsight, sai transition, thiếu state và forecast
  không khớp C2. Reader require_stable/acknowledge_unstable không bị thay đổi.
- B08/NAV/backtest source giữ nguyên hash, không tune trên test.

Evidence: `outputs/metadata/pytest_verification.log`, `pytest_verification.xml`,
`C2_verification.json`, `radar_full_verification.log`, `radar_browser_check.json`,
`radar_scope_before.json`, `radar_acceptance.json`.
Ảnh: `outputs/figures/radar_{btc,eth}_page{1,2,3,4}.png`.

## Cách xem và hạn chế

Mở **http://localhost:8501**, Ctrl+F5 nếu trình duyệt còn cache. Overview →
AI Market Regime Radar; mở mục giải thích để xem công thức và thống kê train.
Regime History → chọn state trên biểu đồ xác suất; Model Comparison → bảng
BTC/ETH và mục mở rộng thống kê/ma trận chuyển. Portfolio giữ kết quả nghiên cứu.

HMM vẫn unstable: Median ARI validation BTC khoảng -0,035, ETH khoảng 0,026.
ETH High-Vol chỉ có 2/637 ngày test; một state ETH khác không có hard occupancy
trên test. Bằng chứng về stress hiếm còn yếu. Chưa chứng minh nhãn Bull/Bear,
chưa có kiểm định drivers, khoảng tin cậy hay calibration xác suất. Tập test đã
được quan sát, không phải một holdout mới. Kết quả regime-aware chưa chứng minh
lợi thế so với buy-and-hold; phí/execution vẫn là giả định nghiên cứu đã công bố.
