"""C3-02 - Lớp đọc kết quả cho dashboard (result service).

Dashboard CHỈ đọc các file đã được pipeline xuất và version hóa (CSV/Parquet/JSON).
Không fit lại mô hình, không tự tính lại chỉ số hiệu suất quan trọng trong UI.
Thiếu file nào thì trả về None kèm thông báo; không sinh dữ liệu giả.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.config import file_hash, load_config

CFG = load_config()
P = {k: ROOT / v for k, v in CFG["paths"].items()}

FILES = {
    "split_manifest": P["metadata"] / "split_manifest.json",
    "model_manifest": P["metadata"] / "model_manifest.json",
    "backtest_manifest": P["metadata"] / "backtest_manifest.json",
    "prices": P["processed"] / "prices_daily.parquet",
    "B03": P["tables"] / "B03_model_selection.csv",
    "B04": P["tables"] / "B04_regime_statistics.csv",
    "B05": P["tables"] / "B05_transition_matrix.csv",
    "B07": P["tables"] / "B07_hmm_vs_gmm.csv",
    "B08": P["tables"] / "B08_portfolio.csv",
    "stability": P["tables"] / "C2_stability_summary.csv",
    "window_sensitivity": P["tables"] / "C2_window_sensitivity.csv",
    "nav": P["predictions"] / "backtest_nav.csv",
    "research_manifest": P["metadata"] / "research_manifest.json",
    "economic": P["tables"] / "research_economic_labels.csv",
    "economic_sensitivity": P["tables"] / "research_economic_sensitivity.csv",
    "liquidity_profiles": P["tables"] / "research_liquidity_profiles.csv",
    "emission_explanation": P["tables"] / "research_emission_explanation.csv",
    "drivers_metrics": P["tables"] / "research_drivers_metrics.csv",
    "drivers_coefficients": P["tables"] / "B06_drivers.csv",
    "research_benchmarks": P["tables"] / "research_benchmarks.csv",
    "research_stability": P["tables"] / "research_hmm_stability.csv",
    "research_portfolio": P["tables"] / "research_portfolio.csv",
    "research_uncertainty": P["tables"] / "research_portfolio_uncertainty.csv",
    "research_nav": P["predictions"] / "research" / "portfolio_nav.csv",
    "trend_evidence": P["tables"] / "research_trend_evidence.csv",
    "trend_comparisons": P["tables"] / "research_trend_comparisons.csv",
    "trend_stats": P["tables"] / "research_trend_stats.csv",
    "trend_portfolio": P["tables"] / "research_trend_portfolio.csv",
}


def asset_files(asset):
    a = asset.lower()
    return {
        "features": P["processed"] / f"features_{a}.parquet",
        "filtered": P["predictions"] / f"regime_filtered_{a}.csv",
        "smoothed": P["predictions"] / f"regime_smoothed_{a}.csv",
        "gmm": P["predictions"] / f"regime_gmm_{a}.csv",
        "trend_filtered": P["predictions"] / "research" / f"trend_filtered_{a}.csv",
    }


REQUIRED = {
    "Dữ liệu C1": ["split_manifest", "prices"],
    "Mô hình C2": ["model_manifest", "B03", "B04", "B05", "B07"],
    "Backtest C3": ["backtest_manifest", "B08", "nav"],
}
FIX_HINT = {
    "Dữ liệu C1": "python run_pipeline.py --steps clean features reports",
    "Mô hình C2": "python scripts/complete_c2.py   (hoặc python run_pipeline.py --steps models)",
    "Backtest C3": "python run_pipeline.py --steps backtest",
}


def assets():
    return list(CFG["assets"])


def file_status():
    """Trạng thái từng nhóm đầu ra: danh sách file thiếu và lệnh khắc phục."""
    out = {}
    for group, keys in REQUIRED.items():
        missing = [FILES[k].relative_to(ROOT).as_posix() for k in keys if not FILES[k].exists()]
        if group == "Mô hình C2":
            for asset in assets():
                for kind in ("filtered", "smoothed"):
                    p = asset_files(asset)[kind]
                    if not p.exists():
                        missing.append(p.relative_to(ROOT).as_posix())
        out[group] = {"missing": missing, "fix": FIX_HINT[group]}
    return out


def mtime_key(path):
    """Khóa cache: đổi file (chạy lại pipeline) thì dashboard đọc lại."""
    path = Path(path)
    return path.stat().st_mtime_ns if path.exists() else None


def dataset_version():
    """A cache key covering manifests AND their dependencies; no underscore arguments."""
    paths = set(FILES.values())
    paths.update((ROOT / "config/config.yaml", ROOT / "config/backtest.yaml", ROOT / "config/research.yaml"))
    for key in ("model_manifest", "backtest_manifest", "research_manifest"):
        try:
            manifest = read_json(key) or {}
            for field in ("output_hashes", "input_hashes", "source_hashes"):
                paths.update(ROOT / p for p in manifest.get(field, {}))
        except (ValueError, OSError):
            pass  # A writer in progress is caught by validate_bundle, never displayed.
    for asset in assets():
        paths.update(asset_files(asset).values())
    return tuple((str(p), mtime_key(p), p.stat().st_size if p.exists() else None) for p in sorted(paths))


def freshness(asset, now=None):
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    expected = now.normalize() - pd.Timedelta(days=1)
    manifest = read_json("split_manifest") or {}
    through = manifest.get("data_through_utc")
    through = through.get(asset) if isinstance(through, dict) else through
    if not through:
        return {
            "status": "missing",
            "through": None,
            "expected": expected.strftime("%Y-%m-%d"),
            "lag_days": None,
        }
    date = pd.Timestamp(through)
    date = date.tz_localize("UTC") if date.tzinfo is None else date.tz_convert("UTC")
    lag = (expected - date).days
    return {
        "status": "current" if lag == 0 else "stale" if lag > 0 else "invalid",
        "through": through,
        "expected": expected.strftime("%Y-%m-%d"),
        "lag_days": max(lag, 0),
    }


def validate_bundle():
    """Reject incomplete, tampered or mixed C1/C2/C3 results before any chart is shown."""
    errors = []
    try:
        model, backtest, split = (
            read_json(k) for k in ("model_manifest", "backtest_manifest", "split_manifest")
        )
        if not all((model, backtest, split)):
            return {
                "ok": False,
                "errors": ["Chưa đủ kết quả C1/C2/C3. Chạy python scripts/refresh_local.py."],
            }
        for name, manifest in (("C2", model), ("C3", backtest)):
            if manifest.get("status") != "complete":
                errors.append(f"{name}: pipeline chưa hoàn thành")
            if not manifest.get("output_hashes"):
                errors.append(f"{name}: thiếu hash kết quả")
            for relative, digest in manifest.get("output_hashes", {}).items():
                path = (ROOT / relative).resolve()
                if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or file_hash(path) != digest:
                    errors.append(f"{name}: kết quả không khớp manifest ({relative})")
        if model.get("config_hash") != file_hash(ROOT / "config/config.yaml"):
            errors.append("Cấu hình C2 đã thay đổi sau lần chạy")
        if backtest.get("backtest_config_hash") != file_hash(ROOT / "config/backtest.yaml"):
            errors.append("Quy tắc backtest đã thay đổi sau lần chạy")
        if split.get("prices_daily_hash") != file_hash(FILES["prices"]):
            errors.append("Giá C1 không khớp manifest chia mẫu")
        b08, nav = read_table("B08"), read_table("nav")
        if b08 is None or nav is None:
            return {"ok": False, "errors": errors + ["Thiếu B08 hoặc chuỗi NAV. Chạy lại pipeline."]}
        for asset in assets():
            meta = model["assets"][asset]
            if backtest["assets"][asset]["model_run_id"] != meta["model_run_id"]:
                errors.append(f"{asset}: backtest dùng model khác phiên hiện tại")
            for frame in (b08,):
                part = frame.loc[frame["asset"].eq(asset)]
                if part.empty or not part["model_run_id"].eq(meta["model_run_id"]).all():
                    errors.append(f"{asset}: B08 không khớp model")
            provenance = meta["c1_provenance"]
            if provenance["features_sha256"] != file_hash(asset_files(asset)["features"]):
                errors.append(f"{asset}: dữ liệu C1 đã đổi sau khi tính model")
            through = split["data_through_utc"][asset]
            if provenance["data_through_utc"] != through or backtest["data_through_utc"][asset] != through:
                errors.append(f"{asset}: ngày dữ liệu C1/C2/C3 không đồng bộ")
            if nav is None or nav.loc[nav["asset"].eq(asset)].empty:
                errors.append(f"{asset}: thiếu chuỗi NAV")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Không xác minh được bộ kết quả: {exc}")
    return {"ok": not errors, "errors": errors}


def research_status():
    """Research never blocks baseline charts; stale/unverified interpretation is withheld."""
    errors = []
    try:
        manifest = read_json("research_manifest")
        if not manifest or manifest.get("status") != "complete":
            return {
                "ok": False,
                "manifest": None,
                "errors": ["Nghiên cứu mở rộng chưa hoàn tất: python scripts/complete_research.py"],
            }
        for section in ("input_hashes", "source_hashes", "output_hashes"):
            if not manifest.get(section):
                errors.append(f"Research thiếu {section}")
            for relative, digest in manifest.get(section, {}).items():
                path = (ROOT / relative).resolve()
                if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or file_hash(path) != digest:
                    errors.append(f"Research không khớp phiên dữ liệu/source: {relative}")
        core = read_json("model_manifest")
        for asset in assets():
            if manifest["assets"][asset]["model_run_id"] != core["assets"][asset]["model_run_id"]:
                errors.append(f"{asset}: diễn giải kinh tế thuộc model cũ")
        return {"ok": not errors, "manifest": manifest if not errors else None, "errors": errors}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"ok": False, "manifest": None, "errors": [f"Không xác minh được research: {exc}"]}


def read_json(key):
    p = FILES[key]
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def read_table(key):
    p = FILES[key]
    return pd.read_csv(p) if p.exists() else None


def prices(asset):
    p = FILES["prices"]
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df = df.loc[df["asset"] == asset].copy()
    df["date"] = pd.to_datetime(df["date_utc"]).dt.tz_localize(None)
    return df.sort_values("date").reset_index(drop=True)


def features(asset):
    p = asset_files(asset)["features"]
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["date"] = pd.to_datetime(df["date_utc"]).dt.tz_localize(None)
    return df


def filtered(asset):
    """Xác suất FILTERED qua reader kiểm chứng của C2 (hash, schema, tổng xác suất, thời điểm).

    Trả về (frame, metadata, cảnh_báo, lỗi). Mô hình unstable được đọc ở chế độ nghiên cứu
    có xác nhận rõ, và cảnh báo được hiển thị trên giao diện.
    """
    if not asset_files(asset)["filtered"].exists() or not FILES["model_manifest"].exists():
        return None, None, [], "Chưa có xác suất filtered của C2"
    from src.models.handoff import UnstableModelWarning, load_filtered

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", UnstableModelWarning)
            frame, meta = load_filtered(CFG, asset, acknowledge_unstable=True)
    except (ValueError, KeyError) as exc:
        return None, None, [], f"Không đọc được xác suất filtered: {exc}"
    frame["date"] = pd.to_datetime(frame["date_utc"])
    notes = [str(w.message) for w in caught if issubclass(w.category, UnstableModelWarning)]
    return frame, meta, notes, None


def smoothed(asset):
    p = asset_files(asset)["smoothed"]
    if not p.exists():
        return None
    df = pd.read_csv(p)
    if not df["hindsight"].astype(bool).all() or not df["probability_type"].eq("smoothed").all():
        raise ValueError("File smoothed không đúng hợp đồng (hindsight=True, probability_type=smoothed)")
    df["date"] = pd.to_datetime(df["date_utc"])
    return df


def gmm(asset):
    """Nhãn GMM đối chứng (posterior từng ngày, không có cấu trúc Markov). None nếu chưa có file."""
    p = asset_files(asset)["gmm"]
    if not p.exists():
        return None, None
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["date_utc"])
    label_map = json.loads(df["label_map"].iloc[0]) if "label_map" in df and len(df) else None
    return df, label_map
