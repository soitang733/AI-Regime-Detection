"""Prevent stale experiment checkpoints from being reused with changed inputs."""
import hashlib
import json
import os
from datetime import datetime,timezone
from src.utils.config import ROOT


def guard(stage,dependencies):
    folder=ROOT/f'outputs/research_v2/{stage}';folder.mkdir(parents=True,exist_ok=True)
    path=folder/'input_lock.json'
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in dependencies}
    if path.exists():
        prior=json.loads(path.read_text())
        if prior['inputs_sha256']!=hashes:
            raise ValueError(f'{stage}: inputs/code changed; archive old stage and create a new version, do not reuse checkpoints')
    else:
        temporary=path.with_suffix(f'.{os.getpid()}.tmp')
        temporary.write_text(json.dumps({'registered_at_utc':datetime.now(timezone.utc).isoformat(),'inputs_sha256':hashes,
            'existing_results_at_registration':any(p.name!='input_lock.json' for p in folder.iterdir()),
            'note':'Existing first-batch results were registered after execution; subsequent reuse is guarded.'},indent=2))
        temporary.replace(path)
    return hashes


def model_inputs():
    return [f'outputs/research_v2/m1/features_{a}.parquet' for a in ['btc','eth']]+['reports/m0_lock/PROTOCOL_V2_M0.md']
