"""Package only technically accepted V2 evidence; never includes credentials or paper prose."""
import hashlib
import json
from pathlib import Path
import zipfile
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/research_v2'


def main():
    acceptance=json.loads((BASE/'technical_acceptance.json').read_text())
    if acceptance['technical_status']!='passed':raise ValueError('Technical acceptance has not passed')
    reportdir=ROOT/'reports/v2_delivery';reportdir.mkdir(parents=True,exist_ok=True)
    nh=json.loads((BASE/'m3/manifest.json').read_text())
    confirmation=json.loads((BASE/'confirmation_lock.json').read_text())
    comparisons=pd.read_csv(BASE/'m3_evaluation/predictive_comparison.csv')
    performance=pd.read_csv(BASE/'m5/performance.csv')
    overview=[]
    for asset in ['BTC','ETH']:
        m=json.loads((BASE/f'm2/{asset.lower()}_metadata.json').read_text())
        overview.append(f"| {asset} | {m['K']} | {m['stability']['median_ari']:.3f} | {m['stability']['minimum_ari']:.3f} | {m['stability']['eligible_initializer_families']} | {'stable' if m['stability']['stable'] else 'unstable / chưa đủ chứng cứ toàn cục'} |")
    rq3=[]
    for r in comparisons.itertuples():
        rq3.append(f'| {r.asset} | {r.K} | {r.next_state_logloss_difference:.6f} | [{r.bonferroni_two_assets_ci_low:.6f}, {r.bonferroni_two_assets_ci_high:.6f}] | {r.stress_proxy_entry_events} |')
    portfolio=[]
    for r in performance.loc[performance.scenario.eq('baseline_close_to_close')&performance.fee_rate.eq(.001)].itertuples():
        portfolio.append(f'| {r.asset} | {r.strategy} | {r.CAGR:.2%} | {r.Sharpe:.3f} | {r.max_drawdown:.2%} |')
    text=f'''# Bàn giao kỹ thuật Research V2 — Crypto Market Regime Radar

Thời điểm nghiệm thu UTC: {acceptance['checked_at_utc']}. Trạng thái kỹ thuật: **PASSED**. Xác nhận nghiên cứu độc lập: **PENDING**.

Cohort prospective được khóa tại {confirmation['locked_at_utc']}; ngày UTC đầy đủ đầu tiên sau khóa là {confirmation['first_prospective_day_utc']}. Hiện có 0 quan sát dùng cho xác nhận. Hai mốc đánh giá là {confirmation['assessment_dates_utc']['180_daily_observations']} và {confirmation['assessment_dates_utc']['365_daily_observations']}; cần tối thiểu 20 stress-entry events mỗi tài sản, nếu không phải ghi underpowered/pending.

## Phạm vi đã thực chạy

- M0: baseline 357 file và protocol đã khóa trước triển khai.
- M1: kiểm khóa/ngày/as-of/freshness, coverage và eligibility; dữ liệu lõi đến 23/10/2026 UTC. Không thay baseline C1.
- M2: 720 HMM candidates theo 3 folds, RV14/21/30, K2–5, hai initializers, 5 seed; K5 chỉ sensitivity. Thêm 60 candidates bỏ volume trên development. Labels/profiles dùng train, có block 14/21/42 và state occupancy theo năm.
- M3: 20/20 simulation hội tụ, beta=0 khớp HMM; {nh['completed']}/990 NHHMM candidates được xử lý, gồm failures. Có models thật, hệ số, seed dispersion, filtered/smoothed và transition forecast.
- M4: GMM, K-means, MS-AR, online change-point, HDBSCAN và MS-GARCH đã được fit/evaluate; lựa chọn khóa trên development trước historical OOS.
- M5: C3 dùng filtered V2 với xác nhận unstable minh bạch; bốn chiến lược cố định, phí 5/10/20 bps và các execution scenarios.
- M6: Dashboard chỉ còn bộ kết quả mới trên cả bốn trang; bộ chọn phiên và renderer giao diện cũ đã bị loại bỏ. Sidebar, model, giá, history và backtest đồng bộ. Hiển thị đủ K, current/T+1, ngày/as-of, cảnh báo; mobile dùng thẻ xác suất từng state. Giá lấy từ snapshot đã xác minh.
- M7: {acceptance['details']['pytest']['tests']} test đạt, không fail/error/skip; {acceptance['details']['browser_checks']} browser checks đạt cho bộ kết quả hiện tại, gồm kiểm nội dung, không còn bộ chọn cũ và kích thước. T01–T08 và F01–F06 cho cả BTC/ETH có file thực và hash.

## Kết quả ổn định HMM V2

| Tài sản | K | Median ARI | Minimum ARI | Họ khởi tạo có fit hợp lệ | Diễn giải |
|---|---:|---:|---:|---:|---|
{chr(10).join(overview)}

BTC có thể đạt ARI cao trong các fit hợp lệ cùng một họ khởi tạo; điều đó không chứng nhận ổn định giữa các họ. Không ép đủ Bull/Bear/Calm/Stress. Các nhãn không đủ bằng chứng vẫn giữ State ID/canonical label.

## RQ3 — kết quả lịch sử có điều kiện

| Tài sản | K NHHMM | Delta next-state log loss, NHHMM−HMM | CI điều chỉnh cho 2 tài sản | Sự kiện entry proxy trên test |
|---|---:|---:|---|---:|
{chr(10).join(rq3)}

Delta âm có lợi cho NHHMM trong phép so này. Target là filtered argmax của HMM đối chứng, không phải latent ground truth; alignment từ train. CI điều kiện theo model/tín hiệu cố định. Family comparison chỉ so likelihood trên cùng sample window; thiếu coverage/số ngày được ghi rõ. Hệ số và dấu beta không chứng minh quan hệ nhân quả hoặc khả năng dự báo stress độc lập. Xem T05 và RQ result cards để phân biệt claim được số liệu hỗ trợ với phần chưa xác nhận.

## RQ5 — kết quả giữ nguyên sau phí

Baseline close-to-close lý tưởng hóa, phí 10 bps/turnover; có bảng riêng cho next-open và turnover drift.

| Tài sản | Chiến lược | CAGR | Sharpe net | Maximum drawdown |
|---|---|---:|---:|---:|
{chr(10).join(portfolio)}

Primary incremental comparison là so volatility targeting; uncertainty và điều chỉnh Holm ở T06. Không chọn lại chiến lược bằng test để tăng lợi nhuận.

## Cách xem và bàn giao

Mở http://127.0.0.1:8501. Dashboard chỉ có bộ kết quả hiện tại, không còn lựa chọn phiên hoặc màn hình Baseline cũ. Hướng dẫn tái lập trong bản sao riêng: `docs/V2_RUNBOOK.md`; entrypoint: `python scripts/run_research_v2.py --stage all`.

Current HMM probability là alpha_t=P(S_t|X_1:t); T+1=alpha_t×P. NHHMM dùng alpha_t×P(z_t), với z_t đã khả dụng tại thời điểm t. Smoothed có hindsight, tách file và không dùng trong backtest.

Bảng/hình và result cards: `outputs/research_v2/deliverables/`. Log test cuối: `outputs/research_v2/acceptance_pytest_final.log/.xml`. Kiểm kỹ thuật: `outputs/research_v2/technical_acceptance.json`; browser evidence: `outputs/research_v2/ui/acceptance.json`.

Source chính thêm tại `src/research_v2/`, `dashboard/v2_service.py`, `dashboard/v2_pages.py`, scripts V2 và tests V2. File baseline chỉnh: {', '.join(acceptance['details']['changed_baseline_files'])}. Các module C1/C2, model/data baseline và paper giữ nguyên theo hash. Không commit/push.

## Hạn chế còn tồn tại

- Historical test đã được quan sát; V2 là exploratory. Chưa có holdout sau khóa champion/protocol đủ dài và chưa có external replication.
- Macro là current-vintage historical downloads; timestamp bảo thủ không chứng minh dữ liệu đúng theo từng historical release vintage.
- State hiếm, instability, hiệu ứng epoch/volume và lựa chọn model làm tăng uncertainty. Bootstrap conditional không bao quát toàn bộ selection/refit uncertainty.
- HDBSCAN dùng adapter medoid/radius cố định cho OOS. Change-point tạo segment chứ không tạo recurrent regimes. MS-GARCH dùng recursion song song, h0 là zero-mean reference initialization; xem ghi chú benchmark.
- 40 trường hợp UI dùng viewport trực tiếp; 8 trường hợp 125% dùng emulation viewport/device scale, không điều khiển menu zoom của Chrome.
- Chưa có full clean-room rerun của tất cả grids bởi một team khác. Nghiệm thu kỹ thuật không phải xác nhận mô hình hữu ích để giao dịch thật.

Team khác viết phần nội dung học thuật; gói này bàn giao số liệu, phương pháp, bằng chứng và limitations.
'''
    (reportdir/'BAO_CAO_BAN_GIAO_V2.md').write_text(text,encoding='utf-8')
    files=[]
    for folder in ['src','dashboard','config','scripts','tests','data','docs','.streamlit','outputs']:
        for p in (ROOT/folder).rglob('*'):
            if not p.is_file():continue
            parts=p.relative_to(ROOT).parts
            if any(part in ['__pycache__','archive'] for part in parts) or p.suffix in ['.pyc','.pid','.zip']:continue
            if p.name.startswith('local_dashboard.') or p.name=='.env' or 'secret' in p.name.lower():continue
            files.append(p)
    files += [p for p in ROOT.iterdir() if p.is_file() and (p.suffix in ['.py','.md','.txt','.toml'] or p.name in ['.env.example','.gitignore'])]
    for folder in ['reports/m0_lock','reports/blueprint_final_plan','reports/v2_delivery','reports/ui_review_20261025']:
        files += [p for p in (ROOT/folder).glob('*') if p.is_file() and p.suffix not in ['.zip','.png'] and p.name!='package_manifest.json']
    files += list((ROOT/'reports').glob('v2_*specification.md'))+list((ROOT/'reports').glob('v2_*notes.md'))
    files=sorted(set(files));inventory={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    package=ROOT/'reports/Crypto_Market_Regime_Radar_V2_delivery.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as archive:
        for p in files:archive.write(p,p.relative_to(ROOT).as_posix())
        archive.writestr('DELIVERY_MANIFEST.json',json.dumps({'files_sha256':inventory,'independent_confirmation':'pending','excluded':['credentials','virtualenv','git','paper prose','nested archives']},indent=2))
    with zipfile.ZipFile(package) as archive:
        if archive.testzip() is not None:raise ValueError('Bad delivery archive CRC')
        if not all(hashlib.sha256(archive.read(name)).hexdigest()==digest for name,digest in inventory.items()):raise ValueError('Archive member hash mismatch')
    result={'package':package.name,'bytes':package.stat().st_size,'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'files':len(files),'all_members_hash_verified':True}
    (reportdir/'package_manifest.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':main()
