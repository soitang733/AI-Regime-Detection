# Bàn giao bản mở rộng theo Research Blueprint 02

> Cập nhật UI sau nghiệm thu: người dùng yêu cầu sửa kích thước và làm gọn giao diện.
> Xem [Dashboard_layout_fix.md](Dashboard_layout_fix.md); các nhận xét giữ nguyên UI bên dưới mô tả thời điểm trước lần sửa này.

Ngày: **24/10/2026**. Thư mục làm việc:
`D:\AI-Regime-Detection-main\local-demo-20261024\AI-Regime-Detection-main`.
Không commit/push. Giữ nguyên theme, màu và kiểu giao diện đã được khôi phục.

## 1. Kết quả chính

Đã bổ sung dữ liệu, phương pháp và phân tích thực chạy, không chỉ đổi tên trên UI.
HMM lõi được giữ làm baseline; các mô hình mới là nghiên cứu bổ sung có provenance
và được ghi rõ, không tự thay tín hiệu B08 hoặc che cảnh báo unstable của mô hình cũ.

| Câu hỏi Blueprint | Phần đã thực hiện | Kết luận và giới hạn |
|---|---|---|
| RQ1: số state hợp lý | Core K=2,3,4; thêm HMM khởi tạo có cấu trúc K=2..5, 5 seeds; thêm họ HMM có xu hướng | Chọn bằng train/validation trong từng họ; không ép đủ bốn nhãn |
| RQ2: khác biệt return/vol/liquidity | Mean/vol, left-tail, Amihud và block bootstrap train; độ nhạy block 14/21/42 | Có bằng chứng cho một số nhãn kinh tế; đây là mô tả có điều kiện theo model, không phải ground truth |
| RQ3: macro/crypto dự báo stress? | Logistic regularized, nguồn as-of, baseline prevalence, Brier/log-loss/PR-AUC, B06 thật | Test chỉ có 2 sự kiện chuyển mỗi tài sản; chưa chứng minh macro cải thiện ổn định; không phải NHHMM hoặc quan hệ nhân quả |
| RQ4: ổn định hơn clustering? | Core HMM/GMM, KMeans, HMM có cấu trúc và GMM cùng K; RV sensitivity | Khởi tạo có cấu trúc cho độ ổn định nội nhóm tốt hơn; chưa chứng minh ổn định toàn cục |
| RQ5: ích lợi quản trị rủi ro? | B&H, regime-aware, volatility targeting và kết hợp; paired block uncertainty; thêm đánh giá HMM xu hướng | Có giảm drawdown trong một số trường hợp; Sharpe/lợi nhuận không vượt trội nhất quán |

Tài liệu team giới hạn MVP ở HMM/GMM; người dùng đã cho phép mở rộng bám Blueprint.
NHHMM, Markov-switching AR/GARCH, HDBSCAN, Bayesian change-point và RL **chưa triển khai**.
Không trình bày logistic proxy như NHHMM hoặc nói đã so sánh các thuật toán chưa chạy.

## 2. Bull / Bear / Calm / Stress thực sự có gì?

Nhãn không được ép theo ví dụ của Blueprint. Điều kiện gán nhãn được ghi trong
`config/research.yaml`: moving-block bootstrap train 1.000 lần; CI mean, tỷ lệ vol
và left-tail có điều chỉnh nhiều so sánh; tối thiểu 100 weighted effective days.
Các ngưỡng là quy ước nghiên cứu được công bố, không phải định nghĩa phổ quát.

| Họ mô hình | BTC | ETH |
|---|---|---|
| HMM lõi + diễn giải train | K=3: Stress, State 1, Calm | K=4: State 0, Calm, Stress, State 3 |
| HMM bổ sung momentum 7/30 ngày | K=4: Bull, Stress, Calm, State 3 | K=5: Calm, State 1, Bull, State 3, High-Vol |

**Chưa có Bear đủ điều kiện**: CI mean của các state return âm còn đi qua 0.
ETH state High-Vol trong họ xu hướng có quá ít weighted days và CI rộng, nên
không đổi thành Stress. Không tạo thêm state hoặc đổi tên để khớp bốn ô giao diện.
Các nhãn trên ổn định qua độ dài block 14/21/42 trong lần chạy này; điều đó không
bao gồm toàn bộ bất định refit, khởi tạo hoặc thay đổi mẫu.

Ví dụ train của họ xu hướng: Bull BTC có mean log return/ngày khoảng **0,743%**,
CI đồng thời khoảng **[0,388%; 1,108%]**; Bull ETH khoảng **0,814%**, CI
**[0,107%; 1,462%]**. Đây là return đồng thời trong state được nhận diện trên train,
**không phải dự báo return ngày mai** hoặc bằng chứng có chiến lược sinh lời.

Dashboard giữ cột nhãn model/State ID và thêm diễn giải kinh tế từ train. Hai họ
mô hình có thể nhận diện trạng thái khác nhau ở cùng ngày; không có nhãn oracle.

## 3. Dữ liệu đã chủ động lấy thêm

- BTC/ETH, SOL/BNB, funding/OI, DefiLlama, CoinGecko: đã có dữ liệu đến **23/10/2026**.
- VIX/SPX/DXY: đến **23/10/2026**; Treasury 10Y/2Y/3M: đến **22/10/2026** theo nguồn FRED.
- Bổ sung lịch sử market cap Coin Metrics: BTC **5.942 ngày**, ETH **4.095 ngày**,
  đến **23/10/2026**, bằng archive công khai kết hợp Community API incremental.
- Market cap Coin Metrics current-supply được lưu riêng với CoinGecko vì khác định nghĩa.
  Giả định availability ngày +2, có ngày quan sát và thời điểm có sẵn.
- CMC200 không tải được từ Yahoo: giữ trạng thái thiếu, không tạo một chỉ số giả thay thế.
- Refresh giữ lịch sử cache, chỉ thêm khóa mới; lỗi từng nguồn được ghi trong manifest.
  Drivers loại giá trị macro quá cũ hơn 7 ngày thay vì carry vô hạn.

Lịch sử tải lại vẫn là current-vintage, chưa phải cơ sở dữ liệu vintage theo ngày
công bố. Độ trễ bảo thủ không loại hết revision bias. Chi tiết nguồn/range/count
nằm trong `source_log.csv`, `external_refresh_manifest.json`, `coinmetrics_refresh.json`
và `blueprint_final_acceptance.json`.

## 4. Mô hình và kết quả không bị làm đẹp

Core BTC K=3 có Median ARI validation khoảng **-0,035**; ETH K=4 khoảng **0,026**,
vẫn được cảnh báo unstable. Cơ chế require_stable/acknowledge_unstable giữ nguyên.

HMM khởi tạo có cấu trúc chọn K=5 cho cả hai tài sản; validation log-score BTC
**-2,37965**, ETH **-2,18197**. Median/min ARI = **1/1 trong họ khởi tạo được chọn**.
Khởi tạo có cấu trúc tập trung vào một vùng nghiệm; không được suy ra ổn định
toàn cục từ con số này. EM vẫn học ma trận chuyển, 95% chỉ là giá trị ban đầu.

Họ xu hướng thêm trailing momentum 7/30 ngày, scaler riêng trên train, loại warm-up;
BTC chọn K=4, ETH K=5. Chỉ so LL với GMM cùng 5 features, không xếp mức LL 5 chiều
với core 3 chiều. Overlap momentum/RV làm giả định độc lập có điều kiện chỉ là xấp xỉ.

Regime-aware lõi trên test giữ nguyên NAV BTC **0,7255** so với B&H **0,7734**;
không chỉnh threshold/tỷ trọng trên test. Volatility targeting cố định 40%/năm
giảm MDD ETH từ **-67,55%** xuống khoảng **-57,01%**, nhưng Sharpe từ **0,0698**
xuống khoảng **-0,0176**. Bootstrap chênh lệch Sharpe còn đi qua 0. Phần giảm MDD
là bằng chứng quản trị exposure trong thí nghiệm, chưa phải alpha triển khai thực tế.

HMM xu hướng cũng không được ưu ái: regime-aware BTC có NAV khoảng **0,7182**, thấp
hơn B&H; ETH gần như B&H vì tín hiệu rủi ro ít hoạt động. Kết quả bất lợi vẫn nằm
trong bảng, paper và UI. Toàn bộ mở rộng là exploratory vì test cũ đã được quan sát.

## 5. Dashboard và khả năng giải thích

- Overview có Radar lõi và Radar xu hướng được phân biệt rõ; đủ K xác suất hiện tại/T+1,
  ngày nến/as_of UTC, High-Risk, nhãn train và chất lượng model.
- Current = filtered alpha_t; next-day = alpha_t @ P, đối chiếu High-Risk T+1 với CSV C2.
- Giải thích phép tính bằng từng log emission Gaussian của ba features và filtered prior;
  chuẩn hóa tái tạo đúng vector đã xuất. Không gọi đây là tác động nhân quả/SHAP.
- Regime History có chọn state, filtered mặc định, cảnh báo smoothed hindsight, heatmap
  và thống kê đúng khoảng ngày/chế độ đang chọn. P/persistence train giữ cố định và ghi rõ.
- Model Comparison có HMM/GMM/KMeans, seed stability và RQ3 thật với cảnh báo hiếm sự kiện.
- Portfolio giữ B08 gốc, thêm benchmark/CI và ba kịch bản execution cho volatility targeting.

## 6. Kiểm thử và kiểm toán thực chạy

**169/169 test đạt, 0 lỗi, 0 skip, 143,81 giây**. Nguồn/đầu vào không thay đổi trong
lúc nghiệm thu cuối. Giữ đủ danh tính 47/55 trường hợp lịch sử. Điều chỉnh test B06
từ giả định chưa triển khai thành kiểm hệ số thực, train-only và không p-value giả.

Quét **70 file Python** bằng AST và kiểm tra runtime tĩnh E9/F: **0 phát hiện**;
lint các module mới/sửa chuyên biệt đã đạt. Kiểm trực tiếp metadata, probability,
likelihood, dependency lock và pip check qua `scripts/verify_c2.py` đã đạt.

Chrome thật: **8/8 tổ hợp BTC/ETH × bốn trang**, không exception; 16 ảnh kiểm tra panel.
Đã xuất thêm bộ H06 hiện tại. Prefix core/trend, scaler train-only, dự báo đủ K,
ngăn future publications, xử lý stale, bảo toàn B08 và từ chối metadata cũ đều có test.

Hash toàn bộ source C2 lõi không thay đổi. Theme/ui.py trùng bản đã khôi phục.
So sánh độc lập B08 với archive trước mở rộng: **sai khác lớn nhất của các chỉ số
tài chính = 0**. Có bổ sung kiểm tra input backtest (NaN fees/initial weight,
threshold không hợp lệ, simple return bất khả thi), không thay công thức baseline.

| Bằng chứng | Đường dẫn |
|---|---|
| Kết quả chạy từng bước | `outputs/metadata/project_completion.json`, `project_*.log` |
| Pytest/JUnit/audit thư viện | `C2_verification.json`, `pytest_verification.log`, `pytest_verification.xml` |
| Hash inputs/source/outputs nghiên cứu | `outputs/metadata/research_manifest.json` |
| Kiểm toán cuối, danh sách thay đổi/range nguồn | `outputs/metadata/blueprint_final_acceptance.json` |
| Browser và ảnh panel | `blueprint_browser_check.json`, `outputs/figures/blueprint_*.png` |
| H06 bài nghiên cứu | `H06_capture.json`, `outputs/figures/H06_dashboard*.png` |
| Báo cáo nghiên cứu | `paper/research_report.md` |
| Bản nền có thể phục hồi | `outputs/archive/pre_blueprint_expansion_20261024.zip` |

## 7. File và cách chạy

Nhóm source mới: `src/research/` (economics, robustness, trend, drivers, portfolio,
runner), `src/data/refresh_extensions.py`, `src/data/coinmetrics_collector.py`,
`dashboard/research_views.py`, `scripts/complete_research.py`, `config/research.yaml`
và `tests/test_blueprint_research.py`. Các phần sửa: C1 extended/dictionary/provenance,
validation C3 backtest, dashboard service/analytics/app, hướng dẫn/CI/daily scripts.
Danh sách từng file có trong kiểm toán cuối; dữ liệu/artifact sinh ra tách khỏi source.

Mở **http://localhost:8501**, Ctrl+F5 nếu còn cache. Chạy lại toàn bộ từ thư mục dự án
trong Python 3.12 đã cài `requirements-dev.txt`:

```powershell
python scripts/complete_research.py --download --rebuild-core
python -m streamlit run dashboard/app.py
```

Không có mạng: bỏ `--download`. Chỉ tính lại nghiên cứu/diagnostics/test từ baseline
đã có: `python scripts/complete_research.py`. GitHub workflow đã được cấu hình nhưng
**chưa chạy trên GitHub**, vì đợt này không commit hoặc push.

Lưu ý cuối: kiểm thử đạt không chứng minh mô hình dự báo tốt; chưa có holdout mới,
calibration độc lập, nhân quả macro, execution thực tế hoặc lợi thế đầu tư được xác nhận.
