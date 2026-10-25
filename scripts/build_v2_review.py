"""Publish the review report and one hash index without rewriting old research results."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'outputs/research_v2'


def markdown(frame):
    def cell(value):
        if isinstance(value, float):
            return f'{value:.6g}'
        return str(value).replace('|', '/')
    header = '| ' + ' | '.join(frame.columns) + ' |'
    rule = '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |'
    return '\n'.join([header, rule] + ['| ' + ' | '.join(map(cell, row)) + ' |' for row in frame.itertuples(index=False, name=None)])


def main():
    out = ROOT / 'reports/v2_review'
    out.mkdir(parents=True, exist_ok=True)
    review = BASE / 'review'
    acceptance = json.loads((BASE / 'technical_acceptance.json').read_text())
    replay = json.loads((BASE / 'reproduction/result.json').read_text())
    numerics = pd.read_csv(review / 'T05_selected_numerics.csv')
    prediction = pd.read_csv(review / 'T05_split_prediction_audit.csv')
    shift = pd.read_csv(review / 'T05_covariate_shift.csv')
    matched = pd.read_csv(review / 'T08_matched_validation_stability.csv')
    economics = pd.read_csv(review / 'T03_economic_summary.csv')
    separation = pd.read_csv(review / 'T03_between_state_separation.csv')
    performance = pd.read_csv(BASE / 'm5/performance.csv')
    performance = performance.loc[performance.scenario.eq('baseline_close_to_close') & performance.fee_rate.eq(.001)]
    ci = pd.read_csv(review / 'T06_paired_uncertainty.csv')
    ci = ci.loc[ci.block_days.eq(21) & ci.metric.eq('Sharpe')]
    rolling = json.loads((review / 'rolling_benchmarks/manifest.json').read_text())
    cleanup = json.loads((out / 'cleanup.json').read_text())
    metadata = {a: json.loads((BASE / f'm2/{a.lower()}_metadata.json').read_text()) for a in ['BTC', 'ETH']}
    selected = pd.DataFrame([{'asset': a, 'K': m['K'], 'candidate': m['candidate_id'],
                              'median_ARI': m['stability']['median_ari'], 'minimum_ARI': m['stability']['minimum_ari'],
                              'initializer_families': m['stability']['eligible_initializer_families'],
                              'stable': m['stability']['stable']} for a, m in metadata.items()])
    index = []
    model_ids={a: {'HMM':m['candidate_id'], 'NHHMM':json.loads((BASE/f'm3_evaluation/{a.lower()}_metadata.json').read_text())['model_run_id']}
               for a,m in metadata.items()}
    last_signal={a:pd.read_csv(BASE/f'm2/{a.lower()}_filtered.csv').iloc[-1] for a in ['BTC','ETH']}
    for folder in [BASE / 'deliverables/tables', BASE / 'deliverables/figures', review]:
        for p in sorted(folder.glob('*')):
            if p.is_file() and p.suffix in ['.csv', '.png']:
                index.append({'path': p.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                              'role': 'original_locked_output' if 'deliverables' in p.parts else 'review_addition',
                              'sample_status': 'historical_exploratory', 'research_confirmation': 'pending',
                              'model_run_ids': model_ids,
                              'data_through_utc': {a:str(s.date_utc) for a,s in last_signal.items()},
                              'as_of_utc': {a:str(s.as_of_utc) for a,s in last_signal.items()},
                              'probability_type': 'filtered for signals; smoothed explicitly hindsight in F02',
                              'units': 'defined by named metric/feature columns and source metadata'})
    cards = {}
    for asset in ['BTC', 'ETH']:
        m = metadata[asset]
        cards[asset] = {
            'RQ1': {'K': m['K'], 'model_run_id': m['candidate_id'], 'selection_sample': 'validation', 'champion_changed': False},
            'RQ2': {'labels': economics.loc[economics.asset.eq(asset), ['state_id', 'economic_label', 'direction', 'risk_profile', 'same_label_blocks_14_21_42']].to_dict('records'),
                    'claim': 'train-only conditional statistics; no forced four labels'},
            'RQ3': {'split_metrics': json.loads(prediction.loc[prediction.asset.eq(asset)].to_json(orient='records')),
                    'claim': 'no confirmed predictive improvement; proxy labels differ from latent truth'},
            'RQ4': {'selected_model_stability': m['stability'],
                    'matched_validation': json.loads(matched.loc[matched.asset.eq(asset)].to_json(orient='records')),
                    'claim': 'HMM superiority not established; rolling comparisons development only'},
            'RQ5': {'net_performance': json.loads(performance.loc[performance.asset.eq(asset)].to_json(orient='records')),
                    'paired_Sharpe_CI_block21': json.loads(ci.loc[ci.asset.eq(asset)].to_json(orient='records')),
                    'claim': 'fixed strategies; conditional block bootstrap; no test tuning'},
            'technical_status': acceptance['technical_status'], 'research_confirmation': 'pending',
        }
    (review / 'RQ_review_cards.json').write_text(json.dumps(cards, indent=2), encoding='utf-8')
    (review / 'artifact_index.json').write_text(json.dumps({'artifacts': index, 'RQ_cards': 'outputs/research_v2/review/RQ_review_cards.json'}, indent=2))
    old = json.loads((review / 'manifest.json').read_text())
    old['files_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in review.iterdir() if p.is_file() and p.name not in ['manifest.json', 'input_snapshot.json']}
    old['rolling_benchmarks_manifest_sha256'] = hashlib.sha256((review / 'rolling_benchmarks/manifest.json').read_bytes()).hexdigest()
    old['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in [
        'src/research_v2/review.py','src/research_v2/rolling_benchmarks.py','scripts/reproduce_v2.py',
        'scripts/build_v2_review.py','docs/V2_REVIEW_PROTOCOL.md']}
    (review / 'manifest.json').write_text(json.dumps(old, indent=2), encoding='utf-8')
    changes={
        'README.md':'V2 entrypoint, actual NHHMM status, RQ1-RQ5 outputs and limits',
        'docs/V2_RUNBOOK.md':'isolated reproduction; prohibit overwrite of locked cohort',
        'docs/V2_REVIEW_PROTOCOL.md':'diagnostic scope and preregistered rolling benchmark extension',
        'docs/V2_HISTORY.md':'Git recovery, archive refs, explicit retention decision',
        'pyproject.toml':'V2 package version and description',
        'requirements-dev.txt':'include pinned V2 runtime dependencies',
        '.gitignore':'ignore cache, temporary replay and export ZIP files',
        '.gitattributes':'preserve exact bytes across Git checkouts for frozen provenance hashes',
        '.github/workflows/verify.yml':'V2 replay/review/tests instead of V1 pipeline',
        'scripts/run_research_v2.py':'refuse mutation of confirmation-locked working tree',
        'scripts/consolidate_repository.py':'one-time root migration and verified Git snapshots; retained by user',
        'scripts/reproduce_v2.py':'13-stage isolated replay, CSV numerical comparisons, automatic temporary-copy cleanup',
        'scripts/restore_history.py':'restore Git archive bytes with SHA-256 verification',
        'scripts/clean_v2.py':'explicit inventory; apply not executed because user chose retention',
        'scripts/build_v2_review.py':'canonical review report, RQ cards and artifact index',
        'dashboard/v2_pages.py':'visible zoom/pan/+/-/reset controls and wheel zoom on every interactive chart',
        'scripts/check_chart_zoom.py':'12 real browser zoom/reset/wheel cases on desktop and mobile',
        'scripts/check_v2_layout.py':'wait for the requested asset/page before measuring rerendered layout',
        'src/research_v2/review.py':'read-only RQ diagnostics, economic separation and portfolio uncertainty',
        'src/research_v2/rolling_benchmarks.py':'120 registered development-only GMM/KMeans fits',
        'src/research_v2/acceptance.py':'numeric/provenance/replay/Git/retention acceptance gates',
        'tests/test_v2_review.py':'eight new tests for pairing, probability, look-ahead and replay comparisons',
    }
    (out/'changes.json').write_text(json.dumps({'files':changes,'champion_refitted':False,
        'legacy_user_decision':cleanup.get('user_decision'),'note':'Review change inventory; Git diff against V1 also includes earlier V2 development.'},indent=2),encoding='utf-8')
    command_scope = ('Đã xóa đúng danh sách đã lưu Git.' if cleanup['apply'] else
                     'Giữ nguyên28 file (79,6MiB) và12 thư mục cache theo lựa chọn rõ ràng của người dùng; không còn chờ phê duyệt. Các file được chỉ mục là retained legacy, không phải kết quả V2 đang dùng.')
    text = f'''# Rà soát và hoàn thiện V2 theo Research Blueprint 02

Nghiệm thu kỹ thuật hiện tại: **{acceptance['technical_status'].upper()}**. Xác nhận nghiên cứu độc lập: **PENDING**.
Đây là báo cáo thay đổi và bằng chứng cho team viết nội dung, không phải bài báo thay team. Không thay champion, split, nhãn, chiến lược hoặc thuật toán đã khóa; không commit/push.

## 1. Repository và thay đổi

- V2 đã được gom về `D:\\AI-Regime-Detection-main`; hai bản source trùng không còn trong working tree. Git giữ commit graph V1, ba archive refs và inventory SHA-256. Các object lịch sử thiếu trong bản local cũ đã được lấy lại từ remote; xem `git_fsck.log` và `repository_history.json`. Không tạo commit mới.
- README, runbook, package version2.0.0, requirements-dev và CI đã chuyển sang V2. Bỏ hướng dẫn mặc định chạy pipeline V1 và phát biểu sai rằng NHHMM chưa có.
- Runner V2 từ chối ghi vào cohort có confirmation lock; `reproduce_v2.py` dùng bản sao tạm, lưu log, kiểm tra số và tự dọn bản sao.
- Dọn file cũ/cache: {command_scope} Danh sách cụ thể ở `cleanup.json`; mọi tài liệu/công cụ/ZIP cũ đều có bản phục hồi Git. M0/protocol và scientific dependencies C1/C2/C3 được giữ; không nhầm dependency với bản ứng dụng V1 trùng.
- Thêm diagnostics RQ1–RQ5, 120 fits rolling đối chứng development, CI backtest và test bảo vệ bootstrap/look-ahead/probabilities/reproduction. Source thuật toán và các kết quả cũ không bị ghi đè.
- Danh sách file chỉnh/thêm cùng lý do ở `changes.json`. Diff Git so V1 còn bao gồm các thay đổi V2 của những lượt trước; không đánh đồng toàn bộ diff đó với thay đổi trong lượt rà soát này. `.gitattributes` giữ nguyên byte để Git không tự đổi line endings làm sai hash.

## 2. RQ1/RQ4 — số state và độ ổn định

{markdown(selected)}

K chính chọn bằng validation LL trong K2/3/4; K5 là sensitivity. BTC có ARI1 trong một họ khởi tạo hợp lệ, **không đạt chứng nhận pooled giữa hai họ**. ETH minimum ARI rất thấp, nên không gọi stable. Pooled/within-initializer, risk MAE/disagreement/Jaccard và ba fold đã có trong T08 gốc; không nới ngưỡng median0,80/min0,50.

Đối chiếu cùng K=4, cùng 630 ngày validation, cùng bộ core train-scaled:

{markdown(matched.loc[matched.K.eq(4), ['asset', 'method', 'valid_fits', 'median_ARI', 'minimum_ARI', 'persistence']])}

HMM có persistence cao hơn trong bảng này nhưng không ổn định seed hơn các đối chứng một cách nhất quán. Persistence cao không tự chứng minh tốt hơn. Bổ sung **{rolling['completed']}/{rolling['planned']} fits**, {rolling['eligible']} hợp lệ, cho GMM/K-means ở fold0/1; fold2 dùng kết quả đã khóa. Không có test trong fit/selection. Xem `T08_rolling_benchmark_stability.csv`, `T08_fold_fit_health.csv` và `T07_matched_validation_LL.csv`; CI trên validation selection sample chỉ mô tả có điều kiện. MS-AR/MS-GARCH dùng return-only; HDBSCAN có noise/adaptor OOS; Page-Hinkley tạo segmentation, không phải recurrent regimes. Không xếp raw LL khác feature spaces.

## 3. RQ2 — economic regimes

{markdown(economics[['asset', 'state_id', 'economic_label', 'direction', 'weighted_effective_days', 'mean_ci_low', 'mean_ci_high', 'volatility_ratio', 'same_label_blocks_14_21_42']])}

Return/volatility/volume/liquidity (Amihud proxy) và conditional contrasts có trong T03. Calm/Stress chỉ gán khi vượt đúng ngưỡng M0; Bull/Bear chưa đủ bằng chứng CI return nên không ép tên. Tên model và State ID vẫn giữ. `T03_economic_summary.csv` bổ sung đầy đủ các biến và kiểm block14/21/42; occupancy theo năm/split nằm ở T08. ESS là weighted sample size, không phải số ngày độc lập; bootstrap điều kiện theo fitted model không bao quát model-selection uncertainty. Amihud không phải order-book depth.

Tỷ phần biến thiên được mô tả bởi khác biệt **mean feature giữa các state**, dùng posterior cố định trên train:

{markdown(separation[['asset', 'feature', 'between_state_mean_variance_share', 'conditional_Holm_contrasts_below_05']])}

Đây là phân rã mô tả, không phải feature importance hoặc xác nhận khác biệt độc lập. Return mean thấp không có nghĩa return volatility giống nhau; state có thể khác về phương sai dù mean return khó phân biệt.

Trên train, BTC được phân tách rõ về RV21 (tỷ phần giữa-state khoảng64%); ETH khác mạnh về log-volume (khoảng80%) và RV21 (khoảng52%). Khác biệt mean return giữa-state rất nhỏ ở cả hai. Vì vậy hiện có cơ sở mạnh hơn cho diễn giải volatility/liquidity/volume regimes so với nhãn Bull/Bear theo xu hướng; riêng dominance volume của ETH còn cần cảnh giác với epoch/exchange-volume effects, không tự coi đó là liquidity regime có nguyên nhân kinh tế đã xác nhận.

## 4. RQ3 — vì sao NHHMM BTC kém HMM?

### Kiểm tra kỹ thuật

{markdown(numerics[['asset', 'converged', 'iterations', 'last_optimizer_success', 'last_gradient_norm', 'probability_error', 'reload_max_error', 'prefix_max_error']])}

Các selected models hội tụ, objective không tăng, probability/transition chuẩn hóa, prefix/save-load khớp trong ngưỡng M0. Không thấy bằng chứng lỗi số học giải thích mức kém. `T05_fit_health.csv` giữ tình trạng cả grid; hội tụ không đồng nghĩa hiệu quả dự báo hay hệ số đáng tin cậy.

### Dữ liệu và đánh giá

{markdown(prediction[['asset', 'split', 'observed_LL_NHHMM_minus_HMM', 'proxy_logloss_NHHMM_minus_HMM', 'state_ARI', 'stress_proxy_entries', 'at_risk_days']])}

BTC: observed predictive LL của NHHMM cao hơn HMM trên train nhưng thấp hơn ở validation và historical test. Đây là dấu hiệu fit không tổng quát tốt; không chứng minh nguyên nhân nhân quả hoặc cho phép chọn lại cấu hình bằng test. Champion NHHMM là lựa chọn tốt nhất trong tập NHHMM đủ điều kiện theo validation, không có quy tắc bảo đảm nó phải thắng HMM đối chứng.

State ARI giữa hai mô hình BTC thấp ngay trên train; khoảng cách train emission means và occupancy lệch rõ trong `T05_train_alignment.csv`. Vì thế proxy next-state log-loss rất lớn còn phản ánh hai mô hình định nghĩa latent states khác nhau. Mapping đã dùng train, không remap trên test để làm đẹp. Observed-data LL (cùng features/scaler/sample) cũng kém ngoài train, nên không thể giải thích toàn bộ bằng proxy target. ETH có state agreement cao hơn nhưng cũng chưa chứng minh cải thiện ngoài mẫu.

Covariate được chọn:

{markdown(shift[['asset', 'split', 'feature', 'train_standardized_mean', 'standard_deviation', 'outside_train_range_share', 'original_missing_share']])}

Amihud BTC không missing trên mẫu đang dùng, nhưng độ phân tán ở validation/test chỉ khoảng0,12–0,13 đơn vị train-standardized so1 trên train. Đây là covariate shift đáng lưu ý, không có bằng chứng lỗi imputation là nguyên nhân. Phân rã loss theo tháng và calibration lưu ở `T05_monthly_loss.csv`/`T05_stress_calibration.csv`. Chưa có historical macro release vintages để chứng minh PIT ở cấp revision.

**Chỉ 2 stress-entry proxy events trên historical test mỗi tài sản**, dưới ngưỡng20; train BTC18 và ETH6 proxy entries cũng ít. Event là target từ filtered HMM, không phải stress ground truth. Expected transition counts/exit screens của NHHMM vẫn được báo riêng ở T05 regressors; chúng không phải p-value. Không phát biểu funding/VIX/DXY/liquidity dự báo stress đáng tin cậy từ dấu beta, Brier nhỏ hoặc vài events. Không sửa/tune NHHMM chỉ để thắng trên test. Hướng cải tiến hợp lệ sau này: đánh giá trên prospective cohort đủ sự kiện, kiểm vintage và replication; nếu thay specification phải mở amendment/cohort riêng.

## 5. RQ5 — backtest sau phí và CI

Baseline10bps/turnover, close-to-close lý tưởng hóa, cùng ngày cho bốn chiến lược:

{markdown(performance[['asset', 'strategy', 'CAGR', 'Sharpe', 'max_drawdown', 'turnover', 'total_cost']])}

Paired Sharpe difference block21 so cả B&H và volatility targeting:

{markdown(ci[['asset', 'strategy', 'reference', 'point', 'ci_low', 'ci_high', 'holm_adjusted_p']])}

Giữ nguyên các trường hợp regime-aware kém benchmark. Không tìm chiến lược thắng trên test. T06 gốc giữ phí5/10/20bps và ba execution scenarios; review bổ sung CI tuyệt đối Sharpe/drawdown/annual turnover và paired differences block14/21/42. Pointwise CI95%; Holm p-value theo asset×strategy×reference cho mỗi metric/block. Bootstrap giữ cặp tín hiệu/lợi suất và phí đã tính; không refit model, không phản ánh toàn bộ selection uncertainty. Annual turnover có đơn vị turnover/năm; bảng gốc ghi tổng turnover mẫu. Drawdown âm, difference dương nghĩa ít giảm hơn.

Ở block21, cả8 CI chênh lệch Sharpe của hai chiến lược regime-aware so hai đối chứng cho BTC/ETH đều chứa0. Chưa có bằng chứng cải thiện Sharpe sau phí trong phép đánh giá có điều kiện này; không lấy một vài điểm estimate thuận lợi để tuyên bố thắng benchmark.

## 6. Dashboard và nghiệm thu

Giữ nguyên phong cách hiện tại. Radar dùng toàn bộ K thật; filtered hiện tại, HMM T+1=`alpha @ P`, NHHMM T+1=`alpha @ P(z_t)`; ngày/as_of UTC rõ ràng. Smoothed chỉ hindsight, không làm tín hiệu backtest. Comparison không đồng nhất State0 giữa BTC/ETH. `unstable` và acknowledge/require-stable không bị xóa.

Biểu đồ giá/regime, xác suất và NAV/drawdown có thanh zoom luôn hiển thị: kéo chọn vùng, +/−, pan, cuộn chuột và reset/nhấp đúp. Chỉ đổi góc nhìn, không thay dữ liệu hoặc kết quả mô hình. Kết quả tương tác thực ở `outputs/research_v2/ui/chart_zoom.json`: {acceptance['details'].get('chart_zoom_cases', 0)} trường hợp desktop/mobile đã được ghi nhận ở lần nghiệm thu này.

- Replay: **{replay['status']}**, {len(replay['stages'])} stage, {len(replay['csv_comparisons'])} CSV so sánh, original artifacts unchanged={replay['original_artifacts_unchanged']}. Fresh fits trong replay={replay['fresh_model_fits']}; các fit cũ dùng checkpoint, không giả là refit toàn bộ hoặc independent replication.
- Pytest: {acceptance['details']['pytest']['tests']} tests; failures/errors={acceptance['details']['pytest']['failures_errors']}; skipped={acceptance['details']['pytest']['skipped']}.
- Browser: {acceptance['details']['browser_checks']} trường hợp có kiểm kích thước/nội dung, hai tài sản/bốn trang/desktop/mobile. Zoom125% là viewport/device emulation, không thao tác menu zoom Chrome.
- Hash model/data/protocol/confirmation lock phải khớp. Bảng/hình T01–T08/F01–F06 cũ giữ nguyên; `outputs/research_v2/review/artifact_index.json` nối tất cả output gốc và bổ sung với SHA-256. `RQ_review_cards.json` cung cấp RQ1–RQ5 cho team viết nội dung.

Research Confirmation **PENDING**: historical test đã xem; chưa có clean-room replication độc lập, prospective sample đủ180 ngày và20 stress entries, hay macro release-vintage verification. Negative research results được giữ trung thực, không coi Technical PASSED là chứng nhận hiệu quả đầu tư.
'''
    (out / 'BAO_CAO_RASOAT_V2.md').write_text(text, encoding='utf-8')
    print(json.dumps({'report': str(out / 'BAO_CAO_RASOAT_V2.md'), 'indexed_artifacts': len(index)}))


if __name__ == '__main__':
    main()
