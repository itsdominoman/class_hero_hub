"""Low-cardinality, payload-free process metrics for Messaging v1 HTTP paths."""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send


_lock = threading.Lock()
_counts: dict[tuple[str, int], int] = defaultdict(int)
_latency_ms_sum: dict[str, float] = defaultdict(float)
_latency_ms_max: dict[str, float] = defaultdict(float)


def operation_label(path: str, method: str) -> str | None:
    if path.startswith("/api/safeguarding"):
        return "safeguarding"
    if path.startswith("/api/school/operations"):
        return "operations"
    if "/messaging" not in path:
        return None
    if "/media" in path:
        return "media"
    if "/voice-media" in path:
        return "voice_media"
    if "/acknowledgements" in path:
        return "receipt"
    if path.endswith("/messages") and method == "POST":
        return "send"
    if path.startswith("/api/integrations/fhh"):
        return "fhh_bridge"
    return "timeline"


def snapshot() -> dict[str, Any]:
    with _lock:
        labels = sorted({label for label, _status in _counts})
        return {
            label: {
                "requests": sum(value for (item, _status), value in _counts.items() if item == label),
                "denied": sum(value for (item, status), value in _counts.items() if item == label and status in (401, 403)),
                "errors": sum(value for (item, status), value in _counts.items() if item == label and status >= 500),
                "average_latency_ms": round(
                    _latency_ms_sum[label] / max(sum(value for (item, _status), value in _counts.items() if item == label), 1), 2
                ),
                "max_latency_ms": round(_latency_ms_max[label], 2),
            }
            for label in labels
        }


class MessagingMetricsMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        label = operation_label(str(scope.get("path", "")), str(scope.get("method", "GET")))
        if label is None:
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status_code = 500

        async def capture(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, capture)
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            with _lock:
                _counts[(label, status_code)] += 1
                _latency_ms_sum[label] += elapsed
                _latency_ms_max[label] = max(_latency_ms_max[label], elapsed)
