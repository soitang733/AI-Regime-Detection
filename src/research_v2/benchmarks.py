"""Benchmark adapters with explicit distinctions between states and segments."""
import itertools
import json
import time
import warnings
import joblib
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.cluster import HDBSCAN,KMeans
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
from statsmodels.tsa.regime_switching.markov_autoregression import MarkovAutoregression
from src.utils.config import ROOT
from src.research_v2.provenance import guard,model_inputs


def page_hinkley(x,threshold=10.,delta=.05):
    """Two-sided online mean-change alarms; segment IDs are not recurrent regimes."""
    labels=[];alarms=[];mean=0.;n=0;up=down=0.;segment=0
    for t,value in enumerate(np.asarray(x,dtype=float)):
        if not np.isfinite(value):raise ValueError('Nonfinite observation')
        n+=1;mean+=(value-mean)/n
        up=max(0.,up+value-mean-delta);down=max(0.,down+mean-value-delta)
        alarm=max(up,down)>threshold
        if alarm:
            segment+=1;n=0;mean=0.;up=down=0.
        labels.append(segment);alarms.append(alarm)
    return np.array(labels),np.array(alarms)


def density_adapter(x,labels):
    centers=[];radii=[];ids=[]
    for k in sorted(set(labels)-{-1}):
        cluster=x[labels==k]
        medoid=cluster[np.argmin(cdist(cluster,cluster).sum(1))]
        centers.append(medoid);radii.append(np.quantile(np.linalg.norm(cluster-medoid,axis=1),.95));ids.append(k)
    return np.array(centers),np.array(radii),np.array(ids,dtype=int)


def assign_density(x,adapter):
    centers,radii,ids=adapter
    if not len(ids):return np.full(len(x),-1,dtype=int)
    dist=cdist(x,centers);nearest=dist.argmin(1)
    return np.where(dist[np.arange(len(x)),nearest]<=radii[nearest],ids[nearest],-1)


def ms_model(y,k,order):
    return (MarkovRegression(y,k_regimes=k,trend='c',switching_variance=True) if order==0 else
            MarkovAutoregression(y,k_regimes=k,order=order,trend='c',switching_ar=True,switching_variance=True))


def run():
    guard('m4',model_inputs()+['src/research_v2/benchmarks.py','reports/v2_benchmark_specification.md'])
    out=ROOT/'outputs/research_v2/m4';out.mkdir(parents=True,exist_ok=True)
    specs=[]
    for a in ['BTC','ETH']:
        for method,k,s in itertools.product(['GMM','KMeans'],[2,3,4],range(5)):
            specs.append({'asset':a,'method':method,'K':k,'seed':s,'id':f'{a}_{method}_{k}_{s}'})
        for k,s,order in itertools.product([2,3,4],range(5),[0,1]):
            specs.append({'asset':a,'method':'MSAR','K':k,'seed':s,'order':order,'id':f'{a}_MSAR_{k}_{s}_{order}'})
        for size,samples in itertools.product([30,60,120],[5,15]):
            specs.append({'asset':a,'method':'HDBSCAN','size':size,'samples':samples,'id':f'{a}_HDBSCAN_{size}_{samples}'})
        for threshold in [5,10,20]: specs.append({'asset':a,'method':'PageHinkley','threshold':threshold,'id':f'{a}_PH_{threshold}'})
    (out/'registry.json').write_text(json.dumps(specs,indent=2))
    rows=[]
    for spec in specs:
        dest=out/f"{spec['id']}.json"
        if dest.exists():rows.append(json.loads(dest.read_text()));continue
        tick=time.monotonic();row={**spec,'eligible':False}
        frame=pd.read_parquet(ROOT/f"outputs/research_v2/m1/features_{spec['asset'].lower()}.parquet")
        # Do not inspect test in fit or candidate selection.
        frame=frame.loc[frame.split.ne('test')].copy();train=frame.split.eq('train').to_numpy();val=~train
        scaler=StandardScaler().fit(frame.loc[train,['log_return','rv21','log_dollar_volume']]);x=scaler.transform(frame[['log_return','rv21','log_dollar_volume']])
        try:
            model=None;offset=0
            if spec['method']=='GMM':
                model=GaussianMixture(spec['K'],covariance_type='diag',n_init=1,max_iter=500,tol=.001,reg_covar=1e-6,random_state=spec['seed']).fit(x[train])
                labels=model.predict(x);row.update(eligible=bool(model.converged_),validation_log_score=float(model.score_samples(x[val]).mean()))
            elif spec['method']=='KMeans':
                model=KMeans(spec['K'],n_init=10,random_state=spec['seed']).fit(x[train]);labels=model.predict(x)
                row.update(eligible=True,train_inertia=model.inertia_,probabilities_available=False)
            elif spec['method']=='MSAR':
                np.random.seed(spec['seed']);y=frame.log_return.to_numpy()*100;offset=spec['order']
                with warnings.catch_warnings(record=True) as recorded:
                    warnings.simplefilter('always')
                    fitted=ms_model(y[train],spec['K'],offset).fit(maxiter=500,disp=False,search_reps=1,search_iter=10)
                filtered=ms_model(y,spec['K'],offset).filter(fitted.params)
                labels=np.asarray(filtered.filtered_marginal_probabilities).argmax(1)
                score=np.asarray(filtered.llf_obs)
                row.update(eligible=bool(fitted.mle_retvals.get('converged',False)),validation_log_score=float(score[val[offset:]].mean()),
                           feature_space='100 * daily log return',warnings=list(dict.fromkeys(str(w.message) for w in recorded)))
                model={'params':fitted.params,'K':spec['K'],'order':offset}
            elif spec['method']=='HDBSCAN':
                model=HDBSCAN(min_cluster_size=spec['size'],min_samples=spec['samples']).fit(x[train])
                adapter=density_adapter(x[train],model.labels_);labels=assign_density(x,adapter);labels[train]=model.labels_
                row.update(eligible=True,K=len(adapter[2]),validation_noise_rate=float((labels[val]==-1).mean()),
                           assignment='fixed nearest train medoid with 95% train-radius; not native prediction',probabilities_available=False)
                model={'model':model,'adapter':adapter}
            else:
                labels,alarms=page_hinkley(x[:,0],spec['threshold'])
                row.update(eligible=True,validation_alarm_count=int(alarms[val].sum()),probabilities_available=False,
                           state_kind='unique chronological segments, not recurrent regimes')
            pred=frame[['asset','date_utc','split']].iloc[offset:].copy();pred['state_id']=labels
            pred.to_csv(out/f"{spec['id']}_development.csv",index=False)
            vv=labels[val[offset:]];row['validation_persistence']=float((vv[1:]==vv[:-1]).mean())
            if model is not None:joblib.dump({'model':model,'scaler':scaler,'specification':spec},out/f"{spec['id']}.joblib")
        except (ValueError,FloatingPointError,np.linalg.LinAlgError,RuntimeError) as exc:row['reason']=str(exc)
        row['runtime_seconds']=time.monotonic()-tick;dest.write_text(json.dumps(row,indent=2));rows.append(row)
        print(f"{len(rows)}/{len(specs)} {spec['id']} eligible={row['eligible']}",flush=True)
    pd.DataFrame(rows).to_csv(out/'development_results.csv',index=False)


if __name__=='__main__':run()
