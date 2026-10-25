"""Predeclared HMM grid, train-only transforms, pooled stability and frozen exports."""
from __future__ import annotations
import hashlib
import itertools
import json
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler

from src.models.inference import infer, sequence_lengths, smooth_probabilities, emission_log_density, diagonal_variances, sequence_starts
from src.models.reports import train_mapping
from src.research.robustness import initialized_hmm
from src.research.economics import economic_evidence
from src.utils.config import ROOT
from src.research_v2.provenance import guard,model_inputs

SETTINGS={'initial_self_transition':.95,'max_iter':500,'tol':.001}
FOLDS=[('2021-05-05','2022-05-05'),('2022-05-05','2023-05-05'),('2023-05-05','2025-01-24')]


def select_candidate(rows):
    eligible=pd.DataFrame(rows)
    eligible=eligible.loc[eligible.eligible & eligible.K.le(4)]
    if eligible.empty:
        raise ValueError('No valid K2..4 candidate; preserve failures, never relax gates')
    best=eligible.validation_log_score.max()
    return eligible.loc[eligible.validation_log_score >= best-1e-8].sort_values(['BIC','K','seed','initializer']).iloc[0].to_dict()


def grid():
    return [{'asset':a,'fold':f,'rv':rv,'K':k,'seed':seed,'initializer':init,
             'candidate_id':f'{a}_f{f}_rv{rv}_k{k}_{init}_s{seed}'}
            for a,f,rv,k,seed,init in itertools.product(['BTC','ETH'],range(3),[14,21,30],[2,3,4,5],range(5),['kmeans','volatility_quantiles'])]


def stability(rows, directory):
    output=[]
    fits=pd.DataFrame(rows)
    for (asset,fold,rv,k), group in fits.groupby(['asset','fold','rv','K']):
        for family in ['pooled','kmeans','volatility_quantiles']:
            good=group.loc[group.eligible]
            if family!='pooled': good=good.loc[good.initializer.eq(family)]
            cache=[np.load(directory/f'{cid}.npz') for cid in good.candidate_id]
            aris=[]; maes=[]; disagreement=[]; jaccard=[]
            for left,right in itertools.combinations(cache,2):
                aris.append(adjusted_rand_score(left['states'],right['states']))
                maes.append(float(abs(left['risk']-right['risk']).mean()))
                a,b=left['risk']>=.5,right['risk']>=.5
                disagreement.append(float((a!=b).mean()))
                jaccard.append(float((a & b).sum()/(a | b).sum()) if (a | b).any() else np.nan)
            median=float(np.median(aris)) if aris else np.nan
            minimum=float(np.min(aris)) if aris else np.nan
            metric_gate=len(good)>=3 and median>=.8 and minimum>=.5
            represented=int(good.initializer.nunique())
            output.append({'asset':asset,'fold':fold,'rv':rv,'K':k,'family':family,'valid_fits':len(good),
                           'median_ari':median,'minimum_ari':minimum,'metric_gate_passed':metric_gate,
                           'eligible_initializer_families':represented,
                           'stable':metric_gate and (family!='pooled' or represented>=2),
                           'scope':'pooled across at least two eligible initializer families' if family=='pooled' and represented>=2 else 'within one eligible initializer family only',
                           'risk_probability_mae':np.mean(maes) if maes else np.nan,
                           'risk_disagreement':np.mean(disagreement) if disagreement else np.nan,
                           'risk_jaccard':np.nanmean(jaccard) if np.isfinite(jaccard).any() else np.nan})
            for item in cache: item.close()
    return pd.DataFrame(output)


def run():
    guard('m2',model_inputs()+['src/research_v2/hmm.py','src/research/robustness.py','src/models/inference.py','src/research/economics.py'])
    out=ROOT/'outputs/research_v2/m2'; out.mkdir(parents=True,exist_ok=True)
    candidates=out/'candidates'; candidates.mkdir(exist_ok=True)
    registry=grid()
    spec={'protocol':'reports/m0_lock/PROTOCOL_V2_M0.md','candidates':registry,'historical_test_used_for_selection':False}
    registry_file=out/'registry.json'
    encoded=json.dumps(spec,indent=2)
    if registry_file.exists() and registry_file.read_text()!=encoded: raise ValueError('Registry changed')
    registry_file.write_text(encoded)
    frames={a:pd.read_parquet(ROOT/f'outputs/research_v2/m1/features_{a.lower()}.parquet') for a in ['BTC','ETH']}
    rows=[]
    for item in registry:
        dest=candidates/f"{item['candidate_id']}.json"
        if dest.exists(): rows.append(json.loads(dest.read_text())); continue
        tick=time.monotonic(); row={**item,'eligible':False,'reason':''}
        end,valend=FOLDS[item['fold']]
        cols=['log_return',f"rv{item['rv']}",'log_dollar_volume']
        history=frames[item['asset']].loc[lambda d:d.date_utc.le(valend)].dropna(subset=cols).copy()
        history['split']=np.where(history.date_utc.le(end),'train','validation')
        train=history.loc[history.split.eq('train')]
        scaler=StandardScaler().fit(train[cols]); x=scaler.transform(train[cols]); allx=scaler.transform(history[cols])
        try:
            model=initialized_hmm(x,item['K'],item['seed'],item['initializer'],SETTINGS)
            model.fit(x,lengths=sequence_lengths(train))
            gains=list(model.monitor_.history); gain=gains[-1]-gains[-2] if len(gains)>1 else np.inf
            alpha,score=infer(model,x,train)
            share=np.bincount(alpha.argmax(1),minlength=item['K'])/len(train)
            params=(item['K']-1)+item['K']*(item['K']-1)+2*item['K']*len(cols)
            row.update(iterations=model.monitor_.iter,last_gain=gain,min_train_share=float(share.min()),
                       train_n=len(train),train_LL=float(score.sum()),AIC=-2*score.sum()+2*params,
                       BIC=-2*score.sum()+params*np.log(len(train)),features=cols)
            if not -1e-6<=gain<=.001 or share.min()<.02:
                row['reason']='nonconvergence_or_sparse_train_state'
            else:
                mapping,risk=train_mapping(train,alpha)
                posterior,scores=infer(model,allx,history); valid=history.split.eq('validation').to_numpy()
                row.update(eligible=True,validation_log_score=float(scores[valid].mean()),label_map=mapping,high_risk_state=risk)
                np.savez_compressed(candidates/f"{item['candidate_id']}.npz",states=posterior[valid].argmax(1),risk=posterior[valid,risk])
                joblib.dump({'model':model,'scaler':scaler,'metadata':row.copy()},candidates/f"{item['candidate_id']}.joblib")
        except (ValueError,FloatingPointError,np.linalg.LinAlgError) as exc: row['reason']=str(exc)
        row['runtime_seconds']=time.monotonic()-tick
        dest.write_text(json.dumps(row,indent=2))
        rows.append(row)
        print(f"{len(rows)}/{len(registry)} {item['candidate_id']} eligible={row['eligible']}",flush=True)
    fits=pd.DataFrame(rows);fits.to_csv(out/'candidate_results.csv',index=False)
    stable=stability(rows,candidates);stable.to_csv(out/'stability.csv',index=False)
    settings=yaml.safe_load((ROOT/'config/research.yaml').read_text())['economics']
    for asset in ['BTC','ETH']:
        chosen=select_candidate([r for r in rows if r['asset']==asset and r['fold']==2 and r['rv']==21])
        for field in ['K','seed','fold','rv','high_risk_state']:
            chosen[field]=int(chosen[field])
        bundle=joblib.load(candidates/f"{chosen['candidate_id']}.joblib")
        model,scaler=bundle['model'],bundle['scaler']
        frame=frames[asset].dropna(subset=chosen['features']).copy(); x=scaler.transform(frame[chosen['features']])
        # Commit selection record BEFORE evaluating historical test.
        metadata={**chosen,'selection_locked_at_utc':datetime.now(timezone.utc).isoformat(),
                  'selection_rule':'validation LL, tie BIC/K/seed; K5 sensitivity only',
                  'sample_status':'historical_exploratory','probability_type':'filtered',
                  'K':model.n_components,'transition_matrix':model.transmat_.tolist(),
                  'stability':stable.loc[stable.asset.eq(asset)&stable.fold.eq(2)&stable.rv.eq(21)&stable.K.eq(model.n_components)&stable.family.eq('pooled')].to_dict('records')[0]}
        (out/f'{asset.lower()}_selection.json').write_text(json.dumps(metadata,indent=2))
        alpha,scores=infer(model,x,frame)
        n=min(100,len(frame));prefix,_=infer(model,x[:n],frame.iloc[:n])
        assert np.max(abs(prefix-alpha[:n]))<=1e-10
        predictions=frame[['asset','date_utc','split','segment_id','decision_time_utc']].rename(columns={'decision_time_utc':'as_of_utc'})
        predictions['K']=model.n_components; predictions['state_id']=alpha.argmax(1)
        predictions['model_run_id']=chosen['candidate_id']; predictions['probability_type']='filtered'
        predictions['label']=predictions.state_id.map({int(k):v for k,v in chosen['label_map'].items()})
        for k in range(model.n_components):
            predictions[f'prob_state_{k}']=alpha[:,k]
            predictions[f'prob_next_state_{k}']=(alpha@model.transmat_)[:,k]
        predictions['prob_high_risk']=alpha[:,chosen['high_risk_state']]
        predictions.to_csv(out/f'{asset.lower()}_filtered.csv',index=False)
        smoothed=smooth_probabilities(emission_log_density(x,model.means_,diagonal_variances(model)),model.startprob_,model.transmat_,sequence_starts(frame))
        hindsight=predictions[['asset','date_utc','split','model_run_id']].copy()
        hindsight['probability_type']='smoothed';hindsight['hindsight']=True
        for k in range(model.n_components): hindsight[f'prob_state_{k}']=smoothed[:,k]
        hindsight.to_csv(out/f'{asset.lower()}_smoothed.csv',index=False)
        mask=frame.split.eq('train').to_numpy()
        econ=economic_evidence(frame.loc[mask],alpha[mask],chosen['label_map'],settings,20261024)
        econ.to_csv(out/f'{asset.lower()}_economic_labels.csv',index=False)
        metadata['economic_labels']=econ.to_dict('records')
        bundle={'model':model,'scaler':scaler,'metadata':metadata}
        joblib.dump(bundle,out/f'{asset.lower()}.joblib')
        loaded=joblib.load(out/f'{asset.lower()}.joblib')
        restored,_=infer(loaded['model'],loaded['scaler'].transform(frame[chosen['features']]),frame)
        assert np.max(abs(restored-alpha))<=1e-10
        (out/f'{asset.lower()}_metadata.json').write_text(json.dumps(metadata,indent=2))
    manifest={'status':'complete','candidate_count':len(rows),'created_at_utc':datetime.now(timezone.utc).isoformat(),
              'sample_status':'historical_exploratory','files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='manifest.json'}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))


if __name__=='__main__': run()
