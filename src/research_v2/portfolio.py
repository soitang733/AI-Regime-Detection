"""Frozen V2 strategies with explicit unstable acknowledgement and execution audit."""
import hashlib
import json

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

from src.evaluation.backtest import performance_metrics, regime_weights, simulate
from src.evaluation.backtest_run import load_backtest_config
from src.research.economics import moving_blocks
from src.research.portfolio import _bootstrap_metrics, volatility_weights
from src.research_v2.handoff import load_hmm
from src.utils.config import ROOT


def aligned_inputs(asset):
    prediction,metadata=load_hmm(asset,require_stable=False,acknowledge_unstable=True)
    prediction=prediction.copy()
    prediction['signal_date_utc']=pd.to_datetime(prediction.pop('date_utc'),utc=True)
    prediction['as_of_utc']=pd.to_datetime(prediction.as_of_utc,utc=True)

    features=pd.read_parquet(ROOT/f'outputs/research_v2/m1/features_{asset.lower()}.parquet')
    features['date_utc']=pd.to_datetime(features.date_utc,utc=True)
    returns=features[['date_utc','split','segment_id']].rename(columns={'date_utc':'return_date_utc'}).copy()

    prices=pd.read_parquet(ROOT/'data/processed/prices_daily.parquet')
    prices=prices.loc[prices.asset.eq(asset)].sort_values('date_utc').copy()
    prices['return_date_utc']=pd.to_datetime(prices.pop('date_utc'),utc=True)
    prices['target_simple_return']=prices.groupby('segment_id',sort=False).close.pct_change()
    returns=returns.merge(prices[['return_date_utc','segment_id','open','target_simple_return']],
                          on=['return_date_utc','segment_id'],validate='one_to_one')
    following_open=prices[['return_date_utc','segment_id','open']].copy()
    following_open['return_date_utc']-=pd.Timedelta(days=1)
    following_open=following_open.rename(columns={'open':'open_t2'})
    returns=returns.merge(following_open,on=['return_date_utc','segment_id'],how='left',validate='one_to_one')
    returns['next_open_return']=returns.open_t2/returns.open-1
    returns['signal_date_utc']=returns.return_date_utc-pd.Timedelta(days=1)
    returns=returns.loc[returns.split.eq('test')]

    wanted=['signal_date_utc','segment_id','prob_high_risk','as_of_utc','state_id']
    merged=returns.merge(prediction[wanted],on=['signal_date_utc','segment_id'],validate='one_to_one')
    if len(merged)!=len(returns):raise ValueError('Incomplete V2 prediction/date coverage')
    signal_features=features[['date_utc','segment_id','rv21']].rename(columns={'date_utc':'signal_date_utc'})
    merged=merged.merge(signal_features,on=['signal_date_utc','segment_id'],validate='one_to_one')
    if (merged.as_of_utc>merged.return_date_utc).any():raise ValueError('Signal not available at execution time')
    if not (merged.signal_date_utc<merged.return_date_utc).all():raise ValueError('Signal must precede return')
    return merged,metadata


def run():
    out=ROOT/'outputs/research_v2/m5';out.mkdir(parents=True,exist_ok=True)
    performance=[];paths=[];intervals=[]
    bt=load_backtest_config()
    for asset in ['BTC','ETH']:
        inputs,metadata=aligned_inputs(asset)
        risk=regime_weights(inputs.prob_high_risk);vol=volatility_weights(inputs.rv21,.4)
        weights={'buy_and_hold':np.ones(len(inputs)),'volatility_targeting':vol,'regime_defensive':risk,'regime_volatility_targeting':risk*vol}
        for scenario,rules in bt['scenarios'].items():
            valid=np.ones(len(inputs),dtype=bool) if rules['return_basis']=='close_to_close' else inputs.next_open_return.notna().to_numpy()
            sample=inputs.loc[valid];returns=sample.target_simple_return if rules['return_basis']=='close_to_close' else sample.next_open_return
            for fee in [.0005,.001,.002]:
                for strategy,w in weights.items():
                    sim=simulate(w[valid],returns,fee_rate=fee,turnover_method=rules['turnover_method'])
                    dates=sample.return_date_utc
                    metrics=performance_metrics(sim.net,sim.nav,sim.turnover,sim.fee,(dates.iloc[-1]-dates.iloc[0]).days+1)
                    identity={'asset':asset,'scenario':scenario,'fee_rate':fee,'strategy':strategy,'model_run_id':metadata['candidate_id']}
                    performance.append({**identity,**metrics,'n':len(sim),'sample_status':'historical_exploratory'})
                    for key,value in identity.items():sim[key]=value
                    sim['date_utc']=dates.dt.strftime('%Y-%m-%d').to_numpy()
                    sim['signal_date_utc']=sample.signal_date_utc.dt.strftime('%Y-%m-%d').to_numpy()
                    sim['as_of_utc']=sample.as_of_utc.astype(str).to_numpy();paths.append(sim)
    nav=pd.concat(paths,ignore_index=True)
    for asset in ['BTC','ETH']:
        subset=nav.loc[nav.asset.eq(asset)&nav.scenario.eq('baseline_close_to_close')&nav.fee_rate.eq(.001)]
        matrix=subset.pivot(index='date_utc',columns='strategy',values='net')
        for block in [14,21,42]:
            ix=moving_blocks(len(matrix),1000,block,20261024)
            ref=_bootstrap_metrics(matrix.volatility_targeting.to_numpy()[ix])['Sharpe']
            for strategy in ['regime_defensive','regime_volatility_targeting']:
                bootstrap=_bootstrap_metrics(matrix[strategy].to_numpy()[ix])['Sharpe']-ref
                point=(matrix[strategy].mean()/matrix[strategy].std()-matrix.volatility_targeting.mean()/matrix.volatility_targeting.std())*np.sqrt(365)
                centered=bootstrap-point
                pvalue=(1+int((abs(centered)>=abs(point)).sum()))/(len(centered)+1)
                low,high=np.nanquantile(bootstrap,[.025,.975])
                intervals.append({'asset':asset,'strategy':strategy,'reference':'volatility_targeting','metric':'net_Sharpe_difference',
                                  'point':point,'ci_low':low,'ci_high':high,'block_days':block,'bootstrap_p_two_sided':pvalue,
                                  'scope':'conditional fixed-signal paired block bootstrap; exploratory, not independent confirmation'})
    ci=pd.DataFrame(intervals)
    # A separate asset x strategy family for each preregistered block sensitivity.
    for block,g in ci.groupby('block_days'):
        ci.loc[g.index,'holm_adjusted_p']=multipletests(g.bootstrap_p_two_sided,method='holm')[1]
    pd.DataFrame(performance).to_csv(out/'performance.csv',index=False)
    nav.to_csv(out/'nav.csv',index=False);ci.to_csv(out/'incremental_uncertainty.csv',index=False)
    manifest={'status':'complete','research_confirmation':'pending','acknowledge_unstable':True,
              'strategy_parameters_tuned_on_test':False,'assumption':'close-to-close is idealized; next-open sensitivity, no intraday latency model',
              'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.name!='manifest.json'}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))


if __name__=='__main__':run()
