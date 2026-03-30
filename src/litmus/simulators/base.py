from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


class HttpTimeoutError(Exception):
    pass


class HttpConnectionRefusedError(Exception):
    pass


@dataclass(slots=True)
class SimulatedHttpResponse:
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    json_body: Any | None = None
    text_body: str | None = None
    latency_ms: int = 0

    def content_bytes(self) -> bytes:
        if self.json_body is not None:
            return json.dumps(self.json_body).encode("utf-8")
        if self.text_body is not None:
            return self.text_body.encode("utf-8")
        return b""
