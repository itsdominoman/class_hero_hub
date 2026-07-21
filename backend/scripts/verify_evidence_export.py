#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.safeguarding_service import verify_evidence_archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a CHH evidence package without extracting it")
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--artifact-sha256")
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args()
    result = verify_evidence_archive(
        args.artifact,
        expected_artifact_sha256=args.artifact_sha256,
        expected_manifest_sha256=args.manifest_sha256,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
