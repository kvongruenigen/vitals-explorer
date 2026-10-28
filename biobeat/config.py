"""Small environment-based configuration (including a local, ignored .env)."""
import os
import re

from biobeat.errors import BioBeatError


def required_env(name):
    value = os.environ.get(name, '').strip()
    if not value or value.startswith('REPLACE_'):
        raise BioBeatError(f'Configure {name} in your local .env or environment.')
    return value


def load_device_ids():
    values = os.environ.get('BIOBEAT_DEVICE_IDS', '').strip()
    if not values:
        return []
    devices = [value.strip() for value in values.split(',')]
    if any(not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value) for value in devices):
        raise BioBeatError('BIOBEAT_DEVICE_IDS must be comma-separated IDs using letters, digits, underscores or hyphens.')
    return list(dict.fromkeys(devices))


def api_settings():
    endpoint = required_env('CUSTOMERPARAMETER3')
    header = required_env('CUSTOMERPARAMETER4')
    if not re.fullmatch(r'[A-Za-z0-9_/-]+', endpoint) or '..' in endpoint:
        raise BioBeatError('CUSTOMERPARAMETER3 must be a relative API path.')
    if not re.fullmatch(r'[A-Za-z0-9-]+', header):
        raise BioBeatError('CUSTOMERPARAMETER4 must be an HTTP header name.')
    return endpoint.lstrip('/'), header
