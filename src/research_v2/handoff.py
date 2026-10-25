"""Explicit research-only C2-to-C3 handoff; no silent unstable bypass."""
import hashlib
import json
import warnings
import numpy as np
import pandas as pd
from src.utils.config import ROOT


class UnstableResearchWarning(UserWarning):
    pass


def load_hmm(asset,require_stable=True,acknowledge_unstable=False,root=ROOT):
    if asset not in ['BTC','ETH']:raise ValueError('Unknown asset')
    path=root/'outputs/research_v2/m2'
    manifest=json.loads((path/'manifest.json').read_text())
    if manifest['status']!='complete':raise ValueError('Incomplete V2 export')
    for name in [f'{asset.lower()}_metadata.json',f'{asset.lower()}_filtered.csv',f'{asset.lower()}.joblib']:
        if hashlib.sha256((path/name).read_bytes()).hexdigest()!=manifest['files_sha256'][name]:raise ValueError(f'Artifact hash mismatch: {name}')
    metadata=json.loads((path/f'{asset.lower()}_metadata.json').read_text())
    stable=metadata['stability']['stable']
    if not stable:
        if require_stable:raise ValueError('Unstable model rejected by require_stable=True')
        if not acknowledge_unstable:raise ValueError('Explicit acknowledge_unstable=True required for research')
        warnings.warn('Unstable V2 model: historical exploratory research only',UnstableResearchWarning,stacklevel=2)
    frame=pd.read_csv(path/f'{asset.lower()}_filtered.csv')
    k=int(metadata['K']);columns=[f'prob_state_{i}' for i in range(k)]
    if not frame.probability_type.eq('filtered').all():raise ValueError('Smoothed probabilities prohibited')
    if not frame.K.eq(k).all() or not frame.model_run_id.eq(metadata['candidate_id']).all():raise ValueError('Model ID/K mismatch')
    p=frame[columns].to_numpy();q=frame[[f'prob_next_state_{i}' for i in range(k)]].to_numpy()
    for a in [p,q]:
        if not np.isfinite(a).all() or (a< -1e-10).any() or (a>1+1e-10).any() or abs(a.sum(1)-1).max()>1e-8:raise ValueError('Invalid probability vectors')
    if not np.array_equal(frame.state_id.to_numpy(),p.argmax(1)):raise ValueError('State ID is not filtered argmax')
    if not np.allclose(p@np.array(metadata['transition_matrix']),q,atol=1e-10,rtol=0):raise ValueError('T+1 formula mismatch')
    date=pd.to_datetime(frame.date_utc,utc=True,errors='raise');available=pd.to_datetime(frame.as_of_utc,utc=True,errors='raise')
    if date.isna().any() or available.isna().any() or date.duplicated().any() or not date.is_monotonic_increasing or (available<date+pd.Timedelta(days=1)).any():raise ValueError('Invalid signal time')
    mapping={int(i):v for i,v in metadata['label_map'].items()}
    if set(mapping)!=set(range(k)) or not frame.state_id.isin(mapping).all() or not frame.label.eq(frame.state_id.map(mapping)).all():raise ValueError('State mapping mismatch')
    if not np.allclose(frame.prob_high_risk,p[:,metadata['high_risk_state']],atol=1e-10,rtol=0):raise ValueError('Risk state mismatch')
    return frame,metadata
