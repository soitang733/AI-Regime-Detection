import itertools
import joblib
import numpy as np
from scipy.optimize import check_grad
from src.models.inference import emission_log_density, forward_filter
from src.research_v2.nhhmm import GaussianNHHMM,transition_loss_gradient


def fixed_model():
    m=GaussianNHHMM(2)
    m.means_=np.array([[-1.],[1.]])
    m.variances_=np.array([[.7],[1.2]])
    m.startprob_=np.array([.4,.6])
    m.coefficients_=np.array([[[1.5,.8]],[[-1.,-.4]]])
    return m


def test_exact_enumeration_and_causal_forecast():
    m=fixed_model();x=np.array([[-.5],[.7],[1.2]]);z=np.array([[.3],[-.9],[.6]])
    alpha,ll,gamma,xi=m.infer(x,z,smooth=True)
    p=m.transitions(z);e=np.exp(emission_log_density(x,m.means_,m.variances_))
    masses={path:m.startprob_[path[0]]*e[0,path[0]]*p[0,path[0],path[1]]*e[1,path[1]]*p[1,path[1],path[2]]*e[2,path[2]] for path in itertools.product(range(2),repeat=3)}
    total=sum(masses.values());assert np.isclose(ll.sum(),np.log(total))
    for t in range(3):
        for k in range(2): assert np.isclose(gamma[t,k],sum(v for s,v in masses.items() if s[t]==k)/total)
    for i,j in itertools.product(range(2),repeat=2):
        assert np.isclose(xi[0,i,j],sum(v for s,v in masses.items() if s[:2]==(i,j))/total)
    prefix,_=m.infer(x[:2],z[:2]);np.testing.assert_allclose(prefix,alpha[:2],atol=1e-10,rtol=0)
    z2=z.copy();z2[-1]=100
    np.testing.assert_allclose(m.infer(x,z2)[0],alpha,atol=1e-10,rtol=0)
    assert not np.allclose(alpha[-1]@m.transitions(z2)[-1],alpha[-1]@p[-1])


def test_beta_zero_and_segment_reset(tmp_path):
    m=fixed_model();m.coefficients_[:,:,1:]=0
    x=np.random.default_rng(1).normal(size=(30,1));z=np.zeros_like(x)
    starts=np.zeros(30,dtype=bool);starts[[0,15]]=True
    actual=m.infer(x,z,starts)[0]
    expected=forward_filter(emission_log_density(x,m.means_,m.variances_),m.startprob_,m.transitions(z)[0],starts)[0]
    np.testing.assert_allclose(actual,expected,atol=1e-10,rtol=0)
    joblib.dump(m,tmp_path/'model.joblib')
    np.testing.assert_allclose(joblib.load(tmp_path/'model.joblib').infer(x,z,starts)[0],actual,atol=1e-10,rtol=0)


def test_transition_objective_analytic_gradient():
    rng=np.random.default_rng(7);d=np.column_stack([np.ones(12),rng.normal(size=(12,2))]);xi=rng.uniform(size=(12,3,3));xi/=xi.sum((1,2),keepdims=True)
    theta=rng.normal(size=3*2*3)
    f=lambda v:transition_loss_gradient(v,d,xi,3,1.,13)
    assert check_grad(lambda v:f(v)[0],lambda v:f(v)[1],theta)<1e-6
