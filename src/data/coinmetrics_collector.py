"""Public Coin Metrics historical market cap, kept separate from CoinGecko definitions."""

from __future__ import annotations

import io
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd
import requests

from src.data.collect import _upsert_source_log
from src.data.refresh_extensions import append_unique
from src.utils.config import load_config, path_of, write_json


def fetch(asset, last_closed):
    url = f"https://raw.githubusercontent.com/coinmetrics/data/master/csv/{asset.lower()}.csv"
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    source = pd.read_csv(io.StringIO(response.text), usecols=["time", "CapMrktCurUSD"])
    source["date_local"] = pd.to_datetime(source["time"], utc=True).dt.strftime("%Y-%m-%d")
    source["value"] = pd.to_numeric(source["CapMrktCurUSD"], errors="coerce")
    source = source.loc[source["date_local"].le(last_closed) & source["value"].gt(0)].copy()
    if source["date_local"].max() < last_closed:
        api = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
        response = requests.get(
            api,
            params={
                "assets": asset.lower(),
                "metrics": "CapMrktCurUSD",
                "frequency": "1d",
                "start_time": (pd.Timestamp(source["date_local"].max()) + pd.Timedelta(days=1)).strftime(
                    "%Y-%m-%d"
                ),
                "end_time": last_closed,
                "page_size": 10000,
            },
            timeout=45,
        )
        if response.ok:
            recent = pd.DataFrame(response.json().get("data", []))
            if not recent.empty:
                recent["date_local"] = pd.to_datetime(recent["time"], utc=True).dt.strftime("%Y-%m-%d")
                recent["value"] = pd.to_numeric(recent["CapMrktCurUSD"], errors="coerce")
                recent = recent.loc[recent["date_local"].le(last_closed) & recent["value"].gt(0)]
                source = pd.concat([source, recent], ignore_index=True).drop_duplicates(
                    "date_local", keep="first"
                )
            url += " + Coin Metrics Community API v4 incremental"
    source["series"] = f"CM_MCAP_{asset}"
    source["available_at_utc"] = (
        pd.to_datetime(source["date_local"], utc=True) + pd.Timedelta(days=2)
    ).astype(str)
    source["source"], source["fetched_at_utc"] = (
        "Coin Metrics Community CapMrktCurUSD",
        datetime.now(timezone.utc).isoformat(),
    )
    return source[["series", "date_local", "value", "available_at_utc", "source", "fetched_at_utc"]], url


def run(cfg=None):
    cfg = cfg or load_config()
    raw, meta = path_of(cfg, "raw"), path_of(cfg, "metadata")
    last_closed = (pd.Timestamp.now(tz="UTC").normalize() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    frames, logs, attempts = [], [], []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {asset: executor.submit(fetch, asset, last_closed) for asset in cfg["assets"]}
        for asset, future in futures.items():
            try:
                frame, url = future.result()
                frames.append(frame)
                attempts.append(
                    {
                        "asset": asset,
                        "status": "fetched",
                        "rows": len(frame),
                        "through": frame["date_local"].max(),
                    }
                )
                logs.append(
                    {
                        "asset": f"CM_MCAP_{asset}",
                        "symbol": asset,
                        "source": "Coin Metrics Community CapMrktCurUSD",
                        "endpoint": url,
                        "interval": "1d",
                        "timezone": "UTC",
                        "actual_start": frame["date_local"].min(),
                        "actual_end": frame["date_local"].max(),
                        "n_rows": len(frame),
                        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                        "notes": "Separate from CoinGecko; current-supply cap, current-vintage history; assumed available day+2, not a vintage database.",
                    }
                )
            except (requests.RequestException, ValueError, KeyError) as exc:
                attempts.append({"asset": asset, "status": "failed", "reason": str(exc)})
    if frames:
        destination = raw / "coinmetrics_market_daily.csv"
        old = pd.read_csv(destination) if destination.exists() else pd.DataFrame()
        append_unique(old, pd.concat(frames, ignore_index=True), ["series", "date_local"]).to_csv(
            destination, index=False
        )
        _upsert_source_log(logs, meta)
    report = {
        "status": "complete" if all(a["status"] == "fetched" for a in attempts) else "source_failures",
        "attempts": attempts,
    }
    write_json(report, meta / "coinmetrics_refresh.json")
    return report


if __name__ == "__main__":
    run()
