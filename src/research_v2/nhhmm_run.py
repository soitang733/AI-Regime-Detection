"""NHHMM real-data experiments gated by the locked simulation protocol."""
import hashlib
import itertools
import json
import time
from datetime import datetime,timezone
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from src.models.inference import sequence_starts
from src.models.reports import train_mapping
from src.research_v2.nhhmm import GaussianNHHMM
from src.utils.config import ROOT
from src.research_v2.provenance import guard,model_inputs

FAMILIES={f:[f] for f in ['rv21','log_dollar_volume','amihud_illiq','funding_sum','vix','dxy_return_1d','oi_growth_7d','stablecoin_supply_growth_7d']}
FAMILIES.update(rv_volume=['rv21','log_dollar_volume'],macro=['vix','dxy_return_1d'],rv_funding=['rv21','funding_sum'])
CORE=['log_return','rv21','log_dollar_volume']


def prepare(frame,features):
    dev=frame.loc[frame.split.ne('test')].copy()
    train=dev.loc[dev.split.eq('train')]
    coverage=train[features].notna().mean()
    start=frame.date_utc.min();window='full_history'
    if coverage.min()<.8:
        first=[train.loc[train[c].notna(),'date_utc'].min() for c in features]
        if any(pd.isna(x) for x in first): raise ValueError('No train observations for covariate')
        start=max(first);window='common_window'
    used=frame.loc[frame.date_utc.ge(start)].copy()
    train=used.loc[used.split.eq('train')];validation=used.loc[used.split.eq('validation')]
    if len(train)<730 or len(validation)<180:raise ValueError('Common window below 730 train / 180 validation days')
    if train[features].notna().mean().min()<.8:raise ValueError('Coverage remains below 80% in eligible window')
    medians=train[features].median()
    indicator=[c for c in features if train[c].isna().any()]
    z=used[features].fillna(medians).copy()
    for c in indicator:z[c+'_missing']=used[c].isna().astype(float)
    train_mask=used.split.eq('train').to_numpy()
    zs=StandardScaler().fit(z.loc[train_mask]);xs=StandardScaler().fit(used.loc[train_mask,CORE])
    zn=zs.transform(z);xn=xs.transform(used[CORE])
    design=np.column_stack([np.ones(train_mask.sum()),zn[train_mask]])
    condition=float(np.linalg.cond(design))
    if np.linalg.matrix_rank(design)!=design.shape[1] or condition>1e8:raise ValueError('Rank deficient or ill-conditioned design')
    return used,xn,zn,{'window':window,'start':str(start),'features':features,'indicator':indicator,'medians':medians.to_dict(),'condition_number':condition,'x_scaler':xs,'z_scaler':zs}


def run(shard=0,shards=1):
    guard('m3',model_inputs()+['src/research_v2/nhhmm.py','src/research_v2/nhhmm_run.py'])
    gate=json.loads((ROOT/'outputs/research_v2/m3_simulation/manifest.json').read_text())
    if not gate['gate_passed']:raise ValueError('Simulation gate failed')
    if gate['source_sha256']!=hashlib.sha256((ROOT/'src/research_v2/nhhmm.py').read_bytes()).hexdigest():raise ValueError('NHHMM changed since simulation')
    out=ROOT/'outputs/research_v2/m3';out.mkdir(parents=True,exist_ok=True)
    candidates=out/'candidates';candidates.mkdir(exist_ok=True)
    registry=[{'asset':a,'family':f,'K':k,'seed':s,'penalty':pen,'id':f'{a}_{f}_k{k}_s{s}_l{pen}'} for a,f,k,s,pen in itertools.product(['BTC','ETH'],FAMILIES,[2,3,4],range(5),[0,1,10])]
    registry_path=out/'registry.json'
    if registry_path.exists():
        if json.loads(registry_path.read_text())['candidates']!=registry:raise ValueError('Candidate registry changed')
    else:
        registry_path.write_text(json.dumps({'created_before_fit_utc':datetime.now(timezone.utc).isoformat(),'candidates':registry},indent=2))
    data={a:pd.read_parquet(ROOT/f'outputs/research_v2/m1/features_{a.lower()}.parquet') for a in ['BTC','ETH']}
    prepared={};rows=[];begin=time.monotonic()
    for index,item in enumerate(registry):
        if index % shards != shard:continue
        path=candidates/f"{item['id']}.json"
        if path.exists():rows.append(json.loads(path.read_text()));continue
        if time.monotonic()-begin>86400:break
        tick=time.monotonic();row={**item,'eligible':False}
        try:
            key=(item['asset'],item['family'])
            if key not in prepared:prepared[key]=prepare(data[item['asset']],FAMILIES[item['family']])
            frame,x,z,prep=prepared[key];train=frame.split.eq('train').to_numpy();dev=frame.split.ne('test').to_numpy()
            model=GaussianNHHMM(item['K'],item['penalty'],item['seed']).fit(x[train],z[train],sequence_starts(frame.loc[train]))
            a,s=model.infer(x[dev],z[dev],sequence_starts(frame.loc[dev]))
            share=np.bincount(a[:train.sum()].argmax(1),minlength=item['K'])/train.sum()
            row.update(converged=model.converged_,iterations=model.n_iter_,min_train_share=float(share.min()),
                       validation_log_score=float(s[~train[dev]].mean()),window=prep['window'],sample_start=prep['start'],
                       gradient_norm=model.transition_gradient_norm_,optimizer_success=model.transition_optimizer_success_,
                       expected_transition_counts=model.expected_transition_counts_.tolist())
            row['eligible']=bool(model.converged_ and share.min()>=.02 and np.isfinite(s).all())
            if row['eligible']:
                mapping,risk=train_mapping(frame.loc[train],a[:train.sum()])
                row.update(label_map=mapping,high_risk_state=risk)
                joblib.dump({'model':model,'preprocessing':prep,'metadata':row},candidates/f"{item['id']}.joblib")
            else:row['reason']='nonconvergence_or_sparse_train_state'
        except (ValueError,FloatingPointError,np.linalg.LinAlgError) as exc:row['reason']=str(exc)
        row['runtime_seconds']=time.monotonic()-tick;path.write_text(json.dumps(row,indent=2));rows.append(row)
        print(f"{len(rows)}/{len(registry)} {item['id']} valid={row['eligible']} seconds={row['runtime_seconds']:.2f}",flush=True)
    rows=[json.loads((candidates/f"{item['id']}.json").read_text()) for item in registry if (candidates/f"{item['id']}.json").exists()]
    if len(rows)!=len(registry):
        (out/f'shard_{shard}_status.json').write_text(json.dumps({'completed_globally':len(rows),'planned':len(registry)}))
        return
    pd.DataFrame(rows).to_csv(out/'candidate_results.csv',index=False)
    # Families with different sample starts are not ranked against one another.
    choices=[]
    fits=pd.DataFrame(rows)
    for (asset,family,k,penalty),g in fits.groupby(['asset','family','K','penalty']):
        valid=g.loc[g.eligible]
        if len(valid)<3:continue
        winner=valid.sort_values(['validation_log_score','seed'],ascending=[False,True]).iloc[0].to_dict()
        choices.append(winner)
    (out/'qualified_groups.json').write_text(json.dumps(choices,indent=2))
    (out/'manifest.json').write_text(json.dumps({'status':'grid_complete' if len(rows)==len(registry) else 'budget_checkpoint',
                  'completed':len(rows),'planned':len(registry),'qualified_groups':len(choices),
                  'historical_test_evaluated':False,'real_data_performance_confirmed':False},indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--shard',type=int,default=0);parser.add_argument('--shards',type=int,default=1)
    args=parser.parse_args()
    if not 0<=args.shard<args.shards:raise ValueError('Invalid shard')
    run(args.shard,args.shards)
