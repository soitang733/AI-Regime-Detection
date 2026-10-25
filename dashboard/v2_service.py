"""Verified V2 view data. No model fitting, strategy tuning, or fallback to baseline."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd

from src.research_v2.handoff import load_hmm, UnstableResearchWarning
from src.utils.config import ROOT


@dataclass
class Context:
    asset: str
    signals: pd.DataFrame
    metadata: dict
    features: pd.DataFrame
    prices: pd.DataFrame
    exported_at: str
    root: Path = ROOT

    @property
    def model_id(self):
        return self.metadata['candidate_id']

    @property
    def through(self):
        return pd.Timestamp(self.signals.date_utc.iloc[-1], tz='UTC')


def manifest(stage, root=ROOT):
    path = root / 'outputs/research_v2' / stage / 'manifest.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('status') not in {'complete', 'outputs_generated', 'passed_structural_time_checks', 'diagnostics_complete'}:
        raise ValueError(f'{stage}: bộ kết quả chưa hoàn tất')
    if not data.get('files_sha256'):
        raise ValueError(f'{stage}: thiếu hash xác minh')
    return data


def verified_path(stage, name, root=ROOT):
    folder = (root / 'outputs/research_v2' / stage).resolve()
    path = (folder / name).resolve()
    if not path.is_relative_to(folder):
        raise ValueError('Đường dẫn artifact không hợp lệ')
    digest = manifest(stage, root)['files_sha256'].get(name)
    if not digest or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError(f'{stage}/{name}: file không khớp manifest')
    return path


def table(stage, name, asset=None, root=ROOT):
    result = pd.read_csv(verified_path(stage, name, root))
    if asset is not None and 'asset' in result:
        result = result.loc[result.asset.eq(asset)].copy()
        if result.empty:
            raise ValueError(f'{stage}/{name}: thiếu {asset}')
    return result


def context(asset, root=ROOT):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UnstableResearchWarning)
        signals, metadata = load_hmm(asset, require_stable=False, acknowledge_unstable=True, root=root)
    features = pd.read_parquet(verified_path('m1', f'features_{asset.lower()}.parquet', root))
    fit_inputs = json.loads(verified_path('m2', 'input_lock.json', root).read_text())['inputs_sha256']
    fit_inputs = {key.replace('\\', '/'): value for key, value in fit_inputs.items()}
    feature_key = f'outputs/research_v2/m1/features_{asset.lower()}.parquet'
    if fit_inputs.get(feature_key) != manifest('m1', root)['files_sha256'][f'features_{asset.lower()}.parquet']:
        raise ValueError('Feature matrix khác phiên dùng khi fit model V2')
    if not features.asset.eq(asset).all() or features.date_utc.duplicated().any():
        raise ValueError('Feature matrix không đúng tài sản hoặc bị trùng ngày')
    if features.date_utc.max() != signals.date_utc.max():
        raise ValueError('Ngày dữ liệu và xác suất V2 không đồng bộ')
    if set(features.dropna(subset=metadata['features']).date_utc) != set(signals.date_utc):
        raise ValueError('Lịch ngày feature và xác suất V2 không khớp')
    name = f'data/raw/{asset.lower()}_ohlcv.csv'
    input_hashes = {key.replace('\\', '/'): value for key, value in manifest('m1', root)['inputs_sha256'].items()}
    expected = input_hashes.get(name)
    path = root / name
    if (root/'outputs/research_v2/view_inputs/manifest.json').exists():
        snapshot = manifest('view_inputs', root)
        if (snapshot['model_run_ids'].get(asset) != metadata['candidate_id']
                or snapshot['source_inputs_sha256'].get(name) != expected):
            raise ValueError('Snapshot giá không thuộc phiên model V2 đang chọn')
        prices = pd.read_parquet(verified_path('view_inputs', f'prices_{asset.lower()}.parquet', root))
    else:
        if not expected or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Giá đã thay đổi sau khi xuất V2; cần bộ inference đồng bộ')
        prices = pd.read_csv(path)
    if prices.date_utc.duplicated().any():
        raise ValueError('Giá có ngày trùng')
    prices = prices.loc[prices.date_utc.isin(signals.date_utc)].copy()
    if set(prices.date_utc) != set(signals.date_utc):
        raise ValueError('Thiếu giá cho lịch sử regime V2')
    return Context(asset, signals, metadata, features, prices,
                   manifest('m2', root)['created_at_utc'], root)


def freshness(through, now=None):
    now = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    now = now.tz_localize('UTC') if now.tzinfo is None else now.tz_convert('UTC')
    through = pd.Timestamp(through)
    through = through.tz_localize('UTC') if through.tzinfo is None else through.tz_convert('UTC')
    lag = int((now.normalize() - pd.Timedelta(days=1) - through.normalize()).days)
    return {'lag_days': max(0, lag), 'status': 'stale' if lag > 0 else 'invalid' if lag < 0 else 'current'}


def probability_rows(ctx):
    last, meta = ctx.signals.iloc[-1], ctx.metadata
    names = {int(r['state_id']): r['economic_label'] for r in meta['economic_labels']}
    return pd.DataFrame([{
        'state_id': i, 'model_label': meta['label_map'][str(i)], 'economic_label': names[i],
        'current': float(last[f'prob_state_{i}']), 'next_day': float(last[f'prob_next_state_{i}']),
        'persistence': float(meta['transition_matrix'][i][i]),
        'expected_days': 1 / (1 - float(meta['transition_matrix'][i][i])),
    } for i in range(meta['K'])])


def portfolio(ctx):
    performance = table('m5', 'performance.csv', ctx.asset, ctx.root)
    nav = table('m5', 'nav.csv', ctx.asset, ctx.root)
    intervals = table('m5', 'incremental_uncertainty.csv', ctx.asset, ctx.root)
    for data in [performance, nav]:
        if not data.model_run_id.eq(ctx.model_id).all():
            raise ValueError('Backtest V2 thuộc model khác phiên đang chọn')
    for row in performance.itertuples():
        part = nav.loc[nav.scenario.eq(row.scenario) & nav.strategy.eq(row.strategy)
                       & np.isclose(nav.fee_rate, row.fee_rate)].sort_values('date_utc')
        if len(part) != row.n or not np.isclose(part.nav.iloc[-1], row.final_nav, atol=1e-10, rtol=0):
            raise ValueError('NAV không khớp bảng hiệu suất V2')
        dates = pd.to_datetime(part.date_utc, utc=True, errors='raise')
        as_of = pd.to_datetime(part.as_of_utc, utc=True, errors='raise')
        if dates.isna().any() or dates.duplicated().any() or as_of.isna().any() or (as_of > dates).any():
            raise ValueError('Ngày NAV hoặc thời điểm khả dụng tín hiệu không hợp lệ')
    return performance, nav, intervals


def dynamic(asset, root=ROOT):
    metadata = json.loads(verified_path('m3_evaluation', f'{asset.lower()}_metadata.json', root).read_text())
    forecasts = table('m3_evaluation', f'{asset.lower()}_latest_forecast.csv', root=root)
    if (metadata['asset'] != asset or len(forecasts) != metadata['K']
            or set(forecasts.state_id) != set(range(metadata['K']))
            or not forecasts.model_run_id.eq(metadata['model_run_id']).all()):
        raise ValueError('Forecast NHHMM không khớp metadata')
    expected_labels = forecasts.state_id.map({int(k): v for k, v in metadata['label_map'].items()})
    if not forecasts.model_label.eq(expected_labels).all() or forecasts.date_utc.nunique() != 1:
        raise ValueError('Forecast NHHMM không khớp state mapping hoặc ngày')
    for column in ['current_probability', 'next_day_probability']:
        p = forecasts[column].to_numpy()
        if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any() or abs(p.sum()-1) > 1e-8:
            raise ValueError('Forecast NHHMM có xác suất không hợp lệ')
    return metadata, forecasts


def review_table(ctx, name):
    """Review diagnostics must refer to the same frozen model shown in the UI."""
    index = json.loads(verified_path('review', 'artifact_index.json', ctx.root).read_text())
    key = f'outputs/research_v2/review/{name}'
    record = next((r for r in index['artifacts'] if r['path'] == key), None)
    if record is None or record['model_run_ids'][ctx.asset]['HMM'] != ctx.model_id:
        raise ValueError('Chẩn đoán nghiên cứu thuộc model khác phiên đang chọn')
    if record['data_through_utc'][ctx.asset] != str(ctx.signals.date_utc.iloc[-1]):
        raise ValueError('Chẩn đoán nghiên cứu khác ngày snapshot')
    return table('review', name, ctx.asset, ctx.root)
