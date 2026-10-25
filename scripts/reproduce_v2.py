"""Run every V2 stage in an isolated copy, compare numbers, then remove the copy.

Default: reuse registered fit checkpoints, rebuild data/inference/evaluation/exports.
This is a local technical replay, never independent research confirmation.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'outputs/research_v2/reproduction'
WORK = ROOT / '.work/v2-reproduction'
STAGES = ['m1', 'm2', 'ablation', 'simulation', 'm3', 'm3_evaluation', 'm4',
          'msgarch', 'm4_evaluation', 'm5', 'profiles', 'outputs', 'seal']
FOLDERS = ['m1', 'm2', 'm2_ablation', 'm3_simulation', 'm3', 'm3_evaluation', 'm4',
           'm4_msgarch', 'm4_evaluation', 'm5', 'm2_profiles', 'deliverables']


def compare_csv(original, reproduced):
    a, b = pd.read_csv(original), pd.read_csv(reproduced)
    if list(a.columns) != list(b.columns) or a.shape != b.shape:
        return {'passed': False, 'reason': 'schema_or_shape'}
    worst = 0.0
    for col in a:
        if pd.api.types.is_numeric_dtype(a[col]) and pd.api.types.is_numeric_dtype(b[col]):
            left, right = a[col].to_numpy(float), b[col].to_numpy(float)
            if not np.allclose(left, right, rtol=1e-9, atol=1e-10, equal_nan=True):
                return {'passed': False, 'reason': f'numeric:{col}'}
            finite = np.isfinite(left) & np.isfinite(right)
            if finite.any():
                worst = max(worst, float(abs(left[finite] - right[finite]).max()))
        elif not a[col].fillna('<NA>').equals(b[col].fillna('<NA>')):
            return {'passed': False, 'reason': f'value:{col}'}
    return {'passed': True, 'rows': len(a), 'max_numeric_error': worst}


def main():
    if not WORK.resolve().is_relative_to(ROOT.resolve()) or WORK.exists():
        raise ValueError('Replay destination must be a new directory inside project')
    DEST.mkdir(parents=True, exist_ok=True)
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for folder in FOLDERS for p in (ROOT / f'outputs/research_v2/{folder}').rglob('*') if p.is_file()}
    (DEST / 'before.json').write_text(json.dumps({'inputs_sha256': hashes}, indent=2))
    log, comparisons = [], []
    started = time.monotonic()
    try:
        for name in ['src', 'config', 'data', 'scripts', 'reports/m0_lock']:
            shutil.copytree(ROOT / name, WORK / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.zip', '*.pyc'))
        for name in ['v2_benchmark_specification.md', 'v2_volume_ablation_specification.md']:
            shutil.copy2(ROOT / 'reports' / name, WORK / 'reports' / name)
        for name in FOLDERS:
            shutil.copytree(ROOT / f'outputs/research_v2/{name}', WORK / f'outputs/research_v2/{name}')
        # Only versioned C1 inputs are dependencies. V2 portfolio signals come from
        # outputs/research_v2/m2, so a clean checkout must not require ignored C2/C3 exports.
        for name in ['metadata', 'models', 'tables']:
            shutil.copytree(ROOT / 'outputs' / name, WORK / 'outputs' / name,
                            ignore=shutil.ignore_patterns('*.pid', '*.zip'))
        env = {**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
               'MKL_NUM_THREADS': '1', 'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1',
               'PYTHONIOENCODING': 'utf-8'}
        for stage in STAGES:
            tick = time.monotonic()
            with (DEST / f'{stage}.log').open('w', encoding='utf-8') as stream:
                command = [sys.executable, 'scripts/run_research_v2.py', '--stage', stage]
                result = subprocess.run(command, check=False, cwd=WORK, env=env,
                                        stdout=stream, stderr=subprocess.STDOUT)
            log.append({'stage': stage, 'exit_code': result.returncode, 'seconds': time.monotonic() - tick,
                        'registered_fit_checkpoints_reused': stage in ['m2', 'ablation', 'simulation', 'm3', 'm4', 'msgarch']})
            internal = WORK / f'outputs/research_v2/run_logs/{stage}.log'
            if internal.exists():
                shutil.copy2(internal, DEST / f'{stage}.detail.log')
            print(json.dumps(log[-1]), flush=True)
            if result.returncode:
                raise RuntimeError(f'Replay stage failed: {stage}')
        for folder in FOLDERS:
            for original in sorted((ROOT / f'outputs/research_v2/{folder}').rglob('*.csv')):
                reproduced = WORK / original.relative_to(ROOT)
                check = compare_csv(original, reproduced) if reproduced.exists() else {'passed': False, 'reason': 'missing'}
                comparisons.append({'path': original.relative_to(ROOT).as_posix(), **check})
        unchanged = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items())
        passed = unchanged and all(c['passed'] for c in comparisons) and len(log) == len(STAGES)
        report = {'status': 'passed' if passed else 'failed', 'stages': log, 'csv_comparisons': comparisons,
                  'original_artifacts_unchanged': unchanged, 'seconds': time.monotonic() - started,
                  'fresh_model_fits': 0, 'mode': 'all stages; registered fit checkpoints reused; data/inference/evaluation rebuilt',
                  'independent_research_confirmation': 'pending'}
        (DEST / 'result.json').write_text(json.dumps(report, indent=2))
        if not passed:
            raise RuntimeError('Numerical replay mismatch; see result.json')
    finally:
        if WORK.exists() and WORK.resolve().is_relative_to(ROOT.resolve()):
            shutil.rmtree(WORK)
        if WORK.parent.exists() and not any(WORK.parent.iterdir()):
            WORK.parent.rmdir()


if __name__ == '__main__':
    main()
