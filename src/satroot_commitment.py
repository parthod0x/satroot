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

What is demonstrated here is a **backend-neutral commitment document** - the
preimage is identical, so no backend gets a privileged format. That is not
the same as the two backends being interchangeable *as evidence*: an
OP_RETURN output and a TSA token differ in who vouches for the time, what a
verifier must trust, and what it costs to check. Choose on those grounds,
not on the document, which is the same either way.

Dependency-free: the RFC 3161 codec below implements just enough DER.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from satroot1 import SatRootError, canonical_json, validate_root_id

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
    # canonical_json, not a second json.dumps: json.dumps defaults to
    # ensure_ascii=True and canonical_json to False, so defining the
    # canonical form twice invites a divergence the first non-hex field finds.
    return canonical_json(payload).encode("utf-8")


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
_SET = 0x31
_CONTEXT_0 = 0xA0

# 2.16.840.1.101.3.4.2.1 - id-sha256. SHA-1 is deliberately unsupported.
_OID_SHA256 = bytes([0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01])
# 1.2.840.113549.1.7.2 - id-signedData (RFC 5652 s5.1)
_OID_SIGNED_DATA = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x07, 0x02])
# 1.2.840.113549.1.9.16.1.4 - id-ct-TSTInfo (RFC 3161 s2.4.2)
_OID_TST_INFO = bytes(
    [0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x09, 0x10, 0x01, 0x04]
)


def _der_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def _tlv(tag: int, body: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(body)) + body


def _read_tlv(buf: bytes, i: int):
    """Return (tag, value, next_index) for the DER TLV starting at i.

    DER, not BER. Lengths must be in shortest form, indefinite lengths are
    rejected, and high-tag-number identifiers are rejected rather than
    silently misparsed with the continuation octet read as a length.
    """
    if i + 2 > len(buf):
        raise SatRootError("truncated DER")
    tag = buf[i]
    if tag & 0x1F == 0x1F:
        raise SatRootError("high-tag-number identifiers are not supported")
    first = buf[i + 1]
    i += 2
    if first < 0x80:
        length = first
    elif first == 0x80:
        raise SatRootError("indefinite length is not valid DER")
    elif first == 0xFF:
        raise SatRootError("reserved DER length octet 0xff")
    else:
        count = first & 0x7F
        if i + count > len(buf):
            raise SatRootError("truncated DER length")
        raw = buf[i:i + count]
        if raw[0] == 0x00:
            raise SatRootError("non-minimal DER length encoding")
        length = int.from_bytes(raw, "big")
        if length < 0x80:
            raise SatRootError("non-minimal DER length encoding")
        i += count
    if i + length > len(buf):
        raise SatRootError("DER value exceeds buffer")
    return tag, buf[i:i + length], i + length


def _children(value: bytes):
    """Every TLV directly inside a constructed DER value."""
    out = []
    i = 0
    while i < len(value):
        tag, body, i = _read_tlv(value, i)
        out.append((tag, body))
    return out


def _field(items, index: int, tag: int, what: str) -> bytes:
    """The value of a field at a known position, or a named error."""
    if index >= len(items):
        raise SatRootError("missing " + what)
    got, body = items[index]
    if got != tag:
        raise SatRootError(
            "expected %s (tag 0x%02x), found tag 0x%02x" % (what, tag, got)
        )
    return body


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
        if not isinstance(nonce, int) or isinstance(nonce, bool):
            raise SatRootError("nonce must be an integer")
        if nonce < 0:
            raise SatRootError("nonce must be non-negative")
        # One extra octet whenever bit_length is a multiple of 8, so a value
        # with the high bit set is not read back as a negative INTEGER.
        raw = nonce.to_bytes((nonce.bit_length() + 8) // 8 or 1, "big")
        body += _tlv(_INTEGER, raw)
    if cert_req:
        body += _tlv(_BOOLEAN, b"\xff")
    return _tlv(_SEQUENCE, body)


def extract_message_imprint(token_der: bytes) -> bytes:
    """Recover the SHA-256 messageImprint from an RFC 3161 timestamp token.

    This walks the structure by its definition and reads ``messageImprint``
    at its defined position::

        TimeStampResp                              RFC 3161 s2.4.2
          PKIStatusInfo
          TimeStampToken = ContentInfo             RFC 5652 s3
            contentType = id-signedData
            content [0] EXPLICIT SignedData        RFC 5652 s5.1
              encapContentInfo                     RFC 5652 s5.2
                eContentType = id-ct-TSTInfo
                eContent [0] EXPLICIT OCTET STRING containing TSTInfo
                  messageImprint                   RFC 3161 s2.4.2

    It deliberately does **not** search for something shaped like a
    messageImprint. An earlier version did, descending only into SEQUENCEs -
    so it could not reach TSTInfo at all, because the path crosses a
    context-specific [0], a SET and an OCTET STRING. It therefore rejected
    every real token while accepting any DER that happened to contain a
    matching shape, including a bare TimeStampReq.

    A shape search is the wrong primitive over attacker-supplied DER.
    ``ESSCertIDv2`` (RFC 5035 s4) is
    ``SEQUENCE { AlgorithmIdentifier DEFAULT sha256, OCTET STRING, ... }``,
    the same shape as a messageImprint whenever the defaulted algorithm is
    written out explicitly. Reading a field by position cannot confuse the
    two; searching for a shape can.
    """
    tag, body, end = _read_tlv(token_der, 0)
    if tag != _SEQUENCE:
        raise SatRootError("timestamp token must be a DER SEQUENCE")
    if end != len(token_der):
        raise SatRootError("trailing bytes after timestamp token")

    items = _children(body)
    if not items:
        raise SatRootError("empty timestamp token")

    # A TimeStampResp opens with PKIStatusInfo, a SEQUENCE. A bare
    # TimeStampToken is a ContentInfo, which opens with an OID.
    if items[0][0] == _SEQUENCE:
        if len(items) < 2:
            raise SatRootError(
                "TimeStampResp carries no timeStampToken (status-only response)"
            )
        content_info = _field(items, 1, _SEQUENCE, "timeStampToken ContentInfo")
    elif items[0][0] == _OID:
        content_info = body
    else:
        raise SatRootError("not an RFC 3161 TimeStampResp or TimeStampToken")

    ci = _children(content_info)
    if _field(ci, 0, _OID, "ContentInfo.contentType") != _OID_SIGNED_DATA:
        raise SatRootError("ContentInfo.contentType is not id-signedData")

    explicit = _children(_field(ci, 1, _CONTEXT_0, "ContentInfo.content [0]"))
    signed_data = _children(_field(explicit, 0, _SEQUENCE, "SignedData"))
    _field(signed_data, 0, _INTEGER, "SignedData.version")
    _field(signed_data, 1, _SET, "SignedData.digestAlgorithms")

    eci = _children(_field(signed_data, 2, _SEQUENCE, "encapContentInfo"))
    if _field(eci, 0, _OID, "eContentType") != _OID_TST_INFO:
        raise SatRootError("encapsulated content is not id-ct-TSTInfo")

    econtent = _children(_field(eci, 1, _CONTEXT_0, "eContent [0]"))
    tst_der = _field(econtent, 0, _OCTET_STRING, "eContent OCTET STRING")

    tag, tst_body, tst_end = _read_tlv(tst_der, 0)
    if tag != _SEQUENCE or tst_end != len(tst_der):
        raise SatRootError("TSTInfo is not a well-formed DER SEQUENCE")
    tst = _children(tst_body)
    _field(tst, 0, _INTEGER, "TSTInfo.version")
    _field(tst, 1, _OID, "TSTInfo.policy")

    imprint = _children(_field(tst, 2, _SEQUENCE, "TSTInfo.messageImprint"))
    algorithm = _children(
        _field(imprint, 0, _SEQUENCE, "messageImprint.hashAlgorithm")
    )
    if _field(algorithm, 0, _OID, "hashAlgorithm OID") != _OID_SHA256:
        raise SatRootError("messageImprint hashAlgorithm is not SHA-256")
    digest = _field(imprint, 1, _OCTET_STRING, "messageImprint.hashedMessage")
    if len(digest) != 32:
        raise SatRootError(
            "SHA-256 imprint must be 32 bytes, found %d" % len(digest)
        )
    return digest


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
                "binding_checker": "satroot_envelope_verification_smoke",
                "authenticity": (
                    "not checked here; the envelope is matched byte for byte "
                    "against the rebuilt commitment, which says which state the "
                    "transaction carries and nothing about who broadcast it"
                ),
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
