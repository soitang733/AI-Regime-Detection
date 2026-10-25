import numpy as np
import pandas as pd
from src.research_v2.nhhmm_run import prepare


def test_covariate_transform_is_train_only():
    rng=np.random.default_rng(3);n=1200
    frame=pd.DataFrame({'date_utc':pd.date_range('2018-01-01',periods=n).strftime('%Y-%m-%d'),
        'split':['train']*800+['validation']*200+['test']*200,
        'log_return':rng.normal(size=n),'rv21':rng.uniform(.01,.1,n),
        'log_dollar_volume':rng.normal(size=n),'vix':rng.normal(20,2,n)})
    frame.loc[5:20,'vix']=np.nan
    _,x,z,pre=prepare(frame,['vix'])
    future=frame.copy();future.loc[future.split.ne('train'),'vix']=1e10
    _,x2,z2,pre2=prepare(future,['vix'])
    np.testing.assert_array_equal(z[:800],z2[:800])
    assert pre['medians']==pre2['medians']
    np.testing.assert_array_equal(x[:800],x2[:800])
