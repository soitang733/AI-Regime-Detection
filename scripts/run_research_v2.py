"""Reproduce V2 stages, capture logs and stop on any failed stage."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STAGES={'m1':'data','m2':'hmm','ablation':'ablation','simulation':'simulation','m3':'nhhmm_run',
        'm3_evaluation':'nhhmm_evaluation','m4':'benchmarks','msgarch':'msgarch',
        'm4_evaluation':'benchmark_evaluation','m5':'portfolio','profiles':'profiles','outputs':'reporting','seal':'seal'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['all']+list(STAGES),default='all');args=parser.parse_args()
    if (ROOT/'outputs/research_v2/confirmation_lock.json').exists():
        raise RuntimeError('Locked cohort: use python scripts/reproduce_v2.py for an isolated replay; do not overwrite live results')
    logs=ROOT/'outputs/research_v2/run_logs';logs.mkdir(parents=True,exist_ok=True)
    import os
    environment={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONHASHSEED':'0'}
    for stage,module in STAGES.items():
        if args.stage not in ['all',stage]:continue
        with (logs/f'{stage}.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,'-u','-m',f'src.research_v2.{module}'],cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT)
        print(f'{stage}: exit={result.returncode}; log={logs/(stage+".log")}',flush=True)
        if result.returncode:sys.exit(result.returncode)


if __name__=='__main__':main()
