"""RFC 3161 timestamp token verification: the signature, not just the imprint.

Round 9 found the defect this module exists to fix, and one reviewer
demonstrated it in twenty minutes: the verifier read a token's 32-byte
``messageImprint`` and nothing else. Swapping those 32 bytes in place — same
length, so every DER length stays valid — minted an attestation for any
checkpoint, and the shipped verifier reported ``published: 2,
attests_action_log: true`` over a truncated action log.

Meanwhile four documents claimed "a third-party timestamp the operator cannot
reissue". Two things were wrong with that sentence. The operator *can*
reissue: a TSA stamps whatever digest you send it, today. And the one
property an operator genuinely cannot forge — **when** — was never read,
because nothing extracted ``genTime``.

What this module establishes
----------------------------

For a token that passes :func:`verify_token`:

1. The CMS ``SignedData`` signature over ``signedAttrs`` verifies under the
   public key of the certificate embedded in the token.
2. The ``messageDigest`` signed attribute equals SHA-256 of the ``TSTInfo``
   that token carries, so the signature covers the timestamp content.
3. The ``messageImprint`` inside ``TSTInfo`` is the digest supplied.
4. ``genTime`` is returned, so a caller can compare it against a time it
   already knew.

What it deliberately does **not** establish
-------------------------------------------

**That the certificate is a TSA you trust.** satledger requests tokens with
``certReq`` set, so the signing certificate travels inside the token (RFC 3161
s2.4.1 - note this is *not* automatic: ``certReq`` is DEFAULT FALSE, and when
absent the ``certificates`` field MUST NOT be present). A self-signed forgery
therefore carries a self-signed certificate and verifies happily against
itself.

Authenticating the signer is a separate step, and RFC 3161 s2.2 requires it:
the requester SHALL verify that the token "contains the correct certificate
identifier of the TSA". Skipping it is non-conformance, not a gap in the
protocol. This module refuses to fake that step: pass
``expected_signer_sha256`` to pin the certificate you mean, or rely on the
built-in list, and the result reports ``signer_pinned`` accordingly. Without
either, a passing signature proves the token is internally coherent and
nothing about who made it.

That is the honest boundary, and it is why the result object separates
``signature_verified`` from ``signer_pinned``.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_SEQUENCE = 0x30
_SET = 0x31
_INTEGER = 0x02
_OID = 0x06
_OCTET_STRING = 0x04
_CONTEXT_0 = 0xA0
_GENERALIZED_TIME = 0x18

# 1.2.840.113549.1.7.2 id-signedData
_OID_SIGNED_DATA = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x07, 0x02])
# 1.2.840.113549.1.9.16.1.4 id-ct-TSTInfo
_OID_TST_INFO = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x09, 0x10, 0x01, 0x04])
# 1.2.840.113549.1.9.4 messageDigest
_OID_MESSAGE_DIGEST = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x09, 0x04])
# 2.16.840.1.101.3.4.2.1 id-sha256
_OID_SHA256 = bytes([0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01])

# The CMS layer's digest algorithm is whatever the SignerInfo says, and it
# is not necessarily the one used for the timestamp imprint. freetsa.org
# stamps a SHA-256 imprint and signs the CMS layer over SHA-1, so hardcoding
# SHA-256 here rejected every genuine token from it.
_DIGEST_OIDS = {
    bytes([0x2B, 0x0E, 0x03, 0x02, 0x1A]): "sha1",
    bytes([0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01]): "sha256",
    bytes([0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x02]): "sha384",
    bytes([0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x03]): "sha512",
}


# Fingerprints of the authorities satledger anchors to, compiled into the
# verifier rather than read from the export.
#
# Round 10 found the defect this fixes, and it was in the instructions, not
# the code. HOW_TO_VERIFY.md told the customer to read `signer_sha256` off a
# first run and pin it. Against a forged export the first run *is* the
# forgery, so the customer pinned the attacker's self-signed certificate and
# the result flipped to `signers_pinned: 1` - the strongest signal the system
# produces - with no external check having happened. Never bootstrap trust
# from the file under examination.
#
# Verify these independently before relying on them:
#   openssl s_client -connect freetsa.org:443   (or the published CA)
KNOWN_TSA_SIGNERS = {
    "32e841a95cc1164101ffde41298ef2fc75c1c4372ef095e88a6bbd47dfb191fc":
        "freetsa.org",
    # DigiCert is the fallback authority, and until this entry existed the
    # fallback quietly sold a weaker receipt: the call succeeded, the buyer
    # was charged, signature_verified stayed true, and signer_pinned came
    # back false - which this module's own documentation tells a customer
    # not to trust. Nothing surfaced the difference; the only way to find
    # it was to make freetsa fail and read the result.
    #
    # Expiry is a known property of this one, not an oversight. The
    # subject is "DigiCert SHA256 RSA4096 Timestamp Responder 2026 1" -
    # they mint a new responder each year, so this fingerprint stops
    # matching when they rotate and the fallback returns to unpinned.
    # That is the same state as before this entry, so it degrades to the
    # old behaviour rather than breaking; re-pin from a live token when
    # the year turns.
    "2da09da7f4131f9fe72db6c5e6e9c9656755af043f1ea742cc0d2120e141ebfc":
        "digicert (responder 2026 1)",
}


class TokenError(Exception):
    """Raised when a timestamp token fails a structural or signature check."""


def _read_tlv(buf: bytes, i: int) -> Tuple[int, bytes, int, int]:
    """(tag, value, next_index, header_length) for the DER TLV at ``i``."""
    if i + 2 > len(buf):
        raise TokenError("truncated DER")
    tag = buf[i]
    if tag & 0x1F == 0x1F:
        raise TokenError("high-tag-number identifiers are not supported")
    first = buf[i + 1]
    j = i + 2
    if first < 0x80:
        length = first
    elif first == 0x80:
        raise TokenError("indefinite length is not valid DER")
    else:
        count = first & 0x7F
        if j + count > len(buf):
            raise TokenError("truncated DER length")
        raw = buf[j:j + count]
        if raw[0] == 0x00:
            raise TokenError("non-minimal DER length")
        length = int.from_bytes(raw, "big")
        j += count
    if j + length > len(buf):
        raise TokenError("DER value exceeds buffer")
    return tag, buf[j:j + length], j + length, j - i


def _children(value: bytes) -> List[Tuple[int, bytes]]:
    out = []
    i = 0
    while i < len(value):
        tag, body, i, _ = _read_tlv(value, i)
        out.append((tag, body))
    return out


def _field(items, index: int, tag: int, what: str) -> bytes:
    if index >= len(items):
        raise TokenError(f"missing {what}")
    got, body = items[index]
    if got != tag:
        raise TokenError(f"expected {what} (tag 0x{tag:02x}), found 0x{got:02x}")
    return body


def _tlv(tag: int, body: bytes) -> bytes:
    if len(body) < 0x80:
        return bytes([tag, len(body)]) + body
    raw = len(body).to_bytes((len(body).bit_length() + 7) // 8, "big")
    return bytes([tag, 0x80 | len(raw)]) + raw + body


def _content_info(token_der: bytes) -> bytes:
    """The ContentInfo, whether given a TimeStampResp or a bare token."""
    tag, body, end, _ = _read_tlv(token_der, 0)
    if tag != _SEQUENCE:
        raise TokenError("token must be a DER SEQUENCE")
    if end != len(token_der):
        raise TokenError("trailing bytes after token")
    items = _children(body)
    if not items:
        raise TokenError("empty token")
    if items[0][0] == _SEQUENCE:  # TimeStampResp: status, then the token
        if len(items) < 2:
            raise TokenError("TimeStampResp carries no timeStampToken")
        return _field(items, 1, _SEQUENCE, "timeStampToken ContentInfo")
    if items[0][0] == _OID:
        return body
    raise TokenError("not a TimeStampResp or TimeStampToken")


def _parse_gentime(raw: bytes) -> datetime:
    text = raw.decode("ascii")
    if not text.endswith("Z"):
        raise TokenError(f"genTime is not UTC: {text}")
    stem = text[:-1]
    fraction = 0
    if "." in stem:
        stem, frac_text = stem.split(".", 1)
        fraction = int(float("0." + frac_text) * 1_000_000)
    parsed = datetime.strptime(stem, "%Y%m%d%H%M%S")
    return parsed.replace(microsecond=fraction, tzinfo=timezone.utc)


def _signer_certificate(certificates, signer, x509):
    """The one certificate matching the SignerInfo's sid."""
    if len(signer) < 2:
        raise TokenError("SignerInfo has no sid")
    sid_tag, sid_body = signer[1]
    if sid_tag == _SEQUENCE:
        parts = _children(sid_body)
        if len(parts) < 2 or parts[0][0] != _SEQUENCE or parts[1][0] != _INTEGER:
            raise TokenError("SignerInfo sid is not issuerAndSerialNumber")
        issuer_der = _tlv(_SEQUENCE, parts[0][1])
        serial = int.from_bytes(parts[1][1], "big", signed=True)
        matches = [c for c in certificates
                   if c.serial_number == serial and c.issuer.public_bytes() == issuer_der]
    elif sid_tag == 0x80:  # [0] IMPLICIT SubjectKeyIdentifier
        matches = []
        for c in certificates:
            try:
                ski = c.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value.digest
            except x509.ExtensionNotFound:
                continue
            if ski == sid_body:
                matches.append(c)
    else:
        raise TokenError("SignerInfo sid has an unknown form")
    if len(matches) != 1:
        raise TokenError("no single certificate in the token matches the SignerInfo's sid "
                         "(%d match)" % len(matches))
    return matches[0]


def verify_token(
    token_der: bytes,
    expected_digest: bytes,
    *,
    expected_signer_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify an RFC 3161 token's signature, content binding and imprint.

    Raises :class:`TokenError` on any failure. Returns what was established,
    including ``genTime`` and the signer certificate's SHA-256 fingerprint.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
    from cryptography.hazmat.primitives.serialization import pkcs7

    content_info = _children(_content_info(token_der))
    if _field(content_info, 0, _OID, "contentType") != _OID_SIGNED_DATA:
        raise TokenError("ContentInfo is not id-signedData")
    explicit = _children(_field(content_info, 1, _CONTEXT_0, "content [0]"))
    signed_data = _children(_field(explicit, 0, _SEQUENCE, "SignedData"))

    # SignedData ::= { version, digestAlgorithms, encapContentInfo,
    #                  [0] certificates OPTIONAL, [1] crls OPTIONAL,
    #                  signerInfos }
    eci = _children(_field(signed_data, 2, _SEQUENCE, "encapContentInfo"))
    if _field(eci, 0, _OID, "eContentType") != _OID_TST_INFO:
        raise TokenError("encapsulated content is not id-ct-TSTInfo")
    econtent = _children(_field(eci, 1, _CONTEXT_0, "eContent [0]"))
    tst_der = _field(econtent, 0, _OCTET_STRING, "eContent OCTET STRING")

    signer_infos = None
    for tag, body in signed_data[3:]:
        if tag == _SET:
            signer_infos = body
    if signer_infos is None:
        raise TokenError("SignedData has no signerInfos")
    signer = _children(_children(signer_infos)[0][1]) if _children(signer_infos) else None
    if signer is None:
        raise TokenError("SignedData has no SignerInfo")

    signed_attrs_raw = None
    signature = None
    sequences = []
    for tag, body in signer:
        if tag == _CONTEXT_0 and signed_attrs_raw is None:
            signed_attrs_raw = body
        elif tag == _OCTET_STRING:
            signature = body
        elif tag == _SEQUENCE:
            sequences.append(body)
    # SignerInfo ::= { version, sid, digestAlgorithm, [0] signedAttrs,
    #                  signatureAlgorithm, signature }
    if len(sequences) < 2:
        raise TokenError("SignerInfo is missing its algorithm identifiers")
    digest_oid = _field(_children(sequences[1]), 0, _OID, "digestAlgorithm")
    digest_name = _DIGEST_OIDS.get(digest_oid)
    if digest_name is None:
        raise TokenError(f"unsupported CMS digest algorithm: {digest_oid.hex()}")
    if signed_attrs_raw is None:
        raise TokenError("SignerInfo has no signedAttrs; unsupported")
    if signature is None:
        raise TokenError("SignerInfo has no signature")

    # The signature is computed over the signedAttrs re-tagged as SET OF,
    # not over the [0] IMPLICIT form they appear in. RFC 5652 s5.4.
    to_be_verified = _tlv(_SET, signed_attrs_raw)

    # messageDigest must equal SHA-256 of the TSTInfo the token carries, so
    # the signature actually covers the timestamp content.
    message_digest = None
    for tag, body in _children(signed_attrs_raw):
        if tag != _SEQUENCE:
            continue
        attr = _children(body)
        if attr and attr[0][0] == _OID and attr[0][1] == _OID_MESSAGE_DIGEST:
            values = _children(attr[1][1])
            if values and values[0][0] == _OCTET_STRING:
                message_digest = values[0][1]
    if message_digest is None:
        raise TokenError("signedAttrs has no messageDigest attribute")
    if message_digest != hashlib.new(digest_name, tst_der).digest():
        raise TokenError(
            "messageDigest does not match the TSTInfo carried by this token: "
            "the signature does not cover this content"
        )

    # load_der_pkcs7_certificates wants the ContentInfo TLV, not its body.
    certificates = pkcs7.load_der_pkcs7_certificates(
        _tlv(_SEQUENCE, _content_info(token_der))
    )
    if not certificates:
        raise TokenError(
            "token embeds no certificate, so its signature cannot be checked"
        )
    # The certificate the SignerInfo names, not the first one carried: a
    # token may carry a chain in any order. RFC 5652 s5.3: sid is
    # issuerAndSerialNumber, or [0] subjectKeyIdentifier.
    signer_cert = _signer_certificate(certificates, signer, x509)

    public_key = signer_cert.public_key()
    hash_algorithm = {
        "sha1": hashes.SHA1(),
        "sha256": hashes.SHA256(),
        "sha384": hashes.SHA384(),
        "sha512": hashes.SHA512(),
    }[digest_name]
    try:
        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(
                signature, to_be_verified, padding.PKCS1v15(), hash_algorithm
            )
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(signature, to_be_verified, ec.ECDSA(hash_algorithm))
        else:
            raise TokenError(
                f"unsupported TSA key type: {type(public_key).__name__}"
            )
    except TokenError:
        raise
    except Exception as exc:  # noqa: BLE001 - any failure is a failed signature
        raise TokenError(f"timestamp token signature is invalid: {exc}") from exc

    # TSTInfo ::= { version, policy, messageImprint, serialNumber, genTime, ... }
    tag, tst_body, tst_end, _ = _read_tlv(tst_der, 0)
    if tag != _SEQUENCE or tst_end != len(tst_der):
        raise TokenError("TSTInfo is not a well-formed SEQUENCE")
    tst = _children(tst_body)
    imprint = _children(_field(tst, 2, _SEQUENCE, "messageImprint"))
    algorithm = _children(_field(imprint, 0, _SEQUENCE, "hashAlgorithm"))
    if _field(algorithm, 0, _OID, "hashAlgorithm OID") != _OID_SHA256:
        raise TokenError("messageImprint is not SHA-256")
    carried = _field(imprint, 1, _OCTET_STRING, "hashedMessage")
    if carried != expected_digest:
        raise TokenError(
            "timestamp token attests a different digest than expected"
        )

    gen_time = None
    for tag, body in tst[3:]:
        if tag == _GENERALIZED_TIME:
            gen_time = _parse_gentime(body)
            break
    if gen_time is None:
        raise TokenError("TSTInfo has no genTime")

    fingerprint = hashlib.sha256(
        signer_cert.public_bytes(
            __import__(
                "cryptography.hazmat.primitives.serialization",
                fromlist=["Encoding"],
            ).Encoding.DER
        )
    ).hexdigest()

    pinned = False
    trusted_via = None
    if expected_signer_sha256 is not None:
        if fingerprint.lower() != expected_signer_sha256.lower().replace(":", ""):
            raise TokenError(
                "timestamp token signer certificate is not the pinned one: "
                f"expected {expected_signer_sha256}, got {fingerprint}"
            )
        pinned = True
        trusted_via = "explicit pin"
    elif fingerprint.lower() in KNOWN_TSA_SIGNERS:
        # A compiled-in fingerprint is a real trust decision made in advance,
        # unlike one read off the export being checked.
        pinned = True
        trusted_via = f"built-in ({KNOWN_TSA_SIGNERS[fingerprint.lower()]})"

    return {
        "signature_verified": True,
        # Surfaced deliberately: several public TSAs still sign the CMS layer
        # with SHA-1. That is the authority's choice, not something to hide.
        "cms_digest_algorithm": digest_name,
        "gen_time": gen_time.isoformat(),
        "signer_subject": signer_cert.subject.rfc4514_string(),
        "signer_sha256": fingerprint,
        # Our tokens carry their signing certificate (certReq set), so a
        # self-signed forgery verifies against itself. Only a pin, or a
        # match against the built-in list, makes this third-party evidence.
        "signer_pinned": bool(pinned),
        "trusted_via": trusted_via,
        "note": (
            "signature and content binding verified; the certificate is the "
            "one the token carries, so trust it only if signer_pinned is true "
            "or you validated the chain yourself"
        ),
    }
