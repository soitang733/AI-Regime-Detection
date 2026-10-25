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


---

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


---

<!-- Historical approved scope, original v1.0 follows. Current status is in M0 lock. -->

# KẾ HOẠCH HOÀN THIỆN AI CRYPTO MARKET REGIME RADAR

**Bản cuối trình duyệt — phiên bản 1.0 — 24/10/2026**  
**Trạng thái: CHỜ NGƯỜI DÙNG DUYỆT, CHƯA TRIỂN KHAI THEO KẾ HOẠCH NÀY.**

Bản này thay thế các bản đề xuất trước về phạm vi thực hiện. Căn cứ là Research Blueprint 02 người dùng cung cấp. Không phải báo cáo kết quả hoặc tuyên bố các đầu ra bên dưới đã tồn tại.

## 1. Phạm vi xin duyệt

### 1.1. Bên triển khai chịu trách nhiệm

Hoàn thiện **data + code + thí nghiệm + mô hình + kết quả RQ1–RQ5 + bảng/hình + dashboard + kiểm thử + hồ sơ kỹ thuật bàn giao**. Chủ động lấy bổ sung dữ liệu hợp lệ khi cần, không dừng ở việc liệt kê thiếu dữ liệu.

Gói chính gồm:

1. Chuẩn hóa protocol và dữ liệu BTC/ETH, bổ sung nguồn macro/crypto và kiểm soát thời điểm thông tin.
2. Gaussian HMM, lựa chọn K, ổn định qua khởi tạo/cửa sổ, hồ sơ và nhãn regime theo thống kê.
3. **NHHMM đúng bản chất**, giữ logistic phụ trợ làm benchmark, trả lời RQ3.
4. Đối chứng **Markov-switching AR, Markov-switching GARCH, GMM, KMeans, HDBSCAN và change-point**. Change-point là lựa chọn cho nhóm Bayesian/change-point trong Blueprint; không ghi là Bayesian nếu không dùng phương pháp Bayesian.
5. Backtest B&H, volatility targeting, defensive regime allocation và kết hợp regime + volatility targeting.
6. Crypto Market Regime Radar đủ current probabilities, history, persistence, drivers, transition và BTC/ETH comparison.
7. Bộ bảng/hình học thuật, artifacts, time series, test logs và result cards để team khác viết bài.

### 1.2. Ngoài phạm vi gói chính

- **Team khác viết nội dung paper:** Abstract, Introduction, literature review, prose Results/Discussion, Conclusion và biên tập tài liệu tham khảo. Bên triển khai cung cấp công thức, số liệu, nguồn, chỉ mục bảng/hình và giới hạn kết luận.
- Mục 4.3 là **gói mở rộng tùy chọn**, không tự triển khai khi chỉ duyệt gói chính: regime-dependent volatility forecasts, Bayesian HMM, common regimes và HMM+RL. Mục 12 nêu đầu ra nếu chọn thêm.
- Không commit/push, không deploy công khai, không chuyển sang giao dịch tiền thật.

### 1.3. Nguyên tắc giữ xuyên suốt

- Giữ cấu trúc repository, tái sử dụng phần đúng; không viết lại toàn dự án.
- Lưu baseline cũ để đối chiếu, không xóa kết quả bất lợi hoặc ghi đè mất dấu nghiên cứu.
- Giữ tông be–xanh rêu và tinh thần giao diện hiện tại; sửa phân cấp thông tin và responsive, không tự thay thiết kế hoàn toàn.
- Không ép K=4, không ép đủ Bull/Bear/Calm/Stress, không tạo xác suất/state giả.
- Không tối ưu theo test để làm đẹp kết quả. Model không tốt vẫn phải được báo trung thực.
- Không hứa model sẽ ổn định, sinh lời hoặc hơn mọi benchmark trước khi chạy thí nghiệm.

## 2. Hình dung sản phẩm sau khi hoàn thiện

Người xem chọn BTC hoặc ETH và trả lời được ngay:

1. Dữ liệu đến nến UTC nào, có sẵn lúc nào?
2. Regime hiện tại tên gì, có đặc điểm kinh tế nào?
3. Xác suất của **tất cả K state** là bao nhiêu?
4. Model căn cứ vào các quan sát nào để nhận diện?
5. Regime này đã kéo dài bao lâu, persistence và expected duration train là gì?
6. Ngày tiếp theo có thể ở những regime nào, xác suất bao nhiêu?
7. BTC/ETH giống hay khác nhau về trạng thái kinh tế/rủi ro?
8. Tín hiệu có giúp kiểm soát rủi ro/allocation trong các thí nghiệm không?

Dashboard là công cụ nhận diện regime theo xác suất, không phải công cụ dự báo giá. Phần chẩn đoán kỹ thuật nằm lớp sau, có liên kết để truy vết thay vì chiếm toàn bộ Overview.

## 3. Thiết kế nghiên cứu và quy tắc chọn model

### 3.1. Tách baseline, development và đánh giá cuối

- Chụp snapshot baseline: config, source, manifest, model, predictions và chỉ số.
- Tạo `research_protocol_v2` trước khi fit model mới: mẫu/folds, candidate budget, features, seeds, quality gates, metric, taxonomy và portfolio rule.
- Kết quả trên lịch sử đã xem được ghi **exploratory**; không chia lại mẫu cũ rồi gọi là untouched.
- Dùng rolling/expanding validation trong lịch sử phát triển để kiểm độ bền; mọi scaler/imputer/label/model của fold chỉ fit train fold đó.
- Khóa cấu hình trước đánh giá cuối. Dữ liệu mới phát sinh sau ngày khóa protocol có thể làm prospective holdout/shadow evaluation; không tuyên bố đã có kết quả tương lai.
- Nếu cần điều chỉnh sau đánh giá cuối, tăng protocol/model version và ghi test reuse, không báo lại là thử nghiệm độc lập.

### 3.2. Cách chọn model chính cho Radar

Đánh giá K=2,3,4 cho RQ1 và thêm K=5 làm sensitivity/bảng học thuật. Dùng quality gates trước, score validation sau; quy tắc tie-break và stability được công bố trong protocol. So sánh LL chỉ trong cùng feature space/định nghĩa density; khi khác feature space phải dùng metric chung phù hợp.

Model chính được chọn bằng train/validation theo protocol. Các mô hình khác có thể là benchmark hoặc nghiên cứu bổ sung; không tự đưa nhiều model lên Overview mà không giải thích model nào đang phát tín hiệu chính.

Khi đổi model chính, pipeline, Radar, transition, backtest và profile phải nhận cùng model ID và mapping; baseline vẫn có thể xem riêng. Model unstable chỉ dùng research với cảnh báo và acknowledgment, không âm thầm bỏ gate.

## 4. Giai đoạn A — Data, features và kiểm soát thời gian

| Công việc | Thực hiện | Đầu ra |
|---|---|---|
| BTC/ETH Spot | Cập nhật nến đã đóng, kiểm duplicate/gap/outlier và units | Raw/processed hợp lệ, quality log |
| Derivatives | Bổ sung funding đã thanh toán, OI và growth từ API/archive hợp lệ | Coverage theo asset/period, timestamps và definitions |
| Macro | VIX, DXY, SPX, Treasury yields; kiểm lịch phiên/availability | As-of features, provenance và stale flags |
| Market controls | CoinGecko/DefiLlama/Coin Metrics, stablecoin/TVL/market cap | Các định nghĩa được lưu tách biệt, không trộn chuỗi tùy tiện |
| Tài sản mở rộng | SOL/BNB và dữ liệu crypto index nếu có nguồn hợp lệ | Descriptives/sensitivity riêng, không thay core BTC/ETH |
| Chỉ số thiếu | Tìm nguồn công khai; nếu không có có thể tạo research basket công thức rõ | Basket tên riêng, universe/rebalancing/survivorship limitations; không giả làm CMC200 |
| Feature engineering | Returns, RV, volume, liquidity, funding, OI, correlation và macro controls | Feature matrix và danh sách feature thực dùng mỗi model/fold |
| Kiểm volume drift | Occupancy theo năm; ablation bỏ volume; thử relative-volume nhân quả | Báo cáo state theo thời kỳ và kết quả ablation |

Đặc biệt kiểm tra ETH state có nhiều ngày train nhưng biến mất OOS; không mặc định đó là regime kinh tế tái diễn. Relative-volume/rolling transforms chỉ dùng dữ liệu quá khứ và phải có warm-up rule.

**Nghiệm thu A:** đủ dictionary, source log, coverage/availability và split; không có nến đang mở, future join, return nối qua gap hoặc scaler fit ngoài train. Dữ liệu current-vintage phải ghi revision bias; độ trễ giả định không được trình bày như chứng minh đã loại hết bias.

## 5. Giai đoạn B — RQ1: HMM, K và stability

**Mục tiêu:** xác định K phù hợp có điều kiện theo mô hình và mức độ chắc chắn của lựa chọn đó.

### Công việc bắt buộc

1. Gaussian HMM với K=2,3,4 và sensitivity K=5; thử nhiều seed/initializer có đa dạng nghiệm.
2. Kiểm hội tụ thực, finite likelihood/covariance, variance floor, state occupancy.
3. Xuất AIC/BIC, train/validation LL, persistence, duration/fragmentation và profile interpretability.
4. Khóa quy tắc selection trước OOS: quality gates, validation score, tie-break và stability sensitivity; không tự cộng điểm kinh tế sau khi xem test.
5. Đánh giá seed, window và refit stability; đo riêng High-Risk agreement, probability MAE và Jaccard trên các ngày rủi ro.
6. Tổng hợp tỷ lệ chọn K qua fold, không chỉ báo một K của một lần chạy.

**Đầu ra:** selection/candidate table, fit/failure diagnostics, seed/window/refit table, hình score theo K và K theo fold.

**Nghiệm thu B:** lý do chọn/loại từng ứng viên truy vết được; không chọn trên test; không gọi persistence cao hoặc ARI cao trong một initializer family là ổn định toàn cục. Nếu K chưa bền, kết luận phản ánh uncertainty.

## 6. Giai đoạn C — RQ2: Hồ sơ và nhãn regime

### 6.1. Mỗi state phải có hồ sơ có ý nghĩa

Mean/median return, volatility, downside/tail risk, volume, liquidity proxy, occupancy, persistence, expected duration, số episode và uncertainty. Có thống kê train/OOS tách riêng; bổ sung funding/OI nếu đủ thông tin.

So sánh từng cặp/effect sizes với block uncertainty và điều chỉnh nhiều so sánh; bổ sung refit sensitivity. Đánh giá các trục khác đơn vị bằng thước đo thích hợp, không kết luận vol “quan trọng hơn” chỉ vì trị số lớn hơn.

### 6.2. Quy tắc đặt tên

Giữ nguyên canonical `state_id` và `label_map`; thêm display label và profile đa chiều, `label_rule_version`, `fit_period`, `evidence_strength`, warnings.

Tên có thể là Calm/Bull/Bear/Stress **hoặc tên khác theo số liệu**, như “Biến động trung bình”, “Khối lượng thấp tương đối · biến động trung bình”, “Tăng trưởng · biến động cao”. Các tên này là ví dụ cấu trúc; tên cuối phải được tạo từ train của model thực chọn.

Phân biệt:

- Tên mô tả/rank trong train với khẳng định có ý nghĩa thống kê.
- Mean train dương với bằng chứng một state Bull bền vững.
- Không bác bỏ mean=0 với chứng minh Sideways.
- Volume cao với liquidity tốt, Calm với an toàn hoặc return tương lai dương.

Distribution hiển thị theo K state tạo thành phân hoạch. Nếu direction/risk là hai trục chồng lấn, không cộng chúng thành bốn xác suất có tổng 100% một cách sai nghĩa. Nếu gộp state vào category, mapping phải fixed, disjoint và công bố rõ.

**Đầu ra:** profiles/contrasts, taxonomy JSON, label evidence, occupancy theo năm, profile heatmap và biểu đồ return/vol/liquidity.

**Nghiệm thu C:** mọi state có mô tả dễ hiểu và ID gốc; nhãn khóa train, không đổi theo test; state thưa/biến mất và uncertainty hiện rõ. Không ép đủ bốn tên nhưng cũng không để các State ID vô nghĩa là lớp hiển thị chính.

## 7. Giai đoạn D — RQ3: Drivers và NHHMM

### 7.1. NHHMM thật

Triển khai `P(S_(t+1)=j | S_t=i, X_t) = softmax_j(a_ij + beta_ij' X_t)` trong latent-state likelihood. Covariates phải sẵn có khi dự báo; convention chỉ số thời gian ghi rõ.

Có thể dùng EM với expected transition weights hoặc tối ưu likelihood tương ứng. Có baseline destination để nhận diện tham số, regularization và giới hạn model size. Không đổi tên logistic binary trên hard labels thành NHHMM.

Xét các nhóm RV/volume, funding/OI, stablecoin growth, VIX/DXY và liquidity/market controls. Lưu feature coverage/feature thực dùng. Khi số chuyển trạng thái quá ít, giảm complexity theo quy tắc train/validation đã khóa; không tạo event giả hoặc sửa định nghĩa stress theo test.

### 7.2. Đối chứng và đánh giá

- Giữ logistic hiện có làm auxiliary benchmark.
- So với homogeneous HMM và train-prevalence baseline trên cùng event/risk set.
- Báo predictive log score, Brier/log-loss, PR-AUC, event counts và uncertainty của incremental value.
- Báo hệ số beta theo cặp state, regularization/diagnostics và conditional transition P_ij(X_t) theo thời gian.
- Không diễn giải hệ số/contribution là quan hệ nhân quả.

### 7.3. Kiểm tra bắt buộc

Simulation trước dữ liệu thật: hàng P tổng 1, finite likelihood, beta=0 khớp homogeneous transition, kiểm optimization/gradient khi phù hợp, parameter recovery có tính label switching, availability và prefix invariance.

**Đầu ra:** NHHMM coefficients, diagnostics, driver scores/ablation, dynamic transition series, marginal state forecasts và failure records.

**Nghiệm thu D:** NHHMM phải thực chạy và được kiểm tra mới nhận mục 2.4/bảng transition regressors hoàn thành. Nếu model chưa fit được thì đó là mục chưa đạt, không thay bằng bảng logistic để đủ tên. Nếu fit được nhưng predictors không hữu ích, kết luận âm vẫn là kết quả hợp lệ.

## 8. Giai đoạn E — RQ4: Benchmark đầy đủ và so sánh công bằng

| Phương pháp | Vai trò/việc thực hiện | Điều kiện đánh giá |
|---|---|---|
| GMM | Benchmark mixture không có Markov dynamics | Cùng feature space khi so joint density, nhiều seeds/folds |
| KMeans | Benchmark clustering | Persistence/refit/profile/utility; inertia không được so với LL |
| Markov-switching AR | Benchmark econometric return dynamics | So raw-return predictive density trên cùng target nếu khác feature space với HMM |
| Markov-switching GARCH | Benchmark volatility switching | Ràng buộc variance/stationarity theo đặc tả; nêu rõ nếu dùng approximate likelihood |
| HDBSCAN | Density clustering, có noise/unassigned | Fit train; xác định cơ chế OOS; không biến membership/distance thành posterior giả |
| Change-point | Phát hiện điểm thay đổi | Online/prefix-causal cho tín hiệu; offline full-series chỉ retrospective, có cảnh báo |

So trên cùng lịch dữ liệu hợp lệ, budget/phạm vi phù hợp. Tách **persistence theo ngày, stability giữa seeds/refits/windows, interpretability, downstream usefulness**. Align state theo train profiles; không xem cùng State ID là cùng ý nghĩa.

Các model khác feature space không được xếp hạng bằng mức joint LL khác chiều. Có thể dùng return-density marginal chung nếu tính nhất quán; model không có density không được gán LL giả.

**Đầu ra:** benchmark scores, state-comparison/alignment matrix, seed/refit/window stability, coverage/noise/failure tables và comparison figures.

**Nghiệm thu E:** mỗi phương pháp trong gói chính có implementation và run/diagnostics. Không hội tụ phải là failure được xử lý/đánh dấu, không tính như output mô hình thành công. Không cần HMM thắng để nghiệm thu thiết kế so sánh đúng.

## 9. Giai đoạn F — RQ5: Giá trị allocation và kiểm soát rủi ro

### Chiến lược phải so

1. Buy-and-Hold.
2. Volatility targeting.
3. Defensive regime allocation.
4. Regime + volatility targeting.

Tham số chỉ định trước hoặc chọn trên validation theo protocol. Filtered signal tại t áp dụng cho kỳ tiếp theo, kiểm as-of và execution time; không smoothed/backward shift. Cùng asset/date, phí, cash assumptions và scenario.

So ba incremental comparisons: regime so B&H; vol target so B&H; **regime+vol target so vol target thuần**. Nếu có Bull được xác định hợp lệ, có thể dùng quy tắc kết hợp P(Bull)/P(Stress); nếu không có, dùng stress defensive rule và giải thích rõ.

Báo annualized return/CAGR, vol, Sharpe, MDD, turnover, transaction costs, exposure, risk-off days, rebalance count. Paired uncertainty và kết quả theo window; thêm refit uncertainty nếu khả thi. Kiểm baseline close-to-close, drift-adjusted và next-open; nêu phần chưa mô phỏng latency/spread/slippage.

**Đầu ra:** performance, incremental value/CI, NAV/return/weight/turnover/cost/drawdown time series, exposure/cost attribution, NAV/drawdown plots.

**Nghiệm thu F:** không gán lợi ích vol targeting thuần cho regime; không tune test; không loại kết quả âm. Kết luận “không cải thiện” được chấp nhận nếu phương pháp và bằng chứng đầy đủ.

## 10. Giai đoạn G — Product output đúng Blueprint 4.2

### 10.1. Overview / Radar chính

```text
Asset · ngày nến UTC · as_of · model version · cảnh báo chất lượng

CURRENT REGIME
Tên mô tả dễ hiểu + State ID/nhãn model gốc
Đặc trưng return / volatility / volume-liquidity và mức bằng chứng

P của toàn bộ K state hiện tại       P của toàn bộ K state ngày tiếp theo
Tên + số liệu + probability bar      Tên + số liệu + probability bar

Vì sao model nhận diện như vậy?      High-Risk và cảnh báo uncertainty
```

Không dùng số minh họa làm dữ liệu thật. Nếu model có bốn nhãn phù hợp thì hiển thị P(Bull), P(Calm), P(Bear), P(Stress); nếu K/tên khác thì hiển thị đúng K/tên theo train.

### 10.2. Các thành phần bắt buộc

| Thành phần | Nội dung phải có |
|---|---|
| Regime history | Giá với nền regime, probabilities theo thời gian, chọn state/khoảng ngày; filtered default, smoothed có hindsight |
| Persistence | Episode đã kéo dài bao lâu; P_kk train, expected duration và observed run stats; không gọi expected total duration là thời gian chắc chắn còn lại |
| Drivers | Tách current-state explanation từ features/prior với transition predictors; mức bằng chứng và limitations rõ |
| Probability of transition | Current/T+1 side by side, conditional P và marginal forecast tách biệt; dynamic P cho NHHMM |
| BTC/ETH comparison | Snapshot, profile/risk, persistence, probability history và mức divergence; không so ID như cùng economic state |
| Portfolio/research | Hiệu suất và đối chứng thật; diagnostics/mô hình phụ nằm lớp sau, không lấn Radar |

### 10.3. Điều kiện UI

Giữ tông màu đã thống nhất, tăng độ rõ của thông tin thay vì thêm nhiều khung. Có kiểm desktop/mobile và zoom 125/150%, table cuộn trong khung, tooltip không đè nhãn, charts resize đúng. UI chỉ đọc artifacts đã xác minh; không fit model trong app.

**Nghiệm thu G:** đủ hành trình người dùng ở mục 2, dữ liệu thật, schema/time/model ID đúng, không lỗi cả BTC/ETH và các trang. Warnings unstable/stale/rare-state giữ rõ; thiếu artifact phải có lỗi/hướng dẫn tái tạo, không tạo số giả.

## 11. Danh mục output bắt buộc và hồ sơ bàn giao

### 11.1. Academic tables — đáp ứng đủ 6 loại Blueprint và bổ sung robustness

| ID | Đầu ra | Nội dung nghiệm thu |
|---|---|---|
| T01 | Descriptive statistics | Core/extensions, units, sample và coverage |
| T02 | Model-selection K=2,3,4,5 | AIC/BIC/LL, quality gates, persistence/duration, failure/selection reasons |
| T03 | Regime-specific profiles | Mean/vol/liquidity, contrasts, occupancy, mapping/evidence |
| T04 | Transition matrix | P_ij/P_kk/duration; conditional dynamic transitions tách riêng |
| T05 | NHHMM transition regressors | beta_ij, feature/scaling definitions, diagnostics/uncertainty; không thay bằng logistic |
| T06 | Portfolio performance | B&H/vol target/regime/kết hợp; return/risk/cost và incremental comparisons |
| T07 | Benchmark comparison | MS-AR/MS-GARCH/GMM/KMeans/HDBSCAN/change-point và HMM/NHHMM |
| T08 | Robustness | Seeds/windows/refits, feature ablation, state drift, failure/coverage |

### 11.2. Academic figures — đáp ứng đủ 5 loại Blueprint và hình hồ sơ bổ sung

| ID | Đầu ra |
|---|---|
| F01 | Giá BTC/ETH kết hợp background regimes |
| F02 | Filtered/smoothed probabilities, hindsight ghi rõ |
| F03 | Transition probabilities theo thời gian; conditional/marginal phân biệt |
| F04 | Comparison/alignment giữa phương pháp; không gọi confusion accuracy nếu thiếu ground truth |
| F05 | Cumulative NAV, kèm drawdown/exposure nếu cần |
| F06 | State profiles và occupancy theo năm, selection/stability diagnostics |

Định dạng: bảng CSV có data dictionary; hình PNG và SVG có legend, units, data period và model/run ID. Team viết không phải lấy screenshot dashboard thay cho hình nghiên cứu.

### 11.3. Artifact kỹ thuật

| Nhóm | Đầu ra phải giao |
|---|---|
| Data | Raw/cache hợp lệ hoặc đường tải rõ, processed features, dictionary, source log, quality/coverage/availability, split/fold manifests |
| Model | Model artifacts, scaler/imputer, config, taxonomy/label maps, metadata, fit/selection/failure diagnostics; kiểm load lại |
| Predictions | Đủ K filtered và smoothed tách riêng; asset/date UTC/as_of, State ID, labels, model/run ID, uncertainty flags |
| Forecast | Đủ K T+1 probabilities, horizon, conditional P/static/dynamic theo model, covariate as-of |
| Portfolio | Signal/execution times, weights/returns/NAV/drawdown/turnover/costs theo chiến lược/scenario |
| Product | Dashboard source/config, local launch instructions, demo/screenshot và browser-check evidence |
| Reproducibility | Dependency lock, pipeline entrypoint, seeds/folds/protocol, hashes/manifests, actual test logs và known issues |
| Team viết | RQ result cards, methods spec, table/figure index và claims/limits |

### 11.4. Hồ sơ đưa team viết, không viết paper thay team

Mỗi RQ result card ghi: câu hỏi, protocol/experiment, sample, model/features, số liệu chính, bảng/hình liên quan, kết luận số liệu hỗ trợ được và điều chưa kết luận được.

Methods spec có công thức/units, feature/availability, fit/selection/inference, label rules và portfolio metrics. Index bảng/hình chỉ đường dẫn và cách đọc. Claims/limits liệt kê cả kết quả âm, uncertainty, vintage bias, state thưa, failures và test reuse.

Không viết Abstract/Introduction/Discussion/Conclusion hoặc sửa paper của team khác trong gói này. Bên triển khai chịu trách nhiệm tính đúng của số liệu và phương pháp bàn giao.

### 11.5. Output manifest và trạng thái

Mỗi deliverable có ID, mục Blueprint/RQ, path, status, experiment/model ID, data-through UTC, units, checksum và limitations. Phân biệt `planned`, `implemented`, `verified`, `failed`, `not_applicable`, `deferred_optional`.

File placeholder hoặc model fit thất bại không được nhận là output thành công. Mục failed của gói chính vẫn là chưa đạt; chỉ kết luận nghiên cứu âm trên một thí nghiệm hợp lệ mới được coi là kết quả hoàn chỉnh.

## 12. Mục 4.3 — Các gói tùy chọn, không tự mở rộng phạm vi

| Gói | Đầu ra nếu được chọn thêm | Không đánh đồng với |
|---|---|---|
| O1: regime-dependent volatility forecast | Forecast variance theo regime, so rolling/EWMA/GARCH, QLIKE/calibration/OOS uncertainty | Volatility targeting hoặc realized vol mô tả |
| O2: Bayesian HMM | Priors, posterior inference, label-switching treatment, diagnostics phù hợp phương pháp và predictive checks | EM đa seed; variational inference cũng phải ghi rõ là xấp xỉ, không gọi MCMC |
| O3: common regimes | Joint/multivariate latent model BTC/ETH, sau đó SOL/BNB nếu phù hợp, so separate models | Correlation hay cùng màu state trên dashboard |
| O4: HMM+RL | Causal environment có phí, policy train/validation, fixed test, nhiều seed và rule-based benchmarks | Quy tắc phân bổ cố định có tên “AI” |

Gói chính đã có model nâng cao NHHMM và đủ benchmark theo mục 2.5. Không cần O1–O4 để làm đẹp checklist. Các gói tùy chọn chỉ triển khai khi người dùng chọn phạm vi bổ sung.

## 13. Thứ tự thực hiện và điểm kiểm tra

| Mốc | Giai đoạn | Bàn giao xem xét được trước khi chuyển tiếp |
|---|---|---|
| M0 | Khóa baseline/protocol/schema | Baseline hashes, protocol V2, danh mục output và tiêu chí |
| M1 | A: data/features | Coverage/time audit, state/volume drift và nguồn bổ sung |
| M2 | B–C: HMM, K, taxonomy | Selection, profiles/labels, RQ1–RQ2 và failures |
| M3 | D: NHHMM/drivers | Simulation evidence, fitted outputs, RQ3 và dynamic transitions |
| M4 | E: benchmarks | So sánh phương pháp cùng protocol, RQ4 |
| M5 | F: portfolio | RQ5, incremental results/CI, NAV/exposure/cost |
| M6 | G: Radar integration | BTC/ETH demo đủ thành phần, screenshots/browser checks |
| M7 | Nghiệm thu/bàn giao | Source/artifacts/T01–T08/F01–F06/result cards/logs/README |

Giữ output contract từ M0 để Research và Product tích hợp cùng schema. Một phần có thể chạy độc lập khi phần khác chờ dữ liệu/fit, nhưng không bỏ kiểm chứng phụ thuộc. Cập nhật tiến độ bằng số liệu/công việc đã chạy, không chỉ lời “đang hoàn thiện”.

Không đưa thời hạn chính xác trước khi đo runtime và độ khó hội tụ của các model mới. Blueprint 8–12 tuần là bối cảnh học phần, không phải cam kết runtime của kế hoạch này.

## 14. File/phạm vi tác động dự kiến

| Nhóm | Phạm vi |
|---|---|
| `config/`, protocol docs | Config V2, folds, experiment budget, feature/label/metric rules |
| `src/data/`, `src/features/` | Bổ sung nguồn/audit/causal features khi cần, không sửa C1 tùy tiện |
| `src/models/` | Adapter/contracts khi cần; baseline giữ truy vết, không âm thầm thay outputs |
| `src/research/` hoặc package V2 cùng cấp | Profiles/taxonomy, walk-forward, NHHMM, benchmark families, portfolio evaluation, runner |
| `dashboard/` | Service/schema và 6 thành phần Radar, model chính/benchmark tách rõ |
| `tests/`, `scripts/` | Kiểm tra số học/thời gian, pipeline/reproducibility và browser acceptance |
| `outputs/`, technical docs, `README.md` | Tables/figures/models/predictions/manifests và hồ sơ team viết |
| `paper/` | Giữ nội dung team viết; chỉ bàn giao tài liệu kỹ thuật riêng, không biên soạn paper |

Tên module có thể điều chỉnh để repository gọn; thay tên file không làm thay yêu cầu hoặc giảm phạm vi đã duyệt.

## 15. Nghiệm thu và điều kiện kết thúc

### 15.1. Kiểm thử bắt buộc

- Train-only scaler/imputer/labels; candidate fitting/selection không nhìn test.
- As-of và target timing đúng, không shift sai ở ranh giới split/segment.
- Probabilities finite/trong [0,1]/tổng 1; P hàng tổng 1; current/T+1 đúng công thức từng model.
- Prefix filtering không đổi khi nối quan sát tương lai với model cố định.
- Smoothed không được dùng trong backtest hoặc giả làm tín hiệu online.
- Model save/load tái tạo inference; metadata/CSV/manifest/model ID nhất quán.
- NHHMM simulation/constraints/optimization được kiểm; beta=0 có kiểm đối chiếu phù hợp.
- Benchmark output không gán probability/likelihood sai bản chất; causal change-point không nhìn tương lai.
- Portfolio cùng sample/scenario, phí và timing có kiểm toán; metrics khớp time series.
- Dashboard đủ BTC/ETH và trang/chế độ, mobile/desktop/zoom; stale/unstable/missing warnings đúng.
- Chạy lại tests cũ và tests mới phù hợp; lưu command/log/exit/JUnit thực tế. Không nới test để đạt.

### 15.2. Tiêu chuẩn hoàn thành gói chính

Gói chính được nhận hoàn thành khi có implementation và run evidence cho phạm vi đã duyệt; T01–T08, F01–F06 và artifacts/handoff có trạng thái rõ; Radar tích hợp đúng; tests phù hợp đạt; source/config/data/model provenance truy vết được. Không có mục chính còn placeholder hoặc bị thay bằng proxy khác nghĩa.

Model unstable, predictors không hữu ích hoặc chiến lược không thắng benchmark **không tự làm thất bại đề tài** nếu đã kiểm chứng và báo cáo đúng. Ngược lại, không hội tụ/chưa có implementation/chưa chạy thì không được coi đã giải quyết chỉ bằng lời giải thích.

Prospective holdout chưa đủ thời gian/sự kiện phải ghi pending; có thể hoàn thành kỹ thuật và historical exploratory evaluation nhưng không tuyên bố đã xác nhận prospective performance. Known issues phải được liệt kê riêng.

### 15.3. Phạm vi để người dùng duyệt

**Đề nghị duyệt gói chính tại mục 1.1, thực hiện theo M0–M7, với bộ đầu ra và nghiệm thu tại mục 11/15.**

Phần viết nội dung paper do team khác làm. O1–O4 chưa nằm trong lệnh triển khai gói chính. Không commit/push hoặc deploy công khai.

Sau khi người dùng duyệt, mới bắt đầu thay đổi code/model/dashboard theo bản kế hoạch này; mọi thay đổi phạm vi đáng kể phải được nêu rõ thay vì tự quyết làm khác sản phẩm đã thống nhất.
