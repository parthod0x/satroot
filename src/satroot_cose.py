"""COSE_Sign1 encoding of SATROOT events, for SCITT interoperability.

RFC 9943 (SCITT) carries application payloads inside COSE_Sign1 Signed
Statements, and treats those payloads as opaque to the Transparency
Service. SATROOT defines what such a payload *means* and what state a
sequence of them produces. This module is the bridge: it encodes a
SATROOT event as a COSE_Sign1 Signed Statement so the two layers can be
demonstrated together rather than described together.

Dependency-free apart from the ed25519 primitives already used by the
kernel: the CBOR encoder below implements the deterministic subset of
RFC 8949 section 4.2 that COSE requires - definite lengths, shortest-form
integers, and map keys sorted by their encoded bytes.

Scope, stated plainly: this produces and verifies Signed Statements. It
does not implement a Transparency Service, does not produce Receipts, and
carries no inclusion proof. Registering these statements with a real
Transparency Service is the next step, not something this module does.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from satroot1 import (
    SatRootError,
    canonical_json,
    ed25519_available,
    event_id,
)

# COSE header labels (RFC 9052) and the CWT claims label used by RFC 9943.
HDR_ALG = 1
HDR_CONTENT_TYPE = 3
HDR_KID = 4
HDR_CWT_CLAIMS = 15

# RFC 9864 (Oct 2025) registers fully-specified Ed25519 as -19 and marks the
# polymorphic EdDSA identifier -8 Deprecated, because -8 alone does not say
# which curve is in use. Emit -19; accept -8 on the way in, since statements
# signed before that RFC exist and the signature does not depend on the label.
ALG_ED25519 = -19
ALG_EDDSA_DEPRECATED = -8
ACCEPTED_ALGS = (ALG_ED25519, ALG_EDDSA_DEPRECATED)
CWT_ISS = 1
CWT_SUB = 2

COSE_SIGN1_TAG = 18
SATROOT_CONTENT_TYPE = "application/satroot1+json"

# Guards the CBOR decoder against deeply nested attacker input, which would
# otherwise surface as RecursionError rather than SatRootError.
MAX_CBOR_DEPTH = 32


class CBORTag:
    """A CBOR tagged value (major type 6).

    Needed because RFC 9943 defines ``Signed_Statement = #6.18(COSE_Sign1)``:
    the tag is part of the type, so it has to survive both encoding and
    decoding rather than being discarded.
    """

    __slots__ = ("tag", "value")

    def __init__(self, tag: int, value: Any) -> None:
        self.tag = tag
        self.value = value

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, CBORTag)
            and self.tag == other.tag
            and self.value == other.value
        )

    def __repr__(self) -> str:
        return f"CBORTag({self.tag}, {self.value!r})"


# ---------------------------------------------------------------------------
# Deterministic CBOR (the subset COSE needs)
# ---------------------------------------------------------------------------


def _head(major: int, value: int) -> bytes:
    if value < 0:
        raise SatRootError("cbor head value must be non-negative")
    if value < 24:
        return bytes([(major << 5) | value])
    for bits, extra in ((8, 24), (16, 25), (32, 26), (64, 27)):
        if value < (1 << bits):
            return bytes([(major << 5) | extra]) + value.to_bytes(bits // 8, "big")
    raise SatRootError("integer too large for CBOR")


def cbor_encode(value: Any) -> bytes:
    """Deterministic CBOR for the types COSE structures use."""
    if isinstance(value, bool):
        # Guard: bool is a subclass of int and must not encode as one.
        raise SatRootError("booleans are not used in these COSE structures")
    if isinstance(value, int):
        return _head(0, value) if value >= 0 else _head(1, -value - 1)
    if isinstance(value, bytes):
        return _head(2, len(value)) + value
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return _head(3, len(raw)) + raw
    if isinstance(value, list):
        return _head(4, len(value)) + b"".join(cbor_encode(v) for v in value)
    if isinstance(value, dict):
        # RFC 8949 4.2.1: keys sorted by their encoded byte sequences.
        # Bytewise on the *encoding*, which is not numeric order and not
        # RFC 7049 s3.9 length-first order. For {10, 100, -1} the three
        # rules disagree and this one gives 0a, 1864, 20.
        items = sorted(((cbor_encode(k), v) for k, v in value.items()), key=lambda kv: kv[0])
        return _head(5, len(items)) + b"".join(k + cbor_encode(v) for k, v in items)
    if isinstance(value, CBORTag):
        return _head(6, value.tag) + cbor_encode(value.value)
    raise SatRootError(f"unsupported CBOR type: {type(value).__name__}")


def _read(buf: bytes, i: int, depth: int = 0) -> Tuple[Any, int]:
    if depth > MAX_CBOR_DEPTH:
        raise SatRootError("CBOR nesting exceeds the permitted depth")
    if i >= len(buf):
        raise SatRootError("truncated CBOR")
    initial = buf[i]
    major, info = initial >> 5, initial & 0x1F
    i += 1
    if info < 24:
        value = info
    elif info in (24, 25, 26, 27):
        n = 1 << (info - 24)
        if i + n > len(buf):
            raise SatRootError("truncated CBOR integer")
        value = int.from_bytes(buf[i:i + n], "big")
        i += n
    else:
        raise SatRootError("unsupported CBOR additional information")

    if major == 0:
        return value, i
    if major == 1:
        return -1 - value, i
    if major in (2, 3):
        if i + value > len(buf):
            raise SatRootError("truncated CBOR string")
        raw = buf[i:i + value]
        return (raw if major == 2 else raw.decode("utf-8")), i + value
    if major == 4:
        out: List[Any] = []
        for _ in range(value):
            item, i = _read(buf, i, depth + 1)
            out.append(item)
        return out, i
    if major == 5:
        obj: Dict[Any, Any] = {}
        for _ in range(value):
            k, i = _read(buf, i, depth + 1)
            v, i = _read(buf, i, depth + 1)
            if k in obj:
                # RFC 9052 s9: applications must not parse or process
                # maps with duplicate labels. Silently keeping the last
                # one lets a second alg override the first.
                raise SatRootError(f"duplicate CBOR map label: {k!r}")
            obj[k] = v
        return obj, i
    if major == 6:
        inner, i = _read(buf, i, depth + 1)
        return CBORTag(value, inner), i
    raise SatRootError(f"unsupported CBOR major type {major}")


def cbor_decode(buf: bytes) -> Any:
    value, i = _read(buf, 0)
    if i != len(buf):
        raise SatRootError("trailing bytes after CBOR value")
    return value


# ---------------------------------------------------------------------------
# COSE_Sign1 Signed Statements over SATROOT events
# ---------------------------------------------------------------------------


def protected_header(
    *, issuer: str, subject: str, key_id: str, alg: int = ALG_ED25519
) -> bytes:
    """Protected header bstr: alg, content type, kid and CWT claims.

    ``alg`` defaults to the fully-specified Ed25519 identifier -19
    (RFC 9864). Pass ``ALG_EDDSA_DEPRECATED`` to emit the deprecated
    polymorphic -8 instead, which is what deployed COSE libraries
    currently understand - see ``docs/COSE_INTEROP.md``.
    """
    if alg not in ACCEPTED_ALGS:
        raise SatRootError(f"unsupported COSE alg for SATROOT: {alg}")
    header = {
        HDR_ALG: alg,
        HDR_CONTENT_TYPE: SATROOT_CONTENT_TYPE,
        HDR_KID: key_id.encode("utf-8"),
        HDR_CWT_CLAIMS: {CWT_ISS: issuer, CWT_SUB: subject},
    }
    return cbor_encode(header)


def signature_structure(protected: bytes, payload: bytes) -> bytes:
    """Sig_structure for COSE_Sign1 (RFC 9052 s4.4), with empty external_aad."""
    return cbor_encode(["Signature1", protected, b"", payload])


def event_payload(event: Dict[str, Any]) -> bytes:
    """The SATROOT event as canonical JSON - the bytes the statement carries."""
    return canonical_json(event).encode("utf-8")


def sign_statement(
    event: Dict[str, Any],
    *,
    issuer: str,
    subject: str,
    key_id: str,
    private_key_hex: str,
    alg: int = ALG_ED25519,
) -> bytes:
    """Encode one SATROOT event as a COSE_Sign1 Signed Statement."""
    if not ed25519_available():
        raise SatRootError("ed25519 support unavailable; install satroot[crypto]")
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    protected = protected_header(
        issuer=issuer, subject=subject, key_id=key_id, alg=alg
    )
    payload = event_payload(event)
    to_be_signed = signature_structure(protected, payload)
    # COSE signs the raw Sig_structure bytes. The kernel's ed25519_sign takes
    # a str, so sign directly here rather than round-tripping through hex,
    # which would not interoperate with any other COSE implementation.
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    signature = key.sign(to_be_signed)
    # RFC 9943: Signed_Statement = #6.18(COSE_Sign1). The tag is part of
    # the type, so a SCITT decoder is entitled to reject an untagged array.
    return cbor_encode(CBORTag(COSE_SIGN1_TAG, [protected, {}, payload, signature]))


def _payload_event(payload: bytes) -> Dict[str, Any]:
    """The JSON payload, with decoding failures kept inside SatRootError."""
    try:
        return json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise SatRootError(f"statement payload is not SATROOT JSON: {exc}") from exc


def parse_statement(statement: bytes) -> Dict[str, Any]:
    """Decode a Signed Statement into its parts, without verifying."""
    decoded = cbor_decode(statement)
    if not isinstance(decoded, CBORTag):
        raise SatRootError(
            "SCITT Signed Statement must be CBOR tag 18; found an untagged "
            "value (RFC 9943: Signed_Statement = #6.18(COSE_Sign1))"
        )
    if decoded.tag != COSE_SIGN1_TAG:
        raise SatRootError(
            f"expected COSE_Sign1 tag {COSE_SIGN1_TAG}, found {decoded.tag}"
        )
    decoded = decoded.value
    if not isinstance(decoded, list) or len(decoded) != 4:
        raise SatRootError("COSE_Sign1 must be a 4-element array")
    protected, unprotected, payload, signature = decoded
    if not isinstance(protected, bytes) or not isinstance(payload, bytes):
        raise SatRootError("protected header and payload must be byte strings")
    header = cbor_decode(protected) if protected else {}
    claims = header.get(HDR_CWT_CLAIMS, {})
    return {
        "alg": header.get(HDR_ALG),
        "content_type": header.get(HDR_CONTENT_TYPE),
        "kid": header.get(HDR_KID, b"").decode("utf-8") if header.get(HDR_KID) else None,
        "issuer": claims.get(CWT_ISS),
        "subject": claims.get(CWT_SUB),
        "payload": payload,
        "event": _payload_event(payload),
        "signature": signature,
        "protected": protected,
        "unprotected": unprotected,
    }


def verify_statement(statement: bytes, public_key_hex: str) -> Dict[str, Any]:
    """Verify a Signed Statement's signature and report what it carries."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    parsed = parse_statement(statement)
    if parsed["alg"] not in ACCEPTED_ALGS:
        raise SatRootError(f"unexpected COSE alg: {parsed['alg']}")
    if parsed["content_type"] != SATROOT_CONTENT_TYPE:
        raise SatRootError(f"unexpected content type: {parsed['content_type']}")
    to_be_signed = signature_structure(parsed["protected"], parsed["payload"])
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(
            parsed["signature"], to_be_signed
        )
        ok = True
    except Exception:
        ok = False
    return {
        "signature_valid": ok,
        "issuer": parsed["issuer"],
        "subject": parsed["subject"],
        "kid": parsed["kid"],
        "event_action": parsed["event"].get("action"),
        "event_id": event_id(parsed["event"]),
    }


def encode_ledger(
    events: List[Dict[str, Any]],
    *,
    issuer: str,
    private_keys: Dict[str, str],
    signer_key_ids: Dict[str, str],
    alg: int = ALG_ED25519,
) -> List[bytes]:
    """Encode a whole SATROOT ledger as a sequence of Signed Statements.

    The subject is the namespace root_id, so every statement in a ledger
    shares a subject - which is how a relying party groups statements
    about one namespace.

    Note this is a *subject grouping*, not a SCITT Statement Sequence:
    RFC 9943 s3 uses that term for the Transparency Service's own ordered
    registration history, which nothing here produces.
    """
    if not events:
        raise SatRootError("cannot encode an empty ledger")
    subject = events[0].get("root_id")
    if not subject:
        raise SatRootError("genesis event has no root_id")
    out = []
    for event in events:
        # Every statement is about to be labelled with the genesis root_id.
        # Without this check, events from two ledgers encode into
        # well-formed, correctly signed statements asserting a namespace
        # they do not belong to - no crash, no failed signature, a
        # plausible and wrong result.
        event_root = event.get("root_id")
        if event_root is not None and event_root != subject:
            raise SatRootError(
                f"event {event.get('sequence')} belongs to namespace "
                f"{event_root!r}, not {subject!r}; a ledger encodes as one subject"
            )
        # A signed event already declares which key signed it; fall back to
        # the signer map, then to the genesis mint authority.
        key_id = event.get("signature_key_id")
        if key_id is None:
            signer = event.get("signer") or event.get("mint_authority")
            key_id = signer_key_ids.get(signer)
        if key_id is None or key_id not in private_keys:
            raise SatRootError(
                f"no private key for event {event.get('sequence')} "
                f"(signer={event.get('signer') or event.get('mint_authority')!r})"
            )
        out.append(
            sign_statement(
                event,
                issuer=issuer,
                subject=subject,
                key_id=key_id,
                private_key_hex=private_keys[key_id],
                alg=alg,
            )
        )
    return out
