"""Auditable availability and freshness contract for V2 research features.

Availability timestamps in historical sources are assumptions, not proof of
historical publication vintages. Keep that distinction in exported metadata.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.features.extended import build_extended
from src.utils.config import ROOT, load_config


def validate_keys(frame, keys):
    if frame[keys].isna().any().any() or frame.duplicated(keys).any():
        raise ValueError(f"Missing or duplicate keys: {keys}")


def checked_daily_source(frame, asset, timestamp, columns):
    """No silent duplicate resolution or future-day snapshot acceptance."""
    part = frame.loc[frame.asset.eq(asset)].copy()
    validate_keys(part, ['asset', 'date_utc'])
    dates = pd.to_datetime(part.date_utc, utc=True, errors='raise')
    stamp = pd.to_datetime(part[timestamp], utc=True, errors='raise', format='ISO8601')
    if stamp.isna().any() or ((stamp < dates) | (stamp >= dates + pd.Timedelta(days=1))).any():
        raise ValueError(f"{timestamp} must belong to its UTC observation day")
    # A daily aggregate is finalized at the close, not at its last observation.
    for col in columns:
        part[f'{col}_available_at'] = dates + pd.Timedelta(days=1)
        part[f'{col}_obs_date'] = part.date_utc
    return part


def enforce_availability(frame, features, max_age_days=7):
    """Reject future or missing provenance; stale observations become missing."""
    out = frame.copy()
    decision = pd.to_datetime(out.decision_time_utc, utc=True, errors='raise')
    if decision.isna().any():
        raise ValueError('Invalid decision time')
    rows = []
    for feature in features:
        present = out[feature].notna()
        available = pd.to_datetime(out[f'{feature}_available_at'], utc=True, errors='raise')
        obs = pd.to_datetime(out[f'{feature}_obs_date'], utc=True, errors='raise')
        bad = present & (available.isna() | obs.isna() | (available > decision) | (obs > available))
        if bad.any():
            raise ValueError(f'{feature}: {int(bad.sum())} invalid availability rows')
        stale = present & ((decision - obs).dt.total_seconds() > max_age_days * 86400)
        out.loc[stale, feature] = np.nan
        for split, group in out.groupby('split'):
            rows.append({'asset': out.asset.iloc[0], 'feature': feature, 'split': split,
                         'n': len(group), 'non_null': int(group[feature].notna().sum()),
                         'coverage': float(group[feature].notna().mean()),
                         'stale_removed': int(stale.loc[group.index].sum()),
                         'future_rows': 0, 'availability_basis': 'historical_assumed_release_not_vintage_verified'})
    return out, rows


def build_frame(asset, root=ROOT, cfg=None):
    cfg = cfg or load_config()
    raw = root / 'data/raw'
    core = pd.read_parquet(root / f'data/processed/features_{asset.lower()}.parquet')
    validate_keys(core, ['asset', 'date_utc'])
    # Reject duplicate source records before legacy builder can keep-last them.
    for name in ['macro_daily', 'crypto_market_daily', 'coinmetrics_market_daily']:
        source = pd.read_csv(raw / f'{name}.csv')
        validate_keys(source, ['series', 'date_local'])
        if pd.to_datetime(source.available_at_utc, utc=True, errors='raise').isna().any():
            raise ValueError(f'{name}: missing availability')
    ext, _ = build_extended(core, raw, cfg)
    fields = ['log_return', 'rv14', 'rv21', 'rv30', 'log_dollar_volume', 'amihud_illiq', 'segment_id']
    ext = ext.merge(core[['asset', 'date_utc'] + fields], on=['asset', 'date_utc'], validate='one_to_one')
    for f in fields[:-1]:
        ext[f'{f}_available_at'] = ext.decision_time_utc
        ext[f'{f}_obs_date'] = ext.date_utc
    funding = checked_daily_source(pd.read_csv(raw/'derivatives_daily.csv'), asset,
                                   'last_funding_utc', ['funding_sum'])
    oi = checked_daily_source(pd.read_csv(raw/'open_interest_daily.csv'), asset,
                              'last_snapshot_utc', ['oi_growth_7d'])
    for source, f in [(funding, 'funding_sum'), (oi, 'oi_growth_7d')]:
        ext = ext.merge(source[['date_utc', f'{f}_available_at', f'{f}_obs_date']],
                        on='date_utc', how='left', validate='one_to_one')
    features = fields[:-1] + ['funding_sum', 'oi_growth_7d', 'vix', 'dxy_return_1d',
                            'stablecoin_supply_growth_7d', 'spx_return_1d', 'us10y']
    ext, coverage = enforce_availability(ext, features)
    ext['sample_status'] = 'historical_exploratory'
    return ext, pd.DataFrame(coverage)


def run(root=ROOT):
    out = root / 'outputs/research_v2/m1'
    out.mkdir(parents=True, exist_ok=True)
    inputs = list((root/'data/raw').glob('*.csv')) + list((root/'data/processed').glob('features_*.parquet'))
    inputs += [root/'config/config.yaml',root/'src/features/extended.py',root/'src/research_v2/data.py']
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    coverage, drift, windows = [], [], []
    for asset in ['BTC', 'ETH']:
        frame, cov = build_frame(asset, root)
        frame.to_parquet(out/f'features_{asset.lower()}.parquet', index=False)
        coverage.append(cov)
        train = frame.loc[frame.split.eq('train')]
        # Scale shifts diagnose possible exchange/epoch regimes; no inference of causality.
        base = train.log_dollar_volume
        for split, g in frame.groupby('split'):
            drift.append({'asset':asset, 'split':split, 'n':len(g),
                          'log_volume_mean':g.log_dollar_volume.mean(),
                          'train_standardized_mean_shift':(g.log_dollar_volume.mean()-base.mean())/base.std(ddof=0)})
        for f in cov.feature.unique():
            available_train = train.loc[train[f].notna()]
            start = None if available_train.empty else str(available_train.date_utc.min())
            ntrain = 0 if start is None else int((train.date_utc >= start).sum())
            nval = int((frame.split.eq('validation') & frame[f].notna()).sum())
            windows.append({'asset':asset,'feature':f,'first_train_date':start,'common_window_train_days':ntrain,
                            'validation_observed_days':nval,'full_history_coverage_eligible':float(train[f].notna().mean())>=.8,
                            'common_window_length_eligible':ntrain>=730 and nval>=180})
    pd.concat(coverage).to_csv(out/'coverage.csv', index=False)
    pd.DataFrame(drift).to_csv(out/'volume_drift.csv', index=False)
    pd.DataFrame(windows).to_csv(out/'feature_eligibility.csv', index=False)
    assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
    manifest={'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'passed_structural_time_checks',
              'inputs_unchanged':True,'inputs_sha256':hashes,
              'limitations':['Release times are conservative assumptions, not archived historical vintages.',
                             'Funding daily aggregate does not prove every scheduled payment was captured.',
                             'Liquidity is an Amihud proxy, not order book depth.',
                             'Common-window eligibility is per feature; joint groups must be rechecked.'],
              'files_sha256':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in
                  ['features_btc.parquet','features_eth.parquet','coverage.csv','volume_drift.csv','feature_eligibility.csv']}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'status':manifest['status'],'outputs':str(out),'files':len(manifest['files_sha256'])}))


if __name__ == '__main__':
    run()
