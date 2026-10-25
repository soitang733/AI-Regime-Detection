"""Locked 20-seed NHHMM recovery gate; no real-data fitting before it passes."""
import hashlib
import json
import time
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from src.research_v2.nhhmm import GaussianNHHMM
from src.models.inference import forward_filter,emission_log_density
from src.utils.config import ROOT
from src.research_v2.provenance import guard


def run():
    guard('m3_simulation',['src/research_v2/nhhmm.py','src/research_v2/simulation.py','reports/m0_lock/PROTOCOL_V2_M0.md'])
    out=ROOT/'outputs/research_v2/m3_simulation';out.mkdir(parents=True,exist_ok=True)
    current_source_hash=hashlib.sha256((ROOT/'src/research_v2/nhhmm.py').read_bytes()).hexdigest()
    if (out/'manifest.json').exists() and json.loads((out/'manifest.json').read_text())['source_sha256']!=current_source_hash:
        raise ValueError('Numerical implementation changed; cached simulations cannot certify new code')
    spec={'seeds':list(range(20)),'n':2000,'K':2,'p':1,'means':[-2.,2.],'variances':[.7,1.2],
          'coefficients':[[[2.,.8]],[[-1.7,-.6]]],'penalty':0.,'max_iterations':1000,
          'relative_tolerance':1e-6,'consecutive_iterations':5,'minimum_converged':18}
    (out/'specification.json').write_text(json.dumps(spec,indent=2))
    rows=[]
    for seed in spec['seeds']:
        path=out/f'seed_{seed}.json'
        if path.exists(): rows.append(json.loads(path.read_text()));continue
        tick=time.monotonic();rng=np.random.default_rng(seed)
        truth=GaussianNHHMM(2);truth.means_=np.array(spec['means'])[:,None];truth.variances_=np.array(spec['variances'])[:,None]
        truth.coefficients_=np.array(spec['coefficients']);truth.startprob_=np.array([.5,.5])
        z=rng.normal(size=(2000,1));p=truth.transitions(z)
        state=np.zeros(2000,dtype=int);state[0]=rng.choice(2,p=truth.startprob_)
        for t in range(1,2000):state[t]=rng.choice(2,p=p[t-1,state[t-1]])
        x=rng.normal(truth.means_[state],np.sqrt(truth.variances_[state]))
        row={'seed':seed,'converged':False}
        try:
            model=GaussianNHHMM(2,seed=seed).fit(x,z)
            _,order=linear_sum_assignment(abs(truth.means_-model.means_.T))
            aligned=model.transitions(z)[:,order][:,:,order]
            # Reference logits after destination permutation, not raw beta comparison.
            probe=np.array([[0.],[1.]])
            ap=model.transitions(probe)[:,order][:,:,order]
            logits=np.log(ap[:,:,:-1]/ap[:,:,-1:])
            coef=np.stack([logits[0],logits[1]-logits[0]],axis=-1)
            errors=coef-truth.coefficients_
            zero=GaussianNHHMM(2);zero.means_=truth.means_;zero.variances_=truth.variances_;zero.startprob_=truth.startprob_;zero.coefficients_=truth.coefficients_.copy();zero.coefficients_[:,:,1:]=0
            a,_=zero.infer(x,z)
            b,_=forward_filter(emission_log_density(x,zero.means_,zero.variances_),zero.startprob_,zero.transitions(z)[0])
            error=float(abs(a-b).max())
            row.update(converged=bool(model.converged_),iterations=model.n_iter_,
                       objective=model.history_[-1],transition_gradient_norm=model.transition_gradient_norm_,
                       transition_optimizer_success=model.transition_optimizer_success_,
                       beta_zero_max_error=error,coefficient_errors=errors.tolist(),
                       coefficient_rmse=float(np.sqrt(np.mean(errors**2))),
                       transition_probability_rmse=float(np.sqrt(np.mean((aligned-p)**2))))
        except (ValueError,FloatingPointError) as exc:row['failure_reason']=str(exc)
        row['runtime_seconds']=time.monotonic()-tick
        path.write_text(json.dumps(row,indent=2));rows.append(row)
        print(json.dumps(row),flush=True)
    valid=[r for r in rows if r['converged'] and r.get('beta_zero_max_error',1)<=1e-8]
    errors=np.array([r['coefficient_errors'] for r in valid])
    summary={'created_at_utc':datetime.now(timezone.utc).isoformat(),'completed':len(rows),'converged':len(valid),
             'gate_passed':len(valid)>=18,'mean_coefficient_error':errors.mean(0).tolist() if len(errors) else None,
             'coefficient_rmse':float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
             'source_sha256':hashlib.sha256((ROOT/'src/research_v2/nhhmm.py').read_bytes()).hexdigest(),
             'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='manifest.json'},
             'scope':'simulation gate only; not evidence of real-data performance'}
    pd.DataFrame(rows).to_csv(out/'results.csv',index=False)
    (out/'manifest.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)


if __name__=='__main__': run()
