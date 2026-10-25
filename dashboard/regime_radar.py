"""Display-only projection of verified C2 filtered probabilities; never refit or relabel."""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_snapshot(frame, metadata):
    """Return the latest alpha_t and alpha_t @ P in the original model's state order.

    The caller uses C2's verified reader. Additional checks prevent this display
    helper from being accidentally reused with hindsight or incompatible vectors.
    """
    if frame is None or frame.empty:
        raise ValueError("No filtered observations available")
    k = int(metadata["K"])
    mapping = metadata["label_map"]
    columns = [f"prob_state_{i}" for i in range(k)]
    if set(mapping) != {str(i) for i in range(k)} or {c for c in frame if c.startswith("prob_state_")} != set(
        columns
    ):
        raise ValueError("State mapping/probability columns disagree with K")
    if (
        not frame["probability_type"].eq("filtered").all()
        or frame["hindsight"].dtype != bool
        or frame["hindsight"].any()
    ):
        raise ValueError("Radar requires causal filtered probabilities, never hindsight")
    if (
        not frame["model_run_id"].eq(metadata["model_run_id"]).all()
        or not frame["asset"].eq(metadata["asset"]).all()
    ):
        raise ValueError("Filtered observations belong to another model or asset")
    dates = pd.to_datetime(frame["date_utc"], utc=True)
    if dates.isna().any() or dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError("Radar dates must be unique and increasing")
    alpha = frame[columns].to_numpy(dtype=float)
    transition = np.asarray(metadata["transition_matrix"], dtype=float)
    for values in (alpha, transition):
        if (
            values.ndim != 2
            or values.shape[1] != k
            or not np.isfinite(values).all()
            or (values < 0).any()
            or (values > 1).any()
            or not np.allclose(values.sum(axis=1), 1, atol=1e-10, rtol=0)
        ):
            raise ValueError("Invalid state probability vector or transition matrix")
    if transition.shape != (k, k):
        raise ValueError("Transition matrix disagrees with K")
    projected = alpha @ transition
    risk = int(metadata["high_risk_state"])
    if not 0 <= risk < k:
        raise ValueError("Invalid high-risk state")
    if not np.allclose(frame["prob_high_risk"], alpha[:, risk], atol=1e-10, rtol=0):
        raise ValueError("High-risk probability disagrees with state vector")
    if "prob_high_risk_next_day" in frame and not np.allclose(
        frame["prob_high_risk_next_day"], projected[:, risk], atol=1e-10, rtol=0
    ):
        raise ValueError("Next-day forecast disagrees with C2's exported forecast")
    last = frame.iloc[-1]
    current = int(alpha[-1].argmax())
    if int(last["state_id"]) != current or last["label"] != mapping[str(current)]:
        raise ValueError("Current regime disagrees with model mapping")
    as_of = pd.Timestamp(last["as_of_utc"])
    if as_of.tzinfo is None or as_of < dates.iloc[-1] + pd.Timedelta(days=1):
        raise ValueError("Signal precedes the closed UTC candle")
    states = pd.DataFrame(
        {
            "state_id": range(k),
            "label": [mapping[str(i)] for i in range(k)],
            "current_probability": alpha[-1],
            "next_day_probability": projected[-1],
            "persistence": np.diag(transition),
        }
    )
    return {
        "asset": metadata["asset"],
        "K": k,
        "model_run_id": metadata["model_run_id"],
        "date_utc": dates.iloc[-1],
        "as_of_utc": as_of.tz_convert("UTC"),
        "forecast_date_utc": dates.iloc[-1] + pd.Timedelta(days=1),
        "state_id": current,
        "label": mapping[str(current)],
        "state_probability": float(alpha[-1, current]),
        "high_risk_state": risk,
        "prob_high_risk": float(alpha[-1, risk]),
        "prob_high_risk_next_day": float(projected[-1, risk]),
        "seed_stability_status": metadata.get("seed_stability_status", "not_assessed"),
        "states": states,
    }
