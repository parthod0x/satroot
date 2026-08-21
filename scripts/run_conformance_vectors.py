"""Run the conformance vector corpus against a SATROOT-1 implementation.

Replays every vector in vectors/ and checks the recorded expectations:
valid vectors must reproduce the exact final state hash, balances, and
record count; rejection vectors must fail replay. Exits non-zero on any
mismatch.

This runner exercises the reference implementation. A second
implementation demonstrates conformance by consuming the same JSON
corpus: replay `events` under `scheme` (fixed key material is documented
in vectors/README.md) and compare against `expect`.

Usage: python scripts/run_conformance_vectors.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import satroot1 as sr

FIXED_ED25519_PRIVATE = {"issuer-key": "11" * 32, "alice-key": "22" * 32}
FIXED_HMAC_SECRETS = {"issuer-key": "33" * 32, "alice-key": "44" * 32}


def verifier_for(scheme: str):
    if scheme == "demo":
        return sr.demo_signature_verifier
    if scheme == "ed25519":
        return sr.make_ed25519_verifier(
            sr.derive_ed25519_public_keys(FIXED_ED25519_PRIVATE)
        )
    if scheme == "hmac-sha256":
        return sr.make_hmac_sha256_verifier(FIXED_HMAC_SECRETS)
    raise ValueError(f"unknown scheme in vector: {scheme}")


def check_vector(vector: dict) -> list[str]:
    problems: list[str] = []
    verifier = verifier_for(vector["scheme"])
    expect = vector["expect"]
    try:
        state = sr.replay(vector["events"], verifier=verifier)
    except sr.SatRootError as exc:
        if expect["ok"]:
            problems.append(f"expected success, replay failed: {exc}")
        return problems

    if not expect["ok"]:
        problems.append("expected rejection, but replay succeeded")
        return problems

    snapshot = state.snapshot()
    if state.state_hash() != expect["final_state_hash"]:
        problems.append(
            f"state hash mismatch: {state.state_hash()} != {expect['final_state_hash']}"
        )
    if snapshot["balances"] != expect["balances"]:
        problems.append(f"balances mismatch: {snapshot['balances']}")
    if len(vector["events"]) != expect["record_count"]:
        problems.append("record count mismatch")
    return problems


def main() -> int:
    vector_paths = sorted((REPO_ROOT / "vectors").glob("*.json"))
    if not vector_paths:
        print("no vectors found under vectors/", file=sys.stderr)
        return 1
    failures = 0
    for path in vector_paths:
        vector = json.loads(path.read_text(encoding="utf-8"))
        problems = check_vector(vector)
        status = "ok" if not problems else "FAIL"
        print(f"{status:4} {vector['name']}")
        for problem in problems:
            print(f"       - {problem}")
            failures += 1
    print(f"{len(vector_paths)} vectors, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
