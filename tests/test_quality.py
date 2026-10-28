from datetime import timedelta

import pandas as pd

from biobeat.demo import DEMO_START, synthetic_measurements
from biobeat.quality import summarize_quality
from biobeat.utils import normalize_measurements


def test_complete_sample():
    result = summarize_quality(normalize_measurements(synthetic_measurements(), 'Europe/Zurich'))
    assert result.records == 72
    assert result.missing == result.duplicates == result.long_intervals == 0
    assert result.median_seconds == 300
    assert result.first.hour == 9
    assert 'not confirmed missing measurements' in result.describe('Europe/Zurich')


def test_missing_duplicates_and_long_intervals():
    records = [{'datetime': (DEMO_START + timedelta(minutes=minute)).isoformat(), 'hr': 70}
               for minute in [0, 5, 5, 10, 40]]
    result = summarize_quality(normalize_measurements(records, 'UTC'))
    assert result.records == 5
    assert result.missing == 25
    assert result.duplicates == 1
    assert result.median_seconds == 300
    assert result.long_intervals == 1


def test_insufficient_and_empty():
    assert summarize_quality(pd.DataFrame()).describe('UTC') == 'No measurements loaded.'
    for count in [1, 2]:
        result = summarize_quality(normalize_measurements(synthetic_measurements()[:count], 'UTC'))
        assert result.median_seconds is None
        assert 'Insufficient intervals' in result.describe('UTC')
    only_duplicates = normalize_measurements([synthetic_measurements()[0]] * 4, 'UTC')
    result = summarize_quality(only_duplicates)
    assert result.duplicates == 3 and result.median_seconds is None


def test_timezone_does_not_change_interval_statistics():
    utc = summarize_quality(normalize_measurements(synthetic_measurements(), 'UTC'))
    zurich = summarize_quality(normalize_measurements(synthetic_measurements(), 'Europe/Zurich'))
    assert utc.median_seconds == zurich.median_seconds
    assert utc.first == zurich.first
    assert utc.first.hour != zurich.first.hour
