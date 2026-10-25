import hashlib
import json
import shutil
import pandas as pd
import pytest
from src.utils.config import ROOT
from src.research_v2.handoff import load_hmm,UnstableResearchWarning


def copied(tmp_path):
    source=ROOT/'outputs/research_v2/m2';dest=tmp_path/'outputs/research_v2/m2';dest.mkdir(parents=True)
    for name in ['manifest.json','btc_metadata.json','btc_filtered.csv','btc.joblib']:
        shutil.copy2(source/name,dest/name)
    metadata=json.loads((dest/'btc_metadata.json').read_text());metadata['stability']['stable']=False
    (dest/'btc_metadata.json').write_text(json.dumps(metadata))
    rehash(dest)
    return dest


def rehash(dest):
    manifest=json.loads((dest/'manifest.json').read_text())
    for name in ['btc_metadata.json','btc_filtered.csv']:
        manifest['files_sha256'][name]=hashlib.sha256((dest/name).read_bytes()).hexdigest()
    (dest/'manifest.json').write_text(json.dumps(manifest))


def test_unstable_requires_explicit_research_ack(tmp_path):
    copied(tmp_path)
    with pytest.raises(ValueError,match='require_stable'):load_hmm('BTC',root=tmp_path)
    with pytest.raises(ValueError,match='acknowledge'):load_hmm('BTC',require_stable=False,root=tmp_path)
    with pytest.warns(UnstableResearchWarning):
        frame,metadata=load_hmm('BTC',require_stable=False,acknowledge_unstable=True,root=tmp_path)
    assert frame.K.eq(metadata['K']).all()


@pytest.mark.parametrize('corruption',['smoothed','time','state','hash'])
def test_reject_corrupt_research_handoff(tmp_path,corruption):
    dest=copied(tmp_path);frame=pd.read_csv(dest/'btc_filtered.csv')
    if corruption=='smoothed':frame['probability_type']='smoothed'
    elif corruption=='time':frame.loc[0,'as_of_utc']='2010-01-01'
    else:frame.loc[0,'state_id']=99
    frame.to_csv(dest/'btc_filtered.csv',index=False)
    if corruption!='hash':rehash(dest)
    with pytest.warns(UnstableResearchWarning) if corruption!='hash' else __import__('contextlib').nullcontext():
        with pytest.raises(ValueError):load_hmm('BTC',False,True,tmp_path)
