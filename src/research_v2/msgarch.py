"""Parallel-recursion Gaussian Markov-switching GARCH benchmark.

Each state variance uses the observed lagged return, not a latent-path variance.
This explicit specification avoids claiming the intractable path-dependent model.
"""
import itertools
import json
import time
import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.signal import lfilter
from scipy.special import softmax
from hmmlearn import _hmmc
from src.utils.config import ROOT
from src.research_v2.provenance import guard,model_inputs


def parameters(theta,k):
    mean=theta[:k];omega=np.exp(theta[k:2*k])
    weights=softmax(np.column_stack([theta[2*k:3*k],theta[3*k:4*k],np.zeros(k)]),axis=1)
    alpha,beta=.999*weights[:,0],.999*weights[:,1]
    logits=np.column_stack([theta[4*k:].reshape(k,k-1),np.zeros(k)])
    return mean,omega,alpha,beta,softmax(logits,axis=1)


def evaluate(y,mean,omega,alpha,beta,p):
    y=np.asarray(y,dtype=float);k=len(mean)
    if (omega<=0).any() or (alpha<0).any() or (beta<0).any() or (alpha+beta>=1).any():raise ValueError('Invalid variance parameters')
    h=np.empty((len(y),k));h[0]=omega/(1-alpha-beta)
    for j in range(k):
        h[1:,j]=lfilter([1.],[1.,-beta[j]],omega[j]+alpha[j]*y[:-1]**2,zi=[beta[j]*h[0,j]])[0]
    b=-.5*(np.log(2*np.pi*h)+(y[:,None]-mean)**2/h)
    offset=b.max(1);emission=np.exp(b-offset[:,None])
    _,posterior,scales=_hmmc.forward_scaling(np.full(k,1/k),p,emission)
    return posterior,-np.log(scales)+offset,h


def fit(y,k,seed):
    rng=np.random.default_rng(seed)
    means=np.quantile(y,np.linspace(.2,.8,k))+rng.normal(0,.05,k)
    omega=np.full(k,max(y.var()*.05,1e-4))
    # alpha~.05, beta~.9; remaining mass~.05.
    logits=np.zeros((k,k));np.fill_diagonal(logits,2.5)
    theta=np.r_[means,np.log(omega),np.zeros(k),np.full(k,np.log(18.)),(logits[:,:-1]-logits[:,-1:]).ravel()]
    def objective(t):
        try:
            scores=evaluate(y,*parameters(t,k))[1]
            return -scores.mean() if np.isfinite(scores).all() else 1e20
        except (ValueError,FloatingPointError):return 1e20
    bounds=[(-30,30)]*k+[(-15,10)]*k+[(-15,15)]*(2*k)+[(-20,20)]*(k*(k-1))
    return minimize(objective,theta,method='L-BFGS-B',bounds=bounds,options={'maxiter':500,'ftol':1e-9})


def run():
    guard('m4_msgarch',model_inputs()+['src/research_v2/msgarch.py','reports/v2_benchmark_specification.md'])
    out=ROOT/'outputs/research_v2/m4_msgarch';out.mkdir(parents=True,exist_ok=True)
    registry=[{'asset':a,'K':k,'seed':s,'id':f'{a}_k{k}_s{s}'} for a,k,s in itertools.product(['BTC','ETH'],[2,3,4],range(5))]
    (out/'registry.json').write_text(json.dumps(registry,indent=2));rows=[]
    for spec in registry:
        dest=out/f"{spec['id']}.json"
        if dest.exists():rows.append(json.loads(dest.read_text()));continue
        tick=time.monotonic();row={**spec,'eligible':False}
        frame=pd.read_parquet(ROOT/f"outputs/research_v2/m1/features_{spec['asset'].lower()}.parquet")
        frame=frame.loc[frame.split.ne('test')];train=frame.split.eq('train').to_numpy();y=frame.log_return.to_numpy()*100
        try:
            fitted=fit(y[train],spec['K'],spec['seed']);params=parameters(fitted.x,spec['K'])
            posterior,score,h=evaluate(y,*params)
            row.update(eligible=bool(fitted.success),message=str(fitted.message),iterations=fitted.nit,
                       gradient_norm=float(np.linalg.norm(fitted.jac)),train_objective=float(fitted.fun),
                       validation_log_score=float(score[~train].mean()),minimum_variance=float(h.min()),
                       alpha_plus_beta=(params[2]+params[3]).tolist(),feature_space='100 * daily log return')
            joblib.dump({'theta':fitted.x,'K':spec['K'],'specification':'parallel_observed_lag_return_recursion'},out/f"{spec['id']}.joblib")
            p=frame[['asset','date_utc','split']].copy();p['state_id']=posterior.argmax(1)
            for j in range(spec['K']):p[f'prob_state_{j}']=posterior[:,j]
            p.to_csv(out/f"{spec['id']}_development.csv",index=False)
        except (ValueError,FloatingPointError) as exc:row['reason']=str(exc)
        row['runtime_seconds']=time.monotonic()-tick;dest.write_text(json.dumps(row,indent=2));rows.append(row)
        print(json.dumps(row),flush=True)
    pd.DataFrame(rows).to_csv(out/'development_results.csv',index=False)


if __name__=='__main__':run()
