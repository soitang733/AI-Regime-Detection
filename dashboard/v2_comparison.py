"""Development selection and fair stability comparisons, with research findings."""
import pandas as pd
import plotly.graph_objects as go

from dashboard import v2_charts as figures, v2_panels as panels, v2_service as service


def render(st,ui,ctx,chart):
    fit = service.table('m2','candidate_results.csv',ctx.asset,ctx.root)
    fit = fit.loc[fit.fold.eq(2)&fit.rv.eq(21)]
    with st.container(border=True,key='card_selection'):
        st.markdown(ui.sec_html('Model selection','RQ1 · K=2–4 chính, K=5 sensitivity'),unsafe_allow_html=True)
        metric = st.radio('Tiêu chí chọn K',['Validation likelihood','Train BIC','Train AIC'],horizontal=True,key='selection_metric')
        chart(st,ui,figures.selection_curve(fit,metric),330)
        panels.source(st,ctx,'T02 · hai initializers × 5 seed · RV21 · fold chính','Train/validation')
        st.caption('Đường tốt nhất theo tiêu chí đang xem có thể đến từ các fit khác nhau. '
                   'Champion không đổi: chọn bằng validation LL, tie-break theo protocol; không dùng test.')
        with st.expander('AIC/BIC, log likelihood và toàn bộ candidate'):
            st.dataframe(fit[['K','seed','initializer','eligible','AIC','BIC','validation_log_score','min_train_share','reason']],
                         hide_index=True,width='stretch')
    with st.container(border=True,key='card_stability'):
        st.markdown(ui.sec_html('Seed & initialization stability','RQ4 · cùng K, features và validation sample'),unsafe_allow_html=True)
        matched = service.review_table(ctx,'T08_matched_validation_stability.csv')
        chart(st,ui,figures.stability(matched),350)
        panels.source(st,ctx,'T08 matched validation · HMM/GMM/K-means','630 ngày validation · fold chính')
        st.caption('Điểm = median pairwise ARI; đoạn dọc = minimum → median, KHÔNG phải CI. '
                   'Đường chấm = median gate 0,80; còn cần minimum≥0,50 và đủ họ khởi tạo.')
        with st.expander('Fit counts, initializer families và risk-probability robustness'):
            st.dataframe(matched,hide_index=True,width='stretch')
            stability = service.table('m2','stability.csv',ctx.asset,ctx.root)
            st.dataframe(stability.loc[stability.fold.eq(2)&stability.rv.eq(21)],hide_index=True,width='stretch')
        st.markdown(ui.sec_html('Temporal-window sensitivity','Development rolling origins'),unsafe_allow_html=True)
        k = st.selectbox('K dùng đối chiếu cửa sổ',[2,3,4],index=ctx.metadata['K']-2,key='rolling_K')
        hmm = service.table('m2','stability.csv',ctx.asset,ctx.root)
        hmm = hmm.loc[hmm.K.eq(k)&hmm.rv.eq(21)&hmm.family.eq('pooled')].copy()
        hmm['method']='HMM'
        rolling = service.review_table(ctx,'T08_rolling_benchmark_stability.csv')
        rolling = rolling.loc[rolling.K.eq(k)].rename(columns={'median_ARI':'median_ari'})
        final = matched.loc[matched.K.eq(k)&matched.method.ne('HMM')].rename(columns={'median_ARI':'median_ari'}).assign(fold=2)
        combined = pd.concat([hmm[['fold','method','median_ari']],rolling[['fold','method','median_ari']],final[['fold','method','median_ari']]])
        fig = go.Figure()
        colors = {'HMM':ui.NAVY,'GMM':ui.ACCENT,'KMeans':'#5E8190'}
        for method,group in combined.groupby('method'):
            group = group.sort_values('fold')
            fig.add_trace(go.Scatter(x=group.fold,y=group.median_ari,mode='lines+markers',name=method,line={'color':colors[method]}))
        fig.update_layout(xaxis={'title':'Development fold','tickmode':'array','tickvals':[0,1,2]},yaxis_title='Median validation ARI')
        chart(st,ui,fig,270)
        st.caption('Ba development windows; preprocessing train-only cho từng fold. Các phương pháp có số fit/họ khởi tạo khác nhau; '
                   'đây là robustness, không phải kiểm định độc lập về model superiority.')
    st.markdown(ui.sec_html('Historical out-of-sample benchmarks','Kết quả phát hiện regime, không phải prediction accuracy'),unsafe_allow_html=True)
    metrics = service.table('m4_evaluation','historical_metrics.csv',ctx.asset,ctx.root)
    selected = metrics.loc[metrics.selected_on_development].copy()
    selected['flips']=pd.Series(index=selected.index,dtype='float')
    for index,row in selected.iterrows():
        states = service.table('m4_evaluation',f'{row.id}_states.csv',root=ctx.root)
        states = states.loc[states.split.eq('test')]
        valid_pair = pd.to_datetime(states.date_utc).diff().dt.days.eq(1)
        selected.loc[index,'flips']=int((states.state_id.ne(states.state_id.shift())&valid_pair).sum())
    st.dataframe(selected[['method','K','n','persistence','flips','noise_rate','mean_log_score','score_space']],hide_index=True,width='stretch')
    st.caption('LL chỉ so trong cùng feature space: GMM/HMM core 3D khác MS-AR/MS-GARCH return-only. '
               'K-means/HDBSCAN/change-point không có predictive LL ở đây. Page-Hinkley là segmentation; '
               'HDBSCAN có noise và adapter OOS; MS-GARCH dùng recursion song song.')
    with st.expander('Chi tiết benchmark, historical seed stability và RV sensitivity'):
        st.dataframe(service.table('m4_evaluation','seed_stability.csv',ctx.asset,ctx.root),hide_index=True,width='stretch')
        st.dataframe(service.table('m2','candidate_results.csv',ctx.asset,ctx.root),hide_index=True,width='stretch')
        st.dataframe(service.table('m2_ablation','stability.csv',ctx.asset,ctx.root),hide_index=True,width='stretch')
        st.caption('Historical stability không được xếp hạng trực tiếp với validation ARI phía trên.')
    with st.container(border=True,key='card_dynamic_comparison'):
        st.markdown(ui.sec_html('HMM vs NHHMM','RQ3 · giữ cả kết quả không thuận lợi'),unsafe_allow_html=True)
        comparison = service.table('m3_evaluation','predictive_comparison.csv',ctx.asset,ctx.root)
        row = comparison.iloc[0]
        fig = go.Figure(go.Scatter(x=[row.next_state_logloss_difference],y=['NHHMM − HMM'],mode='markers',
            marker={'size':11,'color':ui.HIGH if row.next_state_logloss_difference>0 else ui.NAVY},
            error_x={'type':'data','symmetric':False,
                'array':[max(0,row.bonferroni_two_assets_ci_high-row.next_state_logloss_difference)],
                'arrayminus':[max(0,row.next_state_logloss_difference-row.bonferroni_two_assets_ci_low)]}))
        fig.add_vline(x=0,line_dash='dot',line_color=ui.LINE)
        fig.update_layout(xaxis_title='Delta proxy next-state log loss · âm có lợi cho NHHMM',showlegend=False)
        chart(st,ui,fig,240)
        st.caption('Conditional block-bootstrap interval đã điều chỉnh hai tài sản. Target là state proxy của HMM; '
                   'khác định nghĩa state có thể làm loss lớn. Không coi đây là latent ground truth.')
        with st.expander('Observed-data likelihood, Brier, event counts và đầy đủ metrics'):
            st.dataframe(comparison,hide_index=True,width='stretch')
            st.dataframe(service.review_table(ctx,'T05_split_prediction_audit.csv'),hide_index=True,width='stretch')
    m = ctx.metadata['stability']
    panels.finding(st,ui,'Research findings · RQ1 / RQ4',
        f"Champion {ctx.asset} dùng K={ctx.metadata['K']}, không được gọi chính xác nhất hay sinh lợi tốt nhất từ LL. "
        f"Median ARI {m['median_ari']:.3f}, minimum {m['minimum_ari']:.3f}, {m['eligible_initializer_families']} họ khởi tạo hợp lệ. "
        'HMM persistence cao không đủ chứng minh ổn định hơn clustering. Kết quả đang exploratory; xác nhận độc lập pending.')
