import re
from typing import Optional

from .core.data_access import find_asignatura_id

ID_RE = re.compile(r"\b(\d{6,9})\b")


def quick_guess_asig(q: str) -> Optional[str]:
    if not q:
        return None
    m = ID_RE.search(q)
    if m:
        return m.group(1)
    # entre comillas
    m2 = re.search(r'"([^"]+)"', q)
    if m2:
        return find_asignatura_id(m2.group(1))
    return None
