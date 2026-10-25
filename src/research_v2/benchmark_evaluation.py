"""Freeze benchmark selection before historical OOS; retain unselected seed diagnostics."""
import itertools
import json
from datetime import datetime,timezone
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler
from src.research_v2.benchmarks import ms_model,assign_density,page_hinkley
from src.research_v2.msgarch import evaluate,parameters
from src.utils.config import ROOT


def run():
    out=ROOT/'outputs/research_v2/m4_evaluation';out.mkdir(parents=True,exist_ok=True)
    paths={'standard':ROOT/'outputs/research_v2/m4','MSGARCH':ROOT/'outputs/research_v2/m4_msgarch'}
    allfits=pd.read_csv(paths['standard']/'development_results.csv')
    garch=pd.read_csv(paths['MSGARCH']/'development_results.csv');garch['method']='MSGARCH'
    fits=pd.concat([allfits,garch],ignore_index=True);selected=[]
    for (asset,method),group in fits.loc[fits.eligible].groupby(['asset','method']):
        if method in ['GMM','MSAR','MSGARCH']:
            selected.append(group.sort_values(['validation_log_score','K','seed'],ascending=[False,True,True]).iloc[0]['id'])
        elif method=='KMeans':
            selected.extend(group.sort_values('train_inertia').groupby('K').first()['id'].tolist())
        else:selected.extend(group.id.tolist())
    (out/'selection.json').write_text(json.dumps({'locked_at_utc':datetime.now(timezone.utc).isoformat(),'selected_ids':selected,
        'selection_sample':'train/validation only','KMeans':'train inertia within K; no across-K champion','density_and_change_point':'report all preregistered configurations'},indent=2))
    metrics=[];states={}
    for row in fits.loc[fits.eligible].to_dict('records'):
        asset,method=row['asset'],row['method'];folder=paths['MSGARCH' if method=='MSGARCH' else 'standard']
        frame=pd.read_parquet(ROOT/f'outputs/research_v2/m1/features_{asset.lower()}.parquet')
        cols=['log_return','rv21','log_dollar_volume'];train=frame.split.eq('train').to_numpy();test=frame.split.eq('test').to_numpy()
        offset=0;score=None
        if method=='PageHinkley':
            scaler=StandardScaler().fit(frame.loc[train,cols]);x=scaler.transform(frame[cols]);labels,_=page_hinkley(x[:,0],row['threshold'])
        else:
            bundle=joblib.load(folder/f"{row['id']}.joblib")
            if method=='MSGARCH':
                alpha,score,_=evaluate(frame.log_return.to_numpy()*100,*parameters(bundle['theta'],int(row['K'])));labels=alpha.argmax(1)
            else:
                x=bundle['scaler'].transform(frame[cols]);model=bundle['model']
                if method in ['GMM','KMeans']:
                    labels=model.predict(x)
                    if method=='GMM':score=model.score_samples(x)
                elif method=='HDBSCAN':
                    labels=assign_density(x,model['adapter']);labels[train]=model['model'].labels_
                else:
                    offset=int(row['order']);filtered=ms_model(frame.log_return.to_numpy()*100,int(row['K']),offset).filter(model['params'])
                    labels=np.asarray(filtered.filtered_marginal_probabilities).argmax(1);score=np.asarray(filtered.llf_obs)
        used=frame.iloc[offset:].copy();mask=test[offset:];tail=labels[mask]
        if method!='PageHinkley':states[(asset,method,int(row['K']),row['id'])]=tail
        metrics.append({'asset':asset,'method':method,'id':row['id'],'selected_on_development':row['id'] in selected,'K':row['K'],
                        'period':'historical_test','n':int(mask.sum()),'persistence':float((tail[1:]==tail[:-1]).mean()),
                        'noise_rate':float((tail==-1).mean()),'mean_log_score':float(score[mask].mean()) if score is not None else np.nan,
                        'score_space':'100 * log return' if method in ['MSAR','MSGARCH'] else '3D train-standardized core' if method=='GMM' else 'no likelihood'})
        if row['id'] in selected:
            pred=used[['asset','date_utc','split']].copy();pred['state_id']=labels
            pred.to_csv(out/f"{row['id']}_states.csv",index=False)
    stability=[]
    for asset,method,k in sorted(set(key[:3] for key in states)):
        group=[v for key,v in states.items() if key[:3]==(asset,method,k)]
        pairs=[adjusted_rand_score(a,b) for a,b in itertools.combinations(group,2) if len(a)==len(b)]
        stability.append({'asset':asset,'method':method,'K':k,'n_fits':len(group),'median_ari':np.median(pairs) if pairs else np.nan,
                          'minimum_ari':np.min(pairs) if pairs else np.nan,'scope':'historical test; multiple MSAR orders pooled explicitly'})
    pd.DataFrame(metrics).to_csv(out/'historical_metrics.csv',index=False)
    pd.DataFrame(stability).to_csv(out/'seed_stability.csv',index=False)


if __name__=='__main__':run()
