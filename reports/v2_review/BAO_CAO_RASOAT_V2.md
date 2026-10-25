# Rà soát và hoàn thiện V2 theo Research Blueprint 02

Nghiệm thu kỹ thuật hiện tại: **PASSED**. Xác nhận nghiên cứu độc lập: **PENDING**.
Đây là báo cáo thay đổi và bằng chứng cho team viết nội dung, không phải bài báo thay team. Không thay champion, split, nhãn, chiến lược hoặc thuật toán đã khóa; không commit/push.

## 1. Repository và thay đổi

- V2 đã được gom về `D:\AI-Regime-Detection-main`; hai bản source trùng không còn trong working tree. Git giữ commit graph V1, ba archive refs và inventory SHA-256. Các object lịch sử thiếu trong bản local cũ đã được lấy lại từ remote; xem `git_fsck.log` và `repository_history.json`. Không tạo commit mới.
- README, runbook, package version2.0.0, requirements-dev và CI đã chuyển sang V2. Bỏ hướng dẫn mặc định chạy pipeline V1 và phát biểu sai rằng NHHMM chưa có.
- Runner V2 từ chối ghi vào cohort có confirmation lock; `reproduce_v2.py` dùng bản sao tạm, lưu log, kiểm tra số và tự dọn bản sao.
- Dọn file cũ/cache: Giữ nguyên28 file (79,6MiB) và12 thư mục cache theo lựa chọn rõ ràng của người dùng; không còn chờ phê duyệt. Các file được chỉ mục là retained legacy, không phải kết quả V2 đang dùng. Danh sách cụ thể ở `cleanup.json`; mọi tài liệu/công cụ/ZIP cũ đều có bản phục hồi Git. M0/protocol và scientific dependencies C1/C2/C3 được giữ; không nhầm dependency với bản ứng dụng V1 trùng.
- Thêm diagnostics RQ1–RQ5, 120 fits rolling đối chứng development, CI backtest và test bảo vệ bootstrap/look-ahead/probabilities/reproduction. Source thuật toán và các kết quả cũ không bị ghi đè.
- Danh sách file chỉnh/thêm cùng lý do ở `changes.json`. Diff Git so V1 còn bao gồm các thay đổi V2 của những lượt trước; không đánh đồng toàn bộ diff đó với thay đổi trong lượt rà soát này. `.gitattributes` giữ nguyên byte để Git không tự đổi line endings làm sai hash.

## 2. RQ1/RQ4 — số state và độ ổn định

| asset | K | candidate | median_ARI | minimum_ARI | initializer_families | stable |
| --- | --- | --- | --- | --- | --- | --- |
| BTC | 4 | BTC_f2_rv21_k4_volatility_quantiles_s3 | 1 | 1 | 1 | False |
| ETH | 4 | ETH_f2_rv21_k4_kmeans_s4 | 0.791057 | 0.00833851 | 2 | False |

K chính chọn bằng validation LL trong K2/3/4; K5 là sensitivity. BTC có ARI1 trong một họ khởi tạo hợp lệ, **không đạt chứng nhận pooled giữa hai họ**. ETH minimum ARI rất thấp, nên không gọi stable. Pooled/within-initializer, risk MAE/disagreement/Jaccard và ba fold đã có trong T08 gốc; không nới ngưỡng median0,80/min0,50.

Đối chiếu cùng K=4, cùng 630 ngày validation, cùng bộ core train-scaled:

| asset | method | valid_fits | median_ARI | minimum_ARI | persistence |
| --- | --- | --- | --- | --- | --- |
| BTC | GMM | 5 | 0.948376 | 0.905096 | 0.707154 |
| BTC | KMeans | 5 | 0.964831 | 0.308947 | 0.596184 |
| BTC | HMM | 5 | 1 | 1 | 0.952305 |
| ETH | GMM | 5 | 0.863782 | 0.320754 | 0.83434 |
| ETH | KMeans | 5 | 0.960823 | 0.912626 | 0.779014 |
| ETH | HMM | 10 | 0.791057 | 0.00833851 | 0.974245 |

HMM có persistence cao hơn trong bảng này nhưng không ổn định seed hơn các đối chứng một cách nhất quán. Persistence cao không tự chứng minh tốt hơn. Bổ sung **120/120 fits**, 120 hợp lệ, cho GMM/K-means ở fold0/1; fold2 dùng kết quả đã khóa. Không có test trong fit/selection. Xem `T08_rolling_benchmark_stability.csv`, `T08_fold_fit_health.csv` và `T07_matched_validation_LL.csv`; CI trên validation selection sample chỉ mô tả có điều kiện. MS-AR/MS-GARCH dùng return-only; HDBSCAN có noise/adaptor OOS; Page-Hinkley tạo segmentation, không phải recurrent regimes. Không xếp raw LL khác feature spaces.

## 3. RQ2 — economic regimes

| asset | state_id | economic_label | direction | weighted_effective_days | mean_ci_low | mean_ci_high | volatility_ratio | same_label_blocks_14_21_42 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BTC | 0 | Calm | Uncertain | 437.897 | -0.00259087 | 0.00449515 | 0.528491 | True |
| BTC | 1 | State 1 | Uncertain | 580.788 | -0.00313438 | 0.00379811 | 0.784829 | True |
| BTC | 2 | State 2 | Uncertain | 479.456 | -0.0016817 | 0.00820307 | 0.934639 | True |
| BTC | 3 | Stress | Uncertain | 510.418 | -0.00760764 | 0.00469129 | 1.4692 | True |
| ETH | 0 | State 0 | Uncertain | 523.239 | -0.00487371 | 0.00764578 | 0.981847 | True |
| ETH | 1 | High-Vol | Uncertain | 169.21 | -0.0190518 | 0.0146776 | 1.79543 | True |
| ETH | 2 | Calm | Uncertain | 372.639 | -0.002128 | 0.00763904 | 0.648796 | True |
| ETH | 3 | State 3 | Uncertain | 870.492 | -0.00521531 | 0.00488087 | 0.92402 | True |

Return/volatility/volume/liquidity (Amihud proxy) và conditional contrasts có trong T03. Calm/Stress chỉ gán khi vượt đúng ngưỡng M0; Bull/Bear chưa đủ bằng chứng CI return nên không ép tên. Tên model và State ID vẫn giữ. `T03_economic_summary.csv` bổ sung đầy đủ các biến và kiểm block14/21/42; occupancy theo năm/split nằm ở T08. ESS là weighted sample size, không phải số ngày độc lập; bootstrap điều kiện theo fitted model không bao quát model-selection uncertainty. Amihud không phải order-book depth.

Tỷ phần biến thiên được mô tả bởi khác biệt **mean feature giữa các state**, dùng posterior cố định trên train:

| asset | feature | between_state_mean_variance_share | conditional_Holm_contrasts_below_05 |
| --- | --- | --- | --- |
| BTC | log_return | 0.0019038 | 0 |
| BTC | rv21 | 0.639996 | 6 |
| BTC | log_dollar_volume | 0.0211366 | 0 |
| BTC | amihud_illiq | 0.0189059 | 0 |
| ETH | log_return | 0.000772676 | 0 |
| ETH | rv21 | 0.521573 | 5 |
| ETH | log_dollar_volume | 0.798006 | 4 |
| ETH | amihud_illiq | 0.327056 | 3 |

Đây là phân rã mô tả, không phải feature importance hoặc xác nhận khác biệt độc lập. Return mean thấp không có nghĩa return volatility giống nhau; state có thể khác về phương sai dù mean return khó phân biệt.

Trên train, BTC được phân tách rõ về RV21 (tỷ phần giữa-state khoảng64%); ETH khác mạnh về log-volume (khoảng80%) và RV21 (khoảng52%). Khác biệt mean return giữa-state rất nhỏ ở cả hai. Vì vậy hiện có cơ sở mạnh hơn cho diễn giải volatility/liquidity/volume regimes so với nhãn Bull/Bear theo xu hướng; riêng dominance volume của ETH còn cần cảnh giác với epoch/exchange-volume effects, không tự coi đó là liquidity regime có nguyên nhân kinh tế đã xác nhận.

## 4. RQ3 — vì sao NHHMM BTC kém HMM?

### Kiểm tra kỹ thuật

| asset | converged | iterations | last_optimizer_success | last_gradient_norm | probability_error | reload_max_error | prefix_max_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BTC | True | 22 | True | 1.13235e-07 | 4.44089e-16 | 1.11022e-16 | 0 |
| ETH | True | 30 | True | 1.72709e-07 | 4.44089e-16 | 1.11022e-16 | 0 |

Các selected models hội tụ, objective không tăng, probability/transition chuẩn hóa, prefix/save-load khớp trong ngưỡng M0. Không thấy bằng chứng lỗi số học giải thích mức kém. `T05_fit_health.csv` giữ tình trạng cả grid; hội tụ không đồng nghĩa hiệu quả dự báo hay hệ số đáng tin cậy.

### Dữ liệu và đánh giá

| asset | split | observed_LL_NHHMM_minus_HMM | proxy_logloss_NHHMM_minus_HMM | state_ARI | stress_proxy_entries | at_risk_days |
| --- | --- | --- | --- | --- | --- | --- |
| BTC | train | 0.135263 | 4.91012 | 0.158694 | 18 | 1384 |
| BTC | validation | -0.516934 | 5.07307 | -0.0368072 | 2 | 611 |
| BTC | test | -1.05358 | 7.46713 | 0.203197 | 2 | 611 |
| ETH | train | 0.00501137 | -0.00374875 | 0.992227 | 6 | 1738 |
| ETH | validation | 0.0130918 | 0.116559 | 0.931819 | 1 | 628 |
| ETH | test | -0.0188294 | 0.0516979 | 0.960388 | 2 | 635 |

BTC: observed predictive LL của NHHMM cao hơn HMM trên train nhưng thấp hơn ở validation và historical test. Đây là dấu hiệu fit không tổng quát tốt; không chứng minh nguyên nhân nhân quả hoặc cho phép chọn lại cấu hình bằng test. Champion NHHMM là lựa chọn tốt nhất trong tập NHHMM đủ điều kiện theo validation, không có quy tắc bảo đảm nó phải thắng HMM đối chứng.

State ARI giữa hai mô hình BTC thấp ngay trên train; khoảng cách train emission means và occupancy lệch rõ trong `T05_train_alignment.csv`. Vì thế proxy next-state log-loss rất lớn còn phản ánh hai mô hình định nghĩa latent states khác nhau. Mapping đã dùng train, không remap trên test để làm đẹp. Observed-data LL (cùng features/scaler/sample) cũng kém ngoài train, nên không thể giải thích toàn bộ bằng proxy target. ETH có state agreement cao hơn nhưng cũng chưa chứng minh cải thiện ngoài mẫu.

Covariate được chọn:

| asset | split | feature | train_standardized_mean | standard_deviation | outside_train_range_share | original_missing_share |
| --- | --- | --- | --- | --- | --- | --- |
| BTC | train | amihud_illiq | 9.01799e-17 | 1 | 0 | 0 |
| BTC | validation | amihud_illiq | -0.521201 | 0.126808 | 0 | 0 |
| BTC | test | amihud_illiq | -0.525237 | 0.11917 | 0 | 0 |
| ETH | train | vix | 1.503e-16 | 1 | 0 | 0 |
| ETH | train | dxy_return_1d | 3.38175e-17 | 1 | 0 | 0 |
| ETH | validation | vix | -0.721853 | 0.355257 | 0 | 0 |
| ETH | validation | dxy_return_1d | 0.00287527 | 0.887519 | 0 | 0 |
| ETH | test | vix | -0.323687 | 0.58629 | 0 | 0 |
| ETH | test | dxy_return_1d | -0.0640339 | 0.949682 | 0 | 0 |

Amihud BTC không missing trên mẫu đang dùng, nhưng độ phân tán ở validation/test chỉ khoảng0,12–0,13 đơn vị train-standardized so1 trên train. Đây là covariate shift đáng lưu ý, không có bằng chứng lỗi imputation là nguyên nhân. Phân rã loss theo tháng và calibration lưu ở `T05_monthly_loss.csv`/`T05_stress_calibration.csv`. Chưa có historical macro release vintages để chứng minh PIT ở cấp revision.

**Chỉ 2 stress-entry proxy events trên historical test mỗi tài sản**, dưới ngưỡng20; train BTC18 và ETH6 proxy entries cũng ít. Event là target từ filtered HMM, không phải stress ground truth. Expected transition counts/exit screens của NHHMM vẫn được báo riêng ở T05 regressors; chúng không phải p-value. Không phát biểu funding/VIX/DXY/liquidity dự báo stress đáng tin cậy từ dấu beta, Brier nhỏ hoặc vài events. Không sửa/tune NHHMM chỉ để thắng trên test. Hướng cải tiến hợp lệ sau này: đánh giá trên prospective cohort đủ sự kiện, kiểm vintage và replication; nếu thay specification phải mở amendment/cohort riêng.

## 5. RQ5 — backtest sau phí và CI

Baseline10bps/turnover, close-to-close lý tưởng hóa, cùng ngày cho bốn chiến lược:

| asset | strategy | CAGR | Sharpe | max_drawdown | turnover | total_cost |
| --- | --- | --- | --- | --- | --- | --- |
| BTC | buy_and_hold | -0.136903 | -0.127769 | -0.529718 | 1 | 0.001 |
| BTC | volatility_targeting | -0.127069 | -0.165524 | -0.517271 | 9.09279 | 0.00909279 |
| BTC | regime_defensive | -0.16452 | -0.228076 | -0.550916 | 4 | 0.004 |
| BTC | regime_volatility_targeting | -0.147593 | -0.235694 | -0.533928 | 10.5683 | 0.0105683 |
| ETH | buy_and_hold | -0.171189 | 0.0698438 | -0.675535 | 1 | 0.001 |
| ETH | volatility_targeting | -0.107078 | -0.0176213 | -0.570134 | 16.2623 | 0.0162623 |
| ETH | regime_defensive | -0.185972 | 0.0421451 | -0.67062 | 4 | 0.004 |
| ETH | regime_volatility_targeting | -0.113692 | -0.0342707 | -0.566983 | 17.6236 | 0.0176236 |

Paired Sharpe difference block21 so cả B&H và volatility targeting:

| asset | strategy | reference | point | ci_low | ci_high | holm_adjusted_p |
| --- | --- | --- | --- | --- | --- | --- |
| BTC | regime_defensive | buy_and_hold | -0.100307 | -0.359684 | 0.0667572 | 1 |
| BTC | regime_defensive | volatility_targeting | -0.0625519 | -0.281704 | 0.147195 | 1 |
| BTC | regime_volatility_targeting | buy_and_hold | -0.107924 | -0.447522 | 0.149224 | 1 |
| BTC | regime_volatility_targeting | volatility_targeting | -0.0701695 | -0.220385 | 0.0211638 | 1 |
| ETH | regime_defensive | buy_and_hold | -0.0276986 | -0.112571 | 0.0273236 | 1 |
| ETH | regime_defensive | volatility_targeting | 0.0597665 | -0.274551 | 0.46925 | 1 |
| ETH | regime_volatility_targeting | buy_and_hold | -0.104114 | -0.531314 | 0.229141 | 1 |
| ETH | regime_volatility_targeting | volatility_targeting | -0.0166494 | -0.0728364 | 0.0198917 | 1 |

Giữ nguyên các trường hợp regime-aware kém benchmark. Không tìm chiến lược thắng trên test. T06 gốc giữ phí5/10/20bps và ba execution scenarios; review bổ sung CI tuyệt đối Sharpe/drawdown/annual turnover và paired differences block14/21/42. Pointwise CI95%; Holm p-value theo asset×strategy×reference cho mỗi metric/block. Bootstrap giữ cặp tín hiệu/lợi suất và phí đã tính; không refit model, không phản ánh toàn bộ selection uncertainty. Annual turnover có đơn vị turnover/năm; bảng gốc ghi tổng turnover mẫu. Drawdown âm, difference dương nghĩa ít giảm hơn.

Ở block21, cả8 CI chênh lệch Sharpe của hai chiến lược regime-aware so hai đối chứng cho BTC/ETH đều chứa0. Chưa có bằng chứng cải thiện Sharpe sau phí trong phép đánh giá có điều kiện này; không lấy một vài điểm estimate thuận lợi để tuyên bố thắng benchmark.

## 6. Dashboard và nghiệm thu

Giữ nguyên phong cách hiện tại. Radar dùng toàn bộ K thật; filtered hiện tại, HMM T+1=`alpha @ P`, NHHMM T+1=`alpha @ P(z_t)`; ngày/as_of UTC rõ ràng. Smoothed chỉ hindsight, không làm tín hiệu backtest. Comparison không đồng nhất State0 giữa BTC/ETH. `unstable` và acknowledge/require-stable không bị xóa.

Biểu đồ giá/regime, xác suất và NAV/drawdown có thanh zoom luôn hiển thị: kéo chọn vùng, +/−, pan, cuộn chuột và reset/nhấp đúp. Chỉ đổi góc nhìn, không thay dữ liệu hoặc kết quả mô hình. Kết quả tương tác thực ở `outputs/research_v2/ui/chart_zoom.json`: 12 trường hợp desktop/mobile đã được ghi nhận ở lần nghiệm thu này.

- Replay: **passed**, 13 stage, 257 CSV so sánh, original artifacts unchanged=True. Fresh fits trong replay=0; các fit cũ dùng checkpoint, không giả là refit toàn bộ hoặc independent replication.
- Pytest: 226 tests; failures/errors=0; skipped=0.
- Browser: 48 trường hợp có kiểm kích thước/nội dung, hai tài sản/bốn trang/desktop/mobile. Zoom125% là viewport/device emulation, không thao tác menu zoom Chrome.
- Hash model/data/protocol/confirmation lock phải khớp. Bảng/hình T01–T08/F01–F06 cũ giữ nguyên; `outputs/research_v2/review/artifact_index.json` nối tất cả output gốc và bổ sung với SHA-256. `RQ_review_cards.json` cung cấp RQ1–RQ5 cho team viết nội dung.

Research Confirmation **PENDING**: historical test đã xem; chưa có clean-room replication độc lập, prospective sample đủ180 ngày và20 stress entries, hay macro release-vintage verification. Negative research results được giữ trung thực, không coi Technical PASSED là chứng nhận hiệu quả đầu tư.
