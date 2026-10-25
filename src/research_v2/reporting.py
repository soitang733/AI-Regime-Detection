"""Technical tables/figures/result cards for the paper team; never writes paper/."""
import hashlib
import json
from datetime import datetime,timezone
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from sklearn.metrics import adjusted_rand_score
from src.utils.config import ROOT

BASE=ROOT/'outputs/research_v2'
COLORS=['#5D8C70','#BB893D','#5C7D8A','#A45C50','#8A7494']


def run():
    out=BASE/'deliverables';tables=out/'tables';figures=out/'figures'
    tables.mkdir(parents=True,exist_ok=True);figures.mkdir(exist_ok=True)
    descriptions=[];profiles=[];transitions=[];metrics=[];cards={}
    core={};preds={};metadata={}
    for asset in ['BTC','ETH']:
        core[asset]=pd.read_parquet(BASE/f'm1/features_{asset.lower()}.parquet')
        preds[asset]=pd.read_csv(BASE/f'm2/{asset.lower()}_filtered.csv')
        metadata[asset]=json.loads((BASE/f'm2/{asset.lower()}_metadata.json').read_text())
        for split,g in core[asset].groupby('split'):
            for feature in ['log_return','rv21','log_dollar_volume','amihud_illiq','funding_sum','oi_growth_7d','vix','dxy_return_1d','stablecoin_supply_growth_7d']:
                s=g[feature]
                descriptions.append({'asset':asset,'split':split,'feature':feature,'n':len(s),'observed':int(s.notna().sum()),'mean':s.mean(),'std':s.std(),'min':s.min(),'max':s.max(),'coverage':s.notna().mean()})
        profiles.append(pd.read_csv(BASE/f'm2/{asset.lower()}_economic_labels.csv').assign(asset=asset))
        m=metadata[asset];p=np.array(m['transition_matrix'])
        for i in range(m['K']):
            for j in range(m['K']):transitions.append({'asset':asset,'origin':i,'destination':j,'probability':p[i,j],'expected_duration_origin':1/(1-p[i,i]),'model':'homogeneous HMM V2'})
        for period,g in preds[asset].groupby('split'):
            states=g.state_id.to_numpy()
            metrics.append({'asset':asset,'method':'HMM_V2','id':m['candidate_id'],'selected_on_development':True,'K':m['K'],
                            'period':period,'n':len(g),'persistence':float((states[1:]==states[:-1]).mean()),'score_space':'3D train-standardized core'})
        cards[asset]={'RQ1':{'selected_K':m['K'],'candidate':m['candidate_id'],'selection':'validation predictive LL; K5 sensitivity only'},
                      'RQ2':{'economic_labels':{int(r['state_id']):r['economic_label'] for r in m['economic_labels']},'interpretation':'conditional train statistics; no forced Bull/Bear'},
                      'RQ4':{'pooled_validation_stability':m['stability'],'claim':'compare metrics and uncertainty; no automatic HMM superiority'},
                      'limitations':['historical test already observed','economic intervals conditional on fitted model','macro historical release vintages not verified']}
    pd.DataFrame(descriptions).to_csv(tables/'T01_descriptive.csv',index=False)
    fits=pd.read_csv(BASE/'m2/candidate_results.csv')
    for index,row in fits.loc[fits.eligible].iterrows():
        with np.load(BASE/f"m2/candidates/{row.candidate_id}.npz") as cache:
            states=cache['states'];ends=np.r_[0,np.flatnonzero(states[1:]!=states[:-1])+1,len(states)]
            lengths=np.diff(ends)
            fits.loc[index,'validation_persistence']=float((states[1:]==states[:-1]).mean())
            fits.loc[index,'validation_minimum_run_days']=int(lengths.min())
            fits.loc[index,'validation_median_run_days']=float(np.median(lengths))
    fits.to_csv(tables/'T02_model_selection.csv',index=False)
    pd.concat(profiles).to_csv(tables/'T03_economic_labels.csv',index=False)
    for source,name in [('profiles','T03_regime_profiles'),('contrasts','T03_conditional_contrasts'),('label_block_sensitivity','T08_label_sensitivity'),('occupancy_by_year','T08_occupancy')]:
        pd.read_csv(BASE/f'm2_profiles/{source}.csv').to_csv(tables/f'{name}.csv',index=False)
    pd.DataFrame(transitions).to_csv(tables/'T04_transition_matrix.csv',index=False)
    for source,name in [('performance','T06_portfolio'),('incremental_uncertainty','T06_incremental_uncertainty')]:
        pd.read_csv(BASE/f'm5/{source}.csv').to_csv(tables/f'{name}.csv',index=False)
    benchmark=pd.read_csv(BASE/'m4_evaluation/historical_metrics.csv')
    pd.concat([benchmark,pd.DataFrame(metrics)],ignore_index=True).to_csv(tables/'T07_benchmark_comparison.csv',index=False)
    pd.read_csv(BASE/'m2/stability.csv').to_csv(tables/'T08_HMM_stability.csv',index=False)
    pd.read_csv(BASE/'m4_evaluation/seed_stability.csv').to_csv(tables/'T08_benchmark_seed_stability.csv',index=False)
    dynamic_ready=(BASE/'m3_evaluation/manifest.json').exists()
    if dynamic_ready:
        pd.read_csv(BASE/'m3_evaluation/transition_coefficients.csv').to_csv(tables/'T05_NHHMM_regressors.csv',index=False)
        pd.read_csv(BASE/'m3_evaluation/predictive_comparison.csv').to_csv(tables/'T05_predictive_comparison.csv',index=False)
        pd.read_csv(BASE/'m3_evaluation/qualified_family_comparison.csv').to_csv(tables/'T05_family_selection.csv',index=False)
        pd.read_csv(BASE/'m3_evaluation/family_coverage_and_failures.csv').to_csv(tables/'T05_coverage_and_failures.csv',index=False)
        for asset in ['BTC','ETH']:
            nn=pd.read_csv(BASE/f'm3_evaluation/{asset.lower()}_filtered.csv')
            for period,g in nn.groupby('split'):
                states=g.state_id.to_numpy()
                metrics.append({'asset':asset,'method':'NHHMM_V2','id':g.model_run_id.iloc[0],'selected_on_development':True,'K':int(g.K.iloc[0]),
                    'period':period,'n':len(g),'persistence':float((states[1:]==states[:-1]).mean()),'score_space':'3D train-standardized core'})
        pd.concat([benchmark,pd.DataFrame(metrics)],ignore_index=True).to_csv(tables/'T07_benchmark_comparison.csv',index=False)
    if (BASE/'m2_ablation/results.csv').exists():
        pd.read_csv(BASE/'m2_ablation/results.csv').to_csv(tables/'T08_volume_ablation.csv',index=False)
        pd.read_csv(BASE/'m2_ablation/stability.csv').to_csv(tables/'T08_volume_ablation_stability.csv',index=False)
    # Publication figures use actual saved outputs, not synthesized examples.
    for asset in ['BTC','ETH']:
        frame=preds[asset];dates=pd.to_datetime(frame.date_utc);m=metadata[asset]
        prices=pd.read_csv(ROOT/f'data/raw/{asset.lower()}_ohlcv.csv')
        close=prices.set_index('date_utc').close.reindex(frame.date_utc).to_numpy()
        fig,ax=plt.subplots(figsize=(12,4));ax.plot(dates,close,color='#333333',lw=.8)
        change=np.r_[0,np.flatnonzero(frame.state_id.to_numpy()[1:]!=frame.state_id.to_numpy()[:-1])+1,len(frame)]
        for start,end in zip(change[:-1],change[1:]):ax.axvspan(dates.iloc[start],dates.iloc[end-1]+pd.Timedelta(days=1),color=COLORS[int(frame.state_id.iloc[start])],alpha=.18,lw=0)
        ax.legend(handles=[Patch(facecolor=COLORS[i],alpha=.4,label=f'{i}: {m["label_map"][str(i)]}') for i in range(m['K'])],loc='upper left',ncol=m['K'],fontsize=8)
        ax.set(title=f'{asset}: price and filtered HMM states (historical exploratory)',ylabel='USDT');fig.tight_layout();fig.savefig(figures/f'F01_{asset}_price_regimes.png',dpi=180);plt.close(fig)
        smooth=pd.read_csv(BASE/f'm2/{asset.lower()}_smoothed.csv')
        fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True)
        for i in range(m['K']):
            axes[0].plot(dates,frame[f'prob_state_{i}'],label=f'State {i}',color=COLORS[i],lw=.7)
            axes[1].plot(dates,smooth[f'prob_state_{i}'],color=COLORS[i],lw=.7)
        axes[0].set_title(f'{asset}: filtered (causal, fixed model)');axes[1].set_title('Smoothed: hindsight, prohibited as trading signal');axes[0].legend(ncol=m['K']);fig.tight_layout();fig.savefig(figures/f'F02_{asset}_probabilities.png',dpi=180);plt.close(fig)
        if dynamic_ready:
            dynamic=pd.read_csv(BASE/f'm3_evaluation/{asset.lower()}_dynamic_transitions.csv')
            nm=json.loads((BASE/f'm3_evaluation/{asset.lower()}_metadata.json').read_text());risk=nm['high_risk_state']
            fig,ax=plt.subplots(figsize=(12,4))
            for origin,g in dynamic.loc[dynamic.destination_state.eq(risk)].groupby('origin_state'):ax.plot(pd.to_datetime(g.date_utc),g.conditional_probability,label=f'from state {origin}',lw=.7)
            ax.set(title=f'{asset}: NHHMM conditional transition to its High-Risk state',ylabel='P(S[t+1]=risk | S[t], z[t])');ax.legend();fig.tight_layout();fig.savefig(figures/f'F03_{asset}_dynamic_transitions.png',dpi=180);plt.close(fig)
        selection=json.loads((BASE/'m4_evaluation/selection.json').read_text())['selected_ids']
        parts={'HMM_V2':frame.set_index('date_utc').loc[frame.set_index('date_utc').split.eq('test'),'state_id']}
        if dynamic_ready:
            nn=pd.read_csv(BASE/f'm3_evaluation/{asset.lower()}_filtered.csv');parts['NHHMM_V2']=nn.loc[nn.split.eq('test')].set_index('date_utc').state_id
        for cid in selection:
            if cid.startswith(asset) and '_PH_' not in cid and '_HDBSCAN_' not in cid:
                source=BASE/f'm4_evaluation/{cid}_states.csv'
                t=pd.read_csv(source);parts[cid]=t.loc[t.split.eq('test')].set_index('date_utc').state_id
        aligned=pd.concat(parts,axis=1).dropna();names=aligned.columns.tolist()
        matrix=np.array([[adjusted_rand_score(aligned[a],aligned[b]) for b in names] for a in names])
        fig,ax=plt.subplots(figsize=(10,8));im=ax.imshow(matrix,vmin=-1,vmax=1,cmap='RdYlGn');ax.set_xticks(range(len(names)),names,rotation=75,ha='right',fontsize=7);ax.set_yticks(range(len(names)),names,fontsize=7);ax.set_title(f'{asset}: pairwise ARI, no ground-truth accuracy');fig.colorbar(im,ax=ax);fig.tight_layout();fig.savefig(figures/f'F04_{asset}_agreement.png',dpi=180);plt.close(fig)
        nav=pd.read_csv(BASE/'m5/nav.csv');nav=nav.loc[nav.asset.eq(asset)&nav.scenario.eq('baseline_close_to_close')&nav.fee_rate.eq(.001)]
        fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True)
        for name,g in nav.groupby('strategy'):axes[0].plot(pd.to_datetime(g.date_utc),g.nav,label=name);axes[1].plot(pd.to_datetime(g.date_utc),g.drawdown)
        axes[0].set_title(f'{asset}: fixed strategies, 10bps turnover cost');axes[0].legend(fontsize=8);axes[1].set_ylabel('Drawdown');fig.tight_layout();fig.savefig(figures/f'F05_{asset}_portfolio.png',dpi=180);plt.close(fig)
        occ=pd.read_csv(BASE/'m2_profiles/occupancy_by_year.csv');occ=occ.loc[occ.asset.eq(asset)]
        pivot=occ.pivot_table(index='year',columns='state_id',values='days',aggfunc='sum');pivot=pivot.div(pivot.sum(1),axis=0)
        fig,ax=plt.subplots(figsize=(10,4));pivot.plot.bar(stacked=True,ax=ax,color=COLORS[:m['K']]);ax.set(title=f'{asset}: state occupancy by year',ylabel='Fraction of eligible days');fig.tight_layout();fig.savefig(figures/f'F06_{asset}_occupancy.png',dpi=180);plt.close(fig)
    performance=pd.read_csv(BASE/'m5/performance.csv')
    for asset in cards:
        cards[asset]['RQ3']={'status':'evaluated' if dynamic_ready else 'pending_grid_completion','limitation':'proxy next-state targets; expected-count screen is not coefficient significance'}
        cards[asset]['RQ5']={'historical_performance':json.loads(performance.loc[performance.asset.eq(asset)&performance.scenario.eq('baseline_close_to_close')&performance.fee_rate.eq(.001)].to_json(orient='records')),'independent_confirmation':'pending'}
    (out/'RQ_result_cards.json').write_text(json.dumps(cards,indent=2),encoding='utf-8')
    manifest={'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'outputs_generated' if dynamic_ready else 'partial_pending_NHHMM',
        'independent_research_confirmation':'pending','paper_prose_written':False,
        'files_sha256':{p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')


if __name__=='__main__':run()
