"""Append only new closed daily candles; never rewrite the historical research sample."""

from __future__ import annotations

import copy
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from src.data.binance_collector import collect_asset
from src.data.collect import _upsert_source_log
from src.utils.config import path_of, write_json


def append_closed_candles(existing, incoming):
    if incoming["date_utc"].duplicated().any():
        raise ValueError("Duplicate dates in incoming refresh")
    if existing.empty:
        return incoming.sort_values("date_utc").reset_index(drop=True)
    if existing["date_utc"].duplicated().any() or incoming["date_utc"].duplicated().any():
        raise ValueError("Duplicate dates in raw refresh")
    tail = incoming.loc[incoming["date_utc"].gt(existing["date_utc"].max())].copy()
    return pd.concat([existing, tail], ignore_index=True)


def run(cfg):
    raw, meta = path_of(cfg, "raw"), path_of(cfg, "metadata")
    last_closed = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    report = {"status": "running", "last_closed_utc": last_closed, "mode": "append_only", "assets": {}}
    rows = []
    try:
        for asset in cfg["assets"]:
            destination = raw / f"{asset.lower()}_ohlcv.csv"
            old = pd.read_csv(destination) if destination.exists() else pd.DataFrame()
            latest = old["date_utc"].max() if len(old) else None
            if latest and latest > last_closed:
                raise ValueError(f"{asset}: raw data contains an unclosed or future UTC candle")
            if latest == last_closed:
                report["assets"][asset] = {"through": latest, "added": 0}
                continue
            incremental = copy.deepcopy(cfg)
            if latest:
                incremental["collection"]["start_date"] = (
                    pd.Timestamp(latest) + pd.Timedelta(days=1)
                ).strftime("%Y-%m-%d")
            incremental["collection"]["end_date"] = last_closed
            with tempfile.TemporaryDirectory(prefix="refresh-", dir=raw) as directory:
                source = collect_asset(asset, incremental, Path(directory))
                incoming = pd.read_csv(Path(directory) / destination.name)
                combined = append_closed_candles(old, incoming)
            if combined.empty or combined["date_utc"].max() != last_closed:
                raise ValueError(f"{asset}: source has not returned the latest closed UTC day {last_closed}")
            temporary = destination.with_suffix(".csv.tmp")
            if destination.exists():
                # Keep historical CSV bytes, avoiding float-roundtrip changes to train features.
                historical = destination.read_bytes()
                tail = combined.iloc[len(old) :].to_csv(index=False, header=False).encode("utf-8")
                temporary.write_bytes(historical.rstrip(b"\r\n") + b"\n" + tail)
            else:
                combined.to_csv(temporary, index=False)
            temporary.replace(destination)
            source.update(
                actual_start=combined["date_utc"].min(),
                n_rows=len(combined),
                notes=f"Append-only refresh: retained {len(old)} historical rows; appended {len(combined) - len(old)} closed candles. "
                "Historical row provenance remains in raw data.",
            )
            rows.append(source)
            report["assets"][asset] = {
                "through": source["actual_end"],
                "added": len(combined) - len(old),
                "historical_rows_preserved": len(old),
            }
        if rows:
            _upsert_source_log(rows, meta)
        report["status"] = "complete"
    except Exception as exc:
        report["status"], report["error"] = "failed", str(exc)
        raise
    finally:
        write_json(report, meta / "refresh_manifest.json")
    return report
