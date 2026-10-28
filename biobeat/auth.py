"""OAuth client credentials authentication; errors deliberately omit secrets."""
import requests

from biobeat.config import required_env
from biobeat.errors import AuthenticationError, BioBeatError

REQUEST_TIMEOUT = (5, 30)  # connect and read seconds
TOKEN_URL = 'https://biobeatloginprod.auth.eu-west-1.amazoncognito.com/oauth2/token'


def get_access_token():
    scope = required_env('SCOPE')
    credential = required_env('CLIENTIDHASH')
    try:
        response = requests.post(
            TOKEN_URL,
            params={'grant_type': 'client_credentials', 'scope': scope},
            headers={'Authorization': f'Basic {credential}',
                     'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=REQUEST_TIMEOUT, allow_redirects=False,
        )
    except requests.RequestException:
        raise BioBeatError('Authentication service unavailable; check your connection and retry.') from None
    if response.status_code in (400, 401, 403):
        raise AuthenticationError('Authentication failed; verify authorized API credentials.')
    if response.status_code != 200:
        raise BioBeatError(f'Authentication service returned HTTP {response.status_code}.')
    try:
        payload = response.json()
    except ValueError:
        raise AuthenticationError('Authentication service returned invalid JSON.') from None
    token = payload.get('access_token') if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token.strip():
        raise AuthenticationError('Authentication service did not return an access token.')
    return token
