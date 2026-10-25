"""Seal completed stage artifacts without treating operational logs as model data."""
import hashlib
import json
import math
from datetime import datetime,timezone
from src.research_v2.provenance import guard,model_inputs
from src.utils.config import ROOT


def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,list):return [clean(v) for v in value]
    if isinstance(value,float) and not math.isfinite(value):return None
    return value


def run():
    guard('m2',model_inputs()+['src/research_v2/hmm.py','src/research/robustness.py','src/models/inference.py','src/research/economics.py'])
    guard('m3',model_inputs()+['src/research_v2/nhhmm.py','src/research_v2/nhhmm_run.py'])
    guard('m4',model_inputs()+['src/research_v2/benchmarks.py','reports/v2_benchmark_specification.md'])
    guard('m4_msgarch',model_inputs()+['src/research_v2/msgarch.py','reports/v2_benchmark_specification.md'])
    base=ROOT/'outputs/research_v2'
    qualified=base/'m3/qualified_groups.json'
    qualified.write_text(json.dumps(clean(json.loads(qualified.read_text())),indent=2,allow_nan=False))
    for stage in ['m3','m4','m4_msgarch','m4_evaluation','m2_profiles','m2_ablation']:
        folder=base/stage;manifest=folder/'manifest.json'
        metadata=json.loads(manifest.read_text()) if manifest.exists() else {'status':'complete'}
        metadata['hashes_sealed_at_utc']=datetime.now(timezone.utc).isoformat()
        metadata['files_sha256']={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file() and p!=manifest and p.suffix!='.tmp'}
        manifest.write_text(json.dumps(metadata,indent=2,allow_nan=False))
        print(stage,len(metadata['files_sha256']))


if __name__=='__main__':run()
