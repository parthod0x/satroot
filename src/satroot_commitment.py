"""Backend-neutral state commitments.

A SATROOT commitment is a canonical JSON document binding a namespace
``root_id`` to a semantic ``state_hash``. That document is defined
independently of how it is published: publishing it is a separate,
pluggable concern.

This module makes that separation explicit and gives it more than one
implementation, so "the anchoring backend is interchangeable" is a
demonstrated property rather than a claim:

- ``bsv-opreturn`` - embeds the commitment bytes in a SPEC section 4
  ``OP_FALSE OP_RETURN`` output on a Bitcoin SV transaction.
- ``rfc3161`` - submits the commitment *digest* to any RFC 3161 Time-Stamp
  Authority and keeps the returned token. No blockchain involved.

Both bind the same bytes. Verification of the ledger itself never requires
either: replay is offline and self-contained, and a commitment only adds
third-party evidence that a given state existed at a given time.

Dependency-free: the RFC 3161 codec below implements just enough DER.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from satroot1 import SatRootError, validate_root_id

CONTENT_TYPE = "application/satroot1+json"
BACKENDS = ("bsv-opreturn", "rfc3161")


# --------------------------------------------------------------------------
# The commitment itself - identical for every backend
# --------------------------------------------------------------------------


def build_commitment_bytes(root_id: str, state_hash: str) -> bytes:
    """Canonical commitment document. Byte-identical across backends."""
    validate_root_id(root_id)
    if not (
        isinstance(state_hash, str)
        and state_hash.startswith("sha256:")
        and len(state_hash) == len("sha256:") + 64
        and all(c in "0123456789abcdef" for c in state_hash[len("sha256:"):])
    ):
        raise SatRootError(f"invalid state_hash for commitment: {state_hash}")
    payload = {"protocol": "SATROOT-1", "root_id": root_id, "state_hash": state_hash}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def commitment_digest(commitment: bytes) -> bytes:
    """SHA-256 over the commitment bytes; what a timestamp authority signs."""
    return hashlib.sha256(commitment).digest()


# --------------------------------------------------------------------------
# Minimal DER, sufficient for RFC 3161 requests and messageImprint recovery
# --------------------------------------------------------------------------

_SEQUENCE = 0x30
_INTEGER = 0x02
_OID = 0x06
_OCTET_STRING = 0x04
_NULL = 0x05
_BOOLEAN = 0x01

# 2.16.840.1.101.3.4.2.1 - id-sha256. SHA-1 is deliberately unsupported.
_OID_SHA256 = bytes([0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01])


def _der_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def _tlv(tag: int, body: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(body)) + body


def _read_tlv(buf: bytes, i: int):
    """Return (tag, value, next_index) for the TLV starting at i."""
    if i + 2 > len(buf):
        raise SatRootError("truncated DER")
    tag = buf[i]
    first = buf[i + 1]
    i += 2
    if first < 0x80:
        length = first
    else:
        count = first & 0x7F
        if count == 0 or i + count > len(buf):
            raise SatRootError("unsupported or truncated DER length")
        length = int.from_bytes(buf[i:i + count], "big")
        i += count
    if i + length > len(buf):
        raise SatRootError("DER value exceeds buffer")
    return tag, buf[i:i + length], i + length


def build_timestamp_request(
    digest: bytes, *, nonce: Optional[int] = None, cert_req: bool = True
) -> bytes:
    """RFC 3161 TimeStampReq (DER) over a SHA-256 digest."""
    if len(digest) != 32:
        raise SatRootError("commitment digest must be 32 bytes (sha256)")
    algorithm = _tlv(_SEQUENCE, _tlv(_OID, _OID_SHA256) + _tlv(_NULL, b""))
    message_imprint = _tlv(_SEQUENCE, algorithm + _tlv(_OCTET_STRING, digest))
    body = _tlv(_INTEGER, b"\x01") + message_imprint
    if nonce is not None:
        raw = nonce.to_bytes((nonce.bit_length() + 8) // 8 or 1, "big")
        body += _tlv(_INTEGER, raw)
    if cert_req:
        body += _tlv(_BOOLEAN, b"\xff")
    return _tlv(_SEQUENCE, body)


def _match_imprint(seq: bytes):
    """A messageImprint is SEQUENCE{ AlgorithmIdentifier(sha256), OCTET STRING(32) }."""
    try:
        tag_a, alg, j = _read_tlv(seq, 0)
        if tag_a != _SEQUENCE:
            return None
        tag_o, oid, _ = _read_tlv(alg, 0)
        if tag_o != _OID or oid != _OID_SHA256:
            return None
        tag_d, dig, _ = _read_tlv(seq, j)
        if tag_d == _OCTET_STRING and len(dig) == 32:
            return dig
    except SatRootError:
        return None
    return None


def extract_message_imprint(token_der: bytes) -> bytes:
    """Recover the SHA-256 messageImprint from a TimeStampResp or token."""

    def walk(buf: bytes, depth: int = 0):
        if depth > 24:
            return None
        i = 0
        while i < len(buf):
            try:
                tag, value, i = _read_tlv(buf, i)
            except SatRootError:
                return None
            if tag == _SEQUENCE:
                found = _match_imprint(value)
                if found is not None:
                    return found
                nested = walk(value, depth + 1)
                if nested is not None:
                    return nested
        return None

    result = walk(token_der)
    if result is None:
        raise SatRootError("no SHA-256 messageImprint found in timestamp token")
    return result


def verify_timestamp_token(token_der: bytes, root_id: str, state_hash: str) -> Dict[str, Any]:
    """Check that a timestamp token's messageImprint is this commitment.

    **This performs no cryptographic verification of the token.** It parses
    out the SHA-256 messageImprint and compares it against the digest of the
    commitment document. It does not check the TSA's signature over the
    TSTInfo, and it does not validate any certificate chain. A token forged
    by anyone, carrying the right imprint, passes this check.

    What it establishes is therefore one half of the question - *which*
    namespace state a token is about - and none of the other half, which is
    whether the token is authentic. Authenticity requires verifying the CMS
    SignedData signature and a trust decision about the TSA, both of which
    need a certificate store and an X.509 stack this dependency-free module
    deliberately does not carry. Pass the token to a real CMS verifier
    (``openssl ts -verify``, or the ``cryptography`` package) for that.

    Named ``verify_`` for continuity with the v1.7 release; ``binding_matches``
    in the returned mapping is the accurate name for what it answers.
    """
    commitment = build_commitment_bytes(root_id, state_hash)
    expected = commitment_digest(commitment)
    found = extract_message_imprint(token_der)
    return {
        "backend": "rfc3161",
        "commitment_matches": found == expected,
        "binding_matches": found == expected,
        "signature_verified": False,
        "chain_validated": False,
        "expected_digest": expected.hex(),
        "token_digest": found.hex(),
        "root_id": root_id,
        "state_hash": state_hash,
        "note": (
            "binding only: the TSA signature over TSTInfo is NOT checked and no "
            "certificate chain is validated, so this says which state the token "
            "is about and nothing about whether the token is authentic"
        ),
    }


def describe_backends() -> Dict[str, Any]:
    """What each backend publishes, for documentation and reports."""
    return {
        "commitment": (
            "canonical JSON binding root_id to state_hash; identical for all backends"
        ),
        "backends": {
            "bsv-opreturn": {
                "publishes": "the commitment bytes, in an OP_FALSE OP_RETURN output",
                "verifier": "satroot_envelope_verification_smoke",
                "requires_chain": True,
            },
            "rfc3161": {
                "publishes": "the SHA-256 digest of the commitment, to a Time-Stamp Authority",
                "binding_checker": "satroot_commitment.verify_timestamp_token",
                "authenticity": (
                    "not checked here; needs a CMS verifier and a TSA trust decision"
                ),
                "requires_chain": False,
            },
        },
        "invariant": "ledger replay and state verification never require any backend",
    }
