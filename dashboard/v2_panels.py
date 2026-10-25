"""Progressive research panels and downloads backed by verified V2 exports."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard import v2_charts as figures
from dashboard import v2_service as service


def source(st, ctx, text, period):
    st.caption(f'{ctx.asset} · {period} · {text} · snapshot đến {ctx.through:%d/%m/%Y} UTC.')


def finding(st, ui, title, text, tag='RESEARCH FINDING'):
    st.markdown(f"<div class='finding'><span class='eyebrow'>{ui.esc(tag)}</span>"
                f"<strong>{ui.esc(title)}</strong><p>{ui.esc(text)}</p></div>", unsafe_allow_html=True)


def economics(st, ui, ctx, chart):
    profiles = service.table('m2_profiles', 'profiles.csv', ctx.asset, ctx.root)
    st.markdown(ui.sec_html('Economic regime profiles', 'RQ2 · train only'), unsafe_allow_html=True)
    feature = st.selectbox('Thống kê theo regime', list(figures.FEATURES)[:4],
                          format_func=lambda f: figures.FEATURES[f][0], key='economic_feature')
    chart(st, ui, figures.profile(profiles, feature, ctx.metadata), 330)
    source(st, ctx, 'T03 · posterior-weighted mean + moving-block CI 95%', 'Train 2018–2023')
    st.caption('CI có điều kiện theo model đã fit; không bao quát model-selection uncertainty. '
               'Nhãn kinh tế vẫn theo CI/điều kiện đã khóa, không được đổi từ biểu đồ này.')
    labels = pd.DataFrame(ctx.metadata['economic_labels']).sort_values('state_id')
    colors = ui.state_colors(ctx.metadata['label_map'])
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(ui.sec_html('Left-tail risk', 'Ngưỡng 5% từ train'), unsafe_allow_html=True)
        fig = go.Figure(go.Bar(x=[figures.names(ctx.metadata)[i] for i in labels.state_id],
            y=labels.left_tail_rate, marker_color=[colors[i] for i in labels.state_id],
            hovertemplate='%{x}<br>Tần suất đuôi trái: %{y:.2%}<extra></extra>'))
        fig.add_hline(y=float(labels.overall_tail_rate.iloc[0]), line_dash='dot', line_color=ui.MUTED)
        fig.update_layout(yaxis={'title': 'Tỷ lệ return ≤ train 5% cutoff', 'tickformat': '.0%'}, xaxis_title='State',showlegend=False)
        chart(st, ui, fig, 300)
        st.caption('Mô tả có điều kiện theo state trên train; không phải VaR hay xác suất lỗ ngày mai.')
    with col2:
        st.markdown(ui.sec_html('Occupancy & persistence', 'Mỗi state có đủ dữ liệu?'), unsafe_allow_html=True)
        occupancy = service.table('m2_profiles', 'occupancy_by_year.csv', ctx.asset, ctx.root)
        period = st.radio('Mẫu occupancy', ['train', 'validation', 'test'], horizontal=True, key='occupancy_split')
        totals = occupancy.loc[occupancy.split.eq(period)].groupby('state_id').days.sum().reindex(range(ctx.metadata['K']), fill_value=0)
        fig = go.Figure(go.Bar(x=[figures.names(ctx.metadata)[i] for i in totals.index], y=totals/totals.sum(),
            marker_color=[colors[i] for i in totals.index], customdata=totals,
            hovertemplate='%{x}<br>Occupancy: %{y:.1%}<br>%{customdata} ngày<extra></extra>'))
        fig.update_layout(yaxis={'title': 'Tỷ phần ngày quan sát', 'tickformat': '.0%'}, xaxis_title='State',showlegend=False)
        chart(st, ui, fig, 270)
    rows = service.probability_rows(ctx)
    detail = labels[['state_id', 'economic_label', 'direction', 'daily_volatility', 'weighted_effective_days']].merge(
        rows[['state_id', 'persistence', 'expected_days']], on='state_id', validate='one_to_one')
    with st.expander('Thống kê train, nhãn và điều kiện nhận diện'):
        st.dataframe(detail, hide_index=True, width='stretch')
        st.dataframe(service.table('m2_profiles', 'label_block_sensitivity.csv', ctx.asset, ctx.root), hide_index=True, width='stretch')
        st.caption('Weighted ESS không phải số ngày độc lập. Duration = 1/(1−Pii) từ ma trận HMM train.')
    separation = service.review_table(ctx, 'T03_between_state_separation.csv')
    main = separation.sort_values('between_state_mean_variance_share', ascending=False).iloc[0]
    finding(st, ui, 'Regimes khác nhau về điều gì?',
        f"{figures.FEATURES[main.feature][0]} có tỷ phần biến thiên mean giữa-state lớn nhất trong bốn biến "
        f"({ui.pct(main.between_state_mean_variance_share, 1)}). Đây là phân rã mô tả, không phải feature importance "
        'hay quan hệ nhân quả. Chưa có đủ bằng chứng mean return để ép nhãn Bull/Bear.')


def transitions(st, ui, ctx, sample, chart):
    st.markdown(ui.sec_html('Transition analysis', 'RQ3 · phân biệt conditional và marginal probability'), unsafe_allow_html=True)
    kind = st.radio('Mô hình chuyển trạng thái', ['HMM cố định', 'NHHMM động'], horizontal=True, key='transition_kind')
    start, end = sample.date_utc.iloc[0], sample.date_utc.iloc[-1]
    if kind == 'HMM cố định':
        labels = figures.names(ctx.metadata)
        matrix = np.asarray(ctx.metadata['transition_matrix'])
        prediction = ctx.signals
        model_id = ctx.model_id
        dynamic = None
        st.caption('Pij cố định, được ước lượng trên train. Xác suất state T+1 vẫn thay đổi theo filtered alpha_t.')
    else:
        meta, _ = service.dynamic(ctx.asset, ctx.root)
        labels = {i: f"{meta['economic_label_map'][str(i)]} · S{i}" for i in range(meta['K'])}
        dynamic = service.table('m3_evaluation', f'{ctx.asset.lower()}_dynamic_transitions.csv', root=ctx.root)
        if not dynamic.model_run_id.eq(meta['model_run_id']).all():
            raise ValueError('Dynamic transition khác phiên NHHMM')
        dates = sorted(dynamic.loc[dynamic.date_utc.between(start, end), 'date_utc'].unique())
        if not dates:
            st.info('Không có dynamic transition trong giai đoạn này.'); return
        day = st.select_slider('Ngày ma trận NHHMM (UTC)', options=dates, value=dates[-1], key=f'dynamic_day_{ctx.asset}')
        snapshot = dynamic.loc[dynamic.date_utc.eq(day)]
        matrix = snapshot.pivot(index='origin_state', columns='destination_state', values='conditional_probability').to_numpy()
        prediction = service.table('m3_evaluation', f'{ctx.asset.lower()}_filtered.csv', root=ctx.root)
        model_id = meta['model_run_id']
        st.caption(f'NHHMM riêng · K={meta["K"]} · Pij(z_t) tại {day} UTC. State IDs không đồng nhất với HMM.')
    left, right = st.columns([1, 1.15])
    with left:
        st.markdown(ui.sec_html('Ma trận chuyển trạng thái', 'Hàng nguồn → cột đích'), unsafe_allow_html=True)
        chart(st, ui, figures.transition_heatmap(matrix, list(labels.values())), 350)
    with right:
        choices = list(labels)
        origin = st.selectbox('State nguồn', choices, format_func=labels.get, key=f'origin_{ctx.asset}_{kind}')
        destination = st.selectbox('State đích', choices, index=min(1, len(choices)-1), format_func=labels.get,
                                   key=f'destination_{ctx.asset}_{kind}')
        selected = prediction.loc[prediction.date_utc.between(start, end)]
        fig = go.Figure()
        if dynamic is None:
            fig.add_trace(go.Scatter(x=selected.date_utc, y=np.full(len(selected), matrix[origin, destination]),
                name='P(i → j | state i) · cố định', line={'color': ui.ACCENT, 'dash': 'dot'}))
        else:
            conditional = dynamic.loc[dynamic.origin_state.eq(origin) & dynamic.destination_state.eq(destination)
                                      & dynamic.date_utc.between(start, end)]
            fig.add_trace(go.Scatter(x=conditional.date_utc, y=conditional.conditional_probability,
                name='P(i → j | state i, z_t)', line={'color': ui.ACCENT}))
        fig.add_trace(go.Scatter(x=selected.date_utc, y=selected[f'prob_next_state_{destination}'],
            name='P(S_t+1=j | thông tin đến t)', line={'color': ui.NAVY}))
        fig.update_layout(yaxis={'title': 'Xác suất', 'tickformat': '.0%', 'range': [0, 1]}, xaxis_title='Ngày UTC')
        chart(st, ui, fig, 300)
    source(st, ctx, f'Model {model_id}', f'{start} → {end}')
    st.caption('Đường conditional giả định đang ở state nguồn; đường marginal tích hợp toàn bộ filtered probabilities. '
               'Cả hai đều là xác suất trạng thái, không phải dự báo giá.')


def drivers(st, ui, ctx, sample, chart):
    meta, _ = service.dynamic(ctx.asset, ctx.root)
    st.markdown(ui.sec_html('Market drivers', 'RQ3 · dữ liệu quan sát và transition predictors'), unsafe_allow_html=True)
    feature = st.selectbox('Biến thị trường', list(figures.FEATURES),
                          format_func=lambda f: figures.FEATURES[f][0], key='driver_feature')
    title, unit, scale = figures.FEATURES[feature]
    role = ('Biến emission của HMM' if feature in ctx.metadata['features'] else 'Biến bối cảnh')
    if feature in meta['feature_names']:
        role += ' · predictor trong NHHMM đã chọn'
    else:
        role += ' · không nằm trong transition specification NHHMM đã chọn'
    st.caption(role)
    data = ctx.features.loc[ctx.features.date_utc.between(sample.date_utc.iloc[0], sample.date_utc.iloc[-1])]
    merged = data[['date_utc', feature]].merge(ctx.signals[['date_utc', 'prob_high_risk']], on='date_utc', validate='one_to_one')
    if merged[feature].notna().any():
        fig = make_subplots(specs=[[{'secondary_y': True}]])
        fig.add_trace(go.Scatter(x=merged.date_utc, y=merged[feature]*scale, name=title,
            line={'color': ui.NAVY}, connectgaps=False), secondary_y=False)
        fig.add_trace(go.Scatter(x=merged.date_utc, y=merged.prob_high_risk, name='P(High-Risk) · HMM filtered',
            line={'color': ui.HIGH, 'width': 1.2}), secondary_y=True)
        fig.update_yaxes(title_text=unit, secondary_y=False)
        fig.update_yaxes(title_text='P(High-Risk)', tickformat='.0%', range=[0, 1], secondary_y=True)
        fig.update_xaxes(title_text='Ngày UTC')
        chart(st, ui, fig, 350)
        source(st, ctx, 'M1 features + M2 filtered probabilities · quan sát, không nhân quả',
               f'{merged.date_utc.iloc[0]} → {merged.date_utc.iloc[-1]}')
    else:
        st.info('Nguồn này không có quan sát hợp lệ trong khoảng đã chọn; không backfill dữ liệu giả.')
    coverage = service.table('m1', 'coverage.csv', ctx.asset, ctx.root)
    with st.expander('Coverage, availability và biến thực sự được dùng'):
        st.dataframe(coverage.loc[coverage.feature.eq(feature), ['split', 'coverage', 'stale_removed', 'future_rows']],
                     hide_index=True, width='stretch')
        st.write(f"HMM emissions: {', '.join(ctx.metadata['features'])}. NHHMM transitions: "
                 f"{', '.join(n for n in meta['feature_names'] if n != 'intercept')}. Model: {meta['model_run_id']}.")
        st.caption('Macro là historical current-vintage; thời điểm khả dụng bảo thủ không xác minh historical release revisions.')
    st.markdown(ui.sec_html('Hệ số transition của NHHMM', 'Log-odds · seed sensitivity'), unsafe_allow_html=True)
    coefficients = service.table('m3_evaluation', 'transition_coefficients.csv', ctx.asset, ctx.root)
    labels = {i: f"{meta['label_map'][str(i)]} · S{i}" for i in range(meta['K'])}
    left, right = st.columns(2)
    with left:
        origin = st.selectbox('Nguồn của hệ số', list(labels), format_func=labels.get, key=f'coefficient_origin_{ctx.asset}')
    with right:
        destination = st.selectbox('Đích so với tham chiếu', list(labels), format_func=labels.get,
                                   key=f'coefficient_destination_{ctx.asset}')
    selected = coefficients.loc[coefficients.origin_state.eq(origin) & coefficients.destination_state.eq(destination)]
    if selected.empty:
        st.info(f'State {meta["K"]-1} là đích tham chiếu của multinomial logit. Hệ số 0 theo định nghĩa, không phải bằng chứng không có tác động.')
    else:
        chart(st, ui, figures.coefficient_ranges(selected), 270)
        st.caption(f"Điểm = β của fit đã chọn; đoạn ngang = min–max giữa {selected.valid_seed_count.iloc[0]} seed "
                   f"sau train alignment, KHÔNG phải CI. Đích tham chiếu: S{int(selected.reference_destination.iloc[0])}.")
        if not selected.passes_event_count_screen.all():
            st.warning('Cặp chuyển trạng thái chưa qua event-count screen; không diễn giải dấu hệ số như predictor đã được xác nhận.')
        with st.expander('Hệ số, expected transition counts và event-count screen'):
            st.dataframe(selected, hide_index=True, width='stretch')
    audit = service.review_table(ctx, 'T05_split_prediction_audit.csv')
    test = audit.loc[audit.split.eq('test')].iloc[0]
    finding(st, ui, 'RQ3 chưa xác nhận khả năng dự báo Stress',
        f"Historical test có {int(test.stress_proxy_entries)} Stress-entry proxy events trên {int(test.at_risk_days)} ngày at-risk. "
        'Target do HMM tạo, không phải latent ground truth. NHHMM không được mặc định tốt hơn HMM; '
        'hệ số, correlation và seed range không chứng minh nhân quả.')


TABLES = {
    'T01 · Descriptive statistics': 'T01_descriptive.csv',
    'T02 · Model selection K=2–5': 'T02_model_selection.csv',
    'T03 · Regime mean / volatility / liquidity': 'T03_regime_profiles.csv',
    'T03 · Economic labels và bằng chứng': 'T03_economic_labels.csv',
    'T04 · Transition matrix': 'T04_transition_matrix.csv',
    'T05 · NHHMM transition regressors': 'T05_NHHMM_regressors.csv',
    'T05 · NHHMM predictive comparison': 'T05_predictive_comparison.csv',
    'T06 · Portfolio performance': 'T06_portfolio.csv',
    'T07 · Benchmark comparison': 'T07_benchmark_comparison.csv',
    'T08 · Stability qua seed / initializer / window': 'T08_HMM_stability.csv',
}

SUBMISSION_TABLES = {
    'B01 · Thống kê mô tả': 'outputs/tables/B01_descriptives.csv',
    'B02 · Thông tin mẫu': 'outputs/tables/B02_sample_manifest.csv',
    'B03 · Model Selection V2': 'outputs/tables/B03_model_selection_v2.csv',
    'B04 · Regime Statistics V2': 'outputs/tables/B04_regime_statistics_v2.csv',
    'B05 · Transition Matrix V2': 'outputs/tables/B05_transition_matrix_v2.csv',
    'B07 · HMM vs GMM V2': 'outputs/tables/B07_hmm_vs_gmm_v2.csv',
    'B08 · Portfolio 10 bps V2': 'outputs/tables/B08_portfolio_v2.csv',
}

SUBMISSION_FIGURES = {
    'H01 · Price History': 'outputs/figures/H01_price_history.png',
    'H02 · Price & Regimes': 'outputs/figures/H02_{asset}_price_regimes.png',
    'H03 · Filtered & Smoothed Probabilities': 'outputs/figures/H03_{asset}_regime_probabilities.png',
    'H04 · HMM vs GMM': 'outputs/figures/H04_{asset}_hmm_vs_gmm.png',
    'H05 · Portfolio NAV sau phí': 'outputs/figures/H05_{asset}_portfolio_nav.png',
    'H06 · Dashboard Screenshot': 'outputs/figures/H06_dashboard.png',
}


def evidence(st, ui, ctx):
    with st.container(border=True, key='submission_pack'):
        st.markdown(ui.sec_html('Research Outputs', 'B01–B08 và H01–H06 · đã kiểm tra SHA-256'),
                    unsafe_allow_html=True)
        st.caption('B01/B02/H01 được giữ nguyên; B03–B05, B07/B08 và H02–H06 lấy từ V2 đã khóa. '
                   'B06 không xuất vì chưa qua event-count screen.')
        table_label = st.selectbox('Bảng chuẩn', list(SUBMISSION_TABLES), key='submission_table')
        figure_label = st.selectbox('Hình chuẩn', list(SUBMISSION_FIGURES), key='submission_figure')
        table_path = service.submission_path(SUBMISSION_TABLES[table_label], ctx.root)
        relative = SUBMISSION_FIGURES[figure_label].format(asset=ctx.asset)
        figure_path = service.submission_path(relative, ctx.root)
        left, right = st.columns(2)
        left.download_button('↓ Tải bảng CSV', table_path.read_bytes(), file_name=table_path.name,
                             mime='text/csv', key='download_submission_table', width='stretch')
        right.download_button('↓ Tải hình PNG', figure_path.read_bytes(), file_name=figure_path.name,
                              mime='image/png', key='download_submission_figure', width='stretch')
        table_data = pd.read_csv(table_path)
        if 'asset' in table_data:
            table_data = table_data.loc[table_data.asset.eq(ctx.asset)]
        st.dataframe(table_data.head(20), hide_index=True, width='stretch')
        st.caption('Xem trước tối đa 20 dòng; CSV tải xuống chứa toàn bộ dữ liệu.')
        st.image(str(figure_path), caption=f'{figure_label} · {ctx.asset}', width='stretch')

    with st.expander('Research evidence · tải bảng, hình và báo cáo'):
        st.caption('T01–T08 / F01–F06 · kết quả thật đã xác minh · Research Confirmation PENDING.')
        selection = st.selectbox('Bảng nghiên cứu', list(TABLES), key='evidence_table')
        name = TABLES[selection]
        path = service.verified_path('deliverables', f'tables/{name}', ctx.root)
        st.download_button('Tải bảng CSV', path.read_bytes(), file_name=name, mime='text/csv', key='download_table')
        with st.expander('Xem một phần bảng đã chọn'):
            data = pd.read_csv(path)
            if 'asset' in data:
                data = data.loc[data.asset.eq(ctx.asset)]
            st.dataframe(data.head(30), hide_index=True, width='stretch')
            st.caption('Tối đa 30 dòng xem trước; file tải chứa nguyên bảng cho cả hai tài sản nếu có.')
        manifest = service.manifest('deliverables', ctx.root)
        images = sorted(name for name in manifest['files_sha256'] if name.startswith('figures/') and f'_{ctx.asset}_' in name)
        image_name = st.selectbox('Hình nghiên cứu', images, format_func=lambda s: s.split('/')[-1], key='evidence_figure')
        image_path = service.verified_path('deliverables', image_name, ctx.root)
        st.download_button('Tải hình PNG', image_path.read_bytes(), file_name=image_path.name, mime='image/png', key='download_figure')
        report = ctx.root/'reports/v2_review/BAO_CAO_RASOAT_V2.md'
        if report.exists():
            st.download_button('Tải báo cáo RQ1–RQ5', report.read_bytes(), file_name=report.name,
                               mime='text/markdown', key='download_report')
