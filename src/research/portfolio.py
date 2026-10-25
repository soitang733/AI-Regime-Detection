"""Fixed-rule volatility benchmarks and paired block uncertainty, no test optimization."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.evaluation.backtest import performance_metrics, regime_weights, simulate
from src.evaluation.backtest_run import build_inputs, load_backtest_config
from src.research.economics import moving_blocks


def volatility_weights(rv, annual_target, annualization=365):
    rv = np.asarray(rv, dtype=float)
    if annual_target <= 0 or not np.isfinite(rv).all() or (rv < 0).any():
        raise ValueError("Invalid volatility targeting inputs")
    denominator = rv * np.sqrt(annualization)
    return np.minimum(1, np.divide(annual_target, denominator, out=np.ones_like(rv), where=denominator > 0))


def _bootstrap_metrics(net):
    sd = net.std(axis=1, ddof=1)
    sharpe = np.divide(net.mean(axis=1) * np.sqrt(365), sd, out=np.full(len(net), np.nan), where=sd > 0)
    nav = np.cumprod(1 + net, axis=1)
    peaks = np.maximum.accumulate(np.column_stack([np.ones(len(net)), nav]), axis=1)[:, 1:]
    return {
        "Sharpe": sharpe,
        "CAGR": nav[:, -1] ** (365 / net.shape[1]) - 1,
        "max_drawdown": (nav / peaks - 1).min(axis=1),
    }


def run_asset(cfg, frame, asset, settings, seed):
    bt = load_backtest_config()
    inputs, metadata, _ = build_inputs(cfg, bt, asset)
    inputs["rv_date"] = inputs["signal_date_utc"].dt.strftime("%Y-%m-%d")
    inputs = inputs.merge(
        frame[["date_utc", "rv21"]].rename(columns={"date_utc": "rv_date"}),
        on="rv_date",
        validate="one_to_one",
    )
    a, m, costs = bt["allocation"], bt["metrics"], bt["costs"]
    vol_weight = volatility_weights(
        inputs["rv21"], settings["annual_volatility_target"], m["annualization_days"]
    )
    risk_weight = regime_weights(
        inputs["prob_high_risk"], a["risk_threshold"], a["weight_risk_on"], a["weight_risk_off"]
    )
    weights = {
        "buy_and_hold": np.full(len(inputs), a["weight_risk_on"]),
        "regime_aware": risk_weight,
        "volatility_targeting": vol_weight,
        "regime_volatility_targeting": vol_weight * risk_weight,
    }
    performance, navs = [], []
    for scenario, rules in bt["scenarios"].items():
        mask = (
            np.ones(len(inputs), dtype=bool)
            if rules["return_basis"] == "close_to_close"
            else inputs["next_open_return"].notna().to_numpy()
        )
        sub = inputs.loc[mask].reset_index(drop=True)
        returns = sub[
            "target_simple_return" if rules["return_basis"] == "close_to_close" else "next_open_return"
        ]
        calendar_days = (sub["return_date_utc"].iloc[-1] - sub["return_date_utc"].iloc[0]).days + 1
        for name, weight in weights.items():
            sim = simulate(
                weight[mask],
                returns,
                fee_rate=costs["fee_rate"],
                turnover_method=rules["turnover_method"],
                initial_weight=a["initial_weight"],
                cash_return=a["cash_return_daily"],
            )
            metrics = performance_metrics(
                sim["net"],
                sim["nav"],
                sim["turnover"],
                sim["fee"],
                calendar_days,
                m["annualization_days"],
                m["risk_free_daily"],
            )
            performance.append(
                {
                    "asset": asset,
                    "strategy": name,
                    "scenario": scenario,
                    "n_days": len(sub),
                    "start": sub["return_date_utc"].iloc[0].strftime("%Y-%m-%d"),
                    "end": sub["return_date_utc"].iloc[-1].strftime("%Y-%m-%d"),
                    **metrics,
                    "annual_vol_target": settings["annual_volatility_target"],
                    "fee_rate": costs["fee_rate"],
                    "model_run_id": metadata["model_run_id"],
                    "parameters_tuned_on_test": False,
                    "interpretation": "fixed rules; post-hoc exploratory evaluation; not an untouched new holdout",
                }
            )
            sim = sim.assign(
                asset=asset,
                strategy=name,
                scenario=scenario,
                date_utc=sub["return_date_utc"].dt.strftime("%Y-%m-%d"),
                signal_date_utc=sub["signal_date_utc"].dt.strftime("%Y-%m-%d"),
                as_of_utc=sub["as_of_utc"].astype(str),
            )
            navs.append(sim)
    nav = pd.concat(navs, ignore_index=True)
    baseline = nav.loc[nav["scenario"].eq("baseline_close_to_close")].pivot(
        index="date_utc", columns="strategy", values="net"
    )
    indices = moving_blocks(len(baseline), settings["bootstrap_replicates"], settings["block_days"], seed)
    benchmark = _bootstrap_metrics(baseline["buy_and_hold"].to_numpy()[indices])
    intervals = []
    for name in weights:
        if name == "buy_and_hold":
            continue
        boot = _bootstrap_metrics(baseline[name].to_numpy()[indices])
        for metric in benchmark:
            low, high = np.nanquantile(boot[metric] - benchmark[metric], [0.025, 0.975])
            intervals.append(
                {
                    "asset": asset,
                    "strategy": name,
                    "difference_vs": "buy_and_hold",
                    "metric": metric,
                    "ci_low": low,
                    "ci_high": high,
                    "block_days": settings["block_days"],
                    "replicates": settings["bootstrap_replicates"],
                    "scope": "paired block bootstrap; fixed signals/rules; no refit; exploratory",
                }
            )
    return pd.DataFrame(performance), nav, pd.DataFrame(intervals)
