"""Primary V2 pages sharing one verified model context and the existing design system."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard import v2_charts, v2_comparison, v2_history, v2_overview, v2_panels
from dashboard import v2_service as service

STRATEGIES = {
    "buy_and_hold": "Buy-and-Hold",
    "volatility_targeting": "Volatility targeting",
    "regime_defensive": "Regime defensive",
    "regime_volatility_targeting": "Regime + volatility",
}
SCENARIOS = {
    "baseline_close_to_close": "Close-to-close · giả định lý tưởng",
    "crosscheck_drift_adjusted": "Turnover theo tỷ trọng thực tế",
    "crosscheck_next_open": "Khớp giá mở cửa ngày tiếp theo",
}
PAGE_NAMES = {
    "Overview": "Tổng quan",
    "Regime History": "Lịch sử regime",
    "Model Comparison": "So sánh mô hình",
    "Portfolio & Risk": "Danh mục và rủi ro",
    "Research Outputs": "Bộ bảng và hình nghiên cứu",
}


def probability(value, ui):
    return "<0,01%" if 0 < value < 0.0001 else ui.pct(value)


def chart(st, ui, fig, height=340):
    fig = ui.chart_layout(fig, height, legend=fig.layout.showlegend is not False)
    fig.update_layout(
        dragmode="zoom",
        margin={"t": 62},
        modebar={"bgcolor": "#FFFDF8", "color": ui.MUTED, "activecolor": ui.NAVY},
    )
    fig.update_xaxes(fixedrange=False, automargin=True)
    fig.update_yaxes(fixedrange=False, automargin=True)
    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "scrollZoom": True,
            "doubleClick": "reset",
            "responsive": True,
            "modeBarButtonsToRemove": [
                "toImage",
                "select2d",
                "lasso2d",
                "autoScale2d",
                "hoverClosestCartesian",
                "hoverCompareCartesian",
                "toggleSpikelines",
            ],
        },
    )
    st.caption(
        "Kéo chọn vùng để phóng to · + / − để đổi mức zoom · biểu tượng ngôi nhà hoặc nhấp đúp để đặt lại."
    )


def heading(st, ui, title, subtitle):
    st.markdown(ui.sec_html(ui.esc(title), ui.esc(subtitle)), unsafe_allow_html=True)


def diagnostics(st, ctx, warnings=()):
    with st.expander("Chất lượng mô hình & phạm vi dữ liệu"):
        for text in warnings:
            st.warning(text)
        st.write(f"Model: `{ctx.model_id}`")
        st.caption(
            f"Xuất kết quả: {pd.Timestamp(ctx.exported_at):%d/%m/%Y %H:%M} UTC. "
            f"Dữ liệu khả dụng tại {pd.Timestamp(ctx.signals.as_of_utc.iloc[-1]):%d/%m/%Y %H:%M} UTC."
        )
        st.dataframe(pd.DataFrame([ctx.metadata["stability"]]), hide_index=True, width="stretch")
        st.caption(
            "Train kết thúc 05/05/2023; validation kết thúc 24/01/2025. "
            "Test lịch sử đã được quan sát. Kết quả mang tính khám phá; xác nhận độc lập còn pending."
        )


def overview(st, ui, ctx):
    return v2_overview.render(st, ui, ctx, chart)


def history(st, ui, ctx):
    return v2_history.render(st, ui, ctx, chart)


def comparison(st, ui, ctx):
    return v2_comparison.render(st, ui, ctx, chart)


def portfolio(st, ui, ctx):
    performance, nav, intervals = service.portfolio(ctx)
    with st.container(border=True, key="card_portfolio_controls"):
        scenario = st.selectbox(
            "Kịch bản thực thi", list(SCENARIOS), format_func=SCENARIOS.get, key="v2_scenario"
        )
        fee = st.selectbox(
            "Phí trên turnover",
            [0.0005, 0.001, 0.002],
            index=1,
            format_func=lambda x: f"{x * 10000:.0f} bps",
            key="v2_fee",
        )
        strategy = st.selectbox(
            "Chiến lược phân tích", list(STRATEGIES), index=2, format_func=STRATEGIES.get, key="v2_strategy"
        )
    subset = performance.loc[performance.scenario.eq(scenario) & np.isclose(performance.fee_rate, fee)]
    row = subset.loc[subset.strategy.eq(strategy)].iloc[0]
    reference = subset.loc[subset.strategy.eq("volatility_targeting")].iloc[0]
    st.markdown(
        ui.kpis_html(
            [
                ("NAV cuối", ui.num(row.final_nav, 4), STRATEGIES[strategy], ui.NAVY),
                ("Sharpe sau phí", ui.num(row.Sharpe, 3), SCENARIOS[scenario], ui.NAVY),
                ("Max drawdown", ui.pct(row.max_drawdown), "So với đỉnh NAV trước đó", ui.NEG),
                ("CAGR", ui.pct(row.CAGR), f"{row.n} ngày · {fee * 10000:.0f} bps/turnover", ui.NAVY),
            ]
        ),
        unsafe_allow_html=True,
    )
    data = nav.loc[nav.scenario.eq(scenario) & np.isclose(nav.fee_rate, fee)]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12, row_heights=[0.65, 0.35])
    palette = {
        "buy_and_hold": ui.MUTED,
        "volatility_targeting": ui.NAVY,
        "regime_defensive": ui.ACCENT,
        "regime_volatility_targeting": ui.HIGH,
    }
    for name, group in data.groupby("strategy"):
        color = palette[name]
        fig.add_trace(
            go.Scatter(x=group.date_utc, y=group.nav, name=STRATEGIES[name], line={"color": color}),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=group.date_utc,
                y=group.drawdown,
                name=STRATEGIES[name],
                line={"color": color},
                showlegend=False,
            ),
            row=2,
            col=1,
        )
    fig.update_yaxes(title_text="NAV", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown", tickformat=".0%", row=2, col=1)
    chart(st, ui, fig, 490)
    v2_panels.source(
        st,
        ctx,
        f"M5 · {SCENARIOS[scenario]} · {fee * 10000:.0f} bps / turnover",
        f"{data.date_utc.min()} → {data.date_utc.max()}",
    )
    current = data.loc[data.strategy.eq(strategy)].sort_values("date_utc")
    st.markdown(
        "<div class='metric-strip'>"
        f"<span>Volatility năm hóa<b>{ui.pct(row.ann_volatility)}</b></span>"
        f"<span>Tổng turnover<b>{ui.num(row.turnover, 2)}× NAV</b></span>"
        f"<span>Tổng tỷ lệ phí từng kỳ<b>{ui.pct(row.total_cost)}</b></span>"
        f"<span>Exposure cuối mẫu<b>{ui.pct(current.weight.iloc[-1], 1)}</b></span></div>",
        unsafe_allow_html=True,
    )
    columns = [
        "strategy",
        "final_nav",
        "CAGR",
        "ann_volatility",
        "Sharpe",
        "max_drawdown",
        "turnover",
        "total_cost",
    ]
    display = subset[columns].copy()
    display["strategy"] = display.strategy.map(STRATEGIES)
    st.dataframe(display, hide_index=True, width="stretch")
    st.caption(
        f"Model: {ctx.model_id}. Tín hiệu filtered ngày t áp dụng kỳ t+1; các quy tắc cố định, không chọn lại bằng test. "
        "Close-to-close lý tưởng hóa; chưa mô phỏng đầy đủ latency/slippage."
    )
    st.caption(
        "Quy tắc đã khóa: defensive giữ 100% khi P(High-Risk) <50%, ngược lại 25%; "
        "volatility target 40%/năm, cap 100%, cash return bằng 0."
    )
    if scenario == "baseline_close_to_close" and np.isclose(fee, 0.001):
        with st.expander("Giá trị tăng thêm so volatility targeting và uncertainty"):
            paired = service.review_table(ctx, "T06_paired_uncertainty.csv")
            paired = paired.loc[paired.metric.eq("Sharpe") & paired.block_days.eq(21)]
            short = {
                "buy_and_hold": "B&H",
                "volatility_targeting": "Vol-target",
                "regime_defensive": "Defensive",
                "regime_volatility_targeting": "Regime+vol",
            }
            chart(st, ui, v2_charts.uncertainty(paired, short), 310)
            st.caption(
                "Chênh lệch Sharpe so cả B&H và volatility targeting · block21 · CI có điều kiện 95%; "
                "Holm p-value trong tooltip. Không phải independent confirmation."
            )
            st.dataframe(intervals, hide_index=True, width="stretch")
            st.caption(
                "Paired block bootstrap có điều kiện theo tín hiệu cố định; kết quả exploratory, chưa xác nhận độc lập."
            )
    else:
        st.info(
            "Uncertainty hiện được xuất cho kịch bản close-to-close, phí 10 bps; không áp khoảng tin cậy đó cho kịch bản đang chọn."
        )
    with st.expander("Exposure và transaction costs theo thời gian"):
        exposure = go.Figure()
        for name, group in data.groupby("strategy"):
            exposure.add_trace(
                go.Scatter(
                    x=group.date_utc,
                    y=group.weight,
                    name=STRATEGIES[name],
                    line_shape="hv",
                    line={"color": palette[name]},
                )
            )
        exposure.update_layout(
            yaxis={"title": "Exposure", "tickformat": ".0%", "range": [0, 1.05]}, xaxis_title="Ngày UTC"
        )
        chart(st, ui, exposure, 290)
        st.caption("Exposure thực thi sau tín hiệu filtered; turnover và phí vẫn theo scenario đã khóa.")
    reference = subset.loc[subset.strategy.eq("volatility_targeting")].iloc[0]
    delta = row.Sharpe - reference.Sharpe
    v2_panels.finding(
        st,
        ui,
        "Regime signals có cải thiện quản trị rủi ro?",
        f"Với {SCENARIOS[scenario]}, phí {fee * 10000:.0f} bps, {STRATEGIES[strategy]} có Δ Sharpe "
        f"{ui.num(delta, 3, sign=True)} so volatility targeting. "
        "Ở baseline10bps, cả tám CI chênh lệch Sharpe của hai chiến lược regime-aware so hai benchmark đều chứa0. "
        "Chưa chứng minh cải thiện Sharpe sau phí; đánh giá drawdown/turnover riêng và giữ cả kết quả thua benchmark.",
        tag="RESEARCH CONCLUSION · RQ5",
    )


def research_outputs(st, ui, ctx):
    v2_panels.evidence(st, ui, ctx)


def render(st, ui, ctx, page):
    status = "UNSTABLE" if not ctx.metadata["stability"]["stable"] else "STABILITY GATE PASSED"
    st.markdown(
        f"<div class='hero'><p class='t'>{ctx.asset} <span>/ USDT · {PAGE_NAMES[page]} · "
        f"{ctx.through:%d/%m/%Y} UTC · K={ctx.metadata['K']}</span></p>"
        f"<span class='tag' data-model-status='{status}'>{status} · SNAPSHOT</span></div>",
        unsafe_allow_html=True,
    )
    stability = ctx.metadata["stability"]
    warnings = []
    if not stability["stable"]:
        reason = (
            "chỉ một họ khởi tạo có fit hợp lệ"
            if stability["eligible_initializer_families"] < 2
            else f"median ARI {stability['median_ari']:.3f}, minimum {stability['minimum_ari']:.3f}"
        )
        warnings.append(f"Mô hình chưa đủ ổn định: {reason}. Xác suất có điều kiện theo model đã chọn.")
    age = service.freshness(ctx.through)
    if age["status"] == "stale":
        warnings.append(f"Snapshot chậm {age['lag_days']} nến UTC đã đóng; không phải trạng thái realtime.")
    elif age["status"] == "invalid":
        st.error("Ngày dữ liệu nằm sau nến UTC đã đóng gần nhất.")
        return
    try:
        {
            "Overview": overview,
            "Regime History": history,
            "Model Comparison": comparison,
            "Portfolio & Risk": portfolio,
            "Research Outputs": research_outputs,
        }[page](st, ui, ctx)
        diagnostics(st, ctx, warnings)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Không hiển thị kết quả chưa xác minh: {exc}")
    st.markdown(
        "<div class='foot'>Crypto Market Regime Radar · nến ngày UTC · "
        "nghiên cứu mô phỏng · xác nhận độc lập: pending</div>",
        unsafe_allow_html=True,
    )
