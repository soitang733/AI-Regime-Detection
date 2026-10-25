"""One V2 working tree; preserve old working trees in reachable Git archive refs.

No commit, reset --hard, checkout, push, or network request is performed.
Run only from the currently nested checkout in this workspace.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
ROOT = SOURCE.parents[1]
OLD = ROOT / 'AI-Regime-Detection-commit'
SKIP = {'.git', '__pycache__', '.pytest_cache', '.ruff_cache', '.venv', 'venv', '.work', '.ipynb_checkpoints'}


def git(*args, data=None, env=None):
    result = subprocess.run(['git', '-c', f'safe.directory={ROOT.as_posix()}',
                             '-c', 'core.autocrlf=false', '--git-dir', str(ROOT / '.git'),
                             *args], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
    return result.stdout


def snapshot(source, ref):
    files = sorted(p for p in source.rglob('*') if p.is_file()
                   and not any(part in SKIP for part in p.relative_to(source).parts)
                   and p.name != '.env' and not p.name.startswith('.env.')
                   and 'secret' not in p.name.lower())
    # Keep the public template, never local credentials.
    template = source / '.env.example'
    if template.exists():
        files.append(template)
    files = sorted(set(files))
    inventory = {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with tempfile.TemporaryDirectory(prefix='v2-git-index-') as temp:
        env = {**os.environ, 'GIT_INDEX_FILE': str(Path(temp) / 'index')}
        git('read-tree', '--empty', env=env)
        git('--work-tree', str(source), 'add', '--force', '--pathspec-from-file=-', '--pathspec-file-nul',
            data=b'\0'.join(n.encode('utf-8') for n in inventory) + b'\0', env=env)
        tree = git('write-tree', env=env).decode().strip()
    entries = git('ls-tree', '-rz', tree).split(b'\0')
    objects = {}
    for entry in entries:
        if entry:
            header, name = entry.split(b'\t', 1)
            objects[name.decode('utf-8')] = header.split()[2].decode()
    if set(objects) != set(inventory):
        raise ValueError('Archive tree inventory mismatch')
    process = subprocess.Popen(['git', '--git-dir', str(ROOT / '.git'), 'cat-file', '--batch'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for name, oid in objects.items():
            process.stdin.write((oid + '\n').encode())
            process.stdin.flush()
            header = process.stdout.readline().split()
            payload = process.stdout.read(int(header[2]))
            process.stdout.read(1)
            if hashlib.sha256(payload).hexdigest() != inventory[name]:
                raise ValueError(f'Archive bytes differ: {name}')
    finally:
        process.stdin.close()
        process.wait()
    git('update-ref', ref, tree)
    return {'ref': ref, 'tree': tree, 'files': len(files), 'verified_sha256': inventory}


def main():
    if ROOT != Path('D:/AI-Regime-Detection-main') or SOURCE != ROOT / 'local-demo-20261024/AI-Regime-Detection-main':
        raise ValueError('Unexpected workspace layout; this migration is intentionally specific')
    if (ROOT / '.git').exists():
        raise ValueError('Root Git already exists; inspect prior migration before retry')
    if (SOURCE / '.work').exists():
        raise ValueError('Wait for reproduction to finish before moving project')
    # Local clone imports the existing V1 commit graph. No GitHub/network access.
    subprocess.run(['git', '-c', f'safe.directory={OLD.as_posix()}', 'clone', '--bare', '--no-hardlinks',
                    str(OLD), str(ROOT / '.git')], check=True)
    git('config', 'core.bare', 'false')
    remote = subprocess.check_output(['git', '-c', f'safe.directory={OLD.as_posix()}', '-C', str(OLD),
                                      'config', '--get', 'remote.origin.url']).decode().strip()
    git('remote', 'set-url', 'origin', remote)
    history = []
    for path, ref in [(OLD, 'refs/archive/v1-commit-worktree'),
                      (ROOT / 'AI-Regime-Detection-main', 'refs/archive/v1-original-worktree'),
                      (SOURCE, 'refs/archive/v2-before-cleanup')]:
        history.append(snapshot(path, ref))
    report = SOURCE / 'reports/v2_review'
    report.mkdir(parents=True, exist_ok=True)
    (report / 'repository_history.json').write_text(json.dumps({'history': history, 'commits_created': 0,
        'network_used': False, 'root': str(ROOT)}, indent=2), encoding='utf-8')
    for child in list(SOURCE.iterdir()):
        destination = ROOT / child.name
        if destination.exists():
            raise ValueError(f'Destination already exists: {destination}')
        shutil.move(str(child), str(destination))
    for path in [OLD, ROOT / 'AI-Regime-Detection-main']:
        resolved = path.resolve()
        if resolved.parent != ROOT.resolve() or path.name not in ['AI-Regime-Detection-commit', 'AI-Regime-Detection-main']:
            raise ValueError('Refuse recursive removal outside exact archived old checkout')
        shutil.rmtree(path)
    SOURCE.rmdir()
    SOURCE.parent.rmdir()
    # Build the normal V1 index only. Current V2 changes remain uncommitted.
    git('--work-tree', str(ROOT), 'reset', '--mixed', 'HEAD')
    print(json.dumps({'root': str(ROOT), 'archive_refs': [h['ref'] for h in history], 'commits_created': 0}))


if __name__ == '__main__':
    main()
