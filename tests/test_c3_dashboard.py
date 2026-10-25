"""Nghiệm thu C3 - dashboard 4 trang chạy trên kết quả thật (Excel C3-08..C3-13; Methodology 3.13 mục 10-12).

Dùng streamlit.testing (chạy app không cần trình duyệt). Skip nếu chưa cài streamlit hoặc
chưa có đầu ra C2/C3; không dùng dữ liệu mock.
"""

import pandas as pd
import numpy as np
import pytest
from bs4 import BeautifulSoup

pytest.importorskip("streamlit")
pytest.importorskip("plotly")
from streamlit.testing.v1 import AppTest

from src.utils.config import ROOT
from dashboard import ui, v2_service as service

APP = str(ROOT / "dashboard" / "app.py")
PAGES = ["Overview", "Regime History", "Model Comparison", "Portfolio & Risk"]


@pytest.fixture(scope="module")
def ready(cfg):
    need = [ROOT/'outputs/research_v2'/stage/'manifest.json' for stage in ['m1', 'm2', 'm5']]
    for p in need:
        if not p.exists():
            pytest.skip(f"Chưa có {p.name}: chạy `python run_pipeline.py --steps models backtest`")
    return cfg


def _radio(at, label):
    return next(r for r in at.radio if r.label == label)


def _run(asset=None, page=None):
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    if asset:
        _radio(at, "Tài sản").set_value(asset).run()
    if page:
        _radio(at, "Trang").set_value(page).run()
    return at


def _kpi(at, label):
    """Giá trị trong thẻ KPI (HTML) có nhãn label."""
    for m in at.markdown:
        for card in BeautifulSoup(m.value, "html.parser").select(".kpi"):
            caption = card.select_one(".l > span")
            if caption and caption.get_text() == label:
                return card.select_one(".v").get_text()
    raise AssertionError(f"Không thấy thẻ KPI {label}")


@pytest.mark.parametrize("asset", ["BTC", "ETH"])
def test_app_renders_four_pages_without_errors(ready, asset):
    at = _run(asset)
    assert _radio(at, "Trang").options == [f"{i}.  {p}" for i, p in enumerate(PAGES, start=1)]
    for page in PAGES:
        _radio(at, "Trang").set_value(page).run()
        assert not at.exception, (page, [e.value for e in at.exception])
        assert not at.error, (page, [e.value for e in at.error])


@pytest.mark.parametrize("asset", ["BTC", "ETH"])
def test_ui_kpis_match_exported_portfolio(ready, asset):
    at = _run(asset, "Portfolio & Risk")
    b08 = pd.read_csv(ROOT/'outputs/research_v2/m5/performance.csv')
    row = b08[(b08["asset"] == asset) & (b08["strategy"] == "regime_defensive")
              & (b08["scenario"] == "baseline_close_to_close") & np.isclose(b08.fee_rate, .001)].iloc[0]
    assert _kpi(at, "NAV cuối") == ui.num(row["final_nav"], 4)
    assert _kpi(at, "Max drawdown") == ui.pct(row["max_drawdown"])
    assert _kpi(at, "Sharpe sau phí") == ui.num(row["Sharpe"], 3)


def test_vietnamese_number_format():
    assert ui.num(1234.5, 2) == "1.234,50"
    assert ui.pct(-0.5509, 2) == "-55,09%"
    assert ui.num(0.0484, 4, sign=True) == "+0,0484"
    assert ui.pp(-0.0212) == "-2,12 điểm %"
    assert ui.num(float("nan")) == "-" and ui.pct(None) == "-"


def test_unstable_model_is_flagged_and_states_follow_k(ready):
    for asset in ready["assets"]:
        at = _run(asset)
        meta = service.context(asset).metadata
        if not meta['stability']['stable']:
            assert any('chưa đủ ổn định' in item.value for item in at.warning)
        # Thanh bên ghi đúng K của mô hình (không ép 4 nhãn).
        captions = " ".join(c.value for c in at.caption)
        assert f"K = {meta['K']}" in captions


def test_smoothed_view_is_labelled_hindsight(ready):
    at = _run(page="Regime History")
    mode = next(r for r in at.radio if r.label.startswith("Loại xác suất"))
    mode.set_value(mode.options[1]).run()
    assert not at.exception
    assert any("hindsight" in w.value.lower() for w in at.warning)


def test_scenarios_switch_and_show_simulated_label(ready):
    at = _run(page="Portfolio & Risk")
    box = at.selectbox[0]
    for option in ['baseline_close_to_close', 'crosscheck_drift_adjusted', 'crosscheck_next_open']:
        box.set_value(option).run()
        assert not at.exception
        assert any('nghiên cứu mô phỏng' in m.value for m in at.markdown)
