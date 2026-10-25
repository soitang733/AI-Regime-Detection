"""Structured-initialization HMM experiments and independent KMeans benchmark."""

from __future__ import annotations

import itertools
import warnings
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture

from src.models.data import ZCOLS
from src.models.inference import infer, sequence_lengths
from src.models.reports import stability_metrics, train_mapping
from src.utils.config import write_json


def initialized_hmm(train_x, k, seed, initializer, settings):
    rng = np.random.default_rng(seed)
    if initializer == "kmeans":
        labels = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(train_x)
    elif initializer == "volatility_quantiles":
        labels = np.empty(len(train_x), dtype=int)
        for i, group in enumerate(np.array_split(np.argsort(train_x[:, 1], kind="stable"), k)):
            labels[group] = i
    else:
        raise ValueError("Unknown structured initializer")
    means = np.array([train_x[labels == i].mean(axis=0) for i in range(k)])
    variances = np.array([train_x[labels == i].var(axis=0) for i in range(k)])
    means += rng.normal(0, 0.02, means.shape)
    variances = np.maximum(variances * np.exp(rng.normal(0, 0.05, variances.shape)), 1e-6)
    diagonal = settings["initial_self_transition"]
    transition = np.full((k, k), (1 - diagonal) / (k - 1))
    np.fill_diagonal(transition, diagonal)
    model = GaussianHMM(
        n_components=k,
        covariance_type="diag",
        n_iter=settings["max_iter"],
        tol=settings["tol"],
        min_covar=1e-6,
        init_params="",
        params="stmc",
        random_state=seed,
    )
    model.startprob_ = np.bincount(labels, minlength=k) / len(labels)
    model.transmat_, model.means_, model.covars_ = transition, means, variances
    return model


def fit_robust_hmm(frame, settings, feature_columns=None):
    """All fitting/eligibility/ARI/selection happen before accessing test observations."""
    history = frame.loc[frame["split"].isin(["train", "validation"])].reset_index(drop=True)
    train = history.loc[history["split"].eq("train")].reset_index(drop=True)
    columns = ZCOLS if feature_columns is None else list(feature_columns)
    x = train[columns].to_numpy()
    candidates, rows, labels = {}, [], {}
    val_mask = history["split"].eq("validation").to_numpy()
    for initializer in settings["initializers"]:
        for k in settings["states"]:
            for seed in settings["seeds"]:
                row = {
                    "initializer": initializer,
                    "K": k,
                    "seed": seed,
                    "eligible": False,
                    "validation_log_score": np.nan,
                    "reason": "",
                    "test_used": False,
                }
                try:
                    model = initialized_hmm(x, k, seed, initializer, settings)
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model.fit(x, lengths=sequence_lengths(train))
                    gains = list(model.monitor_.history)
                    gain = gains[-1] - gains[-2] if len(gains) > 1 else np.inf
                    alpha, _ = infer(model, x, train)
                    shares = np.bincount(alpha.argmax(axis=1), minlength=k) / len(train)
                    row.update(
                        iterations=model.monitor_.iter,
                        last_gain=gain,
                        minimum_state_share=float(shares.min()),
                    )
                    if not -1e-6 <= gain < settings["tol"] or shares.min() < settings["min_state_share"]:
                        row["reason"] = "nonconvergence or sparse hard train state"
                    else:
                        posterior, score = infer(model, history[columns].to_numpy(), history)
                        value = float(score[val_mask].mean())
                        if not np.isfinite(value):
                            raise ValueError("Nonfinite validation score")
                        row.update(eligible=True, validation_log_score=value)
                        key = (initializer, k, seed)
                        candidates[key], labels[key] = model, posterior[val_mask].argmax(axis=1)
                except (ValueError, FloatingPointError) as exc:
                    row["reason"] = str(exc)
                rows.append(row)
    fits = pd.DataFrame(rows)
    summaries = []
    for (initializer, k), group in fits.groupby(["initializer", "K"]):
        valid = group.loc[group["eligible"]]
        pairs = [
            adjusted_rand_score(labels[(initializer, k, a)], labels[(initializer, k, b)])
            for a, b in itertools.combinations(valid["seed"].astype(int), 2)
        ]
        median, minimum = (float(np.median(pairs)), float(np.min(pairs))) if pairs else (np.nan, np.nan)
        stable = (
            len(valid) >= 3
            and median >= settings["minimum_median_ari"]
            and minimum >= settings["minimum_pair_ari"]
        )
        summaries.append(
            {
                "initializer": initializer,
                "K": k,
                "eligible_seeds": len(valid),
                "pairs": len(pairs),
                "median_ari": median,
                "minimum_ari": minimum,
                "stable_within_initializer": stable,
                "best_validation_log_score": valid["validation_log_score"].max() if len(valid) else np.nan,
            }
        )
    summary = pd.DataFrame(summaries)
    stable_groups = set(
        zip(
            summary.loc[summary["stable_within_initializer"], "initializer"],
            summary.loc[summary["stable_within_initializer"], "K"],
        )
    )
    eligible = fits.loc[fits["eligible"]].copy()
    if eligible.empty:
        raise ValueError("No eligible structured HMM; do not relax quality rules on the test set")
    eligible["stable_group"] = [(row.initializer, row.K) in stable_groups for row in eligible.itertuples()]
    # Prefer configured seed stability, then predictive validation LL; never test.
    winner = eligible.sort_values(
        ["stable_group", "validation_log_score", "K", "seed"], ascending=[False, False, True, True]
    ).iloc[0]
    key = (winner["initializer"], int(winner["K"]), int(winner["seed"]))
    return candidates[key], fits, summary, winner.to_dict()


def run_asset(frame, asset, core_metadata, settings, models_dir, predictions_dir, metadata_dir):
    model, fits, summary, chosen = fit_robust_hmm(frame, settings)
    info = {
        "asset": asset,
        "core_model_run_id": core_metadata["model_run_id"],
        "chosen": chosen,
        "selection_locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "test_used_for_selection": False,
        "selection_rule": "stable-within-initializer groups first, then max validation LL, smaller K and seed",
        "warning": "structured initializer stability is not global stability; original test already observed; exploratory",
    }
    write_json(info, metadata_dir / f"research_hmm_{asset.lower()}_selection.json")
    alpha, scores = infer(model, frame[ZCOLS].to_numpy(), frame)
    train_mask = frame["split"].eq("train").to_numpy()
    mapping, risk = train_mapping(frame.loc[train_mask], alpha[train_mask])
    out = frame[["asset", "date_utc", "split", "segment_id"]].copy()
    out["state_id"] = alpha.argmax(axis=1)
    out["prob_high_risk"] = alpha[:, risk]
    out["label"] = out["state_id"].map(mapping)
    for state in range(model.n_components):
        out[f"prob_state_{state}"] = alpha[:, state]
    out.to_csv(predictions_dir / f"research_hmm_{asset.lower()}.csv", index=False)
    info.update(
        K=model.n_components,
        high_risk_state=risk,
        label_map=mapping,
        transition_matrix=model.transmat_.tolist(),
    )
    joblib.dump({"model": model, "metadata": info}, models_dir / f"research_hmm_{asset.lower()}.joblib")
    rows = []
    x_train = frame.loc[train_mask, ZCOLS].to_numpy()
    km_models = [
        KMeans(n_clusters=core_metadata["K"], n_init=10, random_state=seed).fit(x_train)
        for seed in settings["seeds"]
    ]
    # Choose KMeans initialization on train inertia only.
    km = min(km_models, key=lambda fitted: fitted.inertia_)
    km_labels = km.predict(frame[ZCOLS].to_numpy())
    matched_gmm = GaussianMixture(
        n_components=model.n_components,
        covariance_type="diag",
        n_init=len(settings["seeds"]),
        max_iter=settings["max_iter"],
        tol=settings["tol"],
        reg_covar=1e-6,
        random_state=0,
    ).fit(x_train)
    if not matched_gmm.converged_:
        raise ValueError("Matched-K GMM failed to converge")
    matched_probabilities = matched_gmm.predict_proba(frame[ZCOLS].to_numpy())
    matched_scores = matched_gmm.score_samples(frame[ZCOLS].to_numpy())
    for period in ("train", "validation", "test"):
        mask = frame["split"].eq(period).to_numpy()
        sub = frame.loc[mask].reset_index(drop=True)
        rows.append(
            {
                "asset": asset,
                "method": "HMM_structured",
                "period": period,
                "n": int(mask.sum()),
                "K": model.n_components,
                "avg_log_score": float(scores[mask].mean()),
                "score_kind": "same 3-dimensional one-step predictive density",
                **stability_metrics(sub, alpha[mask].argmax(axis=1)),
            }
        )
        km_parts = [fitted.predict(frame.loc[mask, ZCOLS].to_numpy()) for fitted in km_models]
        ari = [adjusted_rand_score(a, b) for a, b in itertools.combinations(km_parts, 2)]
        rows.append(
            {
                "asset": asset,
                "method": "KMeans",
                "period": period,
                "n": int(mask.sum()),
                "K": core_metadata["K"],
                "avg_log_score": np.nan,
                "score_kind": "clustering; no likelihood; do not compare inertia with HMM LL",
                "median_seed_ari": float(np.median(ari)),
                "mean_squared_centroid_distance": float(
                    np.min(km.transform(frame.loc[mask, ZCOLS].to_numpy()), axis=1).dot(
                        np.min(km.transform(frame.loc[mask, ZCOLS].to_numpy()), axis=1)
                    )
                    / mask.sum()
                ),
                **stability_metrics(sub, km_labels[mask]),
            }
        )
        rows.append(
            {
                "asset": asset,
                "method": "GMM_matched_K",
                "period": period,
                "n": int(mask.sum()),
                "K": model.n_components,
                "avg_log_score": float(matched_scores[mask].mean()),
                "score_kind": "same 3-dimensional marginal density, K matched to structured HMM",
                **stability_metrics(sub, matched_probabilities[mask].argmax(axis=1)),
            }
        )
    joblib.dump(km, models_dir / f"research_kmeans_{asset.lower()}.joblib")
    joblib.dump(matched_gmm, models_dir / f"research_gmm_{asset.lower()}.joblib")
    return fits.assign(asset=asset), summary.assign(asset=asset), pd.DataFrame(rows), info
