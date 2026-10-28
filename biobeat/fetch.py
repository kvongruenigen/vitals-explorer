"""Bounded, cancellable pagination for the existing BioBeat API contract."""
from datetime import datetime

import requests

from biobeat.auth import REQUEST_TIMEOUT
from biobeat.config import api_settings
from biobeat.errors import AuthenticationError, BioBeatError

MAX_PAGES = 1000


def _timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed
    except (ValueError, TypeError, AttributeError):
        raise BioBeatError('API pagination requires valid timezone-aware timestamps.') from None


def fetch_data(device_id, datetime_start, datetime_end, access_token):
    endpoint, header_key = api_settings()
    try:
        response = requests.get(
            f'https://data-api.eu.bio-beat.cloud/{endpoint}',
            params={'device_id': device_id, 'datetime_start': datetime_start,
                    'datetime_end': datetime_end},
            headers={header_key: access_token}, timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
    except requests.RequestException:
        raise BioBeatError('Measurement service unavailable; check your connection and retry.') from None
    if response.status_code in (401, 403):
        raise AuthenticationError('Measurement access denied; verify credentials and device permissions.')
    if response.status_code != 200:
        raise BioBeatError(f'Measurement service returned HTTP {response.status_code}.')
    try:
        payload = response.json()
    except ValueError:
        raise BioBeatError('Measurement service returned invalid JSON.') from None
    if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
        raise BioBeatError('Measurement response must contain a data list.')
    if any(not isinstance(row, dict) for row in payload['data']):
        raise BioBeatError('Measurement response contains invalid records.')
    if not isinstance(payload.get('more_records', False), bool):
        raise BioBeatError('Measurement response has an invalid pagination flag.')
    return payload


def get_all_measurements(device_id, datetime_start, datetime_end, access_token, cancelled=None):
    all_data = []
    current_start = datetime_start
    end = _timestamp(datetime_end)
    for _ in range(MAX_PAGES):
        if cancelled and cancelled():
            raise BioBeatError('Retrieval cancelled.')
        result = fetch_data(device_id, current_start, datetime_end, access_token)
        all_data.extend(result['data'])
        if not result.get('more_records', False):
            return all_data
        next_start = result.get('next_page_datetime')
        if not result['data'] or not (_timestamp(current_start) < _timestamp(next_start) <= end):
            raise BioBeatError('API pagination did not advance; retrieval stopped.')
        current_start = next_start
    raise BioBeatError('API pagination limit reached; select a shorter time range.')
