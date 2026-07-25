#!/usr/bin/env python3
from __future__ import annotations

import sys

from app.operational_health import worker_heartbeat_is_current


if len(sys.argv) != 2 or not worker_heartbeat_is_current(sys.argv[1]):
    raise SystemExit(1)
