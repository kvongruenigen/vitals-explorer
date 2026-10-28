"""Safe, user-facing errors; never include request or response contents."""


class BioBeatError(Exception):
    """An actionable configuration, transport, or data error."""


class AuthenticationError(BioBeatError):
    """Authorization failed or the token response is invalid."""
