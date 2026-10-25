"""Development-only matched rolling benchmark extension; no historical test access."""
import hashlib
import itertools
import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from src.research_v2.hmm import FOLDS
from src.utils.config import ROOT


def development_fold(frame, fold):
    end, valend = FOLDS[fold]
    # Explicitly discard test before building any training or validation array.
    frame = frame.loc[frame.split.ne('test') & frame.date_utc.le(valend)].copy()
    frame['split'] = np.where(frame.date_utc.le(end), 'train', 'validation')
    if not len(frame) or not frame.split.eq('validation').any():
        raise ValueError('Empty development fold')
    return frame


def run():
    base = ROOT / 'outputs/research_v2'
    out = base / 'review/rolling_benchmarks'
    out.mkdir(parents=True, exist_ok=True)
    grid = [{'asset': a, 'fold': f, 'K': k, 'seed': s, 'method': m,
             'id': f'{a}_f{f}_{m}_k{k}_s{s}'}
            for a, f, k, s, m in itertools.product(['BTC', 'ETH'], [0, 1], [2, 3, 4], range(5), ['GMM', 'KMeans'])]
    lock = {'candidates': grid, 'inputs_sha256': {
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in [
            'docs/V2_REVIEW_PROTOCOL.md', 'src/research_v2/rolling_benchmarks.py',
            'outputs/research_v2/m1/features_btc.parquet', 'outputs/research_v2/m1/features_eth.parquet']}}
    registry = out / 'registry.json'
    if registry.exists():
        old = json.loads(registry.read_text())
        if old['candidates'] != grid or old['inputs_sha256'] != lock['inputs_sha256']:
            raise ValueError('Rolling benchmark inputs changed; do not reuse checkpoints')
    else:
        registry.write_text(json.dumps({**lock, 'registered_before_fit_utc': datetime.now(timezone.utc).isoformat()}, indent=2))
    frames = {a: pd.read_parquet(base / f'm1/features_{a.lower()}.parquet') for a in ['BTC', 'ETH']}
    rows = []
    for spec in grid:
        record = out / f"{spec['id']}.json"
        if record.exists():
            rows.append(json.loads(record.read_text()))
            continue
        frame = development_fold(frames[spec['asset']], spec['fold'])
        cols = ['log_return', 'rv21', 'log_dollar_volume']
        train = frame.split.eq('train').to_numpy()
        scaler = StandardScaler().fit(frame.loc[train, cols])
        x = scaler.transform(frame[cols])
        row = {**spec, 'eligible': False, 'train_days': int(train.sum()), 'validation_days': int((~train).sum()),
               'last_date_utc': frame.date_utc.max(), 'sample': 'development only', 'test_used': False}
        try:
            if spec['method'] == 'GMM':
                model = GaussianMixture(spec['K'], covariance_type='diag', n_init=1, max_iter=500,
                                        tol=.001, reg_covar=1e-6, random_state=spec['seed']).fit(x[train])
                row.update(eligible=bool(model.converged_), validation_log_score=float(model.score_samples(x[~train]).mean()))
            else:
                model = KMeans(spec['K'], n_init=10, random_state=spec['seed']).fit(x[train])
                row.update(eligible=True, train_inertia=float(model.inertia_))
            labels = model.predict(x[~train])
            row['persistence'] = float((labels[1:] == labels[:-1]).mean())
            row['min_validation_share'] = float(np.bincount(labels, minlength=spec['K']).min() / len(labels))
            if not row['eligible']:
                row['reason'] = 'nonconvergence'
            np.savez_compressed(out / f"{spec['id']}.npz", states=labels)
            joblib.dump({'model': model, 'scaler': scaler, 'metadata': row}, out / f"{spec['id']}.joblib")
        except (ValueError, FloatingPointError) as exc:
            row['reason'] = str(exc)
        record.write_text(json.dumps(row, indent=2))
        rows.append(row)
    fits = pd.DataFrame(rows)
    fits.to_csv(out / 'candidate_results.csv', index=False)
    stability = []
    for (asset, fold, k, method), group in fits.groupby(['asset', 'fold', 'K', 'method']):
        valid = group.loc[group.eligible]
        states = [np.load(out / f'{cid}.npz')['states'] for cid in valid.id]
        aris = [adjusted_rand_score(a, b) for a, b in itertools.combinations(states, 2)]
        stability.append({'asset': asset, 'fold': fold, 'K': k, 'method': method, 'valid_fits': len(valid),
                          'median_ARI': np.median(aris) if aris else None, 'minimum_ARI': min(aris) if aris else None,
                          'persistence': valid.persistence.mean(), 'sample': 'matched development validation',
                          'feature_space': 'train-scaled log_return, rv21, log_dollar_volume'})
    pd.DataFrame(stability).to_csv(base / 'review/T08_rolling_benchmark_stability.csv', index=False)
    (out / 'manifest.json').write_text(json.dumps({
        'planned': 120, 'completed': len(fits), 'eligible': int(fits.eligible.sum()),
        'test_used': False, 'champion_changed': False,
        'files_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.name != 'manifest.json'}}, indent=2))
    print(json.dumps({'completed': len(fits), 'eligible': int(fits.eligible.sum()), 'test_used': False}))


if __name__ == '__main__':
    run()
