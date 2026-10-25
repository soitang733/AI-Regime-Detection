# Đối chiếu độc lập với Research Blueprint 02

Ngày rà soát: 24/10/2026. Nguồn yêu cầu: bản Blueprint người dùng đính kèm tại
`e80298f4-5288-40d6-a76d-39042985cde4/Pasted text.txt`.
Đây là đánh giá phạm vi và chất lượng bằng chứng, không phải điểm chính thức của giảng viên.
Không huấn luyện lại, đổi nhãn, sửa mô hình hoặc commit trong lượt rà soát này.

## Kết luận và cách chấm

**62/100 — 6,2/10 khi chấm theo Blueprint nghiên cứu đầy đủ.** Dự án đã có pipeline,
HMM, dữ liệu và sản phẩm chạy được, nhưng chưa hoàn thành các trụ cột nghiên cứu.
Số test đạt không thay thế đánh giá chất lượng mô hình.
Không trừ điểm vì chiến lược không thắng Buy-and-Hold hoặc không có đủ bốn tên regime.
Không yêu cầu triển khai mọi thuật toán được liệt kê hoặc các mở rộng tùy chọn như RL.

| Hạng mục | Điểm | Bằng chứng đã có | Thiếu hoặc hạn chế làm mất điểm |
|---|---:|---|---|
| Dữ liệu, nguồn, thời điểm có sẵn | 11/15 | BTC/ETH, macro, funding/OI, market controls; dictionary/source log; as-of join | Current-vintage chưa loại revision bias; độ phủ nguồn ngoài khác nhau; crypto index thiếu; dữ liệu đã tải chưa được sử dụng đầy đủ trong nghiên cứu |
| HMM và model selection | 12/15 | Gaussian HMM, AIC/BIC, LL validation, hội tụ/occupancy; K=2..4 lõi và K=2..5 bổ sung | Lõi ưu tiên LL, BIC chỉ phá hòa; duration/interpretability chưa là tiêu chí quyết định rõ; giả định Gaussian diagonal và feature chồng lấn cần kiểm tra sâu hơn |
| Thống kê và diễn giải regime | 9/15 | Mean/vol/tail, block CI, Amihud, persistence/duration; nhãn train-frozen | Nhiều State ID chưa được mô tả; quy tắc nhãn hẹp và có ưu tiên risk trước direction; thiếu taxonomy đa chiều, kiểm tra khác biệt từng cặp và bất định refit |
| Drivers / RQ3 / mô hình nâng cao | 4/10 | Logistic regularized dự báo chuyển vào nhãn High-Risk t+1, baseline prevalence, proper scores | Không phải NHHMM, không ước lượng beta_ij theo trạng thái xuất phát; chỉ 1–2 sự kiện validation và 2 sự kiện test mỗi tài sản; chưa có mô hình nâng cao khác kiến trúc được kiểm chứng |
| Benchmark / RQ4 | 4/10 | GMM, KMeans, matched feature-space LL và persistence | Thiếu benchmark econometric Markov-switching; chưa có change-point; chưa chứng minh HMM ổn định OOS hơn các phương pháp bằng giao thức chung |
| OOS và robustness | 7/15 | Train/validation/test, lọc nhân quả, seed ARI, RV14/21/30, block14/21/42 | Core unstable; ARI tốt của mô hình bổ sung chỉ trong initializer family; chưa có walk-forward nhiều cửa sổ, refit uncertainty hoặc holdout mới cho phần mở rộng |
| Ứng dụng tài chính / RQ5 | 7/10 | B&H, regime-aware, vol targeting, phí/turnover, execution scenarios, paired bootstrap | Chưa có bằng chứng lợi ích bền vững qua nhiều giai đoạn; một số tín hiệu gần như không hoạt động; chưa kiểm chứng prospective |
| Dashboard | 4/5 | Current/T+1 đủ K, filtered/smoothed tách biệt, UTC, lịch sử, so sánh BTC/ETH, portfolio | Chưa tổng hợp hồ sơ regime đa chiều; kết luận RQ còn rời rạc và nhiều bảng kỹ thuật; mô hình lõi và bổ sung làm sản phẩm thiếu câu chuyện thống nhất |
| Báo cáo và tái lập | 4/5 | Source, dependency lock, scripts, test logs, manifest/hash, paper có kết quả thật | Paper còn dạng technical report sinh tự động; cần literature review, thiết kế giả thuyết, kiểm định và thảo luận kết quả sâu hơn |
| **Tổng** | **62/100** | | |

## Đọc đúng phần gán nhãn của Blueprint

Mục 2.3 cho bốn nhãn làm ví dụ và yêu cầu gán nhãn dựa trên thống kê sau ước lượng.
Mục 2.1/3.5 còn nêu volume, liquidity và derivatives conditions. Vì vậy:

- Không bắt buộc đủ Bull/Bear/Calm/Stress.
- Không bắt buộc mọi state phải vượt kiểm định mean return khác 0 mới được có tên mô tả.
- Có thể dùng tên như biến động trung bình, khối lượng thấp tương đối, hoặc biến động
  cao kèm lợi nhuận trung bình âm, với phạm vi/độ chắc chắn rõ ràng.
- Mean dương trong mẫu không tự chứng minh Bull có ý nghĩa thống kê hoặc khả năng dự báo.
  Không bác bỏ mean=0 cũng không chứng minh Sideways; cần tiêu chí riêng nếu muốn dùng tên đó.
- Tên mô tả theo rank trong cùng tài sản khác với khẳng định khác biệt có ý nghĩa thống kê.
  Hai mức này phải được phân biệt trên UI và báo cáo.

Hiện `train_mapping()` chỉ đặt Low-Vol/High-Vol và để các state còn lại trung tính.
`economic_evidence()` bổ sung Calm/Stress/Bull/Bear từ return/vol/tail; khi cả direction
và risk đều đạt, risk được ưu tiên làm tên chính. Liquidity được thống kê ở bảng riêng
nhưng chưa được kết hợp vào nhãn. Cơ chế này thận trọng, nhưng chưa khai thác hết Blueprint.

### Tên mô tả có thể cân nhắc từ số liệu hiện có — chưa áp dụng

Các số dưới đây là train của HMM lõi, daily log-return standard deviation, không năm hóa.

| Asset/state | Vol/ngày | Khối lượng quote trung bình/ngày | Tên mô tả gợi ý |
|---|---:|---:|---|
| BTC/0 | 5,44% | 1,91 tỷ USDT | Biến động cao · rủi ro đuôi cao; Stress có bằng chứng theo quy tắc hiện tại |
| BTC/1 | 3,28% | 1,88 tỷ USDT | Biến động trung bình; hướng lợi nhuận chưa rõ |
| BTC/2 | 1,99% | 1,69 tỷ USDT | Biến động thấp; Calm có bằng chứng theo quy tắc hiện tại |
| ETH/0 | 4,32% | 86,9 triệu USDT | Khối lượng thấp tương đối · biến động trung bình |
| ETH/1 | 3,23% | 845,6 triệu USDT | Biến động thấp; Calm theo quy tắc hiện tại |
| ETH/2 | 8,60% | 1,37 tỷ USDT | Biến động cao · rủi ro đuôi cao; Stress theo quy tắc hiện tại |
| ETH/3 | 4,93% | 1,65 tỷ USDT | Khối lượng cao tương đối · biến động trung bình |

Đây là đề xuất diễn đạt hồ sơ đã đo, chưa phải taxonomy mới được kiểm định.
Giữ nguyên State ID/label_map gốc, lưu display_label/description riêng và khóa từ train.
Không gọi khối lượng thấp là thiếu thanh khoản khi chưa có bằng chứng spread/depth/proxy phù hợp.
So sánh volume chỉ trong cùng tài sản và mẫu train, không áp dụng ngưỡng tuyệt đối cho tài sản khác.

## Những vấn đề nghiên cứu quan trọng hơn việc đổi tên

1. **ETH state 0 biến mất ngoài mẫu.** Có 819/1.891 ngày train nhưng 0 ngày hard assignment
   trên validation và 0/637 ngày test. Khối lượng train thấp hơn hẳn các state khác.
   Đây là dấu hiệu cần kiểm tra state có đang mô tả giai đoạn quy mô giao dịch cũ,
   thay vì một trạng thái thị trường tái diễn. Chưa đủ để kết luận nguyên nhân.
2. **ETH Stress hiếm ngoài mẫu.** 7/630 ngày validation và 2/637 ngày test.
   Chưa đủ bằng chứng OOS để kết luận nhãn này bao phủ tốt các giai đoạn stress.
3. **BTC Calm chiếm 526/637 ngày test (~82,57%).** Cần đối chiếu biến động thực tế,
   drift của feature và các giai đoạn thị trường; không tự xem tỷ lệ cao là đúng hoặc sai.
4. **High-Risk đã có kiểm tra riêng.** `C2_stability_summary.csv` có disagreement,
   probability MAE và Jaccard; đề xuất trước đó nói như chưa có là chưa chính xác.
   Với K được chọn, Jaccard sự kiện trung bình validation BTC khoảng 0,61,
   ETH khoảng 0,253. Disagreement toàn bộ ngày chỉ khoảng 1,24%/0,76% nhưng có thể
   bị che bởi số ngày High-Risk rất ít. Không thể dùng tỷ lệ đồng thuận tổng thể cao
   để bỏ qua bất đồng ở các ngày rủi ro.
5. **Test của phần mở rộng không còn untouched.** Source tránh đưa test vào fit/selection
   theo từng lần chạy; tuy nhiên các hướng mở rộng đã được thiết kế sau khi test cũ
   được xem. Đây là nghiên cứu khám phá, cần giao thức khóa trước và dữ liệu mới để xác nhận.

## Đối chiếu các đầu ra được Blueprint nêu

| Đầu ra | Hiện trạng |
|---|---|
| Descriptive statistics | Có B01/B01_ext |
| Model selection K=2,3,4,5 | Có ở các họ bổ sung; lõi chỉ K=2,3,4 |
| Regime-specific mean/vol | Có B04 và bảng research |
| Transition matrix | Có B05, transition cố định của HMM |
| NHHMM transition regressors | Chưa có; B06 logistic không thay thế bảng này |
| Portfolio performance | Có B08 và research portfolio |
| Giá với nền regime | Có |
| Smoothed probabilities | Có, hindsight được cảnh báo; filtered mặc định |
| Transition probability through time | Có marginal forecast alpha_t @ P; chưa có conditional transition matrix P_ij(X_t) biến thiên |
| Confusion/comparison across methods | Có một phần comparison/ARI; chưa thành so sánh đa phương pháp, nhãn được căn chỉnh và kiểm định đầy đủ |
| Cumulative portfolio value | Có |
| Drivers trên sản phẩm | Có panel logistic; bằng chứng suy luận còn yếu |
| Econometric/statistical benchmark | GMM/KMeans là statistical benchmarks; Markov-switching econometric còn thiếu |
| Ít nhất một model nâng cao | Có feature/initializer extensions và logistic phụ; chưa tương đương NHHMM/Bayesian HMM/Markov-switching AR/GARCH |
| Untouched OOS test | Có chia mẫu ban đầu; không thể xác nhận untouched cho toàn bộ phần mở rộng |

## Thứ tự hoàn thiện đề xuất

1. Hồ sơ đa chiều của từng regime: return, volatility, volume/liquidity, duration,
   occupancy theo năm, mức bất định; đặt tên mô tả trung tính cho state chưa có tên.
   Kiểm tra ETH state 0 và feature volume có secular trend trước khi đặt nhãn kinh tế mạnh.
2. Chốt protocol mới: cửa sổ train/validation theo thời gian, rolling/expanding evaluation,
   tiêu chí selection và gán nhãn từ trước; lưu kết quả test cũ như exploratory.
3. Thêm một benchmark Markov-switching AR và một phương pháp change-point.
   So theo cùng thời điểm dữ liệu, persistence, thống kê kinh tế, OOS score phù hợp và
   downstream risk utility; không xếp hạng các likelihood khác feature space.
4. Bổ sung một mô hình nâng cao có mục tiêu rõ: NHHMM nếu muốn bám RQ3/section2.4,
   với giới hạn tham số/regularization và kiểm tra simulation trước. Logistic vẫn là đối chứng,
   không đổi tên logistic thành NHHMM. Đánh giá độ đủ thông tin trước khi diễn giải beta_ij.
5. Hoàn thiện sensitivity/refit uncertainty và kiểm chứng ích lợi tài chính qua nhiều cửa sổ.
   Kết quả không thắng benchmark vẫn được chấp nhận nếu thiết kế và kết luận đúng.
6. Viết paper theo RQ1–RQ5, mỗi câu có giả thuyết, giao thức, bảng/hình, kết luận và giới hạn.
   Dashboard trình bày cùng kết luận này, không chỉ gom các bảng kết quả.

## Nguồn kiểm chứng tại chỗ

- `src/models/selection.py`, `reports.py`, `stability.py`, `inference.py`.
- `src/research/economics.py`, `drivers.py`, `robustness.py`, `trend.py`, `run.py`.
- `dashboard/app.py`, `research_views.py`, `result_service.py`.
- `outputs/tables/B03_model_selection.csv`, `B04_regime_statistics.csv`, `B05_transition_matrix.csv`,
  `B06_drivers.csv`, `B07_hmm_vs_gmm.csv`, `B08_portfolio.csv`.
- `research_economic_labels.csv`, `research_liquidity_profiles.csv`, `research_drivers_metrics.csv`,
  `C2_state_coverage.csv`, `C2_stability_summary.csv` và các bảng research khác.
- `paper/research_report.md`, `config/research.yaml`.
- Kiểm tra trực tiếp trong lượt này: `validate_bundle()` và `research_status()` đều ok,
  không lỗi hash. Không chạy lại huấn luyện hoặc pytest; log gần nhất ghi 169 test đạt
  ở chế độ một luồng, sau chỉnh UI có 67 test liên quan đạt. Những log đó là bằng chứng
  phần mềm, không được quy đổi thành độ chính xác hay điểm chất lượng nghiên cứu.
