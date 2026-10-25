"""RQ3: as-of logistic transition proxy, explicitly NOT a non-homogeneous HMM."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.features.extended import build_extended
from src.models.data import CORE
from src.utils.config import write_json


def transition_dataset(frame, signals, extended, risk, max_age_days):
    """X at candle t -> non-risk to high-risk proxy at contiguous t+1.

    Splits follow the TARGET date. Consequently the final train feature row
    cannot smuggle the first validation outcome into training labels.
    """
    keys = ["asset", "date_utc", "split", "segment_id"]
    merged = frame.merge(signals[keys + ["state_id"]], on=keys, validate="one_to_one")
    dates = pd.to_datetime(merged["date_utc"], utc=True)
    merged["target_date_utc"] = dates.shift(-1)
    merged["target_split"] = merged["split"].shift(-1)
    merged["target_high_risk"] = merged["state_id"].shift(-1).eq(risk).astype(int)
    valid = merged["state_id"].ne(risk) & dates.shift(-1).sub(dates).eq(pd.Timedelta(days=1))
    valid &= merged["segment_id"].eq(merged["segment_id"].shift(-1))
    if extended is not None:
        merged = merged.merge(
            extended, on=["asset", "date_utc", "split"], validate="one_to_one", suffixes=("", "_ext")
        )
        decision = dates + pd.Timedelta(days=1)
        for column in extended:
            if not column.endswith("_available_at"):
                continue
            variable = column.removesuffix("_available_at")
            available = pd.to_datetime(merged[column], utc=True)
            if (available > decision).any():
                raise ValueError(f"Future publication in drivers: {variable}")
            stale = decision.sub(available).gt(pd.Timedelta(days=max_age_days))
            if variable in merged:
                merged.loc[stale, variable] = np.nan
        if "term_spread_10y_2y" in merged:
            fresh = merged["us10y"].notna() & merged["us2y"].notna()
            merged.loc[~fresh, "term_spread_10y_2y"] = np.nan
    merged = merged.loc[valid].copy().reset_index(drop=True)
    merged["feature_split"] = merged["split"]
    merged["split"] = merged["target_split"]
    return merged


def probability_scores(y, probability):
    y = np.asarray(y, dtype=int)
    p = np.asarray(probability, dtype=float)
    events = int(y.sum())
    return {
        "n": len(y),
        "events": events,
        "prevalence": float(y.mean()),
        "Brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "PR_AUC": float(average_precision_score(y, p)) if events else np.nan,
        "ROC_AUC": float(roc_auc_score(y, p)) if 0 < events < len(y) else np.nan,
        "rare_events_warning": bool(events < 20),
    }


def run_asset(cfg, frame, signals, metadata, settings, metadata_dir, models_dir):
    import joblib

    extended, _ = build_extended(
        frame, Path(cfg["_config_path"]).resolve().parents[1] / cfg["paths"]["raw"], cfg
    )
    dataset = transition_dataset(
        frame, signals, extended, metadata["high_risk_state"], settings["max_source_age_days"]
    )
    train, validation = (dataset.loc[dataset["split"].eq(period)] for period in ("train", "validation"))
    if (
        train["target_high_risk"].sum() < settings["minimum_train_events"]
        or train["target_high_risk"].nunique() != 2
    ):
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            {"status": "insufficient_train_events", "train_events": int(train["target_high_risk"].sum())},
            pd.DataFrame(),
        )
    groups = {
        "core": CORE,
        "macro": CORE + settings["macro_features"],
        "macro_crypto": CORE
        + settings["macro_features"]
        + settings["crypto_features"]
        + ["amihud_illiq", "btc_eth_corr21"],
    }
    fitted, candidates, used = {}, [], {}
    for group, requested in groups.items():
        columns = [
            c
            for c in requested
            if c in train
            and np.isfinite(pd.to_numeric(train[c], errors="coerce")).mean() >= settings["min_train_coverage"]
        ]
        used[group] = columns
        for regularization in settings["regularization_C"]:
            model = make_pipeline(
                SimpleImputer(strategy="median", add_indicator=True),
                StandardScaler(),
                LogisticRegression(C=regularization, max_iter=2000, random_state=0),
            )
            model.fit(train[columns].replace([np.inf, -np.inf], np.nan), train["target_high_risk"])
            p = model.predict_proba(validation[columns].replace([np.inf, -np.inf], np.nan))[:, 1]
            score = probability_scores(validation["target_high_risk"], p)
            candidates.append(
                {
                    "group": group,
                    "C": regularization,
                    "validation_log_loss": score["log_loss"],
                    "n_features": len(columns),
                }
            )
            fitted[(group, regularization)] = model
    selected = min(candidates, key=lambda item: (item["validation_log_loss"], item["n_features"], item["C"]))
    info = {
        "status": "complete",
        "asset": metadata["asset"],
        "core_model_run_id": metadata["model_run_id"],
        "selected_on": "validation log loss, then smaller feature set and stronger regularization",
        "selected": selected,
        "candidates": candidates,
        "features": used,
        "target": "next-day non-risk -> high-risk FILTERED HMM proxy; not ground truth",
        "causal_interpretation": False,
        "NHHMM": False,
        "test_used_for_selection": False,
        "missing_values": "median and indicators fitted on train only; no backfill; stale macro >7 days set missing",
        "train_events": int(train["target_high_risk"].sum()),
        "validation_events": int(validation["target_high_risk"].sum()),
    }
    write_json(info, metadata_dir / f"drivers_{metadata['asset'].lower()}_selection.json")
    # Only now access test outcomes for descriptive evaluation of frozen candidates.
    rows, coefficients, predictions = [], [], []
    baseline = float(train["target_high_risk"].mean())
    for group, columns in used.items():
        winner = min(
            [c for c in candidates if c["group"] == group],
            key=lambda item: (item["validation_log_loss"], item["C"]),
        )
        model = fitted[(group, winner["C"])]
        for period in ("train", "validation", "test"):
            part = dataset.loc[dataset["split"].eq(period)]
            p = model.predict_proba(part[columns].replace([np.inf, -np.inf], np.nan))[:, 1]
            rows.append(
                {
                    "asset": metadata["asset"],
                    "group": group,
                    "period": period,
                    "C": winner["C"],
                    "selected_group": group == selected["group"],
                    **probability_scores(part["target_high_risk"], p),
                }
            )
            predictions.append(
                pd.DataFrame(
                    {
                        "asset": metadata["asset"],
                        "feature_date_utc": part["date_utc"],
                        "target_date_utc": part["target_date_utc"],
                        "split": period,
                        "group": group,
                        "y_proxy": part["target_high_risk"],
                        "probability": p,
                    }
                )
            )
        names = model[0].get_feature_names_out(columns)
        for name, coefficient in zip(names, model[-1].coef_[0]):
            coefficients.append(
                {
                    "asset": metadata["asset"],
                    "group": group,
                    "feature": name,
                    "standardized_coefficient": float(coefficient),
                    "C": winner["C"],
                    "selected_group": group == selected["group"],
                    "fit_on": "train",
                    "model": "regularized_logistic_transition_proxy",
                    "inference": "association only; no p-values; not NHHMM; post-hoc exploratory research",
                }
            )
        joblib.dump(model, models_dir / f"drivers_{metadata['asset'].lower()}_{group}.joblib")
    for period in ("train", "validation", "test"):
        part = dataset.loc[dataset["split"].eq(period)]
        rows.append(
            {
                "asset": metadata["asset"],
                "group": "train_prevalence_baseline",
                "period": period,
                "C": np.nan,
                "selected_group": False,
                **probability_scores(part["target_high_risk"], np.full(len(part), baseline)),
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(coefficients), info, pd.concat(predictions, ignore_index=True)
