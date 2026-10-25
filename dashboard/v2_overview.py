"""Decision-first overview using only verified current V2 probabilities."""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard import v2_charts as figures, v2_panels as panels, v2_service as service
from dashboard import v2_market_art as market_art
from src.models.data import ZCOLS
from src.research.run import explain_latest


def probability(value, ui):
    return '<0,01%' if 0 < value < .0001 else ui.pct(value)


def render(st, ui, ctx, chart):
    rows = service.probability_rows(ctx)
    last = ctx.signals.iloc[-1]
    current = int(last.state_id)
    selected = rows.loc[rows.state_id.eq(current)].iloc[0]
    next_state = rows.loc[rows.next_day.idxmax()]
    color = ui.state_colors(ctx.metadata['label_map'])
    economic = next(r for r in ctx.metadata['economic_labels'] if int(r['state_id']) == current)
    spells = figures.timeline(ctx.signals)
    duration = int(spells.iloc[-1].days)
    other=service.context('ETH' if ctx.asset=='BTC' else 'BTC',ctx.root)
    ordered=[ctx,other] if ctx.asset=='BTC' else [other,ctx]
    st.markdown("<div class='market-tickers'>"+''.join(market_art.ticker(item) for item in ordered)+"</div>",unsafe_allow_html=True)
    with st.container(border=True, key='card_ai_radar'):
        st.markdown(ui.sec_html('AI Market Regime Radar', 'Current probability → next day'), unsafe_allow_html=True)
        state = (f"<div class='radar-state kpi market-state' style='--c:{color[current]}'>"
                 f"<div class='market-artwork'>{market_art.candles(ctx.prices)}</div>"
                 f"<div class='market-kicker'>{ctx.asset} / USDT <span>REGIME ENGINE</span></div>"
                 "<div class='l'><span>Regime hiện tại</span></div>"
                 f"<div class='v'>{ui.esc(selected.economic_label)}</div>"
                 f"<div class='s'>State {current} · {ui.esc(selected.model_label)} · K={ctx.metadata['K']}</div>"
                 f"<div class='radar-confidence'>{probability(selected.current, ui)}<span>filtered posterior</span>"
                 f"<span>T+1: {ui.esc(next_state.economic_label)} · {probability(next_state.next_day, ui)}</span></div>"
                 f"<div class='regime-tenure'><b>{duration} ngày</b> trong regime này<br>"
                 f"Kỳ vọng từ train: {ui.num(selected.expected_days, 1)} ngày</div></div>")
        body = []
        for row in rows.itertuples():
            readings = []
            for label, value in [('Hiện tại', row.current), ('Ngày T+1', row.next_day)]:
                readings.append(f"<div class='prob-reading'><small>{label}</small>"
                    f"<b>{probability(value, ui)}</b><div class='terminal-track'>"
                    f"<i style='width:{value*100:.6f}%'></i></div></div>")
            body.append(f"<div class='probability-row regime-mobile-state {'selected' if row.state_id==current else ''}' "
                f"data-state-id='{row.state_id}' style='--c:{color[row.state_id]}'>"
                f"<div class='state-label'><strong>{ui.esc(row.economic_label)}</strong>"
                f"<small>S{row.state_id} · {ui.esc(row.model_label)}</small></div>{''.join(readings)}</div>")
        st.markdown("<div class='radar-terminal'>"+state+"<div class='probability-board'>"+''.join(body)+"</div></div>", unsafe_allow_html=True)
        st.caption(f'Filtered P(Sₜ | X₁:ₜ), ngày {ctx.through:%d/%m/%Y} UTC. '
                   f'T+1 cho {(ctx.through+pd.Timedelta(days=1)):%d/%m/%Y} UTC = alphaₜ × P. '
                   'Mỗi phân phối có tổng bằng 1; đây không phải độ chính xác dự báo hay dự báo giá.')
        with st.expander('State mapping và xác suất chính xác'):
            st.markdown(ui.html_table(['State ID','Nhãn model','Diễn giải train','P hiện tại (filtered)','P ngày T+1'],
                [[str(r.state_id),ui.esc(r.model_label),ui.esc(r.economic_label),probability(r.current,ui),probability(r.next_day,ui)]
                 for r in rows.itertuples()]), unsafe_allow_html=True)
        if economic['risk_profile']=='Calm':
            meaning='Biến động trong state thấp hơn thị trường train và không có xu hướng mean return đủ rõ để gọi Bull/Bear.'
        elif economic['risk_profile']=='Stress':
            meaning='State có biến động và rủi ro đuôi trái cao theo thống kê train; không đồng nghĩa giá chắc chắn giảm ngày mai.'
        elif economic['direction'] in ['Bull','Bear']:
            meaning=f"Mean return trên train hỗ trợ diễn giải {economic['direction']}; tín hiệu vẫn là phân phối xác suất."
        else:
            meaning='State có hồ sơ return/volatility riêng, nhưng chưa đủ bằng chứng để gắn nhãn xu hướng Bull/Bear.'
        st.markdown(f"<div class='market-interpretation'><span>ĐỌC TÍN HIỆU</span><p>{ui.esc(meaning)} "
                    f"T+1 nghiêng về {ui.esc(next_state.economic_label)} ({probability(next_state.next_day,ui)}), "
                    "không phải dự báo giá.</p></div>",unsafe_allow_html=True)
    feature = ctx.features.loc[ctx.features.date_utc.eq(last.date_utc)].iloc[0]
    price = ctx.prices.sort_values('date_utc').close.iloc[-1]
    st.markdown(ui.kpis_html([
        ('Giá đóng cửa', ui.num(price, 2), 'USDT · nến ngày Binance', ui.INK),
        ('P(High-Risk)', probability(last.prob_high_risk, ui), f"State {ctx.metadata['high_risk_state']} · xác định từ train", ui.HIGH),
        ('Volatility RV21', ui.pct(feature.rv21*np.sqrt(365), 1), 'Năm hóa · 21 ngày quan sát', ui.NAVY),
        ('Left-tail trong state', ui.pct(economic['left_tail_rate'], 1), 'Train · return dưới ngưỡng 5% train', ui.ACCENT),
    ]), unsafe_allow_html=True)
    with st.container(border=True, key='card_overview_price'):
        st.markdown(ui.sec_html(f'{ctx.asset} · price & regimes', 'Thị trường đã thay đổi ra sao?'), unsafe_allow_html=True)
        first, second = st.columns([1, 1.6])
        with first:
            window = st.selectbox('Khoảng hiển thị', ['90 ngày','180 ngày','1 năm','2 năm','Toàn bộ'], index=2, key='overview_window')
        with second:
            mode = st.radio('Lớp hiển thị', ['Regime labels','Filtered probability'], horizontal=True, key='overview_price_mode')
        appearance=st.radio('Biểu đồ giá',['Nến OHLC','Đường giá'],horizontal=True,key='overview_chart_style')
        days = {'90 ngày':90,'180 ngày':180,'1 năm':365,'2 năm':730}
        sample = ctx.signals if window=='Toàn bộ' else ctx.signals.loc[
            ctx.signals.date_utc.ge((ctx.through-pd.Timedelta(days=days[window]-1)).strftime('%Y-%m-%d'))]
        state = None
        if mode=='Filtered probability':
            labels = figures.names(ctx.metadata)
            state = st.selectbox('Xác suất state trên giá', list(labels), format_func=labels.get, key=f'overview_state_{ctx.asset}')
        else:
            st.markdown("<div class='state-legend'>"+' '.join(ui.chip(color[i])+ui.esc(figures.names(ctx.metadata)[i])
                for i in range(ctx.metadata['K']))+"</div>", unsafe_allow_html=True)
        chart(st, ui, figures.price(ctx, sample, probability_state=state, candlestick=appearance=='Nến OHLC'), 390)
        panels.source(st, ctx, 'Binance Spot close + HMM filtered; tooltip có state và posterior',
                      f'{sample.date_utc.iloc[0]} → {sample.date_utc.iloc[-1]}')
        st.caption('Khoảng hiển thị chỉ lọc biểu đồ; Radar phía trên luôn là snapshot cuối đã xuất.')
    with st.container(border=True, key='card_explanation'):
        st.markdown(ui.sec_html('Drivers summary', 'Các đầu vào thực sự của HMM'), unsafe_allow_html=True)
        observations = []
        bundle = joblib.load(service.verified_path('m2', f'{ctx.asset.lower()}.joblib', ctx.root))
        raw = ctx.features.dropna(subset=ctx.metadata['features'])
        scaled = bundle['scaler'].transform(raw[ctx.metadata['features']])
        for i, name in enumerate(ctx.metadata['features']):
            title, unit, multiplier = figures.FEATURES[name]
            observations.append(f"<div class='driver-observation'><span>{ui.esc(title)}</span>"
                f"<b>{ui.num(float(feature[name])*multiplier, 2)}</b><small>{ui.esc(unit)} · "
                f"z(train) {ui.num(scaled[-1,i], 2, sign=True)}</small></div>")
        st.markdown("<div class='drivers-strip'>"+''.join(observations)+"</div>", unsafe_allow_html=True)
        st.caption('Mô hình kết hợp Gaussian emissions và state prior. Z-score mô tả quan sát so train, '
                   'không phải feature importance, nguyên nhân hay predictor của giá.')
        with st.expander('Giải thích chính xác: log emission + prior → posterior'):
            explained = explain_latest(pd.DataFrame(scaled, columns=ZCOLS),ctx.signals,bundle)
            with np.errstate(divide='ignore'):
                log_prior = np.log(explained.prior_probability)
            terms = np.column_stack([explained[['log_density_return','log_density_rv21','log_density_volume']],log_prior])
            fig = go.Figure(go.Heatmap(z=terms,x=['Return','RV21','Volume','Prior'],y=list(figures.names(ctx.metadata).values()),
                colorscale=[[0,'#EFE9DC'],[1,ui.NAVY]],
                colorbar={'title':'log score','thickness':8},
                hovertemplate='%{y}<br>%{x}: %{z:.4f}<extra></extra>'))
            fig.update_layout(xaxis_title='Thành phần log-density + log prior',yaxis={'autorange':'reversed'},showlegend=False)
            chart(st,ui,fig,300)
            st.dataframe(explained, hide_index=True, width='stretch')
            st.caption('Tổng theo hàng rồi chuẩn hóa softmax tái tạo filtered posterior. '
                       'Log-density có thể dương; prior=0 có log=−∞. Đây không phải SHAP, độ quan trọng nhân quả hay xác suất lợi nhuận.')
    with st.container(border=True, key='card_asset_comparison'):
        st.markdown(ui.sec_html('BTC vs ETH snapshot', 'Hai mô hình, hai hệ state riêng'), unsafe_allow_html=True)
        cards = []
        for asset in ['BTC','ETH']:
            other = ctx if asset==ctx.asset else service.context(asset,ctx.root)
            probs = service.probability_rows(other)
            current_row = probs.loc[probs.state_id.eq(int(other.signals.state_id.iloc[-1]))].iloc[0]
            next_row = probs.loc[probs.next_day.idxmax()]
            risk = int(other.metadata['high_risk_state'])
            cards.append(f"<div class='asset-snapshot'><div class='asset-snapshot-head'><b>{asset}</b><span>K={other.metadata['K']}</span></div>"
                f"<strong>{ui.esc(current_row.economic_label)}</strong><small>S{int(current_row.state_id)} · "
                f"{probability(current_row.current,ui)} hiện tại</small><div class='asset-snapshot-metrics'>"
                f"<span>High-Risk<b>{probability(other.signals.prob_high_risk.iloc[-1],ui)}</b></span>"
                f"<span>High-Risk T+1<b>{probability(float(probs.loc[probs.state_id.eq(risk),'next_day'].iloc[0]),ui)}</b></span></div>"
                f"<p>T+1 ưu thế: {ui.esc(next_row.economic_label)} · {probability(next_row.next_day,ui)}</p>"
                f"<small>{other.through:%d/%m/%Y} UTC · {'Qua gate' if other.metadata['stability']['stable'] else 'Unstable'}</small></div>")
        st.markdown("<div class='asset-snapshots'>"+''.join(cards)+"</div>", unsafe_allow_html=True)
        st.caption('Không đồng nhất State ID giữa BTC/ETH. T+1 là phân phối xác suất, không đảm bảo state ngày mai.')
    with st.expander('Độ tin cậy & giới hạn mô hình'):
        stability = ctx.metadata['stability']
        panels.finding(st, ui, 'Model reliability · chưa đủ ổn định' if not stability['stable'] else 'Model reliability · đạt gate định trước',
            f"Validation median ARI {stability['median_ari']:.3f}, minimum {stability['minimum_ari']:.3f}; "
            f"{stability['eligible_initializer_families']} họ khởi tạo có fit hợp lệ. "
            'Posterior có điều kiện theo model đã chọn, chưa phản ánh toàn bộ model uncertainty. '
            'Historical test đã được xem; Research Confirmation PENDING.', tag='MODEL RELIABILITY')
        with st.expander('NHHMM · model riêng và khả năng dự báo Stress'):
            meta, forecast = service.dynamic(ctx.asset,ctx.root)
            st.caption(f"{meta['model_run_id']} · K={meta['K']}. State IDs riêng; chưa chứng nhận ổn định.")
            st.dataframe(forecast,hide_index=True,width='stretch')
            audit = service.review_table(ctx,'T05_split_prediction_audit.csv')
            row = audit.loc[audit.split.eq('test')].iloc[0]
            st.warning(f'Historical test chỉ có {int(row.stress_proxy_entries)} Stress-entry proxy events; '
                       'chưa đủ để xác nhận predictor. Hệ số không phải bằng chứng nhân quả.')
