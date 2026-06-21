import copy
import json
from pathlib import Path

import pytest

from satroot1 import (
    annotate_ledger_events,
    bootstrap_ed25519_workflow,
    bootstrap_hmac_workflow,
    bootstrap_signed_ledger_bundle,
    build_signed_ledger_bundle_manifest,
    build_signer_key_map,
    derive_ed25519_public_keys,
    generate_ed25519_private_keys,
    generate_hmac_shared_secrets,
    SatRootError,
    ed25519_available,
    ed25519_public_key_hex,
    ed25519_sign,
    event_id,
    hmac_sha256_sign,
    load_bundle_manifest_schema,
    load_protocol_schema,
    load_profile_registry,
    main,
    make_ed25519_verifier,
    make_hmac_sha256_verifier,
    replay,
    rendered_json_sha256,
    sha256_hex,
    sign_ledger_events,
    signing_payload,
    validate_instance_against_schema,
    verify_signed_ledger_bundle,
)


ROOT = Path(__file__).resolve().parents[1]


def load_events(name="events_floor1.json"):
    return json.loads((ROOT / "examples" / name).read_text())


def write_json(path: Path, data):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def build_rotation_ledger():
    genesis = copy.deepcopy(load_events()[0])
    genesis["max_supply"] = "1000000000"
    genesis["initial_balances"] = {"issuer": "900000000"}

    rotate = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "action": "rotate-authority",
        "root_id": genesis["root_id"],
        "sequence": 1,
        "prev_event_id": event_id(genesis),
        "new_mint_authority": "issuer_v2",
        "signer": "issuer",
        "signature": "demo",
    }
    mint = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "action": "mint",
        "root_id": genesis["root_id"],
        "sequence": 2,
        "prev_event_id": event_id(rotate),
        "to": "alice",
        "amount": "50000000",
        "signer": "issuer_v2",
        "signature": "demo",
    }
    return [genesis, rotate, mint]


def test_replay_demo_ledger():
    state = replay(load_events())
    assert state.symbol == "FLOOR1"
    assert state.supply == 999_000_000
    assert state.balances["issuer"] == 750_000_000
    assert state.balances["alice"] == 150_000_000
    assert state.balances["bob"] == 99_000_000
    assert state.transfer_model == "account-ledger"
    assert state.genesis_metadata["rules_hash"] == "sha256:demo"
    assert state.genesis_metadata["nonce"] == "satroot-v0.1-demo"


def test_reject_overspend():
    events = load_events()
    bad = copy.deepcopy(events[-1])
    bad["sequence"] = 4
    bad["prev_event_id"] = event_id(events[-1])
    bad["from"] = "bob"
    bad["amount"] = "999999999999"
    bad["signer"] = "bob"
    events.append(bad)
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_wrong_root():
    events = load_events()
    events[1]["root_id"] = "f" * 64 + ":0"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_zero_amount_transfer():
    events = load_events()
    bad = copy.deepcopy(events[1])
    bad["amount"] = "0"
    events[1] = bad
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_missing_signature():
    events = load_events()
    bad = copy.deepcopy(events[1])
    del bad["signature"]
    events[1] = bad
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_unsupported_signature_scheme():
    events = load_events()
    events[1]["signature_scheme"] = "rsa2048"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_demo_signature_with_key_id():
    events = load_events()
    events[1]["signature_scheme"] = "demo"
    events[1]["signature_key_id"] = "demo-key"
    with pytest.raises(SatRootError):
        replay(events)


def test_replay_stable_profile_demo():
    state = replay(load_events("events_usdroot1.json"))
    assert state.symbol == "USDROOT1"
    assert state.decimals == 2
    assert state.supply == 24_995_000
    assert state.balances["issuer"] == 23_500_000
    assert state.balances["merchant"] == 1_245_000
    assert state.balances["api_node"] == 250_000
    assert state.genesis_metadata["reference_unit"] == "USD"
    assert state.genesis_metadata["redemption"] == "none"
    assert state.genesis_metadata["reserve_model"] == "none"
    assert state.snapshot()["genesis_metadata"]["intended_use"] == "invoice-credit-accounting"


def test_replay_machine_profile_demo():
    state = replay(load_events("events_apicredit1.json"))
    assert state.symbol == "APICREDIT1"
    assert state.decimals == 0
    assert state.supply == 99_800_000
    assert state.balances["issuer"] == 95_000_000
    assert state.balances["tenant_a"] == 3_800_000
    assert state.balances["worker_node"] == 1_000_000


def test_replay_receipt_profile_demo():
    state = replay(load_events("events_receipt1.json"))
    assert state.symbol == "RECEIPT1"
    assert state.decimals == 0
    assert state.supply == 0
    assert state.balances["issuer"] == 0
    assert state.balances["buyer"] == 0
    assert state.balances["archive"] == 0


def test_replay_identity_profile_demo():
    state = replay(load_events("events_identity1.json"))
    assert state.symbol == "IDENTITY1"
    assert state.decimals == 0
    assert state.supply == 0
    assert state.balances["issuer"] == 0
    assert state.balances["node_alpha"] == 0
    assert state.balances["rotated_controller"] == 0


def test_replay_license_profile_demo():
    state = replay(load_events("events_license1.json"))
    assert state.symbol == "LICENSE1"
    assert state.decimals == 0
    assert state.supply == 0
    assert state.balances["issuer"] == 0
    assert state.balances["customer"] == 0
    assert state.balances["archive"] == 0


def test_rotate_authority_allows_new_minter():
    state = replay(build_rotation_ledger())
    assert state.mint_authority == "issuer_v2"
    assert state.supply == 950_000_000
    assert state.balances["issuer"] == 900_000_000
    assert state.balances["alice"] == 50_000_000


def test_reject_unauthorized_rotate_authority():
    events = build_rotation_ledger()
    events[1]["signer"] = "alice"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_mint_by_old_authority_after_rotation():
    events = build_rotation_ledger()
    events[2]["signer"] = "issuer"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_unknown_profile():
    events = load_events()
    events[0]["profile"] = "SATROOT-UNKNOWN-1"
    events[0]["profile_mode"] = "unknown-mode"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_bad_profile_mode():
    events = load_events("events_usdroot1.json")
    events[0]["profile_mode"] = "wrong-mode"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_event_id_mismatch():
    events = load_events()
    events[1]["event_id"] = "sha256:" + ("0" * 64)
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_state_hash_mismatch():
    events = load_events()
    events[1]["state_hash"] = "sha256:" + ("0" * 64)
    with pytest.raises(SatRootError):
        replay(events)


def test_accept_matching_event_id_and_state_hash():
    events = load_events()
    probe = replay(events[:2])
    events[1]["state_hash"] = probe.state_hash()
    events[1]["event_id"] = event_id(events[1])
    final_state = replay(events)
    assert final_state.symbol == "FLOOR1"


def test_floor1_state_hash_regression():
    state = replay(load_events())
    assert state.state_hash() == "sha256:5e57031b9c736b6d3d6f73c07e9df5d6d86123af032119e16148859080797721"


def test_profile_registry_contains_supported_profiles():
    registry = load_profile_registry()
    assert registry["SATROOT-STABLE-1"]["profile_mode"] == "reference-only"
    assert registry["SATROOT-LICENSE-1"]["required_fields"][-1] == "intended_use"


def test_load_protocol_schema_supports_rotate_authority():
    schema = load_protocol_schema()
    assert "rotate-authority" in schema["properties"]["action"]["enum"]


def test_load_bundle_manifest_schema_supports_signed_ledger_bundles():
    schema = load_bundle_manifest_schema()
    assert schema["properties"]["bundle_type"]["const"] == "signed-ledger"
    assert "hmac-sha256" in schema["properties"]["scheme"]["enum"]


def test_validate_instance_against_schema_accepts_demo_ledger():
    count = validate_instance_against_schema(load_events())
    assert count == 4


def test_validate_instance_against_schema_rejects_bad_signature_shape():
    events = load_events()
    events[1]["signature_scheme"] = "hmac-sha256"
    events[1]["signature"] = "demo"
    with pytest.raises(SatRootError):
        validate_instance_against_schema(events)


def test_annotate_ledger_events_adds_commitments():
    annotated = annotate_ledger_events(load_events())
    assert annotated[0]["event_id"].startswith("sha256:")
    assert annotated[0]["state_hash"].startswith("sha256:")
    assert annotated[-1]["event_id"].startswith("sha256:")
    assert annotated[-1]["state_hash"].startswith("sha256:")
    state = replay(annotated)
    assert state.symbol == "FLOOR1"


def test_annotate_ledger_events_preserves_hmac_replay():
    events = load_events()
    secrets = {"issuer-key": "issuer-secret", "alice-key": "alice-secret", "bob-key": "bob-secret"}
    signer_keys = {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}
    prev = event_id(events[0])
    for event in events[1:]:
        event["prev_event_id"] = prev
        event["signature_scheme"] = "hmac-sha256"
        event["signature_key_id"] = signer_keys[event["signer"]]
        event["signature"] = hmac_sha256_sign(signing_payload(event), secrets[event["signature_key_id"]])
        prev = event_id(event)

    verifier = make_hmac_sha256_verifier(secrets)
    annotated = annotate_ledger_events(events, verifier=verifier)
    state = replay(annotated, verifier=verifier)
    assert state.symbol == "FLOOR1"


def test_reject_missing_required_profile_field():
    events = load_events("events_identity1.json")
    del events[0]["subject_id"]
    with pytest.raises(SatRootError):
        replay(events)


def test_signing_payload_excludes_unsigned_fields():
    event = copy.deepcopy(load_events()[1])
    event["event_id"] = "sha256:" + ("1" * 64)
    event["state_hash"] = "sha256:" + ("2" * 64)
    payload = signing_payload(event)
    parsed = json.loads(payload)
    assert "signature" not in parsed
    assert "event_id" not in parsed
    assert "state_hash" not in parsed
    assert parsed["action"] == "transfer"


def test_replay_with_custom_signature_verifier():
    events = load_events()
    prev = event_id(events[0])
    for event in events[1:]:
        event["prev_event_id"] = prev
        event["signature"] = "sha256:" + sha256_hex(signing_payload(event))
        prev = event_id(event)

    def hash_verifier(event, payload):
        return event["signature"] == "sha256:" + sha256_hex(payload)

    state = replay(events, verifier=hash_verifier)
    assert state.symbol == "FLOOR1"


def test_replay_with_hmac_sha256_verifier():
    events = load_events()
    secrets = {"issuer-key": "issuer-secret", "alice-key": "alice-secret", "bob-key": "bob-secret"}
    signer_keys = {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}
    prev = event_id(events[0])
    for event in events[1:]:
        event["prev_event_id"] = prev
        event["signature_scheme"] = "hmac-sha256"
        event["signature_key_id"] = signer_keys[event["signer"]]
        event["signature"] = hmac_sha256_sign(signing_payload(event), secrets[event["signature_key_id"]])
        prev = event_id(event)

    verifier = make_hmac_sha256_verifier(secrets)
    state = replay(events, verifier=verifier)
    assert state.symbol == "FLOOR1"


def test_hmac_sha256_verifier_rejects_wrong_secret():
    events = load_events()
    secrets = {"issuer-key": "issuer-secret", "alice-key": "alice-secret", "bob-key": "bob-secret"}
    signer_keys = {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}
    prev = event_id(events[0])
    for event in events[1:]:
        event["prev_event_id"] = prev
        event["signature_scheme"] = "hmac-sha256"
        event["signature_key_id"] = signer_keys[event["signer"]]
        event["signature"] = hmac_sha256_sign(signing_payload(event), secrets[event["signature_key_id"]])
        prev = event_id(event)

    bad_verifier = make_hmac_sha256_verifier({"issuer-key": "wrong", "alice-key": "wrong", "bob-key": "wrong"})
    with pytest.raises(SatRootError):
        replay(events, verifier=bad_verifier)


def test_reject_hmac_signature_without_key_id():
    events = load_events()
    prev = event_id(events[0])
    for event in events[1:]:
        event["prev_event_id"] = prev
        event["signature_scheme"] = "hmac-sha256"
        event["signature"] = hmac_sha256_sign(signing_payload(event), "shared-secret")
        prev = event_id(event)

    with pytest.raises(SatRootError):
        replay(events, verifier=make_hmac_sha256_verifier({"issuer-key": "shared-secret"}))


def test_ed25519_availability_or_sign_verify_roundtrip():
    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            ed25519_sign("payload", "00" * 32)
        with pytest.raises(SatRootError):
            derive_ed25519_public_keys({"issuer-key": "00" * 32})
        return

    secrets = {
        "issuer-key": "11" * 32,
        "alice-key": "22" * 32,
        "bob-key": "33" * 32,
    }
    public_keys = {key_id: ed25519_public_key_hex(private_key_hex) for key_id, private_key_hex in secrets.items()}
    events = load_events()
    signer_keys = {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}
    prev = event_id(events[0])
    for event in events[1:]:
        event["prev_event_id"] = prev
        event["signature_scheme"] = "ed25519"
        event["signature_key_id"] = signer_keys[event["signer"]]
        event["signature"] = ed25519_sign(signing_payload(event), secrets[event["signature_key_id"]])
        prev = event_id(event)

    verifier = make_ed25519_verifier(public_keys)
    state = replay(events, verifier=verifier)
    assert state.symbol == "FLOOR1"


def test_ed25519_verifier_rejects_wrong_key_when_available():
    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            make_ed25519_verifier({"issuer-key": "00" * 32})
        return

    secrets = {
        "issuer-key": "11" * 32,
        "alice-key": "22" * 32,
        "bob-key": "33" * 32,
    }
    public_keys = {key_id: ed25519_public_key_hex(private_key_hex) for key_id, private_key_hex in secrets.items()}
    events = load_events()
    signer_keys = {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}
    prev = event_id(events[0])
    for event in events[1:]:
        event["prev_event_id"] = prev
        event["signature_scheme"] = "ed25519"
        event["signature_key_id"] = signer_keys[event["signer"]]
        event["signature"] = ed25519_sign(signing_payload(event), secrets[event["signature_key_id"]])
        prev = event_id(event)

    wrong_public_keys = {"issuer-key": "44" * 32, "alice-key": "55" * 32, "bob-key": "66" * 32}
    verifier = make_ed25519_verifier(wrong_public_keys)
    with pytest.raises(SatRootError):
        replay(events, verifier=verifier)


def test_derive_ed25519_public_keys_when_available():
    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            derive_ed25519_public_keys({"issuer-key": "00" * 32})
        return

    public_keys = derive_ed25519_public_keys({"issuer-key": "11" * 32, "alice-key": "22" * 32})
    assert public_keys["issuer-key"] == ed25519_public_key_hex("11" * 32)
    assert public_keys["alice-key"] == ed25519_public_key_hex("22" * 32)


def test_generate_ed25519_private_keys_creates_hex_map():
    private_keys = generate_ed25519_private_keys(["issuer-key", "alice-key"])
    assert set(private_keys) == {"issuer-key", "alice-key"}
    assert len(private_keys["issuer-key"]) == 64
    assert len(private_keys["alice-key"]) == 64
    assert private_keys["issuer-key"] != private_keys["alice-key"]
    int(private_keys["issuer-key"], 16)
    int(private_keys["alice-key"], 16)


def test_generate_ed25519_private_keys_rejects_duplicate_key_ids():
    with pytest.raises(SatRootError):
        generate_ed25519_private_keys(["issuer-key", "issuer-key"])


def test_build_signer_key_map_uses_ledger_signers():
    signer_key_map = build_signer_key_map(load_events())
    assert signer_key_map == {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}


def test_build_signer_key_map_supports_prefix_and_suffix():
    signer_key_map = build_signer_key_map(load_events(), key_prefix="satroot-", key_suffix="-ed25519")
    assert signer_key_map["issuer"] == "satroot-issuer-ed25519"
    assert signer_key_map["alice"] == "satroot-alice-ed25519"
    assert signer_key_map["bob"] == "satroot-bob-ed25519"


def test_build_signer_key_map_rejects_missing_signer():
    events = load_events()
    del events[1]["signer"]
    with pytest.raises(SatRootError):
        build_signer_key_map(events)


def test_bootstrap_ed25519_workflow_when_available():
    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            bootstrap_ed25519_workflow(load_events())
        return

    material = bootstrap_ed25519_workflow(load_events())
    assert material["signer_key_map"] == {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}
    assert set(material["private_keys"]) == {"issuer-key", "alice-key", "bob-key"}
    assert set(material["public_keys"]) == {"issuer-key", "alice-key", "bob-key"}
    assert material["public_keys"]["issuer-key"] == ed25519_public_key_hex(material["private_keys"]["issuer-key"])


def test_generate_hmac_shared_secrets_creates_hex_map():
    shared_secrets = generate_hmac_shared_secrets(["issuer-key", "alice-key"])
    assert set(shared_secrets) == {"issuer-key", "alice-key"}
    assert len(shared_secrets["issuer-key"]) == 64
    assert len(shared_secrets["alice-key"]) == 64
    assert shared_secrets["issuer-key"] != shared_secrets["alice-key"]
    int(shared_secrets["issuer-key"], 16)
    int(shared_secrets["alice-key"], 16)


def test_generate_hmac_shared_secrets_rejects_duplicate_key_ids():
    with pytest.raises(SatRootError):
        generate_hmac_shared_secrets(["issuer-key", "issuer-key"])


def test_bootstrap_hmac_workflow_from_ledger():
    material = bootstrap_hmac_workflow(load_events())
    assert material["signer_key_map"] == {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}
    assert set(material["shared_secrets"]) == {"issuer-key", "alice-key", "bob-key"}
    assert len(material["shared_secrets"]["issuer-key"]) == 64


def test_bootstrap_signed_ledger_bundle_hmac_roundtrip():
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    verifier = make_hmac_sha256_verifier(bundle["material"]["shared_secrets"])
    assert replay(bundle["signed_events"], verifier=verifier).symbol == "FLOOR1"
    assert bundle["annotated_events"] is not None
    assert bundle["annotated_events"][0]["event_id"].startswith("sha256:")
    assert bundle["annotated_events"][-1]["state_hash"].startswith("sha256:")
    assert bundle["final_state_snapshot"]["symbol"] == "FLOOR1"
    assert bundle["final_state_hash"].startswith("sha256:")


def test_build_signed_ledger_bundle_manifest_summarizes_bundle():
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    manifest = build_signed_ledger_bundle_manifest(
        bundle,
        output_files={
            "signer_key_map": "signer_key_map.json",
            "secrets": "secrets.json",
            "signed_events": "signed_events.json",
            "annotated_signed_events": "annotated_signed_events.json",
            "bundle_manifest": "bundle_manifest.json",
        },
        output_file_hashes={
            "signer_key_map": rendered_json_sha256(bundle["material"]["signer_key_map"]),
            "secrets": rendered_json_sha256(bundle["material"]["shared_secrets"]),
            "signed_events": rendered_json_sha256(bundle["signed_events"]),
            "annotated_signed_events": rendered_json_sha256(bundle["annotated_events"]),
        },
    )
    assert manifest["protocol"] == "SATROOT-1"
    assert manifest["bundle_type"] == "signed-ledger"
    assert manifest["scheme"] == "hmac-sha256"
    assert manifest["record_count"] == 4
    assert manifest["symbol"] == "FLOOR1"
    assert manifest["files"]["bundle_manifest"] == "bundle_manifest.json"
    assert manifest["file_hashes"]["signed_events"].startswith("sha256:")
    assert manifest["final_state_hash"].startswith("sha256:")


def test_validate_instance_against_bundle_manifest_schema_accepts_generated_manifest():
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    manifest = build_signed_ledger_bundle_manifest(
        bundle,
        output_files={
            "signer_key_map": "signer_key_map.json",
            "secrets": "secrets.json",
            "signed_events": "signed_events.json",
            "annotated_signed_events": "annotated_signed_events.json",
            "bundle_manifest": "bundle_manifest.json",
        },
        output_file_hashes={
            "signer_key_map": rendered_json_sha256(bundle["material"]["signer_key_map"]),
            "secrets": rendered_json_sha256(bundle["material"]["shared_secrets"]),
            "signed_events": rendered_json_sha256(bundle["signed_events"]),
            "annotated_signed_events": rendered_json_sha256(bundle["annotated_events"]),
        },
    )
    count = validate_instance_against_schema(manifest, load_bundle_manifest_schema())
    assert count == 1


def test_validate_instance_against_bundle_manifest_schema_rejects_bad_scheme():
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    manifest = build_signed_ledger_bundle_manifest(
        bundle,
        output_files={
            "signer_key_map": "signer_key_map.json",
            "secrets": "secrets.json",
            "signed_events": "signed_events.json",
            "annotated_signed_events": "annotated_signed_events.json",
            "bundle_manifest": "bundle_manifest.json",
        },
        output_file_hashes={
            "signer_key_map": rendered_json_sha256(bundle["material"]["signer_key_map"]),
            "secrets": rendered_json_sha256(bundle["material"]["shared_secrets"]),
            "signed_events": rendered_json_sha256(bundle["signed_events"]),
            "annotated_signed_events": rendered_json_sha256(bundle["annotated_events"]),
        },
    )
    manifest["scheme"] = "demo"
    with pytest.raises(SatRootError):
        validate_instance_against_schema(manifest, load_bundle_manifest_schema())


def test_verify_signed_ledger_bundle_accepts_hmac_bundle(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    manifest = build_signed_ledger_bundle_manifest(
        bundle,
        output_files={
            "signer_key_map": "signer_key_map.json",
            "secrets": "secrets.json",
            "signed_events": "signed_events.json",
            "annotated_signed_events": "annotated_signed_events.json",
            "bundle_manifest": "bundle_manifest.json",
        },
        output_file_hashes={
            "signer_key_map": rendered_json_sha256(bundle["material"]["signer_key_map"]),
            "secrets": rendered_json_sha256(bundle["material"]["shared_secrets"]),
            "signed_events": rendered_json_sha256(bundle["signed_events"]),
            "annotated_signed_events": rendered_json_sha256(bundle["annotated_events"]),
        },
    )
    write_json(tmp_path / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(tmp_path / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(tmp_path / "signed_events.json", bundle["signed_events"])
    write_json(tmp_path / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(tmp_path / "bundle_manifest.json", manifest)

    summary = verify_signed_ledger_bundle(tmp_path)
    assert summary["scheme"] == "hmac-sha256"
    assert summary["symbol"] == "FLOOR1"
    assert summary["annotated_verified"] is True


def test_verify_signed_ledger_bundle_rejects_manifest_mismatch(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    manifest = build_signed_ledger_bundle_manifest(
        bundle,
        output_files={
            "signer_key_map": "signer_key_map.json",
            "secrets": "secrets.json",
            "signed_events": "signed_events.json",
            "annotated_signed_events": "annotated_signed_events.json",
            "bundle_manifest": "bundle_manifest.json",
        },
        output_file_hashes={
            "signer_key_map": rendered_json_sha256(bundle["material"]["signer_key_map"]),
            "secrets": rendered_json_sha256(bundle["material"]["shared_secrets"]),
            "signed_events": rendered_json_sha256(bundle["signed_events"]),
            "annotated_signed_events": rendered_json_sha256(bundle["annotated_events"]),
        },
    )
    manifest["final_state_hash"] = "sha256:" + ("0" * 64)
    write_json(tmp_path / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(tmp_path / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(tmp_path / "signed_events.json", bundle["signed_events"])
    write_json(tmp_path / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(tmp_path / "bundle_manifest.json", manifest)

    with pytest.raises(SatRootError):
        verify_signed_ledger_bundle(tmp_path)


def test_verify_signed_ledger_bundle_rejects_file_hash_mismatch(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    manifest = build_signed_ledger_bundle_manifest(
        bundle,
        output_files={
            "signer_key_map": "signer_key_map.json",
            "secrets": "secrets.json",
            "signed_events": "signed_events.json",
            "annotated_signed_events": "annotated_signed_events.json",
            "bundle_manifest": "bundle_manifest.json",
        },
        output_file_hashes={
            "signer_key_map": rendered_json_sha256(bundle["material"]["signer_key_map"]),
            "secrets": rendered_json_sha256(bundle["material"]["shared_secrets"]),
            "signed_events": rendered_json_sha256(bundle["signed_events"]),
            "annotated_signed_events": rendered_json_sha256(bundle["annotated_events"]),
        },
    )
    write_json(tmp_path / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(tmp_path / "secrets.json", bundle["material"]["shared_secrets"])
    tampered_events = copy.deepcopy(bundle["signed_events"])
    tampered_events[-1]["signature"] = "hmac-sha256:" + ("0" * 64)
    write_json(tmp_path / "signed_events.json", tampered_events)
    write_json(tmp_path / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(tmp_path / "bundle_manifest.json", manifest)

    with pytest.raises(SatRootError):
        verify_signed_ledger_bundle(tmp_path)


def test_bootstrap_signed_ledger_bundle_ed25519_when_unavailable():
    if ed25519_available():
        bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="ed25519")
        assert bundle["material"]["public_keys"]
        return

    assert ed25519_available() is False
    with pytest.raises(SatRootError):
        bootstrap_signed_ledger_bundle(load_events(), scheme="ed25519")


def test_sign_ledger_events_demo_helper():
    events = load_events()
    signed = sign_ledger_events(events, scheme="demo")
    assert signed[1]["signature_scheme"] == "demo"
    assert signed[1]["signature"] == "demo"
    assert signed[1]["prev_event_id"] == event_id(signed[0])
    assert replay(signed).symbol == "FLOOR1"


def test_cli_sign_ledger_hmac_output(tmp_path):
    events_path = tmp_path / "events.json"
    signer_key_map_path = tmp_path / "signers.json"
    secrets_path = tmp_path / "secrets.json"
    output_path = tmp_path / "signed.json"

    events_path.write_text(json.dumps(load_events()), encoding="utf-8")
    signer_key_map_path.write_text(
        json.dumps({"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}),
        encoding="utf-8",
    )
    secrets_path.write_text(
        json.dumps({"issuer-key": "issuer-secret", "alice-key": "alice-secret", "bob-key": "bob-secret"}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "sign-ledger",
            str(events_path),
            "--scheme",
            "hmac-sha256",
            "--signer-key-map-json",
            str(signer_key_map_path),
            "--secrets-json",
            str(secrets_path),
            "--include-state-hash",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    signed_events = json.loads(output_path.read_text(encoding="utf-8"))
    verifier = make_hmac_sha256_verifier({"issuer-key": "issuer-secret", "alice-key": "alice-secret", "bob-key": "bob-secret"})
    state = replay(signed_events, verifier=verifier)
    assert state.symbol == "FLOOR1"


def test_cli_replay_hmac_signed_ledger(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    signer_key_map_path = tmp_path / "signers.json"
    secrets_path = tmp_path / "secrets.json"
    signed_path = tmp_path / "signed.json"

    events_path.write_text(json.dumps(load_events()), encoding="utf-8")
    signer_key_map_path.write_text(
        json.dumps({"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}),
        encoding="utf-8",
    )
    secrets_path.write_text(
        json.dumps({"issuer-key": "issuer-secret", "alice-key": "alice-secret", "bob-key": "bob-secret"}),
        encoding="utf-8",
    )

    sign_exit_code = main(
        [
            "sign-ledger",
            str(events_path),
            "--scheme",
            "hmac-sha256",
            "--signer-key-map-json",
            str(signer_key_map_path),
            "--secrets-json",
            str(secrets_path),
            "--output",
            str(signed_path),
        ]
    )
    assert sign_exit_code == 0

    replay_exit_code = main(
        [
            "replay",
            str(signed_path),
            "--scheme",
            "hmac-sha256",
            "--secrets-json",
            str(secrets_path),
        ]
    )
    assert replay_exit_code == 0

    captured = capsys.readouterr()
    assert '"symbol":"FLOOR1"' in captured.out
    assert "state_hash=sha256:" in captured.out


def test_cli_validate_accepts_demo_ledger(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    exit_code = main(["validate", str(events_path)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "valid SATROOT-1 JSON: 4 record(s)" in captured.out


def test_cli_validate_rejects_invalid_ledger(tmp_path):
    events = load_events()
    events[1]["signature_scheme"] = "ed25519"
    events_path = tmp_path / "events.json"
    events_path.write_text(json.dumps(events), encoding="utf-8")

    with pytest.raises(SatRootError):
        main(["validate", str(events_path)])


def test_cli_annotate_ledger_demo_output(tmp_path):
    events_path = tmp_path / "events.json"
    output_path = tmp_path / "annotated.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    exit_code = main(["annotate-ledger", str(events_path), "--output", str(output_path)])
    assert exit_code == 0

    annotated_events = json.loads(output_path.read_text(encoding="utf-8"))
    assert annotated_events[0]["event_id"].startswith("sha256:")
    assert annotated_events[0]["state_hash"].startswith("sha256:")
    assert replay(annotated_events).symbol == "FLOOR1"


def test_cli_annotate_hmac_signed_ledger(tmp_path):
    events_path = tmp_path / "events.json"
    signer_key_map_path = tmp_path / "signers.json"
    secrets_path = tmp_path / "secrets.json"
    signed_path = tmp_path / "signed.json"
    annotated_path = tmp_path / "annotated.json"

    events_path.write_text(json.dumps(load_events()), encoding="utf-8")
    signer_key_map_path.write_text(
        json.dumps({"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}),
        encoding="utf-8",
    )
    secrets_path.write_text(
        json.dumps({"issuer-key": "issuer-secret", "alice-key": "alice-secret", "bob-key": "bob-secret"}),
        encoding="utf-8",
    )

    sign_exit_code = main(
        [
            "sign-ledger",
            str(events_path),
            "--scheme",
            "hmac-sha256",
            "--signer-key-map-json",
            str(signer_key_map_path),
            "--secrets-json",
            str(secrets_path),
            "--output",
            str(signed_path),
        ]
    )
    assert sign_exit_code == 0

    annotate_exit_code = main(
        [
            "annotate-ledger",
            str(signed_path),
            "--scheme",
            "hmac-sha256",
            "--secrets-json",
            str(secrets_path),
            "--output",
            str(annotated_path),
        ]
    )
    assert annotate_exit_code == 0

    annotated_events = json.loads(annotated_path.read_text(encoding="utf-8"))
    verifier = make_hmac_sha256_verifier({"issuer-key": "issuer-secret", "alice-key": "alice-secret", "bob-key": "bob-secret"})
    assert annotated_events[-1]["state_hash"].startswith("sha256:")
    assert replay(annotated_events, verifier=verifier).symbol == "FLOOR1"


def test_cli_derive_ed25519_public_keys(tmp_path):
    private_keys_path = tmp_path / "private_keys.json"
    output_path = tmp_path / "public_keys.json"
    private_keys_path.write_text(json.dumps({"issuer-key": "11" * 32, "alice-key": "22" * 32}), encoding="utf-8")

    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            main(["derive-ed25519-public-keys", str(private_keys_path), "--output", str(output_path)])
        return

    exit_code = main(["derive-ed25519-public-keys", str(private_keys_path), "--output", str(output_path)])
    assert exit_code == 0

    public_keys = json.loads(output_path.read_text(encoding="utf-8"))
    assert public_keys["issuer-key"] == ed25519_public_key_hex("11" * 32)
    assert public_keys["alice-key"] == ed25519_public_key_hex("22" * 32)


def test_cli_generate_ed25519_private_keys(tmp_path):
    output_path = tmp_path / "private_keys.json"
    exit_code = main(
        [
            "generate-ed25519-private-keys",
            "--key-id",
            "issuer-key",
            "--key-id",
            "alice-key",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    private_keys = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(private_keys) == {"issuer-key", "alice-key"}
    assert len(private_keys["issuer-key"]) == 64
    assert len(private_keys["alice-key"]) == 64


def test_cli_generate_hmac_secrets(tmp_path):
    output_path = tmp_path / "secrets.json"
    exit_code = main(
        [
            "generate-hmac-secrets",
            "--key-id",
            "issuer-key",
            "--key-id",
            "alice-key",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    shared_secrets = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(shared_secrets) == {"issuer-key", "alice-key"}
    assert len(shared_secrets["issuer-key"]) == 64
    assert len(shared_secrets["alice-key"]) == 64


def test_cli_generate_hmac_secrets_from_signer_map(tmp_path):
    signer_key_map_path = tmp_path / "signers.json"
    output_path = tmp_path / "secrets.json"
    signer_key_map_path.write_text(
        json.dumps({"issuer": "issuer-key", "alice": "alice-key", "bob": "alice-key"}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "generate-hmac-secrets",
            "--signer-key-map-json",
            str(signer_key_map_path),
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    shared_secrets = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(shared_secrets) == {"issuer-key", "alice-key"}


def test_cli_generate_ed25519_private_keys_from_signer_map(tmp_path):
    signer_key_map_path = tmp_path / "signers.json"
    output_path = tmp_path / "private_keys.json"
    signer_key_map_path.write_text(
        json.dumps({"issuer": "issuer-key", "alice": "alice-key", "bob": "alice-key"}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "generate-ed25519-private-keys",
            "--signer-key-map-json",
            str(signer_key_map_path),
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    private_keys = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(private_keys) == {"issuer-key", "alice-key"}


def test_cli_init_signer_key_map(tmp_path):
    events_path = tmp_path / "events.json"
    output_path = tmp_path / "signers.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    exit_code = main(["init-signer-key-map", str(events_path), "--output", str(output_path)])
    assert exit_code == 0

    signer_key_map = json.loads(output_path.read_text(encoding="utf-8"))
    assert signer_key_map == {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}


def test_cli_init_signer_key_map_with_prefix_and_suffix(tmp_path):
    events_path = tmp_path / "events.json"
    output_path = tmp_path / "signers.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    exit_code = main(
        [
            "init-signer-key-map",
            str(events_path),
            "--key-prefix",
            "satroot-",
            "--key-suffix=-ed25519",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    signer_key_map = json.loads(output_path.read_text(encoding="utf-8"))
    assert signer_key_map["issuer"] == "satroot-issuer-ed25519"
    assert signer_key_map["alice"] == "satroot-alice-ed25519"
    assert signer_key_map["bob"] == "satroot-bob-ed25519"


def test_cli_bootstrap_ed25519_workflow(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    output_dir = tmp_path / "bootstrap"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            main(["bootstrap-ed25519-workflow", str(events_path), "--output-dir", str(output_dir)])
        assert not output_dir.exists()
        return

    exit_code = main(["bootstrap-ed25519-workflow", str(events_path), "--output-dir", str(output_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote Ed25519 workflow files to" in captured.out
    signer_key_map = json.loads((output_dir / "signer_key_map.json").read_text(encoding="utf-8"))
    private_keys = json.loads((output_dir / "private_keys.json").read_text(encoding="utf-8"))
    public_keys = json.loads((output_dir / "public_keys.json").read_text(encoding="utf-8"))
    assert signer_key_map == {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}
    assert public_keys["issuer-key"] == ed25519_public_key_hex(private_keys["issuer-key"])


def test_cli_bootstrap_hmac_workflow_and_sign_replay(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    output_dir = tmp_path / "bootstrap"
    signed_path = tmp_path / "signed.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    bootstrap_exit_code = main(["bootstrap-hmac-workflow", str(events_path), "--output-dir", str(output_dir)])
    assert bootstrap_exit_code == 0

    captured = capsys.readouterr()
    assert "wrote HMAC workflow files to" in captured.out
    signer_key_map = json.loads((output_dir / "signer_key_map.json").read_text(encoding="utf-8"))
    shared_secrets = json.loads((output_dir / "secrets.json").read_text(encoding="utf-8"))
    assert signer_key_map == {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}

    sign_exit_code = main(
        [
            "sign-ledger",
            str(events_path),
            "--scheme",
            "hmac-sha256",
            "--signer-key-map-json",
            str(output_dir / "signer_key_map.json"),
            "--secrets-json",
            str(output_dir / "secrets.json"),
            "--output",
            str(signed_path),
        ]
    )
    assert sign_exit_code == 0

    signed_events = json.loads(signed_path.read_text(encoding="utf-8"))
    verifier = make_hmac_sha256_verifier(shared_secrets)
    assert replay(signed_events, verifier=verifier).symbol == "FLOOR1"


def test_cli_bootstrap_signed_ledger_hmac_bundle(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    output_dir = tmp_path / "bundle"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    exit_code = main(
        [
            "bootstrap-signed-ledger",
            str(events_path),
            "--scheme",
            "hmac-sha256",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote signed SATROOT-1 hmac-sha256 bundle to" in captured.out
    signer_key_map = json.loads((output_dir / "signer_key_map.json").read_text(encoding="utf-8"))
    shared_secrets = json.loads((output_dir / "secrets.json").read_text(encoding="utf-8"))
    signed_events = json.loads((output_dir / "signed_events.json").read_text(encoding="utf-8"))
    annotated_events = json.loads((output_dir / "annotated_signed_events.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    verifier = make_hmac_sha256_verifier(shared_secrets)
    assert signer_key_map == {"issuer": "issuer-key", "alice": "alice-key", "bob": "bob-key"}
    assert replay(signed_events, verifier=verifier).symbol == "FLOOR1"
    assert replay(annotated_events, verifier=verifier).symbol == "FLOOR1"
    assert annotated_events[0]["event_id"].startswith("sha256:")
    assert manifest["scheme"] == "hmac-sha256"
    assert manifest["files"]["signed_events"] == "signed_events.json"
    assert manifest["files"]["bundle_manifest"] == "bundle_manifest.json"
    assert manifest["final_state_hash"].startswith("sha256:")


def test_cli_bootstrap_signed_ledger_ed25519_unavailable(tmp_path):
    events_path = tmp_path / "events.json"
    output_dir = tmp_path / "bundle"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    if ed25519_available():
        exit_code = main(
            [
                "bootstrap-signed-ledger",
                str(events_path),
                "--scheme",
                "ed25519",
                "--output-dir",
                str(output_dir),
            ]
        )
        assert exit_code == 0
        assert (output_dir / "private_keys.json").exists()
        assert (output_dir / "public_keys.json").exists()
        return

    assert ed25519_available() is False
    with pytest.raises(SatRootError):
        main(
            [
                "bootstrap-signed-ledger",
                str(events_path),
                "--scheme",
                "ed25519",
                "--output-dir",
                str(output_dir),
            ]
        )
    assert not output_dir.exists()


def test_cli_verify_bundle_hmac_bundle(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    output_dir = tmp_path / "bundle"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    bootstrap_exit_code = main(
        [
            "bootstrap-signed-ledger",
            str(events_path),
            "--scheme",
            "hmac-sha256",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert bootstrap_exit_code == 0
    capsys.readouterr()

    verify_exit_code = main(["verify-bundle", str(output_dir)])
    assert verify_exit_code == 0

    captured = capsys.readouterr()
    assert '"scheme":"hmac-sha256"' in captured.out
    assert '"symbol":"FLOOR1"' in captured.out
    assert '"annotated_verified":true' in captured.out


def test_cli_validate_bundle_manifest(tmp_path, capsys):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    manifest = build_signed_ledger_bundle_manifest(
        bundle,
        output_files={
            "signer_key_map": "signer_key_map.json",
            "secrets": "secrets.json",
            "signed_events": "signed_events.json",
            "annotated_signed_events": "annotated_signed_events.json",
            "bundle_manifest": "bundle_manifest.json",
        },
        output_file_hashes={
            "signer_key_map": rendered_json_sha256(bundle["material"]["signer_key_map"]),
            "secrets": rendered_json_sha256(bundle["material"]["shared_secrets"]),
            "signed_events": rendered_json_sha256(bundle["signed_events"]),
            "annotated_signed_events": rendered_json_sha256(bundle["annotated_events"]),
        },
    )
    manifest_path = tmp_path / "bundle_manifest.json"
    write_json(manifest_path, manifest)

    exit_code = main(["validate-bundle-manifest", str(manifest_path)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "valid SATROOT-1 bundle manifest: 1 record(s)" in captured.out
