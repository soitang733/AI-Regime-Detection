"""Read-only model diagnostics; never selects, refits or replaces a champion."""
from __future__ import annotations

import hashlib
import itertools
import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score, average_precision_score
from statsmodels.stats.multitest import multipletests

from src.models.inference import infer, sequence_starts
from src.research.economics import moving_blocks
from src.research_v2.hmm import FOLDS
from src.research_v2.nhhmm_run import FAMILIES, prepare
from src.utils.config import ROOT

BASE = ROOT / 'outputs/research_v2'


def probability_error(values):
    values = np.asarray(values)
    if not np.isfinite(values).all() or values.min() < -1e-10 or values.max() > 1 + 1e-10:
        raise ValueError('Invalid probabilities')
    error = float(np.abs(values.sum(axis=-1) - 1).max())
    if error > 1e-8:
        raise ValueError('Probabilities do not sum to one')
    return error


def paired_interval(left, right, indices):
    """Paired arithmetic score difference; positive means left is larger."""
    delta = np.asarray(left) - np.asarray(right)
    bootstrap = delta[indices].mean(axis=1)
    point = float(delta.mean())
    low, high = np.quantile(bootstrap, [.025, .975])
    p = (1 + (abs(bootstrap - point) >= abs(point)).sum()) / (len(bootstrap) + 1)
    return {'point': point, 'ci_low': float(low), 'ci_high': float(high), 'bootstrap_p': float(p)}


def path_metrics(net, turnover):
    """Calendar-daily metrics, with initial wealth included in drawdown peaks."""
    net, turnover = np.asarray(net), np.asarray(turnover)
    nav = np.cumprod(1 + net, axis=-1)
    peak = np.maximum.accumulate(np.maximum(nav, 1), axis=-1)
    sd = np.std(net, axis=-1, ddof=1)
    return {
        'Sharpe': np.divide(np.mean(net, axis=-1) * np.sqrt(365), sd,
                            out=np.full_like(sd, np.nan), where=sd > 0),
        'max_drawdown': np.min(nav / peak - 1, axis=-1),
        'annual_turnover': np.mean(turnover, axis=-1) * 365,
    }


def nhhmm_audit(out):
    health, distribution, performance, calibration, alignment, months = [], [], [], [], [], []
    records = pd.read_csv(BASE / 'm3/candidate_results.csv')
    records.groupby(['asset', 'family', 'K', 'penalty'], dropna=False).agg(
        attempted=('id', 'size'), eligible=('eligible', 'sum'),
        converged=('converged', 'sum'), optimizer_success=('optimizer_success', 'sum'),
        maximum_gradient_norm=('gradient_norm', 'max'),
    ).reset_index().to_csv(out / 'T05_fit_health.csv', index=False)
    comparisons = pd.read_csv(BASE / 'm3_evaluation/predictive_comparison.csv')
    for asset in ['BTC', 'ETH']:
        nn = joblib.load(BASE / f'm3_evaluation/{asset.lower()}.joblib')
        model, meta = nn['model'], nn['metadata']
        source = pd.read_parquet(BASE / f'm1/features_{asset.lower()}.parquet')
        frame, x, z, prep = prepare(source, FAMILIES[meta['selected_family']])
        alpha, scores = model.infer(x, z, sequence_starts(frame))
        transition = model.transitions(z)
        q = np.einsum('ti,tij->tj', alpha, transition)
        export = pd.read_csv(BASE / f'm3_evaluation/{asset.lower()}_filtered.csv')
        k = meta['K']
        reload_error = float(abs(alpha - export[[f'prob_state_{i}' for i in range(k)]]).max().max())
        forecast_error = float(abs(q - export[[f'prob_next_state_{i}' for i in range(k)]]).max().max())
        prefix_errors = []
        for end in [100, int(frame.split.eq('train').sum()), int(frame.split.ne('test').sum())]:
            prefix = model.infer(x[:end], z[:end], sequence_starts(frame.iloc[:end]))[0]
            prefix_errors.append(float(abs(prefix - alpha[:end]).max()))
        history = np.asarray(model.history_)
        health.append({
            'asset': asset, 'model_run_id': meta['model_run_id'], 'K': k,
            'converged': model.converged_, 'iterations': model.n_iter_,
            'last_optimizer_success': model.transition_optimizer_success_,
            'last_gradient_norm': model.transition_gradient_norm_,
            'objective_max_increase': float(np.diff(history).max()),
            'probability_error': max(probability_error(alpha), probability_error(q), probability_error(transition)),
            'reload_max_error': reload_error, 'prefix_max_error': max(prefix_errors),
            'forecast_reload_max_error': forecast_error,
            'condition_number': prep['condition_number'],
        })
        if max(reload_error, forecast_error, max(prefix_errors)) > 1e-10:
            raise ValueError('NHHMM export/prefix mismatch')
        reference = comparisons.loc[comparisons.asset.eq(asset)].iloc[0]
        hb = joblib.load(BASE / f'm2/candidates/{reference.homogeneous_reference}.joblib')
        hm = hb['model']
        ha, hs = infer(hm, hb['scaler'].transform(frame[['log_return', 'rv21', 'log_dollar_volume']]), frame)
        _, order = linear_sum_assignment(((hm.means_[:, None] - model.means_[None]) ** 2).sum(2))
        hq, nq = ha @ hm.transmat_, q[:, order]
        for h, n in enumerate(order):
            alignment.append({'asset': asset, 'hmm_state': h, 'nhhmm_state': int(n),
                              'train_mean_squared_distance': float(((hm.means_[h] - model.means_[n]) ** 2).sum()),
                              'hmm_train_share': float((ha[frame.split.eq('train')].argmax(1) == h).mean()),
                              'nhhmm_train_share': float((alpha[frame.split.eq('train')].argmax(1) == n).mean()),
                              'mapping_scope': 'train emission coordinates only; no test remapping'})
        design_names = prep['features'] + [f'{f}_missing' for f in prep['indicator']]
        train_z = z[frame.split.eq('train')]
        risk = int(hb['metadata']['high_risk_state'])
        contiguous = pd.to_datetime(frame.date_utc).diff().dt.days.eq(1).to_numpy()[1:]
        target = ha[1:].argmax(1)
        nn_loss = -np.log(np.maximum(nq[:-1][np.arange(len(target)), target], 1e-15))
        hh_loss = -np.log(np.maximum(hq[:-1][np.arange(len(target)), target], 1e-15))
        for split in ['train', 'validation', 'test']:
            rowmask = frame.split.eq(split).to_numpy()
            mask = rowmask[1:] & contiguous
            at_risk = mask & (ha[:-1].argmax(1) != risk)
            events = (target[at_risk] == risk).astype(int)
            nprob, hprob = nq[:-1, risk][at_risk], hq[:-1, risk][at_risk]
            delta = nn_loss[mask] - hh_loss[mask]
            performance.append({
                'asset': asset, 'split': split, 'days': int(mask.sum()),
                'observed_LL_NHHMM_minus_HMM': float((scores - hs)[rowmask].mean()),
                'proxy_logloss_NHHMM_minus_HMM': float(delta.mean()),
                'proxy_target_probability_below_1e12': int((nq[:-1][np.arange(len(target)), target][mask] < 1e-12).sum()),
                'state_ARI': adjusted_rand_score(ha[rowmask].argmax(1), alpha[rowmask].argmax(1)),
                'at_risk_days': int(at_risk.sum()), 'stress_proxy_entries': int(events.sum()),
                'event_rate': float(events.mean()) if len(events) else None,
                'Brier_NHHMM': float(np.mean((nprob - events) ** 2)) if len(events) else None,
                'Brier_HMM': float(np.mean((hprob - events) ** 2)) if len(events) else None,
                'PR_AUC_NHHMM': average_precision_score(events, nprob) if 0 < events.sum() < len(events) else None,
                'PR_AUC_HMM': average_precision_score(events, hprob) if 0 < events.sum() < len(events) else None,
                'event_count_screen_20': bool(events.sum() >= 20),
                'target': 'matched HMM filtered next-state argmax, proxy not latent truth',
                'scope': 'train descriptive' if split == 'train' else 'development' if split == 'validation' else 'historical exploratory',
            })
            for name, probabilities in [('NHHMM', nprob), ('HMM', hprob)]:
                for low, high in zip([0, .01, .05, .1, .25, .5], [.01, .05, .1, .25, .5, 1.0000001]):
                    use = (probabilities >= low) & (probabilities < high)
                    calibration.append({'asset': asset, 'split': split, 'model': name, 'bin_low': low,
                                        'bin_high': min(high, 1), 'days': int(use.sum()),
                                        'events': int(events[use].sum()),
                                        'mean_prediction': float(probabilities[use].mean()) if use.any() else None,
                                        'event_frequency': float(events[use].mean()) if use.any() else None})
            for c, name in enumerate(design_names):
                v = z[rowmask, c]
                distribution.append({'asset': asset, 'split': split, 'feature': name,
                                     'train_standardized_mean': float(v.mean()), 'standard_deviation': float(v.std()),
                                     'outside_train_range_share': float(((v < train_z[:, c].min()) | (v > train_z[:, c].max())).mean()),
                                     'abs_z_above_3_share': float((abs(v) > 3).mean()),
                                     'original_missing_share': float(frame.loc[rowmask, name].isna().mean()) if name in frame else None})
        monthly = pd.DataFrame({'date': frame.date_utc.iloc[1:].to_numpy(), 'delta': nn_loss - hh_loss,
                                'nn_observed_LL': scores[1:], 'hmm_observed_LL': hs[1:],
                                'split': frame.split.iloc[1:].to_numpy()})
        monthly['month'] = monthly.date.str[:7]
        monthly = monthly.loc[contiguous].groupby(['split', 'month']).agg(
            days=('delta', 'size'), proxy_logloss_delta=('delta', 'mean'),
            NHHMM_observed_LL=('nn_observed_LL', 'mean'), HMM_observed_LL=('hmm_observed_LL', 'mean')).reset_index()
        months.append(monthly.assign(asset=asset))
    pd.DataFrame(health).to_csv(out / 'T05_selected_numerics.csv', index=False)
    pd.DataFrame(distribution).to_csv(out / 'T05_covariate_shift.csv', index=False)
    pd.DataFrame(performance).to_csv(out / 'T05_split_prediction_audit.csv', index=False)
    pd.DataFrame(calibration).to_csv(out / 'T05_stress_calibration.csv', index=False)
    pd.DataFrame(alignment).to_csv(out / 'T05_train_alignment.csv', index=False)
    pd.concat(months).to_csv(out / 'T05_monthly_loss.csv', index=False)


def fair_stability(out):
    """Matched core features/scaler/dates/K; report GMM/KMeans only where fits exist."""
    fits = pd.read_csv(BASE / 'm2/candidate_results.csv')
    benchmark = pd.read_csv(BASE / 'm4/development_results.csv')
    rows, comparisons = [], []
    for asset in ['BTC', 'ETH']:
        frame = pd.read_parquet(BASE / f'm1/features_{asset.lower()}.parquet')
        end, valend = FOLDS[2]
        validation = frame.loc[frame.date_utc.gt(end) & frame.date_utc.le(valend)]
        for k in [2, 3, 4]:
            paths = fits.loc[fits.asset.eq(asset) & fits.fold.eq(2) & fits.rv.eq(21) & fits.K.eq(k) & fits.eligible]
            states, scores = {}, {}
            for r in paths.itertuples():
                b = joblib.load(BASE / f'm2/candidates/{r.candidate_id}.joblib')
                a, s = infer(b['model'], b['scaler'].transform(frame[['log_return', 'rv21', 'log_dollar_volume']]), frame)
                mask = frame.date_utc.isin(validation.date_utc).to_numpy()
                states.setdefault('HMM', []).append(a[mask].argmax(1))
                scores[r.candidate_id] = s[mask]
            for method in ['GMM', 'KMeans']:
                group = benchmark.loc[benchmark.asset.eq(asset) & benchmark.method.eq(method) & benchmark.K.eq(k)]
                for r in group.loc[group.eligible].itertuples():
                    b = joblib.load(BASE / f'm4/{r.id}.joblib')
                    x = b['scaler'].transform(validation[['log_return', 'rv21', 'log_dollar_volume']])
                    states.setdefault(method, []).append(b['model'].predict(x))
                    if method == 'GMM':
                        scores[r.id] = b['model'].score_samples(x)
                arrays = states.get(method, [])
                aris = [adjusted_rand_score(a, b) for a, b in itertools.combinations(arrays, 2)]
                rows.append({'asset': asset, 'K': k, 'method': method, 'sample': 'fold2 validation',
                             'planned_fits': len(group), 'valid_fits': len(arrays),
                             'median_ARI': float(np.median(aris)) if aris else None,
                             'minimum_ARI': float(min(aris)) if aris else None,
                             'persistence': float(np.mean([(s[1:] == s[:-1]).mean() for s in arrays])) if arrays else None,
                             'claim': 'same days/features/K; method-specific fitted parameters; no superiority imposed'})
            arrays = states.get('HMM', [])
            aris = [adjusted_rand_score(a, b) for a, b in itertools.combinations(arrays, 2)]
            rows.append({'asset': asset, 'K': k, 'method': 'HMM', 'sample': 'fold2 validation',
                         'planned_fits': 10, 'valid_fits': len(arrays),
                         'median_ARI': float(np.median(aris)) if aris else None,
                         'minimum_ARI': float(min(aris)) if aris else None,
                         'persistence': float(np.mean([(s[1:] == s[:-1]).mean() for s in arrays])) if arrays else None,
                         'claim': 'pooled initializers; consult T08_HMM_stability for family coverage'})
            # Select matched-K representatives using validation scores only, as existing protocol specifies.
            hs = {cid: s for cid, s in scores.items() if '_f2_' in cid}
            gs = {cid: s for cid, s in scores.items() if '_GMM_' in cid}
            if hs and gs:
                hid = max(hs, key=lambda cid: (hs[cid].mean(), cid))
                gid = max(gs, key=lambda cid: (gs[cid].mean(), cid))
                for block in [14, 21, 42]:
                    interval = paired_interval(hs[hid], gs[gid], moving_blocks(len(validation), 1000, block, 20261024))
                    comparisons.append({'asset': asset, 'K': k, 'HMM_id': hid, 'GMM_id': gid,
                                        'block_days': block, 'metric': 'HMM_minus_GMM_predictive_LL', **interval,
                                        'scope': 'validation selection sample; conditional descriptive CI, not confirmatory'})
    pd.DataFrame(rows).to_csv(out / 'T08_matched_validation_stability.csv', index=False)
    pd.DataFrame(comparisons).to_csv(out / 'T07_matched_validation_LL.csv', index=False)
    fits.groupby(['asset', 'fold', 'rv', 'K', 'initializer']).agg(
        attempted=('candidate_id', 'size'), eligible=('eligible', 'sum'),
        median_min_train_share=('min_train_share', 'median')).reset_index().to_csv(out / 'T08_fold_fit_health.csv', index=False)


def economic_summary(out):
    profiles = pd.read_csv(BASE / 'm2_profiles/profiles.csv')
    means = profiles.pivot(index=['asset', 'state_id'], columns='feature', values='weighted_mean').reset_index()
    labels = pd.concat([pd.read_csv(BASE / f'm2/{a.lower()}_economic_labels.csv').assign(asset=a) for a in ['BTC', 'ETH']])
    summary = labels.merge(means, on=['asset', 'state_id'], validate='one_to_one')
    sensitivity = pd.read_csv(BASE / 'm2_profiles/label_block_sensitivity.csv')
    consistent = sensitivity.groupby(['asset', 'state_id']).economic_label.nunique().eq(1).rename('same_label_blocks_14_21_42')
    summary.merge(consistent, on=['asset', 'state_id'], validate='one_to_one').to_csv(out / 'T03_economic_summary.csv', index=False)
    separation=[]
    for asset in ['BTC','ETH']:
        frame=pd.read_parquet(BASE/f'm1/features_{asset.lower()}.parquet')
        posterior=pd.read_csv(BASE/f'm2/{asset.lower()}_filtered.csv')
        frame=frame.loc[frame.split.eq('train')].merge(
            posterior[['date_utc']+[c for c in posterior if c.startswith('prob_state_')]],
            on='date_utc',validate='one_to_one')
        weights=frame[[c for c in frame if c.startswith('prob_state_')]].to_numpy()
        contrasts=pd.read_csv(BASE/'m2_profiles/contrasts.csv')
        for feature in ['log_return','rv21','log_dollar_volume','amihud_illiq']:
            observed=frame[feature].notna().to_numpy()
            values=frame.loc[observed,feature].to_numpy()
            w=weights[observed];mass=w.sum(0);means=w.T@values/mass
            total=float(((values-values.mean())**2).sum())
            between=float((mass*(means-values.mean())**2).sum())
            ratio=between/total if total else 0.
            if not -1e-10<=ratio<=1+1e-10:
                raise ValueError('Invalid weighted variance decomposition')
            group=contrasts.loc[contrasts.asset.eq(asset)&contrasts.feature.eq(feature)]
            separation.append({'asset':asset,'feature':feature,'between_state_mean_variance_share':ratio,
                               'conditional_Holm_contrasts_below_05':int(group.holm_adjusted_p.lt(.05).sum()),
                               'pairwise_contrasts':len(group),'sample':'train only',
                               'scope':'descriptive fixed posterior; not feature importance, causality or independent significance'})
    pd.DataFrame(separation).to_csv(out/'T03_between_state_separation.csv',index=False)


def portfolio_uncertainty(out):
    nav = pd.read_csv(BASE / 'm5/nav.csv')
    subset = nav.loc[nav.scenario.eq('baseline_close_to_close') & nav.fee_rate.eq(.001)]
    absolute, relative = [], []
    for asset, group in subset.groupby('asset'):
        net = group.pivot(index='date_utc', columns='strategy', values='net')
        turn = group.pivot(index='date_utc', columns='strategy', values='turnover').reindex(net.index)
        if net.isna().any().any() or turn.isna().any().any():
            raise ValueError('Unpaired backtest dates')
        for block in [14, 21, 42]:
            ix = moving_blocks(len(net), 1000, block, 20261024)
            boot, point = {}, {}
            for strategy in net:
                boot[strategy] = path_metrics(net[strategy].to_numpy()[ix], turn[strategy].to_numpy()[ix])
                point[strategy] = path_metrics(net[strategy].to_numpy(), turn[strategy].to_numpy())
                for metric, values in boot[strategy].items():
                    lo, hi = np.nanquantile(values, [.025, .975])
                    absolute.append({'asset': asset, 'strategy': strategy, 'metric': metric, 'block_days': block,
                                     'point': float(point[strategy][metric]), 'ci_low': lo, 'ci_high': hi,
                                     'scope': 'fixed-signal paired block bootstrap; pointwise conditional CI'})
            for strategy in ['regime_defensive', 'regime_volatility_targeting']:
                for reference in ['buy_and_hold', 'volatility_targeting']:
                    for metric in boot[strategy]:
                        delta = boot[strategy][metric] - boot[reference][metric]
                        p = float(point[strategy][metric] - point[reference][metric])
                        lo, hi = np.nanquantile(delta, [.025, .975])
                        relative.append({'asset': asset, 'strategy': strategy, 'reference': reference,
                                         'metric': metric, 'block_days': block, 'point': p, 'ci_low': lo, 'ci_high': hi,
                                         'bootstrap_p': (1 + (abs(delta - p) >= abs(p)).sum()) / (len(delta) + 1),
                                         'scope': 'historical exploratory; model/strategy selection uncertainty excluded'})
    rel = pd.DataFrame(relative)
    for _, group in rel.groupby(['metric', 'block_days']):
        rel.loc[group.index, 'holm_adjusted_p'] = multipletests(group.bootstrap_p, method='holm')[1]
    pd.DataFrame(absolute).to_csv(out / 'T06_absolute_uncertainty.csv', index=False)
    rel.to_csv(out / 'T06_paired_uncertainty.csv', index=False)


def run():
    out = BASE / 'review'
    out.mkdir(parents=True, exist_ok=True)
    inputs = {}
    for stage in ['m1', 'm2', 'm2_profiles', 'm3', 'm3_evaluation', 'm4', 'm4_evaluation', 'm5', 'deliverables']:
        for p in (BASE / stage).rglob('*'):
            if p.is_file():
                inputs[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    lock = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'inputs_sha256': inputs,
            'protocol': 'docs/V2_REVIEW_PROTOCOL.md', 'new_fits': 0, 'test_used_for_selection': False}
    (out / 'input_snapshot.json').write_text(json.dumps(lock, indent=2), encoding='utf-8')
    nhhmm_audit(out)
    fair_stability(out)
    economic_summary(out)
    portfolio_uncertainty(out)
    if any(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest for p, digest in inputs.items()):
        raise ValueError('Frozen input modified during review')
    supplemental = [p for p in out.iterdir() if p.is_file() and p.name not in ['manifest.json', 'input_snapshot.json']]
    source_files = ['src/research_v2/review.py', 'src/research_v2/rolling_benchmarks.py',
                    'scripts/reproduce_v2.py', 'scripts/build_v2_review.py', 'docs/V2_REVIEW_PROTOCOL.md']
    rolling_manifest = out / 'rolling_benchmarks/manifest.json'
    manifest = {'status': 'diagnostics_complete', 'research_confirmation': 'pending', 'frozen_inputs_unchanged': True,
                'new_fits': 0, 'test_used_for_selection': False,
                'files_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in supplemental},
                'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_files}}
    if rolling_manifest.exists():
        manifest['rolling_benchmarks_manifest_sha256'] = hashlib.sha256(rolling_manifest.read_bytes()).hexdigest()
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest))


if __name__ == '__main__':
    run()
