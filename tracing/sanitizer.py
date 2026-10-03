"""Strip secrets from trace payloads (P1)."""
import re
from typing import Any
_KEYS = re.compile(r"(key|secret|password|authorization|api)", re.I)
_VAL = re.compile(r"(sk-[A-Za-z0-9]{8,}|eyJ[A-Za-z0-9_\-]{10,}|postgres(ql)?://\S+)")

def sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if _KEYS.search(k) else sanitize(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, str):
        return _VAL.sub("[REDACTED]", obj)
    return obj
