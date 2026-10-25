"""Additional causal trend-feature HMM family; economic labels remain train-derived."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

from src.evaluation.backtest import performance_metrics, regime_weights, simulate
from src.evaluation.backtest_run import load_backtest_config
from src.models.inference import infer
from src.models.reports import probability_frame, regime_statistics, stability_metrics, train_mapping
from src.research.economics import economic_evidence
from src.research.robustness import fit_robust_hmm
from src.utils.config import write_json

FEATURES = ["log_return", "rv21", "log_dollar_volume", "momentum_7d", "momentum_30d"]
TREND_Z = [f"trend_z_{column}" for column in FEATURES]


def trend_inputs(frame):
    """Only trailing, segment-local returns; freeze all five scales on train."""
    out = frame.copy()
    for days in (7, 30):
        out[f"momentum_{days}d"] = out.groupby("segment_id", sort=False)["log_return"].transform(
            lambda values, window=days: values.rolling(window, min_periods=window).sum()
        )
    out = out.loc[np.isfinite(out[FEATURES]).all(axis=1)].reset_index(drop=True)
    train = out.loc[out["split"].eq("train"), FEATURES].to_numpy()
    if len(train) < 200:
        raise ValueError("Insufficient train observations for trend HMM")
    mean, scale = train.mean(axis=0), train.std(axis=0, ddof=0)
    scale = np.where(scale == 0, 1, scale)
    out[TREND_Z] = (out[FEATURES].to_numpy() - mean) / scale
    return out, {
        "fit_on": "train",
        "features": FEATURES,
        "mean": mean.tolist(),
        "scale": scale.tolist(),
        "n_train": len(train),
        "warmup_rows_removed": len(frame) - len(out),
        "caution": "overlapping trailing features; diagonal conditional-independence approximation",
    }


def trend_portfolio(frame, signals, metadata):
    """Same fixed rule and costs as baseline, explicit t -> t+1 availability checks."""
    bt = load_backtest_config()
    left = signals.copy()
    left["target_date"] = pd.to_datetime(left["date_utc"], utc=True) + pd.Timedelta(days=1)
    targets = frame[["date_utc", "segment_id", "split", "simple_return"]].copy()
    targets["target_date"] = pd.to_datetime(targets.pop("date_utc"), utc=True)
    targets = targets.rename(columns={"split": "target_split"})
    aligned = left.merge(targets, on=["target_date", "segment_id"], validate="one_to_one")
    aligned = aligned.loc[aligned["target_split"].eq("test")].reset_index(drop=True)
    if (pd.to_datetime(aligned["as_of_utc"], utc=True) > aligned["target_date"]).any():
        raise ValueError("Trend signal arrives after the assumed execution time")
    a = bt["allocation"]
    weights = regime_weights(
        aligned["prob_high_risk"], a["risk_threshold"], a["weight_risk_on"], a["weight_risk_off"]
    )
    rows, navs = [], []
    for name, w in [("buy_and_hold", np.ones(len(aligned))), ("trend_regime_aware", weights)]:
        sim = simulate(
            w, aligned["simple_return"], fee_rate=bt["costs"]["fee_rate"], initial_weight=a["initial_weight"]
        )
        n_days = (aligned["target_date"].iloc[-1] - aligned["target_date"].iloc[0]).days + 1
        rows.append(
            {
                "asset": metadata["asset"],
                "strategy": name,
                "scenario": "baseline_close_to_close",
                "n_days": len(aligned),
                "model_run_id": metadata["model_run_id"],
                "parameters_tuned_on_test": False,
                **performance_metrics(sim["net"], sim["nav"], sim["turnover"], sim["fee"], n_days),
                "scope": "exploratory trend HMM; original test already observed; idealized execution",
            }
        )
        navs.append(
            sim.assign(
                asset=metadata["asset"],
                strategy=name,
                date_utc=aligned["target_date"].dt.strftime("%Y-%m-%d"),
                signal_date_utc=aligned["date_utc"],
                as_of_utc=aligned["as_of_utc"].astype(str),
            )
        )
    return pd.DataFrame(rows), pd.concat(navs, ignore_index=True)


def run_asset(
    frame, asset, core_metadata, settings, economic_settings, seed, models_dir, predictions_dir, metadata_dir
):
    transformed, scaler = trend_inputs(frame)
    model, fits, stability, chosen = fit_robust_hmm(transformed, settings, feature_columns=TREND_Z)
    train = transformed.loc[transformed["split"].eq("train")].reset_index(drop=True)
    train_alpha, _ = infer(model, train[TREND_Z].to_numpy(), train)
    mapping, risk = train_mapping(train, train_alpha)
    original_mapping = {str(k): v for k, v in mapping.items()}
    evidence = economic_evidence(train, train_alpha, original_mapping, economic_settings, seed)
    sensitivity = [evidence]
    for days in (14, 42):
        alternative = copy.deepcopy(economic_settings)
        alternative["block_days"] = days
        sensitivity.append(economic_evidence(train, train_alpha, original_mapping, alternative, seed))
    all_evidence = pd.concat(sensitivity, ignore_index=True)
    consistent = all_evidence.groupby("state_id")["economic_label"].nunique().eq(1)
    evidence["label_stable_across_block_lengths"] = evidence["state_id"].map(consistent)
    identity = {
        "asset": asset,
        "core_model_run_id": core_metadata["model_run_id"],
        "features": FEATURES,
        "scaler": scaler,
        "settings": settings,
        "chosen": chosen,
    }
    run_id = (
        f"trend-{asset.lower()}-"
        + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    )
    metadata = {
        **identity,
        "model_run_id": run_id,
        "K": model.n_components,
        "label_map": original_mapping,
        "high_risk_state": risk,
        "economic_label_map": {str(r.state_id): r.economic_label for r in evidence.itertuples()},
        "transition_matrix": model.transmat_.tolist(),
        "seed_stability_status": "stable_within_initializer" if chosen["stable_group"] else "unstable",
        "selection_locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "test_used_for_selection": False,
        "score_warning": "5-dimensional density; never rank this LL against the 3-dimensional core",
        "economic_scope": "train-frozen interpretation; conditional block bootstrap; exploratory feature extension",
    }
    write_json(metadata, metadata_dir / f"research_trend_{asset.lower()}_selection.json")
    alpha, scores = infer(model, transformed[TREND_Z].to_numpy(), transformed)
    signals = probability_frame(asset, transformed, alpha, mapping, risk, run_id, "filtered")
    signals["prob_high_risk_next_day"] = (alpha @ model.transmat_)[:, risk]
    signals.to_csv(predictions_dir / f"trend_filtered_{asset.lower()}.csv", index=False)
    joblib.dump({"model": model, "metadata": metadata}, models_dir / f"trend_hmm_{asset.lower()}.joblib")
    gmm = GaussianMixture(
        n_components=model.n_components,
        covariance_type="diag",
        n_init=5,
        reg_covar=1e-6,
        max_iter=settings["max_iter"],
        random_state=seed,
    ).fit(train[TREND_Z].to_numpy())
    if not gmm.converged_:
        raise ValueError("Trend matched-K GMM did not converge")
    joblib.dump(gmm, models_dir / f"trend_gmm_{asset.lower()}.joblib")
    gmm_scores, gmm_alpha = (
        gmm.score_samples(transformed[TREND_Z].to_numpy()),
        gmm.predict_proba(transformed[TREND_Z].to_numpy()),
    )
    comparisons = []
    for period in ("train", "validation", "test"):
        mask = transformed["split"].eq(period).to_numpy()
        sub = transformed.loc[mask].reset_index(drop=True)
        for method, log_scores, probabilities in [
            ("HMM_trend_5d", scores, alpha),
            ("GMM_trend_5d", gmm_scores, gmm_alpha),
        ]:
            comparisons.append(
                {
                    "asset": asset,
                    "method": method,
                    "period": period,
                    "n": int(mask.sum()),
                    "K": model.n_components,
                    "avg_log_score": float(log_scores[mask].mean()),
                    **stability_metrics(sub, probabilities[mask].argmax(axis=1)),
                    "score_space": "5d trend features; only compare within this family",
                }
            )
    stats = regime_statistics(asset, transformed, alpha, mapping, model.transmat_, 365, 0.6)
    stats["economic_label"] = stats["state_id"].astype(str).map(metadata["economic_label_map"])
    perf, nav = trend_portfolio(transformed, signals, metadata)
    return {
        "fits": fits.assign(asset=asset),
        "stability": stability.assign(asset=asset),
        "evidence": evidence.assign(asset=asset),
        "sensitivity": all_evidence.assign(asset=asset),
        "stats": stats,
        "comparisons": pd.DataFrame(comparisons),
        "portfolio": perf,
        "nav": nav,
        "metadata": metadata,
    }
