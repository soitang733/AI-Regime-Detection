import pandas as pd
import pytest

from src.research_v2.data import checked_daily_source, enforce_availability, validate_keys


def test_reject_future_snapshot_and_duplicate():
    d=pd.DataFrame({'asset':['BTC'],'date_utc':['2020-01-01'],'last':['2020-01-02T00:00:00Z']})
    with pytest.raises(ValueError,match='observation day'):
        checked_daily_source(d,'BTC','last',['funding_sum'])
    with pytest.raises(ValueError,match='duplicate'):
        validate_keys(pd.concat([d,d]),['asset','date_utc'])


def test_daily_aggregate_available_at_close():
    d=pd.DataFrame({'asset':['BTC','BTC'],'date_utc':['2020-01-01','2020-01-02'],
                    'last':['2020-01-01T16:00:00Z','2020-01-02 16:00:00.001000+00:00']})
    result=checked_daily_source(d,'BTC','last',['funding_sum'])
    assert result.funding_sum_available_at.iloc[0] == pd.Timestamp('2020-01-02T00:00:00Z')


def test_stale_mask_and_future_release_rejected():
    d=pd.DataFrame({'asset':['BTC'],'split':['train'],'decision_time_utc':['2020-01-10T00:00:00Z'],
                    'vix':[20.], 'vix_available_at':['2020-01-02T00:00:00Z'],'vix_obs_date':['2020-01-01']})
    clean,rows=enforce_availability(d,['vix'])
    assert pd.isna(clean.vix.iloc[0]) and rows[0]['stale_removed']==1
    d['vix_available_at']='2020-01-11T00:00:00Z'
    with pytest.raises(ValueError,match='invalid availability'):
        enforce_availability(d,['vix'])
