"""Build the canonical B01-B08/H01-H06 submission pack from locked V2 artifacts.

This script never fits a model. B01, B02 and H01 are retained in place; all
other files are deterministic projections or copies of verified V2 outputs.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import ROOT

BASE = ROOT / "outputs/research_v2"
TABLES = ROOT / "outputs/tables"
FIGURES = ROOT / "outputs/figures"
META = ROOT / "outputs/metadata"
ASSETS = ("BTC", "ETH")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_existing() -> list[Path]:
    paths = [
        TABLES / "B01_descriptives.csv",
        TABLES / "B02_sample_manifest.csv",
        FIGURES / "H01_price_history.png",
    ]
    for path in paths:
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"Required existing artifact is missing: {path}")
    return paths


def _metadata(asset: str) -> dict:
    return json.loads((BASE / f"m2/{asset.lower()}_metadata.json").read_text(encoding="utf-8"))


def _b03() -> pd.DataFrame:
    source = pd.read_csv(BASE / "deliverables/tables/T02_model_selection.csv")
    rows = source.loc[source.fold.eq(2) & source.rv.eq(21) & source.K.isin([2, 3, 4])].copy()
    champions = {asset: _metadata(asset)["candidate_id"] for asset in ASSETS}
    rows["selected_v2"] = rows.apply(lambda r: r.candidate_id == champions[r.asset], axis=1)
    rows["selection_sample"] = "train/validation only"
    rows["selection_rule"] = "max eligible validation predictive LL; tie BIC/K/seed"
    rows["historical_test_used_for_selection"] = False
    return rows


def _b04() -> pd.DataFrame:
    rows = []
    for asset in ASSETS:
        meta = _metadata(asset)
        signals = pd.read_csv(BASE / f"m2/{asset.lower()}_filtered.csv")
        train = signals.loc[signals.split.eq("train")]
        trans = np.asarray(meta["transition_matrix"], dtype=float)
        for item in meta["economic_labels"]:
            state = int(item["state_id"])
            hard_days = int(train.state_id.eq(state).sum())
            pii = float(trans[state, state])
            rows.append({
                "asset": asset,
                "model_run_id": meta["candidate_id"],
                "K": meta["K"],
                "state_id": state,
                "model_label": item["model_label"],
                "economic_label": item["economic_label"],
                "mean_daily_log_return": item["mean_daily_log_return"],
                "mean_ci_low": item["mean_ci_low"],
                "mean_ci_high": item["mean_ci_high"],
                "daily_volatility": item["daily_volatility"],
                "annualized_volatility": item["daily_volatility"] * np.sqrt(365),
                "volatility_ratio": item["volatility_ratio"],
                "left_tail_rate": item["left_tail_rate"],
                "train_hard_days": hard_days,
                "train_frequency": hard_days / len(train),
                "persistence": pii,
                "expected_duration_days": np.inf if np.isclose(pii, 1.0) else 1.0 / (1.0 - pii),
                "label_scope": "train only; conditional on fixed fitted model",
            })
    return pd.DataFrame(rows)


def _b05() -> pd.DataFrame:
    source = pd.read_csv(BASE / "deliverables/tables/T04_transition_matrix.csv")
    labels = {
        (asset, int(item["state_id"])): item["economic_label"]
        for asset in ASSETS for item in _metadata(asset)["economic_labels"]
    }
    source["origin_label"] = [labels[(a, int(s))] for a, s in zip(source.asset, source.origin)]
    source["destination_label"] = [labels[(a, int(s))] for a, s in zip(source.asset, source.destination)]
    diagonal = source.origin.eq(source.destination)
    source["persistence"] = np.where(diagonal, source.probability, np.nan)
    source["expected_duration_days"] = np.where(
        diagonal,
        np.where(np.isclose(source.probability, 1.0), np.inf, 1.0 / (1.0 - source.probability)),
        np.nan,
    )
    source["duration_status"] = np.where(
        diagonal & np.isclose(source.probability, 1.0), "absorbing_or_rounded_to_one",
        np.where(diagonal, "finite", "not_applicable"),
    )
    return source


def _score(model_path: Path, features: pd.DataFrame) -> float:
    artifact = joblib.load(model_path)
    x = artifact["scaler"].transform(features[["log_return", "rv21", "log_dollar_volume"]])
    return float(artifact["model"].score(x) / len(x))


def _flips(states: pd.DataFrame) -> int:
    dates = pd.to_datetime(states.date_utc)
    contiguous = dates.diff().dt.days.eq(1)
    return int((states.state_id.ne(states.state_id.shift()) & contiguous).sum())


def _b07() -> pd.DataFrame:
    stability = pd.read_csv(BASE / "review/T08_matched_validation_stability.csv")
    rows = []
    for asset in ASSETS:
        meta = _metadata(asset)
        k = int(meta["K"])
        features = pd.read_parquet(BASE / f"m1/features_{asset.lower()}.parquet")
        hmm_signals = pd.read_csv(BASE / f"m2/{asset.lower()}_filtered.csv")
        hmm_model = BASE / f"m2/{asset.lower()}.joblib"
        gmm_candidates = []
        for path in (BASE / "m4").glob(f"{asset}_GMM_{k}_*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("eligible"):
                gmm_candidates.append(record)
        gmm = max(gmm_candidates, key=lambda x: x["validation_log_score"])
        for method, model_id, model_path in [
            ("HMM", meta["candidate_id"], hmm_model),
            ("GMM", gmm["id"], BASE / f"m4/{gmm['id']}.joblib"),
        ]:
            stab = stability.loc[
                stability.asset.eq(asset) & stability.K.eq(k) & stability.method.eq(method)
            ].iloc[0]
            if method == "HMM":
                validation = hmm_signals.loc[hmm_signals.split.eq("validation")]
                test_states = hmm_signals.loc[hmm_signals.split.eq("test")]
                validation_ll = float(meta["validation_log_score"])
            else:
                validation = pd.read_csv(BASE / f"m4/{model_id}_development.csv")
                validation = validation.loc[validation.split.eq("validation")]
                artifact = joblib.load(BASE / f"m4/{model_id}.joblib")
                test_frame = features.loc[features.split.eq("test")].copy()
                test_x = artifact["scaler"].transform(
                    test_frame[["log_return", "rv21", "log_dollar_volume"]]
                )
                test_states = test_frame[["date_utc"]].assign(
                    state_id=artifact["model"].predict(test_x)
                )
                validation_ll = float(gmm["validation_log_score"])
            test_features = features.loc[features.split.eq("test")]
            rows.append({
                "asset": asset,
                "method": method,
                "model_id": model_id,
                "K": k,
                "feature_space": "3D train-standardized core",
                "validation_n": len(validation),
                "validation_mean_log_score": validation_ll,
                "validation_persistence": float(stab.persistence),
                "validation_median_ARI": float(stab.median_ARI),
                "validation_minimum_ARI": float(stab.minimum_ARI),
                "valid_seed_fits": int(stab.valid_fits),
                "test_n": len(test_states),
                "test_mean_log_score": _score(model_path, test_features),
                "test_persistence": float((test_states.state_id.iloc[1:].to_numpy() == test_states.state_id.iloc[:-1].to_numpy()).mean()),
                "test_flips": _flips(test_states),
                "comparison_scope": "same K/features/validation and historical-test dates; exploratory",
            })
    return pd.DataFrame(rows)


def _b08() -> pd.DataFrame:
    source = pd.read_csv(BASE / "deliverables/tables/T06_portfolio.csv")
    out = source.loc[source.scenario.eq("baseline_close_to_close") & np.isclose(source.fee_rate, 0.001)].copy()
    out["fee_bps"] = 10
    out["signal_probability"] = "filtered"
    out["selection_status"] = "fixed rules; historical exploratory"
    return out


def run() -> dict:
    retained = _require_existing()
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    tables = {
        "B03_model_selection_v2.csv": _b03(),
        "B04_regime_statistics_v2.csv": _b04(),
        "B05_transition_matrix_v2.csv": _b05(),
        "B07_hmm_vs_gmm_v2.csv": _b07(),
        "B08_portfolio_v2.csv": _b08(),
    }
    written = []
    for name, frame in tables.items():
        path = TABLES / name
        frame.to_csv(path, index=False)
        written.append(path)
    copies = {
        "H02_BTC_price_regimes.png": BASE / "deliverables/figures/F01_BTC_price_regimes.png",
        "H02_ETH_price_regimes.png": BASE / "deliverables/figures/F01_ETH_price_regimes.png",
        "H03_BTC_regime_probabilities.png": BASE / "deliverables/figures/F02_BTC_probabilities.png",
        "H03_ETH_regime_probabilities.png": BASE / "deliverables/figures/F02_ETH_probabilities.png",
        "H04_BTC_hmm_vs_gmm.png": BASE / "deliverables/figures/F04_BTC_agreement.png",
        "H04_ETH_hmm_vs_gmm.png": BASE / "deliverables/figures/F04_ETH_agreement.png",
        "H05_BTC_portfolio_nav.png": BASE / "deliverables/figures/F05_BTC_portfolio.png",
        "H05_ETH_portfolio_nav.png": BASE / "deliverables/figures/F05_ETH_portfolio.png",
        "H06_dashboard.png": BASE / "ui/current_overview_1440_1.png",
    }
    for name, source in copies.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        target = FIGURES / name
        shutil.copyfile(source, target)
        written.append(target)
    all_files = retained + written
    manifest = {
        "created_at_utc": json.loads(
            (BASE / "deliverables/manifest.json").read_text(encoding="utf-8")
        )["created_at_utc"],
        "status": "complete",
        "source": "locked Research V2 artifacts; no model fitting",
        "B06_status": "omitted: event-count screen failed; T05 coefficients retained without inferential claims",
        "retained_existing": [p.relative_to(ROOT).as_posix() for p in retained],
        "generated": [p.relative_to(ROOT).as_posix() for p in written],
        "files_sha256": {p.relative_to(ROOT).as_posix(): _sha(p) for p in all_files},
    }
    path = META / "submission_pack_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": result["status"], "files": len(result["files_sha256"])}, indent=2))
