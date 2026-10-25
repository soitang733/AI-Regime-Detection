import numpy as np
from src.research_v2.benchmarks import page_hinkley,density_adapter,assign_density
from src.research_v2.hmm import select_candidate,stability
from src.research_v2.benchmarks import ms_model


def test_change_point_prefix_and_known_shift():
    x=np.r_[np.zeros(100),np.full(100,4.)]
    states,alarms=page_hinkley(x)
    np.testing.assert_array_equal(page_hinkley(x[:110])[0],states[:110])
    assert not alarms[:100].any() and alarms[100:110].any()


def test_density_noise_and_frozen_assignment():
    x=np.array([[0.,0.],[.1,0.],[0.,.1],[5.,5.],[5.1,5.],[5.,5.1]])
    adapter=density_adapter(x,np.array([0,0,0,1,1,1]))
    z=np.array([[0.,0.],[5.,5.],[100.,100.]])
    np.testing.assert_array_equal(assign_density(z,adapter),[0,1,-1])
    np.testing.assert_array_equal(assign_density(z[:2],adapter),assign_density(z,adapter)[:2])


def test_k5_never_selected_as_main_and_ll_before_stability():
    rows=[dict(K=k,eligible=True,validation_log_score=ll,BIC=b,seed=0,initializer='kmeans') for k,ll,b in [(2,-2,30),(3,-1,50),(5,10,1)]]
    assert select_candidate(rows)['K']==3


def test_markov_switching_ar_filter_prefix_with_fixed_parameters():
    y=np.random.default_rng(4).normal(size=120)
    for order in [0,1]:
        parameters=ms_model(y[:80],2,order).start_params
        prefix=ms_model(y[:80],2,order).filter(parameters).filtered_marginal_probabilities
        full=ms_model(y,2,order).filter(parameters).filtered_marginal_probabilities
        np.testing.assert_allclose(prefix,np.asarray(full)[:len(prefix)],atol=1e-10,rtol=0)


def test_one_initializer_cannot_claim_pooled_stability(tmp_path):
    rows=[]
    for seed in range(3):
        cid=f'one_{seed}'
        rows.append(dict(asset='BTC',fold=2,rv=21,K=2,initializer='kmeans',seed=seed,eligible=True,candidate_id=cid))
        np.savez(tmp_path/f'{cid}.npz',states=[0,0,1,1],risk=[.1,.1,.9,.9])
    result=stability(rows,tmp_path)
    pooled=result.loc[result.family.eq('pooled')].iloc[0]
    assert pooled.metric_gate_passed and not pooled.stable
    assert pooled.eligible_initializer_families==1
