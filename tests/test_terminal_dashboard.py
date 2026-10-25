"""Scientific display contracts for the refined V2 terminal."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from dashboard import v2_charts as figures, v2_service as service
from dashboard import v2_market_art as market_art
from src.utils.config import ROOT


@pytest.fixture(scope='module', params=['BTC','ETH'])
def ctx(request):
    return service.context(request.param)


def test_price_tooltip_uses_actual_filtered_state_probability(ctx):
    sample = ctx.signals.tail(35)
    fig = figures.price(ctx,sample)
    trace = fig.data[0]
    probabilities = sample[[f'prob_state_{i}' for i in range(ctx.metadata['K'])]].to_numpy()
    state = sample.state_id.to_numpy(int)
    expected = probabilities[np.arange(len(sample)),state]
    np.testing.assert_allclose(np.asarray(trace.customdata)[:,1].astype(float),expected)
    assert list(np.asarray(trace.customdata)[:,0]) == [figures.names(ctx.metadata)[i] for i in state]
    expected_prices = ctx.prices.set_index('date_utc').loc[sample.date_utc,'close']
    np.testing.assert_array_equal(trace.y,expected_prices)


def test_candles_use_verified_ohlc_without_synthesizing_prices(ctx):
    sample=ctx.signals.tail(40)
    fig=figures.price(ctx,sample,candlestick=True)
    expected=ctx.prices.set_index('date_utc').loc[sample.date_utc]
    assert fig.data[0].type=='candlestick'
    for column in ['open','high','low','close']:
        np.testing.assert_array_equal(getattr(fig.data[0],column),expected[column])


def test_market_visuals_are_based_on_actual_observations(ctx):
    svg=market_art.candles(ctx.prices)
    assert svg.count('<rect ')==min(52,len(ctx.prices))
    assert 'OHLC' in svg and 'polyline' in market_art.sparkline(ctx.prices)
    assert figures.ui.num(ctx.prices.sort_values('date_utc').close.iloc[-1],2) in market_art.ticker(ctx)


def test_price_overlay_and_probability_history_keep_state_ids(ctx):
    sample = ctx.signals.tail(30)
    state = ctx.metadata['K']-1
    fig = figures.price(ctx,sample,probability_state=state)
    np.testing.assert_array_equal(fig.data[1].y,sample[f'prob_state_{state}'])
    assert fig.data[1].yaxis=='y2'
    probability = figures.probability_history(sample,ctx.metadata,[state,0])
    assert len(probability.data)==2
    np.testing.assert_array_equal(probability.data[0].y,sample[f'prob_state_{state}'])
    assert probability.data[0].line.color == figures.ui.state_colors(ctx.metadata['label_map'])[state]


def test_regime_timeline_does_not_bridge_missing_dates():
    sample = pd.DataFrame({'date_utc':['2024-01-01','2024-01-02','2024-01-05','2024-01-06'],
                           'state_id':[0,0,0,1]})
    result = figures.timeline(sample)
    assert result.days.tolist()==[2,1,1]
    assert result.start.tolist()==['2024-01-01','2024-01-05','2024-01-06']


def test_profile_displays_real_ci_and_units(ctx):
    frame = service.table('m2_profiles','profiles.csv',ctx.asset,ctx.root)
    subset = frame.loc[frame.feature.eq('log_return')].sort_values('state_id')
    fig = figures.profile(frame,'log_return',ctx.metadata)
    trace = fig.data[0]
    np.testing.assert_allclose(trace.x,subset.weighted_mean*100)
    np.testing.assert_allclose(np.asarray(trace.x)-np.asarray(trace.error_x.arrayminus),subset.ci_low*100)
    np.testing.assert_allclose(np.asarray(trace.x)+np.asarray(trace.error_x.array),subset.ci_high*100)


def test_invalid_transition_matrix_is_not_drawn():
    with pytest.raises(ValueError):
        figures.transition_heatmap([[.8,.8],[.3,.7]],['A','B'])


def test_review_panels_reject_another_model(ctx):
    with pytest.raises(ValueError,match='model khác'):
        service.review_table(replace(ctx,metadata={**ctx.metadata,'candidate_id':'another-model'}),
                             'T05_split_prediction_audit.csv')


def radio(at,label):
    return next(r for r in at.radio if r.label==label)


def test_header_asset_selector_and_sidebar_are_synchronized():
    at = AppTest.from_file(str(ROOT/'dashboard/app.py'),default_timeout=180).run()
    radio(at,'Tài sản nhanh').set_value('ETH').run()
    assert radio(at,'Tài sản').value=='ETH'
    assert any("ETH <span>" in m.value for m in at.markdown if "class='hero'" in m.value)
    radio(at,'Tài sản').set_value('BTC').run()
    assert radio(at,'Tài sản nhanh').value=='BTC'
    assert not at.exception and not at.error


def test_dynamic_transitions_use_nhhmm_K_and_do_not_fabricate_CI():
    at = AppTest.from_file(str(ROOT/'dashboard/app.py'),default_timeout=180).run()
    radio(at,'Trang').set_value('Regime History').run()
    radio(at,'Mô hình chuyển trạng thái').set_value('NHHMM động').run()
    metadata,_ = service.dynamic('BTC')
    origin = next(s for s in at.selectbox if s.label=='State nguồn')
    assert len(origin.options)==metadata['K']
    assert not at.exception and not at.error
    assert any('KHÔNG phải CI' in c.value for c in at.caption)
    assert any('không phải latent ground truth' in m.value for m in at.markdown)


def test_download_evidence_is_accessible_without_a_baseline_version():
    at = AppTest.from_file(str(ROOT/'dashboard/app.py'),default_timeout=180).run()
    labels = [item.proto.label for item in at.get('download_button')]
    assert {'Tải bảng CSV','Tải hình PNG','Tải báo cáo RQ1–RQ5'}<=set(labels)
    assert all(r.label!='Phiên kết quả' for r in at.radio)


def test_model_warnings_are_available_in_collapsed_quality_details():
    at=AppTest.from_file(str(ROOT/'dashboard/app.py'),default_timeout=180).run()
    quality=next(e for e in at.expander if e.label=='Chất lượng mô hình & phạm vi dữ liệu')
    assert not quality.proto.expanded
    assert any('chưa đủ ổn định' in w.value for w in quality.warning)
    assert any('UNSTABLE' in m.value for m in at.markdown if "class='hero'" in m.value)
    assert any('ĐỌC TÍN HIỆU' in m.value for m in at.markdown)


def test_dashboard_presents_outputs_without_a_repeated_interpretation_banner():
    at=AppTest.from_file(str(ROOT/'dashboard/app.py'),default_timeout=180).run()
    for page in ['Overview','Regime History','Model Comparison','Portfolio & Risk']:
        radio(at,'Trang').set_value(page).run()
        assert not any("aria-label='Diễn giải kết quả'" in m.value for m in at.markdown)
        assert not at.exception and not at.error
