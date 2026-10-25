"""Research acceptance: real artifacts, temporal leakage, economic evidence and baselines."""

import warnings

import joblib
import numpy as np
import pandas as pd
import pytest
import yaml
from scipy.special import softmax
from streamlit.testing.v1 import AppTest

from dashboard import result_service as rs
from dashboard.analytics import window_statistics
from src.data.refresh_extensions import append_unique
from src.features.extended import build_extended
from src.models.data import load_asset
from src.models.handoff import UnstableModelWarning, load_filtered
from src.models.inference import infer
from src.research.drivers import probability_scores, transition_dataset
from src.research.economics import economic_evidence, moving_blocks
from src.research.portfolio import volatility_weights
from src.research.trend import FEATURES, TREND_Z, trend_inputs
from src.utils.config import ROOT, path_of, read_json


@pytest.fixture(scope="module", params=["BTC", "ETH"])
def research_asset(cfg, request):
    frame, _, _ = load_asset(cfg, request.param)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UnstableModelWarning)
        signals, metadata = load_filtered(cfg, request.param, acknowledge_unstable=True)
    settings = yaml.safe_load((ROOT / "config/research.yaml").read_text(encoding="utf-8"))
    return frame, signals, metadata, settings


def test_research_manifest_and_hashes_are_current():
    status = rs.research_status()
    assert status["ok"], status["errors"]
    assert not status["manifest"]["production_model_replaced"]


def test_research_configuration_change_invalidates_interpretation(monkeypatch):
    original = rs.file_hash
    monkeypatch.setattr(
        rs, "file_hash", lambda path: "changed" if path == ROOT / "config/research.yaml" else original(path)
    )
    assert not rs.research_status()["ok"]
    assert rs.validate_bundle()["ok"]  # Baseline remains readable independently.


def test_moving_blocks_retain_contiguous_days(research_asset):
    frame, _, _, _ = research_asset
    indices = moving_blocks(len(frame), 100, 21, 17)
    assert indices.min() >= 0 and indices.max() < len(frame)
    assert np.all(np.diff(indices[:, :21], axis=1) == 1)
    assert np.all(np.diff(indices[:, 21:42], axis=1) == 1)


def test_economic_labels_refuse_validation_or_test(research_asset):
    frame, signals, meta, settings = research_asset
    with pytest.raises(ValueError, match="train only"):
        economic_evidence(
            frame,
            signals[[f"prob_state_{i}" for i in range(meta["K"])]].to_numpy(),
            meta["label_map"],
            settings["economics"],
            0,
        )


def test_each_economic_name_has_its_declared_train_evidence(research_asset):
    _, _, meta, settings = research_asset
    table = pd.read_csv(ROOT / "outputs/tables/research_economic_labels.csv")
    rows = table.loc[table["asset"].eq(meta["asset"])]
    assert len(rows) == meta["K"]
    rule = settings["economics"]
    for row in rows.itertuples():
        assert row.model_label == meta["label_map"][str(row.state_id)]
        if row.economic_label in ("Calm", "Stress", "Bull", "Bear"):
            assert row.weighted_effective_days >= rule["minimum_effective_days"]
        if row.economic_label == "Calm":
            assert row.vol_ratio_ci_high < rule["calm_volatility_ratio_upper"]
        if row.economic_label == "Stress":
            assert (
                row.vol_ratio_ci_low > rule["stress_volatility_ratio_lower"] and row.tail_contrast_ci_low > 0
            )
        if row.direction == "Bull":
            assert row.mean_ci_low > rule["direction_min_daily_return"]
        if row.direction == "Bear":
            assert row.mean_ci_high < -rule["direction_min_daily_return"]
        assert "train only" in row.scope and row.block_days == rule["block_days"]


def test_emission_explanation_reproduces_exported_filtered_vector(research_asset):
    _, signals, meta, _ = research_asset
    table = pd.read_csv(ROOT / "outputs/tables/research_emission_explanation.csv")
    part = table.loc[table["asset"].eq(meta["asset"])].sort_values("state_id")
    log_joint = part[["log_density_return", "log_density_rv21", "log_density_volume"]].sum(
        axis=1
    ).to_numpy() + np.log(part["prior_probability"])
    exported = signals[[f"prob_state_{i}" for i in range(meta["K"])]].iloc[-1].to_numpy()
    np.testing.assert_allclose(softmax(log_joint), exported, atol=1e-10)
    np.testing.assert_allclose(part["posterior_probability"], exported, atol=1e-10)


def test_driver_targets_follow_outcome_split_not_feature_split(cfg, research_asset):
    frame, signals, meta, settings = research_asset
    extended, _ = build_extended(frame, path_of(cfg, "raw"), cfg)
    dataset = transition_dataset(
        frame, signals, extended, meta["high_risk_state"], settings["drivers"]["max_source_age_days"]
    )
    train_end = pd.Timestamp(cfg["split"]["train_end"], tz="UTC")
    assert dataset.loc[dataset["split"].eq("train"), "target_date_utc"].max() <= train_end
    assert dataset.loc[dataset["split"].eq("validation"), "target_date_utc"].min() > train_end
    assert (
        (dataset["target_date_utc"] - pd.to_datetime(dataset["date_utc"], utc=True))
        .eq(pd.Timedelta(days=1))
        .all()
    )
    assert dataset["state_id"].ne(meta["high_risk_state"]).all()
    target_splits = frame.set_index("date_utc")["split"]
    assert dataset["target_date_utc"].dt.strftime("%Y-%m-%d").map(target_splits).equals(dataset["split"])


def test_driver_future_publication_is_rejected(cfg, research_asset):
    frame, signals, meta, settings = research_asset
    extended, _ = build_extended(frame, path_of(cfg, "raw"), cfg)
    extended.loc[extended.index[-2], "vix_available_at"] = extended["decision_time_utc"].iloc[
        -2
    ] + pd.Timedelta(hours=1)
    with pytest.raises(ValueError, match="Future publication"):
        transition_dataset(
            frame, signals, extended, meta["high_risk_state"], settings["drivers"]["max_source_age_days"]
        )


def test_driver_stale_macro_is_missing_not_carried_forever(cfg, research_asset):
    frame, signals, meta, _settings = research_asset
    extended, _ = build_extended(frame, path_of(cfg, "raw"), cfg)
    i = signals.index[signals["state_id"].ne(meta["high_risk_state"])][10]
    extended.loc[i, "vix_available_at"] = extended.loc[i, "decision_time_utc"] - pd.Timedelta(days=30)
    result = transition_dataset(frame, signals, extended, meta["high_risk_state"], 7)
    assert result.loc[result["date_utc"].eq(frame.loc[i, "date_utc"]), "vix"].isna().all()


def test_driver_baseline_scores_have_same_sample_and_real_events(research_asset):
    _, _, meta, _ = research_asset
    scores = pd.read_csv(ROOT / "outputs/tables/research_drivers_metrics.csv")
    part = scores.loc[scores["asset"].eq(meta["asset"])]
    for _, period in part.groupby("period"):
        assert period["n"].nunique() == period["events"].nunique() == 1
        assert "train_prevalence_baseline" in set(period["group"])
        assert np.isfinite(period[["Brier", "log_loss"]]).all().all()
    predictions = pd.read_csv(ROOT / "outputs/predictions/research/drivers_predictions.csv")
    predictions = predictions.loc[
        predictions["asset"].eq(meta["asset"])
        & predictions["group"].eq("core")
        & predictions["split"].eq("test")
    ]
    computed = probability_scores(predictions["y_proxy"], predictions["probability"])
    exported = part.loc[part["group"].eq("core") & part["period"].eq("test")].iloc[0]
    assert computed["Brier"] == pytest.approx(exported["Brier"])


def test_robust_hmm_candidates_and_selection_use_only_validation(research_asset):
    _, _, meta, settings = research_asset
    table = pd.read_csv(ROOT / "outputs/tables/research_hmm_candidates.csv")
    part = table.loc[table["asset"].eq(meta["asset"])]
    assert len(part) == len(settings["robust_hmm"]["states"]) * len(settings["robust_hmm"]["seeds"]) * len(
        settings["robust_hmm"]["initializers"]
    )
    assert not part["test_used"].any()
    lock = read_json(ROOT / f"outputs/metadata/research_hmm_{meta['asset'].lower()}_selection.json")
    assert not lock["test_used_for_selection"] and lock["selection_locked_at_utc"]
    candidate = lock["chosen"]
    assert np.isfinite(candidate["validation_log_score"]) and candidate["eligible"]
    bundle = joblib.load(ROOT / f"outputs/models/research/research_hmm_{meta['asset'].lower()}.joblib")
    assert bundle["metadata"]["chosen"] == candidate


def test_volatility_benchmark_preserves_original_b08_results(research_asset):
    _, _, meta, _ = research_asset
    base = pd.read_csv(ROOT / "outputs/tables/B08_portfolio.csv")
    new = pd.read_csv(ROOT / "outputs/tables/research_portfolio.csv")
    base = base.loc[base["asset"].eq(meta["asset"])]
    new = new.loc[new["asset"].eq(meta["asset"])]
    merged = base.merge(
        new, on=["asset", "strategy", "scenario"], suffixes=("_base", "_research"), validate="one_to_one"
    )
    assert len(merged) == 6
    for column in ["final_nav", "CAGR", "Sharpe", "max_drawdown", "total_cost"]:
        np.testing.assert_allclose(merged[f"{column}_base"], merged[f"{column}_research"], atol=1e-12)
    assert not new["parameters_tuned_on_test"].any()


def test_volatility_weights_are_causal_and_long_cash(research_asset):
    frame, _, _, settings = research_asset
    rv = frame["rv21"].to_numpy()
    a = volatility_weights(rv, settings["portfolio"]["annual_volatility_target"])
    b = volatility_weights(rv[:-10], settings["portfolio"]["annual_volatility_target"])
    np.testing.assert_array_equal(a[:-10], b)
    assert ((a >= 0) & (a <= 1)).all()


def test_window_statistics_uses_exact_visible_rows(research_asset):
    frame, signals, meta, _ = research_asset
    window = signals.iloc[-50:].copy()
    table = window_statistics(frame, window, meta)
    assert table["n_days"].sum() == 50 and table["n_window"].eq(50).all()
    assert table["posterior_mass_days"].sum() == pytest.approx(50)


def test_external_refresh_never_revises_old_values(cfg):
    frame = pd.read_csv(path_of(cfg, "raw") / "macro_daily.csv").iloc[:20].copy().reset_index(drop=True)
    incoming = frame.iloc[-5:].copy()
    incoming["value"] = -1  # Adversarial refetch, not simulated research data.
    result = append_unique(frame, incoming, ["series", "date_local"])
    pd.testing.assert_frame_equal(result, frame)


@pytest.mark.parametrize("asset", ["BTC", "ETH"])
def test_overview_shows_verified_economic_names_and_explanation(asset):
    at = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=180).run()
    next(r for r in at.radio if r.label == "Tài sản").set_value(asset).run()
    assert not at.exception and not at.error
    assert any("Diễn giải train" in m.value for m in at.markdown)
    explanations = [item.value for item in at.dataframe if 'log_density_return' in item.value.columns]
    assert len(explanations) == 1
    assert np.isclose(explanations[0].posterior_probability.sum(), 1)
    assert any('Regime hiện tại' in m.value for m in at.markdown)


def test_backtest_rejects_invalid_initial_state_or_nonfinite_fees():
    from src.evaluation.backtest import regime_weights, simulate

    with pytest.raises(ValueError):
        regime_weights([0.2], threshold=np.nan)
    with pytest.raises(ValueError):
        simulate([1.0], [0.01], initial_weight=np.nan)
    with pytest.raises(ValueError):
        simulate([1.0], [0.01], fee_rate=np.nan)
    with pytest.raises(ValueError):
        simulate([1.0], [-1.2])


def test_trend_features_and_train_scaler_ignore_future_rows(research_asset):
    frame, _, _, _ = research_asset
    complete, full_scaler = trend_inputs(frame)
    prefix, prefix_scaler = trend_inputs(frame.loc[frame["split"].ne("test")])
    assert full_scaler == prefix_scaler and full_scaler["fit_on"] == "train"
    pd.testing.assert_frame_equal(
        complete.iloc[: len(prefix)][FEATURES + TREND_Z], prefix[FEATURES + TREND_Z]
    )
    assert len(complete) == len(frame) - 29


def test_trend_model_filtered_vectors_and_prefix_are_causal(research_asset):
    frame, _, meta, _ = research_asset
    transformed, _ = trend_inputs(frame)
    bundle = joblib.load(ROOT / f"outputs/models/research/trend_hmm_{meta['asset'].lower()}.joblib")
    model, info = bundle["model"], bundle["metadata"]
    x = transformed[TREND_Z].to_numpy()
    full, _ = infer(model, x, transformed)
    n = int(transformed["split"].ne("test").sum())
    prefix, _ = infer(model, x[:n], transformed.iloc[:n])
    np.testing.assert_allclose(prefix, full[:n], atol=1e-12)
    output = pd.read_csv(ROOT / f"outputs/predictions/research/trend_filtered_{meta['asset'].lower()}.csv")
    np.testing.assert_allclose(output[[f"prob_state_{i}" for i in range(info["K"])]], full, atol=1e-12)
    np.testing.assert_allclose(
        output["prob_high_risk_next_day"], (full @ model.transmat_)[:, info["high_risk_state"]], atol=1e-12
    )
    assert output["probability_type"].eq("filtered").all() and not output["hindsight"].any()
    assert info["scaler"]["fit_on"] == "train" and not info["test_used_for_selection"]


def test_trend_economic_labels_have_train_evidence(research_asset):
    _, _, meta, settings = research_asset
    table = pd.read_csv(ROOT / "outputs/tables/research_trend_evidence.csv")
    rows = table.loc[table["asset"].eq(meta["asset"])]
    info = read_json(ROOT / f"outputs/metadata/research_trend_{meta['asset'].lower()}_selection.json")
    assert len(rows) == info["K"]
    for row in rows.itertuples():
        assert info["economic_label_map"][str(row.state_id)] == row.economic_label
        if row.direction == "Bull":
            assert row.mean_ci_low > settings["economics"]["direction_min_daily_return"]
        elif row.direction == "Bear":
            assert row.mean_ci_high < -settings["economics"]["direction_min_daily_return"]
        assert "train only" in row.scope


def test_trend_likelihood_comparison_stays_within_same_feature_space(research_asset):
    _, _, meta, _ = research_asset
    table = pd.read_csv(ROOT / "outputs/tables/research_trend_comparisons.csv")
    rows = table.loc[table["asset"].eq(meta["asset"])]
    assert set(rows["method"]) == {"HMM_trend_5d", "GMM_trend_5d"}
    for _, part in rows.groupby("period"):
        assert part["n"].nunique() == part["K"].nunique() == 1
    assert rows["score_space"].str.contains("5d").all()


def test_trend_backtest_alignment_preserves_buy_hold_baseline(research_asset):
    _, _, meta, _ = research_asset
    table = pd.read_csv(ROOT / "outputs/tables/research_trend_portfolio.csv")
    rows = table.loc[table["asset"].eq(meta["asset"])]
    baseline = pd.read_csv(ROOT / "outputs/tables/B08_portfolio.csv")
    baseline = baseline.loc[
        baseline["asset"].eq(meta["asset"])
        & baseline["strategy"].eq("buy_and_hold")
        & baseline["scenario"].eq("baseline_close_to_close")
    ].iloc[0]
    observed = rows.loc[rows["strategy"].eq("buy_and_hold")].iloc[0]
    assert observed["final_nav"] == pytest.approx(baseline["final_nav"], abs=1e-12)
    assert rows["n_days"].eq(baseline["n_days"]).all()
    assert not rows["parameters_tuned_on_test"].any()


def test_liquidity_proxy_is_real_and_uncertainty_is_train_only(research_asset):
    _, _, meta, _ = research_asset
    table = pd.read_csv(ROOT / "outputs/tables/research_liquidity_profiles.csv")
    rows = table.loc[table["asset"].eq(meta["asset"])]
    assert len(rows) == meta["K"] * 3
    assert rows["mean_amihud_illiquidity"].ge(0).all()
    train = rows.loc[rows["period"].eq("train")]
    assert train["train_ci_low"].notna().all() and train["train_ci_high"].ge(train["train_ci_low"]).all()
    assert rows.loc[rows["period"].ne("train"), ["train_ci_low", "train_ci_high"]].isna().all().all()
