"""Real-artifact regression coverage for version routing and mismatched display data."""
from dataclasses import replace
import hashlib
import json
import shutil

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from bs4 import BeautifulSoup

from dashboard import v2_service as service
from dashboard import ui
from src.utils.config import ROOT

PAGES = ['Overview', 'Regime History', 'Model Comparison', 'Portfolio & Risk']


def radio(at, label):
    return next(item for item in at.radio if item.label == label)


@pytest.mark.parametrize('asset', ['BTC', 'ETH'])
def test_current_model_metadata_matches_every_page_without_version_selector(asset):
    ctx = service.context(asset)
    at = AppTest.from_file(str(ROOT/'dashboard/app.py'), default_timeout=180).run()
    assert all(item.label != 'Phiên kết quả' for item in at.radio)
    radio(at, 'Tài sản').set_value(asset).run()
    for page in PAGES:
        radio(at, 'Trang').set_value(page).run()
        assert not at.exception and not at.error
        sidebar = ' '.join(item.value for item in at.sidebar.caption)
        assert f'Gaussian HMM · K = {ctx.metadata["K"]}' in sidebar
        assert 'cập nhật mỗi ngày' not in ' '.join(item.value for item in at.markdown)
        hero = next(item.value for item in at.markdown if "class='hero'" in item.value)
        assert f'{asset} ' in hero and f'K={ctx.metadata["K"]}' in hero
        assert not any('Phiên Baseline' in item.value for item in at.caption)


def test_stale_legacy_session_state_cannot_restore_old_dashboard():
    at = AppTest.from_file(str(ROOT/'dashboard/app.py'), default_timeout=180)
    at.session_state['result_version'] = 'Baseline'
    at.run()
    assert all(item.label != 'Phiên kết quả' for item in at.radio)
    for asset in ['BTC', 'ETH']:
        radio(at, 'Tài sản').set_value(asset).run()
        assert not at.exception and not at.error
        k = service.context(asset).metadata['K']
        assert any(f'Gaussian HMM · K = {k}' in item.value for item in at.sidebar.caption)


def test_missing_v2_stays_on_v2_without_silent_baseline(monkeypatch):
    def unavailable(*args, **kwargs):
        raise ValueError('controlled missing-artifact regression')
    monkeypatch.setattr(service, 'context', unavailable)
    at = AppTest.from_file(str(ROOT/'dashboard/app.py'), default_timeout=180).run()
    assert all(item.label != 'Phiên kết quả' for item in at.radio)
    assert at.error and not at.exception
    assert not any('Phiên Baseline' in item.value for item in at.caption)


@pytest.mark.parametrize('asset', ['BTC', 'ETH'])
def test_context_forecasts_and_portfolio_share_actual_model(asset):
    ctx = service.context(asset)
    rows = service.probability_rows(ctx)
    assert len(rows) == ctx.metadata['K']
    assert np.isclose(rows.current.sum(), 1) and np.isclose(rows.next_day.sum(), 1)
    performance, nav, _ = service.portfolio(ctx)
    assert performance.model_run_id.eq(ctx.model_id).all() and nav.model_run_id.eq(ctx.model_id).all()
    metadata, dynamic = service.dynamic(asset)
    assert len(dynamic) == metadata['K']


def test_reject_backtest_from_other_model_even_with_updated_hash(tmp_path):
    ctx = service.context('BTC')
    source = ROOT/'outputs/research_v2/m5'
    dest = tmp_path/'outputs/research_v2/m5'
    dest.mkdir(parents=True)
    for name in ['manifest.json', 'performance.csv', 'nav.csv', 'incremental_uncertainty.csv']:
        shutil.copy2(source/name, dest/name)
    frame = pd.read_csv(dest/'performance.csv')
    frame.loc[frame.asset.eq('BTC'), 'model_run_id'] = 'wrong-version'
    frame.to_csv(dest/'performance.csv', index=False)
    manifest = json.loads((dest/'manifest.json').read_text())
    manifest['files_sha256']['performance.csv'] = hashlib.sha256((dest/'performance.csv').read_bytes()).hexdigest()
    (dest/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='model khác'):
        service.portfolio(replace(ctx, root=tmp_path))


def test_freshness_uses_closed_utc_candle_not_local_today():
    assert service.freshness('2026-10-23', '2026-10-24T23:59:59Z')['status'] == 'current'
    assert service.freshness('2026-10-23', '2026-10-25T00:00:00Z')['lag_days'] == 1


def test_historical_view_uses_verified_snapshot_after_raw_refresh(tmp_path):
    for stage, names in {
        'm1': ['manifest.json', 'features_btc.parquet'],
        'm2': ['manifest.json', 'input_lock.json', 'btc_metadata.json', 'btc_filtered.csv', 'btc.joblib'],
        'view_inputs': ['manifest.json', 'prices_btc.parquet'],
    }.items():
        target = tmp_path/'outputs/research_v2'/stage
        target.mkdir(parents=True)
        for name in names:
            shutil.copy2(ROOT/'outputs/research_v2'/stage/name, target/name)
    raw = tmp_path/'data/raw'
    raw.mkdir(parents=True)
    # Adversarial refresh in an isolated fixture; no synthetic value enters research outputs.
    (raw/'btc_ohlcv.csv').write_text('date_utc,close\n2099-01-01,1\n')
    ctx = service.context('BTC', tmp_path)
    assert ctx.prices.date_utc.max() == ctx.signals.date_utc.max()
    assert not ctx.prices.date_utc.eq('2099-01-01').any()
    manifest_path = tmp_path/'outputs/research_v2/view_inputs/manifest.json'
    metadata = json.loads(manifest_path.read_text())
    metadata['model_run_ids']['BTC'] = 'other-model'
    manifest_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match='Snapshot giá'):
        service.context('BTC', tmp_path)
    shutil.copy2(ROOT/'outputs/research_v2/view_inputs/manifest.json', manifest_path)
    features_path = tmp_path/'outputs/research_v2/m1/features_btc.parquet'
    features = pd.read_parquet(features_path)
    features.loc[0, 'log_return'] = 99  # Adversarial fixture: correctly hashed but not the fitted input.
    features.to_parquet(features_path, index=False)
    m1path = tmp_path/'outputs/research_v2/m1/manifest.json'
    m1 = json.loads(m1path.read_text())
    m1['files_sha256']['features_btc.parquet'] = hashlib.sha256(features_path.read_bytes()).hexdigest()
    m1path.write_text(json.dumps(m1))
    with pytest.raises(ValueError, match='Feature matrix khác phiên'):
        service.context('BTC', tmp_path)


@pytest.mark.parametrize('asset', ['BTC', 'ETH'])
def test_v2_portfolio_controls_match_exported_results(asset):
    performance, _, _ = service.portfolio(service.context(asset))
    at = AppTest.from_file(str(ROOT/'dashboard/app.py'), default_timeout=180).run()
    radio(at, 'Tài sản').set_value(asset).run()
    radio(at, 'Trang').set_value('Portfolio & Risk').run()
    for scenario, fee in [('baseline_close_to_close', .001), ('crosscheck_drift_adjusted', .0005),
                           ('crosscheck_next_open', .002)]:
        next(s for s in at.selectbox if s.label == 'Kịch bản thực thi').set_value(scenario).run()
        next(s for s in at.selectbox if s.label == 'Phí trên turnover').set_value(fee).run()
        assert not at.exception and not at.error
        row = performance.loc[performance.strategy.eq('regime_defensive') & performance.scenario.eq(scenario)
                              & np.isclose(performance.fee_rate, fee)].iloc[0]
        cards = [card for md in at.markdown for card in BeautifulSoup(md.value, 'html.parser').select('.kpi')]
        nav = next(card.select_one('.v').get_text() for card in cards
                   if card.select_one('.l > span').get_text() == 'NAV cuối')
        assert nav == ui.num(row.final_nav, 4)
        if scenario != 'baseline_close_to_close':
            assert any('không áp khoảng tin cậy' in item.value for item in at.info)


def test_v2_history_smoothed_and_empty_state_selection_are_explicit():
    at = AppTest.from_file(str(ROOT/'dashboard/app.py'), default_timeout=180).run()
    radio(at, 'Trang').set_value('Regime History').run()
    mode = radio(at, 'Loại xác suất')
    assert mode.value.startswith('Filtered')
    mode.set_value(mode.options[1]).run()
    assert not at.exception and any('Hindsight' in warning.value for warning in at.warning)
    at.multiselect[0].set_value([]).run()
    assert not at.exception and any('Chọn ít nhất' in item.value for item in at.info)
