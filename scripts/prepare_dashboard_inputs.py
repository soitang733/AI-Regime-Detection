"""Freeze verified price views so later C1 refreshes cannot change historical V2 charts."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = ROOT/'outputs/research_v2'
    m1 = json.loads((base/'m1/manifest.json').read_text())
    inputs = {k.replace('\\', '/'): v for k, v in m1['inputs_sha256'].items()}
    output = base/'view_inputs'
    output.mkdir(exist_ok=True)
    metadata = {'status': 'complete', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'model_run_ids': {}, 'source_inputs_sha256': {}, 'files_sha256': {}}
    staged = []
    for asset in ['BTC', 'ETH']:
        name = f'data/raw/{asset.lower()}_ohlcv.csv'
        path = ROOT/name
        expected = inputs[name]
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'{asset}: raw prices changed since V2; restore the verified source before preparing a snapshot')
        model = json.loads((base/f'm2/{asset.lower()}_metadata.json').read_text())
        signals = pd.read_csv(base/f'm2/{asset.lower()}_filtered.csv')
        prices = pd.read_csv(path)
        prices = prices.loc[prices.date_utc.isin(signals.date_utc)].sort_values('date_utc')
        if prices.date_utc.duplicated().any() or set(prices.date_utc) != set(signals.date_utc):
            raise ValueError('Price snapshot does not cover the model dates')
        destination = output/f'prices_{asset.lower()}.parquet'
        temporary = destination.with_suffix('.parquet.tmp')
        prices.to_parquet(temporary, index=False)
        staged.append((temporary, destination))
        metadata['model_run_ids'][asset] = model['candidate_id']
        metadata['source_inputs_sha256'][name] = expected
        metadata['files_sha256'][destination.name] = hashlib.sha256(temporary.read_bytes()).hexdigest()
    for temporary, destination in staged:
        temporary.replace(destination)
    temporary = output/'manifest.json.tmp'
    temporary.write_text(json.dumps(metadata, indent=2))
    temporary.replace(output/'manifest.json')
    print('Verified price snapshots prepared for BTC/ETH')


if __name__ == '__main__':
    main()
