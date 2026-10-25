"""Historical, economic and transition views share one frozen HMM context."""
import numpy as np
import pandas as pd

from dashboard import v2_charts as figures, v2_panels as panels, v2_service as service


def render(st, ui, ctx, chart):
    labels = figures.names(ctx.metadata)
    with st.container(border=True, key='card_controls'):
        dates = st.date_input('Khoảng ngày UTC', value=(ctx.through.date()-pd.Timedelta(days=729),ctx.through.date()),
            min_value=pd.Timestamp(ctx.signals.date_utc.iloc[0]).date(), max_value=ctx.through.date(),key=f'v2_dates_{ctx.asset}')
        mode = st.radio('Loại xác suất',['Filtered · dùng thông tin đến ngày t','Smoothed · hindsight'],
                        horizontal=True,key='v2_probability_mode')
        chosen = st.multiselect('State hiển thị',list(labels),default=list(labels),format_func=labels.get,key=f'v2_states_{ctx.asset}')
    if len(dates)!=2:
        st.info('Chọn ngày bắt đầu và kết thúc.'); return
    if not chosen:
        st.info('Chọn ít nhất một state để hiển thị.'); return
    start,end = map(str,dates)
    sample = ctx.signals.loc[ctx.signals.date_utc.between(start,end)]
    if sample.empty:
        st.info('Không có quan sát trong khoảng đã chọn.'); return
    history,economic,transition,drivers = st.tabs(['Historical Regimes','Economic Profiles','Transition Analysis','Market Drivers'])
    with history:
        colors = ui.state_colors(ctx.metadata['label_map'])
        with st.container(border=True,key='card_history_price'):
            st.markdown(ui.sec_html('Giá và regime','Nền màu luôn theo filtered'),unsafe_allow_html=True)
            st.markdown("<div class='state-legend'>"+' '.join(ui.chip(colors[i])+ui.esc(labels[i]) for i in chosen)+"</div>",unsafe_allow_html=True)
            chart(st,ui,figures.price(ctx,sample,chosen),370)
            panels.source(st,ctx,'Binance Spot + M2 filtered',f'{start} → {end}')
        probabilities = sample
        if mode.startswith('Smoothed'):
            st.warning('Hindsight: smoothed dùng quan sát tương lai; không dùng làm tín hiệu backtest. Nền giá vẫn theo filtered.')
            probabilities = service.table('m2',f'{ctx.asset.lower()}_smoothed.csv',root=ctx.root)
            probabilities = probabilities.loc[probabilities.date_utc.between(start,end)]
        with st.container(border=True,key='card_history_probability'):
            st.markdown(ui.sec_html('Regime probabilities','Smoothed · hindsight' if mode.startswith('Smoothed') else 'Filtered · causal'),unsafe_allow_html=True)
            chart(st,ui,figures.probability_history(probabilities,ctx.metadata,chosen),310)
            panels.source(st,ctx,'M2 · Gaussian HMM · '+('smoothed hindsight' if mode.startswith('Smoothed') else 'filtered'),f'{start} → {end}')
        spells = figures.timeline(sample)
        with st.container(border=True,key='card_history_timeline'):
            st.markdown(ui.sec_html('Regime timeline','Các đoạn gần nhất trong khoảng chọn'),unsafe_allow_html=True)
            items = []
            for row in spells.tail(7).iloc[::-1].itertuples():
                items.append(f"<div class='timeline-row'><span>{ui.esc(row.start)}<small>→ {ui.esc(row.end)}</small></span>"
                    f"<b style='color:{colors[row.state_id]}'>{ui.esc(labels[row.state_id])}</b><strong>{row.days} ngày</strong></div>")
            st.markdown("<div class='regime-timeline'>"+''.join(items)+"</div>",unsafe_allow_html=True)
            st.caption('Đoạn có thể bị cắt ở hai đầu bộ lọc. Không nối state qua ngày thiếu dữ liệu.')
        data = sample.merge(ctx.features[['date_utc','log_return']],on='date_utc',validate='one_to_one')
        rows = []
        for r in service.probability_rows(ctx).itertuples():
            values = data.loc[data.state_id.eq(r.state_id),'log_return']
            rows.append({'State':labels[r.state_id],'Số ngày':len(values),'Mean return/ngày':values.mean(),
                'Volatility năm hóa':values.std(ddof=1)*np.sqrt(365),
                'Persistence (train)':r.persistence,'Expected duration (train, ngày)':r.expected_days})
        with st.expander('Thống kê khoảng quan sát, persistence và expected duration'):
            st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch',column_config={
                c:st.column_config.NumberColumn(format='percent') for c in ['Mean return/ngày','Volatility năm hóa','Persistence (train)']})
            st.caption('Return/volatility theo khoảng đang chọn; persistence/duration từ transition matrix train.')
    with economic:
        panels.economics(st,ui,ctx,chart)
    with transition:
        panels.transitions(st,ui,ctx,sample,chart)
    with drivers:
        panels.drivers(st,ui,ctx,sample,chart)
