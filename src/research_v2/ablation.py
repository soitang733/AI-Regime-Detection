import itertools
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import adjusted_rand_score
from src.research.robustness import initialized_hmm
from src.models.inference import infer,sequence_lengths
from src.research_v2.hmm import SETTINGS
from src.research_v2.provenance import guard,model_inputs
from src.utils.config import ROOT


def run():
    out=ROOT/'outputs/research_v2/m2_ablation';out.mkdir(parents=True,exist_ok=True)
    guard('m2_ablation',model_inputs()+['reports/v2_volume_ablation_specification.md','src/research_v2/ablation.py'])
    registry=[{'asset':a,'K':k,'seed':s,'initializer':init,'id':f'{a}_{k}_{s}_{init}'} for a,k,s,init in itertools.product(['BTC','ETH'],[2,3,4],range(5),['kmeans','volatility_quantiles'])]
    (out/'registry.json').write_text(json.dumps(registry,indent=2));rows=[];labels={}
    for spec in registry:
        path=out/f"{spec['id']}.json"
        if path.exists():
            row=json.loads(path.read_text());rows.append(row)
            if row['eligible']:labels[spec['id']]=np.load(out/f"{spec['id']}.npy")
            continue
        frame=pd.read_parquet(ROOT/f"outputs/research_v2/m1/features_{spec['asset'].lower()}.parquet")
        frame=frame.loc[frame.split.ne('test')];mask=frame.split.eq('train').to_numpy();cols=['log_return','rv21']
        scaler=StandardScaler().fit(frame.loc[mask,cols]);x=scaler.transform(frame[cols]);row={**spec,'eligible':False,'feature_space':'2D; likelihood not comparable to3D'}
        try:
            model=initialized_hmm(x[mask],spec['K'],spec['seed'],spec['initializer'],SETTINGS)
            model.fit(x[mask],lengths=sequence_lengths(frame.loc[mask]))
            a,s=infer(model,x,frame);shares=np.bincount(a[mask].argmax(1),minlength=spec['K'])/mask.sum()
            history=list(model.monitor_.history);gain=history[-1]-history[-2]
            row.update(last_gain=gain,min_train_share=float(shares.min()),eligible=bool(-1e-6<=gain<=.001 and shares.min()>=.02),validation_log_score=float(s[~mask].mean()))
            if row['eligible']:
                lab=a[~mask].argmax(1);labels[spec['id']]=lab;np.save(out/f"{spec['id']}.npy",lab)
                row['validation_persistence']=float((lab[1:]==lab[:-1]).mean())
        except (ValueError,FloatingPointError) as exc:row['reason']=str(exc)
        path.write_text(json.dumps(row,indent=2));rows.append(row)
        print(spec['id'],row['eligible'],flush=True)
    results=pd.DataFrame(rows);results.to_csv(out/'results.csv',index=False);stability=[]
    for (asset,k),group in results.loc[results.eligible].groupby(['asset','K']):
        scores=[adjusted_rand_score(labels[a],labels[b]) for a,b in itertools.combinations(group.id,2)]
        stability.append({'asset':asset,'K':k,'valid_fits':len(group),'median_ari':np.median(scores) if scores else np.nan,'min_ari':np.min(scores) if scores else np.nan})
    pd.DataFrame(stability).to_csv(out/'stability.csv',index=False)


if __name__=='__main__':run()
