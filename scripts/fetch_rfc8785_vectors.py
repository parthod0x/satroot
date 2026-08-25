"""Fetch the published RFC 8785 conformance vectors.

Not vendored, to avoid redistributing another project's test data. The
suite lives at https://github.com/cyberphone/json-canonicalization and is
the reference test data referenced by implementers of RFC 8785.

    python scripts/fetch_rfc8785_vectors.py

Writes into tests/vectors/rfc8785/, which is gitignored. Tests that use
these vectors skip when they are absent.
"""

from __future__ import annotations

import pathlib
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/cyberphone/json-canonicalization/master/testdata"
FILES = ("arrays", "structures", "unicode", "values", "weird")
DEST = pathlib.Path(__file__).resolve().parents[1] / "tests" / "vectors" / "rfc8785"


def main() -> int:
    for kind in ("input", "output"):
        (DEST / kind).mkdir(parents=True, exist_ok=True)
        for name in FILES:
            url = f"{BASE}/{kind}/{name}.json"
            target = DEST / kind / f"{name}.json"
            with urllib.request.urlopen(url, timeout=30) as response:
                target.write_bytes(response.read())
            print(f"  {kind}/{name}.json")
    print(f"\nfetched into {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
