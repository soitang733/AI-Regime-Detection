"""Remove known superseded generated files; preserve manifests and research artifacts.

Dry-run by default. --apply is an explicit request to remove the listed files.
The retained-file inventory protects the frozen baseline and live manifest inputs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1].resolve()
BASE = ROOT/'outputs/research_v2'
CACHE_NAMES = {'__pycache__', '.pytest_cache', '.ruff_cache', '.ipynb_checkpoints'}
OLD_DIRECTORIES = [
    'reports/archive', 'reports/blueprint_improvement_proposal_20261024',
    'reports/blueprint_research_review_20261024', 'reports/ui_review_20261025/previous',
    'reports/ui_review_20261025/diagnostics',
    'outputs/research_v2/m3_python_reference',
    'outputs/research_v2/m3_simulation_python_reference',
]
OLD_PACKAGES = [
    'reports/Blueprint_02_research_report_20261024.zip',
    'reports/De_xuat_cai_tien_Blueprint_02_20261024.zip',
    'reports/KE_HOACH_FINAL_CHO_DUYET_Blueprint_02.zip',
]
KEEP_V2_LOGS = {
    'acceptance_pytest_final.log', 'acceptance_pytest_final.xml', 'acceptance_browser_release.log',
    'dashboard_server.stderr.log', 'dashboard_server.stdout.log',
    'm2_run.log', 'm3_accelerated_run.log', 'm3_shard_0.log', 'm3_shard_1.log',
    'm3_shard_2.log', 'm3_shard_3.log', 'm3_simulation_accelerated.log',
    'm4_run.log', 'm4_msgarch_run.log', 'ablation.log',
    'final_nhhmm_evaluation.log', 'final_portfolio.log', 'final_reporting.log',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_files():
    baseline = json.loads((ROOT/'reports/m0_lock/baseline_manifest.json').read_text())
    protected = {(ROOT/name).resolve() for name in baseline['files']}
    documents = [ROOT/'reports/m0_lock/lock_manifest.json']
    documents += list((ROOT/'outputs').rglob('*manifest*.json'))
    documents += list(BASE.rglob('input_lock.json')) + [BASE/'confirmation_lock.json']
    for path in documents:
        if any(path.is_relative_to(ROOT/old) for old in OLD_DIRECTORIES):
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        protected.add(path.resolve())
        for field in ['files_sha256', 'inputs_sha256', 'input_hashes', 'output_hashes', 'source_hashes']:
            for name in data.get(field, {}):
                relative = name.replace('\\', '/')
                parent = path.parent if field == 'files_sha256' else ROOT
                protected.add((parent/relative).resolve())
    return protected


def files_under(path):
    return [p for p in path.rglob('*') if p.is_file()] if path.is_dir() else [path]


def build_plan():
    protected = protected_files()
    targets = [(ROOT/name, 'superseded generated output') for name in OLD_DIRECTORIES + OLD_PACKAGES]
    for path in BASE.iterdir():
        if path.is_file() and path.suffix in {'.log', '.xml'} and path.name not in KEEP_V2_LOGS:
            targets.append((path, 'superseded intermediate verification log'))
    targets += [(BASE/'ui_router_smoke.json', 'superseded UI smoke result')]
    for path in ROOT.rglob('*'):
        if path.is_dir() and path.name in CACHE_NAMES and not any(
                part in {'.git', '.venv', 'venv', '.agents', '.codex'} for part in path.relative_to(ROOT).parts):
            targets.append((path, 'regenerable tool cache'))
    # These are earlier assistant-generated exports, not the user's source ZIPs/checkouts.
    outer = Path('D:/AI-Regime-Detection-main').resolve()
    if ROOT.is_relative_to(outer) and ROOT.parent.name == 'local-demo-20261024':
        for name in ['AI-Crypto-Regime-Radar-complete-20261024.zip',
                     'AI-Crypto-Regime-Radar-complete-20261024.zip.sha256']:
            targets.append((outer/name, 'superseded project export'))
    chosen = []
    for path, reason in sorted(targets, key=lambda item: len(item[0].parts)):
        if not path.exists() or any(path.is_relative_to(parent) for parent, _ in chosen):
            continue
        absolute = path.resolve()
        allowed_parent_export = absolute.parent == outer and absolute.name in {
            'AI-Crypto-Regime-Radar-complete-20261024.zip',
            'AI-Crypto-Regime-Radar-complete-20261024.zip.sha256'}
        if not absolute.is_relative_to(ROOT) and not allowed_parent_export:
            raise ValueError(f'Outside cleanup scope: {absolute}')
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise ValueError(f'Refuse linked target: {absolute}')
        members = files_under(path)
        if any(p.resolve() in protected for p in members):
            raise ValueError(f'Cleanup would remove a referenced artifact: {path}')
        if any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in path.rglob('*')) if path.is_dir() else False:
            raise ValueError(f'Refuse directory containing linked entries: {path}')
        chosen.append((absolute, reason))
    return chosen, protected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--caches-only', action='store_true', help='Limit deletion to regenerable Python/test/lint caches')
    args = parser.parse_args()
    targets, protected = build_plan()
    if args.caches_only:
        targets = [(path, reason) for path, reason in targets if reason == 'regenerable tool cache']
    existing_protected = {str(p): digest(p) for p in protected if p.is_file()}
    items = []
    for path, reason in targets:
        members = files_under(path)
        items.append({'path': str(path), 'reason': reason, 'files': len(members),
                      'bytes': sum(p.stat().st_size for p in members)})
    report = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'mode': 'apply' if args.apply else 'dry_run',
              'scope': 'caches_only' if args.caches_only else 'proposed_generated_outputs',
              'targets': items, 'files': sum(row['files'] for row in items),
              'bytes': sum(row['bytes'] for row in items)}
    if args.apply:
        for path, _ in targets:
            # Each resolved absolute target and all protected members were checked above.
            shutil.rmtree(path) if path.is_dir() else path.unlink()
        changed = [name for name, value in existing_protected.items()
                   if not Path(name).is_file() or digest(Path(name)) != value]
        if changed:
            raise RuntimeError(f'Protected files changed: {changed}')
        report['protected_files_verified_unchanged'] = len(existing_protected)
        destination = ROOT/'reports/cleanup'
        destination.mkdir(exist_ok=True)
        name = 'cache_cleanup_manifest.json' if args.caches_only else 'cleanup_manifest.json'
        (destination/name).write_text(json.dumps(report, indent=2), encoding='utf-8')
    else:
        destination = ROOT/'reports/cleanup'
        destination.mkdir(exist_ok=True)
        (destination/'cleanup_plan.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'mode': report['mode'], 'targets': len(items), 'files': report['files'],
                      'MiB': round(report['bytes']/1048576, 2),
                      'paths': [row['path'] for row in items]}, indent=2))


if __name__ == '__main__':
    main()
