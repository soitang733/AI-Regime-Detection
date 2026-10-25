"""Conditional train profiles and block sensitivity; not independent discovery tests."""
import itertools
import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests
from src.research_v2.handoff import load_hmm
from src.research.economics import economic_evidence,moving_blocks
from src.utils.config import ROOT
import yaml


def run():
    out=ROOT/'outputs/research_v2/m2_profiles';out.mkdir(parents=True,exist_ok=True)
    settings=yaml.safe_load((ROOT/'config/research.yaml').read_text())['economics']
    rows=[];contrasts=[];occupancy=[];sensitivity=[]
    for asset in ['BTC','ETH']:
        signals,meta=load_hmm(asset,False,True)
        features=pd.read_parquet(ROOT/f'outputs/research_v2/m1/features_{asset.lower()}.parquet')
        f=features.merge(signals.drop(columns=['split','asset','segment_id']),on='date_utc',validate='one_to_one')
        train=f.loc[f.split.eq('train')].reset_index(drop=True)
        prob=train[[f'prob_state_{i}' for i in range(meta['K'])]].to_numpy()
        for block in [14,21,42]:
            rules={**settings,'block_days':block}
            e=economic_evidence(train,prob,meta['label_map'],rules,20261024)
            sensitivity.append(e.assign(asset=asset,block_days=block))
        ix=moving_blocks(len(train),1000,21,20261024)
        for feature in ['log_return','rv21','log_dollar_volume','amihud_illiq']:
            values=train[feature].to_numpy();valid=np.isfinite(values)
            w=prob*valid[:,None];v=np.nan_to_num(values)
            mean=w.T@v/w.sum(0)
            boot=[]
            for chunk in np.array_split(ix,10):
                wb=w[chunk];vb=v[chunk]
                boot.append((wb*vb[:,:,None]).sum(1)/wb.sum(1))
            boot=np.concatenate(boot)
            for k in range(meta['K']):
                lo,hi=np.quantile(boot[:,k],[.025,.975])
                rows.append({'asset':asset,'state_id':k,'feature':feature,'weighted_mean':mean[k],'ci_low':lo,'ci_high':hi,
                             'train_hard_days':int(train.state_id.eq(k).sum()),'scope':'conditional on fixed fitted model; train descriptive'})
            for i,j in itertools.combinations(range(meta['K']),2):
                delta=boot[:,i]-boot[:,j];point=mean[i]-mean[j];centered=delta-point
                contrasts.append({'asset':asset,'feature':feature,'state_i':i,'state_j':j,'mean_difference':point,
                                  'ci_low':np.quantile(delta,.025),'ci_high':np.quantile(delta,.975),
                                  'bootstrap_p':(1+(abs(centered)>=abs(point)).sum())/(len(delta)+1),
                                  'scope':'conditional train contrast; same data fitted states; not independent significance'})
        f['year']=pd.to_datetime(f.date_utc).dt.year
        for (split,year),g in f.groupby(['split','year']):
            for k in range(meta['K']):occupancy.append({'asset':asset,'split':split,'year':year,'state_id':k,'days':int(g.state_id.eq(k).sum()),'share':float(g.state_id.eq(k).mean())})
    contrasts=pd.DataFrame(contrasts)
    for asset,g in contrasts.groupby('asset'):
        contrasts.loc[g.index,'holm_adjusted_p']=multipletests(g.bootstrap_p,method='holm')[1]
    pd.DataFrame(rows).to_csv(out/'profiles.csv',index=False)
    contrasts.to_csv(out/'contrasts.csv',index=False)
    pd.concat(sensitivity).to_csv(out/'label_block_sensitivity.csv',index=False)
    pd.DataFrame(occupancy).to_csv(out/'occupancy_by_year.csv',index=False)


if __name__=='__main__':run()
