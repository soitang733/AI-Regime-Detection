# Phụ lục thí nghiệm volume ablation — trước fit

Trong phạm vi M1/M2/T08 đã duyệt: kiểm tra giả thuyết state phản ánh epoch/volume bằng cách bỏ log-volume. Không đổi champion hoặc lựa chọn dựa trên test.

BTC/ETH, fold chính train tới05/05/2023 và validation tới24/01/2025. Features chỉ log-return/RV21, scaler train; K2/3/4, seed0–4, initializers kmeans/volatility_quantiles, cùng convergence/occupancy gate M0. 60 candidate. Báo validation persistence, state occupancy và seed ARI trong từngK; **không so raw likelihood2D với3D**. Chỉ báo selected2D bằng validation LL trong2D. Chưa thêm vào tín hiệu portfolio hoặc dashboard champion. Kết quả này không chứng minh quan hệ nhân quả giữa volume và state.
