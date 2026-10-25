"""Contracts for the report-team B/H package."""
import hashlib
import json

import numpy as np
import pandas as pd

from dashboard import v2_service
from scripts.build_submission_pack import run
from src.utils.config import ROOT


def test_submission_pack_is_complete_and_hash_verified():
    result = run()
    assert result["status"] == "complete"
    assert "B06_status" in result and "omitted" in result["B06_status"]
    for relative, digest in result["files_sha256"].items():
        path = ROOT / relative
        assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_v2_tables_keep_locked_models_and_required_schema():
    b03 = pd.read_csv(ROOT / "outputs/tables/B03_model_selection_v2.csv")
    champions = b03.loc[b03.selected_v2]
    assert set(champions.K) == {4}
    assert set(champions.candidate_id) == {
        "BTC_f2_rv21_k4_volatility_quantiles_s3", "ETH_f2_rv21_k4_kmeans_s4"
    }
    assert not b03.historical_test_used_for_selection.any()

    b04 = pd.read_csv(ROOT / "outputs/tables/B04_regime_statistics_v2.csv")
    assert len(b04) == 8
    assert {"mean_daily_log_return", "annualized_volatility", "train_frequency",
            "expected_duration_days", "economic_label"} <= set(b04)

    b05 = pd.read_csv(ROOT / "outputs/tables/B05_transition_matrix_v2.csv")
    for _, group in b05.groupby(["asset", "origin"]):
        assert np.isclose(group.probability.sum(), 1.0)
    assert np.isfinite(b05.loc[b05.duration_status.eq("finite"), "expected_duration_days"]).all()

    b07 = pd.read_csv(ROOT / "outputs/tables/B07_hmm_vs_gmm_v2.csv")
    assert len(b07) == 4 and set(b07.method) == {"HMM", "GMM"}
    assert b07.groupby("asset").K.nunique().eq(1).all()
    assert b07.groupby("asset").test_n.nunique().eq(1).all()

    b08 = pd.read_csv(ROOT / "outputs/tables/B08_portfolio_v2.csv")
    assert np.allclose(b08.fee_rate, 0.001)
    assert set(b08.signal_probability) == {"filtered"}


def test_dashboard_only_serves_hash_verified_submission_artifacts():
    path = v2_service.submission_path("outputs/tables/B07_hmm_vs_gmm_v2.csv")
    manifest = json.loads((ROOT / "outputs/metadata/submission_pack_manifest.json").read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["files_sha256"][path.relative_to(ROOT).as_posix()]
