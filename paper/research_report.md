# AI Crypto Market Regime Detection — Báo cáo kết quả V2

**Phiên bản kết quả:** V2

**Dữ liệu lõi:** Binance Spot daily BTC/USDT và ETH/USDT, đến hết nến UTC 23/10/2026

**Trạng thái:** Technical PASSED; Research Confirmation PENDING

## Tóm tắt

Nghiên cứu nhận diện trạng thái ẩn của BTC và ETH bằng Gaussian HMM, mở rộng xác suất chuyển trạng thái bằng non-homogeneous HMM (NHHMM), so sánh benchmark và đánh giá giá trị kinh tế của regime signal. Mẫu được chia theo thời gian thành train, validation và historical test. Cấu hình chỉ được chọn trên train/validation; test không được dùng để chọn lại mô hình.

V2 chọn **K=4 cho cả BTC và ETH**. Đây là kết quả của protocol, không phải ép đủ bốn tên Bull/Bear/Calm/Stress. Nhãn kinh tế chỉ được gán khi thống kê train thỏa điều kiện định trước. BTC có Calm và Stress; ETH có Calm, High-Vol và hai state trung tính. Chưa đủ bằng chứng gán Bull/Bear.

NHHMM đã được triển khai và kiểm tra kỹ thuật, nhưng **chưa chứng minh cải thiện ngoài mẫu so với HMM đồng nhất**. Historical test chỉ có hai stress-entry proxy events cho mỗi tài sản, không đủ để kết luận mạnh về funding rate, VIX, DXY, volume hoặc liquidity.

## Protocol và nguồn kết quả

- Biến lõi: daily log return, RV21 và log dollar volume.
- Chuẩn hóa được fit trên train rồi giữ nguyên trên validation/test.
- Model selection dùng validation predictive log likelihood, kèm hội tụ, occupancy, BIC và stability.
- K thuộc {2, 3, 4}; K=5 chỉ là sensitivity.
- Dashboard/backtest chỉ dùng filtered probability; smoothed chỉ để hindsight.
- HMM T+1: `alpha_t @ P`; NHHMM T+1: `alpha_t @ P(z_t)` với dữ liệu khả dụng tại t.
- Nhãn kinh tế suy ra trên train bằng posterior-weighted statistics và moving-block bootstrap.
- Historical test đã được quan sát trong quá trình hoàn thiện V2, nên kết quả vẫn là exploratory.

Nguồn chuẩn là `outputs/research_v2/deliverables/tables/T01–T08`, metadata trong `outputs/research_v2/m2`, audit trong `outputs/research_v2/review` và hình F01–F06.

## RQ1 — Số trạng thái

| Tài sản | K | Model ID | RV | Khởi tạo | Validation log score |
| --- | ---: | --- | ---: | --- | ---: |
| BTC | 4 | `BTC_f2_rv21_k4_volatility_quantiles_s3` | 21 | volatility quantiles | -2,387947 |
| ETH | 4 | `ETH_f2_rv21_k4_kmeans_s4` | 21 | K-means | -2,192518 |

**Kết luận RQ1:** K=4 là lựa chọn phát triển cho cả hai tài sản theo protocol V2. K=4 không đồng nghĩa bốn state đều có thể mang bốn nhãn kinh tế. K=5 và RV14/RV30 chỉ là robustness/sensitivity.

## RQ2 — Ý nghĩa kinh tế của regime

| Tài sản | State | Nhãn model | Nhãn kinh tế | Mean log return/ngày | Volatility ratio | Diễn giải |
| --- | ---: | --- | --- | ---: | ---: | --- |
| BTC | 0 | Low-Vol | Calm | 0,1147% | 0,5285 | Biến động thấp có bằng chứng |
| BTC | 1 | State 1 | State 1 | 0,0180% | 0,7848 | Chưa đủ bằng chứng đặt tên |
| BTC | 2 | State 2 | State 2 | 0,2874% | 0,9346 | Mean CI chứa 0; không gán Bull |
| BTC | 3 | High-Vol | Stress | -0,1740% | 1,4692 | Volatility và left-tail risk cao |
| ETH | 0 | State 0 | State 0 | 0,1190% | 0,9818 | Trung tính theo tiêu chí hiện hành |
| ETH | 1 | High-Vol | High-Vol | -0,0770% | 1,7954 | Volatility cao; tail CI chưa đủ gọi Stress |
| ETH | 2 | Low-Vol | Calm | 0,2745% | 0,6488 | Biến động thấp có bằng chứng |
| ETH | 3 | State 3 | State 3 | -0,0740% | 0,9240 | Chưa đủ bằng chứng đặt tên |

Mean-return CI của mọi state đều chứa 0, nên V2 không xác nhận Bull/Bear. Regime phân tách rõ hơn theo volatility và tail risk. Liquidity dùng Amihud từ daily quote volume, chỉ là proxy chứ không phải spread/order-book depth.

## RQ3 — NHHMM và dự báo chuyển Stress

V2 triển khai NHHMM thật với transition matrix biến thiên theo covariates. Recovery mô phỏng, hội tụ, save/load, tổng xác suất và trường hợp beta=0 khớp HMM đều đã qua kiểm tra. Đó là nghiệm thu kỹ thuật, không phải bằng chứng predictive superiority.

| Tài sản | Split | Observed LL delta NHHMM−HMM | Brier NHHMM | Brier HMM | Stress-entry proxy events |
| --- | --- | ---: | ---: | ---: | ---: |
| BTC | validation | -0,516934 | — | — | 2 |
| BTC | historical test | -1,053583 | 0,003445 | 0,003296 | 2 |
| ETH | validation | 0,013092 | — | — | 1 |
| ETH | historical test | -0,018829 | 0,008682 | 0,003616 | 2 |

Delta LL âm nghĩa là NHHMM kém HMM trong phép so tương ứng. Trên historical test, NHHMM kém HMM ở cả hai tài sản; Brier cũng không tốt hơn. PR-AUC không đủ tin cậy khi mỗi test chỉ có hai event.

Target là proxy từ filtered next-state argmax của HMM đối chứng, không phải latent ground truth. Không split nào đạt ngưỡng sàng lọc 20 stress-entry events. Vì vậy:

- chưa có bằng chứng NHHMM vượt HMM ngoài mẫu;
- chưa thể kết luận funding, volume, VIX, DXY hay liquidity dự báo Stress đáng tin cậy;
- beta thể hiện association có điều kiện, không phải p-value hay quan hệ nhân quả;
- không được đổi specification theo test để làm đẹp kết quả.

**Kết luận RQ3:** NHHMM đã triển khai và technically valid, nhưng research confirmation về predictive improvement vẫn **PENDING**. Cần prospective cohort đủ Stress events và dữ liệu macro theo historical vintage.

## RQ4 — Stability và benchmark

| Tài sản | K | Valid fits | Median ARI | Minimum ARI | Eligible initializer families | Kết luận |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BTC | 4 | 5 | 1,0000 | 1,0000 | 1 | Chưa ổn định toàn cục |
| ETH | 4 | 10 | 0,7911 | 0,0083 | 2 | Unstable |

BTC nhất quán trong họ volatility-quantile đủ điều kiện, nhưng chỉ một initializer family hợp lệ nên chưa chứng minh stability toàn cục. ETH nhạy với initialization: median ARI tương đối cao nhưng minimum ARI gần 0. Cả hai model vì thế giữ cảnh báo `unstable`.

HMM được đối chiếu với GMM, K-means, MS-AR, online change-point, HDBSCAN và MS-GARCH bằng metric phù hợp. K-means không có generative likelihood nên không xếp hạng trực tiếp bằng log score với HMM/GMM. Không có latent-state ground truth; ARI không phải độ chính xác Bull/Bear.

**Kết luận RQ4:** HMM tạo regime persistent và diễn giải được, nhưng chưa đạt ngưỡng stability nghiên cứu. Kết quả không hỗ trợ tuyên bố chung rằng HMM luôn tốt hơn mọi benchmark.

## RQ5 — Giá trị kinh tế

Historical test dùng cùng lịch tín hiệu, phí 0,1%, cash return bằng 0, không leverage; rule và tham số được khóa trước test.

| Tài sản | Chiến lược | CAGR | Ann. volatility | Sharpe | Max drawdown | Total cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| BTC | Buy-and-Hold | -13,69% | 42,99% | -0,128 | -52,97% | 0,10% |
| BTC | Volatility Targeting | -12,71% | 38,14% | -0,166 | -51,73% | 0,91% |
| BTC | Regime Defensive | -16,45% | 41,30% | -0,228 | -55,09% | 0,40% |
| BTC | Regime + Vol Target | -14,76% | 37,64% | -0,236 | -53,39% | 1,06% |
| ETH | Buy-and-Hold | -17,12% | 69,08% | 0,070 | -67,55% | 0,10% |
| ETH | Volatility Targeting | -10,71% | 46,16% | -0,018 | -57,01% | 1,63% |
| ETH | Regime Defensive | -18,60% | 68,90% | 0,042 | -67,06% | 0,40% |
| ETH | Regime + Vol Target | -11,37% | 46,11% | -0,034 | -56,70% | 1,76% |

Volatility targeting giảm volatility/drawdown trong mẫu này, đặc biệt với ETH, nhưng Sharpe không vượt Buy-and-Hold. Regime Defensive không cải thiện kết quả sau phí; chiến lược kết hợp cũng không chứng minh alpha. T06 bootstrap intervals là conditional/exploratory.

**Kết luận RQ5:** chưa có bằng chứng regime probability cải thiện Sharpe hoặc lợi nhuận sau phí. Tác dụng giảm rủi ro quan sát được chủ yếu đến từ volatility targeting, không thể quy riêng cho regime signal.

## Product output — Crypto Market Regime Radar

Dashboard V2 hiển thị current filtered probability của toàn bộ K state, nhãn model/economic label, forecast T+1, history, persistence, transition/drivers, BTC–ETH comparison, backtest sau phí, ngày UTC/`as_of_utc` và cảnh báo `unstable`. State ID của BTC không bị coi là cùng nghĩa với State ID tương ứng của ETH. Smoothed probability chỉ dùng trong hindsight, không dùng làm tín hiệu. Đây là công cụ nhận diện regime, không phải dự báo giá hay khuyến nghị đầu tư.

## Đối chiếu thử nghiệm cũ

`HMM_structured K=5`, trend-HMM 5 chiều và logistic transition proxy thuộc giai đoạn exploratory trước V2. Chúng được giữ trong lịch sử Git/artifacts để audit và robustness, nhưng **không phải model hiện hành và không dùng cho kết luận chính**. Bản nộp lấy bảng/hình chính từ T01–T08/F01–F06 V2.

## Hạn chế và kết luận chung

- HMM BTC/ETH chưa được xác nhận ổn định toàn cục.
- Economic-label intervals có điều kiện theo fitted model, chưa bao trọn model-selection uncertainty.
- Không đủ bằng chứng gán Bull/Bear.
- NHHMM không vượt HMM ngoài mẫu; Stress events quá ít.
- Macro histories chưa phải fully vintage-real-time database.
- Quote-volume/Amihud chỉ là liquidity proxy.
- Historical test đã được quan sát; cần prospective data để xác nhận độc lập.
- Backtest chưa chứng minh regime signal tạo alpha sau phí.

V2 trả lời RQ1–RQ5 ở mức trung thực: pipeline và output hoàn chỉnh về kỹ thuật, nhưng stability, NHHMM superiority và economic alpha chưa được xác nhận. Trạng thái đúng là **Technical PASSED / Research Confirmation PENDING**.

## Danh mục output

- T01: descriptive statistics.
- T02: model selection K/seed/initializer/window.
- T03: regime profiles, labels và conditional contrasts.
- T04: transition matrices.
- T05: NHHMM regressors, coverage, failures và predictive comparison.
- T06: portfolio performance và uncertainty.
- T07: benchmark comparison.
- T08: seed/window/label/occupancy sensitivity.
- F01–F06: price-regime, probabilities, dynamic transitions, agreement, portfolio NAV và occupancy.

## Tài liệu tham khảo

1. Hamilton, J. D. (1989). *Econometrica*, 57(2), 357–384.
2. Rabiner, L. R. (1989). *Proceedings of the IEEE*, 77(2), 257–286.
3. Giudici, P., & Abu-Hashish, I. (2020). *Quality and Reliability Engineering International*.
4. Figà-Talamanca, G., Focardi, S., & Patacca, M. (2021). *North American Journal of Economics and Finance*, 57, 101425.
