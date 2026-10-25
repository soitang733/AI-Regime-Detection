"""Incremental external-data refresh: retain cached history and log source failures."""

from __future__ import annotations

import copy
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from src.data.binance_collector import collect_asset
from src.data.collect import _upsert_source_log
from src.data.crypto_market_collector import collect_crypto_market
from src.data.derivatives_collector import _funding_history, _oi_one_day
from src.data.macro_collector import collect_macro
from src.utils.config import load_config, path_of, write_json


def append_unique(old, incoming, keys):
    """Append genuinely new keys; a refetch never revises historical observations."""
    if incoming.empty:
        return old.copy()
    if incoming.duplicated(keys).any() or (not old.empty and old.duplicated(keys).any()):
        raise ValueError(f"Duplicate source keys: {keys}")
    if old.empty:
        return incoming.copy()
    old_keys = pd.MultiIndex.from_frame(old[keys])
    new_keys = pd.MultiIndex.from_frame(incoming[keys])
    return pd.concat([old, incoming.loc[~new_keys.isin(old_keys)]], ignore_index=True)


def _derivative(asset, cfg, raw, end, kind):
    filename = "derivatives_daily.csv" if kind == "funding" else "open_interest_daily.csv"
    old = pd.read_csv(raw / filename)
    part = old.loc[old["asset"].eq(asset)]
    start = pd.Timestamp(part["date_utc"].max()) + pd.Timedelta(days=1)
    if start > pd.Timestamp(end):
        return filename, pd.DataFrame(), []
    incremental = copy.deepcopy(cfg)
    symbol = cfg["derivatives"]["symbols"][asset]
    if kind == "funding":
        incremental["derivatives"]["funding_start_date"] = start.strftime("%Y-%m-%d")
        frame = _funding_history(symbol, incremental)
        frame["date_utc"] = frame["funding_time_utc"].dt.strftime("%Y-%m-%d")
        frame = frame.loc[frame["date_utc"].le(end)]
        frame = (
            frame.groupby("date_utc")
            .agg(
                funding_sum=("fundingRate", "sum"),
                funding_mean=("fundingRate", "mean"),
                funding_n=("fundingRate", "size"),
                last_funding_utc=("funding_time_utc", "max"),
            )
            .reset_index()
        )
    else:
        days = pd.date_range(start, end).strftime("%Y-%m-%d").tolist()
        with ThreadPoolExecutor(max_workers=8) as executor:
            observations = list(executor.map(lambda day: _oi_one_day(symbol, day, cfg), days))
        frame = pd.DataFrame([row for row in observations if row])
    if not frame.empty:
        frame.insert(0, "asset", asset)
    return filename, frame, []


def run(cfg=None):
    cfg = cfg or load_config()
    raw, metadata = path_of(cfg, "raw"), path_of(cfg, "metadata")
    end = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    report = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "last_closed_utc": end,
        "mode": "append_only",
        "sources": [],
    }
    staged = []
    with tempfile.TemporaryDirectory(prefix="external-refresh-", dir=raw) as directory:
        stage = Path(directory)

        def macro():
            return "macro_daily.csv", collect_macro(cfg, stage)

        def crypto():
            return "crypto_market_daily.csv", collect_crypto_market(cfg, stage)

        def extra(asset):
            destination = raw / f"{asset.lower()}_ohlcv.csv"
            incremental = copy.deepcopy(cfg)
            if destination.exists():
                latest = pd.read_csv(destination)["date_utc"].max()
                if latest >= end:
                    return destination.name, pd.DataFrame(), []
                incremental["collection"]["start_date"] = (
                    pd.Timestamp(latest) + pd.Timedelta(days=1)
                ).strftime("%Y-%m-%d")
            incremental["collection"]["end_date"] = end
            log = collect_asset(asset, incremental, stage)
            return destination.name, pd.read_csv(stage / destination.name), [log]

        jobs = {"macro": macro, "crypto_market": crypto}
        for asset in cfg["assets"]:
            for kind in ("funding", "open_interest"):
                jobs[f"{asset}_{kind}"] = lambda a=asset, k=kind: _derivative(a, cfg, raw, end, k)
        for asset in cfg["extension_assets"]:
            jobs[asset] = lambda a=asset: extra(a)
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(fn): name for name, fn in jobs.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    if len(result) == 2:
                        filename, logs = result
                        frame = (
                            pd.read_csv(stage / filename) if (stage / filename).exists() else pd.DataFrame()
                        )
                    else:
                        filename, frame, logs = result
                    staged.append((filename, frame))
                    report["sources"].append(
                        {
                            "name": name,
                            "status": "partial_source_failure"
                            if any(not log.get("actual_end") for log in logs)
                            else "fetched"
                            if not frame.empty
                            else "no_new_data",
                            "rows_fetched": len(frame),
                            "attempts": logs,
                        }
                    )
                except Exception as exc:  # noqa: BLE001 -- isolate external source failures and preserve caches
                    report["sources"].append({"name": name, "status": "failed", "reason": str(exc)})
        # Mutate each cached file once; parallel downloads never overwrite each other.
        for filename in sorted({item[0] for item in staged}):
            incoming = pd.concat([frame for name, frame in staged if name == filename], ignore_index=True)
            if incoming.empty:
                continue
            keys = ["series", "date_local"] if "series" in incoming else ["asset", "date_utc"]
            if "asset" not in incoming and "series" not in incoming:
                keys = ["date_utc"]
            destination = raw / filename
            old = pd.read_csv(destination) if destination.exists() else pd.DataFrame()
            combined = append_unique(old, incoming, keys)
            temporary = destination.with_suffix(".csv.tmp")
            combined.to_csv(temporary, index=False)
            temporary.replace(destination)
            report.setdefault("files", []).append(
                {
                    "file": filename,
                    "historical_rows": len(old),
                    "added_rows": len(combined) - len(old),
                    "total_rows": len(combined),
                }
            )
        # Preserve failed sources' prior provenance. Full attempt details stay in this manifest.
        success_logs = [
            log for source in report["sources"] for log in source.get("attempts", []) if log.get("actual_end")
        ]
        for record in success_logs:
            asset = record["asset"]
            if asset in cfg["extension_assets"]:
                history = pd.read_csv(raw / f"{asset.lower()}_ohlcv.csv")
                date_column = "date_utc"
            elif asset in cfg["macro"]["tickers"] or asset in cfg["macro"].get("fred_series", {}):
                data = pd.read_csv(raw / "macro_daily.csv")
                history, date_column = data.loc[data["series"].eq(asset)], "date_local"
            else:
                data = pd.read_csv(raw / "crypto_market_daily.csv")
                history, date_column = data.loc[data["series"].eq(asset)], "date_local"
            if not history.empty:
                record.update(
                    actual_start=history[date_column].min(),
                    actual_end=history[date_column].max(),
                    n_rows=len(history),
                )
                record["notes"] = (
                    str(record.get("notes", ""))
                    + " Append-only refresh; source range/count describes retained cache."
                )
        for filename, suffix, source in [
            ("derivatives_daily.csv", "funding", "Binance Futures funding history"),
            ("open_interest_daily.csv", "open_interest", "Binance Vision daily metrics"),
        ]:
            if not (raw / filename).exists():
                continue
            for asset, history in pd.read_csv(raw / filename).groupby("asset"):
                success_logs.append(
                    {
                        "asset": f"{asset}_{suffix}",
                        "symbol": cfg["assets"][asset]["symbol"],
                        "source": source,
                        "actual_start": history["date_utc"].min(),
                        "actual_end": history["date_utc"].max(),
                        "n_rows": len(history),
                        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                        "timezone": "UTC",
                        "interval": "1d",
                        "notes": "Append-only cache; attempts and failures in external_refresh_manifest.json.",
                    }
                )
        if success_logs:
            _upsert_source_log(success_logs, metadata)
    report["status"] = (
        "complete_with_source_failures"
        if any(s["status"] in ("failed", "partial_source_failure") for s in report["sources"])
        else "complete"
    )
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(report, metadata / "external_refresh_manifest.json")
    return report


if __name__ == "__main__":
    run()
