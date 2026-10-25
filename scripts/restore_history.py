"""Restore an archived file byte-for-byte, with its recorded SHA-256."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ref', required=True)
    parser.add_argument('--path', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    history = json.loads((ROOT / 'reports/v2_review/repository_history.json').read_text())['history']
    snapshot = next((s for s in history if s['ref'] == args.ref), None)
    path = PurePosixPath(args.path)
    if snapshot is None or path.is_absolute() or '..' in path.parts or str(path) not in snapshot['verified_sha256']:
        raise ValueError('Unknown archive ref/path')
    destination = (ROOT / args.output).resolve()
    if not destination.is_relative_to(ROOT.resolve()) or destination.exists():
        raise ValueError('Destination must be new and inside the repository')
    data = subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}', '-C', str(ROOT),
                                    'show', f'{args.ref}:{path}'])
    digest = hashlib.sha256(data).hexdigest()
    if digest != snapshot['verified_sha256'][str(path)]:
        raise ValueError('Archive SHA-256 mismatch')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    print(json.dumps({'path': str(destination), 'bytes': len(data), 'sha256': digest}))


if __name__ == '__main__':
    main()
