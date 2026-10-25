"""Gaussian non-homogeneous HMM with covariates known at the origin time.

P[t,i,j] = P(S[t+1]=j | S[t]=i, z[t]); last destination is reference.
Generalized EM estimates emissions and weighted multinomial transitions jointly.
The objective is mean negative observed log likelihood + L2 mean slope squared.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax
from sklearn.cluster import KMeans
from numba import njit

from src.models.inference import emission_log_density


@njit(cache=True)
def _forward(emission, transition, initial, starts):
    n,k=emission.shape
    alpha=np.empty_like(emission);scale=np.empty(n)
    for t in range(n):
        total=0.
        for j in range(k):
            prior=initial[j] if starts[t] else 0.
            if not starts[t]:
                for i in range(k):prior+=alpha[t-1,i]*transition[t-1,i,j]
            alpha[t,j]=prior*emission[t,j];total+=alpha[t,j]
        if not np.isfinite(total) or total<=0:raise ValueError('Zero predictive density')
        scale[t]=total
        for j in range(k):alpha[t,j]/=total
    return alpha,scale


@njit(cache=True)
def _backward(emission,transition,scale,starts):
    n,k=emission.shape;beta=np.ones_like(emission)
    for t in range(n-2,-1,-1):
        if not starts[t+1]:
            for i in range(k):
                value=0.
                for j in range(k):value+=transition[t,i,j]*emission[t+1,j]*beta[t+1,j]
                beta[t,i]=value/scale[t+1]
    return beta


def transition_loss_gradient(flat, design, xi, k, penalty, n_observations):
    coefficients=flat.reshape(k,k-1,design.shape[1])
    logits=np.zeros((len(design),k,k))
    logits[:,:,:-1]=np.einsum('tp,ijp->tij',design,coefficients)
    logp=logits-logsumexp(logits,axis=2,keepdims=True)
    probability=np.exp(logp)
    loss=-float((xi*logp).sum())/n_observations
    error=probability*xi.sum(axis=2,keepdims=True)-xi
    gradient=np.einsum('tij,tp->ijp',error[:,:,:-1],design)/n_observations
    slopes=coefficients[:,:,1:]
    if slopes.size:
        loss+=penalty*float(np.mean(slopes**2))
        gradient[:,:,1:]+=2*penalty*slopes/slopes.size
    return loss,gradient.ravel()


class GaussianNHHMM:
    def __init__(self,k=2,penalty=0.,seed=0,max_iter=1000,tol=1e-6):
        self.k=k;self.penalty=penalty;self.seed=seed;self.max_iter=max_iter;self.tol=tol

    def transitions(self,z):
        z=np.asarray(z,dtype=float)
        if z.ndim!=2 or not np.isfinite(z).all() or z.shape[1]+1!=self.coefficients_.shape[2]:
            raise ValueError('Invalid transition covariates')
        design=np.column_stack([np.ones(len(z)),z])
        logits=np.zeros((len(z),self.k,self.k))
        logits[:,:,:-1]=np.einsum('tp,ijp->tij',design,self.coefficients_)
        return softmax(logits,axis=2)

    def infer(self,x,z,starts=None,smooth=False):
        x,z=np.asarray(x,dtype=float),np.asarray(z,dtype=float)
        if not len(x) or len(x)!=len(z): raise ValueError('Empty or unequal observation/covariate lengths')
        starts=np.zeros(len(x),dtype=bool) if starts is None else np.asarray(starts,dtype=bool).copy()
        if starts.shape!=(len(x),): raise ValueError('Invalid segment boundaries')
        starts[0]=True
        p=self.transitions(z)
        b=emission_log_density(x,self.means_,self.variances_)
        offset=b.max(axis=1); e=np.exp(b-offset[:,None])
        alpha,scale=_forward(e,p,self.startprob_,starts)
        scores=np.log(scale)+offset
        if not smooth: return alpha,scores
        beta=_backward(e,p,scale,starts)
        gamma=alpha*beta;gamma/=gamma.sum(1,keepdims=True)
        xi=alpha[:-1,:,None]*p[:-1]*(e[1:]*beta[1:])[:,None,:]
        sums=xi.sum(axis=(1,2),keepdims=True)
        xi=np.divide(xi,sums,out=np.zeros_like(xi),where=sums>0)
        xi[starts[1:]]=0
        return alpha,scores,gamma,xi

    def fit(self,x,z,starts=None):
        x,z=np.asarray(x,dtype=float),np.asarray(z,dtype=float)
        if x.ndim!=2 or z.ndim!=2 or len(x)!=len(z) or not np.isfinite(x).all() or not np.isfinite(z).all():
            raise ValueError('Invalid training observations')
        if self.penalty<0: raise ValueError('Negative regularization')
        starts=np.zeros(len(x),dtype=bool) if starts is None else np.asarray(starts,dtype=bool).copy()
        starts[0]=True
        labels=KMeans(n_clusters=self.k,n_init=10,random_state=self.seed).fit_predict(x)
        self.means_=np.array([x[labels==k].mean(0) for k in range(self.k)])
        self.variances_=np.maximum(np.array([x[labels==k].var(0) for k in range(self.k)]),1e-6)
        self.startprob_=np.full(self.k,1/self.k)
        p=np.full((self.k,self.k),.05/(self.k-1));np.fill_diagonal(p,.95)
        self.coefficients_=np.zeros((self.k,self.k-1,z.shape[1]+1))
        self.coefficients_[:,:,0]=np.log(p[:,:-1]/p[:,-1:])
        self.coefficients_[:,:,1:]=np.random.default_rng(self.seed).normal(0,.01,(self.k,self.k-1,z.shape[1]))
        design=np.column_stack([np.ones(len(z)-1),z[:-1]])
        self.history_=[]; consecutive=0; self.converged_=False
        for iteration in range(self.max_iter):
            _,scores,gamma,xi=self.infer(x,z,starts,smooth=True)
            slopes=self.coefficients_[:,:,1:]
            objective=-scores.mean()+self.penalty*np.mean(slopes**2) if slopes.size else -scores.mean()
            self.history_.append(float(objective))
            if len(self.history_)>1:
                improvement=self.history_[-2]-objective
                if improvement < -1e-7: raise ValueError('Penalized objective increased')
                relative=abs(improvement)/max(1,abs(self.history_[-2]))
                consecutive=consecutive+1 if relative<=self.tol else 0
                if consecutive>=5:
                    self.converged_=True;break
            mass=gamma.sum(0)
            if (mass<1e-8).any(): raise ValueError('Degenerate posterior state mass')
            self.means_=gamma.T@x/mass[:,None]
            self.variances_=np.maximum(np.einsum('tk,tkd->kd',gamma,(x[:,None]-self.means_)**2)/mass[:,None],1e-6)
            self.startprob_=np.maximum(gamma[starts].mean(0),1e-12);self.startprob_/=self.startprob_.sum()
            result=minimize(transition_loss_gradient,self.coefficients_.ravel(),
                            args=(design,xi,self.k,self.penalty,len(x)),jac=True,method='L-BFGS-B',
                            options={'maxiter':1000,'ftol':1e-12,'gtol':1e-7})
            if not np.isfinite(result.fun): raise ValueError('Nonfinite transition objective')
            self.coefficients_=result.x.reshape(self.coefficients_.shape)
            self.transition_gradient_norm_=float(np.linalg.norm(result.jac))
            self.transition_optimizer_success_=bool(result.success)
        self.n_iter_=iteration+1
        _,scores,_,xi=self.infer(x,z,starts,smooth=True)
        self.expected_transition_counts_=xi.sum(0)
        self.train_log_likelihood_=float(scores.sum())
        return self
