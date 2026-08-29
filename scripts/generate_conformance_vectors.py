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


def _rechain(events, index=-1):
    """Recompute the `event_id` of a record after tampering with it.

    Mutating a field of a signed record leaves its stated `event_id` stale,
    and the reference checks the id before it checks anything semantic - so
    a vector named for an amount rule, an action allow-list or a signature
    was really testing `event_id` and nothing else. Seven vectors were in
    that state, which let an implementation with no amount grammar, no
    action allow-list and no demo signature check score full marks.

    `event_id` covers `signature`, so this is applied after any signature
    tampering too, leaving the signature check as the deciding one.

    Found by the first independent implementation, 2026-08-29.
    """
    events = copy.deepcopy(events)
    event = events[index]
    event.pop("event_id", None)
    event["event_id"] = sr.event_id(event)
    return events


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
    unicode_amount = _rechain(unicode_amount, 1)
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
    unknown = _rechain(unknown, 1)
    add("reject-unknown-action", "actions outside the frozen kernel set",
        "demo", unknown, _expect_error(unknown, verifier, "unknown action"))

    # -- remaining kernel actions: freeze, mint, rotate-authority ---------
    FREEZE = dict(action="freeze", signer="issuer", account="alice", frozen="true")
    UNFREEZE = dict(action="freeze", signer="issuer", account="alice", frozen="false")
    ROTATE = dict(action="rotate-authority", signer="issuer", new_mint_authority="alice")

    events, verifier = _build_ledger("demo", [FREEZE])
    add("valid-freeze-account-demo", "freezing an account is a valid authority action",
        "demo", events, _expect_ok(events, verifier))

    events, verifier = _build_ledger("demo", [FREEZE, UNFREEZE])
    add("valid-freeze-then-unfreeze-demo", "freeze state is reversible by the authority",
        "demo", events, _expect_ok(events, verifier))

    events, verifier = _build_ledger("demo", [MINT])
    add("valid-mint-demo", "the mint authority may mint new units",
        "demo", events, _expect_ok(events, verifier))

    events, verifier = _build_ledger("demo", [ROTATE])
    add("valid-rotate-authority-demo", "mint authority may hand off to another account",
        "demo", events, _expect_ok(events, verifier))

    events, verifier = _build_ledger(
        "demo", [ROTATE, dict(action="mint", signer="alice", to_account="alice", amount="10")]
    )
    add("valid-mint-after-rotation-demo", "the new authority may mint after handoff",
        "demo", events, _expect_ok(events, verifier))

    events, verifier = _build_ledger(
        "demo", [dict(TRANSFER, amount="1000")]
    )
    add("valid-transfer-entire-balance-demo", "transferring the full balance leaves zero",
        "demo", events, _expect_ok(events, verifier))

    events, verifier = _build_ledger("ed25519", [FREEZE, UNFREEZE, MINT, ROTATE])
    add("valid-all-actions-ed25519", "every kernel action in one signed ledger",
        "ed25519", events, _expect_ok(events, verifier))

    # -- authority and state rejections ----------------------------------
    frozen_events, verifier = _build_ledger("demo", [TRANSFER, FREEZE])
    blocked = sr.scaffold_event_from_ledger(
        frozen_events, action="transfer", signer="alice",
        from_account="alice", to_account="issuer", amount="1", verifier=verifier,
    )
    blocked = sr.sign_event_record(blocked, scheme="demo", key_id=None, signer=None)
    frozen_ledger = copy.deepcopy(frozen_events) + [blocked]
    add("reject-transfer-from-frozen-account", "a frozen account cannot move units",
        "demo", frozen_ledger, _expect_error(frozen_ledger, verifier, "frozen account"))

    base, verifier = _build_ledger("demo", [TRANSFER])
    rogue_mint = sr.scaffold_event_from_ledger(
        base, action="mint", signer="alice", to_account="alice", amount="5", verifier=verifier,
    )
    rogue_mint = sr.sign_event_record(rogue_mint, scheme="demo", key_id=None, signer=None)
    rogue_ledger = copy.deepcopy(base) + [rogue_mint]
    add("reject-mint-by-non-authority", "only the mint authority may mint",
        "demo", rogue_ledger, _expect_error(rogue_ledger, verifier, "not mint authority"))

    rogue_rotate = sr.scaffold_event_from_ledger(
        base, action="rotate-authority", signer="alice",
        new_mint_authority="alice", verifier=verifier,
    )
    rogue_rotate = sr.sign_event_record(rogue_rotate, scheme="demo", key_id=None, signer=None)
    rotate_ledger = copy.deepcopy(base) + [rogue_rotate]
    add("reject-rotate-by-non-authority", "only the mint authority may hand off authority",
        "demo", rotate_ledger, _expect_error(rotate_ledger, verifier, "not mint authority"))

    rogue_freeze = sr.scaffold_event_from_ledger(
        base, action="freeze", signer="alice", account="issuer",
        frozen="true", verifier=verifier,
    )
    rogue_freeze = sr.sign_event_record(rogue_freeze, scheme="demo", key_id=None, signer=None)
    freeze_ledger = copy.deepcopy(base) + [rogue_freeze]
    add("reject-freeze-by-non-authority", "only the authority may freeze accounts",
        "demo", freeze_ledger, _expect_error(freeze_ledger, verifier, "not mint authority"))

    # -- amount and chain-integrity rejections ---------------------------
    zero_amount = copy.deepcopy(base)
    zero_amount[1]["amount"] = "0"
    zero_amount = _rechain(zero_amount, 1)
    add("reject-zero-amount", "transfers must move a positive quantity",
        "demo", zero_amount, _expect_error(zero_amount, verifier, "zero amount"))

    negative_amount = copy.deepcopy(base)
    negative_amount[1]["amount"] = "-5"
    negative_amount = _rechain(negative_amount, 1)
    add("reject-negative-amount", "amounts are unsigned digit strings",
        "demo", negative_amount, _expect_error(negative_amount, verifier, "negative amount"))

    overlong_amount = copy.deepcopy(base)
    overlong_amount[1]["amount"] = "9" * (sr.MAX_AMOUNT_DIGITS + 1)
    overlong_amount = _rechain(overlong_amount, 1)
    add("reject-amount-exceeds-digit-bound",
        "amounts are bounded so the decision never depends on host integer limits",
        "demo", overlong_amount,
        _expect_error(overlong_amount, verifier, "amount digit bound"))

    overlong_genesis_balance = _genesis()
    overlong_genesis_balance["initial_balances"]["issuer"] = "9" * (sr.MAX_AMOUNT_DIGITS + 1)
    overlong_genesis = [
        sr.sign_event_record(overlong_genesis_balance, scheme="demo", key_id=None, signer=None)
    ]
    add("reject-genesis-balance-exceeds-digit-bound",
        "the digit bound applies to genesis balances too",
        "demo", overlong_genesis,
        _expect_error(overlong_genesis, sr.demo_signature_verifier, "amount digit bound"))

    leading_zero = copy.deepcopy(base)
    leading_zero[1]["amount"] = "0400"
    leading_zero = _rechain(leading_zero, 1)
    add("reject-leading-zero-amount", "amounts must be in canonical form",
        "demo", leading_zero, _expect_error(leading_zero, verifier, "non-canonical amount"))

    broken_chain, verifier2 = _build_ledger("demo", [TRANSFER, BURN])
    broken_chain = copy.deepcopy(broken_chain)
    broken_chain[2]["prev_event_id"] = "sha256:" + "00" * 32
    add("reject-broken-prev-event-id", "each event commits to its predecessor",
        "demo", broken_chain, _expect_error(broken_chain, verifier2, "hash chain broken"))

    reordered, verifier3 = _build_ledger("demo", [TRANSFER, BURN])
    reordered = [copy.deepcopy(reordered[0]), copy.deepcopy(reordered[2]), copy.deepcopy(reordered[1])]
    add("reject-reordered-events", "event order is fixed by sequence and hash chain",
        "demo", reordered, _expect_error(reordered, verifier3, "out-of-order events"))

    forged_sig = copy.deepcopy(base)
    forged_sig[1]["signature"] = "demo:not-a-real-signature"
    forged_sig = _rechain(forged_sig, 1)
    add("reject-forged-signature-demo", "signatures are checked, not merely present",
        "demo", forged_sig, _expect_error(forged_sig, verifier, "bad signature"))

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

    # ------------------------------------------------------------------
    # Coverage added 2026-08-29 after the first independent implementation
    # showed ten protocol checks could be deleted at once while the corpus
    # still reported 33/33. Each vector below is the deciding check for a
    # rule that nothing previously exercised.
    # ------------------------------------------------------------------

    # SPEC 2.6: non-ASCII must be emitted raw, not escaped. Nothing tested
    # this - and it is the rule most likely to fork across languages, since
    # Python escapes by default and JavaScript does not. A valid ledger
    # whose committed state contains non-ASCII makes the two serialisations
    # produce different state hashes.
    nonascii_genesis = _genesis(symbol="VECÉ", name="Conformance unit café — naïve")
    nonascii = [sr.sign_event_record(nonascii_genesis, scheme="demo", key_id=None, signer=None)]
    add("valid-non-ascii-metadata-demo",
        "canonical JSON emits non-ASCII raw, so escaping it forks the state hash",
        "demo", nonascii, _expect_ok(nonascii, sr.demo_signature_verifier))

    # SPEC 8.8: with the seven tampered vectors rechained, nothing else
    # exercised the stated-event_id check. This vector is it.
    stale_id = copy.deepcopy(base)
    stale_id[1]["event_id"] = "sha256:" + "00" * 32
    add("reject-stale-event-id", "a stated event_id must match the record",
        "demo", stale_id, _expect_error(stale_id, verifier, "event_id mismatch"))

    # SPEC 8.9: no event in the corpus carried a state_hash at all.
    bad_state = copy.deepcopy(base)
    bad_state[1]["state_hash"] = "sha256:" + "11" * 32
    bad_state = _rechain(bad_state, 1)
    add("reject-wrong-per-event-state-hash",
        "a stated state_hash must match replayed state",
        "demo", bad_state, _expect_error(bad_state, verifier, "state_hash mismatch"))

    # SPEC 8.3 for a transfer - reject-overspend is a burn, so the transfer
    # arm of the balance check was never exercised.
    over_events, over_verifier = _build_ledger("demo", [])
    big_transfer = sr.scaffold_event_from_ledger(
        over_events, verifier=over_verifier, action="transfer", signer="issuer",
        from_account="issuer", to_account="alice", amount="999999",
    )
    over_ledger = copy.deepcopy(over_events) + [
        sr.sign_event_record(big_transfer, scheme="demo", key_id=None, signer=None)
    ]
    add("reject-transfer-overspend", "a transfer cannot move more than the sender holds",
        "demo", over_ledger, _expect_error(over_ledger, over_verifier, "insufficient balance"))

    # SPEC 8.5: no vector used a foreign root_id.
    foreign = copy.deepcopy(base)
    foreign[1]["root_id"] = "cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd:0"
    foreign = _rechain(foreign, 1)
    add("reject-foreign-root-id", "every event must carry the ledger's own root_id",
        "demo", foreign, _expect_error(foreign, verifier, "root_id mismatch"))

    # SPEC 8.4: no vector minted past max_supply.
    cap_events, cap_verifier = _build_ledger("demo", [])
    ok_mint = sr.scaffold_event_from_ledger(
        cap_events, verifier=cap_verifier, action="mint", signer="issuer",
        to_account="alice", amount="1",
    )
    cap_ledger = copy.deepcopy(cap_events) + [
        sr.sign_event_record(ok_mint, scheme="demo", key_id=None, signer=None)
    ]
    # Scaffolding refuses to build an over-cap mint, so raise the amount
    # afterwards and rechain, leaving the supply check as the deciding one.
    cap_ledger[-1]["amount"] = "9" * 12
    cap_ledger = _rechain(cap_ledger, -1)
    add("reject-mint-exceeds-max-supply", "minting cannot take supply past max_supply",
        "demo", cap_ledger, _expect_error(cap_ledger, cap_verifier, "mint exceeds max supply"))

    # SPEC 6.5: the freeze check was only exercised on the sending side.
    for label, action_kwargs, note in (
        ("mint", dict(action="mint", signer="issuer", to_account="alice", amount="10"),
         "a frozen account cannot receive a mint"),
        ("transfer", dict(action="transfer", signer="issuer", from_account="issuer",
                          to_account="alice", amount="10"),
         "a frozen account cannot receive a transfer"),
    ):
        fr_events, fr_verifier = _build_ledger(
            "demo", [dict(action="freeze", signer="issuer", account="alice", frozen="true")]
        )
        blocked = sr.scaffold_event_from_ledger(fr_events, verifier=fr_verifier, **action_kwargs)
        fr_ledger = copy.deepcopy(fr_events) + [
            sr.sign_event_record(blocked, scheme="demo", key_id=None, signer=None)
        ]
        add(f"reject-{label}-to-frozen-account", note,
            "demo", fr_ledger, _expect_error(fr_ledger, fr_verifier, "recipient is frozen"))

    # max_supply: null - the unbounded branch never appeared in the corpus.
    # scaffold_genesis_record's max_supply=None means "use the default",
    # not "unbounded", so the null has to be set explicitly.
    unbounded_genesis = _genesis()
    unbounded_genesis["max_supply"] = None
    unbounded = [sr.sign_event_record(unbounded_genesis, scheme="demo", key_id=None, signer=None)]
    unbounded_mint = sr.scaffold_event_from_ledger(
        unbounded, verifier=sr.demo_signature_verifier, action="mint",
        signer="issuer", to_account="alice", amount="9" * 20,
    )
    unbounded = unbounded + [
        sr.sign_event_record(unbounded_mint, scheme="demo", key_id=None, signer=None)
    ]
    add("valid-unbounded-max-supply-demo",
        "max_supply null means no cap, and is committed to as JSON null",
        "demo", unbounded, _expect_ok(unbounded, sr.demo_signature_verifier))

    # SPEC 8.2 in isolation. reject-sequence-gap drops an event, which also
    # breaks prev_event_id, so the sequence check is redundant with the
    # chain check there and an implementation missing it still passes.
    # Here the chain is intact and only `sequence` is wrong.
    seq_ledger = copy.deepcopy(base)
    seq_ledger[1]["sequence"] = 7
    seq_ledger = _rechain(seq_ledger, 1)
    add("reject-bad-sequence-intact-chain",
        "sequence must be checked even when prev_event_id is correct",
        "demo", seq_ledger, _expect_error(seq_ledger, verifier, "bad sequence"))

    # SPEC 8.1 in isolation. reject-duplicate-genesis appends a copy of the
    # genesis record, which lacks prev_event_id and signer, so it is decided
    # by the missing-field check rather than by the one-genesis rule. This
    # second genesis is well-formed as a non-genesis record would be.
    dup_ledger = copy.deepcopy(base)
    second_genesis = copy.deepcopy(base[0])
    second_genesis["sequence"] = 2
    second_genesis["prev_event_id"] = sr.event_id(base[1])
    second_genesis["signer"] = "issuer"
    second_genesis.pop("event_id", None)
    second_genesis["event_id"] = sr.event_id(second_genesis)
    dup_ledger = dup_ledger + [second_genesis]
    add("reject-second-genesis-well-formed",
        "a ledger has exactly one genesis, however well-formed the second is",
        "demo", dup_ledger, _expect_error(dup_ledger, verifier, "one genesis only"))

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
