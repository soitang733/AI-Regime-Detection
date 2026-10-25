# Phụ lục nghiệm thu và protocol V2 — khóa tại M0

Phụ lục này bổ sung kế hoạch `reports/blueprint_final_plan/KE_HOACH_FINAL_CHO_DUYET.md` đã được người dùng đồng ý về phạm vi. Bản kế hoạch gốc được giữ nguyên trong baseline để bảo toàn lịch sử duyệt. Khi có khác biệt về nghiệm thu, áp dụng phụ lục này. Phạm vi M0 hiện tại chỉ gồm snapshot, kiểm tra chỉ đọc, protocol và hồ sơ; chưa triển khai M1–M7.

Không thêm O1–O4, không commit/push/deploy, không viết paper thay team khác. Không tự bỏ benchmark hoặc thay NHHMM bằng logistic. Không đổi source, runtime config, dữ liệu hay model trong M0.

## 1. Baseline và ranh giới bằng chứng

Baseline là source/config/data/artifacts thực tế tại thời điểm ghi `baseline_manifest.json`, không phải một bản phát hành cũ. `baseline.zip` chứa 357 file; từng thành viên được kiểm CRC và full SHA-256, đối chiếu lại với file gốc. Danh mục, kích thước, hash và các loại file loại trừ có trong manifest. Đây là snapshot phục hồi; chưa có bằng chứng chạy toàn bộ pipeline từ bản giải nén trên một máy độc lập.

Hai tài sản có 1.891 ngày train (02/03/2018–05/05/2023), 630 ngày validation (06/05/2023–24/01/2025), 637 ngày historical test (25/01/2025–23/10/2026). Giữ nguyên split baseline. Test này đã được quan sát, vì vậy mọi thay đổi tiếp theo được đánh giá trên đó phải mang nhãn **historical exploratory**, không phải untouched confirmation.

Các ngưỡng dưới đây là quy tắc vận hành được khai báo trước các thí nghiệm V2, không phải định luật thống kê hay kết quả đã đạt. Chúng không làm biến mất việc người thực hiện đã biết kết quả baseline. Không chỉnh ngưỡng sau khi xem kết quả để đổi fail thành pass.

## 2. Điều kiện bổ sung số 1 — ngưỡng định lượng

| Hạng mục | Ngưỡng và cách nghiệm thu | Khi không đạt |
|---|---|---|
| Baseline/provenance | 100% file trong manifest khớp full SHA-256; 0 thay đổi source/config/data/model trong M0 | Không mở triển khai |
| Dữ liệu | 0 khóa asset/date trùng; 0 timestamp không hợp lệ; 0 quan sát có availability sau decision time được đưa vào feature | Chặn pipeline liên quan; không forward-fill xuyên tương lai |
| Probabilities/transition | Finite; trong [0,1] với sai số số học tối đa 1e-10; sai số tổng mỗi vector/hàng ≤1e-8 | Fail kỹ thuật, không chỉ warning |
| Prefix và save/load | Max absolute difference ≤1e-10 với model cố định và float64; so cả vector filtered trước/sau nối tương lai và trước/sau serialization | Fail kỹ thuật |
| Metadata | 100% K, state IDs, labels, high-risk ID, run ID, ngày/as-of khớp model/CSV/manifest; số trạng thái hiển thị đúng K | Fail tích hợp |
| HMM fit | 5 seed [0,1,2,3,4]; tối đa 500 EM iterations; chênh LL cuối nằm [-1e-6, 1e-3]; covariance floor 1e-6; mỗi state có train hard occupancy ≥2% | Loại candidate, lưu failure; không lấy max-iter làm hội tụ |
| Stability HMM | Ít nhất 3 fit hợp lệ; validation median pairwise ARI ≥0,80 và minimum ARI ≥0,50 | Gắn unstable; không tuyên bố ổn định |
| Risk probability robustness | Báo cáo MAE, disagreement và Jaccard; chỉ gọi ổn định tín hiệu nếu MAE ≤0,05 và disagreement ở ngưỡng 0,5 ≤5% | Không đánh đồng ARI cao/thấp với ổn định tín hiệu rủi ro |
| State/nhãn kinh tế | Train-only; weighted ESS ≥100; moving-block bootstrap 1.000 lần, block 21 ngày, sensitivity 14/42; CI 95% có điều chỉnh nhiều phép thử theo quy tắc economics hiện có | Giữ nhãn trung tính; ESS không được gọi là số ngày độc lập |
| Bull/Bear | CI mean return hoàn toàn trên +0,0005/ngày hoặc dưới -0,0005/ngày | Không ép có Bull/Bear |
| Calm/Stress | Calm: CI trên của vol ratio <0,85 và abs(mean)<0,15×vol; Stress: CI dưới của vol ratio >1,25 và CI dưới của tail contrast >0 | Giữ canonical label; không đồng nhất High-Vol với Stress nếu thiếu bằng chứng |
| Benchmark | Cùng asset, sample giao nhau, feature space ở từng phép so; 5 seed cho phương pháp stochastic; báo cáo cả failures | Không so raw likelihood giữa feature spaces khác nhau; không tạo likelihood/probability giả cho clustering |
| Tests | 0 failed/errors; không thêm skip để che test bắt buộc; log command/environment/exit/JUnit thực tế | Chưa nghiệm thu kỹ thuật phần bị ảnh hưởng |
| UI | 2 asset × 4 trang × widths 390/768/1280/1440/1920 =40 tổ hợp; thêm 8 tổ hợp desktop 1280 ở zoom 125%; 0 exception, 0 page overflow ngoài bảng cuộn riêng, 0 KPI bị cắt | Sửa layout; không thiết kế lại toàn bộ |

Stability phải báo cáo riêng theo initializer và pooled giữa các initializer, không dùng ARI=1 trong một nhóm khởi tạo để tuyên bố ổn định toàn cục. State alignment khi so xác suất dùng train profiles, không chọn mapping trên test. Fit hợp lệ nhưng unstable vẫn có giá trị nghiên cứu; không được quảng bá thành model đáng tin cậy để đầu tư.

Các CI dùng để mô tả nhãn vẫn có tính điều kiện theo model đã fit. Kiểm tra đa seed/refit/window là bằng chứng bổ sung, không gọi CI điều kiện là toàn bộ bất định mô hình.

### 2.1. Selection và kiểm soát thí nghiệm

- K chính [2,3,4], K=5 chỉ sensitivity; initializers kmeans/volatility_quantiles theo cấu hình research baseline. Giữ baseline riêng, không ghi đè champion cũ.
- Fit scaler/imputer/labels trên train. Chọn trong candidates hợp lệ bằng validation predictive LL/ngày; tie ≤1e-8 dùng BIC rồi K nhỏ hơn rồi seed nhỏ hơn. AIC, duration, interpretability và occupancy đều phải báo cáo, không chọn bằng test.
- Báo cáo homogeneous HMM có/không vượt stability gate; không âm thầm thay tiêu chí lựa chọn baseline. Mọi champion V2 phải ghi rõ rule và candidate registry.
- Rolling-origin robustness trong phần development: train mở rộng tới 05/05/2021, 05/05/2022, 05/05/2023; validation tương ứng 06/05/2021–05/05/2022, 06/05/2022–05/05/2023, 06/05/2023–24/01/2025. Mỗi fold fit preprocessing/labels lại từ train fold. Không dùng historical test để chọn window.
- RV14/RV21/RV30 là sensitivity đã khai báo, giữ log-return/log-volume nhất quán. Mọi candidate chạy thêm phải được đăng ký trước khi chạy và có amendment; không âm thầm mở grid.
- Run registry phải ghi seed, sample, features, hyperparameters, runtime, convergence, selection status và failure reason, kể cả run không thành công.

## 3. Điều kiện bổ sung số 2 — khả thi NHHMM

### 3.1. Bằng chứng M0 đã đo

Đọc các filtered state trong **train**, đếm cặp ngày liên tiếp cùng segment; đây là hard-path diagnostics của HMM baseline, không phải latent truth hoặc expected transition counts ξ của NHHMM.

| Asset | K baseline | Số lần rời từng state trên train | Số hệ số transition nếu p=1 / 3 / 7 |
|---|---:|---|---|
| BTC | 3 | 19 / 39 / 25 | 12 / 24 / 48 |
| ETH | 4 | 11 / 7 / 15 / 11 | 24 / 48 / 96 |

Số hệ số là K(K−1)(p+1), có intercept và một destination tham chiếu mỗi origin. Chưa bao gồm emission parameters. ETH có nhiều cặp chuyển trạng thái chưa xuất hiện trên hard path. Không suy diễn từ 1.891 ngày rằng có 1.891 sự kiện chuyển trạng thái độc lập.

Train raw non-null coverage: VIX/DXY 100% ở cả hai; funding BTC 70,54%, ETH 66,42%; OI growth BTC 51,30%, ETH 27,18%; stablecoin growth 64,15%. Đây chưa phải coverage sau freshness/as-of audit. Phải kiểm lại tại M1; không dùng non-null để chứng nhận point-in-time.

**Kết luận khả thi M0: GO có điều kiện cho triển khai pilot; chưa GO cho xác nhận các hệ số đầy đủ.** Có đủ cơ sở thử mô hình ít covariate có regularization. Không có cơ sở cam kết NHHMM K=4 với 7 predictors sẽ xác định tốt hay hội tụ. Chưa fit NHHMM tại M0.

### 3.2. Protocol pilot và cửa kiểm tra

1. Simulation trước dữ liệu thật: 20 chuỗi ×2.000 quan sát, K=2, p=1, seed 0–19; beta=0 đối chiếu homogeneous HMM với **cùng emission/transition parameters**, filtered max error ≤1e-8. Với beta khác 0, báo cáo recovery sau state alignment, bias/RMSE và failure rate; không tự đặt kết quả recovery là đã đạt.
2. Numerical gate: xác suất hợp lệ như mục 2; objective finite; ít nhất 18/20 simulation fits hội tụ. Không tiếp tục real-data claims nếu gate fail. Tối đa 1.000 optimizer iterations, relative objective change ≤1e-6 qua 5 iterations liên tiếp; ghi norm gradient và kiểm objective cùng penalties. Không nhầm unpenalized LL với penalized objective.
3. Grid thực tế: K=[2,3,4], 5 seed, diagonal Gaussian emissions giữ feature space core; transition covariate families: từng biến đơn {RV21, log-volume, liquidity proxy Amihud, funding, VIX, DXY return, OI growth, stablecoin growth}; thêm nhóm {RV21,log-volume}, {VIX,DXY return}, {RV21,funding}. Chuẩn hóa train; L2 lambda [0,1,10] với objective mean negative LL + lambda×mean(beta²), intercept không phạt. Chọn validation predictive LL trên cùng sample cho từng comparison, complexity làm tie-break.
4. Full-history family chỉ nhận covariate train coverage ≥80%, missing ≤20%, macro age ≤7 ngày; median imputation train với missing indicator được tính vào p. Nguồn muộn: chạy common-window sensitivity bắt đầu khi các nguồn thực sự có dữ liệu; tối thiểu 730 ngày train và 180 ngày validation, không dịch ranh giới sang test. Nếu thiếu số ngày, báo unavailable cho family đó, tiếp tục thu nguồn hợp lệ ở M1; không bịa backfill.
5. Sau preprocessing, design matrix phải full rank; condition number ≤1e8. Nếu fail, không diễn giải beta của design đó; chỉ dùng các nhóm đơn/nhóm đã đăng ký hợp lệ, không lựa predictor bằng test.
6. Mỗi origin cần ≥20 expected exits trên train mới được diễn giải directional transition coefficients; mỗi cặp được diễn giải cần ≥10 expected transitions. Dùng ξ của fitted NHHMM khi có, báo song song hard counts. Đây là ngưỡng sàng lọc thận trọng, **không phải bảo đảm nhận dạng hoặc ý nghĩa thống kê**. Nếu thiếu, chỉ báo predictive fit và bất định; không phát biểu “X dự báo stress” từ dấu beta.
7. Ít nhất 3/5 real-data fits hợp lệ để đưa candidate vào so sánh; kiểm sensitivity regularization, coefficient variability và transition forecast. Nếu không đạt: giữ failed/pending, dừng nhánh đó, ghi lý do. Logistic chỉ là benchmark phụ. Không đánh dấu toàn bộ NHHMM hoàn thành khi chỉ có logistic.

Tại M3, đo runtime 1 cấu hình hợp lệ trước grid đầy đủ; giới hạn 24 giờ cho một batch địa phương, checkpoint và báo phần chưa chạy. Hết ngân sách không đồng nghĩa đạt nghiệm thu. Giảm scope cần người dùng duyệt; không tự bỏ NHHMM hoặc MS-GARCH.

## 4. Điều kiện bổ sung số 3 — thứ tự benchmark

| Thứ tự | Benchmark | Mục tiêu và gate |
|---:|---|---|
| 1 | GMM, K-means | Tận dụng baseline; matched K/features/sample, causal transform; 5 seed; persistence/ARI/state occupancy/economic usefulness |
| 2 | Markov-Switching AR | Econometric comparator trước các mô hình phức tạp; AR order [0,1], K=[2,3,4], selection validation; báo rõ feature space return-only |
| 3 | Online change-point | Chọn nhánh change-point của Blueprint; causal prefix test bắt buộc, không gọi Bayesian nếu implementation không Bayesian |
| 4 | HDBSCAN | Noise rate và out-of-sample assignment rõ; không gọi membership strength là calibrated HMM regime probability |
| 5 | Markov-Switching GARCH | Kiểm numerical likelihood, positivity/stationarity theo specification; simulation/reference validation trước so OOS |

Tất cả vẫn nằm trong phạm vi gói chính. Ưu tiên là thứ tự đầu tư công sức, không phải lý do bỏ các mục cuối. NHHMM là nhánh model nâng cao M3, không lẫn vào benchmark logistic.

Đối với change-point/HDBSCAN/MS-GARCH chưa có implementation đã kiểm: khóa specification, grid và reference tests trong phụ lục riêng **trước khi bắt đầu code/fit từng nhánh**. Chỉ dùng train/development cho pilot; ghi version/amendment, không thay protocol sau khi xem kết quả confirmation. M0 khóa nguyên tắc và gate chung; không giả vờ đã chốt các chi tiết kỹ thuật chưa kiểm khả thi.

## 5. Điều kiện bổ sung số 4 — hai tầng nghiệm thu

| Tầng | Được xác nhận khi | Không được suy diễn |
|---|---|---|
| A. Nghiệm thu kỹ thuật | Source/artifacts thực chạy, gates số học/thời gian/schema pass, các model trong scope có implementation/run hợp lệ, outputs và failures đầy đủ, UI 48 tổ hợp đạt, README tái lập và logs thật | Không đồng nghĩa model stable, hiệu quả đầu tư hay predictors có tác dụng |
| B. Xác nhận nghiên cứu độc lập | Người/team khác tái lập từ package khóa và đối chiếu hashes/metrics; đánh giá trên holdout sau khóa model/protocol, không tham gia tuning, đủ sample/sự kiện; CI và multiple-testing rõ | Tests do chính người sửa chạy hoặc chạy pytest lần nữa không phải independent research validation |

Gói kỹ thuật có thể hoàn thành với kết quả nghiên cứu âm. Model không hội tụ, placeholder hay thiếu benchmark chính là chưa hoàn thành phần kỹ thuật tương ứng; không đổi tên thành “kết quả âm”.

### 5.1. Confirmation, portfolio và claims

- Chưa có prospective holdout tại M0. Holdout bắt đầu từ **ngày UTC đầy đủ đầu tiên sau khi khóa champion, label map, strategy và data protocol tại M5**; ghi cutoff thực tế lúc đó. Dữ liệu phát sinh giữa M0 và M5 nếu đã xem cũng không được gọi untouched.
- Mức tối thiểu trước đánh giá confirmation: 180 daily observations và 20 stress-entry events mỗi tài sản cho claim về stress prediction. Nếu thiếu: pending/underpowered, không kéo dài/chọn ngày kết thúc dựa trên p-value; đánh giá theo mốc 180/365 ngày đã khai báo, điều chỉnh multiple looks bằng Bonferroni 2 lần.
- RQ3: primary predictive metric là paired log-loss difference của next-state distributions so homogeneous HMM cùng K/sample/features; stress-event Brier, PR-AUC và calibration là phụ và có model-derived-target limitation. Chỉ gọi cải thiện khi CI 95% của difference nằm hoàn toàn phía có lợi sau điều chỉnh multiple testing.
- RQ4: không đặt yêu cầu HMM phải thắng; báo median/min ARI, seed/refit/window variation, persistence và OOS usefulness cho mọi method. So cải thiện cần paired uncertainty; không chỉ silhouette.
- RQ5: giữ B&H, vol-target và regime defensive hiện có; target vol 40%/năm, cash return 0, cap1, ngưỡng risk0,5, defensive weight0,25, phí baseline10bps/turnover. Sensitivity phí5/20bps và next-open execution được báo riêng, không chọn chiến lược thắng trên test. Primary incremental metric: net Sharpe difference so vol-target; B&H, drawdown, return, turnover là đối chiếu bổ sung. Moving-block paired bootstrap1.000, block21, sensitivity14/42; CI95%, Holm cho family asset×strategy comparisons. Không gọi CI bootstrap là bằng chứng chắc chắn trong mẫu hiếm sự kiện.
- Chưa có external replication hoặc đủ prospective sample thì trạng thái tầng B là **pending**, dù tầng A pass. Người triển khai bàn giao result cards, tables/figures và limitations; team khác viết nội dung học thuật.

## 6. Output contract và thứ tự mở triển khai

Giữ T01–T08, F01–F06 và RQ result cards của kế hoạch gốc; không giảm deliverables. Mỗi output có ID, version, model/run ID, SHA-256, data-through/as-of UTC, sample, units, probability type, status và limitation. Filtered/smoothed tách riêng. NHHMM T+1 dùng covariates đã có ở thời điểm t; không lấy X ngày mai thực tế.

Trình tự: xác minh baseline → ghi protocol này → ghi `lock_manifest.json` hash baseline, kế hoạch gốc, protocol và evidence → mới cho phép thay đổi source trong milestone sau. Mọi amendment ghi thời điểm/lý do/phạm vi, giữ bản cũ và chỉ rõ có ảnh hưởng confirmation không. Hash là dấu vết kiểm tra, không phải cơ chế lưu trữ bất biến bên ngoài.

M0 không tuyên bố các gates M1–M7 đã pass, không chạy model mới và không sửa app. Baseline test evidence được trích riêng trong báo cáo M0; không nhận là lần chạy mới của lượt này.
