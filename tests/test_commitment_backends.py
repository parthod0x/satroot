"""Backend-neutrality of state commitments.

The claim under test is narrow and load-bearing: the commitment a SATROOT
namespace publishes is defined independently of *where* it is published,
and more than one publication backend exists. These tests exist so that
claim cannot quietly become false.
"""

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


def test_rfc3161_request_roundtrips_the_digest():
    digest = sc.commitment_digest(sc.build_commitment_bytes(ROOT, STATE))
    request = sc.build_timestamp_request(digest, nonce=42)
    assert sc.extract_message_imprint(request) == digest


def test_rfc3161_request_rejects_non_sha256_digest():
    with pytest.raises(SatRootError):
        sc.build_timestamp_request(b"\x00" * 20)  # sha1-length


def test_verification_binds_token_to_exact_state():
    digest = sc.commitment_digest(sc.build_commitment_bytes(ROOT, STATE))
    token = sc.build_timestamp_request(digest)

    good = sc.verify_timestamp_token(token, ROOT, STATE)
    assert good["commitment_matches"] is True
    assert good["backend"] == "rfc3161"

    # A different state, or a different root, must not verify.
    assert sc.verify_timestamp_token(token, ROOT, "sha256:" + "22" * 32)["commitment_matches"] is False
    assert sc.verify_timestamp_token(token, "cd" * 32 + ":1", STATE)["commitment_matches"] is False


def test_verification_rejects_garbage_token():
    with pytest.raises(SatRootError):
        sc.verify_timestamp_token(b"not der at all", ROOT, STATE)


def test_described_backends_stay_in_sync_with_reality():
    described = sc.describe_backends()["backends"]
    assert set(described) == set(sc.BACKENDS)
    # Exactly one backend requires a blockchain; that is the property that
    # makes "optional anchoring backend" a true statement.
    assert [k for k, v in described.items() if not v["requires_chain"]] == ["rfc3161"]
