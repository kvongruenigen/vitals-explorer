"""Normalization, strict timezone conversion, and CSV export."""
from pathlib import Path
import re

import pandas as pd
import pytz

from biobeat.errors import BioBeatError

VITALS = ['sbp', 'dbp', 'hr', 'spo2', 'rr', 'temp']
COLUMNS = ['timezone', 'datetime_tz', *VITALS, 'datetime_utc', 'battery', 'offline_records']


def local_to_utc(value, timezone):
    try:
        return pytz.timezone(timezone).localize(value, is_dst=None).astimezone(pytz.utc)
    except (pytz.UnknownTimeZoneError, pytz.InvalidTimeError):
        raise BioBeatError('Selected local time is invalid or ambiguous; choose a time outside the daylight-saving transition.') from None


def convert_to_dataframe(json_data):
    if not isinstance(json_data, list) or any(not isinstance(row, dict) for row in json_data):
        raise BioBeatError('Measurements must be a list of records.')
    return pd.json_normalize(json_data)


def normalize_measurements(records, timezone):
    df = convert_to_dataframe(records)
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    if 'datetime' not in df:
        raise BioBeatError('Measurements are missing timestamps.')
    df['datetime_utc'] = pd.to_datetime(df.pop('datetime'), utc=True, errors='coerce')
    if df['datetime_utc'].isna().any():
        raise BioBeatError('Measurements contain invalid timestamps.')
    df['timezone'] = timezone
    df['datetime_tz'] = df['datetime_utc'].dt.tz_convert(timezone)
    for column in [*VITALS, 'battery', 'offline_records']:
        df[column] = pd.to_numeric(df[column], errors='coerce') if column in df else float('nan')
    return df.reindex(columns=COLUMNS).sort_values('datetime_utc').reset_index(drop=True)


def export_csv(df, path):
    df.to_csv(path, index=False, encoding='utf-8')
    return Path(path)


def save_dataframe_csv(df, device_id, start, end):
    directory = Path('Recordings')
    directory.mkdir(exist_ok=True)
    name = re.sub(r'[^A-Za-z0-9_.-]', '-', f'measurements_{device_id}_{start}_{end}')
    return export_csv(df, directory / f'{name}.csv')
