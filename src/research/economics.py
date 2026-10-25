"""Train-frozen economic interpretation with conditional moving-block uncertainty."""

from __future__ import annotations

import numpy as np
import pandas as pd


def moving_blocks(n, replicates, block_days, seed):
    if n < 2 or not 1 <= block_days <= n or replicates < 100:
        raise ValueError("Invalid moving-block bootstrap dimensions")
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n - block_days + 1, size=(replicates, int(np.ceil(n / block_days))))
    return (starts[..., None] + np.arange(block_days)).reshape(replicates, -1)[:, :n]


def economic_evidence(train, probabilities, original_mapping, settings, seed):
    """Bootstrap paired (return, fixed-model posterior) blocks on TRAIN only.

    Intervals are conditional on the fitted model and mapping; no refit/causal
    claim. Bonferroni adjustment covers mean, volatility ratio and tail contrast
    across all states. These are research conventions, not universal definitions.
    """
    if not train["split"].eq("train").all():
        raise ValueError("Economic labels must be determined on train only")
    r = train["log_return"].to_numpy(dtype=float)
    p = np.asarray(probabilities, dtype=float)
    if (
        len(r) != len(p)
        or not np.isfinite(r).all()
        or not np.isfinite(p).all()
        or (p < 0).any()
        or not np.allclose(p.sum(axis=1), 1)
    ):
        raise ValueError("Invalid train observations or posteriors")
    n, k = p.shape
    cutoff = float(np.quantile(r, settings["tail_quantile"]))
    tail = r <= cutoff
    mass = p.sum(axis=0)
    mean = p.T @ r / mass
    vol = np.sqrt((p * (r[:, None] - mean) ** 2).sum(axis=0) / mass)
    overall_vol = float(r.std(ddof=0))
    tail_rate = p.T @ tail / mass
    effective = mass**2 / (p**2).sum(axis=0)
    blocks = moving_blocks(n, settings["bootstrap_replicates"], settings["block_days"], seed)
    boot_mean, boot_ratio, boot_tail = [], [], []
    for indices in np.array_split(blocks, max(1, len(blocks) // 100)):
        rb, pb = r[indices], p[indices]
        wb = pb.sum(axis=1)
        mu = (pb * rb[..., None]).sum(axis=1) / wb
        sd = np.sqrt((pb * (rb[..., None] - mu[:, None, :]) ** 2).sum(axis=1) / wb)
        boot_mean.extend(mu)
        boot_ratio.extend(sd / rb.std(axis=1, ddof=0)[:, None])
        boot_tail.extend(
            (pb * tail[indices][..., None]).sum(axis=1) / wb - tail[indices].mean(axis=1)[:, None]
        )
    error = (1 - settings["confidence"]) / (3 * k)
    intervals = [
        np.quantile(np.asarray(values), [error / 2, 1 - error / 2], axis=0)
        for values in [boot_mean, boot_ratio, boot_tail]
    ]
    rows = []
    for state in range(k):
        lo, hi = intervals[0][:, state]
        vol_lo, vol_hi = intervals[1][:, state]
        tail_lo, tail_hi = intervals[2][:, state]
        enough = effective[state] >= settings["minimum_effective_days"]
        direction = "Uncertain"
        if enough and lo > settings["direction_min_daily_return"]:
            direction = "Bull"
        elif enough and hi < -settings["direction_min_daily_return"]:
            direction = "Bear"
        risk = "Intermediate"
        if enough and vol_lo > settings["stress_volatility_ratio_lower"] and tail_lo > 0:
            risk = "Stress"
        elif (
            enough
            and vol_hi < settings["calm_volatility_ratio_upper"]
            and abs(mean[state]) < 0.15 * vol[state]
        ):
            risk = "Calm"
        label = (
            risk
            if risk in ("Calm", "Stress")
            else direction
            if direction != "Uncertain"
            else original_mapping[str(state)]
        )
        rows.append(
            {
                "state_id": state,
                "model_label": original_mapping[str(state)],
                "economic_label": label,
                "direction": direction,
                "risk_profile": risk,
                "mean_daily_log_return": mean[state],
                "mean_ci_low": lo,
                "mean_ci_high": hi,
                "daily_volatility": vol[state],
                "volatility_ratio": vol[state] / overall_vol,
                "vol_ratio_ci_low": vol_lo,
                "vol_ratio_ci_high": vol_hi,
                "left_tail_rate": tail_rate[state],
                "overall_tail_rate": float(tail.mean()),
                "tail_contrast_ci_low": tail_lo,
                "tail_contrast_ci_high": tail_hi,
                "train_tail_cutoff": cutoff,
                "posterior_mass_days": mass[state],
                "weighted_effective_days": effective[state],
                "sufficient_weighted_days": bool(enough),
                "block_days": settings["block_days"],
                "replicates": settings["bootstrap_replicates"],
                "familywise_confidence": settings["confidence"],
                "scope": "train only; conditional on fitted model; no refit; post-hoc exploratory interpretation",
            }
        )
    return pd.DataFrame(rows)


def liquidity_profiles(frame, probabilities, mapping, settings, seed):
    """Amihud is an observable proxy, not order-book depth; uncertainty uses train only."""
    p = np.asarray(probabilities)
    records = []
    train_mask = frame["split"].eq("train").to_numpy()
    train = frame.loc[train_mask]
    values = train["amihud_illiq"].to_numpy(dtype=float)
    weights = p[train_mask]
    indices = moving_blocks(len(train), settings["bootstrap_replicates"], settings["block_days"], seed)
    intervals = {}
    for state in range(p.shape[1]):
        observed = np.isfinite(values)
        weighted = weights[:, state] * observed
        boot = (weighted[indices] * np.nan_to_num(values)[indices]).sum(axis=1) / weighted[indices].sum(
            axis=1
        )
        low, high = np.quantile(boot, [0.025, 0.975])
        intervals[state] = (float(low), float(high))
    for period in ("train", "validation", "test"):
        mask = frame["split"].eq(period).to_numpy()
        observations = frame.loc[mask, "amihud_illiq"].to_numpy(dtype=float)
        valid = np.isfinite(observations)
        for state in range(p.shape[1]):
            w = p[mask, state] * valid
            mass = w.sum()
            mean = float(w @ np.nan_to_num(observations) / mass) if mass else np.nan
            low, high = intervals[state] if period == "train" else (np.nan, np.nan)
            records.append(
                {
                    "state_id": state,
                    "model_label": mapping[str(state)],
                    "period": period,
                    "mean_amihud_illiquidity": mean,
                    "train_ci_low": low,
                    "train_ci_high": high,
                    "posterior_mass_valid_days": mass,
                    "n_hard": int((p[mask].argmax(axis=1) == state).sum()),
                    "definition": "abs(simple_return) / quote_volume_USDT; larger = less liquid proxy",
                    "scope": "weighted description; train conditional block CI; not order-book liquidity or causality",
                }
            )
    return pd.DataFrame(records)
