# AI Crypto Market Regime Detection

## Research report — reproducible exploratory extension

Generated UTC: 2026-10-24T11:59:45.946875+00:00. Core candles through
{'BTC': '2026-10-23', 'ETH': '2026-10-23'}. Source: Binance BTC/ETH daily Spot; external sources
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

| asset | method | period | K | avg_log_score | persistence |
| --- | --- | --- | --- | --- | --- |
| BTC | HMM_structured | validation | 5 | -2.3796 | 0.94913 |
| BTC | KMeans | validation | 3 | — | 0.72496 |
| BTC | GMM_matched_K | validation | 5 | -3.3565 | 0.72337 |
| BTC | HMM_structured | test | 5 | -2.2534 | 0.96855 |
| BTC | KMeans | test | 3 | — | 0.72642 |
| BTC | GMM_matched_K | test | 5 | -3.5878 | 0.71855 |
| ETH | HMM_structured | validation | 5 | -2.182 | 0.98251 |
| ETH | KMeans | validation | 4 | — | 0.7806 |
| ETH | GMM_matched_K | validation | 5 | -3.6211 | 0.80922 |
| ETH | HMM_structured | test | 5 | -2.3199 | 0.95912 |
| ETH | KMeans | test | 4 | — | 0.72484 |
| ETH | GMM_matched_K | test | 5 | -3.4876 | 0.79403 |

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

| asset | state_id | model_label | economic_label | direction | mean_ci_low | mean_ci_high | volatility_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BTC | 0 | High-Vol | Stress | Uncertain | -0.0067696 | 0.004589 | 1.4375 |
| BTC | 1 | State 1 | State 1 | Uncertain | -0.0016436 | 0.0044076 | 0.86813 |
| BTC | 2 | Low-Vol | Calm | Uncertain | -0.0025647 | 0.0043602 | 0.52739 |
| ETH | 0 | State 0 | State 0 | Uncertain | -0.0049314 | 0.005421 | 0.86621 |
| ETH | 1 | Low-Vol | Calm | Uncertain | -0.0020832 | 0.00766 | 0.64773 |
| ETH | 2 | High-Vol | Stress | Uncertain | -0.015886 | 0.010331 | 1.7225 |
| ETH | 3 | State 3 | State 3 | Uncertain | -0.0051502 | 0.0075482 | 0.98822 |

Direction and risk are separate axes. Failure to establish Bull/Bear is a valid
finding, not a reason to rename a state on visual intuition. The model's original
label_map/IDs remain available; the research interpretation is frozen from train.
Intervals are conditional on the selected fitted model, do not refit HMM parameters,
and understate total uncertainty if initialization/selection uncertainty is ignored.

### Liquidity interpretation

Amihud uses abs(daily simple return) / daily quote-volume USD. Larger values
indicate a less liquid proxy, not measured order-book depth or spread. Weighted
state means and pointwise conditional train block-bootstrap intervals are below.
Liquidity and return-volatility rankings need not agree. Absolute quote-volume
levels can also encode secular market growth; states with little later occupancy
must not automatically be presented as persistent economic market classes.

| asset | state_id | mean_amihud_illiquidity | train_ci_low | train_ci_high | n_hard |
| --- | --- | --- | --- | --- | --- |
| BTC | 0 | 5.5297e-11 | 3.614e-11 | 7.7157e-11 | 506 |
| BTC | 1 | 3.6724e-11 | 2.8251e-11 | 4.5714e-11 | 950 |
| BTC | 2 | 3.5964e-11 | 2.4542e-11 | 4.9113e-11 | 435 |
| ETH | 0 | 4.2007e-10 | 3.6374e-10 | 4.7182e-10 | 819 |
| ETH | 1 | 3.7887e-11 | 2.8322e-11 | 5.0116e-11 | 357 |
| ETH | 2 | 1.8265e-10 | 9.7795e-11 | 2.9312e-10 | 213 |
| ETH | 3 | 2.4945e-11 | 2.1882e-11 | 2.9151e-11 | 502 |

### RQ3 — macro/crypto transition proxies

Regularized logistic regression predicts a non-High-Risk to High-Risk transition
on the following contiguous day, using frozen HMM filtered hard labels as noisy
proxies. Predictors at t are paired to outcomes at t+1; split assignment follows
the outcome date. Regularization is selected on validation log loss. Compare
core-only, macro, macro/crypto and constant train-prevalence baseline on equal
periods. Coefficients are associations per standardized input, not causal effects
or p-values. This is NOT a non-homogeneous HMM and no such claim is made.

| asset | group | n | events | Brier | log_loss | PR_AUC |
| --- | --- | --- | --- | --- | --- | --- |
| BTC | core | 611 | 2 | 0.0032422 | 0.020062 | 0.049603 |
| BTC | macro | 611 | 2 | 0.0038517 | 0.02713 | 0.013759 |
| BTC | macro_crypto | 611 | 2 | 0.0032947 | 0.021801 | 0.016591 |
| BTC | train_prevalence_baseline | 611 | 2 | 0.0033573 | 0.027262 | 0.0032733 |
| ETH | core | 635 | 2 | 0.0031637 | 0.02199 | 0.012066 |
| ETH | macro | 635 | 2 | 0.0035247 | 0.022787 | 0.010238 |
| ETH | macro_crypto | 635 | 2 | 0.003408 | 0.022713 | 0.0081346 |
| ETH | train_prevalence_baseline | 635 | 2 | 0.0031733 | 0.023812 | 0.0031496 |

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

| asset | strategy | CAGR | ann_volatility | Sharpe | max_drawdown | total_cost |
| --- | --- | --- | --- | --- | --- | --- |
| BTC | buy_and_hold | -0.1369 | 0.42987 | -0.12777 | -0.52972 | 0.001 |
| BTC | regime_aware | -0.16794 | 0.41264 | -0.23856 | -0.55092 | 0.004 |
| BTC | volatility_targeting | -0.12707 | 0.38136 | -0.16552 | -0.51727 | 0.0090928 |
| BTC | regime_volatility_targeting | -0.14894 | 0.37634 | -0.24005 | -0.53393 | 0.010432 |
| ETH | buy_and_hold | -0.17119 | 0.69081 | 0.069844 | -0.67553 | 0.001 |
| ETH | regime_aware | -0.17486 | 0.68818 | 0.061052 | -0.66274 | 0.004 |
| ETH | volatility_targeting | -0.10708 | 0.46162 | -0.017621 | -0.57013 | 0.016262 |
| ETH | regime_volatility_targeting | -0.10975 | 0.46095 | -0.024807 | -0.56361 | 0.017451 |

Paired 21-day block bootstrap intervals for differences in Sharpe, CAGR and maximum
drawdown are in research_portfolio_uncertainty.csv. Signals/rules are held fixed,
not refitted; intervals are exploratory, not an untouched confirmatory test.

### Additional feature-family experiment — trend-aware regimes

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

| asset | state_id | economic_label | direction | mean_ci_low | mean_ci_high | volatility_ratio |
| --- | --- | --- | --- | --- | --- | --- |
| BTC | 0 | Bull | Bull | 0.003878 | 0.011079 | 1.0105 |
| BTC | 1 | Stress | Uncertain | -0.019466 | 0.00098139 | 1.6833 |
| BTC | 2 | Calm | Uncertain | -0.0031068 | 0.0020785 | 0.63609 |
| BTC | 3 | State 3 | Uncertain | -0.0052496 | 0.0011585 | 0.7998 |
| ETH | 0 | Calm | Uncertain | -0.0036003 | 0.0037244 | 0.62807 |
| ETH | 1 | State 1 | Uncertain | -0.0010346 | 0.0067788 | 0.73366 |
| ETH | 2 | Bull | Bull | 0.0010648 | 0.014623 | 1.1257 |
| ETH | 3 | State 3 | Uncertain | -0.015817 | 0.0019421 | 1.2076 |
| ETH | 4 | High-Vol | Uncertain | -0.1856 | 0.058728 | 2.5235 |

Same-feature-space comparison:

| asset | method | period | K | avg_log_score | persistence |
| --- | --- | --- | --- | --- | --- |
| BTC | HMM_trend_5d | validation | 4 | -4.8558 | 0.94436 |
| BTC | GMM_trend_5d | validation | 4 | -5.0276 | 0.74086 |
| BTC | HMM_trend_5d | test | 4 | -4.9709 | 0.96069 |
| BTC | GMM_trend_5d | test | 4 | -4.9937 | 0.83333 |
| ETH | HMM_trend_5d | validation | 5 | -4.3927 | 0.98092 |
| ETH | GMM_trend_5d | validation | 5 | -5.3227 | 0.82194 |
| ETH | HMM_trend_5d | test | 5 | -4.6403 | 0.96384 |
| ETH | GMM_trend_5d | test | 5 | -5.5568 | 0.82704 |

Out-of-sample meanings, with labels kept frozen (contrary signs are retained):

| asset | period | state_id | economic_label | mean_return | annualized_volatility | n_hard |
| --- | --- | --- | --- | --- | --- | --- |
| BTC | train | 0 | Bull | 0.0074315 | 0.72609 | 613 |
| BTC | train | 1 | Stress | -0.0079578 | 1.2096 | 245 |
| BTC | train | 2 | Calm | -0.00047215 | 0.45708 | 540 |
| BTC | train | 3 | State 3 | -0.0019473 | 0.57472 | 464 |
| BTC | validation | 0 | Bull | 0.0067325 | 0.55248 | 167 |
| BTC | validation | 1 | Stress | -0.035394 | 0.76383 | 1 |
| BTC | validation | 2 | Calm | 0.0002246 | 0.26827 | 103 |
| BTC | validation | 3 | State 3 | 0.00041454 | 0.4671 | 359 |
| BTC | test | 0 | Bull | 0.005396 | 0.40759 | 84 |
| BTC | test | 1 | Stress | -0.003427 | 0.83625 | 25 |
| BTC | test | 2 | Calm | 0.0019889 | 0.20058 | 26 |
| BTC | test | 3 | State 3 | -0.0013704 | 0.41001 | 502 |
| ETH | train | 0 | Calm | 8.6708e-05 | 0.59764 | 482 |
| ETH | train | 1 | State 1 | 0.0028871 | 0.69811 | 567 |
| ETH | train | 2 | Bull | 0.0081368 | 1.0712 | 388 |
| ETH | train | 3 | State 3 | -0.0066645 | 1.1491 | 379 |
| ETH | train | 4 | High-Vol | -0.01513 | 2.4013 | 46 |
| ETH | validation | 0 | Calm | 0.00048922 | 0.090755 | 0 |
| ETH | validation | 1 | State 1 | 0.00022388 | 0.5263 | 580 |
| ETH | validation | 2 | Bull | 0.012797 | 0.87653 | 29 |
| ETH | validation | 3 | State 3 | -0.00042096 | 0.91424 | 21 |
| ETH | validation | 4 | High-Vol | 0.037786 | 1.4961 | 0 |
| ETH | test | 0 | Calm | 0.0066315 | 0.2031 | 3 |
| ETH | test | 1 | State 1 | -0.00127 | 0.56411 | 487 |
| ETH | test | 2 | Bull | 0.011378 | 0.91161 | 62 |
| ETH | test | 3 | State 3 | -0.0048948 | 1.0255 | 85 |
| ETH | test | 4 | High-Vol | -0.064469 | 2.1185 | 0 |

Fixed baseline allocation on trend-HMM filtered High-Risk:

| asset | strategy | n_days | CAGR | Sharpe | max_drawdown |
| --- | --- | --- | --- | --- | --- |
| BTC | buy_and_hold | 637 | -0.1369 | -0.12777 | -0.52972 |
| BTC | trend_regime_aware | 637 | -0.17279 | -0.25362 | -0.56332 |
| ETH | buy_and_hold | 637 | -0.17119 | 0.069844 | -0.67553 |
| ETH | trend_regime_aware | 637 | -0.17119 | 0.069844 | -0.67553 |

A Bull label describes contemporaneous fitted-state returns on train; it is not a
forecast of tomorrow's positive return. All subsequent sample results remain
exploratory because the original test has been observed.

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
