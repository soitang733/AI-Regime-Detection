"""Regression guards for the submission report's V2 identity."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_submission_report_uses_locked_v2_models() -> None:
    report = (ROOT / "paper/research_report.md").read_text(encoding="utf-8")

    assert "BTC_f2_rv21_k4_volatility_quantiles_s3" in report
    assert "ETH_f2_rv21_k4_kmeans_s4" in report
    assert "K=4 cho cả BTC và ETH" in report
    assert "NHHMM đã được triển khai" in report
    assert "Technical PASSED / Research Confirmation PENDING" in report
    assert "NHHMM, Markov-switching GARCH, Bayesian change-point" not in report


def test_legacy_pipeline_cannot_overwrite_submission_report() -> None:
    source = (ROOT / "src/research/run.py").read_text(encoding="utf-8")

    assert 'destination = ROOT / "paper/research_report_legacy.md"' in source
