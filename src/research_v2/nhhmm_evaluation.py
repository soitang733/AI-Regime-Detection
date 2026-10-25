"""Development-selected dynamic forecasts and explicitly model-derived RQ3 targets."""
import hashlib
import json
from datetime import datetime,timezone
import joblib
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from statsmodels.stats.multitest import multipletests
from sklearn.metrics import brier_score_loss,average_precision_score
import yaml
from src.models.inference import infer,sequence_starts
from src.research.economics import moving_blocks
from src.research.economics import economic_evidence
from src.research_v2.nhhmm_run import prepare,FAMILIES
from src.utils.config import ROOT


def run():
    source=ROOT/'outputs/research_v2/m3';status=json.loads((source/'manifest.json').read_text())
    if status['status']!='grid_complete':raise ValueError('NHHMM grid not complete; no premature selection')
    out=ROOT/'outputs/research_v2/m3_evaluation';out.mkdir(parents=True,exist_ok=True)
    qualified=pd.DataFrame(json.loads((source/'qualified_groups.json').read_text()))
    qualified.to_csv(out/'qualified_family_comparison.csv',index=False)
    all_fits=pd.read_csv(source/'candidate_results.csv')
    family_status=all_fits.groupby(['asset','family']).agg(attempted=('id','count'),valid_fits=('eligible','sum')).reset_index()
    family_status['interpretation']='Compare validation scores only within the same sample window; not evidence of predictor causality.'
    family_status.to_csv(out/'family_coverage_and_failures.csv',index=False)
    full=qualified.loc[qualified.window.eq('full_history')]
    selected=full.sort_values(['validation_log_score','K','penalty','seed'],ascending=[False,True,False,True]).groupby('asset').head(1)
    (out/'selection.json').write_text(json.dumps({'locked_at_utc':datetime.now(timezone.utc).isoformat(),
        'selected':json.loads(selected.to_json(orient='records')),'selection_rule':'full-history qualified groups; validation LL, K, stronger penalty, seed; common-window groups reported separately'},indent=2))
    coefficients=[];metrics=[]
    hmmfits=pd.read_csv(ROOT/'outputs/research_v2/m2/candidate_results.csv')
    for row in selected.to_dict('records'):
        asset=row['asset'];k=int(row['K']);bundle=joblib.load(source/f"candidates/{row['id']}.joblib");model=bundle['model']
        frame=pd.read_parquet(ROOT/f'outputs/research_v2/m1/features_{asset.lower()}.parquet')
        frame,x,z,prep=prepare(frame,FAMILIES[row['family']])
        alpha,scores,gamma,xi=model.infer(x,z,sequence_starts(frame),smooth=True)
        transition=model.transitions(z);forecast=np.einsum('ti,tij->tj',alpha,transition)
        if abs(forecast.sum(1)-1).max()>1e-8:raise ValueError('Invalid next-state probabilities')
        prefix=model.infer(x[:100],z[:100],sequence_starts(frame.iloc[:100]))[0]
        if abs(prefix-alpha[:100]).max()>1e-10:raise ValueError('Prefix filtering changed')
        output=frame[['asset','date_utc','split','decision_time_utc']].rename(columns={'decision_time_utc':'as_of_utc'}).copy()
        output['model_run_id']=row['id'];output['K']=k;output['state_id']=alpha.argmax(1);output['probability_type']='filtered'
        risk=int(row['high_risk_state']);output['prob_high_risk']=alpha[:,risk]
        train_mask=frame.split.eq('train').to_numpy()
        economics=economic_evidence(frame.loc[train_mask],alpha[train_mask],row['label_map'],
            yaml.safe_load((ROOT/'config/research.yaml').read_text())['economics'],20261024)
        economics.to_csv(out/f'{asset.lower()}_economic_labels.csv',index=False)
        economic_map={int(r.state_id):r.economic_label for r in economics.itertuples()}
        for j in range(k):output[f'prob_state_{j}']=alpha[:,j];output[f'prob_next_state_{j}']=forecast[:,j]
        output.to_csv(out/f'{asset.lower()}_filtered.csv',index=False)
        smooth=output[['asset','date_utc','split','model_run_id']].copy();smooth['probability_type']='smoothed';smooth['hindsight']=True
        for j in range(k):smooth[f'prob_state_{j}']=gamma[:,j]
        smooth.to_csv(out/f'{asset.lower()}_smoothed.csv',index=False)
        counts=model.expected_transition_counts_;exits=counts.sum(1)-counts.diagonal()
        feature_names=['intercept']+prep['features']+[f'{f}_missing' for f in prep['indicator']]
        seed_coefficients=[]
        for seed in range(5):
            cid=f"{asset}_{row['family']}_k{k}_s{seed}_l{int(row['penalty'])}"
            record=json.loads((source/f'candidates/{cid}.json').read_text())
            if not record['eligible']:continue
            other=joblib.load(source/f'candidates/{cid}.joblib')['model']
            _,alignment=linear_sum_assignment(((model.means_[:,None]-other.means_[None])**2).sum(2))
            full_coefficients=np.concatenate([other.coefficients_,np.zeros((k,1,z.shape[1]+1))],axis=1)
            reordered=full_coefficients[alignment][:,alignment]
            aligned=(reordered-reordered[:,-1:,:])[:,:-1,:]
            seed_coefficients.append(aligned)
        seed_coefficients=np.asarray(seed_coefficients)
        for i in range(k):
            for j in range(k-1):
                for column,(feature,value) in enumerate(zip(feature_names,model.coefficients_[i,j])):
                    coefficients.append({'asset':asset,'model_run_id':row['id'],'origin_state':i,'destination_state':j,'reference_destination':k-1,
                        'feature':feature,'coefficient':value,'expected_train_transition_count':counts[i,j],'expected_train_origin_exits':exits[i],
                        'passes_event_count_screen':bool(exits[i]>=20 and counts[i,j]>=10),
                        'valid_seed_count':len(seed_coefficients),'aligned_seed_min':float(seed_coefficients[:,i,j,column].min()),
                        'aligned_seed_max':float(seed_coefficients[:,i,j,column].max()),'aligned_seed_std':float(seed_coefficients[:,i,j,column].std()),
                        'uncertainty_kind':'aligned initialization sensitivity, not a confidence interval or posterior',
                        'interpretation':'standardized-input log odds; reference category; no causal or independent significance claim'})
        # Matched-K homogeneous model selected on the same development sample.
        candidates=hmmfits.loc[hmmfits.asset.eq(asset)&hmmfits.fold.eq(2)&hmmfits.rv.eq(21)&hmmfits.K.eq(k)&hmmfits.eligible]
        chosen=candidates.sort_values(['validation_log_score','BIC','seed'],ascending=[False,True,True]).iloc[0]
        homogeneous=joblib.load(ROOT/f"outputs/research_v2/m2/candidates/{chosen.candidate_id}.joblib")
        hm=homogeneous['model'];ha,hs=infer(hm,homogeneous['scaler'].transform(frame[['log_return','rv21','log_dollar_volume']]),frame)
        # Both emission coordinates use the same train scaler and same feature space.
        _,order=linear_sum_assignment(((hm.means_[:,None]-model.means_[None])**2).sum(2))
        target=ha[1:].argmax(1);nq=forecast[:-1,order];hq=(ha@hm.transmat_)[:-1]
        test=frame.split.eq('test').to_numpy()[1:]
        contiguous=pd.to_datetime(frame.date_utc).diff().dt.days.eq(1).to_numpy()[1:]
        mask=test&contiguous
        nloss=-np.log(np.maximum(nq[np.arange(len(target)),target],1e-15))[mask]
        hloss=-np.log(np.maximum(hq[np.arange(len(target)),target],1e-15))[mask]
        delta=nloss-hloss;ix=moving_blocks(len(delta),1000,21,20261024)
        ci=np.quantile(delta[ix].mean(1),[.025,.975])
        adjusted_ci=np.quantile(delta[ix].mean(1),[.0125,.9875])
        centered=delta[ix].mean(1)-delta.mean()
        reference_risk=int(homogeneous['metadata']['high_risk_state'])
        risk_set=mask & (ha[:-1].argmax(1)!=reference_risk)
        events=(target[risk_set]==reference_risk).astype(int)
        predicted=nq[risk_set,reference_risk];reference=hq[risk_set,reference_risk]
        metrics.append({'asset':asset,'model_run_id':row['id'],'homogeneous_reference':chosen.candidate_id,'K':k,'n':len(delta),
            'next_state_logloss_difference':float(delta.mean()),'conditional_ci_low':ci[0],'conditional_ci_high':ci[1],
            'bonferroni_two_assets_ci_low':adjusted_ci[0],'bonferroni_two_assets_ci_high':adjusted_ci[1],
            'bootstrap_p':float((1+(abs(centered)>=abs(delta.mean())).sum())/(len(centered)+1)),
            'stress_proxy_at_risk_days':int(risk_set.sum()),'stress_proxy_entry_events':int(events.sum()),
            'stress_proxy_Brier_NHHMM':brier_score_loss(events,predicted) if len(events) else None,
            'stress_proxy_Brier_HMM':brier_score_loss(events,reference) if len(events) else None,
            'stress_proxy_PR_AUC_NHHMM':average_precision_score(events,predicted) if 0<events.sum()<len(events) else None,
            'stress_proxy_prediction_mean':float(predicted.mean()) if len(events) else None,
            'stress_proxy_event_rate':float(events.mean()) if len(events) else None,
            'observed_predictive_LL_difference':float((scores-hs)[frame.split.eq('test').to_numpy()].mean()),
            'target_definition':'next-day filtered argmax of matched homogeneous HMM; model-derived proxy, not latent truth',
            'alignment':'minimum train emission-mean distance; no test alignment','sample_status':'historical_exploratory',
            'research_confirmation':'pending'})
        last=output.iloc[-1]
        pd.DataFrame([{'state_id':j,'model_label':row['label_map'][str(j)],'economic_label':economic_map[j],'current_probability':alpha[-1,j],
                       'next_day_probability':forecast[-1,j],'date_utc':last.date_utc,'as_of_utc':last.as_of_utc,
                       'model_run_id':row['id']} for j in range(k)]).to_csv(out/f'{asset.lower()}_latest_forecast.csv',index=False)
        dynamic=[]
        for i in range(k):
            for j in range(k):
                dynamic.append(pd.DataFrame({'asset':asset,'date_utc':frame.date_utc,'origin_state':i,'destination_state':j,
                    'conditional_probability':transition[:,i,j],'probability_kind':'P(S_t+1=j | S_t=i, z_t)','model_run_id':row['id']}))
        pd.concat(dynamic).to_csv(out/f'{asset.lower()}_dynamic_transitions.csv',index=False)
        metadata={'asset':asset,'model_run_id':row['id'],'K':k,'label_map':row['label_map'],'high_risk_state':risk,
                  'feature_names':feature_names,'selected_family':row['family'],'penalty':row['penalty'],
                  'expected_train_transition_counts':counts.tolist(),'stability_status':'not_yet_certified',
                  'economic_label_map':economic_map,
                  'sample_status':'historical_exploratory','last_data_date_utc':last.date_utc}
        (out/f'{asset.lower()}_metadata.json').write_text(json.dumps(metadata,indent=2))
        joblib.dump({**bundle,'metadata':metadata},out/f'{asset.lower()}.joblib')
    pd.DataFrame(coefficients).to_csv(out/'transition_coefficients.csv',index=False)
    metrics=pd.DataFrame(metrics)
    if len(metrics):metrics['holm_adjusted_p']=multipletests(metrics.bootstrap_p,method='holm')[1]
    metrics.to_csv(out/'predictive_comparison.csv',index=False)
    (out/'manifest.json').write_text(json.dumps({'status':'complete','independent_confirmation':'pending',
        'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.name!='manifest.json'}},indent=2))


if __name__=='__main__':run()
