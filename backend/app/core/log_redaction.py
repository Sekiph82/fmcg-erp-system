"""Keep URL secrets out of access logs (M44.S01.T014).

Africa's Talking voice callbacks are unsigned, so their secret travels as ?token=… in the URL by provider design;
uvicorn's access log would print it. This filter masks token-like query values in every access-log line."""
from __future__ import annotations

import logging
import re

_SECRET_QS = re.compile(r"([?&](?:token|access_token|secret|key)=)[^&\s\"]+", re.IGNORECASE)


def redact(text: str) -> str:
    return _SECRET_QS.sub(r"\1[REDACTED]", text)


class RedactQuerySecrets(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        return True


def install() -> None:
    for name in ("uvicorn.access", "uvicorn.error"):
        lg = logging.getLogger(name)
        if not any(isinstance(f, RedactQuerySecrets) for f in lg.filters):
            lg.addFilter(RedactQuerySecrets())
