"""Regression coverage for refresh, result integrity, caching and calendar gaps."""

import hashlib
import json
import shutil
import sys

import numpy as np
import pandas as pd
import pytest

from src.data.refresh import append_closed_candles
from src.utils.config import ROOT
from dashboard import v2_service

sys.path.insert(0, str(ROOT / "dashboard"))
import result_service as rs
from analytics import forward_returns


def test_refresh_preserves_existing_history(raw):
    original = raw["BTC"].tail(8).reset_index(drop=True)
    incoming = original.tail(4).copy()
    incoming.loc[incoming.index[0], "close"] = -1  # Adversarial historical revision.
    result = append_closed_candles(original.head(6), incoming)
    pd.testing.assert_frame_equal(result, original)


def test_refresh_rejects_duplicate_dates(raw):
    incoming = raw["BTC"].tail(2)
    with pytest.raises(ValueError, match="Duplicate"):
        append_closed_candles(pd.DataFrame(), pd.concat([incoming, incoming]))


@pytest.mark.parametrize("days,status,lag", [(1, "current", 0), (4, "stale", 3), (0, "invalid", 0)])
def test_freshness_uses_last_closed_utc_day(days, status, lag):
    through = rs.read_json("split_manifest")["data_through_utc"]["BTC"]
    result = rs.freshness("BTC", pd.Timestamp(through, tz="UTC") + pd.Timedelta(days=days, hours=12))
    assert result["status"] == status and result["lag_days"] == lag


def test_real_bundle_passes_integrity():
    result = rs.validate_bundle()
    assert result["ok"], result["errors"]


def test_changed_price_hash_is_rejected(monkeypatch):
    original = rs.file_hash
    monkeypatch.setattr(rs, "file_hash", lambda p: "tampered" if p == rs.FILES["prices"] else original(p))
    assert not rs.validate_bundle()["ok"]


def test_missing_b08_is_rejected_without_crashing(monkeypatch):
    original = rs.read_table
    monkeypatch.setattr(rs, "read_table", lambda key: None if key == "B08" else original(key))
    assert not rs.validate_bundle()["ok"]


def test_version_changes_when_dependency_changes(tmp_path, monkeypatch):
    dependency = tmp_path / "result.json"
    dependency.write_text("{}", encoding="utf-8")
    monkeypatch.setitem(rs.FILES, "test_dependency", dependency)
    before = rs.dataset_version()
    dependency.write_text('{"updated":true}', encoding="utf-8")
    assert rs.dataset_version() != before


def test_current_reader_reloads_verified_changes_and_rejects_unverified_changes(tmp_path):
    folder = tmp_path/'outputs/research_v2/m4_evaluation'
    folder.mkdir(parents=True)
    source = ROOT/'outputs/research_v2/m4_evaluation'
    for name in ['manifest.json', 'historical_metrics.csv']:
        shutil.copy2(source/name, folder/name)
    before = v2_service.table('m4_evaluation', 'historical_metrics.csv', root=tmp_path)
    updated = before.assign(verification_marker='updated_fixture')
    path = folder/'historical_metrics.csv'
    updated.to_csv(path, index=False)
    with pytest.raises(ValueError, match='không khớp manifest'):
        v2_service.table('m4_evaluation', 'historical_metrics.csv', root=tmp_path)
    manifest = json.loads((folder/'manifest.json').read_text())
    manifest['files_sha256'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (folder/'manifest.json').write_text(json.dumps(manifest))
    result = v2_service.table('m4_evaluation', path.name, root=tmp_path)
    assert result.verification_marker.eq('updated_fixture').all()
    pd.testing.assert_frame_equal(result.drop(columns='verification_marker'), before)


def test_forward_returns_do_not_cross_missing_calendar_day(feats):
    frame = feats["BTC"].tail(15).copy().reset_index(drop=True)
    frame["date"] = pd.to_datetime(frame["date_utc"])
    frame["state_id"] = np.arange(len(frame)) % 2
    frame = frame.drop(index=5).reset_index(drop=True)
    result = forward_returns(frame, horizons=(1, 5))
    assert pd.isna(result.loc[4, "fwd_1"])
    assert not result.loc[5, "entry"]
    assert pd.isna(result.loc[0, "fwd_5"])
    assert result.loc[5, "fwd_1"] == pytest.approx(np.expm1(frame.loc[6, "log_return"]))
