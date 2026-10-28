from datetime import datetime
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from biobeat.auth import get_access_token
from biobeat.config import load_device_ids, api_settings
from biobeat.demo import synthetic_measurements
from biobeat.errors import AuthenticationError, BioBeatError
from biobeat.fetch import get_all_measurements, fetch_data
from biobeat.utils import local_to_utc, normalize_measurements, convert_to_dataframe, export_csv


@pytest.fixture(autouse=True)
def configuration(monkeypatch):
    for key, value in {'SCOPE': 'fictional-scope', 'CLIENTIDHASH': 'fictional-credential',
                       'CUSTOMERPARAMETER3': 'measurements', 'CUSTOMERPARAMETER4': 'X-Token'}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv('BIOBEAT_DEVICE_IDS', raising=False)


def response(status=200, payload=None):
    return Mock(status_code=status, json=Mock(return_value=payload))


def test_devices(monkeypatch):
    assert load_device_ids() == []
    monkeypatch.setenv('BIOBEAT_DEVICE_IDS', 'DEMO-001, DEMO-002, DEMO-001')
    assert load_device_ids() == ['DEMO-001', 'DEMO-002']
    for value in ['a,,b', '../bad', 'a\nb']:
        monkeypatch.setenv('BIOBEAT_DEVICE_IDS', value)
        with pytest.raises(BioBeatError):
            load_device_ids()


@pytest.mark.parametrize('key', ['SCOPE', 'CLIENTIDHASH'])
def test_missing_auth_env(monkeypatch, key):
    monkeypatch.delenv(key)
    with pytest.raises(BioBeatError, match=key):
        get_access_token()


@pytest.mark.parametrize('endpoint,header', [('https://evil.invalid', 'X-Token'), ('../path', 'X-Token'), ('path', 'bad\nheader')])
def test_api_configuration(monkeypatch, endpoint, header):
    monkeypatch.setenv('CUSTOMERPARAMETER3', endpoint)
    monkeypatch.setenv('CUSTOMERPARAMETER4', header)
    with pytest.raises(BioBeatError):
        api_settings()


@pytest.mark.parametrize('status', [400, 401, 403, 500, 302])
def test_auth_failure(monkeypatch, status):
    post = Mock(return_value=response(status, {'secret': 'must-never-appear'}))
    monkeypatch.setattr('biobeat.auth.requests.post', post)
    with pytest.raises(BioBeatError) as error:
        get_access_token()
    assert 'must-never-appear' not in str(error.value)
    assert post.call_args.kwargs['timeout'] == (5, 30)
    assert post.call_args.kwargs['allow_redirects'] is False


@pytest.mark.parametrize('payload', [None, [], {}, {'access_token': ''}, {'access_token': 123}])
def test_bad_token(monkeypatch, payload):
    monkeypatch.setattr('biobeat.auth.requests.post', Mock(return_value=response(payload=payload)))
    with pytest.raises(AuthenticationError):
        get_access_token()


def test_token_success(monkeypatch):
    monkeypatch.setattr('biobeat.auth.requests.post', Mock(return_value=response(payload={'access_token': 'fictional'})))
    assert get_access_token() == 'fictional'


@pytest.mark.parametrize('method', ['post', 'get'])
def test_transport_errors_are_safe(monkeypatch, method):
    monkeypatch.setattr(f'requests.{method}', Mock(side_effect=requests.Timeout('private-url-and-token')))
    with pytest.raises(BioBeatError) as error:
        get_access_token() if method == 'post' else fetch_data('DEMO-001', 'start', 'end', 'fictional')
    assert 'private-url' not in str(error.value)


@pytest.mark.parametrize('method', ['post', 'get'])
def test_invalid_json(monkeypatch, method):
    result = response()
    result.json.side_effect = ValueError('private-data')
    monkeypatch.setattr(f'requests.{method}', Mock(return_value=result))
    with pytest.raises(BioBeatError, match='invalid JSON'):
        get_access_token() if method == 'post' else fetch_data('DEMO-001', 'start', 'end', 'fictional')


@pytest.mark.parametrize('status', [401, 403, 429, 500, 302])
def test_fetch_failure(monkeypatch, status):
    monkeypatch.setattr('requests.get', Mock(return_value=response(status)))
    with pytest.raises(BioBeatError):
        fetch_data('DEMO-001', 'start', 'end', 'fictional')


@pytest.mark.parametrize('payload', [None, [], {}, {'data': None}, {'data': ['bad']}, {'data': [], 'more_records': 'true'}])
def test_malformed_data(monkeypatch, payload):
    monkeypatch.setattr('requests.get', Mock(return_value=response(payload=payload)))
    with pytest.raises(BioBeatError):
        fetch_data('DEMO-001', 'start', 'end', 'fictional')


START, NEXT, END = '2026-01-01T00:00:00Z', '2026-01-01T01:00:00Z', '2026-01-01T02:00:00Z'


def test_pagination(monkeypatch):
    get = Mock(side_effect=[response(payload={'data': [{'hr': 70}], 'more_records': True, 'next_page_datetime': NEXT}),
                            response(payload={'data': [{'hr': 71}]})])
    monkeypatch.setattr('requests.get', get)
    assert len(get_all_measurements('DEMO-001', START, END, 'fictional')) == 2
    assert get.call_args.kwargs['params']['datetime_start'] == NEXT
    assert get.call_args.kwargs['timeout'] == (5, 30)


@pytest.mark.parametrize('cursor', [START, 'invalid', None, '2027-01-01T00:00:00Z'])
def test_pagination_does_not_loop(monkeypatch, cursor):
    monkeypatch.setattr('requests.get', Mock(return_value=response(payload={
        'data': [{'hr': 70}], 'more_records': True, 'next_page_datetime': cursor})))
    with pytest.raises(BioBeatError):
        get_all_measurements('DEMO-001', START, END, 'fictional')


def test_empty_and_cancelled(monkeypatch):
    get = Mock(return_value=response(payload={'data': []}))
    monkeypatch.setattr('requests.get', get)
    assert get_all_measurements('DEMO-001', START, END, 'fictional') == []
    with pytest.raises(BioBeatError, match='cancelled'):
        get_all_measurements('DEMO-001', START, END, 'fictional', cancelled=lambda: True)
    assert get.call_count == 1


def test_page_limit(monkeypatch):
    monkeypatch.setattr('biobeat.fetch.MAX_PAGES', 1)
    monkeypatch.setattr('requests.get', Mock(return_value=response(payload={
        'data': [{}], 'more_records': True, 'next_page_datetime': NEXT})))
    with pytest.raises(BioBeatError, match='limit'):
        get_all_measurements('DEMO-001', START, END, 'fictional')


def test_timezone():
    assert local_to_utc(datetime(2026, 1, 15, 12), 'Europe/Zurich').hour == 11
    assert local_to_utc(datetime(2026, 7, 15, 12), 'Europe/Zurich').hour == 10
    for value in [datetime(2026, 3, 29, 2, 30), datetime(2026, 10, 25, 2, 30)]:
        with pytest.raises(BioBeatError):
            local_to_utc(value, 'Europe/Zurich')


def test_normalization_and_export(tmp_path):
    df = normalize_measurements(synthetic_measurements(), 'Europe/Zurich')
    assert len(df) == 72
    assert df.datetime_tz.iloc[0].hour == 9
    assert str(df.datetime_utc.dt.tz) == 'UTC'
    path = export_csv(df, tmp_path / 'synthetic.csv')
    result = pd.read_csv(path)
    assert len(result) == 72
    assert result.hr.iloc[0] == df.hr.iloc[0]
    assert 'datetime_utc' in result
    assert normalize_measurements([], 'UTC').empty
    partial = normalize_measurements([{'datetime': START, 'hr': '70'}], 'UTC')
    assert partial.hr.iloc[0] == 70
    assert pd.isna(partial.sbp.iloc[0])
    assert 'nested.value' in convert_to_dataframe([{'nested': {'value': 1}}])


@pytest.mark.parametrize('records', [{}, [1], [{'hr': 70}], [{'datetime': 'invalid'}]])
def test_invalid_normalization(records):
    with pytest.raises(BioBeatError):
        normalize_measurements(records, 'UTC')


def test_empty_page_with_continuation_is_rejected(monkeypatch):
    monkeypatch.setattr('requests.get', Mock(return_value=response(payload={
        'data': [], 'more_records': True, 'next_page_datetime': NEXT})))
    with pytest.raises(BioBeatError, match='did not advance'):
        get_all_measurements('DEMO-001', START, END, 'fictional')


@pytest.mark.parametrize('key', ['CUSTOMERPARAMETER3', 'CUSTOMERPARAMETER4'])
def test_missing_api_env(monkeypatch, key):
    monkeypatch.delenv(key)
    with pytest.raises(BioBeatError, match=key):
        api_settings()
