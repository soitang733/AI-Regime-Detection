import numpy as np
import pandas as pd
import pytest

from scripts.reproduce_v2 import compare_csv
from src.research_v2.review import paired_interval, path_metrics, probability_error
from src.research_v2.rolling_benchmarks import development_fold


def test_drawdown_includes_initial_wealth_and_turnover_units():
    result = path_metrics(np.array([-.1, .05]), np.array([1., 0.]))
    assert result['max_drawdown'] == pytest.approx(-.1)
    assert result['annual_turnover'] == pytest.approx(182.5)


def test_paired_bootstrap_keeps_shared_shocks_paired():
    left = np.array([100., -50., 20., -10.])
    indices = np.array([[0, 1, 2, 3], [3, 3, 0, 1], [1, 2, 1, 2]])
    result = paired_interval(left + .25, left, indices)
    assert result['point'] == result['ci_low'] == result['ci_high'] == .25


@pytest.mark.parametrize('invalid', [np.array([[.6, .6]]), np.array([[np.nan, 1]]), np.array([[-.01, 1.01]])])
def test_invalid_probabilities_are_rejected(invalid):
    with pytest.raises(ValueError):
        probability_error(invalid)


def test_transition_tensor_normalizes_destinations():
    assert probability_error(np.array([[[.9, .1], [.3, .7]], [[.1, .9], [.6, .4]]])) < 1e-12


def test_rolling_fold_discards_test_even_when_date_would_fit():
    frame = pd.DataFrame({'date_utc': ['2020-01-01', '2021-06-01', '2021-06-02', '2026-01-01'],
                          'split': ['train', 'train', 'test', 'test'], 'value': [1, 2, 999, 999]})
    used = development_fold(frame, 0)
    assert used.value.tolist() == [1, 2]
    assert used.split.tolist() == ['train', 'validation']


def test_reproduction_comparison_rejects_changed_metric_and_schema(tmp_path):
    original, reproduced = tmp_path / 'original.csv', tmp_path / 'reproduced.csv'
    pd.DataFrame({'metric': [1., np.nan], 'state': ['Calm', 'Stress']}).to_csv(original, index=False)
    pd.DataFrame({'metric': [1., np.nan], 'state': ['Calm', 'Stress']}).to_csv(reproduced, index=False)
    assert compare_csv(original, reproduced)['passed']
    pd.DataFrame({'metric': [2., np.nan], 'state': ['Calm', 'Stress']}).to_csv(reproduced, index=False)
    assert not compare_csv(original, reproduced)['passed']
    pd.DataFrame({'different': [1., np.nan]}).to_csv(reproduced, index=False)
    assert not compare_csv(original, reproduced)['passed']
