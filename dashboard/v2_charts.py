"""Figures for the research terminal; no fitting, relabeling or strategy changes."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard import ui

FEATURES = {
    'log_return': ('Lợi suất ngày', '% / ngày', 100),
    'rv21': ('Realized volatility · RV21', '% / năm', 100 * np.sqrt(365)),
    'log_dollar_volume': ('Log volume USDT', 'log(USDT)', 1),
    'amihud_illiq': ('Thanh khoản · Amihud', '× 10⁻¹⁰ USDT⁻¹', 1e10),
    'funding_sum': ('Funding rate · tổng ngày', '% / ngày', 100),
    'oi_growth_7d': ('Open interest · tăng trưởng 7 ngày', '% / 7 ngày', 100),
    'vix': ('VIX', 'điểm', 1),
    'dxy_return_1d': ('DXY · lợi suất ngày', '% / ngày', 100),
    'stablecoin_supply_growth_7d': ('Stablecoin supply · tăng trưởng 7 ngày', '% / 7 ngày', 100),
}


def names(metadata):
    economic = {int(r['state_id']): r['economic_label'] for r in metadata['economic_labels']}
    return {i: f'{economic[i]} · S{i}' for i in range(metadata['K'])}


def timeline(signals):
    data = signals.sort_values('date_utc').copy()
    dates = pd.to_datetime(data.date_utc, utc=True)
    change = data.state_id.ne(data.state_id.shift()) | dates.diff().dt.days.ne(1)
    rows = []
    for _, group in data.groupby(change.cumsum()):
        rows.append({'state_id': int(group.state_id.iloc[0]), 'start': group.date_utc.iloc[0],
                     'end': group.date_utc.iloc[-1], 'days': len(group)})
    return pd.DataFrame(rows, columns=['state_id', 'start', 'end', 'days'])


def price(ctx, sample, chosen=None, probability_state=None, candlestick=False):
    """Price + frozen filtered states; hover includes the actual state posterior."""
    colors, labels = ui.state_colors(ctx.metadata['label_map']), names(ctx.metadata)
    columns=['date_utc','open','high','low','close'] if candlestick else ['date_utc','close']
    frame = sample.merge(ctx.prices[columns], on='date_utc', validate='one_to_one')
    state = frame.state_id.to_numpy(int)
    posterior = frame[[f'prob_state_{i}' for i in range(ctx.metadata['K'])]].to_numpy()
    custom = [[labels[k], posterior[t, k]] for t, k in enumerate(state)]
    fig = go.Figure(go.Scatter(x=frame.date_utc, y=frame.close, name='Giá đóng cửa',
        line={'color': ui.INK, 'width': 1.7}, customdata=custom,
        hovertemplate='%{x}<br>Giá: %{y:,.2f} USDT<br>%{customdata[0]}<br>P(state): %{customdata[1]:.2%}<extra></extra>'))
    if candlestick:
        fig=go.Figure(go.Candlestick(x=frame.date_utc,open=frame.open,high=frame.high,low=frame.low,close=frame.close,
            name='OHLC · Binance Spot',increasing_line_color=ui.NAVY,decreasing_line_color=ui.HIGH,customdata=custom,
            hovertemplate='%{x}<br>O %{open:,.2f} · H %{high:,.2f}<br>L %{low:,.2f} · C %{close:,.2f} USDT<br>%{customdata[0]}<br>P(state): %{customdata[1]:.2%}<extra></extra>'))
        fig.update_layout(xaxis_rangeslider_visible=False)
    if probability_state is None:
        chosen = list(labels) if chosen is None else chosen
        shapes = []
        for row in timeline(sample).itertuples():
            if row.state_id in chosen:
                shapes.append({'type': 'rect', 'xref': 'x', 'yref': 'paper', 'x0': row.start,
                    'x1': (pd.Timestamp(row.end) + pd.Timedelta(days=1)).strftime('%Y-%m-%d'),
                    'y0': 0, 'y1': 1, 'fillcolor': colors[row.state_id], 'opacity': .12,
                    'line_width': 0, 'layer': 'below'})
        fig.update_layout(shapes=shapes)
    else:
        fig.add_trace(go.Scatter(x=frame.date_utc, y=frame[f'prob_state_{probability_state}'],
            name=f'P({labels[probability_state]}) · filtered', yaxis='y2',
            line={'color': colors[probability_state], 'width': 1.4},
            hovertemplate='%{x}<br>P(state): %{y:.2%}<extra></extra>'))
        fig.update_layout(yaxis2={'overlaying': 'y', 'side': 'right', 'range': [0, 1],
                                 'tickformat': '.0%', 'title': 'P(state)'})
    fig.update_layout(yaxis_title='Giá · USDT', xaxis_title='Ngày UTC', hovermode='x unified')
    return fig


def probability_history(frame, metadata, chosen):
    labels, colors = names(metadata), ui.state_colors(metadata['label_map'])
    fig = go.Figure()
    for state in chosen:
        fig.add_trace(go.Scatter(x=frame.date_utc, y=frame[f'prob_state_{state}'], name=labels[state],
            line={'color': colors[state], 'width': 1.5}, hovertemplate='%{x}<br>%{y:.2%}<extra>%{fullData.name}</extra>'))
    fig.update_layout(yaxis={'range': [0, 1], 'tickformat': '.0%', 'title': 'Xác suất state'},
                      xaxis_title='Ngày UTC', hovermode='x unified')
    return fig


def profile(frame, feature, metadata):
    label, unit, scale = FEATURES[feature]
    data = frame.loc[frame.feature.eq(feature)].sort_values('state_id')
    labels, colors = names(metadata), ui.state_colors(metadata['label_map'])
    point, low, high = (data[c].to_numpy() * scale for c in ['weighted_mean', 'ci_low', 'ci_high'])
    fig = go.Figure(go.Scatter(x=point, y=[labels[int(s)] for s in data.state_id], mode='markers',
        marker={'size': 11, 'color': [colors[int(s)] for s in data.state_id]},
        error_x={'type': 'data', 'symmetric': False, 'array': np.maximum(high-point, 0),
                 'arrayminus': np.maximum(point-low, 0), 'color': ui.MUTED, 'thickness': 1.4},
        customdata=np.column_stack([low, high]),
        hovertemplate='%{y}<br>Mean: %{x:.4g}<br>CI: [%{customdata[0]:.4g}, %{customdata[1]:.4g}]<extra></extra>'))
    fig.add_vline(x=0, line_color=ui.LINE, line_dash='dot')
    fig.update_layout(xaxis_title=f'{label} · {unit}', yaxis={'autorange': 'reversed'}, showlegend=False)
    return fig


def transition_heatmap(matrix, labels):
    matrix = np.asarray(matrix, float)
    if matrix.shape != (len(labels), len(labels)) or not np.isfinite(matrix).all() or not np.allclose(matrix.sum(1), 1):
        raise ValueError('Ma trận chuyển trạng thái không hợp lệ')
    fig = go.Figure(go.Heatmap(z=matrix, x=labels, y=labels, zmin=0, zmax=1,
        colorscale=[[0, '#F5F3EB'], [.35, '#C5D3BC'], [1, ui.NAVY]],
        texttemplate='%{z:.1%}', textfont={'size': 12},
        colorbar={'tickformat': '.0%', 'thickness': 9, 'len': .7},
        hovertemplate='Từ %{y}<br>Sang %{x}<br>P: %{z:.2%}<extra></extra>'))
    fig.update_layout(xaxis_title='State đích', yaxis={'title': 'State nguồn', 'autorange': 'reversed'}, showlegend=False)
    return fig


def coefficient_ranges(frame):
    data = frame.loc[frame.feature.ne('intercept')].copy()
    fig = go.Figure(go.Scatter(x=data.coefficient, y=data.feature, mode='markers',
        marker={'size': 10, 'color': ui.NAVY},
        error_x={'type': 'data', 'symmetric': False,
                 'array': np.maximum(data.aligned_seed_max-data.coefficient, 0),
                 'arrayminus': np.maximum(data.coefficient-data.aligned_seed_min, 0),
                 'color': ui.ACCENT, 'thickness': 2},
        customdata=np.column_stack([data.aligned_seed_min, data.aligned_seed_max]),
        hovertemplate='%{y}<br>β: %{x:.3g}<br>Seed min–max: [%{customdata[0]:.3g}, %{customdata[1]:.3g}]<extra></extra>'))
    fig.add_vline(x=0, line_color=ui.LINE, line_dash='dot')
    fig.update_layout(xaxis_title='Log-odds / 1 train standard deviation', showlegend=False)
    return fig


def selection_curve(fits, metric):
    label, column, maximize = {
        'Validation likelihood': ('Validation log likelihood / ngày', 'validation_log_score', True),
        'Train BIC': ('BIC · thấp hơn tốt hơn', 'BIC', False),
        'Train AIC': ('AIC · thấp hơn tốt hơn', 'AIC', False),
    }[metric]
    valid = fits.loc[fits.eligible]
    aggregate = valid.groupby('K')[column].max() if maximize else valid.groupby('K')[column].min()
    fig = go.Figure(go.Scatter(x=valid.K, y=valid[column], mode='markers', name='Từng fit hợp lệ',
        marker={'color': ui.MUTED, 'opacity': .3, 'size': 6},
        customdata=valid[['initializer', 'seed']],
        hovertemplate='K=%{x}<br>%{y:.4g}<br>%{customdata[0]} · seed %{customdata[1]}<extra></extra>'))
    fig.add_trace(go.Scatter(x=aggregate.index, y=aggregate, mode='lines+markers', name='Tốt nhất theo tiêu chí',
                            line={'color': ui.NAVY}, marker={'size': 9}))
    fig.update_layout(xaxis={'title': 'Số state K · K=5 chỉ sensitivity', 'tickmode': 'array', 'tickvals': [2, 3, 4, 5]},
                      yaxis_title=label)
    return fig


def stability(frame):
    fig = go.Figure()
    colors = {'HMM': ui.NAVY, 'GMM': ui.ACCENT, 'KMeans': '#5E8190'}
    for method, group in frame.groupby('method', sort=False):
        group = group.sort_values('K')
        fig.add_trace(go.Scatter(x=group.K, y=group.median_ARI, mode='lines+markers', name=method,
            line={'color': colors[method]}, marker={'size': 8},
            error_y={'type': 'data', 'symmetric': False, 'array': np.zeros(len(group)),
                     'arrayminus': np.maximum(group.median_ARI-group.minimum_ARI, 0)},
            customdata=group[['minimum_ARI', 'valid_fits']],
            hovertemplate='K=%{x}<br>Median ARI: %{y:.3f}<br>Min ARI: %{customdata[0]:.3f}<br>Fit hợp lệ: %{customdata[1]}<extra>%{fullData.name}</extra>'))
    fig.add_hline(y=.8, line_color=ui.ACCENT, line_dash='dot')
    fig.update_layout(xaxis={'title': 'K · cùng validation sample', 'tickmode': 'array', 'tickvals': [2, 3, 4]},
                      yaxis_title='Pairwise ARI · min → median')
    return fig


def uncertainty(frame, strategies):
    data = frame.copy()
    data['name'] = data.strategy.map(strategies) + ' − ' + data.reference.map(strategies)
    fig = go.Figure(go.Scatter(x=data.point, y=data.name, mode='markers',
        marker={'color': ui.NAVY, 'size': 9},
        error_x={'type': 'data', 'symmetric': False, 'array': np.maximum(data.ci_high-data.point, 0),
                 'arrayminus': np.maximum(data.point-data.ci_low, 0), 'color': ui.ACCENT},
        customdata=data[['ci_low', 'ci_high', 'holm_adjusted_p']],
        hovertemplate='%{y}<br>Δ Sharpe: %{x:.3f}<br>CI: [%{customdata[0]:.3f}, %{customdata[1]:.3f}]<br>Holm p: %{customdata[2]:.3f}<extra></extra>'))
    fig.add_vline(x=0, line_color=ui.LINE, line_dash='dot')
    fig.update_layout(xaxis_title='Chênh lệch Sharpe sau phí · CI 95% có điều kiện', showlegend=False)
    return fig
