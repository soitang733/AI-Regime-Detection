"""Calendar-aware descriptive charts; separated from Streamlit for testing."""

from __future__ import annotations

import numpy as np
import pandas as pd


def forward_returns(frame, horizons=(5, 10, 20)):
    out = frame.copy().sort_values("date").reset_index(drop=True)
    dates = pd.to_datetime(out["date"], utc=True)
    boundary = out["segment_id"].ne(out["segment_id"].shift()) | dates.diff().ne(pd.Timedelta(days=1))
    groups = boundary.cumsum()
    cumulative = out.groupby(groups)["log_return"].cumsum()
    for horizon in horizons:
        out[f"fwd_{horizon}"] = np.expm1(cumulative.groupby(groups).shift(-horizon) - cumulative)
    out["entry"] = out["state_id"].ne(out["state_id"].shift()) & ~boundary
    return out


def window_statistics(features, probabilities, metadata, annualization=365):
    """Stats on precisely the visible dates and probability mode; P remains train-frozen."""
    k = metadata["K"]
    left = features[["date_utc", "log_return"]].copy()
    left["date_utc"] = pd.to_datetime(left["date_utc"], utc=True)
    right = probabilities.copy()
    right["date_utc"] = pd.to_datetime(right["date_utc"], utc=True)
    joined = left.merge(right, on="date_utc", validate="one_to_one")
    rows = []
    for state in range(k):
        weight = joined[f"prob_state_{state}"].to_numpy(dtype=float)
        r = joined["log_return"].to_numpy(dtype=float)
        mass = weight.sum()
        mean = float(weight @ r / mass) if mass else np.nan
        sd = float(np.sqrt(weight @ ((r - mean) ** 2) / mass)) if mass else np.nan
        persistence = metadata["transition_matrix"][state][state]
        rows.append(
            {
                "state_id": state,
                "n_days": int(joined["state_id"].eq(state).sum()),
                "n_window": len(joined),
                "posterior_mass_days": mass,
                "mean_return": mean,
                "annualized_volatility": sd * np.sqrt(annualization),
                "persistence": persistence,
                "expected_duration": 1 / (1 - persistence) if persistence < 1 else np.inf,
            }
        )
    return pd.DataFrame(rows)
