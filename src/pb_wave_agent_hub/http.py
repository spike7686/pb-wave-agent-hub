from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request_json(url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None, timeout: int = 30):
    if params:
        query = urlencode({k: v for k, v in params.items() if v is not None})
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{query}"
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

