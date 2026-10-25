"""Document the UI change separately from the unchanged scientific experiment."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    out=ROOT/'reports/terminal_design'
    technical=json.loads((ROOT/'outputs/research_v2/technical_acceptance.json').read_text())
    browser=json.loads((out/'acceptance.json').read_text())
    if technical['technical_status']!='passed' or browser['status']!='passed':
        raise ValueError('Do not publish an accepted design report before actual acceptance')
    changes={
        'dashboard/app.py':'Terminal title, UTC/as-of snapshot strip, synchronized BTC/ETH header and sidebar; V2 only.',
        'dashboard/ui.py':'Established moss/ivory/copper palette, readable hierarchy, responsive radar, compact cards and research findings.',
        'dashboard/v2_pages.py':'Keep four-page routing/backtest controls; shared chart zoom/fullscreen, portfolio exposure and conditional uncertainty.',
        'dashboard/v2_overview.py':'Decision-first radar, all K current/T+1 probabilities, price overlay, exact emission explanation and BTC/ETH snapshot.',
        'dashboard/v2_history.py':'Filtered/hindsight history, timeline and tabs for economic profiles, transitions and drivers.',
        'dashboard/v2_comparison.py':'K selection, matched validation seed stability, rolling windows, honest benchmark/NHHMM findings.',
        'dashboard/v2_panels.py':'Verified research panels, real NHHMM matrices/regressors and downloadable T01-T08/F01-F06.',
        'dashboard/v2_charts.py':'Figures use frozen labels, probabilities, CI and units; never refit/relabel.',
        'dashboard/v2_market_art.py':'Real-data OHLC backdrop and BTC/ETH sparklines; no synthetic prices or decorative return claims.',
        'dashboard/v2_service.py':'Verify diagnostic stage hashes and require the same model ID/snapshot for review panels.',
        'tests/test_terminal_dashboard.py':'23 scientific-display and integration tests, including interpretation consistency, real OHLC and collapsed quality warnings.',
        'scripts/check_terminal_design.py':'32 actual desktop/mobile tab/filter/download/transition checks.',
        'scripts/capture_terminal_design.py':'16 before + 16 after screenshots with source hashes.',
        'scripts/check_chart_zoom.py':'Visible charts only, track every chart module; preserve 12 interaction cases.',
        'scripts/check_v2_layout.py':'Track all V2 renderer modules in the existing 48-case layout checks.',
        'src/research_v2/acceptance.py':'Add design/interaction/source/screenshot gates; quantitative research gates unchanged.',
        'scripts/build_terminal_report.py':'Publish verified design/acceptance report, change inventory and before/after links.',
        'README.md':'Document current terminal navigation, interpretation and research evidence downloads.',
    }
    inventory={'files':changes,'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in changes},
               'user_decision':'V2 only; do not restore Baseline selector',
               'model_refit':False,'economic_relabeling':False,'backtest_change':False,'commit_or_push':False}
    (out/'changes.json').write_text(json.dumps(inventory,indent=2))
    text=f'''# Dashboard V2 — Premium Quantitative Research Terminal

Trạng thái: **Technical PASSED** · **Research Confirmation PENDING**.
Đã đọc yêu cầu thiết kế đính kèm và Research Blueprint 02. Người dùng xác nhận chỉ dùng V2; không khôi phục bộ chọn Baseline hoặc giao diện cũ.

## Đối chiếu yêu cầu → giao diện hoàn thiện

| Yêu cầu | Trước | Sau và bằng chứng |
|---|---|---|
| Hiểu current regime / T+1 / reliability nhanh | KPI và bảng xác suất dài | Radar nổi bật, toàn bộ K state thật, current/T+1 song song; cảnh báo unstable/snapshot, không coi posterior là accuracy |
| Overview có bối cảnh thị trường | Thiếu price chart tại Overview | Price + filtered backgrounds; chọn probability overlay, hover giá/state/posterior; khoảng hiển thị chỉ lọc chart |
| RQ2 — khác biệt kinh tế | Chủ yếu bảng | CI plot cho return/RV21/volume/Amihud; tail-risk, occupancy, persistence/duration và timeline; train-only labels giữ nguyên |
| RQ3 — transition và drivers | Bảng NHHMM khó đọc | Fixed HMM heatmap và dynamic NHHMM theo ngày, source/destination controls, conditional vs marginal curves; predictor roles rõ ràng |
| AI explainability | Log-density dataframe | Quan sát thực + z(train), heatmap log emission/prior tái tạo posterior; không gọi là causal attribution |
| RQ1/RQ4 — selection / benchmark | Nhiều bảng mở ngay | K/AIC/BIC/validation plots, matched-sample stability, rolling folds, compact benchmark table, findings; không so raw LL khác feature spaces |
| RQ5 — economic usefulness | NAV và bảng metric | Giữ NAV/drawdown thực, exposure, turnover/costs, paired Sharpe CI và kết luận nghiên cứu; phí/scenario khác không dùng nhầm baseline CI |
| T01–T08 / F01–F06 | Chỉ có trên filesystem | Chọn và tải CSV/PNG/báo cáo từ mỗi trang; download CSV đã đối chiếu SHA-256 với file gốc |
| Desktop/mobile | Đã có responsive cơ bản | Giữ màu xanh rêu/kem/vàng đồng, typography phân cấp, card ít bóng, chọn tài sản nhanh; kiểm 1440/390 và các widths bổ sung |

## Kết quả thực chạy

- Pytest: **{technical['details']['pytest']['tests']} passed**,0 failed/errors/skipped.23 test hiển thị kiểm diễn giải đúng asset/K/phí/scenario, tooltip, OHLC, SVG thật, CI/units, timeline, model-ID guard, selector đồng bộ, NHHMM K, cảnh báo thu gọn và downloads.
- **{technical['details']['browser_checks']}** layout checks, hai tài sản/bốn trang/desktop-tablet-mobile; thêm zoom125% bằng viewport/device emulation.
- **{technical['details']['terminal_interaction_cases']}** terminal interaction cases tại1440px/390px: overlay, CI profile, NHHMM matrix đối chiếu trực tiếp CSV, funding predictor role, hindsight, selector K/BIC, phí và download.
- **{technical['details']['chart_zoom_cases']}** chart zoom cases: +/−, wheel, reset trên desktop/mobile. Toolbar vẫn có pan và fullscreen.
- **{technical['details']['pre_review_artifacts']['checked']}** artifact nghiên cứu trước đó được đối chiếu, **0 thay đổi**. Không fit lại, đổi labels hoặc tinh chỉnh chiến lược. Đây là UI verification; không giả là một lượt fresh fit pipeline hay independent replication.
- **{technical['details']['locked_scientific_input_files']}** source/data/protocol inputs đã khóa còn khớp SHA-256; confirmation lock và backtest giữ nguyên.
- Cổng layout đã phát hiện headline regime thiếu line-height; đã sửa khung chữ và chạy lại,0 trường hợp clipped. Không bỏ hoặc nới điều kiện kiểm tra.
- Source hashes, log/JSON/JUnit nằm trong `outputs/research_v2/` và `reports/terminal_design/acceptance.json`.

## Ảnh trước/sau

Ảnh theo viewport1440×1000 và390×1000; nội dung dài cuộn trong Streamlit. Có16 ảnh trước và16 ảnh sau cho BTC/ETH trên cả bốn trang; thêm ảnh tab kinh tế/transition/drivers trong thư mục này.

| | Trước | Sau |
|---|---|---|
| BTC Overview desktop | [Ảnh trước](before/BTC_1_1440.png) | [Ảnh sau](after/BTC_1_1440.png) |
| BTC Overview mobile | [Ảnh trước](before/BTC_1_390.png) | [Ảnh sau](after/BTC_1_390.png) |
| History desktop | [Ảnh trước](before/BTC_2_1440.png) | [Ảnh sau](after/BTC_2_1440.png) |
| Portfolio mobile | [Ảnh trước](before/BTC_4_390.png) | [Ảnh sau](after/BTC_4_390.png) |

## Cách demo

Mở http://127.0.0.1:8501. Chọn BTC/ETH ở header hoặc sidebar; hai bộ chọn đồng bộ. Overview luôn là snapshot cuối đã xác minh; không gọi là live. Dùng History → Economic Profiles / Transition Analysis / Market Drivers để trình bày RQ2/RQ3; Comparison cho RQ1/RQ4; Portfolio cho RQ5. Cuối mỗi trang mở Research evidence để tải bảng/hình.

## Bổ sung market-studio theo phản hồi thiết kế

Header có ticker BTC/ETH và sparkline45 quan sát thật, biến động1D ghi riêng. Hero xanh rêu đậm có họa tiết52 nến OHLC từ snapshot; không dựng nến ngẫu nhiên. Nền lưới tài chính, typography và bảng xác suất đồng bộ màu. Biểu đồ chính chọn Nến OHLC/Đường giá; state probability vẫn lấy nguyên từ filtered exports.

Các đoạn cảnh báo ổn định/snapshot dài được đưa vào expander “Chất lượng mô hình & phạm vi dữ liệu”; badge UNSTABLE và ngày UTC vẫn hiển thị. Cơ chế require_stable/acknowledge_unstable không đổi. Overview có mục ĐỌC TÍN HIỆU diễn giải state và T+1; toàn bộ RQ1–RQ5 và bằng chứng ở các tab vẫn được giữ. Ảnh ngay trước chỉnh sửa này được lưu riêng ở `reports/market_studio/before/`.

Theo phản hồi về mật độ nội dung, dashboard không dùng banner diễn giải lặp lại ở đầu trang. RQ1–RQ5 được trình bày bằng output tại đúng ngữ cảnh: Radar current/T+1; Economic Profiles và Drivers; Model Selection và Stability; Portfolio sau bộ lọc phí/scenario. Kết luận ngắn nằm cạnh bảng/biểu đồ liên quan; CI chỉ dùng đúng baseline đã xuất, không áp sang phí/scenario khác.

## Giới hạn giữ nguyên

- Chưa đủ bằng chứng ép Bull/Bear; chỉ dùng nhãn kinh tế hiện có từ train. State IDs thuộc từng asset/model riêng.
- HMM/NHHMM chưa được chứng nhận ổn định toàn cục; historical test đã được quan sát. Stress proxy rất ít sự kiện; không coi beta hoặc seed range là CI/nhân quả.
- Macro historical-release vintages chưa được xác minh. Funding/OI và các biến bối cảnh không tự trở thành predictors của model đang chọn.
- CI portfolio điều kiện theo model/tín hiệu cố định. Không che các kết quả thua benchmark hoặc suy diễn Technical PASSED thành hiệu quả đầu tư.
- Không thêm SOL/BNB AI, không thay thuật toán/model/data/backtest, không commit/push. Danh sách file và lý do trong `changes.json`.
'''
    (out/'BAO_CAO_THIET_KE.md').write_text(text,encoding='utf-8')
    print(json.dumps({'report':str(out/'BAO_CAO_THIET_KE.md'),'changed_files':len(changes)}))


if __name__=='__main__':main()
