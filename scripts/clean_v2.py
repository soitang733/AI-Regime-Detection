"""Remove archived legacy documentation/exports and regenerable caches only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1].resolve()
CACHES = {'__pycache__', '.pytest_cache', '.ruff_cache', '.ipynb_checkpoints'}
LEGACY_TOOLS = ['scripts/check_dashboard_layout.py', 'scripts/capture_dashboard.py',
                'scripts/build_ui_review_report.py', 'scripts/build_v2_delivery.py',
                'scripts/finalize_research_v2.py', 'scripts/consolidate_repository.py']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    history = json.loads((ROOT / 'reports/v2_review/repository_history.json').read_text())
    snapshot = next(h for h in history['history'] if h['ref'] == 'refs/archive/v2-before-cleanup')
    targets = [p for p in (ROOT / 'docs').glob('*.md') if not p.name.startswith('V2_') and p.name != 'A01_data_contract.md']
    targets += [ROOT / p for p in LEGACY_TOOLS]
    targets += list(ROOT.rglob('*.zip'))
    for folder in ['reports/v2_delivery', 'reports/ui_review_20261025', 'reports/cleanup']:
        targets += [p for p in (ROOT / folder).rglob('*') if p.is_file()]
    rows = []
    for p in sorted(set(targets)):
        if not p.exists() or '.git' in p.relative_to(ROOT).parts:
            continue
        name = p.relative_to(ROOT).as_posix()
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if not p.resolve().is_relative_to(ROOT) or snapshot['verified_sha256'].get(name) != digest:
            raise ValueError(f'Not safely archived: {name}')
        rows.append({'path': name, 'bytes': p.stat().st_size, 'sha256': digest, 'archive_ref': snapshot['ref']})
    removed_caches = []
    for p in ROOT.rglob('*'):
        if p.is_dir() and p.name in CACHES and '.git' not in p.relative_to(ROOT).parts:
            if not p.resolve().is_relative_to(ROOT):
                raise ValueError('Cache outside root')
            removed_caches.append(p)
    report = {'apply': args.apply, 'archived_files': rows,
              'cache_directories': [p.relative_to(ROOT).as_posix() for p in removed_caches]}
    if args.apply:
        for row in rows:
            (ROOT / row['path']).unlink()
        for p in removed_caches:
            if p.exists():
                shutil.rmtree(p)
        for folder in ['reports/v2_delivery', 'reports/ui_review_20261025', 'reports/cleanup']:
            for p in sorted((ROOT / folder).rglob('*'), reverse=True):
                if p.is_dir() and not any(p.iterdir()):
                    p.rmdir()
            p = ROOT / folder
            if p.exists() and not any(p.iterdir()):
                p.rmdir()
    (ROOT / 'reports/v2_review/cleanup.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'apply': args.apply, 'archived_files': len(rows), 'bytes': sum(r['bytes'] for r in rows),
                      'cache_directories': len(removed_caches)}))


if __name__ == '__main__':
    main()
