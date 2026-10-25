"""Reproduce blueprint research without replacing the archived C2/C3 baseline."""

from __future__ import annotations

import copy
import warnings
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import yaml
from scipy.special import logsumexp

from src.models.data import ZCOLS, load_asset
from src.models.handoff import UnstableModelWarning, load_filtered
from src.models.inference import diagonal_variances
from src.research import drivers, economics, portfolio, robustness, trend
from src.utils.config import ROOT, file_hash, load_config, path_of, read_json, write_json


def explain_latest(frame, signals, bundle):
    """Exact additive Gaussian emission terms plus the causal state prior, not SHAP."""
    model = bundle["model"]
    variances = diagonal_variances(model)
    x = frame[ZCOLS].iloc[-1].to_numpy(dtype=float)
    terms = -0.5 * (np.log(2 * np.pi) + np.log(variances) + (x - model.means_) ** 2 / variances)
    k = model.n_components
    dates = pd.to_datetime(signals["date_utc"], utc=True)
    continuous = (
        len(signals) > 1
        and dates.iloc[-1] - dates.iloc[-2] == pd.Timedelta(days=1)
        and signals["segment_id"].iloc[-1] == signals["segment_id"].iloc[-2]
    )
    previous = (
        signals[[f"prob_state_{i}" for i in range(k)]].iloc[-2].to_numpy(dtype=float) if continuous else None
    )
    prior = previous @ model.transmat_ if continuous else model.startprob_
    with np.errstate(divide="ignore"):
        log_posterior = terms.sum(axis=1) + np.log(prior)
    posterior = np.exp(log_posterior - logsumexp(log_posterior))
    exported = signals[[f"prob_state_{i}" for i in range(k)]].iloc[-1].to_numpy(dtype=float)
    if not np.allclose(posterior, exported, atol=1e-10, rtol=0):
        raise ValueError("Emission explanation disagrees with C2 filtered posterior")
    result = pd.DataFrame(terms, columns=["log_density_return", "log_density_rv21", "log_density_volume"])
    result["state_id"], result["prior_probability"], result["posterior_probability"] = (
        range(k),
        prior,
        posterior,
    )
    result["date_utc"] = signals["date_utc"].iloc[-1]
    result["scope"] = (
        "exact diagonal Gaussian emission decomposition plus filtered prior; model explanation, not causality"
    )
    return result


def markdown_table(frame):
    def cell(value):
        if isinstance(value, float):
            return f"{value:.5g}" if np.isfinite(value) else "—"
        return str(value).replace("|", "/")

    header = "| " + " | ".join(map(str, frame.columns)) + " |\n"
    header += "| " + " | ".join("---" for _ in frame.columns) + " |\n"
    return header + "\n".join(
        "| " + " | ".join(cell(value) for value in row) + " |"
        for row in frame.itertuples(index=False, name=None)
    )


def write_paper(tables, manifest):
    economic = tables["economic"][
        [
            "asset",
            "state_id",
            "model_label",
            "economic_label",
            "direction",
            "mean_ci_low",
            "mean_ci_high",
            "volatility_ratio",
        ]
    ]
    benchmark = tables["benchmarks"].loc[
        lambda t: t["period"].isin(["validation", "test"]),
        ["asset", "method", "period", "K", "avg_log_score", "persistence"],
    ]
    performance = tables["portfolio"].loc[
        lambda t: t["scenario"].eq("baseline_close_to_close"),
        ["asset", "strategy", "CAGR", "ann_volatility", "Sharpe", "max_drawdown", "total_cost"],
    ]
    prediction = (
        tables["drivers_metrics"].loc[
            lambda t: t["period"].eq("test"), ["asset", "group", "n", "events", "Brier", "log_loss", "PR_AUC"]
        ]
        if not tables["drivers_metrics"].empty
        else pd.DataFrame()
    )
    content = f"""# AI Crypto Market Regime Detection

## Research report — reproducible exploratory extension

Generated UTC: {datetime.now(timezone.utc).isoformat()}. Core candles through
{manifest["data_through_utc"]}. Source: Binance BTC/ETH daily Spot; external sources
and acquisition failures are recorded in external_refresh_manifest.json.

### Abstract

We estimate latent regimes using frozen train-scaled Gaussian HMMs and evaluate
economic interpretation, initialization sensitivity, clustering comparisons,
transition proxies and defensive allocation. We retain all unfavorable results.
The original test has already been observed; this extension is exploratory and
does not constitute a newly untouched holdout or evidence of deployable alpha.

### Data and protocol

Chronological train ends 2023-05-05, validation ends 2025-01-24. New dates only
extend the evaluation tail. Core inputs are daily log return, 21-day realized
volatility and log(1 + quote volume USDT), standardized on train. No interpolated
returns across gaps; separate filtered and hindsight-smoothed outputs. External
features use publication-time as-of joins; observations older than seven days
are missing in the drivers experiment. Imputation/scaling is fitted on train only.
Historical macro values are current-vintage downloads, not a fully vintage-real-time
database; conservative time lags cannot eliminate all revision bias.

### RQ1 — number of states and initialization

Core K=2,3,4 is selected on predictive validation likelihood, with train fit
quality checks. A separate K=2..5 structured-initialization experiment uses both
KMeans initialization and volatility-quantile initialization, small seeded
perturbations and an initial 95% self-transition matrix. EM still learns the
matrix; it is not held at 95%. Configurations meeting seed-ARI criteria are
preferred, then validation likelihood. This stability is conditional on the
initializer family and does not negate instability under unrestricted starts.
Selection records are saved before test evaluation. K=5 is an optional candidate,
not an attempt to manufacture four economically named classes.

{markdown_table(benchmark)}

KMeans has no generative likelihood here: centroid distance is a separate metric,
never ranked against HMM/GMM log density. Higher persistence is not independently
proof of economic usefulness.

### RQ2 — economic meaning

Labels are inferred on train using paired moving-block bootstrap of returns and
fixed-model filtered weights, 1,000 replicates, 21-day blocks; 14/42-day sensitivity
is reported separately. Familywise bands use Bonferroni correction across mean,
volatility-ratio and tail contrasts for all K states. A minimum 100 weighted
effective days is required. Calm requires the upper volatility-ratio band below
0.85 and modest mean/vol ratio. Stress requires the lower ratio band above 1.25
and excess left-tail exposure with lower confidence bound above zero. Bull/Bear
require the entire mean-return band beyond +/-0.05% daily log return. These are
declared research conventions, not universally identified market classes.

{markdown_table(economic)}

Direction and risk are separate axes. Failure to establish Bull/Bear is a valid
finding, not a reason to rename a state on visual intuition. The model's original
label_map/IDs remain available; the research interpretation is frozen from train.
Intervals are conditional on the selected fitted model, do not refit HMM parameters,
and understate total uncertainty if initialization/selection uncertainty is ignored.

### RQ3 — macro/crypto transition proxies

Regularized logistic regression predicts a non-High-Risk to High-Risk transition
on the following contiguous day, using frozen HMM filtered hard labels as noisy
proxies. Predictors at t are paired to outcomes at t+1; split assignment follows
the outcome date. Regularization is selected on validation log loss. Compare
core-only, macro, macro/crypto and constant train-prevalence baseline on equal
periods. Coefficients are associations per standardized input, not causal effects
or p-values. This is NOT a non-homogeneous HMM and no such claim is made.

{markdown_table(prediction) if not prediction.empty else "Insufficient events: no fabricated driver estimates."}

Rare stress transitions, especially on ETH test, severely limit PR-AUC and
calibration inference. A model must beat its prevalence baseline to support
predictive utility; attractive coefficients alone are insufficient evidence.

### RQ4 — out-of-sample robustness

See research_hmm_stability.csv, C2_stability_summary.csv, research_benchmarks.csv
and C2_window_sensitivity.csv. Random-start core models remain flagged unstable.
Structured initialization, KMeans seed agreement, temporal persistence and
predictive density are reported separately. No latent state has observed ground
truth; log-score and ARI are not Bull/Bear classification accuracy.

### RQ5 — economic value

Fixed 40% annual volatility target, long/cash cap 1, no leverage, cash return zero.
Also report the fixed baseline regime-aware allocation and their multiplicative
combination. All use the same signal dates, opening fee, costs and execution
scenario. Parameters are declared in research.yaml, not optimized on test.
Close-to-close execution is idealized; next-open and drift-adjusted cross-checks
are shown separately. These remain research assumptions without spread, slippage
or market impact. Original B08/NAV are retained for audit.

{markdown_table(performance)}

Paired 21-day block bootstrap intervals for differences in Sharpe, CAGR and maximum
drawdown are in research_portfolio_uncertainty.csv. Signals/rules are held fixed,
not refitted; intervals are exploratory, not an untouched confirmatory test.

### Product and reproducibility

Run `python scripts/complete_research.py` after the C1/C2/C3 pipeline; see README.
Dashboard retains its established visual theme. It distinguishes model labels,
train-derived interpretation, state probabilities, next-day marginal distribution,
model-instability warnings and simulated performance. The exact explanation of
the latest observation decomposes diagonal-Gaussian log emission terms and the
filtered prior; it is a model calculation, not a macro causal explanation.

### Limitations and conclusions

The project is a probabilistic research tool, not a price forecaster or investment
recommendation. Core EM can reach different local optima; overlapping RV windows
violate exact emission independence; quote volume is not full market liquidity.
Some external histories are unavailable or limited. Cached data is retained on
source failure. Revised historical external data and endogenous regime proxies
limit causal interpretation. New holdout observations are needed before making
prospective performance claims. NHHMM, Markov-switching GARCH, Bayesian change-point
and RL are not implemented; the report does not represent them as completed.

### References and implementation sources

- Hamilton (1989), Econometrica 57(2), 357–384: regime-switching framework.
- Rabiner (1989), Proceedings of the IEEE 77(2), 257–286: HMM inference.
- hmmlearn tutorial: https://hmmlearn.readthedocs.io/en/stable/tutorial.html
- scikit-learn leakage guidance: https://scikit-learn.org/stable/common_pitfalls.html
- Temporal evaluation: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- Probability assessment: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html
"""
    liquidity = tables["liquidity"].loc[
        lambda t: t["period"].eq("train"),
        ["asset", "state_id", "mean_amihud_illiquidity", "train_ci_low", "train_ci_high", "n_hard"],
    ]
    liquidity_section = (
        """### Liquidity interpretation

Amihud uses abs(daily simple return) / daily quote-volume USD. Larger values
indicate a less liquid proxy, not measured order-book depth or spread. Weighted
state means and pointwise conditional train block-bootstrap intervals are below.
Liquidity and return-volatility rankings need not agree. Absolute quote-volume
levels can also encode secular market growth; states with little later occupancy
must not automatically be presented as persistent economic market classes.

"""
        + markdown_table(liquidity)
        + "\n\n"
    )
    content = content.replace(
        "### RQ3 — macro/crypto transition proxies",
        liquidity_section + "### RQ3 — macro/crypto transition proxies",
    )
    if not tables.get("trend_evidence", pd.DataFrame()).empty:
        evidence = tables["trend_evidence"][
            [
                "asset",
                "state_id",
                "economic_label",
                "direction",
                "mean_ci_low",
                "mean_ci_high",
                "volatility_ratio",
            ]
        ]
        comparisons = tables["trend_comparisons"].loc[
            lambda t: t["period"].isin(["validation", "test"]),
            ["asset", "method", "period", "K", "avg_log_score", "persistence"],
        ]
        state_stats = tables["trend_stats"][
            [
                "asset",
                "period",
                "state_id",
                "economic_label",
                "mean_return",
                "annualized_volatility",
                "n_hard",
            ]
        ]
        trend_section = (
            """### Additional feature-family experiment — trend-aware regimes

To investigate directional regimes, augment the three core inputs with trailing
7/30-day sums of log returns, computed within segments after closed candles.
Drop warm-up rows and fit all five scales on train; keep the original split dates.
Select K=2..5 and seed within this family on initialization stability and validation
likelihood. The 5-dimensional density is **not comparable in level** to the
3-dimensional core likelihood. A separate matched-K GMM uses the same five inputs.
Overlapping momentum/RV windows weaken the diagonal conditional-independence
assumption. This is an exploratory feature extension, not a replacement for the
archived core model or proof that Bull/Bear exist as ground-truth classes.

Train-frozen labels and conditional mean intervals:

"""
            + markdown_table(evidence)
            + "\n\nSame-feature-space comparison:\n\n"
            + markdown_table(comparisons)
        )
        trend_section += (
            "\n\nOut-of-sample meanings, with labels kept frozen (contrary signs are retained):\n\n"
            + markdown_table(state_stats)
        )
        trend_section += (
            "\n\nFixed baseline allocation on trend-HMM filtered High-Risk:\n\n"
            + markdown_table(
                tables["trend_portfolio"][["asset", "strategy", "n_days", "CAGR", "Sharpe", "max_drawdown"]]
            )
        )
        trend_section += "\n\nA Bull label describes contemporaneous fitted-state returns on train; it is not a\nforecast of tomorrow's positive return. All subsequent sample results remain\nexploratory because the original test has been observed.\n\n"
        content = content.replace(
            "### Product and reproducibility", trend_section + "### Product and reproducibility"
        )
    destination = ROOT / "paper/research_report.md"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def run():
    cfg = load_config()
    settings = yaml.safe_load((ROOT / "config/research.yaml").read_text(encoding="utf-8"))
    tables_dir, metadata_dir = path_of(cfg, "tables"), path_of(cfg, "metadata")
    models_dir, predictions_dir = (
        path_of(cfg, "models") / "research",
        path_of(cfg, "predictions") / "research",
    )
    models_dir.mkdir(exist_ok=True)
    predictions_dir.mkdir(exist_ok=True)
    core = read_json(metadata_dir / "model_manifest.json")
    if core["status"] != "complete":
        raise ValueError("Complete C2 before research")
    source_files = sorted((ROOT / "src").rglob("*.py")) + [ROOT / "config/research.yaml"]
    input_files = [metadata_dir / "model_manifest.json", metadata_dir / "backtest_manifest.json"]
    input_files += sorted(path_of(cfg, "processed").glob("*.parquet")) + sorted(
        path_of(cfg, "raw").glob("*.csv")
    )
    manifest = {
        "status": "running",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_hash": file_hash(ROOT / "config/research.yaml"),
        "source_hashes": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in source_files},
        "input_hashes": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in input_files},
        "assets": {},
        "data_through_utc": {a: v["c1_provenance"]["data_through_utc"] for a, v in core["assets"].items()},
        "scope": settings["scope"],
        "production_model_replaced": False,
    }
    write_json(manifest, metadata_dir / "research_manifest.json")
    collected = {
        key: []
        for key in [
            "economic",
            "liquidity",
            "economic_sensitivity",
            "explanations",
            "drivers_metrics",
            "drivers_coefficients",
            "drivers_predictions",
            "portfolio",
            "nav",
            "uncertainty",
            "fits",
            "stability",
            "benchmarks",
            "trend_fits",
            "trend_stability",
            "trend_evidence",
            "trend_sensitivity",
            "trend_stats",
            "trend_comparisons",
            "trend_portfolio",
            "trend_nav",
        ]
    }
    try:
        for asset in cfg["assets"]:
            print(f"Research: {asset}", flush=True)
            frame, _, _ = load_asset(cfg, asset)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UnstableModelWarning)
                signals, info = load_filtered(cfg, asset, acknowledge_unstable=True)
            k = info["K"]
            mask = frame["split"].eq("train").to_numpy()
            probabilities = signals[[f"prob_state_{i}" for i in range(k)]].to_numpy()
            evidence = economics.economic_evidence(
                frame.loc[mask],
                probabilities[mask],
                info["label_map"],
                settings["economics"],
                settings["seed"],
            )
            sensitivity = []
            for block in (14, 42):
                alternate = copy.deepcopy(settings["economics"])
                alternate["block_days"] = block
                sensitivity.append(
                    economics.economic_evidence(
                        frame.loc[mask], probabilities[mask], info["label_map"], alternate, settings["seed"]
                    )
                )
            all_blocks = pd.concat([evidence, *sensitivity], ignore_index=True)
            stable_labels = all_blocks.groupby("state_id")["economic_label"].nunique().eq(1)
            evidence["label_stable_across_block_lengths"] = evidence["state_id"].map(stable_labels)
            collected["economic"].append(evidence.assign(asset=asset))
            collected["economic_sensitivity"].append(all_blocks.assign(asset=asset))
            liquidity = economics.liquidity_profiles(
                frame, probabilities, info["label_map"], settings["economics"], settings["seed"]
            )
            collected["liquidity"].append(liquidity.assign(asset=asset))
            explanation = explain_latest(
                frame, signals, joblib.load(path_of(cfg, "models") / f"hmm_{asset.lower()}.joblib")
            )
            collected["explanations"].append(explanation.assign(asset=asset))
            scores, coefficients, driver_info, driver_predictions = drivers.run_asset(
                cfg, frame, signals, info, settings["drivers"], metadata_dir, models_dir
            )
            for key, result in [
                ("drivers_metrics", scores),
                ("drivers_coefficients", coefficients),
                ("drivers_predictions", driver_predictions),
            ]:
                if not result.empty:
                    collected[key].append(result)
            perf, nav, intervals = portfolio.run_asset(
                cfg, frame, asset, settings["portfolio"], settings["seed"]
            )
            collected["portfolio"].append(perf)
            collected["nav"].append(nav)
            collected["uncertainty"].append(intervals)
            fits, stability, benchmarks, robust_info = robustness.run_asset(
                frame, asset, info, settings["robust_hmm"], models_dir, predictions_dir, metadata_dir
            )
            collected["fits"].append(fits)
            collected["stability"].append(stability)
            collected["benchmarks"].append(benchmarks)
            manifest["assets"][asset] = {
                "model_run_id": info["model_run_id"],
                "economic_label_map": {
                    str(row.state_id): row.economic_label for row in evidence.itertuples()
                },
                "drivers": driver_info,
                "robust_hmm": robust_info,
            }
            if settings.get("trend_hmm", {}).get("enabled"):
                trend_settings = copy.deepcopy(settings["robust_hmm"])
                trend_settings["initializers"] = settings["trend_hmm"]["initializers"]
                result = trend.run_asset(
                    frame,
                    asset,
                    info,
                    trend_settings,
                    settings["economics"],
                    settings["seed"],
                    models_dir,
                    predictions_dir,
                    metadata_dir,
                )
                for key in (
                    "fits",
                    "stability",
                    "evidence",
                    "sensitivity",
                    "stats",
                    "comparisons",
                    "portfolio",
                    "nav",
                ):
                    collected[f"trend_{key}"].append(result[key])
                manifest["assets"][asset]["trend_hmm"] = result["metadata"]
        tables = {
            key: pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
            for key, parts in collected.items()
        }
        names = {
            "economic": "research_economic_labels.csv",
            "liquidity": "research_liquidity_profiles.csv",
            "economic_sensitivity": "research_economic_sensitivity.csv",
            "explanations": "research_emission_explanation.csv",
            "drivers_metrics": "research_drivers_metrics.csv",
            "drivers_coefficients": "B06_drivers.csv",
            "portfolio": "research_portfolio.csv",
            "uncertainty": "research_portfolio_uncertainty.csv",
            "fits": "research_hmm_candidates.csv",
            "stability": "research_hmm_stability.csv",
            "benchmarks": "research_benchmarks.csv",
            "trend_fits": "research_trend_fits.csv",
            "trend_stability": "research_trend_stability.csv",
            "trend_evidence": "research_trend_evidence.csv",
            "trend_stats": "research_trend_stats.csv",
            "trend_sensitivity": "research_trend_sensitivity.csv",
            "trend_comparisons": "research_trend_comparisons.csv",
            "trend_portfolio": "research_trend_portfolio.csv",
        }
        for key, name in names.items():
            if not tables[key].empty:
                tables[key].to_csv(tables_dir / name, index=False)
        tables["nav"].to_csv(predictions_dir / "portfolio_nav.csv", index=False)
        if not tables["drivers_predictions"].empty:
            tables["drivers_predictions"].to_csv(predictions_dir / "drivers_predictions.csv", index=False)
        if not tables["trend_nav"].empty:
            tables["trend_nav"].to_csv(predictions_dir / "trend_portfolio_nav.csv", index=False)
        write_paper(tables, manifest)
        if any(
            file_hash(ROOT / p) != h
            for section in ("input_hashes", "source_hashes")
            for p, h in manifest[section].items()
        ):
            raise ValueError("Research input/source changed during execution")
        outputs = [tables_dir / name for key, name in names.items() if not tables[key].empty]
        outputs += (
            list(models_dir.glob("*.joblib"))
            + list(predictions_dir.glob("*.csv"))
            + [ROOT / "paper/research_report.md"]
        )
        manifest["output_hashes"] = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in outputs}
        manifest["status"] = "complete"
    except Exception as exc:
        manifest["status"], manifest["error"] = "failed", str(exc)
        raise
    finally:
        manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(manifest, metadata_dir / "research_manifest.json")
    return manifest


if __name__ == "__main__":
    run()
