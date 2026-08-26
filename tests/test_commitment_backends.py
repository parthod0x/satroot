"""Backend-neutrality of state commitments.

The claim under test is narrow and load-bearing: the commitment a SATROOT
namespace publishes is defined independently of *where* it is published,
and more than one publication backend exists. These tests exist so that
claim cannot quietly become false.
"""

import pathlib

import pytest

import satroot_commitment as sc
import satroot_onchain_envelope_smoke as env
from satroot1 import SatRootError

ROOT = "ab" * 32 + ":0"
STATE = "sha256:" + "11" * 32


def test_backends_commit_byte_identical_documents():
    """The whole point: the chain backend has no special commitment format."""
    assert sc.build_commitment_bytes(ROOT, STATE) == env.build_envelope_payload(ROOT, STATE)


def test_commitment_is_canonical_and_stable():
    first = sc.build_commitment_bytes(ROOT, STATE)
    assert first == sc.build_commitment_bytes(ROOT, STATE)
    # Canonical JSON: sorted keys, no whitespace.
    assert first.decode() == (
        '{"protocol":"SATROOT-1","root_id":"%s","state_hash":"%s"}' % (ROOT, STATE)
    )


def test_commitment_rejects_malformed_inputs():
    for bad_state in ("", "sha256:zz", "sha256:" + "11" * 31, "11" * 32, None):
        with pytest.raises(SatRootError):
            sc.build_commitment_bytes(ROOT, bad_state)
    with pytest.raises(SatRootError):
        sc.build_commitment_bytes("not-an-outpoint", STATE)


def test_rfc3161_request_carries_the_digest_at_its_defined_position():
    """Check the request as a TimeStampReq, by structure (RFC 3161 s2.4.1).

    This used to assert `extract_message_imprint(request) == digest`, feeding
    the module's own request back into the token parser. That is what let one
    wrong model of the ASN.1 live in the code and its tests at once: a request
    is not a token, and the parser is now right to refuse it.
    """
    digest = sc.commitment_digest(sc.build_commitment_bytes(ROOT, STATE))
    request = sc.build_timestamp_request(digest, nonce=42)

    tag, body, end = sc._read_tlv(request, 0)
    assert tag == sc._SEQUENCE and end == len(request)
    items = sc._children(body)
    assert items[0] == (sc._INTEGER, b"\x01")            # version
    imprint = sc._children(items[1][1])                  # messageImprint
    algorithm = sc._children(imprint[0][1])
    assert algorithm[0] == (sc._OID, sc._OID_SHA256)
    assert imprint[1] == (sc._OCTET_STRING, digest)


def test_rfc3161_request_rejects_non_sha256_digest():
    with pytest.raises(SatRootError):
        sc.build_timestamp_request(b"\x00" * 20)  # sha1-length


FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "rfc3161"
REAL_TOKENS = sorted(FIXTURES.glob("*.tsr"))


def _token(name):
    return (FIXTURES / name).read_bytes()


@pytest.mark.parametrize("path", REAL_TOKENS, ids=lambda p: p.stem)
def test_real_tsa_tokens_parse_and_bind(path):
    """Genuine tokens from two independent authorities.

    Until these were checked in, every fixture reaching this parser was a
    TimeStampReq that this module had built and handed back to itself, so
    the implementation and its tests shared one wrong model of the ASN.1.
    Both real tokens were rejected by the code that those tests passed.
    """
    result = sc.verify_timestamp_token(path.read_bytes(), ROOT, STATE)
    assert result["binding_matches"] is True
    assert result["backend"] == "rfc3161"
    assert result["signature_verified"] is False
    assert result["chain_validated"] is False


def test_both_authorities_are_present():
    """One TSA is not a corpus, and the two differ where it matters.

    freetsa.org signs with the ESS v1 signingCertificate attribute and
    DigiCert with signingCertificateV2 (RFC 5035 s4) - the attribute whose
    ESSCertIDv2 has the same shape as a messageImprint. Keeping one of each
    means the fixture set covers the structure a shape search confuses.
    """
    assert {p.stem for p in REAL_TOKENS} == {"freetsa-org", "digicert"}


@pytest.mark.parametrize("path", REAL_TOKENS, ids=lambda p: p.stem)
def test_real_token_does_not_bind_to_a_different_state(path):
    token = path.read_bytes()
    assert sc.verify_timestamp_token(token, ROOT, "sha256:" + "22" * 32)["binding_matches"] is False
    assert sc.verify_timestamp_token(token, "cd" * 32 + ":1", STATE)["binding_matches"] is False


def test_a_timestamp_request_is_not_a_timestamp_token():
    """The exact regression. A request carries a correct messageImprint and
    no signature; the previous parser accepted it as a token, because a
    TimeStampReq is SEQUENCEs all the way down and its shape search could
    traverse nothing else. Reading fields by position rejects it on
    structure, before the digest is ever compared.
    """
    digest = sc.commitment_digest(sc.build_commitment_bytes(ROOT, STATE))
    request = sc.build_timestamp_request(digest)
    with pytest.raises(SatRootError):
        sc.extract_message_imprint(request)


def test_imprint_shaped_decoy_is_not_mistaken_for_a_token():
    """A bare SEQUENCE{ AlgorithmIdentifier(sha256), OCTET STRING(32) } is
    the shape of a messageImprint - and also of an ESSCertIDv2 certHash
    when the defaulted algorithm is written out. Carrying the right digest
    must not be enough.
    """
    digest = sc.commitment_digest(sc.build_commitment_bytes(ROOT, STATE))
    algorithm = sc._tlv(sc._SEQUENCE, sc._tlv(sc._OID, sc._OID_SHA256) + sc._tlv(sc._NULL, b""))
    decoy = sc._tlv(sc._SEQUENCE, sc._tlv(sc._SEQUENCE, algorithm + sc._tlv(sc._OCTET_STRING, digest)))
    with pytest.raises(SatRootError):
        sc.extract_message_imprint(decoy)


def test_verification_rejects_garbage_token():
    with pytest.raises(SatRootError):
        sc.verify_timestamp_token(b"not der at all", ROOT, STATE)


def test_der_parser_rejects_ber_and_high_tag_forms():
    """DER, not BER."""
    with pytest.raises(SatRootError):  # non-minimal length
        sc._read_tlv(bytes([0x30, 0x82, 0x00, 0x05]) + b"\x00" * 5, 0)
    with pytest.raises(SatRootError):  # indefinite length
        sc._read_tlv(bytes([0x30, 0x80]), 0)
    with pytest.raises(SatRootError):  # high-tag-number identifier
        sc._read_tlv(bytes([0x3F, 0x01, 0x02, 0x00]), 0)


def test_nonce_encoding_and_rejection():
    digest = sc.commitment_digest(sc.build_commitment_bytes(ROOT, STATE))
    # DER INTEGER: a pad octet exactly when the high bit would otherwise set.
    assert b"\x02\x02\x00\x80" in sc.build_timestamp_request(digest, nonce=128)
    assert b"\x02\x01\x7f" in sc.build_timestamp_request(digest, nonce=127)
    with pytest.raises(SatRootError):
        sc.build_timestamp_request(digest, nonce=-1)


def test_described_backends_stay_in_sync_with_reality():
    described = sc.describe_backends()["backends"]
    assert set(described) == set(sc.BACKENDS)
    # Exactly one backend requires a blockchain; that is the property that
    # makes "optional anchoring backend" a true statement.
    assert [k for k, v in described.items() if not v["requires_chain"]] == ["rfc3161"]


def test_no_backend_advertises_more_than_it_does():
    """Naming discipline applies to both backends, not just the one a
    reviewer happened to look at.
    """
    for name, described in sc.describe_backends()["backends"].items():
        assert "verifier" not in described, name
        assert "binding_checker" in described, name
        assert "authenticity" in described, name


def test_rfc3161_binding_check_makes_no_authenticity_claim():
    """A real token whose signature is never checked still reports a match.

    The point is not that a forgery passes - it is that this function
    answers only *which* state a token commits to. Authenticity needs a CMS
    verifier and a TSA trust decision, neither of which lives here.
    """
    result = sc.verify_timestamp_token(_token("freetsa-org.tsr"), ROOT, STATE)
    assert result["binding_matches"] is True
    assert result["signature_verified"] is False
    assert result["chain_validated"] is False
    assert "NOT checked" in result["note"]


def test_commitment_uses_the_kernel_canonical_form():
    """One definition of canonical JSON, not two with different defaults."""
    from satroot1 import canonical_json

    payload = {"protocol": "SATROOT-1", "root_id": ROOT, "state_hash": STATE}
    assert sc.build_commitment_bytes(ROOT, STATE) == canonical_json(payload).encode("utf-8")
