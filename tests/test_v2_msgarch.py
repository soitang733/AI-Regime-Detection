import numpy as np
from src.research_v2.msgarch import evaluate
from src.models.inference import forward_filter,emission_log_density


def test_single_state_garch_reference_recursion():
    y=np.array([1.,-2.,.5,3.]);p=np.ones((1,1));a=np.array([.1]);b=np.array([.8]);o=np.array([.2]);m=np.array([.1])
    posterior,s,h=evaluate(y,m,o,a,b,p)
    variance=[2.]
    for value in y[:-1]:variance.append(.2+.1*value**2+.8*variance[-1])
    np.testing.assert_allclose(h[:,0],variance,atol=1e-12)
    np.testing.assert_allclose(s,-.5*(np.log(2*np.pi*np.array(variance))+(y-.1)**2/variance),atol=1e-12)
    assert np.all(posterior==1)


def test_constant_variance_matches_hmm_and_prefix():
    y=np.random.default_rng(0).normal(size=100);m=np.array([-1.,1.]);o=np.array([.5,1.5]);zero=np.zeros(2);p=np.array([[.9,.1],[.2,.8]])
    a,s,h=evaluate(y,m,o,zero,zero,p)
    b,t=forward_filter(emission_log_density(y[:,None],m[:,None],o[:,None]),np.array([.5,.5]),p)
    np.testing.assert_allclose(a,b,atol=1e-10,rtol=0);np.testing.assert_allclose(s,t,atol=1e-10,rtol=0)
    np.testing.assert_allclose(evaluate(y[:50],m,o,zero,zero,p)[0],a[:50],atol=1e-10,rtol=0)
