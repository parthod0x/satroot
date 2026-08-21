"""Regenerate the conformance vector corpus under vectors/.

Deterministic by construction: fixed key material, no timestamps, and
ed25519 (RFC 8032) signs deterministically — running this twice produces
byte-identical output. Vectors use placeholder roots only.

Usage: python scripts/generate_conformance_vectors.py
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import satroot1 as sr

VECTORS_DIR = REPO_ROOT / "vectors"

FIXED_ROOT = "ab" * 32 + ":0"
FIXED_ED25519_PRIVATE = {"issuer-key": "11" * 32, "alice-key": "22" * 32}
FIXED_HMAC_SECRETS = {"issuer-key": "33" * 32, "alice-key": "44" * 32}
SIGNER_KEY_IDS = {"issuer": "issuer-key", "alice": "alice-key"}


def _genesis(**overrides):
    kwargs = dict(
        symbol="VEC1",
        name="Conformance vector unit",
        root_id=FIXED_ROOT,
        mint_authority="issuer",
        decimals=0,
        initial_balance="1000",
        nonce="satroot-scaffold-0000000000000000",  # fixed for reproducibility
    )
    kwargs.update(overrides)
    return sr.scaffold_genesis_record(**kwargs)


def _signing_context(scheme):
    if scheme == "demo":
        return None, sr.demo_signature_verifier
    if scheme == "ed25519":
        signer = sr.make_ed25519_signer(FIXED_ED25519_PRIVATE)
        verifier = sr.make_ed25519_verifier(
            sr.derive_ed25519_public_keys(FIXED_ED25519_PRIVATE)
        )
        return signer, verifier
    if scheme == "hmac-sha256":
        signer = sr.make_hmac_sha256_signer(FIXED_HMAC_SECRETS)
        verifier = sr.make_hmac_sha256_verifier(FIXED_HMAC_SECRETS)
        return signer, verifier
    raise ValueError(scheme)


def _build_ledger(scheme, actions):
    """genesis + a list of (action_kwargs) appended via the reference path."""
    signer, verifier = _signing_context(scheme)
    genesis = _genesis()
    events = [
        sr.sign_event_record(
            genesis, scheme=scheme, key_id=SIGNER_KEY_IDS["issuer"], signer=signer
        )
    ]
    for kwargs in actions:
        event = sr.scaffold_event_from_ledger(events, verifier=verifier, **kwargs)
        events = sr.append_signed_event_to_ledger(
            events,
            event,
            scheme=scheme,
            signer_key_ids=SIGNER_KEY_IDS,
            signer=signer,
            verifier=verifier,
        )
    return events, verifier


def _expect_ok(events, verifier):
    state = sr.replay(events, verifier=verifier)
    snapshot = state.snapshot()
    return {
        "ok": True,
        "final_state_hash": state.state_hash(),
        "balances": snapshot["balances"],
        "record_count": len(events),
    }


def _expect_error(events, verifier, note):
    try:
        sr.replay(events, verifier=verifier)
    except sr.SatRootError as exc:
        return {"ok": False, "reference_error": str(exc), "note": note}
    raise AssertionError(f"vector expected to fail but replayed cleanly: {note}")


def build_vectors():
    vectors = []

    def add(name, description, scheme, events, expect):
        vectors.append(
            {
                "vector_format": "satroot1-conformance/1",
                "name": name,
                "description": description,
                "scheme": scheme,
                "events": events,
                "expect": expect,
            }
        )

    TRANSFER = dict(
        action="transfer", signer="issuer", from_account="issuer",
        to_account="alice", amount="400",
    )
    BURN = dict(action="burn", signer="alice", from_account="alice", amount="150")
    MINT = dict(action="mint", signer="issuer", to_account="alice", amount="50")

    # -- valid ledgers across all three schemes --------------------------
    for scheme in ("demo", "hmac-sha256", "ed25519"):
        events, verifier = _build_ledger(scheme, [TRANSFER, BURN, MINT])
        add(
            f"valid-lifecycle-{scheme}",
            "genesis, transfer, burn, mint — full happy path",
            scheme,
            events,
            _expect_ok(events, verifier),
        )

    events, verifier = _build_ledger("demo", [])
    add("valid-genesis-only-demo", "a bare genesis is a complete ledger",
        "demo", events, _expect_ok(events, verifier))

    events, verifier = _build_ledger(
        "demo", [TRANSFER, dict(TRANSFER, amount="100"), dict(TRANSFER, amount="1")]
    )
    add("valid-repeated-transfers-demo", "sequence and hash chain over repeated actions",
        "demo", events, _expect_ok(events, verifier))

    # -- rejections ------------------------------------------------------
    events, verifier = _build_ledger("demo", [TRANSFER])
    no_genesis = copy.deepcopy(events[1:])
    add("reject-first-event-not-genesis", "a ledger must begin with genesis",
        "demo", no_genesis, _expect_error(no_genesis, verifier, "first event must be genesis"))

    dup = copy.deepcopy(events) + [copy.deepcopy(events[0])]
    add("reject-duplicate-genesis", "a second genesis is invalid",
        "demo", dup, _expect_error(dup, verifier, "genesis appears twice"))

    events3, verifier = _build_ledger("demo", [TRANSFER, BURN])
    gap = copy.deepcopy([events3[0], events3[2]])
    add("reject-sequence-gap", "removing an interior event breaks the sequence",
        "demo", gap, _expect_error(gap, verifier, "sequence must be contiguous"))

    tampered = copy.deepcopy(events3)
    tampered[1]["amount"] = "999"
    add("reject-tampered-amount", "editing a signed field invalidates the record",
        "demo", tampered, _expect_error(tampered, verifier, "signature/hash must fail"))

    overspend_events, verifier = _build_ledger("demo", [TRANSFER])
    bad_burn = sr.scaffold_event_from_ledger(
        overspend_events, action="burn", signer="alice",
        from_account="alice", amount="401", verifier=verifier,
    )
    bad_burn = sr.sign_event_record(bad_burn, scheme="demo", key_id=None, signer=None)
    overspend = copy.deepcopy(overspend_events) + [bad_burn]
    add("reject-overspend", "burning more than the account holds",
        "demo", overspend, _expect_error(overspend, verifier, "insufficient balance"))

    unicode_amount = copy.deepcopy(events)
    unicode_amount[1]["amount"] = "４００"  # fullwidth 400
    add("reject-unicode-digits", "amounts must be ASCII digit strings",
        "demo", unicode_amount, _expect_error(unicode_amount, verifier, "non-ASCII digits rejected"))

    bool_decimals_genesis = _genesis()
    bool_decimals_genesis["decimals"] = True
    bad_genesis = [
        sr.sign_event_record(bool_decimals_genesis, scheme="demo", key_id=None, signer=None)
    ]
    add("reject-bool-decimals", "JSON booleans are not accepted where integers are required",
        "demo", bad_genesis, _expect_error(bad_genesis, sr.demo_signature_verifier, "bool decimals rejected"))

    unknown = copy.deepcopy(events)
    unknown[1]["action"] = "teleport"
    add("reject-unknown-action", "actions outside the frozen kernel set",
        "demo", unknown, _expect_error(unknown, verifier, "unknown action"))

    # ed25519 wrong-key: alice's event re-signed with a key not registered for her
    ed_events, ed_verifier = _build_ledger("ed25519", [TRANSFER])
    wrong_signer = sr.make_ed25519_signer({"alice-key": "55" * 32})
    forged = sr.scaffold_event_from_ledger(
        ed_events, action="burn", signer="alice",
        from_account="alice", amount="10", verifier=ed_verifier,
    )
    forged = sr.sign_event_record(
        forged, scheme="ed25519", key_id="alice-key", signer=wrong_signer
    )
    forged_ledger = copy.deepcopy(ed_events) + [forged]
    add("reject-wrong-key-ed25519", "valid signature under an unregistered key",
        "ed25519", forged_ledger, _expect_error(forged_ledger, ed_verifier, "wrong key rejected"))

    return vectors


def main():
    VECTORS_DIR.mkdir(exist_ok=True)
    vectors = build_vectors()
    names = [v["name"] for v in vectors]
    assert len(names) == len(set(names)), "duplicate vector names"
    for vector in vectors:
        path = VECTORS_DIR / f"{vector['name']}.json"
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(vector, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(vectors)} vectors to {VECTORS_DIR}")


if __name__ == "__main__":
    main()
