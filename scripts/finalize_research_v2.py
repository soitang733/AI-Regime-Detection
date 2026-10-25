"""Wait for the registered NHHMM grid, then run dependent evaluation and exports."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    start=time.monotonic();manifest=ROOT/'outputs/research_v2/m3/manifest.json'
    while True:
        if manifest.exists():
            try:
                if json.loads(manifest.read_text())['status']=='grid_complete':break
            except json.JSONDecodeError:pass
        if time.monotonic()-start>86400:raise TimeoutError('Grid not complete within24h; no dependent evaluation')
        time.sleep(10)
    env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONHASHSEED':'0'}
    for module in ['nhhmm_evaluation','portfolio','reporting']:
        with (ROOT/f'outputs/research_v2/final_{module}.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,'-u','-m',f'src.research_v2.{module}'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        print(module,'exit_code',result.returncode,flush=True)
        if result.returncode:sys.exit(result.returncode)


if __name__=='__main__':main()
