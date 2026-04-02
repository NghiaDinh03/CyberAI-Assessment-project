"""Centralised SlowAPI rate-limiter instance.

Import `limiter` and `_has_rate_limit` from here instead of from `main`
to break the circular-import chain:
    main → routes/chat → main   (was circular)
    main → routes/chat → core/limiter   (clean)
"""

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    _has_rate_limit = True
except ImportError:
    limiter = None  # type: ignore[assignment]
    _has_rate_limit = False
