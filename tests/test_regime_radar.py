"""Acceptance of the radar using actual exported BTC/ETH models and probabilities."""

import copy
import warnings

import numpy as np
import pandas as pd
import pytest
from bs4 import BeautifulSoup
from streamlit.testing.v1 import AppTest

from dashboard.regime_radar import build_snapshot
from dashboard import v2_service
from src.models.handoff import UnstableModelWarning, load_filtered
from src.utils.config import ROOT


@pytest.fixture(scope="module", params=["BTC", "ETH"])
def real_signals(cfg, request):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UnstableModelWarning)
        return load_filtered(cfg, request.param, acknowledge_unstable=True)


def test_snapshot_uses_all_real_states_and_metadata(real_signals):
    frame, metadata = real_signals
    snapshot = build_snapshot(frame, metadata)
    states = snapshot["states"]
    assert len(states) == metadata["K"]
    assert states["label"].tolist() == [metadata["label_map"][str(i)] for i in range(metadata["K"])]
    assert states["current_probability"].sum() == pytest.approx(1, abs=1e-12)
    assert states["next_day_probability"].sum() == pytest.approx(1, abs=1e-12)
    assert snapshot["date_utc"] == pd.Timestamp(frame.iloc[-1]["date_utc"], tz="UTC")
    assert snapshot["as_of_utc"] >= snapshot["date_utc"] + pd.Timedelta(days=1)
    assert snapshot["forecast_date_utc"] == snapshot["date_utc"] + pd.Timedelta(days=1)
    assert snapshot["prob_high_risk_next_day"] == pytest.approx(frame.iloc[-1]["prob_high_risk_next_day"])


def test_forecast_integrates_all_current_states_not_only_argmax(real_signals):
    frame, metadata = real_signals
    columns = [f"prob_state_{i}" for i in range(metadata["K"])]
    # Select a real ambiguous observation; no fabricated market probabilities.
    end = int(frame[columns].max(axis=1).to_numpy().argmin()) + 1
    snapshot = build_snapshot(frame.iloc[:end], metadata)
    alpha = frame.iloc[end - 1][columns].to_numpy(dtype=float)
    p = np.asarray(metadata["transition_matrix"])
    np.testing.assert_allclose(snapshot["states"]["next_day_probability"], alpha @ p, atol=1e-12)
    assert not np.allclose(alpha @ p, p[alpha.argmax()], atol=1e-5)


def test_snapshot_history_is_unchanged_when_later_rows_exist(real_signals):
    frame, metadata = real_signals
    n = len(frame) - 10
    before = build_snapshot(frame.iloc[:n].copy(), metadata)
    _ = build_snapshot(frame, metadata)
    after = build_snapshot(
        frame.loc[pd.to_datetime(frame["date_utc"], utc=True) <= before["date_utc"]], metadata
    )
    pd.testing.assert_frame_equal(before["states"], after["states"])


def test_snapshot_rejects_hindsight(real_signals):
    frame, metadata = real_signals
    altered = frame.tail(3).copy()
    altered["probability_type"], altered["hindsight"] = "smoothed", True
    with pytest.raises(ValueError, match="filtered"):
        build_snapshot(altered, metadata)


def test_snapshot_rejects_invalid_transition(real_signals):
    frame, metadata = real_signals
    altered = copy.deepcopy(metadata)
    altered["transition_matrix"][0][0] = -0.1
    with pytest.raises(ValueError, match="probability"):
        build_snapshot(frame, altered)


def test_snapshot_rejects_forecast_inconsistent_with_c2(real_signals):
    frame, metadata = real_signals
    altered = frame.tail(3).copy()
    altered["prob_high_risk_next_day"] = 0.9
    with pytest.raises(ValueError, match="exported forecast"):
        build_snapshot(altered, metadata)


def test_snapshot_rejects_wrong_state_count(real_signals):
    frame, metadata = real_signals
    altered = frame.drop(columns=f"prob_state_{metadata['K'] - 1}")
    with pytest.raises(ValueError, match="K"):
        build_snapshot(altered, metadata)


@pytest.mark.parametrize("asset", ["BTC", "ETH"])
def test_radar_ui_matches_real_probabilities_and_warnings(cfg, asset):
    at = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=180).run()
    next(r for r in at.radio if r.label == "Tài sản").set_value(asset).run()
    assert not at.exception and not at.error
    context = v2_service.context(asset)
    frame, metadata = context.signals, context.metadata
    html = next(m.value for m in at.markdown if "P hiện tại (filtered)" in m.value and "<table" in m.value)
    table = BeautifulSoup(html, "html.parser")
    rows = table.select("tbody tr") or table.select("tr")[1:]
    assert len(rows) == metadata["K"]
    assert [r.select("td")[1].get_text() for r in rows] == [
        metadata["label_map"][str(i)] for i in range(metadata["K"])
    ]
    assert any("AI Market Regime Radar" in m.value for m in at.markdown)
    assert any(pd.Timestamp(frame.iloc[-1]["date_utc"]).strftime("%d/%m/%Y") in c.value for c in at.caption)
    if not metadata['stability']['stable']:
        assert any('chưa đủ ổn định' in w.value for w in at.warning)


def test_history_can_select_states_and_keeps_hindsight_separate():
    at = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=180).run()
    next(r for r in at.radio if r.label == "Trang").set_value("Regime History").run()
    mode = next(r for r in at.radio if r.label.startswith("Loại xác suất"))
    assert mode.value.startswith("Filtered")
    at.multiselect[0].set_value([0]).run()
    assert not at.exception and not at.error
    at.multiselect[0].set_value([]).run()
    assert not at.exception and any("Chọn ít nhất" in m.value for m in at.info)
    at.multiselect[0].set_value([0]).run()
    mode = next(r for r in at.radio if r.label.startswith("Loại xác suất"))
    mode.set_value(mode.options[1]).run()
    assert not at.exception and any("hindsight" in w.value.lower() for w in at.warning)
