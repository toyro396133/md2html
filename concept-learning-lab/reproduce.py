"""Standalone reproduction for Recursive Concepts V4 (384 synthetic objects).
Run: pip install numpy torch && python reproduce.py
Predefined ontology and feature-composition *architecture*; features are learned.
"""
import json
import numpy as np
import torch
from torch import nn

N_MATERIALS, N_FORMS = 16, 24
RELATIONS = ["matter_form","general_particular","whole_part","cause_effect","subject_predicate"]

def dataset(seed=20261027):
    rng=np.random.default_rng(seed)
    m=rng.uniform(.06,.94,(16,4)).astype(np.float32)
    f=rng.uniform(.06,.94,(24,4)).astype(np.float32)
    m[:,0]=rng.permutation(np.linspace(.07,.93,16,dtype=np.float32))
    f[:,0]=rng.permutation(np.linspace(.07,.93,24,dtype=np.float32))
    mc=m-.5; fc=f-.5
    z1=4*mc[:,None,0]*fc[None,:,0]
    z2=4*mc[:,None,1]*fc[None,:,1]
    z3=z1*z2
    base=np.array([.41,.46,.51,.44,.47],np.float32)
    lm=np.array([[.09,.02,.04,.06],[.01,.10,.03,.01],[.02,.08,.03,.04],[.03,.03,.10,.04],[.08,.03,.02,.05]],np.float32)
    lf=np.array([[.02,.06,.05,.02],[.04,.04,.06,.03],[.05,.03,.02,.07],[.02,.07,.04,.02],[.03,.03,.05,.06]],np.float32)
    loads=np.array([[.13,-.08,.11,.15,.03],[-.09,.13,.06,-.06,.15],[.15,-.16,.17,.18,.12]],np.float32)
    y=base+(mc@lm.T)[:,None,:]+(fc@lf.T)[None,:,:]
    y=y+z1[:,:,None]*loads[0]+z2[:,:,None]*loads[1]+z3[:,:,None]*loads[2]
    y=y+rng.normal(0,.002,(16,24,5)).astype(np.float32)
    vals, tests = [], []
    for i in range(16):
        vals += [24*i+(5*i+3)%24,24*i+(5*i+4)%24]
        tests += [24*i+(5*i+10)%24,24*i+(5*i+11)%24]
    train=sorted(set(range(384))-set(vals)-set(tests))
    assert len(train)==320 and len(vals)==32 and len(tests)==32
    mm=np.repeat(m,24,axis=0)
    ff=np.tile(f,(16,1))
    return (torch.from_numpy(mm),torch.from_numpy(ff),torch.from_numpy(y.reshape(-1,5)),
            train,vals,tests,z3.flatten())

class Additive(nn.Module):
    def __init__(self):
        super().__init__();self.linear=nn.Linear(8,5)
    def forward(self,m,f):
        return self.linear(torch.cat([m,f],dim=-1)-.5)

class Features(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear=nn.Linear(8,5)
        self.mat_proj=nn.Parameter(torch.randn(2,4)*.25)
        self.form_proj=nn.Parameter(torch.randn(2,4)*.25)
        self.loading=nn.Parameter(torch.randn(2,5)*.07)
    def features(self,m,f):
        return ((m-.5)@self.mat_proj.T)*((f-.5)@self.form_proj.T)
    def forward(self,m,f):
        return self.linear(torch.cat([m,f],dim=-1)-.5)+self.features(m,f)@self.loading

class Nested(Features):
    def __init__(self):
        super().__init__();self.nested_loading=nn.Parameter(torch.randn(5)*.05)
    def forward(self,m,f):
        z=self.features(m,f)
        return super().forward(m,f)+(z[:,0]*z[:,1])[:,None]*self.nested_loading

class EqualLinear(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear=nn.Linear(8,5)
        self.more=nn.Linear(8,2,bias=False)
        self.read=nn.Parameter(torch.randn(2,5)*.06)
        self.bias=nn.Parameter(torch.zeros(5))
    def forward(self,m,f):
        x=torch.cat([m,f],dim=-1)-.5
        return self.linear(x)+self.more(x)@self.read+self.bias

def fit(model,m,f,y,tr,steps,lr=.025):
    ids=torch.tensor(tr)
    opt=torch.optim.Adam(model.parameters(),lr=lr)
    for _ in range(steps):
        opt.zero_grad()
        loss=(model(m[ids],f[ids])-y[ids]).square().mean()
        loss.backward();opt.step()
    return model

@torch.no_grad()
def mse(model,m,f,y,ids):
    idx=torch.tensor(ids)
    return float((model(m[idx],f[idx])-y[idx]).square().mean())

def run(seeds=(7,19,31),epochs=600):
    torch.set_num_threads(1)
    m,f,y,tr,va,te,truth=dataset()
    trials=[]
    for seed in seeds:
        torch.manual_seed(seed)
        base=fit(Additive(),m,f,y,tr,epochs)
        torch.manual_seed(seed+100)
        pair=Features()
        pair.linear.load_state_dict(base.linear.state_dict())
        pair=fit(pair,m,f,y,tr,2*epochs)
        improvement=mse(base,m,f,y,va)-mse(pair,m,f,y,va)
        grow=(improvement>0.0001 and mse(pair,m,f,y,va)>.00005)
        torch.manual_seed(seed+200)
        nested=Nested()
        nested.linear.load_state_dict(pair.linear.state_dict())
        with torch.no_grad():
            nested.mat_proj.copy_(pair.mat_proj)
            nested.form_proj.copy_(pair.form_proj)
            nested.loading.copy_(pair.loading)
        nested=fit(nested,m,f,y,tr,3*epochs if grow else epochs)
        torch.manual_seed(seed+300)
        match=fit(EqualLinear(),m,f,y,tr,3*epochs)
        with torch.no_grad():
            ix=torch.tensor(te)
            z=nested.features(m[ix],f[ix])
            prediction=nested(m[ix],f[ix])
            without=prediction-(z[:,0]*z[:,1])[:,None]*nested.nested_loading
            ablation=float((without-y[ix]).square().mean())
        trials.append({
           "seed":seed,"grew":bool(grow),
           "test_mse_additive":mse(base,m,f,y,te),
           "test_mse_equal_parameters":mse(match,m,f,y,te),
           "test_mse_two_features":mse(pair,m,f,y,te),
           "test_mse_nested":mse(nested,m,f,y,te),
           "test_mse_without_nested_unit":ablation,
           "parameters":[sum(p.numel() for p in mod.parameters()) for mod in (base,match,pair,nested)]
        })
    print(json.dumps({"count":384,"train":320,"validation":32,"test":32,"relations":RELATIONS,"trials":trials},indent=2))

if __name__=="__main__":
    run()
