import copy
import json
from pathlib import Path

import pytest

from satroot1 import (
    annotate_ledger_events,
    build_signed_ledger_bundle_index,
    build_publication_metadata_catalog,
    build_publication_registry,
    build_signed_publication_metadata_catalog_manifest,
    build_signed_publication_metadata_manifest,
    build_signed_publication_registry_manifest,
    build_signed_release_catalog,
    build_signed_release_catalog_index,
    build_signed_release_catalog_index_manifest,
    build_signed_release_catalog_manifest,
    build_signed_release_manifest,
    build_signed_publication_descriptor_index_manifest,
    append_signed_event_to_ledger,
    bootstrap_machine_credit_demo_ledger,
    bootstrap_machine_credit_demo_release,
    bootstrap_publication_descriptor_index_publication,
    bootstrap_release_catalog_index_publication,
    bootstrap_release_catalog_publication,
    bootstrap_release_ed25519_material,
    bootstrap_release_publication,
    bootstrap_release_hmac_material,
    bootstrap_ed25519_workflow,
    bootstrap_genesis_bundle,
    bootstrap_hmac_workflow,
    bootstrap_singleton_object_demo_bundle,
    bootstrap_singleton_object_demo_ledger,
    bootstrap_singleton_object_demo_release,
    bootstrap_signed_ledger_bundle,
    bootstrap_stable_reference_demo_bundle,
    bootstrap_stable_reference_demo_ledger,
    bootstrap_stable_reference_demo_release,
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
    load_bundle_index_schema,
    load_bundle_manifest_schema,
    load_demo_catalog_summary_schema,
    load_demo_catalog_preset,
    load_protocol_schema,
    load_profile_registry,
    load_publication_descriptor_index_preset,
    load_publication_network_preset,
    load_publication_metadata_catalog_preset,
    load_publication_metadata_catalog_manifest_schema,
    load_publication_metadata_catalog_schema,
    load_publication_registry_manifest_schema,
    load_publication_registry_preset,
    load_publication_registry_schema,
    load_publication_descriptor_index_manifest_schema,
    load_publication_descriptor_index_schema,
    load_publication_metadata_manifest_schema,
    load_publication_network_summary_schema,
    load_publication_stack_preset,
    load_publication_stack_summary_schema,
    load_release_catalog_index_manifest_schema,
    load_release_catalog_index_preset,
    load_release_catalog_index_schema,
    load_release_catalog_preset,
    load_release_catalog_manifest_schema,
    load_release_catalog_schema,
    load_release_manifest_schema,
    main,
    make_ed25519_verifier,
    make_hmac_sha256_verifier,
    make_hmac_sha256_signer,
    parse_named_string_overrides,
    parse_profile_field_override_map,
    parse_profile_field_overrides,
    parse_profile_structure_override_map,
    replay,
    rendered_json_sha256,
    scaffold_genesis_record,
    scaffold_event_from_ledger,
    scaffold_event_record,
    scaffold_machine_credit_consumption_event,
    scaffold_singleton_object_archive_event,
    scaffold_singleton_object_retirement_event,
    scaffold_singleton_object_transfer_event,
    sha256_hex,
    sign_ledger_events,
    signing_payload,
    lint_signed_ledger_bundle,
    summarize_signed_ledger_bundle,
    validate_instance_against_schema,
    validate_bundle_index_consistency,
    validate_demo_catalog_summary_consistency,
    validate_publication_network_summary_consistency,
    validate_publication_metadata_catalog_consistency,
    validate_publication_registry_consistency,
    validate_publication_descriptor_index_consistency,
    validate_publication_stack_summary_consistency,
    validate_release_catalog_index_consistency,
    validate_release_catalog_consistency,
    verify_signed_release_catalog_index_manifest,
    verify_signed_release_catalog_manifest,
    verify_signed_release_manifest,
    verify_signed_publication_metadata_catalog_manifest,
    verify_signed_publication_descriptor_index_manifest,
    verify_signed_publication_metadata_manifest,
    verify_signed_publication_registry_manifest,
    verify_signed_ledger_bundle,
)


ROOT = Path(__file__).resolve().parents[1]


def load_events(name="events_floor1.json"):
    return json.loads((ROOT / "examples" / name).read_text())


def write_json(path: Path, data):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def make_demo_release_dirs(tmp_path: Path) -> tuple[str, str]:
    stable = bootstrap_stable_reference_demo_release(
        symbol="RELSTB1",
        name="Release Stable Demo",
        bundle_scheme="hmac-sha256",
        output_dir=tmp_path / "stable_workspace",
        release_key_id="release-key",
        release_metadata={
            "channel": "stable",
            "label": "Stable Release Workspace",
            "published_at": "2026-06-30T02:00:00Z",
        },
    )
    machine = bootstrap_machine_credit_demo_release(
        symbol="RELMCH1",
        name="Release Machine Demo",
        bundle_scheme="hmac-sha256",
        output_dir=tmp_path / "machine_workspace",
        release_key_id="release-key",
        release_metadata={
            "channel": "stable",
            "label": "Machine Release Workspace",
            "published_at": "2026-06-30T03:00:00Z",
        },
    )
    return stable["release_dir"], machine["release_dir"]


def make_demo_release_catalog_dir(tmp_path: Path) -> Path:
    stable_release_dir, machine_release_dir = make_demo_release_dirs(tmp_path)
    output_dir = tmp_path / "release_catalog_publication"
    published = bootstrap_release_catalog_publication(
        [stable_release_dir, machine_release_dir],
        output_dir=output_dir,
        signature_scheme="hmac-sha256",
        key_id="catalog-key",
        catalog_metadata={
            "channel": "stable",
            "label": "SATROOT Catalog of Releases",
            "published_at": "2026-06-30T05:00:00Z",
        },
    )
    assert Path(published["release_catalog_manifest_path"]).is_file()
    return output_dir


def make_demo_release_catalog_index_dir(tmp_path: Path) -> Path:
    catalog_alpha_root = tmp_path / "catalog_alpha_root"
    catalog_beta_root = tmp_path / "catalog_beta_root"
    alpha_release_dirs = make_demo_release_dirs(catalog_alpha_root)
    beta_release_dirs = make_demo_release_dirs(catalog_beta_root)

    catalog_alpha_dir = tmp_path / "catalog_alpha"
    bootstrap_release_catalog_publication(
        list(alpha_release_dirs),
        output_dir=catalog_alpha_dir,
        signature_scheme="hmac-sha256",
        key_id="catalog-alpha-key",
        catalog_metadata={
            "channel": "stable",
            "label": "SATROOT Catalog Alpha",
            "published_at": "2026-07-02T01:00:00Z",
        },
    )

    catalog_beta_dir = tmp_path / "catalog_beta"
    bootstrap_release_catalog_publication(
        list(beta_release_dirs),
        output_dir=catalog_beta_dir,
        signature_scheme="hmac-sha256",
        key_id="catalog-beta-key",
        catalog_metadata={
            "channel": "beta",
            "label": "SATROOT Catalog Beta",
            "published_at": "2026-07-02T02:00:00Z",
        },
    )

    output_dir = tmp_path / "release_catalog_index_publication"
    published = bootstrap_release_catalog_index_publication(
        [catalog_alpha_dir, catalog_beta_dir],
        output_dir=output_dir,
        signature_scheme="hmac-sha256",
        key_id="index-key",
        index_metadata={
            "channel": "network",
            "label": "SATROOT Catalog Network",
            "published_at": "2026-07-02T03:00:00Z",
        },
    )
    assert Path(published["release_catalog_index_manifest_path"]).is_file()
    return output_dir


def make_demo_catalog_workspace_dir(tmp_path: Path) -> Path:
    output_dir = tmp_path / "catalog_workspace"
    exit_code = main(
        [
            "bootstrap-demo-catalog",
            "--scheme",
            "hmac-sha256",
            "--profile",
            "SATROOT-STABLE-1",
            "--profile",
            "SATROOT-MACHINE-1",
            "--release-key-id",
            "release-key",
            "--output-dir",
            str(output_dir),
            "--channel",
            "stable",
            "--label",
            "CLI Demo Catalog",
            "--published-at",
            "2026-07-05T02:00:00Z",
        ]
    )
    assert exit_code == 0
    return output_dir


def make_demo_publication_stack_dir(tmp_path: Path) -> Path:
    catalog_preset_a = tmp_path / "stable_catalog.json"
    write_json(
        catalog_preset_a,
        {
            "type": "SATROOT-DEMO-CATALOG-PRESET",
            "version": "0.1",
            "profiles": ["SATROOT-STABLE-1"],
            "symbol_overrides": {"SATROOT-STABLE-1": "PSTSTB1"},
            "name_overrides": {"SATROOT-STABLE-1": "Publication Stable Catalog"},
            "release": {
                "channel": "stable",
                "label": "Publication Stable Release",
                "published_at": "2026-07-04T01:00:00Z",
            },
        },
    )
    catalog_preset_b = tmp_path / "machine_catalog.json"
    write_json(
        catalog_preset_b,
        {
            "type": "SATROOT-DEMO-CATALOG-PRESET",
            "version": "0.1",
            "profiles": ["SATROOT-MACHINE-1"],
            "symbol_overrides": {"SATROOT-MACHINE-1": "PSTMCH1"},
            "name_overrides": {"SATROOT-MACHINE-1": "Publication Machine Catalog"},
            "release": {
                "channel": "stable",
                "label": "Publication Machine Release",
                "published_at": "2026-07-04T02:00:00Z",
            },
        },
    )
    release_catalog_preset = tmp_path / "release_stack.json"
    write_json(
        release_catalog_preset,
        {
            "type": "SATROOT-RELEASE-CATALOG-PRESET",
            "version": "0.1",
            "catalog": {
                "channel": "stable",
                "label": "Publication Stack Releases",
                "published_at": "2026-07-04T03:00:00Z",
            },
        },
    )
    output_dir = tmp_path / "publication_stack"
    exit_code = main(
        [
            "bootstrap-publication-stack",
            "--catalog-preset-json",
            str(catalog_preset_a),
            "--catalog-preset-json",
            str(catalog_preset_b),
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--release-catalog-preset-json",
            str(release_catalog_preset),
            "--release-catalog-key-id",
            "catalog-key",
            "--output-dir",
            str(output_dir),
            "--label",
            "Publication Stack Override",
        ]
    )
    assert exit_code == 0
    return output_dir


def make_demo_publication_network_dir(tmp_path: Path) -> Path:
    stable_catalog_preset = tmp_path / "stable_catalog.json"
    write_json(
        stable_catalog_preset,
        {
            "type": "SATROOT-DEMO-CATALOG-PRESET",
            "version": "0.1",
            "profiles": ["SATROOT-STABLE-1"],
            "symbol_overrides": {"SATROOT-STABLE-1": "PNWSTB1"},
            "name_overrides": {"SATROOT-STABLE-1": "Publication Network Stable Catalog"},
            "release": {
                "channel": "stable",
                "label": "Publication Network Stable Release",
                "published_at": "2026-07-04T04:00:00Z",
            },
        },
    )
    machine_catalog_preset = tmp_path / "machine_catalog.json"
    write_json(
        machine_catalog_preset,
        {
            "type": "SATROOT-DEMO-CATALOG-PRESET",
            "version": "0.1",
            "profiles": ["SATROOT-MACHINE-1"],
            "symbol_overrides": {"SATROOT-MACHINE-1": "PNWMCH1"},
            "name_overrides": {"SATROOT-MACHINE-1": "Publication Network Machine Catalog"},
            "release": {
                "channel": "stable",
                "label": "Publication Network Machine Release",
                "published_at": "2026-07-04T05:00:00Z",
            },
        },
    )
    stack_preset_a = tmp_path / "stack_a.json"
    write_json(
        stack_preset_a,
        {
            "type": "SATROOT-PUBLICATION-STACK-PRESET",
            "version": "0.1",
            "catalog_presets": [str(Path(stable_catalog_preset).relative_to(tmp_path))],
            "release_catalog": {
                "channel": "stable",
                "label": "Publication Network Stack Alpha",
                "published_at": "2026-07-04T06:00:00Z",
            },
        },
    )
    stack_preset_b = tmp_path / "stack_b.json"
    write_json(
        stack_preset_b,
        {
            "type": "SATROOT-PUBLICATION-STACK-PRESET",
            "version": "0.1",
            "catalog_presets": [str(Path(machine_catalog_preset).relative_to(tmp_path))],
            "release_catalog": {
                "channel": "beta",
                "label": "Publication Network Stack Beta",
                "published_at": "2026-07-04T07:00:00Z",
            },
        },
    )
    index_preset = tmp_path / "network_index.json"
    write_json(
        index_preset,
        {
            "type": "SATROOT-RELEASE-CATALOG-INDEX-PRESET",
            "version": "0.1",
            "index": {
                "channel": "network",
                "label": "Publication Network Index",
                "published_at": "2026-07-04T08:00:00Z",
            },
        },
    )
    output_dir = tmp_path / "publication_network"
    exit_code = main(
        [
            "bootstrap-publication-network",
            "--stack-preset-json",
            str(stack_preset_a),
            "--stack-preset-json",
            str(stack_preset_b),
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--release-catalog-key-id",
            "catalog-key",
            "--release-catalog-index-preset-json",
            str(index_preset),
            "--release-catalog-index-key-id",
            "index-key",
            "--output-dir",
            str(output_dir),
            "--label",
            "Publication Network Override",
        ]
    )
    assert exit_code == 0
    return output_dir


def make_publication_metadata_bundle_dirs(tmp_path: Path) -> tuple[Path, Path]:
    release_dir, _ = make_demo_release_dirs(tmp_path)
    network_dir = make_demo_publication_network_dir(tmp_path)
    release_bundle_dir = tmp_path / "publication_metadata_release"
    network_bundle_dir = tmp_path / "publication_metadata_network"

    assert main(
        [
            "bootstrap-publication-metadata-bundle",
            release_dir,
            "--output-dir",
            str(release_bundle_dir),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "metadata-key",
        ]
    ) == 0
    assert main(
        [
            "bootstrap-publication-metadata-bundle",
            str(network_dir),
            "--output-dir",
            str(network_bundle_dir),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "metadata-key",
        ]
    ) == 0
    return release_bundle_dir, network_bundle_dir


def make_publication_metadata_catalog_dir(tmp_path: Path) -> Path:
    _release_bundle_dir, _network_bundle_dir = make_publication_metadata_bundle_dirs(tmp_path)
    output_dir = tmp_path / "publication_metadata_catalog_publication"
    assert main(
        [
            "bootstrap-publication-metadata-catalog-publication",
            "--discover-under",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--channel",
            "network",
            "--label",
            "SATROOT Metadata Catalog Publication",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "catalog-key",
        ]
    ) == 0
    return output_dir


def make_publication_descriptor_index_dir(tmp_path: Path) -> Path:
    network_dir = make_demo_publication_network_dir(tmp_path)
    output_dir = tmp_path / "publication_descriptor_index_publication"
    assert main(
        [
            "bootstrap-publication-descriptor-index-publication",
            "--discover-under",
            str(network_dir),
            "--output-dir",
            str(output_dir),
            "--channel",
            "network",
            "--label",
            "SATROOT Descriptor Publication",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "descriptor-key",
        ]
    ) == 0
    return output_dir


def make_publication_registry_component_dirs(tmp_path: Path) -> tuple[Path, Path, Path]:
    network_root = tmp_path / "network_root"
    network_root.mkdir(parents=True, exist_ok=True)
    network_dir = make_demo_publication_network_dir(network_root)
    release_catalog_index_dir = network_dir / "release_catalog_index"

    descriptor_index_dir = tmp_path / "publication_descriptor_index_publication"
    assert main(
        [
            "bootstrap-publication-descriptor-index-publication",
            "--discover-under",
            str(network_dir),
            "--output-dir",
            str(descriptor_index_dir),
            "--channel",
            "network",
            "--label",
            "Registry Descriptor Index",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "descriptor-key",
        ]
    ) == 0

    release_root = tmp_path / "registry_release_root"
    release_root.mkdir(parents=True, exist_ok=True)
    release_dir, _ = make_demo_release_dirs(release_root)
    metadata_release_bundle_dir = tmp_path / "registry_metadata_inputs" / "release"
    metadata_network_bundle_dir = tmp_path / "registry_metadata_inputs" / "network"
    assert main(
        [
            "bootstrap-publication-metadata-bundle",
            release_dir,
            "--output-dir",
            str(metadata_release_bundle_dir),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "metadata-key",
        ]
    ) == 0
    assert main(
        [
            "bootstrap-publication-metadata-bundle",
            str(network_dir),
            "--output-dir",
            str(metadata_network_bundle_dir),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "metadata-key",
        ]
    ) == 0

    metadata_catalog_dir = tmp_path / "publication_metadata_catalog_publication"
    assert main(
        [
            "bootstrap-publication-metadata-catalog-publication",
            str(metadata_release_bundle_dir),
            str(metadata_network_bundle_dir),
            "--output-dir",
            str(metadata_catalog_dir),
            "--channel",
            "network",
            "--label",
            "Registry Metadata Catalog",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "catalog-key",
        ]
    ) == 0

    return release_catalog_index_dir, descriptor_index_dir, metadata_catalog_dir


def make_publication_registry_dir(tmp_path: Path) -> Path:
    release_catalog_index_dir, descriptor_index_dir, metadata_catalog_dir = make_publication_registry_component_dirs(tmp_path)
    output_dir = tmp_path / "publication_registry_publication"
    assert main(
        [
            "bootstrap-publication-registry-publication",
            "--release-catalog-index-dir",
            str(release_catalog_index_dir),
            "--publication-descriptor-index-dir",
            str(descriptor_index_dir),
            "--publication-metadata-catalog-dir",
            str(metadata_catalog_dir),
            "--output-dir",
            str(output_dir),
            "--channel",
            "network",
            "--label",
            "SATROOT Publication Registry",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "registry-key",
        ]
    ) == 0
    return output_dir


def make_publication_registry_workspace_dir(tmp_path: Path) -> Path:
    network_dir = make_demo_publication_network_dir(tmp_path)
    output_dir = tmp_path / "publication_registry_workspace"
    assert main(
        [
            "bootstrap-publication-registry-workspace",
            "--publication-network-dir",
            str(network_dir),
            "--scheme",
            "hmac-sha256",
            "--publication-descriptor-index-key-id",
            "descriptor-key",
            "--publication-metadata-key-id",
            "metadata-key",
            "--publication-metadata-catalog-key-id",
            "catalog-key",
            "--publication-registry-key-id",
            "registry-key",
            "--output-dir",
            str(output_dir),
            "--descriptor-index-channel",
            "network",
            "--descriptor-index-label",
            "Workspace Descriptor Index",
            "--publication-metadata-catalog-channel",
            "network",
            "--publication-metadata-catalog-label",
            "Workspace Metadata Catalog",
            "--publication-registry-channel",
            "network",
            "--publication-registry-label",
            "Workspace Publication Registry",
        ]
    ) == 0
    return output_dir


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


def test_bootstrap_machine_credit_demo_ledger():
    demo = bootstrap_machine_credit_demo_ledger(
        symbol="APIDEMO2",
        name="Machine Demo",
        service_scope="vector-index",
        billing_unit="call",
        worker_burn_amount="0",
    )

    state = replay(demo["events"])
    assert len(demo["events"]) == 3
    assert state.symbol == "APIDEMO2"
    assert state.genesis_metadata["service_scope"] == "vector-index"
    assert state.genesis_metadata["billing_unit"] == "call"
    assert state.balances["tenant_a"] == 3_800_000
    assert state.balances["worker_node"] == 1_200_000


def test_bootstrap_machine_credit_demo_ledger_rejects_non_burn_consumption_flow():
    with pytest.raises(SatRootError):
        bootstrap_machine_credit_demo_ledger(
            symbol="APIBAD1",
            name="Bad Machine Demo",
            consumption_model="metered-ledger",
            worker_burn_amount="1",
        )


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


def test_reject_stable_reference_only_redemption_claim():
    events = load_events("events_usdroot1.json")
    events[0]["redemption"] = "issuer-redeemable"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_stable_reference_only_reserve_claim():
    events = load_events("events_usdroot1.json")
    events[0]["reserve_model"] = "fiat-backed"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_stable_reference_unit_with_lowercase_letters():
    events = load_events("events_usdroot1.json")
    events[0]["reference_unit"] = "usd"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_machine_profile_non_compact_service_scope():
    events = load_events("events_apicredit1.json")
    events[0]["service_scope"] = "API Compute"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_receipt_profile_non_uppercase_settlement_unit():
    events = load_events("events_receipt1.json")
    events[0]["settlement_unit"] = "usd"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_receipt_profile_non_singleton_max_supply():
    events = load_events("events_receipt1.json")
    events[0]["max_supply"] = "2"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_identity_profile_nonzero_decimals():
    events = load_events("events_identity1.json")
    events[0]["decimals"] = 1
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_license_profile_non_compact_usage_scope():
    events = load_events("events_license1.json")
    events[0]["usage_scope"] = "production api"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_license_profile_without_single_issued_unit():
    events = load_events("events_license1.json")
    events[0]["initial_balances"] = {"issuer": "0"}
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


def test_scaffold_genesis_record_base_replays():
    genesis = scaffold_genesis_record(
        symbol="BASE1",
        name="SATROOT Base Asset",
        root_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:0",
        nonce="base-scaffold",
    )
    state = replay([genesis])
    assert state.symbol == "BASE1"
    assert state.supply == 1_000_000
    assert state.balances["issuer"] == 1_000_000


def test_scaffold_genesis_record_stable_profile_replays():
    genesis = scaffold_genesis_record(
        symbol="USDTEST1",
        name="SATROOT Test Dollar",
        root_id="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb:0",
        profile="SATROOT-STABLE-1",
        profile_fields={"reference_unit": "INR", "intended_use": "internal-ledger"},
        nonce="stable-scaffold",
    )
    state = replay([genesis])
    assert state.profile == "SATROOT-STABLE-1"
    assert state.decimals == 2
    assert state.genesis_metadata["reference_unit"] == "INR"
    assert state.genesis_metadata["redemption"] == "none"


def test_scaffold_genesis_record_rejects_unknown_profile_override():
    with pytest.raises(SatRootError):
        scaffold_genesis_record(
            symbol="BAD1",
            name="Bad Asset",
            root_id="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc:0",
            profile="SATROOT-STABLE-1",
            profile_fields={"service_scope": "api-compute"},
        )


def test_parse_profile_field_overrides_rejects_duplicate_keys():
    with pytest.raises(SatRootError):
        parse_profile_field_overrides(["reference_unit=USD", "reference_unit=INR"])


def test_parse_named_string_overrides_rejects_duplicate_keys():
    with pytest.raises(SatRootError):
        parse_named_string_overrides(
            ["SATROOT-STABLE-1=USDCAT2", "SATROOT-STABLE-1=USDCAT3"],
            label="demo catalog symbol override",
            allowed_keys=["SATROOT-STABLE-1", "SATROOT-MACHINE-1"],
        )


def test_parse_profile_field_override_map_rejects_duplicate_fields():
    with pytest.raises(SatRootError):
        parse_profile_field_override_map(
            [
                "SATROOT-STABLE-1:reference_unit=USD",
                "SATROOT-STABLE-1:reference_unit=EUR",
            ],
            allowed_profiles=["SATROOT-STABLE-1", "SATROOT-MACHINE-1"],
        )


def test_parse_profile_structure_override_map_rejects_duplicate_fields():
    with pytest.raises(SatRootError):
        parse_profile_structure_override_map(
            [
                "SATROOT-MACHINE-1:tenant_amount=5000000",
                "SATROOT-MACHINE-1:tenant_amount=7000000",
            ],
            allowed_profiles=["SATROOT-STABLE-1", "SATROOT-MACHINE-1"],
        )


def test_load_demo_catalog_preset_example():
    preset = load_demo_catalog_preset(ROOT / "examples" / "catalog_presets" / "ai_compute_catalog.json")
    assert preset["profiles"] == ["SATROOT-STABLE-1", "SATROOT-MACHINE-1", "SATROOT-IDENTITY-1"]
    assert preset["symbol_overrides"]["SATROOT-MACHINE-1"] == "AICORE1"
    assert preset["profile_field_overrides"]["SATROOT-MACHINE-1"]["service_scope"] == "batch-inference"
    assert preset["profile_structure_overrides"]["SATROOT-IDENTITY-1"]["next_holder"] is None
    assert preset["profile_structure_overrides"]["SATROOT-IDENTITY-1"]["retire"] is False
    assert preset["release_metadata"]["label"] == "SATROOT AI Compute Catalog"


def test_load_release_catalog_preset_example():
    preset = load_release_catalog_preset(ROOT / "examples" / "release_catalog_presets" / "ai_compute_release_stack.json")
    assert preset["release_dirs"] == []
    assert preset["discover_under"] == [str((ROOT / "generated_release_workspaces").resolve())]
    assert preset["recursive"] is True
    assert preset["catalog_metadata"]["label"] == "SATROOT AI Compute Release Stack"


def test_load_release_catalog_index_preset_example():
    preset = load_release_catalog_index_preset(ROOT / "examples" / "release_catalog_index_presets" / "ai_compute_catalog_network.json")
    assert preset["release_catalog_dirs"] == []
    assert preset["discover_under"] == [str((ROOT / "generated_release_catalogs").resolve())]
    assert preset["recursive"] is True
    assert preset["index_metadata"]["label"] == "SATROOT AI Compute Catalog Network"


def test_load_publication_descriptor_index_preset_example():
    preset = load_publication_descriptor_index_preset(
        ROOT / "examples" / "publication_descriptor_index_presets" / "ai_compute_publication_descriptor_index.json"
    )
    assert preset["discover_under"] == [str((ROOT / "examples" / "generated_publication_network").resolve())]
    assert preset["index_metadata"]["label"] == "SATROOT AI Compute Publication Descriptor Index"


def test_load_publication_stack_preset_example():
    preset = load_publication_stack_preset(ROOT / "examples" / "stack_presets" / "ai_compute_publication_stack.json")
    assert preset["catalog_preset_paths"] == [str((ROOT / "examples" / "catalog_presets" / "ai_compute_catalog.json").resolve())]
    assert preset["release_catalog_metadata"]["label"] == "SATROOT AI Compute Publication Stack"


def test_load_publication_network_preset_example():
    preset = load_publication_network_preset(ROOT / "examples" / "network_presets" / "ai_compute_publication_network.json")
    assert preset["stack_preset_paths"] == [str((ROOT / "examples" / "stack_presets" / "ai_compute_publication_stack.json").resolve())]
    assert preset["release_catalog_index_metadata"]["label"] == "SATROOT AI Compute Publication Network"


def test_load_publication_registry_preset_example():
    preset = load_publication_registry_preset(ROOT / "examples" / "registry_presets" / "ai_compute_publication_registry.json")
    assert preset["release_catalog_index_dir"] == str((ROOT / "examples" / "generated_publication_network" / "release_catalog_index").resolve())
    assert preset["publication_descriptor_index_dir"] == str((ROOT / "examples" / "generated_publication_descriptor_index_publication").resolve())
    assert preset["publication_metadata_catalog_dir"] == str((ROOT / "examples" / "generated_publication_metadata_catalog_publication").resolve())
    assert preset["registry_metadata"]["label"] == "SATROOT AI Compute Publication Registry"


def test_load_publication_metadata_catalog_preset_example():
    preset = load_publication_metadata_catalog_preset(
        ROOT / "examples" / "publication_metadata_catalog_presets" / "ai_compute_publication_metadata_catalog.json"
    )
    assert preset["discover_under"] == [str((ROOT / "examples" / "generated_publication_metadata_root").resolve())]
    assert preset["catalog_metadata"]["label"] == "SATROOT AI Compute Publication Metadata Catalog"


def test_validate_publication_stack_summary_schema_accepts_generated_summary(tmp_path):
    stack_dir = make_demo_publication_stack_dir(tmp_path)
    summary = json.loads((stack_dir / "summary.json").read_text(encoding="utf-8"))

    count = validate_instance_against_schema(summary, load_publication_stack_summary_schema())
    assert count == 1
    validate_publication_stack_summary_consistency(summary)


def test_validate_publication_network_summary_schema_accepts_generated_summary(tmp_path):
    network_dir = make_demo_publication_network_dir(tmp_path)
    summary = json.loads((network_dir / "summary.json").read_text(encoding="utf-8"))

    count = validate_instance_against_schema(summary, load_publication_network_summary_schema())
    assert count == 1
    validate_publication_network_summary_consistency(summary)


def test_validate_demo_catalog_summary_schema_accepts_generated_summary(tmp_path):
    output_dir = tmp_path / "catalog_workspace"
    exit_code = main(
        [
            "bootstrap-demo-catalog",
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--output-dir",
            str(output_dir),
            "--channel",
            "stable",
            "--label",
            "Schema Demo Catalog",
            "--published-at",
            "2026-07-05T01:00:00Z",
        ]
    )
    assert exit_code == 0

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    count = validate_instance_against_schema(summary, load_demo_catalog_summary_schema())
    assert count == 1
    validate_demo_catalog_summary_consistency(summary)


def test_bootstrap_signed_ledger_bundle_accepts_genesis_only_hmac():
    genesis = scaffold_genesis_record(
        symbol="GENHMAC1",
        name="Genesis HMAC Asset",
        root_id="dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd:0",
        nonce="genesis-only-hmac",
    )
    bundle = bootstrap_signed_ledger_bundle([genesis], scheme="hmac-sha256")
    assert bundle["material"]["signer_key_map"] == {}
    assert bundle["material"]["shared_secrets"] == {}
    assert len(bundle["signed_events"]) == 1
    assert bundle["final_state_snapshot"]["symbol"] == "GENHMAC1"


def test_bootstrap_genesis_bundle_scaffolds_profiled_starter():
    bundle = bootstrap_genesis_bundle(
        symbol="GENUSD1",
        name="Genesis USD Asset",
        scheme="hmac-sha256",
        root_id="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee:0",
        profile="SATROOT-STABLE-1",
        profile_fields={"reference_unit": "GBP"},
        nonce="genesis-bundle",
    )
    assert bundle["genesis"]["profile"] == "SATROOT-STABLE-1"
    assert bundle["genesis"]["reference_unit"] == "GBP"
    assert bundle["signed_events"][0]["symbol"] == "GENUSD1"
    assert bundle["final_state_snapshot"]["symbol"] == "GENUSD1"


def test_bootstrap_stable_reference_demo_ledger_replays():
    demo = bootstrap_stable_reference_demo_ledger(
        symbol="USDDEMO1",
        name="Stable Demo Asset",
        root_id="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff:0",
        reference_unit="EUR",
        nonce="stable-demo-bootstrap",
    )
    events = demo["events"]
    state = replay(events)
    assert len(events) == 4
    assert state.profile == "SATROOT-STABLE-1"
    assert state.profile_mode == "reference-only"
    assert state.genesis_metadata["reference_unit"] == "EUR"
    assert state.balances["issuer"] == 23_500_000
    assert state.balances["merchant"] == 1_245_000
    assert state.balances["api_node"] == 250_000
    assert demo["annotated_events"][-1]["state_hash"].startswith("sha256:")


def test_bootstrap_singleton_object_demo_ledger_receipt_replays():
    demo = bootstrap_singleton_object_demo_ledger(
        profile="SATROOT-RECEIPT-1",
        symbol="RECDEMO1",
        name="Receipt Demo Asset",
        root_id="cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd:0",
        holder_account="buyer",
        archive_account="archive",
        nonce="singleton-demo-bootstrap",
    )
    events = demo["events"]
    state = replay(events)
    assert len(events) == 4
    assert state.profile == "SATROOT-RECEIPT-1"
    assert state.supply == 0
    assert state.balances["archive"] == 0
    assert demo["annotated_events"][-1]["state_hash"].startswith("sha256:")


def test_bootstrap_singleton_object_demo_ledger_rejects_unsupported_profile():
    with pytest.raises(SatRootError):
        bootstrap_singleton_object_demo_ledger(
            profile="SATROOT-STABLE-1",
            symbol="BADSINGLE1",
            name="Bad Singleton Demo",
            holder_account="holder",
        )


def test_bootstrap_singleton_object_demo_bundle_hmac():
    bundle = bootstrap_singleton_object_demo_bundle(
        profile="SATROOT-LICENSE-1",
        symbol="LICBUNDLE1",
        name="License Bundle Asset",
        scheme="hmac-sha256",
        root_id="efefefefefefefefefefefefefefefefefefefefefefefefefefefefefefefef:0",
        holder_account="customer",
        archive_account="archive",
        nonce="singleton-bundle-bootstrap",
    )
    verifier = make_hmac_sha256_verifier(bundle["material"]["shared_secrets"])
    state = replay(bundle["signed_events"], verifier=verifier)
    assert bundle["genesis"]["profile"] == "SATROOT-LICENSE-1"
    assert len(bundle["events"]) == 4
    assert bundle["material"]["signer_key_map"] == {"issuer": "issuer-key", "customer": "customer-key", "archive": "archive-key"}
    assert state.symbol == "LICBUNDLE1"
    assert state.supply == 0


def test_bootstrap_singleton_object_demo_release_hmac(tmp_path):
    released = bootstrap_singleton_object_demo_release(
        profile="SATROOT-RECEIPT-1",
        symbol="RECREL1",
        name="Receipt Release Asset",
        bundle_scheme="hmac-sha256",
        release_key_id="release-key",
        output_dir=tmp_path / "singleton_release",
        holder_account="buyer",
        archive_account="archive",
        release_metadata={"channel": "stable", "label": "Receipt Release Asset"},
    )
    bundle_dir = Path(released["bundle_dir"])
    release_dir = Path(released["release_dir"])
    assert (bundle_dir / "bundle_manifest.json").is_file()
    assert (release_dir / "release_manifest.json").is_file()
    assert (release_dir / "bundle_index.json").is_file()
    secrets = released["release_material"]["shared_secrets"]
    summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert summary["bundle_count"] == 1
    assert summary["release"]["channel"] == "stable"
    assert summary["release"]["label"] == "Receipt Release Asset"


def test_bootstrap_stable_reference_demo_bundle_hmac():
    bundle = bootstrap_stable_reference_demo_bundle(
        symbol="USDBUNDLE1",
        name="Stable Bundle Asset",
        scheme="hmac-sha256",
        root_id="abababababababababababababababababababababababababababababababab:0",
        reference_unit="GBP",
        nonce="stable-bundle-bootstrap",
    )
    verifier = make_hmac_sha256_verifier(bundle["material"]["shared_secrets"])
    state = replay(bundle["signed_events"], verifier=verifier)
    assert bundle["genesis"]["profile"] == "SATROOT-STABLE-1"
    assert bundle["genesis"]["reference_unit"] == "GBP"
    assert len(bundle["events"]) == 4
    assert bundle["material"]["signer_key_map"] == {"issuer": "issuer-key", "merchant": "merchant-key"}
    assert state.symbol == "USDBUNDLE1"
    assert state.genesis_metadata["reference_unit"] == "GBP"


def test_bootstrap_stable_reference_demo_release_hmac(tmp_path):
    released = bootstrap_stable_reference_demo_release(
        symbol="USDREL1",
        name="Stable Release Asset",
        bundle_scheme="hmac-sha256",
        release_key_id="release-key",
        output_dir=tmp_path / "stable_release",
        reference_unit="CAD",
        release_metadata={"channel": "stable", "label": "Stable Release Asset"},
    )
    bundle_dir = Path(released["bundle_dir"])
    release_dir = Path(released["release_dir"])
    assert (bundle_dir / "bundle_manifest.json").is_file()
    assert (release_dir / "release_manifest.json").is_file()
    assert (release_dir / "bundle_index.json").is_file()
    secrets = released["release_material"]["shared_secrets"]
    summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert summary["bundle_count"] == 1
    assert summary["release"]["channel"] == "stable"
    assert summary["release"]["label"] == "Stable Release Asset"


def test_bootstrap_stable_reference_demo_ledger_rejects_overallocated_distribution():
    with pytest.raises(SatRootError):
        bootstrap_stable_reference_demo_ledger(
            symbol="BADDEMO1",
            name="Bad Stable Demo",
            initial_balance="100",
            merchant_amount="90",
            service_amount="20",
        )


def test_bootstrap_release_publication_writes_hmac_material(tmp_path):
    bundle_dir = tmp_path / "bundle"
    assert main(
        [
            "bootstrap-genesis-bundle",
            "--symbol",
            "RELBOOT1",
            "--name",
            "Release Bootstrap Asset",
            "--scheme",
            "hmac-sha256",
            "--output-dir",
            str(bundle_dir),
        ]
    ) == 0

    publication_dir = tmp_path / "release"
    published = bootstrap_release_publication(
        [bundle_dir],
        output_dir=publication_dir,
        signature_scheme="hmac-sha256",
        key_id="release-key",
        release_metadata={"channel": "stable"},
    )
    assert (publication_dir / "release_secrets.json").exists()
    assert (publication_dir / "bundle_index.json").exists()
    assert (publication_dir / "release_manifest.json").exists()
    assert published["bundle_index"]["release"] == {"channel": "stable"}
    assert published["release_manifest"]["signature_key_id"] == "release-key"


def test_scaffold_event_record_transfer_replays_when_appended():
    events = load_events()
    next_event = scaffold_event_record(
        action="transfer",
        root_id=events[0]["root_id"],
        sequence=4,
        prev_event_id=event_id(events[-1]),
        signer="bob",
        from_account="bob",
        to_account="issuer",
        amount="1000",
    )
    state = replay([*events, next_event])
    assert state.balances["bob"] == 98_999_000
    assert state.balances["issuer"] == 750_001_000


def test_scaffold_event_from_ledger_uses_next_sequence_and_profile():
    events = load_events("events_usdroot1.json")
    next_event = scaffold_event_from_ledger(
        events,
        action="burn",
        signer="api_node",
        from_account="api_node",
        amount="1000",
    )
    assert next_event["sequence"] == 4
    assert next_event["prev_event_id"] == event_id(events[-1])
    assert next_event["profile"] == "SATROOT-STABLE-1"
    assert next_event["profile_mode"] == "reference-only"


def test_append_signed_event_to_ledger_demo_roundtrip():
    events = load_events()
    next_event = scaffold_event_from_ledger(
        events,
        action="transfer",
        signer="bob",
        from_account="bob",
        to_account="issuer",
        amount="1000",
    )
    appended = append_signed_event_to_ledger(events, next_event, scheme="demo", include_state_hash=True)
    assert len(appended) == len(events) + 1
    assert appended[-1]["signature"] == "demo"
    assert appended[-1]["state_hash"].startswith("sha256:")
    state = replay(appended)
    assert state.balances["bob"] == 98_999_000


def test_scaffold_machine_credit_consumption_event_requires_machine_profile():
    with pytest.raises(SatRootError):
        scaffold_machine_credit_consumption_event(load_events(), signer="bob", amount="1000")


def test_scaffold_machine_credit_consumption_event_from_machine_ledger():
    events = load_events("events_apicredit1.json")
    event = scaffold_machine_credit_consumption_event(events, signer="worker_node", amount="1000")
    assert event["action"] == "burn"
    assert event["from"] == "worker_node"
    assert event["amount"] == "1000"
    assert event["sequence"] == 4


def test_scaffold_singleton_object_archive_event_requires_supported_profile():
    with pytest.raises(SatRootError):
        scaffold_singleton_object_archive_event(load_events(), signer="bob")


def test_scaffold_singleton_object_transfer_event_from_receipt_ledger():
    events = load_events("events_receipt1.json")[:2]
    event = scaffold_singleton_object_transfer_event(events, signer="buyer", to_account="custodian")
    assert event["action"] == "transfer"
    assert event["from"] == "buyer"
    assert event["to"] == "custodian"
    assert event["amount"] == "1"
    assert event["sequence"] == 2


def test_scaffold_singleton_object_transfer_event_rejects_same_holder():
    events = load_events("events_identity1.json")[:2]
    with pytest.raises(SatRootError):
        scaffold_singleton_object_transfer_event(events, signer="node_alpha", to_account="node_alpha")


def test_scaffold_singleton_object_archive_event_from_receipt_ledger():
    events = load_events("events_receipt1.json")[:2]
    event = scaffold_singleton_object_archive_event(events, signer="buyer")
    assert event["action"] == "transfer"
    assert event["from"] == "buyer"
    assert event["to"] == "archive"
    assert event["amount"] == "1"
    assert event["sequence"] == 2


def test_scaffold_singleton_object_retirement_event_requires_archived_holder():
    events = load_events("events_receipt1.json")[:2]
    with pytest.raises(SatRootError):
        scaffold_singleton_object_retirement_event(events, signer="archive")


def test_scaffold_singleton_object_retirement_event_from_archived_receipt_ledger():
    events = load_events("events_receipt1.json")[:3]
    event = scaffold_singleton_object_retirement_event(events, signer="archive")
    assert event["action"] == "burn"
    assert event["from"] == "archive"
    assert event["amount"] == "1"
    assert event["sequence"] == 3


def test_load_protocol_schema_supports_rotate_authority():
    schema = load_protocol_schema()
    assert "rotate-authority" in schema["properties"]["action"]["enum"]


def test_load_bundle_manifest_schema_supports_signed_ledger_bundles():
    schema = load_bundle_manifest_schema()
    assert schema["properties"]["bundle_type"]["const"] == "signed-ledger"
    assert "hmac-sha256" in schema["properties"]["scheme"]["enum"]
    assert "verification_material_scope" in schema["properties"]
    assert "genesis" in schema["properties"]["files"]["properties"]


def test_load_bundle_index_schema_supports_bundle_indexes():
    schema = load_bundle_index_schema()
    assert schema["properties"]["index_type"]["const"] == "bundle-index"
    assert "bundles" in schema["properties"]


def test_load_release_manifest_schema_supports_release_manifests():
    schema = load_release_manifest_schema()
    assert schema["properties"]["manifest_type"]["const"] == "release-manifest"
    assert "signature_scheme" in schema["properties"]


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


def test_reject_blank_required_profile_field():
    events = load_events("events_identity1.json")
    events[0]["subject_id"] = "   "
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
    assert manifest["verification_material_scope"] == "shared-secret"
    assert manifest["record_count"] == 4
    assert manifest["symbol"] == "FLOOR1"
    assert manifest["final_state_snapshot"] == bundle["final_state_snapshot"]
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
    assert summary["verification_material_scope"] == "shared-secret"
    assert summary["symbol"] == "FLOOR1"
    assert summary["annotated_verified"] is True


def test_summarize_signed_ledger_bundle_reads_manifest_only(tmp_path):
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
    write_json(tmp_path / "bundle_manifest.json", manifest)

    summary = summarize_signed_ledger_bundle(tmp_path)
    assert summary["scheme"] == "hmac-sha256"
    assert summary["verification_material_scope"] == "shared-secret"
    assert summary["annotated_output"] is True
    assert summary["final_state_snapshot"] == bundle["final_state_snapshot"]
    assert summary["files"]["signed_events"] == "signed_events.json"


def test_lint_signed_ledger_bundle_accepts_clean_hmac_bundle(tmp_path):
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

    report = lint_signed_ledger_bundle(tmp_path)
    assert report["ok"] is True
    assert report["missing_files"] == []
    assert report["extra_files"] == []
    assert report["unhashed_declared_files"] == []
    assert report["dangling_hash_entries"] == []
    assert report["duplicate_declared_paths"] == []


def test_build_signed_ledger_bundle_index_from_bundle_dir(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    bundle_dir = tmp_path / "bundle_a"
    bundle_dir.mkdir()
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
    write_json(bundle_dir / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(bundle_dir / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(bundle_dir / "signed_events.json", bundle["signed_events"])
    write_json(bundle_dir / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(bundle_dir / "bundle_manifest.json", manifest)

    index = build_signed_ledger_bundle_index([bundle_dir], base_dir=tmp_path)
    assert index["protocol"] == "SATROOT-1"
    assert index["index_type"] == "bundle-index"
    assert index["bundle_count"] == 1
    assert index["bundles"][0]["bundle_path"] == "bundle_a"
    assert index["bundles"][0]["manifest_path"] == "bundle_a/bundle_manifest.json"
    assert index["bundles"][0]["scheme"] == "hmac-sha256"
    assert index["bundles"][0]["symbol"] == "FLOOR1"


def test_build_signed_ledger_bundle_index_includes_release_metadata(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    bundle_dir = tmp_path / "bundle_a"
    bundle_dir.mkdir()
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
    write_json(bundle_dir / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(bundle_dir / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(bundle_dir / "signed_events.json", bundle["signed_events"])
    write_json(bundle_dir / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(bundle_dir / "bundle_manifest.json", manifest)

    index = build_signed_ledger_bundle_index(
        [bundle_dir],
        base_dir=tmp_path,
        release_metadata={
            "channel": "stable",
            "label": "SATROOT FLOOR1 Demo",
            "published_at": "2026-06-22T12:00:00Z",
        },
    )
    assert index["release"] == {
        "channel": "stable",
        "label": "SATROOT FLOOR1 Demo",
        "published_at": "2026-06-22T12:00:00Z",
    }


def test_validate_bundle_index_schema_accepts_generated_index(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    bundle_dir = tmp_path / "bundle_a"
    bundle_dir.mkdir()
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
    write_json(bundle_dir / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(bundle_dir / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(bundle_dir / "signed_events.json", bundle["signed_events"])
    write_json(bundle_dir / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(bundle_dir / "bundle_manifest.json", manifest)

    index = build_signed_ledger_bundle_index([bundle_dir], base_dir=tmp_path)
    count = validate_instance_against_schema(index, load_bundle_index_schema())
    assert count == 1
    validate_bundle_index_consistency(index)


def test_validate_bundle_index_schema_accepts_release_metadata(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    bundle_dir = tmp_path / "bundle_a"
    bundle_dir.mkdir()
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
    write_json(bundle_dir / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(bundle_dir / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(bundle_dir / "signed_events.json", bundle["signed_events"])
    write_json(bundle_dir / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(bundle_dir / "bundle_manifest.json", manifest)

    index = build_signed_ledger_bundle_index(
        [bundle_dir],
        base_dir=tmp_path,
        release_metadata={
            "channel": "stable",
            "label": "SATROOT FLOOR1 Demo",
            "published_at": "2026-06-22T12:00:00Z",
        },
    )
    count = validate_instance_against_schema(index, load_bundle_index_schema())
    assert count == 1


def test_validate_bundle_index_consistency_rejects_mismatch():
    with pytest.raises(SatRootError):
        validate_bundle_index_consistency(
            {
                "protocol": "SATROOT-1",
                "version": "0.1",
                "index_type": "bundle-index",
                "bundle_count": 2,
                "bundles": [{"bundle_id": "sha256:" + ("0" * 64)}],
            }
        )


def test_build_signed_release_manifest_hmac(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    bundle_dir = tmp_path / "bundle_a"
    bundle_dir.mkdir()
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
    write_json(bundle_dir / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(bundle_dir / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(bundle_dir / "signed_events.json", bundle["signed_events"])
    write_json(bundle_dir / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(bundle_dir / "bundle_manifest.json", manifest)
    index = build_signed_ledger_bundle_index(
        [bundle_dir],
        base_dir=tmp_path,
        release_metadata={"channel": "stable", "label": "SATROOT FLOOR1 Demo", "published_at": "2026-06-26T12:00:00Z"},
    )
    index_path = tmp_path / "bundle_index.json"
    write_json(index_path, index)

    release_manifest = build_signed_release_manifest(
        index_path,
        signature_scheme="hmac-sha256",
        key_id="release-key",
        signer=make_hmac_sha256_signer({"release-key": "release-secret"}),
        base_dir=tmp_path,
    )
    assert release_manifest["manifest_type"] == "release-manifest"
    assert release_manifest["bundle_index_path"] == "bundle_index.json"
    assert release_manifest["signature_scheme"] == "hmac-sha256"
    assert release_manifest["signature_key_id"] == "release-key"
    assert release_manifest["signature"].startswith("hmac-sha256:")
    assert release_manifest["release"] == index["release"]


def test_bootstrap_release_hmac_material_generates_secret_map():
    material = bootstrap_release_hmac_material(["release-key"])
    assert set(material["shared_secrets"]) == {"release-key"}
    assert len(material["shared_secrets"]["release-key"]) == 64


def test_bootstrap_release_ed25519_material_generates_keypair_map():
    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            bootstrap_release_ed25519_material(["release-key"])
        return

    material = bootstrap_release_ed25519_material(["release-key"])
    assert set(material["private_keys"]) == {"release-key"}
    assert set(material["public_keys"]) == {"release-key"}
    assert len(material["private_keys"]["release-key"]) == 64
    assert len(material["public_keys"]["release-key"]) == 64


def test_validate_release_manifest_schema_accepts_generated_manifest(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    bundle_dir = tmp_path / "bundle_a"
    bundle_dir.mkdir()
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
    write_json(bundle_dir / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(bundle_dir / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(bundle_dir / "signed_events.json", bundle["signed_events"])
    write_json(bundle_dir / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(bundle_dir / "bundle_manifest.json", manifest)
    index = build_signed_ledger_bundle_index([bundle_dir], base_dir=tmp_path)
    index_path = tmp_path / "bundle_index.json"
    write_json(index_path, index)

    release_manifest = build_signed_release_manifest(
        index_path,
        signature_scheme="hmac-sha256",
        key_id="release-key",
        signer=make_hmac_sha256_signer({"release-key": "release-secret"}),
        base_dir=tmp_path,
    )
    count = validate_instance_against_schema(release_manifest, load_release_manifest_schema())
    assert count == 1


def test_build_signed_release_manifest_hmac_from_secrets_json(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    bundle_dir = tmp_path / "bundle_a"
    bundle_dir.mkdir()
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
    write_json(bundle_dir / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(bundle_dir / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(bundle_dir / "signed_events.json", bundle["signed_events"])
    write_json(bundle_dir / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(bundle_dir / "bundle_manifest.json", manifest)
    index = build_signed_ledger_bundle_index([bundle_dir], base_dir=tmp_path)
    index_path = tmp_path / "bundle_index.json"
    write_json(index_path, index)
    secrets_path = tmp_path / "release_secrets.json"
    write_json(secrets_path, {"release-key": "release-secret"})

    exit_code = main(
        [
            "build-release-manifest",
            str(index_path),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "release-key",
            "--secrets-json",
            str(secrets_path),
            "--output",
            str(tmp_path / "release_manifest.json"),
        ]
    )
    assert exit_code == 0

    release_manifest = json.loads((tmp_path / "release_manifest.json").read_text(encoding="utf-8"))
    assert release_manifest["signature_scheme"] == "hmac-sha256"
    assert release_manifest["signature_key_id"] == "release-key"


def test_verify_signed_release_manifest_accepts_hmac(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    bundle_dir = tmp_path / "bundle_a"
    bundle_dir.mkdir()
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
    write_json(bundle_dir / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(bundle_dir / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(bundle_dir / "signed_events.json", bundle["signed_events"])
    write_json(bundle_dir / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(bundle_dir / "bundle_manifest.json", manifest)
    index = build_signed_ledger_bundle_index(
        [bundle_dir],
        base_dir=tmp_path,
        release_metadata={"channel": "stable", "label": "SATROOT FLOOR1 Demo", "published_at": "2026-06-26T12:00:00Z"},
    )
    index_path = tmp_path / "bundle_index.json"
    write_json(index_path, index)
    release_manifest = build_signed_release_manifest(
        index_path,
        signature_scheme="hmac-sha256",
        key_id="release-key",
        signer=make_hmac_sha256_signer({"release-key": "release-secret"}),
        base_dir=tmp_path,
    )
    release_manifest_path = tmp_path / "release_manifest.json"
    write_json(release_manifest_path, release_manifest)

    summary = verify_signed_release_manifest(
        release_manifest_path,
        verifier=make_hmac_sha256_verifier({"release-key": "release-secret"}),
    )
    assert summary["signature_scheme"] == "hmac-sha256"
    assert summary["signature_key_id"] == "release-key"
    assert summary["bundle_index_path"] == "bundle_index.json"
    assert summary["release"] == index["release"]


def test_verify_signed_release_manifest_rejects_index_hash_mismatch(tmp_path):
    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="hmac-sha256")
    bundle_dir = tmp_path / "bundle_a"
    bundle_dir.mkdir()
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
    write_json(bundle_dir / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(bundle_dir / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(bundle_dir / "signed_events.json", bundle["signed_events"])
    write_json(bundle_dir / "annotated_signed_events.json", bundle["annotated_events"])
    write_json(bundle_dir / "bundle_manifest.json", manifest)
    index = build_signed_ledger_bundle_index([bundle_dir], base_dir=tmp_path)
    index_path = tmp_path / "bundle_index.json"
    write_json(index_path, index)
    release_manifest = build_signed_release_manifest(
        index_path,
        signature_scheme="hmac-sha256",
        key_id="release-key",
        signer=make_hmac_sha256_signer({"release-key": "release-secret"}),
        base_dir=tmp_path,
    )
    release_manifest["bundle_index_hash"] = "sha256:" + ("0" * 64)
    release_manifest_path = tmp_path / "release_manifest.json"
    write_json(release_manifest_path, release_manifest)

    with pytest.raises(SatRootError):
        verify_signed_release_manifest(
            release_manifest_path,
            verifier=make_hmac_sha256_verifier({"release-key": "release-secret"}),
        )


def test_build_signed_release_catalog_from_release_dirs(tmp_path):
    stable_release_dir, machine_release_dir = make_demo_release_dirs(tmp_path)

    catalog = build_signed_release_catalog(
        [stable_release_dir, machine_release_dir],
        base_dir=tmp_path,
        catalog_metadata={
            "channel": "stable",
            "label": "SATROOT Multi Release Catalog",
            "published_at": "2026-06-30T04:00:00Z",
        },
    )
    assert catalog["protocol"] == "SATROOT-1"
    assert catalog["catalog_type"] == "release-catalog"
    assert catalog["release_count"] == 2
    assert catalog["catalog"]["label"] == "SATROOT Multi Release Catalog"
    assert {entry["signature_scheme"] for entry in catalog["releases"]} == {"hmac-sha256"}
    assert {symbol for entry in catalog["releases"] for symbol in entry["bundle_symbols"]} == {"RELSTB1", "RELMCH1"}


def test_validate_release_catalog_schema_accepts_generated_catalog(tmp_path):
    stable_release_dir, machine_release_dir = make_demo_release_dirs(tmp_path)
    catalog = build_signed_release_catalog([stable_release_dir, machine_release_dir], base_dir=tmp_path)

    count = validate_instance_against_schema(catalog, load_release_catalog_schema())
    assert count == 1
    validate_release_catalog_consistency(catalog)


def test_build_and_verify_signed_release_catalog_manifest_hmac(tmp_path):
    stable_release_dir, machine_release_dir = make_demo_release_dirs(tmp_path)
    catalog = build_signed_release_catalog(
        [stable_release_dir, machine_release_dir],
        base_dir=tmp_path,
        catalog_metadata={
            "channel": "stable",
            "label": "SATROOT Multi Release Catalog",
            "published_at": "2026-06-30T04:30:00Z",
        },
    )
    catalog_path = tmp_path / "release_catalog.json"
    write_json(catalog_path, catalog)

    manifest = build_signed_release_catalog_manifest(
        catalog_path,
        signature_scheme="hmac-sha256",
        key_id="catalog-key",
        signer=make_hmac_sha256_signer({"catalog-key": "catalog-secret"}),
        base_dir=tmp_path,
    )
    count = validate_instance_against_schema(manifest, load_release_catalog_manifest_schema())
    assert count == 1

    manifest_path = tmp_path / "release_catalog_manifest.json"
    write_json(manifest_path, manifest)
    summary = verify_signed_release_catalog_manifest(
        manifest_path,
        verifier=make_hmac_sha256_verifier({"catalog-key": "catalog-secret"}),
    )
    assert summary["signature_scheme"] == "hmac-sha256"
    assert summary["signature_key_id"] == "catalog-key"
    assert summary["release_catalog_path"] == "release_catalog.json"
    assert summary["catalog"] == catalog["catalog"]


def test_cli_bootstrap_release_catalog_publication(tmp_path, capsys):
    stable_release_dir, machine_release_dir = make_demo_release_dirs(tmp_path)
    output_dir = tmp_path / "release_catalog_publication"

    exit_code = main(
        [
            "bootstrap-release-catalog-publication",
            stable_release_dir,
            machine_release_dir,
            "--output-dir",
            str(output_dir),
            "--channel",
            "stable",
            "--label",
            "SATROOT Catalog of Releases",
            "--published-at",
            "2026-06-30T05:00:00Z",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "catalog-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT release catalog publication to" in captured.out

    catalog = json.loads((output_dir / "release_catalog.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "release_catalog_manifest.json").read_text(encoding="utf-8"))
    secrets = json.loads((output_dir / "release_catalog_secrets.json").read_text(encoding="utf-8"))

    assert catalog["release_count"] == 2
    assert catalog["catalog"]["label"] == "SATROOT Catalog of Releases"
    assert manifest["signature_key_id"] == "catalog-key"

    verified = verify_signed_release_catalog_manifest(
        output_dir / "release_catalog_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert verified["release_count"] == 2
    assert verified["catalog"] == catalog["catalog"]


def test_cli_bootstrap_release_catalog_publication_with_preset_json_and_cli_overrides(tmp_path, capsys):
    stable_release_dir, machine_release_dir = make_demo_release_dirs(tmp_path)
    preset_path = tmp_path / "release_catalog_preset.json"
    write_json(
        preset_path,
        {
            "type": "SATROOT-RELEASE-CATALOG-PRESET",
            "version": "0.1",
            "release_dirs": [
                str(Path(stable_release_dir).relative_to(tmp_path)),
                str(Path(machine_release_dir).relative_to(tmp_path)),
            ],
            "recursive": True,
            "catalog": {
                "channel": "beta",
                "label": "SATROOT Preset Release Stack",
                "published_at": "2026-07-01T01:00:00Z",
            },
        },
    )
    output_dir = tmp_path / "release_catalog_preset_publication"

    exit_code = main(
        [
            "bootstrap-release-catalog-publication",
            "--preset-json",
            str(preset_path),
            "--output-dir",
            str(output_dir),
            "--label",
            "SATROOT Preset Override Stack",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "catalog-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT release catalog publication to" in captured.out

    catalog = json.loads((output_dir / "release_catalog.json").read_text(encoding="utf-8"))
    assert catalog["release_count"] == 2
    assert catalog["catalog"]["channel"] == "beta"
    assert catalog["catalog"]["label"] == "SATROOT Preset Override Stack"
    assert catalog["catalog"]["published_at"] == "2026-07-01T01:00:00Z"


def test_build_signed_release_catalog_index_from_catalog_dirs(tmp_path):
    index_dir = make_demo_release_catalog_index_dir(tmp_path)
    catalog_alpha_dir = tmp_path / "catalog_alpha"
    catalog_beta_dir = tmp_path / "catalog_beta"

    index = build_signed_release_catalog_index(
        [catalog_alpha_dir, catalog_beta_dir],
        base_dir=index_dir,
        index_metadata={
            "channel": "network",
            "label": "SATROOT Catalog Network",
            "published_at": "2026-07-02T03:30:00Z",
        },
    )
    assert index["protocol"] == "SATROOT-1"
    assert index["index_type"] == "release-catalog-index"
    assert index["release_catalog_count"] == 2
    assert index["index"]["label"] == "SATROOT Catalog Network"
    assert {entry["signature_scheme"] for entry in index["release_catalogs"]} == {"hmac-sha256"}
    assert sorted(index["release_catalogs"][0]["release_paths"])


def test_validate_release_catalog_index_schema_accepts_generated_index(tmp_path):
    catalog_alpha_dir = make_demo_release_catalog_dir(tmp_path / "catalog_alpha_root")
    catalog_beta_dir = make_demo_release_catalog_dir(tmp_path / "catalog_beta_root")
    index = build_signed_release_catalog_index([catalog_alpha_dir, catalog_beta_dir], base_dir=tmp_path)

    count = validate_instance_against_schema(index, load_release_catalog_index_schema())
    assert count == 1
    validate_release_catalog_index_consistency(index)


def test_build_and_verify_signed_release_catalog_index_manifest_hmac(tmp_path):
    catalog_alpha_dir = make_demo_release_catalog_dir(tmp_path / "catalog_alpha_root")
    catalog_beta_dir = make_demo_release_catalog_dir(tmp_path / "catalog_beta_root")
    index = build_signed_release_catalog_index(
        [catalog_alpha_dir, catalog_beta_dir],
        base_dir=tmp_path,
        index_metadata={
            "channel": "network",
            "label": "SATROOT Release Catalog Mesh",
            "published_at": "2026-07-02T04:00:00Z",
        },
    )
    index_path = tmp_path / "release_catalog_index.json"
    write_json(index_path, index)

    manifest = build_signed_release_catalog_index_manifest(
        index_path,
        signature_scheme="hmac-sha256",
        key_id="index-key",
        signer=make_hmac_sha256_signer({"index-key": "index-secret"}),
        base_dir=tmp_path,
    )
    count = validate_instance_against_schema(manifest, load_release_catalog_index_manifest_schema())
    assert count == 1

    manifest_path = tmp_path / "release_catalog_index_manifest.json"
    write_json(manifest_path, manifest)
    summary = verify_signed_release_catalog_index_manifest(
        manifest_path,
        verifier=make_hmac_sha256_verifier({"index-key": "index-secret"}),
    )
    assert summary["signature_scheme"] == "hmac-sha256"
    assert summary["signature_key_id"] == "index-key"
    assert summary["release_catalog_index_path"] == "release_catalog_index.json"
    assert summary["index"] == index["index"]


def test_cli_bootstrap_release_catalog_index_publication(tmp_path, capsys):
    catalog_alpha_dir = make_demo_release_catalog_dir(tmp_path / "catalog_alpha_root")
    catalog_beta_dir = make_demo_release_catalog_dir(tmp_path / "catalog_beta_root")
    output_dir = tmp_path / "release_catalog_index_publication"

    exit_code = main(
        [
            "bootstrap-release-catalog-index-publication",
            str(catalog_alpha_dir),
            str(catalog_beta_dir),
            "--output-dir",
            str(output_dir),
            "--channel",
            "network",
            "--label",
            "SATROOT Catalog Network",
            "--published-at",
            "2026-07-02T05:00:00Z",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "index-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT release catalog index publication to" in captured.out

    index = json.loads((output_dir / "release_catalog_index.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "release_catalog_index_manifest.json").read_text(encoding="utf-8"))
    secrets = json.loads((output_dir / "release_catalog_index_secrets.json").read_text(encoding="utf-8"))

    assert index["release_catalog_count"] == 2
    assert index["index"]["label"] == "SATROOT Catalog Network"
    assert manifest["signature_key_id"] == "index-key"

    verified = verify_signed_release_catalog_index_manifest(
        output_dir / "release_catalog_index_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert verified["release_catalog_count"] == 2
    assert verified["index"] == index["index"]


def test_cli_bootstrap_release_catalog_index_publication_with_preset_json_and_cli_overrides(tmp_path, capsys):
    catalog_alpha_dir = make_demo_release_catalog_dir(tmp_path / "catalog_alpha_root")
    catalog_beta_dir = make_demo_release_catalog_dir(tmp_path / "catalog_beta_root")
    preset_path = tmp_path / "release_catalog_index_preset.json"
    write_json(
        preset_path,
        {
            "type": "SATROOT-RELEASE-CATALOG-INDEX-PRESET",
            "version": "0.1",
            "release_catalog_dirs": [
                str(Path(catalog_alpha_dir).relative_to(tmp_path)),
                str(Path(catalog_beta_dir).relative_to(tmp_path)),
            ],
            "recursive": True,
            "index": {
                "channel": "network",
                "label": "SATROOT Preset Catalog Network",
                "published_at": "2026-07-02T06:00:00Z",
            },
        },
    )
    output_dir = tmp_path / "release_catalog_index_preset_publication"

    exit_code = main(
        [
            "bootstrap-release-catalog-index-publication",
            "--preset-json",
            str(preset_path),
            "--output-dir",
            str(output_dir),
            "--label",
            "SATROOT Preset Override Network",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "index-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT release catalog index publication to" in captured.out

    index = json.loads((output_dir / "release_catalog_index.json").read_text(encoding="utf-8"))
    assert index["release_catalog_count"] == 2
    assert index["index"]["channel"] == "network"
    assert index["index"]["label"] == "SATROOT Preset Override Network"
    assert index["index"]["published_at"] == "2026-07-02T06:00:00Z"


def test_cli_bootstrap_publication_stack_from_presets(tmp_path, capsys):
    catalog_preset_a = tmp_path / "stable_catalog.json"
    write_json(
        catalog_preset_a,
        {
            "type": "SATROOT-DEMO-CATALOG-PRESET",
            "version": "0.1",
            "profiles": ["SATROOT-STABLE-1"],
            "symbol_overrides": {"SATROOT-STABLE-1": "STKSTB1"},
            "name_overrides": {"SATROOT-STABLE-1": "Stack Stable Catalog"},
            "release": {
                "channel": "stable",
                "label": "Stack Stable Release",
                "published_at": "2026-07-01T02:00:00Z",
            },
        },
    )
    catalog_preset_b = tmp_path / "machine_catalog.json"
    write_json(
        catalog_preset_b,
        {
            "type": "SATROOT-DEMO-CATALOG-PRESET",
            "version": "0.1",
            "profiles": ["SATROOT-MACHINE-1"],
            "symbol_overrides": {"SATROOT-MACHINE-1": "STKMCH1"},
            "name_overrides": {"SATROOT-MACHINE-1": "Stack Machine Catalog"},
            "release": {
                "channel": "stable",
                "label": "Stack Machine Release",
                "published_at": "2026-07-01T03:00:00Z",
            },
        },
    )
    release_catalog_preset = tmp_path / "release_stack.json"
    write_json(
        release_catalog_preset,
        {
            "type": "SATROOT-RELEASE-CATALOG-PRESET",
            "version": "0.1",
            "catalog": {
                "channel": "stable",
                "label": "SATROOT Stack Releases",
                "published_at": "2026-07-01T04:00:00Z",
            },
        },
    )
    output_dir = tmp_path / "publication_stack"

    exit_code = main(
        [
            "bootstrap-publication-stack",
            "--catalog-preset-json",
            str(catalog_preset_a),
            "--catalog-preset-json",
            str(catalog_preset_b),
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--release-catalog-preset-json",
            str(release_catalog_preset),
            "--release-catalog-key-id",
            "catalog-key",
            "--output-dir",
            str(output_dir),
            "--label",
            "SATROOT Stack Override",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT publication stack to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["workspace_count"] == 2
    assert summary["release_catalog"]["release_count"] == 2
    assert summary["release_catalog"]["catalog"]["label"] == "SATROOT Stack Override"
    assert {entry["workspace_name"] for entry in summary["workspaces"]} == {"stable_catalog", "machine_catalog"}

    stable_summary = json.loads((output_dir / "catalog_workspaces" / "stable_catalog" / "summary.json").read_text(encoding="utf-8"))
    machine_summary = json.loads((output_dir / "catalog_workspaces" / "machine_catalog" / "summary.json").read_text(encoding="utf-8"))
    assert stable_summary["bundle_count"] == 1
    assert machine_summary["bundle_count"] == 1
    assert {entry["symbol"] for entry in stable_summary["bundles"]} == {"STKSTB1"}
    assert {entry["symbol"] for entry in machine_summary["bundles"]} == {"STKMCH1"}

    secrets = json.loads((output_dir / "release_catalog" / "release_catalog_secrets.json").read_text(encoding="utf-8"))
    verified = verify_signed_release_catalog_manifest(
        output_dir / "release_catalog" / "release_catalog_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert verified["release_count"] == 2
    assert verified["catalog"]["label"] == "SATROOT Stack Override"


def test_cli_bootstrap_publication_stack_with_stack_preset_json(tmp_path, capsys):
    catalog_preset = tmp_path / "identity_catalog.json"
    write_json(
        catalog_preset,
        {
            "type": "SATROOT-DEMO-CATALOG-PRESET",
            "version": "0.1",
            "profiles": ["SATROOT-IDENTITY-1"],
            "symbol_overrides": {"SATROOT-IDENTITY-1": "STKID1"},
            "name_overrides": {"SATROOT-IDENTITY-1": "Stack Identity Catalog"},
            "release": {
                "channel": "stable",
                "label": "Stack Identity Release",
                "published_at": "2026-07-01T05:00:00Z",
            },
        },
    )
    stack_preset = tmp_path / "publication_stack.json"
    write_json(
        stack_preset,
        {
            "type": "SATROOT-PUBLICATION-STACK-PRESET",
            "version": "0.1",
            "catalog_presets": [str(Path(catalog_preset).relative_to(tmp_path))],
            "release_catalog": {
                "channel": "beta",
                "label": "SATROOT Embedded Stack",
                "published_at": "2026-07-01T06:00:00Z",
            },
        },
    )
    output_dir = tmp_path / "publication_stack_single"

    exit_code = main(
        [
            "bootstrap-publication-stack",
            "--stack-preset-json",
            str(stack_preset),
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--release-catalog-key-id",
            "catalog-key",
            "--output-dir",
            str(output_dir),
            "--label",
            "SATROOT Embedded Override",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT publication stack to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["workspace_count"] == 1
    assert summary["stack_preset_path"] == str(stack_preset.resolve())
    assert summary["release_catalog"]["catalog"]["channel"] == "beta"
    assert summary["release_catalog"]["catalog"]["label"] == "SATROOT Embedded Override"

    identity_summary = json.loads((output_dir / "catalog_workspaces" / "identity_catalog" / "summary.json").read_text(encoding="utf-8"))
    assert identity_summary["bundle_count"] == 1
    assert {entry["symbol"] for entry in identity_summary["bundles"]} == {"STKID1"}


def test_cli_bootstrap_publication_network_from_presets(tmp_path, capsys):
    stable_catalog_preset = tmp_path / "stable_catalog.json"
    write_json(
        stable_catalog_preset,
        {
            "type": "SATROOT-DEMO-CATALOG-PRESET",
            "version": "0.1",
            "profiles": ["SATROOT-STABLE-1"],
            "symbol_overrides": {"SATROOT-STABLE-1": "NETSTB1"},
            "name_overrides": {"SATROOT-STABLE-1": "Network Stable Catalog"},
            "release": {
                "channel": "stable",
                "label": "Network Stable Release",
                "published_at": "2026-07-03T01:00:00Z",
            },
        },
    )
    machine_catalog_preset = tmp_path / "machine_catalog.json"
    write_json(
        machine_catalog_preset,
        {
            "type": "SATROOT-DEMO-CATALOG-PRESET",
            "version": "0.1",
            "profiles": ["SATROOT-MACHINE-1"],
            "symbol_overrides": {"SATROOT-MACHINE-1": "NETMCH1"},
            "name_overrides": {"SATROOT-MACHINE-1": "Network Machine Catalog"},
            "release": {
                "channel": "stable",
                "label": "Network Machine Release",
                "published_at": "2026-07-03T02:00:00Z",
            },
        },
    )
    stack_preset_a = tmp_path / "stack_a.json"
    write_json(
        stack_preset_a,
        {
            "type": "SATROOT-PUBLICATION-STACK-PRESET",
            "version": "0.1",
            "catalog_presets": [str(Path(stable_catalog_preset).relative_to(tmp_path))],
            "release_catalog": {
                "channel": "stable",
                "label": "Network Stack Alpha",
                "published_at": "2026-07-03T03:00:00Z",
            },
        },
    )
    stack_preset_b = tmp_path / "stack_b.json"
    write_json(
        stack_preset_b,
        {
            "type": "SATROOT-PUBLICATION-STACK-PRESET",
            "version": "0.1",
            "catalog_presets": [str(Path(machine_catalog_preset).relative_to(tmp_path))],
            "release_catalog": {
                "channel": "beta",
                "label": "Network Stack Beta",
                "published_at": "2026-07-03T04:00:00Z",
            },
        },
    )
    index_preset = tmp_path / "network_index.json"
    write_json(
        index_preset,
        {
            "type": "SATROOT-RELEASE-CATALOG-INDEX-PRESET",
            "version": "0.1",
            "index": {
                "channel": "network",
                "label": "SATROOT Network Index",
                "published_at": "2026-07-03T05:00:00Z",
            },
        },
    )
    output_dir = tmp_path / "publication_network"

    exit_code = main(
        [
            "bootstrap-publication-network",
            "--stack-preset-json",
            str(stack_preset_a),
            "--stack-preset-json",
            str(stack_preset_b),
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--release-catalog-key-id",
            "catalog-key",
            "--release-catalog-index-preset-json",
            str(index_preset),
            "--release-catalog-index-key-id",
            "index-key",
            "--output-dir",
            str(output_dir),
            "--label",
            "SATROOT Network Override",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT publication network to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["stack_count"] == 2
    assert summary["release_catalog_index"]["release_catalog_count"] == 2
    assert summary["release_catalog_index"]["index"]["label"] == "SATROOT Network Override"
    assert {entry["workspace_name"] for entry in summary["workspaces"]} == {"stack_a", "stack_b"}

    alpha_summary = json.loads((output_dir / "stack_workspaces" / "stack_a" / "summary.json").read_text(encoding="utf-8"))
    beta_summary = json.loads((output_dir / "stack_workspaces" / "stack_b" / "summary.json").read_text(encoding="utf-8"))
    assert alpha_summary["workspace_count"] == 1
    assert beta_summary["workspace_count"] == 1
    assert alpha_summary["release_catalog"]["catalog"]["label"] == "Network Stack Alpha"
    assert beta_summary["release_catalog"]["catalog"]["label"] == "Network Stack Beta"

    secrets = json.loads((output_dir / "release_catalog_index" / "release_catalog_index_secrets.json").read_text(encoding="utf-8"))
    verified = verify_signed_release_catalog_index_manifest(
        output_dir / "release_catalog_index" / "release_catalog_index_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert verified["release_catalog_count"] == 2
    assert verified["index"]["label"] == "SATROOT Network Override"


def test_cli_bootstrap_publication_network_with_network_preset_json(tmp_path, capsys):
    identity_catalog_preset = tmp_path / "identity_catalog.json"
    write_json(
        identity_catalog_preset,
        {
            "type": "SATROOT-DEMO-CATALOG-PRESET",
            "version": "0.1",
            "profiles": ["SATROOT-IDENTITY-1"],
            "symbol_overrides": {"SATROOT-IDENTITY-1": "NETID1"},
            "name_overrides": {"SATROOT-IDENTITY-1": "Network Identity Catalog"},
            "release": {
                "channel": "stable",
                "label": "Network Identity Release",
                "published_at": "2026-07-03T06:00:00Z",
            },
        },
    )
    stack_preset = tmp_path / "stack_single.json"
    write_json(
        stack_preset,
        {
            "type": "SATROOT-PUBLICATION-STACK-PRESET",
            "version": "0.1",
            "catalog_presets": [str(Path(identity_catalog_preset).relative_to(tmp_path))],
            "release_catalog": {
                "channel": "stable",
                "label": "Embedded Network Stack",
                "published_at": "2026-07-03T07:00:00Z",
            },
        },
    )
    network_preset = tmp_path / "publication_network.json"
    write_json(
        network_preset,
        {
            "type": "SATROOT-PUBLICATION-NETWORK-PRESET",
            "version": "0.1",
            "stack_presets": [str(Path(stack_preset).relative_to(tmp_path))],
            "release_catalog_index": {
                "channel": "mesh",
                "label": "SATROOT Embedded Network",
                "published_at": "2026-07-03T08:00:00Z",
            },
        },
    )
    output_dir = tmp_path / "publication_network_single"

    exit_code = main(
        [
            "bootstrap-publication-network",
            "--network-preset-json",
            str(network_preset),
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--release-catalog-key-id",
            "catalog-key",
            "--release-catalog-index-key-id",
            "index-key",
            "--output-dir",
            str(output_dir),
            "--label",
            "SATROOT Embedded Network Override",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT publication network to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["stack_count"] == 1
    assert summary["network_preset_path"] == str(network_preset.resolve())
    assert summary["release_catalog_index"]["index"]["channel"] == "mesh"
    assert summary["release_catalog_index"]["index"]["label"] == "SATROOT Embedded Network Override"

    stack_summary = json.loads((output_dir / "stack_workspaces" / "stack_single" / "summary.json").read_text(encoding="utf-8"))
    assert stack_summary["workspace_count"] == 1
    assert {entry["symbol"] for entry in json.loads((output_dir / "stack_workspaces" / "stack_single" / "catalog_workspaces" / "identity_catalog" / "summary.json").read_text(encoding="utf-8"))["bundles"]} == {"NETID1"}


def test_cli_publish_publication_stack_from_existing_catalog_workspaces(tmp_path, capsys):
    stable_dir = tmp_path / "stable_workspace"
    machine_dir = tmp_path / "machine_workspace"

    assert main(
        [
            "bootstrap-demo-catalog",
            "--scheme",
            "hmac-sha256",
            "--profile",
            "SATROOT-STABLE-1",
            "--release-key-id",
            "release-key",
            "--output-dir",
            str(stable_dir),
            "--channel",
            "stable",
            "--label",
            "Stable Existing Workspace",
            "--published-at",
            "2026-07-06T01:00:00Z",
        ]
    ) == 0
    capsys.readouterr()
    assert main(
        [
            "bootstrap-demo-catalog",
            "--scheme",
            "hmac-sha256",
            "--profile",
            "SATROOT-MACHINE-1",
            "--release-key-id",
            "release-key",
            "--output-dir",
            str(machine_dir),
            "--channel",
            "stable",
            "--label",
            "Machine Existing Workspace",
            "--published-at",
            "2026-07-06T02:00:00Z",
        ]
    ) == 0
    capsys.readouterr()

    output_dir = tmp_path / "published_stack"
    exit_code = main(
        [
            "publish-publication-stack",
            str(stable_dir),
            str(machine_dir),
            "--scheme",
            "hmac-sha256",
            "--release-catalog-key-id",
            "catalog-key",
            "--output-dir",
            str(output_dir),
            "--channel",
            "stable",
            "--label",
            "Published Existing Stack",
            "--published-at",
            "2026-07-06T03:00:00Z",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT publication stack from existing workspaces to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["workspace_count"] == 2
    assert summary["catalog_preset_paths"] == []
    assert summary["release_catalog"]["catalog"]["label"] == "Published Existing Stack"
    assert {entry["workspace_name"] for entry in summary["workspaces"]} == {"stable_workspace", "machine_workspace"}
    assert (output_dir / "catalog_workspaces" / "stable_workspace" / "summary.json").is_file()
    assert (output_dir / "catalog_workspaces" / "machine_workspace" / "summary.json").is_file()

    secrets = json.loads((output_dir / "release_catalog" / "release_catalog_secrets.json").read_text(encoding="utf-8"))
    verified = verify_signed_release_catalog_manifest(
        output_dir / "release_catalog" / "release_catalog_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert verified["release_count"] == 2
    assert verified["catalog"]["label"] == "Published Existing Stack"
    assert main(["publication-stack-lint", str(output_dir)]) == 0
    capsys.readouterr()


def test_cli_publish_publication_network_from_existing_stack_workspaces(tmp_path, capsys):
    stack_alpha = tmp_path / "stack_alpha_root" / "publication_stack"
    stack_beta = tmp_path / "stack_beta_root" / "publication_stack"
    (tmp_path / "stack_alpha_root").mkdir()
    (tmp_path / "stack_beta_root").mkdir()
    alpha_dir = make_demo_publication_stack_dir(tmp_path / "stack_alpha_root")
    beta_dir = make_demo_publication_stack_dir(tmp_path / "stack_beta_root")
    assert alpha_dir == stack_alpha
    assert beta_dir == stack_beta
    capsys.readouterr()

    output_dir = tmp_path / "published_network"
    exit_code = main(
        [
            "publish-publication-network",
            str(alpha_dir),
            str(beta_dir),
            "--scheme",
            "hmac-sha256",
            "--release-catalog-index-key-id",
            "index-key",
            "--output-dir",
            str(output_dir),
            "--channel",
            "network",
            "--label",
            "Published Existing Network",
            "--published-at",
            "2026-07-06T04:00:00Z",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT publication network from existing workspaces to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["stack_count"] == 2
    assert summary["stack_preset_paths"] == []
    assert summary["release_catalog_index"]["index"]["label"] == "Published Existing Network"
    assert {entry["workspace_name"] for entry in summary["workspaces"]} == {"publication_stack", "publication_stack-2"}
    assert (output_dir / "stack_workspaces" / "publication_stack" / "summary.json").is_file()
    assert (output_dir / "stack_workspaces" / "publication_stack-2" / "summary.json").is_file()

    secrets = json.loads((output_dir / "release_catalog_index" / "release_catalog_index_secrets.json").read_text(encoding="utf-8"))
    verified = verify_signed_release_catalog_index_manifest(
        output_dir / "release_catalog_index" / "release_catalog_index_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert verified["release_catalog_count"] == 2
    assert verified["index"]["label"] == "Published Existing Network"
    assert main(["publication-network-lint", str(output_dir)]) == 0
    capsys.readouterr()


def test_cli_bootstrap_publication_registry_workspace_from_publication_network(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)
    output_dir = tmp_path / "publication_registry_workspace"

    exit_code = main(
        [
            "bootstrap-publication-registry-workspace",
            "--publication-network-dir",
            str(network_dir),
            "--scheme",
            "hmac-sha256",
            "--publication-descriptor-index-key-id",
            "descriptor-key",
            "--publication-metadata-key-id",
            "metadata-key",
            "--publication-metadata-catalog-key-id",
            "catalog-key",
            "--publication-registry-key-id",
            "registry-key",
            "--output-dir",
            str(output_dir),
            "--descriptor-index-channel",
            "network",
            "--descriptor-index-label",
            "Workspace Descriptor Index",
            "--publication-metadata-catalog-channel",
            "network",
            "--publication-metadata-catalog-label",
            "Workspace Metadata Catalog",
            "--publication-registry-channel",
            "network",
            "--publication-registry-label",
            "Workspace Publication Registry",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT publication registry workspace to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["source_publication_network_dir"] == str(network_dir.resolve())
    assert summary["artifact_count"] == 12
    assert summary["publication_metadata_bundle_count"] == 12
    assert summary["publication_descriptor_index"]["index"]["label"] == "Workspace Descriptor Index"
    assert summary["publication_metadata_catalog"]["index"]["label"] == "Workspace Metadata Catalog"
    assert summary["publication_registry"]["index"]["label"] == "Workspace Publication Registry"
    assert summary["publication_network_dir"] == str((output_dir / "publication_network").resolve())
    assert Path(summary["release_catalog_index_dir"]) == (output_dir / "publication_network" / "release_catalog_index").resolve()
    assert (output_dir / "publication_network" / "release_catalog_index" / "release_catalog_index_manifest.json").is_file()
    assert (output_dir / "publication_descriptor_index" / "publication_descriptor_index_manifest.json").is_file()
    assert (output_dir / "publication_metadata_catalog" / "publication_metadata_catalog_manifest.json").is_file()
    assert (output_dir / "publication_registry" / "publication_registry_manifest.json").is_file()

    secrets = json.loads((output_dir / "publication_registry" / "publication_registry_secrets.json").read_text(encoding="utf-8"))
    verified = verify_signed_publication_registry_manifest(
        output_dir / "publication_registry" / "publication_registry_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert verified["component_count"] == 3
    assert verified["index"]["label"] == "Workspace Publication Registry"
    assert main(["publication-registry-lint", str(output_dir / "publication_registry")]) == 0
    capsys.readouterr()


def test_cli_inventory_artifacts_reports_recursive_publication_network(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)

    exit_code = main(["inventory-artifacts", str(network_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"publication_network_count":1' in captured.out
    assert '"publication_stack_count":2' in captured.out
    assert '"demo_catalog_workspace_count":2' in captured.out
    assert '"release_catalog_index_count":1' in captured.out
    assert '"release_catalog_count":2' in captured.out
    assert '"release_count":2' in captured.out
    assert '"bundle_count":2' in captured.out
    assert '"workspace_names":["stack_a","stack_b"]' in captured.out


def test_cli_inventory_artifacts_non_recursive_reports_top_level_only(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)

    exit_code = main(["inventory-artifacts", str(network_dir), "--non-recursive"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"publication_network_count":1' in captured.out
    assert '"publication_stack_count":0' in captured.out
    assert '"demo_catalog_workspace_count":0' in captured.out
    assert '"release_catalog_index_count":0' in captured.out
    assert '"release_catalog_count":0' in captured.out
    assert '"release_count":0' in captured.out
    assert '"bundle_count":0' in captured.out


def test_cli_inventory_artifacts_reports_publication_registry(tmp_path, capsys):
    registry_dir = make_publication_registry_dir(tmp_path)

    exit_code = main(["inventory-artifacts", str(registry_dir), "--non-recursive"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"publication_registry_count":1' in captured.out
    assert '"publication_network_count":0' in captured.out


def test_cli_export_demo_catalog_preset_from_workspace(tmp_path):
    output_dir = make_demo_catalog_workspace_dir(tmp_path)
    preset_path = tmp_path / "exported_catalog.json"

    exit_code = main(["export-demo-catalog-preset", str(output_dir), "--output", str(preset_path)])
    assert exit_code == 0

    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    loaded = load_demo_catalog_preset(preset_path)
    assert preset["type"] == "SATROOT-DEMO-CATALOG-PRESET"
    assert preset["profiles"] == ["SATROOT-STABLE-1", "SATROOT-MACHINE-1"]
    assert preset["release"]["label"] == "CLI Demo Catalog"
    assert loaded["profiles"] == ["SATROOT-STABLE-1", "SATROOT-MACHINE-1"]
    assert loaded["release_metadata"]["published_at"] == "2026-07-05T02:00:00Z"


def test_cli_export_publication_stack_preset_with_generated_catalog_presets(tmp_path):
    stack_dir = make_demo_publication_stack_dir(tmp_path)
    preset_path = tmp_path / "exported_stack.json"
    catalog_preset_dir = tmp_path / "exported_catalog_presets"

    exit_code = main(
        [
            "export-publication-stack-preset",
            str(stack_dir),
            "--catalog-preset-dir",
            str(catalog_preset_dir),
            "--output",
            str(preset_path),
        ]
    )
    assert exit_code == 0

    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    loaded = load_publication_stack_preset(preset_path)
    assert preset["type"] == "SATROOT-PUBLICATION-STACK-PRESET"
    assert preset["release_catalog"]["label"] == "Publication Stack Override"
    assert sorted(Path(value).name for value in loaded["catalog_preset_paths"]) == ["machine_catalog.json", "stable_catalog.json"]

    stable_catalog = json.loads((catalog_preset_dir / "stable_catalog.json").read_text(encoding="utf-8"))
    machine_catalog = json.loads((catalog_preset_dir / "machine_catalog.json").read_text(encoding="utf-8"))
    assert stable_catalog["profiles"] == ["SATROOT-STABLE-1"]
    assert machine_catalog["profiles"] == ["SATROOT-MACHINE-1"]
    assert stable_catalog["symbol_overrides"]["SATROOT-STABLE-1"] == "PSTSTB1"
    assert machine_catalog["symbol_overrides"]["SATROOT-MACHINE-1"] == "PSTMCH1"


def test_cli_export_publication_network_preset_with_generated_nested_presets(tmp_path):
    network_dir = make_demo_publication_network_dir(tmp_path)
    preset_path = tmp_path / "exported_network.json"
    stack_preset_dir = tmp_path / "exported_stack_presets"
    catalog_preset_dir = tmp_path / "exported_catalog_presets"

    exit_code = main(
        [
            "export-publication-network-preset",
            str(network_dir),
            "--stack-preset-dir",
            str(stack_preset_dir),
            "--catalog-preset-dir",
            str(catalog_preset_dir),
            "--output",
            str(preset_path),
        ]
    )
    assert exit_code == 0

    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    loaded = load_publication_network_preset(preset_path)
    assert preset["type"] == "SATROOT-PUBLICATION-NETWORK-PRESET"
    assert preset["release_catalog_index"]["label"] == "Publication Network Override"
    assert sorted(Path(value).name for value in loaded["stack_preset_paths"]) == ["stack_a.json", "stack_b.json"]

    stack_a = json.loads((stack_preset_dir / "stack_a.json").read_text(encoding="utf-8"))
    stack_b = json.loads((stack_preset_dir / "stack_b.json").read_text(encoding="utf-8"))
    assert stack_a["release_catalog"]["label"] == "Publication Network Stack Alpha"
    assert stack_b["release_catalog"]["label"] == "Publication Network Stack Beta"
    assert (catalog_preset_dir / "stack_a" / "stable_catalog.json").is_file()
    assert (catalog_preset_dir / "stack_b" / "machine_catalog.json").is_file()


def test_cli_export_publication_registry_preset(tmp_path):
    registry_dir = make_publication_registry_dir(tmp_path)
    preset_path = tmp_path / "exported_registry.json"

    exit_code = main(["export-publication-registry-preset", str(registry_dir), "--output", str(preset_path)])
    assert exit_code == 0

    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    loaded = load_publication_registry_preset(preset_path)
    assert preset["type"] == "SATROOT-PUBLICATION-REGISTRY-PRESET"
    assert Path(loaded["release_catalog_index_dir"]).name == "release_catalog_index"
    assert Path(loaded["publication_descriptor_index_dir"]).name == "publication_descriptor_index_publication"
    assert Path(loaded["publication_metadata_catalog_dir"]).name == "publication_metadata_catalog_publication"
    assert preset["registry"]["label"] == "SATROOT Publication Registry"


def test_cli_export_publication_metadata_catalog_preset(tmp_path):
    catalog_dir = make_publication_metadata_catalog_dir(tmp_path)
    preset_path = tmp_path / "exported_publication_metadata_catalog.json"

    exit_code = main(["export-publication-metadata-catalog-preset", str(catalog_dir), "--output", str(preset_path)])
    assert exit_code == 0

    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    loaded = load_publication_metadata_catalog_preset(preset_path)
    assert preset["type"] == "SATROOT-PUBLICATION-METADATA-CATALOG-PRESET"
    assert sorted(Path(value).name for value in loaded["publication_metadata_bundle_dirs"]) == [
        "publication_metadata_network",
        "publication_metadata_release",
    ]
    assert preset["catalog"]["label"] == "SATROOT Metadata Catalog Publication"


def test_cli_export_publication_descriptor_index_preset(tmp_path):
    descriptor_index_dir = make_publication_descriptor_index_dir(tmp_path)
    preset_path = tmp_path / "exported_publication_descriptor_index.json"

    exit_code = main(["export-publication-descriptor-index-preset", str(descriptor_index_dir), "--output", str(preset_path)])
    assert exit_code == 0

    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    loaded = load_publication_descriptor_index_preset(preset_path)
    assert preset["type"] == "SATROOT-PUBLICATION-DESCRIPTOR-INDEX-PRESET"
    assert len(loaded["artifact_paths"]) == 12
    loaded_names = {Path(value).name for value in loaded["artifact_paths"]}
    assert {"publication_network", "stack_a", "stack_b", "release_catalog_index", "stable_catalog", "machine_catalog"} <= loaded_names
    assert preset["index"]["label"] == "SATROOT Descriptor Publication"


def test_cli_render_publication_report_for_network(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)

    exit_code = main(["render-publication-report", str(network_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "# SATROOT Publication Network Report" in captured.out
    assert "- Stack count: `2`" in captured.out
    assert "- Label: `Publication Network Override`" in captured.out
    assert "## Stack Workspaces" in captured.out
    assert "- `stack_a`:" in captured.out


def test_cli_render_publication_report_for_release(tmp_path, capsys):
    release_dir = make_demo_release_catalog_dir(tmp_path).parent / "stable_workspace" / "release"

    exit_code = main(["render-publication-report", str(release_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "# SATROOT Release Report" in captured.out
    assert "- Bundle count: `1`" in captured.out
    assert "## Bundles" in captured.out
    assert "- `RELSTB1`" in captured.out


def test_cli_render_publication_report_for_registry(tmp_path, capsys):
    registry_dir = make_publication_registry_dir(tmp_path)

    exit_code = main(["render-publication-report", str(registry_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "# SATROOT Publication Registry Report" in captured.out
    assert "- Component count: `3`" in captured.out
    assert "## Components" in captured.out
    assert "Release Catalog Index" in captured.out


def test_cli_export_publication_descriptor_for_network(tmp_path):
    network_dir = make_demo_publication_network_dir(tmp_path)
    output_path = tmp_path / "network_descriptor.json"

    exit_code = main(["export-publication-descriptor", str(network_dir), "--output", str(output_path)])
    assert exit_code == 0

    descriptor = json.loads(output_path.read_text(encoding="utf-8"))
    assert descriptor["descriptor_type"] == "SATROOT-ARTIFACT-DESCRIPTOR"
    assert descriptor["artifact_kind"] == "publication-network"
    assert descriptor["stack_count"] == 2
    assert descriptor["workspace_names"] == ["stack_a", "stack_b"]
    assert descriptor["release_catalog_index"]["label"] == "Publication Network Override"


def test_cli_export_publication_descriptor_for_registry(tmp_path):
    registry_dir = make_publication_registry_dir(tmp_path)
    output_path = tmp_path / "registry_descriptor.json"

    exit_code = main(["export-publication-descriptor", str(registry_dir), "--output", str(output_path)])
    assert exit_code == 0

    descriptor = json.loads(output_path.read_text(encoding="utf-8"))
    assert descriptor["descriptor_type"] == "SATROOT-ARTIFACT-DESCRIPTOR"
    assert descriptor["artifact_kind"] == "publication-registry"
    assert descriptor["component_count"] == 3
    assert descriptor["components"] == [
        "publication_descriptor_index_publication",
        "publication_metadata_catalog_publication",
        "release_catalog_index_publication",
    ]


def test_cli_export_publication_descriptor_for_release(tmp_path):
    release_dir = make_demo_release_catalog_dir(tmp_path).parent / "stable_workspace" / "release"
    output_path = tmp_path / "release_descriptor.json"

    exit_code = main(["export-publication-descriptor", str(release_dir), "--output", str(output_path)])
    assert exit_code == 0

    descriptor = json.loads(output_path.read_text(encoding="utf-8"))
    assert descriptor["descriptor_type"] == "SATROOT-ARTIFACT-DESCRIPTOR"
    assert descriptor["artifact_kind"] == "release"
    assert descriptor["bundle_count"] == 1
    assert descriptor["release"]["label"] == "Stable Release Workspace"
    assert descriptor["bundle_symbols"] == ["RELSTB1"]


def test_cli_build_publication_descriptor_index_recursive(tmp_path):
    network_dir = make_demo_publication_network_dir(tmp_path)
    output_path = tmp_path / "descriptor_index.json"

    exit_code = main(
        [
            "build-publication-descriptor-index",
            "--discover-under",
            str(network_dir),
            "--channel",
            "network",
            "--label",
            "SATROOT Descriptor Index",
            "--published-at",
            "2026-07-07T01:00:00Z",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    index = json.loads(output_path.read_text(encoding="utf-8"))
    assert index["type"] == "SATROOT-PUBLICATION-DESCRIPTOR-INDEX"
    assert index["artifact_count"] == 12
    assert index["artifact_kind_counts"]["bundle"] == 2
    assert index["artifact_kind_counts"]["release"] == 2
    assert index["artifact_kind_counts"]["release-catalog"] == 2
    assert index["artifact_kind_counts"]["release-catalog-index"] == 1
    assert index["artifact_kind_counts"]["demo-catalog"] == 2
    assert index["artifact_kind_counts"]["publication-stack"] == 2
    assert index["artifact_kind_counts"]["publication-network"] == 1
    assert index["index"]["label"] == "SATROOT Descriptor Index"


def test_cli_build_publication_descriptor_index_non_recursive(tmp_path):
    network_dir = make_demo_publication_network_dir(tmp_path)
    output_path = tmp_path / "descriptor_index_non_recursive.json"

    exit_code = main(
        [
            "build-publication-descriptor-index",
            "--discover-under",
            str(network_dir),
            "--non-recursive",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    index = json.loads(output_path.read_text(encoding="utf-8"))
    assert index["artifact_count"] == 1
    assert index["artifact_kind_counts"]["publication-network"] == 1
    assert index["artifact_kind_counts"]["publication-stack"] == 0
    assert index["artifacts"][0]["artifact_kind"] == "publication-network"


def test_cli_build_publication_descriptor_index_for_registry_path(tmp_path):
    registry_dir = make_publication_registry_dir(tmp_path)
    output_path = tmp_path / "registry_descriptor_index.json"

    exit_code = main(["build-publication-descriptor-index", str(registry_dir), "--output", str(output_path)])
    assert exit_code == 0

    index = json.loads(output_path.read_text(encoding="utf-8"))
    assert index["artifact_count"] == 1
    assert index["artifact_kind_counts"]["publication-registry"] == 1
    assert index["artifacts"][0]["artifact_kind"] == "publication-registry"


def test_validate_publication_descriptor_index_schema_accepts_generated_index(tmp_path):
    network_dir = make_demo_publication_network_dir(tmp_path)
    index = json.loads((tmp_path / "descriptor_index.json").read_text(encoding="utf-8")) if (tmp_path / "descriptor_index.json").exists() else None
    if index is None:
        output_path = tmp_path / "descriptor_index.json"
        assert main(["build-publication-descriptor-index", "--discover-under", str(network_dir), "--output", str(output_path)]) == 0
        index = json.loads(output_path.read_text(encoding="utf-8"))

    count = validate_instance_against_schema(index, load_publication_descriptor_index_schema())
    assert count == 1
    validate_publication_descriptor_index_consistency(index)


def test_build_and_verify_signed_publication_descriptor_index_manifest_hmac(tmp_path):
    network_dir = make_demo_publication_network_dir(tmp_path)
    index = json.loads((tmp_path / "descriptor_index.json").read_text(encoding="utf-8")) if (tmp_path / "descriptor_index.json").exists() else None
    if index is None:
        output_path = tmp_path / "descriptor_index.json"
        assert main(["build-publication-descriptor-index", "--discover-under", str(network_dir), "--output", str(output_path)]) == 0
        index = json.loads(output_path.read_text(encoding="utf-8"))
        index_path = output_path
    else:
        index_path = tmp_path / "descriptor_index.json"
        write_json(index_path, index)

    manifest = build_signed_publication_descriptor_index_manifest(
        index_path,
        signature_scheme="hmac-sha256",
        key_id="descriptor-key",
        signer=make_hmac_sha256_signer({"descriptor-key": "descriptor-secret"}),
        base_dir=tmp_path,
    )
    count = validate_instance_against_schema(manifest, load_publication_descriptor_index_manifest_schema())
    assert count == 1

    manifest_path = tmp_path / "publication_descriptor_index_manifest.json"
    write_json(manifest_path, manifest)
    summary = verify_signed_publication_descriptor_index_manifest(
        manifest_path,
        verifier=make_hmac_sha256_verifier({"descriptor-key": "descriptor-secret"}),
    )
    assert summary["signature_scheme"] == "hmac-sha256"
    assert summary["signature_key_id"] == "descriptor-key"
    assert summary["publication_descriptor_index_path"] == "descriptor_index.json"
    assert summary["artifact_count"] == index["artifact_count"]


def test_cli_bootstrap_publication_descriptor_index_publication(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)
    output_dir = tmp_path / "publication_descriptor_index_publication"

    exit_code = main(
        [
            "bootstrap-publication-descriptor-index-publication",
            "--discover-under",
            str(network_dir),
            "--output-dir",
            str(output_dir),
            "--channel",
            "network",
            "--label",
            "SATROOT Descriptor Publication",
            "--published-at",
            "2026-07-07T02:00:00Z",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "descriptor-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT publication descriptor index to" in captured.out

    index = json.loads((output_dir / "publication_descriptor_index.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "publication_descriptor_index_manifest.json").read_text(encoding="utf-8"))
    secrets = json.loads((output_dir / "publication_descriptor_index_secrets.json").read_text(encoding="utf-8"))

    assert index["artifact_count"] == 12
    assert index["index"]["label"] == "SATROOT Descriptor Publication"
    assert manifest["signature_key_id"] == "descriptor-key"

    verified = verify_signed_publication_descriptor_index_manifest(
        output_dir / "publication_descriptor_index_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert verified["artifact_count"] == 12
    assert verified["index"] == index["index"]


def test_cli_bootstrap_publication_descriptor_index_publication_with_preset_json_and_cli_overrides(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)
    preset_path = tmp_path / "publication_descriptor_index_preset.json"
    write_json(
        preset_path,
        {
            "type": "SATROOT-PUBLICATION-DESCRIPTOR-INDEX-PRESET",
            "version": "0.1",
            "discover_under": [str(Path(network_dir).relative_to(tmp_path))],
            "index": {
                "channel": "network",
                "label": "SATROOT Preset Descriptor Index",
                "published_at": "2026-07-08T02:30:00Z",
            },
        },
    )
    output_dir = tmp_path / "publication_descriptor_index_publication_preset"

    exit_code = main(
        [
            "bootstrap-publication-descriptor-index-publication",
            "--preset-json",
            str(preset_path),
            "--output-dir",
            str(output_dir),
            "--label",
            "SATROOT Descriptor Index Override",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "descriptor-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT publication descriptor index to" in captured.out

    index = json.loads((output_dir / "publication_descriptor_index.json").read_text(encoding="utf-8"))
    assert index["artifact_count"] == 12
    assert index["index"]["channel"] == "network"
    assert index["index"]["label"] == "SATROOT Descriptor Index Override"
    assert index["index"]["published_at"] == "2026-07-08T02:30:00Z"


def test_build_and_verify_signed_publication_metadata_manifest_hmac(tmp_path):
    release_dir, _ = make_demo_release_dirs(tmp_path)
    report_path = tmp_path / "publication_report.md"
    descriptor_path = tmp_path / "publication_descriptor.json"

    assert main(["render-publication-report", release_dir, "--output", str(report_path)]) == 0
    assert main(["export-publication-descriptor", release_dir, "--output", str(descriptor_path)]) == 0

    manifest = build_signed_publication_metadata_manifest(
        report_path,
        descriptor_path,
        signature_scheme="hmac-sha256",
        key_id="metadata-key",
        signer=make_hmac_sha256_signer({"metadata-key": "metadata-secret"}),
        base_dir=tmp_path,
    )
    count = validate_instance_against_schema(manifest, load_publication_metadata_manifest_schema())
    assert count == 1

    manifest_path = tmp_path / "publication_metadata_manifest.json"
    write_json(manifest_path, manifest)
    summary = verify_signed_publication_metadata_manifest(
        manifest_path,
        verifier=make_hmac_sha256_verifier({"metadata-key": "metadata-secret"}),
    )
    assert summary["signature_scheme"] == "hmac-sha256"
    assert summary["signature_key_id"] == "metadata-key"
    assert summary["artifact_kind"] == "release"
    assert summary["publication_report_path"] == "publication_report.md"
    assert summary["publication_descriptor_path"] == "publication_descriptor.json"


def test_cli_bootstrap_publication_metadata_bundle(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)
    output_dir = tmp_path / "publication_metadata_bundle"

    exit_code = main(
        [
            "bootstrap-publication-metadata-bundle",
            str(network_dir),
            "--output-dir",
            str(output_dir),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "metadata-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT publication metadata bundle to" in captured.out

    descriptor = json.loads((output_dir / "publication_descriptor.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "publication_metadata_manifest.json").read_text(encoding="utf-8"))
    secrets = json.loads((output_dir / "publication_metadata_secrets.json").read_text(encoding="utf-8"))

    assert (output_dir / "publication_report.md").is_file()
    assert descriptor["artifact_kind"] == "publication-network"
    assert manifest["signature_key_id"] == "metadata-key"

    verified = verify_signed_publication_metadata_manifest(
        output_dir / "publication_metadata_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert verified["artifact_kind"] == "publication-network"
    assert verified["publication_report_path"] == "publication_report.md"


def test_cli_validate_and_verify_publication_metadata_manifest(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)
    output_dir = tmp_path / "publication_metadata_bundle"

    assert main(
        [
            "bootstrap-publication-metadata-bundle",
            str(network_dir),
            "--output-dir",
            str(output_dir),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "metadata-key",
        ]
    ) == 0
    capsys.readouterr()

    manifest_path = output_dir / "publication_metadata_manifest.json"
    secrets_path = output_dir / "publication_metadata_secrets.json"

    exit_code = main(["validate-publication-metadata-manifest", str(manifest_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "valid SATROOT publication metadata manifest: 1 record(s)" in captured.out

    exit_code = main(["verify-publication-metadata-manifest", str(manifest_path), "--secrets-json", str(secrets_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"signature_scheme":"hmac-sha256"' in captured.out
    assert '"signature_key_id":"metadata-key"' in captured.out
    assert '"publication_report_path":"publication_report.md"' in captured.out


def test_cli_build_publication_metadata_catalog_recursive(tmp_path):
    _release_bundle_dir, _network_bundle_dir = make_publication_metadata_bundle_dirs(tmp_path)
    catalog_path = tmp_path / "publication_metadata_catalog.json"

    assert main(
        [
            "build-publication-metadata-catalog",
            "--discover-under",
            str(tmp_path),
            "--channel",
            "network",
            "--label",
            "SATROOT Metadata Catalog",
            "--published-at",
            "2026-07-08T03:00:00Z",
            "--output",
            str(catalog_path),
        ]
    ) == 0

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert catalog["bundle_count"] == 2
    assert catalog["artifact_kind_counts"]["release"] == 1
    assert catalog["artifact_kind_counts"]["publication-network"] == 1
    assert catalog["index"]["label"] == "SATROOT Metadata Catalog"


def test_validate_publication_metadata_catalog_schema_accepts_generated_catalog(tmp_path):
    release_bundle_dir, network_bundle_dir = make_publication_metadata_bundle_dirs(tmp_path)
    catalog = build_publication_metadata_catalog([release_bundle_dir, network_bundle_dir], base_dir=tmp_path)

    count = validate_instance_against_schema(catalog, load_publication_metadata_catalog_schema())
    assert count == 1
    validate_publication_metadata_catalog_consistency(catalog)


def test_build_and_verify_signed_publication_metadata_catalog_manifest_hmac(tmp_path):
    release_bundle_dir, network_bundle_dir = make_publication_metadata_bundle_dirs(tmp_path)
    catalog = build_publication_metadata_catalog(
        [release_bundle_dir, network_bundle_dir],
        base_dir=tmp_path,
        catalog_metadata={"label": "SATROOT Metadata Catalog"},
    )
    catalog_path = tmp_path / "publication_metadata_catalog.json"
    write_json(catalog_path, catalog)

    manifest = build_signed_publication_metadata_catalog_manifest(
        catalog_path,
        signature_scheme="hmac-sha256",
        key_id="catalog-key",
        signer=make_hmac_sha256_signer({"catalog-key": "catalog-secret"}),
        base_dir=tmp_path,
    )
    count = validate_instance_against_schema(manifest, load_publication_metadata_catalog_manifest_schema())
    assert count == 1

    manifest_path = tmp_path / "publication_metadata_catalog_manifest.json"
    write_json(manifest_path, manifest)
    summary = verify_signed_publication_metadata_catalog_manifest(
        manifest_path,
        verifier=make_hmac_sha256_verifier({"catalog-key": "catalog-secret"}),
    )
    assert summary["signature_scheme"] == "hmac-sha256"
    assert summary["signature_key_id"] == "catalog-key"
    assert summary["publication_metadata_catalog_path"] == "publication_metadata_catalog.json"
    assert summary["bundle_count"] == 2


def test_cli_bootstrap_publication_metadata_catalog_publication(tmp_path, capsys):
    _release_bundle_dir, _network_bundle_dir = make_publication_metadata_bundle_dirs(tmp_path)
    output_dir = tmp_path / "publication_metadata_catalog_publication"

    exit_code = main(
        [
            "bootstrap-publication-metadata-catalog-publication",
            "--discover-under",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--channel",
            "network",
            "--label",
            "SATROOT Metadata Catalog Publication",
            "--published-at",
            "2026-07-08T04:00:00Z",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "catalog-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT publication metadata catalog to" in captured.out

    catalog = json.loads((output_dir / "publication_metadata_catalog.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "publication_metadata_catalog_manifest.json").read_text(encoding="utf-8"))
    secrets = json.loads((output_dir / "publication_metadata_catalog_secrets.json").read_text(encoding="utf-8"))

    assert catalog["bundle_count"] == 2
    assert catalog["index"]["label"] == "SATROOT Metadata Catalog Publication"
    assert manifest["signature_key_id"] == "catalog-key"

    verified = verify_signed_publication_metadata_catalog_manifest(
        output_dir / "publication_metadata_catalog_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert verified["bundle_count"] == 2
    assert verified["index"] == catalog["index"]


def test_cli_bootstrap_publication_metadata_catalog_publication_with_preset_json_and_cli_overrides(tmp_path, capsys):
    _release_bundle_dir, _network_bundle_dir = make_publication_metadata_bundle_dirs(tmp_path)
    preset_path = tmp_path / "publication_metadata_catalog_preset.json"
    write_json(
        preset_path,
        {
            "type": "SATROOT-PUBLICATION-METADATA-CATALOG-PRESET",
            "version": "0.1",
            "discover_under": ["."],
            "catalog": {
                "channel": "network",
                "label": "SATROOT Preset Metadata Catalog",
                "published_at": "2026-07-08T05:00:00Z",
            },
        },
    )
    output_dir = tmp_path / "publication_metadata_catalog_publication_preset"

    exit_code = main(
        [
            "bootstrap-publication-metadata-catalog-publication",
            "--preset-json",
            str(preset_path),
            "--output-dir",
            str(output_dir),
            "--label",
            "SATROOT Metadata Catalog Override",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "catalog-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT publication metadata catalog to" in captured.out

    catalog = json.loads((output_dir / "publication_metadata_catalog.json").read_text(encoding="utf-8"))
    assert catalog["bundle_count"] == 2
    assert catalog["index"]["channel"] == "network"
    assert catalog["index"]["label"] == "SATROOT Metadata Catalog Override"
    assert catalog["index"]["published_at"] == "2026-07-08T05:00:00Z"


def test_cli_validate_and_verify_publication_metadata_catalog_manifest(tmp_path, capsys):
    _release_bundle_dir, _network_bundle_dir = make_publication_metadata_bundle_dirs(tmp_path)
    output_dir = tmp_path / "publication_metadata_catalog_publication"

    assert main(
        [
            "bootstrap-publication-metadata-catalog-publication",
            "--discover-under",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "catalog-key",
        ]
    ) == 0
    capsys.readouterr()

    catalog_path = output_dir / "publication_metadata_catalog.json"
    manifest_path = output_dir / "publication_metadata_catalog_manifest.json"
    secrets_path = output_dir / "publication_metadata_catalog_secrets.json"

    exit_code = main(["validate-publication-metadata-catalog", str(catalog_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "valid SATROOT publication metadata catalog: 1 record(s)" in captured.out

    exit_code = main(["validate-publication-metadata-catalog-manifest", str(manifest_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "valid SATROOT publication metadata catalog manifest: 1 record(s)" in captured.out

    exit_code = main(["verify-publication-metadata-catalog-manifest", str(manifest_path), "--secrets-json", str(secrets_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"signature_scheme":"hmac-sha256"' in captured.out
    assert '"signature_key_id":"catalog-key"' in captured.out
    assert '"publication_metadata_catalog_path":"publication_metadata_catalog.json"' in captured.out


def test_validate_publication_registry_schema_accepts_generated_registry(tmp_path):
    release_catalog_index_dir, descriptor_index_dir, metadata_catalog_dir = make_publication_registry_component_dirs(tmp_path)
    registry = build_publication_registry(
        release_catalog_index_dir=release_catalog_index_dir,
        publication_descriptor_index_dir=descriptor_index_dir,
        publication_metadata_catalog_dir=metadata_catalog_dir,
        base_dir=tmp_path,
    )

    count = validate_instance_against_schema(registry, load_publication_registry_schema())
    assert count == 1
    validate_publication_registry_consistency(registry)


def test_build_and_verify_signed_publication_registry_manifest_hmac(tmp_path):
    release_catalog_index_dir, descriptor_index_dir, metadata_catalog_dir = make_publication_registry_component_dirs(tmp_path)
    registry = build_publication_registry(
        release_catalog_index_dir=release_catalog_index_dir,
        publication_descriptor_index_dir=descriptor_index_dir,
        publication_metadata_catalog_dir=metadata_catalog_dir,
        base_dir=tmp_path,
        registry_metadata={"label": "SATROOT Publication Registry"},
    )
    registry_path = tmp_path / "publication_registry.json"
    write_json(registry_path, registry)

    manifest = build_signed_publication_registry_manifest(
        registry_path,
        signature_scheme="hmac-sha256",
        key_id="registry-key",
        signer=make_hmac_sha256_signer({"registry-key": "registry-secret"}),
        base_dir=tmp_path,
    )
    count = validate_instance_against_schema(manifest, load_publication_registry_manifest_schema())
    assert count == 1

    manifest_path = tmp_path / "publication_registry_manifest.json"
    write_json(manifest_path, manifest)
    summary = verify_signed_publication_registry_manifest(
        manifest_path,
        verifier=make_hmac_sha256_verifier({"registry-key": "registry-secret"}),
    )
    assert summary["signature_scheme"] == "hmac-sha256"
    assert summary["signature_key_id"] == "registry-key"
    assert summary["publication_registry_path"] == "publication_registry.json"
    assert summary["component_count"] == 3


def test_cli_bootstrap_publication_registry_publication(tmp_path, capsys):
    release_catalog_index_dir, descriptor_index_dir, metadata_catalog_dir = make_publication_registry_component_dirs(tmp_path)
    output_dir = tmp_path / "publication_registry_publication"

    exit_code = main(
        [
            "bootstrap-publication-registry-publication",
            "--release-catalog-index-dir",
            str(release_catalog_index_dir),
            "--publication-descriptor-index-dir",
            str(descriptor_index_dir),
            "--publication-metadata-catalog-dir",
            str(metadata_catalog_dir),
            "--output-dir",
            str(output_dir),
            "--channel",
            "network",
            "--label",
            "SATROOT Publication Registry",
            "--published-at",
            "2026-07-08T05:00:00Z",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "registry-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT publication registry to" in captured.out

    registry = json.loads((output_dir / "publication_registry.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "publication_registry_manifest.json").read_text(encoding="utf-8"))
    secrets = json.loads((output_dir / "publication_registry_secrets.json").read_text(encoding="utf-8"))

    assert registry["component_count"] == 3
    assert registry["index"]["label"] == "SATROOT Publication Registry"
    assert manifest["signature_key_id"] == "registry-key"

    verified = verify_signed_publication_registry_manifest(
        output_dir / "publication_registry_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert verified["component_count"] == 3
    assert verified["index"] == registry["index"]


def test_cli_bootstrap_publication_registry_publication_with_preset_json_and_cli_overrides(tmp_path, capsys):
    release_catalog_index_dir, descriptor_index_dir, metadata_catalog_dir = make_publication_registry_component_dirs(tmp_path)
    preset_path = tmp_path / "publication_registry_preset.json"
    write_json(
        preset_path,
        {
            "type": "SATROOT-PUBLICATION-REGISTRY-PRESET",
            "version": "0.1",
            "release_catalog_index_dir": str(Path(release_catalog_index_dir).relative_to(tmp_path)),
            "publication_descriptor_index_dir": str(Path(descriptor_index_dir).relative_to(tmp_path)),
            "publication_metadata_catalog_dir": str(Path(metadata_catalog_dir).relative_to(tmp_path)),
            "registry": {
                "channel": "mesh",
                "label": "Preset Publication Registry",
                "published_at": "2026-07-08T06:00:00Z",
            },
        },
    )
    output_dir = tmp_path / "publication_registry_preset_publication"

    exit_code = main(
        [
            "bootstrap-publication-registry-publication",
            "--preset-json",
            str(preset_path),
            "--output-dir",
            str(output_dir),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "registry-key",
            "--label",
            "CLI Publication Registry Override",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT publication registry to" in captured.out

    registry = json.loads((output_dir / "publication_registry.json").read_text(encoding="utf-8"))
    assert registry["index"]["channel"] == "mesh"
    assert registry["index"]["label"] == "CLI Publication Registry Override"
    assert registry["index"]["published_at"] == "2026-07-08T06:00:00Z"


def test_cli_validate_and_verify_publication_registry_manifest(tmp_path, capsys):
    release_catalog_index_dir, descriptor_index_dir, metadata_catalog_dir = make_publication_registry_component_dirs(tmp_path)
    output_dir = tmp_path / "publication_registry_publication"

    assert main(
        [
            "bootstrap-publication-registry-publication",
            "--release-catalog-index-dir",
            str(release_catalog_index_dir),
            "--publication-descriptor-index-dir",
            str(descriptor_index_dir),
            "--publication-metadata-catalog-dir",
            str(metadata_catalog_dir),
            "--output-dir",
            str(output_dir),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "registry-key",
        ]
    ) == 0
    capsys.readouterr()

    registry_path = output_dir / "publication_registry.json"
    manifest_path = output_dir / "publication_registry_manifest.json"
    secrets_path = output_dir / "publication_registry_secrets.json"

    exit_code = main(["validate-publication-registry", str(registry_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "valid SATROOT publication registry: 1 record(s)" in captured.out

    exit_code = main(["validate-publication-registry-manifest", str(manifest_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "valid SATROOT publication registry manifest: 1 record(s)" in captured.out

    exit_code = main(["verify-publication-registry-manifest", str(manifest_path), "--secrets-json", str(secrets_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"signature_scheme":"hmac-sha256"' in captured.out
    assert '"signature_key_id":"registry-key"' in captured.out
    assert '"publication_registry_path":"publication_registry.json"' in captured.out


def test_lint_signed_ledger_bundle_reports_structural_findings(tmp_path):
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
    manifest["files"]["public_keys"] = "public_keys.json"
    manifest["files"]["annotated_signed_events"] = "signed_events.json"
    manifest["file_hashes"]["private_keys"] = "sha256:" + ("1" * 64)
    write_json(tmp_path / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(tmp_path / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(tmp_path / "signed_events.json", bundle["signed_events"])
    write_json(tmp_path / "bundle_manifest.json", manifest)
    write_json(tmp_path / "unexpected.txt", {"note": "extra"})

    report = lint_signed_ledger_bundle(tmp_path)
    assert report["ok"] is False
    assert report["missing_files"] == ["public_keys"]
    assert report["unhashed_declared_files"] == ["public_keys"]
    assert report["dangling_hash_entries"] == ["private_keys"]
    assert report["duplicate_declared_paths"] == ["signed_events.json"]
    assert report["extra_files"] == ["unexpected.txt"]


def test_validate_instance_against_bundle_manifest_schema_accepts_public_only_ed25519_manifest():
    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            bootstrap_signed_ledger_bundle(load_events(), scheme="ed25519")
        return

    bundle = bootstrap_signed_ledger_bundle(load_events(), scheme="ed25519")
    manifest = build_signed_ledger_bundle_manifest(
        bundle,
        output_files={
            "signer_key_map": "signer_key_map.json",
            "public_keys": "public_keys.json",
            "signed_events": "signed_events.json",
            "annotated_signed_events": "annotated_signed_events.json",
            "bundle_manifest": "bundle_manifest.json",
        },
        output_file_hashes={
            "signer_key_map": rendered_json_sha256(bundle["material"]["signer_key_map"]),
            "public_keys": rendered_json_sha256(bundle["material"]["public_keys"]),
            "signed_events": rendered_json_sha256(bundle["signed_events"]),
            "annotated_signed_events": rendered_json_sha256(bundle["annotated_events"]),
        },
    )
    assert manifest["verification_material_scope"] == "public-only"
    count = validate_instance_against_schema(manifest, load_bundle_manifest_schema())
    assert count == 1


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


def test_verify_signed_ledger_bundle_rejects_snapshot_mismatch(tmp_path):
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
    manifest["final_state_snapshot"]["balances"]["issuer"] = "600000001"
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


def test_cli_init_genesis_profile_output(tmp_path):
    output_path = tmp_path / "genesis.json"

    exit_code = main(
        [
            "init-genesis",
            "--symbol",
            "USDCLI1",
            "--name",
            "SATROOT CLI Dollar",
            "--profile",
            "SATROOT-STABLE-1",
            "--profile-field",
            "reference_unit=EUR",
            "--profile-field",
            "intended_use=cli-reference-ledger",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    genesis = json.loads(output_path.read_text(encoding="utf-8"))
    state = replay([genesis])
    assert genesis["profile"] == "SATROOT-STABLE-1"
    assert genesis["profile_mode"] == "reference-only"
    assert genesis["reference_unit"] == "EUR"
    assert state.symbol == "USDCLI1"
    assert state.genesis_metadata["intended_use"] == "cli-reference-ledger"


def test_cli_init_event_from_ledger(tmp_path):
    events_path = tmp_path / "events.json"
    output_path = tmp_path / "event.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    exit_code = main(
        [
            "init-event",
            "--action",
            "transfer",
            "--events-json",
            str(events_path),
            "--signer",
            "bob",
            "--from",
            "bob",
            "--to",
            "issuer",
            "--amount",
            "1000",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    event = json.loads(output_path.read_text(encoding="utf-8"))
    assert event["sequence"] == 4
    assert event["prev_event_id"] == event_id(load_events()[-1])
    assert event["action"] == "transfer"


def test_cli_init_event_manual_rotate_authority(tmp_path):
    output_path = tmp_path / "event.json"

    exit_code = main(
        [
            "init-event",
            "--action",
            "rotate-authority",
            "--root-id",
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff:0",
            "--sequence",
            "1",
            "--prev-event-id",
            "sha256:" + ("1" * 64),
            "--signer",
            "issuer",
            "--new-mint-authority",
            "issuer_v2",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    event = json.loads(output_path.read_text(encoding="utf-8"))
    assert event["action"] == "rotate-authority"
    assert event["new_mint_authority"] == "issuer_v2"
    assert event["sequence"] == 1


def test_cli_append_event_hmac(tmp_path):
    events_path = tmp_path / "events.json"
    bootstrap_dir = tmp_path / "bootstrap"
    signed_path = tmp_path / "signed.json"
    appended_path = tmp_path / "appended.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    assert main(["bootstrap-hmac-workflow", str(events_path), "--output-dir", str(bootstrap_dir)]) == 0
    assert (
        main(
            [
                "sign-ledger",
                str(events_path),
                "--scheme",
                "hmac-sha256",
                "--signer-key-map-json",
                str(bootstrap_dir / "signer_key_map.json"),
                "--secrets-json",
                str(bootstrap_dir / "secrets.json"),
                "--output",
                str(signed_path),
            ]
        )
        == 0
    )

    exit_code = main(
        [
            "append-event",
            str(signed_path),
            "--action",
            "transfer",
            "--signer",
            "bob",
            "--from",
            "bob",
            "--to",
            "issuer",
            "--amount",
            "1000",
            "--scheme",
            "hmac-sha256",
            "--signer-key-map-json",
            str(bootstrap_dir / "signer_key_map.json"),
            "--secrets-json",
            str(bootstrap_dir / "secrets.json"),
            "--include-state-hash",
            "--output",
            str(appended_path),
        ]
    )
    assert exit_code == 0

    shared_secrets = json.loads((bootstrap_dir / "secrets.json").read_text(encoding="utf-8"))
    appended = json.loads(appended_path.read_text(encoding="utf-8"))
    assert appended[-1]["signature_scheme"] == "hmac-sha256"
    assert appended[-1]["signature_key_id"] == "bob-key"
    assert appended[-1]["state_hash"].startswith("sha256:")
    state = replay(appended, verifier=make_hmac_sha256_verifier(shared_secrets))
    assert state.balances["bob"] == 98_999_000


def test_cli_consume_machine_credit_demo(tmp_path):
    events_path = tmp_path / "machine_events.json"
    output_path = tmp_path / "consumed.json"
    events_path.write_text(json.dumps(load_events("events_apicredit1.json")), encoding="utf-8")

    exit_code = main(
        [
            "consume-machine-credit",
            str(events_path),
            "--signer",
            "worker_node",
            "--amount",
            "1000",
            "--include-state-hash",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    appended = json.loads(output_path.read_text(encoding="utf-8"))
    assert appended[-1]["action"] == "burn"
    assert appended[-1]["from"] == "worker_node"
    assert appended[-1]["state_hash"].startswith("sha256:")
    state = replay(appended)
    assert state.balances["worker_node"] == 999_000
    assert state.supply == 99_799_000


def test_cli_consume_machine_credit_hmac(tmp_path):
    events_path = tmp_path / "machine_events.json"
    bootstrap_dir = tmp_path / "bootstrap"
    signed_path = tmp_path / "signed.json"
    output_path = tmp_path / "consumed.json"
    events_path.write_text(json.dumps(load_events("events_apicredit1.json")), encoding="utf-8")

    assert main(["bootstrap-hmac-workflow", str(events_path), "--output-dir", str(bootstrap_dir)]) == 0
    assert (
        main(
            [
                "sign-ledger",
                str(events_path),
                "--scheme",
                "hmac-sha256",
                "--signer-key-map-json",
                str(bootstrap_dir / "signer_key_map.json"),
                "--secrets-json",
                str(bootstrap_dir / "secrets.json"),
                "--output",
                str(signed_path),
            ]
        )
        == 0
    )

    exit_code = main(
        [
            "consume-machine-credit",
            str(signed_path),
            "--signer",
            "worker_node",
            "--amount",
            "1000",
            "--scheme",
            "hmac-sha256",
            "--signer-key-map-json",
            str(bootstrap_dir / "signer_key_map.json"),
            "--secrets-json",
            str(bootstrap_dir / "secrets.json"),
            "--include-state-hash",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    shared_secrets = json.loads((bootstrap_dir / "secrets.json").read_text(encoding="utf-8"))
    appended = json.loads(output_path.read_text(encoding="utf-8"))
    assert appended[-1]["signature_scheme"] == "hmac-sha256"
    assert appended[-1]["signature_key_id"] == "worker_node-key"
    state = replay(appended, verifier=make_hmac_sha256_verifier(shared_secrets))
    assert state.balances["worker_node"] == 999_000
    assert state.supply == 99_799_000


def test_cli_archive_singleton_object_demo(tmp_path):
    events_path = tmp_path / "receipt_events.json"
    output_path = tmp_path / "archived.json"
    events = load_events("events_receipt1.json")[:2]
    events_path.write_text(json.dumps(events), encoding="utf-8")

    exit_code = main(
        [
            "archive-singleton-object",
            str(events_path),
            "--signer",
            "buyer",
            "--include-state-hash",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    appended = json.loads(output_path.read_text(encoding="utf-8"))
    assert appended[-1]["action"] == "transfer"
    assert appended[-1]["to"] == "archive"
    assert appended[-1]["state_hash"].startswith("sha256:")
    state = replay(appended)
    assert state.balances["archive"] == 1
    assert state.balances["buyer"] == 0


def test_cli_archive_singleton_object_hmac(tmp_path):
    events_path = tmp_path / "license_events.json"
    bootstrap_dir = tmp_path / "bootstrap"
    signed_path = tmp_path / "signed.json"
    output_path = tmp_path / "archived.json"
    signer_map_path = bootstrap_dir / "signer_key_map.json"
    secrets_path = bootstrap_dir / "secrets.json"
    events = load_events("events_license1.json")[:2]
    events_path.write_text(json.dumps(events), encoding="utf-8")
    bootstrap_dir.mkdir()
    write_json(signer_map_path, {"issuer": "issuer-key", "customer": "customer-key"})
    write_json(secrets_path, {"issuer-key": "issuer-secret", "customer-key": "customer-secret"})
    assert (
        main(
            [
                "sign-ledger",
                str(events_path),
                "--scheme",
                "hmac-sha256",
                "--signer-key-map-json",
                str(signer_map_path),
                "--secrets-json",
                str(secrets_path),
                "--output",
                str(signed_path),
            ]
        )
        == 0
    )

    exit_code = main(
        [
            "archive-singleton-object",
            str(signed_path),
            "--signer",
            "customer",
            "--scheme",
            "hmac-sha256",
            "--signer-key-map-json",
            str(signer_map_path),
            "--secrets-json",
            str(secrets_path),
            "--include-state-hash",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    shared_secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
    appended = json.loads(output_path.read_text(encoding="utf-8"))
    assert appended[-1]["signature_scheme"] == "hmac-sha256"
    assert appended[-1]["signature_key_id"] == "customer-key"
    state = replay(appended, verifier=make_hmac_sha256_verifier(shared_secrets))
    assert state.balances["archive"] == 1
    assert state.balances["customer"] == 0


def test_cli_transfer_singleton_object_demo(tmp_path):
    events_path = tmp_path / "identity_events.json"
    output_path = tmp_path / "transferred.json"
    events = load_events("events_identity1.json")[:2]
    events_path.write_text(json.dumps(events), encoding="utf-8")

    exit_code = main(
        [
            "transfer-singleton-object",
            str(events_path),
            "--signer",
            "node_alpha",
            "--to",
            "rotated_controller",
            "--include-state-hash",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    appended = json.loads(output_path.read_text(encoding="utf-8"))
    assert appended[-1]["action"] == "transfer"
    assert appended[-1]["from"] == "node_alpha"
    assert appended[-1]["to"] == "rotated_controller"
    assert appended[-1]["state_hash"].startswith("sha256:")
    state = replay(appended)
    assert state.balances["node_alpha"] == 0
    assert state.balances["rotated_controller"] == 1


def test_cli_transfer_singleton_object_hmac(tmp_path):
    events_path = tmp_path / "license_events.json"
    bootstrap_dir = tmp_path / "bootstrap"
    signed_path = tmp_path / "signed.json"
    output_path = tmp_path / "transferred.json"
    signer_map_path = bootstrap_dir / "signer_key_map.json"
    secrets_path = bootstrap_dir / "secrets.json"
    events = load_events("events_license1.json")[:2]
    events_path.write_text(json.dumps(events), encoding="utf-8")
    bootstrap_dir.mkdir()
    write_json(signer_map_path, {"issuer": "issuer-key", "customer": "customer-key"})
    write_json(secrets_path, {"issuer-key": "issuer-secret", "customer-key": "customer-secret"})
    assert (
        main(
            [
                "sign-ledger",
                str(events_path),
                "--scheme",
                "hmac-sha256",
                "--signer-key-map-json",
                str(signer_map_path),
                "--secrets-json",
                str(secrets_path),
                "--output",
                str(signed_path),
            ]
        )
        == 0
    )

    exit_code = main(
        [
            "transfer-singleton-object",
            str(signed_path),
            "--signer",
            "customer",
            "--to",
            "customer-v2",
            "--scheme",
            "hmac-sha256",
            "--signer-key-map-json",
            str(signer_map_path),
            "--secrets-json",
            str(secrets_path),
            "--include-state-hash",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    shared_secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
    appended = json.loads(output_path.read_text(encoding="utf-8"))
    assert appended[-1]["signature_scheme"] == "hmac-sha256"
    assert appended[-1]["signature_key_id"] == "customer-key"
    state = replay(appended, verifier=make_hmac_sha256_verifier(shared_secrets))
    assert state.balances["customer"] == 0
    assert state.balances["customer-v2"] == 1


def test_cli_retire_singleton_object_demo(tmp_path):
    events_path = tmp_path / "archived_receipt_events.json"
    output_path = tmp_path / "retired.json"
    events = load_events("events_receipt1.json")[:3]
    events_path.write_text(json.dumps(events), encoding="utf-8")

    exit_code = main(
        [
            "retire-singleton-object",
            str(events_path),
            "--signer",
            "archive",
            "--include-state-hash",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    appended = json.loads(output_path.read_text(encoding="utf-8"))
    assert appended[-1]["action"] == "burn"
    assert appended[-1]["from"] == "archive"
    assert appended[-1]["state_hash"].startswith("sha256:")
    state = replay(appended)
    assert state.supply == 0
    assert state.balances["archive"] == 0


def test_cli_retire_singleton_object_hmac(tmp_path):
    events_path = tmp_path / "archived_license_events.json"
    bootstrap_dir = tmp_path / "bootstrap"
    signed_path = tmp_path / "signed.json"
    output_path = tmp_path / "retired.json"
    signer_map_path = bootstrap_dir / "signer_key_map.json"
    secrets_path = bootstrap_dir / "secrets.json"
    events = load_events("events_license1.json")[:3]
    events_path.write_text(json.dumps(events), encoding="utf-8")
    bootstrap_dir.mkdir()
    write_json(signer_map_path, {"issuer": "issuer-key", "customer": "customer-key", "archive": "archive-key"})
    write_json(
        secrets_path,
        {
            "issuer-key": "issuer-secret",
            "customer-key": "customer-secret",
            "archive-key": "archive-secret",
        },
    )
    assert (
        main(
            [
                "sign-ledger",
                str(events_path),
                "--scheme",
                "hmac-sha256",
                "--signer-key-map-json",
                str(signer_map_path),
                "--secrets-json",
                str(secrets_path),
                "--output",
                str(signed_path),
            ]
        )
        == 0
    )

    exit_code = main(
        [
            "retire-singleton-object",
            str(signed_path),
            "--signer",
            "archive",
            "--scheme",
            "hmac-sha256",
            "--signer-key-map-json",
            str(signer_map_path),
            "--secrets-json",
            str(secrets_path),
            "--include-state-hash",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0

    shared_secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
    appended = json.loads(output_path.read_text(encoding="utf-8"))
    assert appended[-1]["signature_scheme"] == "hmac-sha256"
    assert appended[-1]["signature_key_id"] == "archive-key"
    state = replay(appended, verifier=make_hmac_sha256_verifier(shared_secrets))
    assert state.supply == 0
    assert state.balances["archive"] == 0


def test_cli_bootstrap_genesis_bundle_hmac(tmp_path, capsys):
    output_dir = tmp_path / "bundle"

    exit_code = main(
        [
            "bootstrap-genesis-bundle",
            "--symbol",
            "BUNDLE1",
            "--name",
            "SATROOT Bundle Asset",
            "--scheme",
            "hmac-sha256",
            "--profile",
            "SATROOT-MACHINE-1",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote scaffolded SATROOT-1 hmac-sha256 genesis bundle to" in captured.out
    genesis = json.loads((output_dir / "genesis.json").read_text(encoding="utf-8"))
    signer_key_map = json.loads((output_dir / "signer_key_map.json").read_text(encoding="utf-8"))
    secrets = json.loads((output_dir / "secrets.json").read_text(encoding="utf-8"))
    signed_events = json.loads((output_dir / "signed_events.json").read_text(encoding="utf-8"))
    assert genesis["profile"] == "SATROOT-MACHINE-1"
    assert signer_key_map == {}
    assert secrets == {}
    assert len(signed_events) == 1

    summary = verify_signed_ledger_bundle(output_dir)
    assert summary["symbol"] == "BUNDLE1"
    assert summary["record_count"] == 1


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
    assert manifest["verification_material_scope"] == "shared-secret"
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


def test_cli_bootstrap_signed_ledger_ed25519_verifier_only(tmp_path):
    events_path = tmp_path / "events.json"
    output_dir = tmp_path / "bundle"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    if not ed25519_available():
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
                    "--verifier-only",
                ]
            )
        return

    exit_code = main(
        [
            "bootstrap-signed-ledger",
            str(events_path),
            "--scheme",
            "ed25519",
            "--output-dir",
            str(output_dir),
            "--verifier-only",
        ]
    )
    assert exit_code == 0
    assert not (output_dir / "private_keys.json").exists()
    assert (output_dir / "public_keys.json").exists()

    manifest = json.loads((output_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    assert manifest["verification_material_scope"] == "public-only"
    assert "private_keys" not in manifest["files"]
    assert "private_keys" not in manifest["file_hashes"]

    verify_exit_code = main(["verify-bundle", str(output_dir)])
    assert verify_exit_code == 0


def test_cli_bootstrap_signed_ledger_rejects_verifier_only_hmac(tmp_path):
    events_path = tmp_path / "events.json"
    output_dir = tmp_path / "bundle"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    with pytest.raises(SatRootError):
        main(
            [
                "bootstrap-signed-ledger",
                str(events_path),
                "--scheme",
                "hmac-sha256",
                "--output-dir",
                str(output_dir),
                "--verifier-only",
            ]
        )


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
    assert '"verification_material_scope":"shared-secret"' in captured.out
    assert '"symbol":"FLOOR1"' in captured.out
    assert '"annotated_verified":true' in captured.out


def test_cli_bundle_summary_reads_manifest_without_replay(tmp_path, capsys):
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
    write_json(tmp_path / "bundle_manifest.json", manifest)

    exit_code = main(["bundle-summary", str(tmp_path)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"scheme":"hmac-sha256"' in captured.out
    assert '"verification_material_scope":"shared-secret"' in captured.out
    assert '"annotated_output":true' in captured.out
    assert '"symbol":"FLOOR1"' in captured.out


def test_cli_bundle_lint_accepts_clean_bundle(tmp_path, capsys):
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

    lint_exit_code = main(["bundle-lint", str(output_dir)])
    assert lint_exit_code == 0

    captured = capsys.readouterr()
    assert '"ok":true' in captured.out
    assert '"missing_files":[]' in captured.out
    assert '"extra_files":[]' in captured.out


def test_cli_bundle_lint_reports_findings(tmp_path, capsys):
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
    manifest["files"]["public_keys"] = "public_keys.json"
    manifest["files"]["annotated_signed_events"] = "signed_events.json"
    manifest["file_hashes"]["private_keys"] = "sha256:" + ("1" * 64)
    write_json(tmp_path / "signer_key_map.json", bundle["material"]["signer_key_map"])
    write_json(tmp_path / "secrets.json", bundle["material"]["shared_secrets"])
    write_json(tmp_path / "signed_events.json", bundle["signed_events"])
    write_json(tmp_path / "bundle_manifest.json", manifest)
    (tmp_path / "unexpected.txt").write_text("extra", encoding="utf-8")

    lint_exit_code = main(["bundle-lint", str(tmp_path)])
    assert lint_exit_code == 1

    captured = capsys.readouterr()
    assert '"ok":false' in captured.out
    assert '"missing_files":["public_keys"]' in captured.out
    assert '"unhashed_declared_files":["public_keys"]' in captured.out
    assert '"dangling_hash_entries":["private_keys"]' in captured.out
    assert '"duplicate_declared_paths":["signed_events.json"]' in captured.out
    assert '"extra_files":["unexpected.txt"]' in captured.out


def test_cli_release_summary_reads_manifest_and_index(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    bundle_dir = tmp_path / "bundle"
    release_material_dir = tmp_path / "release_hmac"
    release_dir = tmp_path / "release"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    assert main(["bootstrap-signed-ledger", str(events_path), "--scheme", "hmac-sha256", "--output-dir", str(bundle_dir)]) == 0
    assert main(["bootstrap-release-hmac", "--key-id", "release-key", "--output-dir", str(release_material_dir)]) == 0
    assert main(
        [
            "publish-release",
            str(bundle_dir),
            "--output-dir",
            str(release_dir),
            "--channel",
            "stable",
            "--label",
            "SATROOT FLOOR1 Demo",
            "--published-at",
            "2026-06-28T20:00:00Z",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "release-key",
            "--secrets-json",
            str(release_material_dir / "release_secrets.json"),
        ]
    ) == 0
    capsys.readouterr()

    exit_code = main(["release-summary", str(release_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"signature_scheme":"hmac-sha256"' in captured.out
    assert '"signature_key_id":"release-key"' in captured.out
    assert '"bundle_count":1' in captured.out
    assert '"bundle_symbols":["FLOOR1"]' in captured.out


def test_cli_release_lint_accepts_clean_release(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    bundle_dir = tmp_path / "bundle"
    release_material_dir = tmp_path / "release_hmac"
    release_dir = tmp_path / "release"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    assert main(["bootstrap-signed-ledger", str(events_path), "--scheme", "hmac-sha256", "--output-dir", str(bundle_dir)]) == 0
    assert main(["bootstrap-release-hmac", "--key-id", "release-key", "--output-dir", str(release_material_dir)]) == 0
    assert main(
        [
            "publish-release",
            str(bundle_dir),
            "--output-dir",
            str(release_dir),
            "--channel",
            "stable",
            "--label",
            "SATROOT FLOOR1 Demo",
            "--published-at",
            "2026-06-28T20:30:00Z",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "release-key",
            "--secrets-json",
            str(release_material_dir / "release_secrets.json"),
        ]
    ) == 0
    capsys.readouterr()

    exit_code = main(["release-lint", str(release_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"ok":true' in captured.out
    assert '"bundle_index_hash_matches":true' in captured.out
    assert '"missing_bundle_manifests":[]' in captured.out


def test_cli_release_lint_reports_findings(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    bundle_dir = tmp_path / "bundle"
    release_material_dir = tmp_path / "release_hmac"
    release_dir = tmp_path / "release"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    assert main(["bootstrap-signed-ledger", str(events_path), "--scheme", "hmac-sha256", "--output-dir", str(bundle_dir)]) == 0
    assert main(["bootstrap-release-hmac", "--key-id", "release-key", "--output-dir", str(release_material_dir)]) == 0
    assert main(
        [
            "publish-release",
            str(bundle_dir),
            "--output-dir",
            str(release_dir),
            "--channel",
            "stable",
            "--label",
            "SATROOT FLOOR1 Demo",
            "--published-at",
            "2026-06-28T21:00:00Z",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "release-key",
            "--secrets-json",
            str(release_material_dir / "release_secrets.json"),
        ]
    ) == 0
    capsys.readouterr()

    bundle_index_path = release_dir / "bundle_index.json"
    bundle_index = json.loads(bundle_index_path.read_text(encoding="utf-8"))
    bundle_index["release"]["label"] = "Tampered Release Label"
    write_json(bundle_index_path, bundle_index)
    (bundle_dir / "bundle_manifest.json").unlink()

    exit_code = main(["release-lint", str(release_dir)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert '"ok":false' in captured.out
    assert '"bundle_index_hash_matches":false' in captured.out
    assert '"release_metadata_matches":false' in captured.out
    assert '"missing_bundle_manifests":["../bundle/bundle_manifest.json"]' in captured.out


def test_cli_release_catalog_summary_reads_manifest_and_catalog(tmp_path, capsys):
    catalog_dir = make_demo_release_catalog_dir(tmp_path)

    exit_code = main(["release-catalog-summary", str(catalog_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"signature_scheme":"hmac-sha256"' in captured.out
    assert '"signature_key_id":"catalog-key"' in captured.out
    assert '"release_count":2' in captured.out
    assert '"release_labels":["Machine Release Workspace","Stable Release Workspace"]' in captured.out


def test_cli_release_catalog_lint_accepts_clean_catalog(tmp_path, capsys):
    catalog_dir = make_demo_release_catalog_dir(tmp_path)

    exit_code = main(["release-catalog-lint", str(catalog_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"ok":true' in captured.out
    assert '"release_catalog_hash_matches":true' in captured.out
    assert '"missing_release_manifests":[]' in captured.out
    assert '"release_publication_metadata_mismatches":[]' in captured.out


def test_cli_release_catalog_lint_reports_findings(tmp_path, capsys):
    catalog_dir = make_demo_release_catalog_dir(tmp_path)

    catalog_path = catalog_dir / "release_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["catalog"]["label"] = "Tampered Catalog Label"
    write_json(catalog_path, catalog)
    first_release = Path(catalog_dir / catalog["releases"][0]["release_manifest_path"])
    first_release.unlink()

    exit_code = main(["release-catalog-lint", str(catalog_dir)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert '"ok":false' in captured.out
    assert '"release_catalog_hash_matches":false' in captured.out
    assert '"catalog_metadata_matches":false' in captured.out
    assert '"missing_release_manifests":[' in captured.out


def test_cli_release_catalog_index_summary_reads_manifest_and_index(tmp_path, capsys):
    index_dir = make_demo_release_catalog_index_dir(tmp_path)

    exit_code = main(["release-catalog-index-summary", str(index_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"signature_scheme":"hmac-sha256"' in captured.out
    assert '"signature_key_id":"index-key"' in captured.out
    assert '"release_catalog_count":2' in captured.out
    assert '"catalog_labels":["SATROOT Catalog Alpha","SATROOT Catalog Beta"]' in captured.out


def test_cli_release_catalog_index_lint_accepts_clean_index(tmp_path, capsys):
    index_dir = make_demo_release_catalog_index_dir(tmp_path)

    exit_code = main(["release-catalog-index-lint", str(index_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"ok":true' in captured.out
    assert '"release_catalog_index_hash_matches":true' in captured.out
    assert '"missing_release_catalog_manifests":[]' in captured.out
    assert '"release_catalog_publication_metadata_mismatches":[]' in captured.out


def test_cli_release_catalog_index_lint_reports_findings(tmp_path, capsys):
    index_dir = make_demo_release_catalog_index_dir(tmp_path)

    index_path = index_dir / "release_catalog_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["index"]["label"] = "Tampered Index Label"
    write_json(index_path, index)
    first_catalog_manifest = Path(index_dir / index["release_catalogs"][0]["release_catalog_manifest_path"])
    first_catalog_manifest.unlink()

    exit_code = main(["release-catalog-index-lint", str(index_dir)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert '"ok":false' in captured.out
    assert '"release_catalog_index_hash_matches":false' in captured.out
    assert '"index_metadata_matches":false' in captured.out
    assert '"missing_release_catalog_manifests":[' in captured.out


def test_cli_publication_descriptor_index_summary_reads_manifest_and_index(tmp_path, capsys):
    descriptor_index_dir = make_publication_descriptor_index_dir(tmp_path)

    exit_code = main(["publication-descriptor-index-summary", str(descriptor_index_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"signature_scheme":"hmac-sha256"' in captured.out
    assert '"signature_key_id":"descriptor-key"' in captured.out
    assert '"artifact_count":12' in captured.out
    assert '"artifact_kinds":["bundle","demo-catalog","publication-network","publication-stack","release","release-catalog","release-catalog-index"]' in captured.out


def test_cli_publication_descriptor_index_lint_accepts_clean_index(tmp_path, capsys):
    descriptor_index_dir = make_publication_descriptor_index_dir(tmp_path)

    exit_code = main(["publication-descriptor-index-lint", str(descriptor_index_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"ok":true' in captured.out
    assert '"publication_descriptor_index_hash_matches":true' in captured.out
    assert '"missing_artifact_paths":[]' in captured.out
    assert '"artifact_descriptor_mismatches":[]' in captured.out


def test_cli_publication_descriptor_index_lint_reports_findings(tmp_path, capsys):
    descriptor_index_dir = make_publication_descriptor_index_dir(tmp_path)

    index_path = descriptor_index_dir / "publication_descriptor_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["index"]["label"] = "Tampered Descriptor Index Label"
    index["artifacts"][0]["artifact_path"] = str(tmp_path / "missing_artifact")
    write_json(index_path, index)

    exit_code = main(["publication-descriptor-index-lint", str(descriptor_index_dir)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert '"ok":false' in captured.out
    assert '"publication_descriptor_index_hash_matches":false' in captured.out
    assert '"index_metadata_matches":false' in captured.out
    assert '"missing_artifact_paths":[' in captured.out


def test_cli_demo_catalog_summary_reads_summary_and_release(tmp_path, capsys):
    output_dir = make_demo_catalog_workspace_dir(tmp_path)

    exit_code = main(["demo-catalog-summary", str(output_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"bundle_count":2' in captured.out
    assert '"bundle_names":["machine","stable"]' in captured.out
    assert '"release_summary":' in captured.out


def test_cli_demo_catalog_lint_accepts_clean_workspace(tmp_path, capsys):
    output_dir = make_demo_catalog_workspace_dir(tmp_path)

    exit_code = main(["demo-catalog-lint", str(output_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"ok":true' in captured.out
    assert '"release_lint":' in captured.out
    assert '"bundle_summary_metadata_mismatches":[]' in captured.out


def test_cli_demo_catalog_lint_reports_findings(tmp_path, capsys):
    output_dir = make_demo_catalog_workspace_dir(tmp_path)

    summary_path = output_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["release_manifest_path"] = "tampered"
    write_json(summary_path, summary)
    (output_dir / "bundles" / "stable" / "bundle_manifest.json").unlink()

    exit_code = main(["demo-catalog-lint", str(output_dir)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert '"ok":false' in captured.out
    assert '"release_manifest_path_matches":false' in captured.out
    assert '"missing_bundle_manifests":["stable"]' in captured.out


def test_cli_publication_stack_summary_reads_summary_and_catalog(tmp_path, capsys):
    stack_dir = make_demo_publication_stack_dir(tmp_path)

    exit_code = main(["publication-stack-summary", str(stack_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"workspace_count":2' in captured.out
    assert '"workspace_names":["machine_catalog","stable_catalog"]' in captured.out
    assert '"release_catalog_summary":' in captured.out


def test_cli_publication_stack_lint_accepts_clean_stack(tmp_path, capsys):
    stack_dir = make_demo_publication_stack_dir(tmp_path)

    exit_code = main(["publication-stack-lint", str(stack_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"ok":true' in captured.out
    assert '"release_catalog_lint":' in captured.out
    assert '"workspace_summary_metadata_mismatches":[]' in captured.out
    assert '"workspace_lint_failures":[]' in captured.out


def test_cli_publication_stack_lint_reports_nested_workspace_failures(tmp_path, capsys):
    stack_dir = make_demo_publication_stack_dir(tmp_path)
    (
        stack_dir
        / "catalog_workspaces"
        / "stable_catalog"
        / "bundles"
        / "stable"
        / "bundle_manifest.json"
    ).unlink()

    exit_code = main(["publication-stack-lint", str(stack_dir)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert '"ok":false' in captured.out
    assert '"workspace_lint_failures":["stable_catalog"]' in captured.out


def test_cli_publication_stack_lint_reports_findings(tmp_path, capsys):
    stack_dir = make_demo_publication_stack_dir(tmp_path)

    summary_path = stack_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["release_catalog_manifest_path"] = "tampered"
    write_json(summary_path, summary)
    (stack_dir / "catalog_workspaces" / "stable_catalog" / "summary.json").unlink()

    exit_code = main(["publication-stack-lint", str(stack_dir)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert '"ok":false' in captured.out
    assert '"release_catalog_manifest_path_matches":false' in captured.out
    assert '"missing_workspace_summaries":["stable_catalog"]' in captured.out


def test_cli_publication_network_summary_reads_summary_and_index(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)

    exit_code = main(["publication-network-summary", str(network_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"stack_count":2' in captured.out
    assert '"workspace_names":["stack_a","stack_b"]' in captured.out
    assert '"release_catalog_index_summary":' in captured.out


def test_cli_publication_network_lint_accepts_clean_network(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)

    exit_code = main(["publication-network-lint", str(network_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"ok":true' in captured.out
    assert '"release_catalog_index_lint":' in captured.out
    assert '"workspace_lint_failures":[]' in captured.out


def test_cli_publication_network_lint_reports_findings(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)

    summary_path = network_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["release_catalog_index_manifest_path"] = "tampered"
    write_json(summary_path, summary)
    (network_dir / "stack_workspaces" / "stack_a" / "summary.json").unlink()

    exit_code = main(["publication-network-lint", str(network_dir)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert '"ok":false' in captured.out
    assert '"release_catalog_index_manifest_path_matches":false' in captured.out
    assert '"missing_workspace_summaries":["stack_a"]' in captured.out


def test_cli_publication_registry_workspace_summary_reads_summary_and_components(tmp_path, capsys):
    workspace_dir = make_publication_registry_workspace_dir(tmp_path)

    exit_code = main(["publication-registry-workspace-summary", str(workspace_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"artifact_count":12' in captured.out
    assert '"publication_network_summary":' in captured.out
    assert '"release_catalog_index_summary":' in captured.out
    assert '"publication_registry_summary":' in captured.out


def test_cli_publication_registry_workspace_lint_accepts_clean_workspace(tmp_path, capsys):
    workspace_dir = make_publication_registry_workspace_dir(tmp_path)

    exit_code = main(["publication-registry-workspace-lint", str(workspace_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"ok":true' in captured.out
    assert '"publication_registry_lint":' in captured.out
    assert '"metadata_bundle_lint_failures":[]' in captured.out


def test_cli_publication_registry_workspace_lint_reports_findings(tmp_path, capsys):
    workspace_dir = make_publication_registry_workspace_dir(tmp_path)

    summary_path = workspace_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["publication_registry_manifest_path"] = "tampered"
    write_json(summary_path, summary)

    bundle_name = summary["publication_metadata_bundles"][0]["bundle_name"]
    (workspace_dir / "publication_metadata_bundles" / bundle_name / "publication_metadata_manifest.json").unlink()

    exit_code = main(["publication-registry-workspace-lint", str(workspace_dir)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert '"ok":false' in captured.out
    assert '"publication_registry_manifest_path_matches":false' in captured.out
    assert f'"missing_bundle_manifests":["{bundle_name}"]' in captured.out


def test_cli_publication_registry_summary_reads_manifest_and_registry(tmp_path, capsys):
    registry_dir = make_publication_registry_dir(tmp_path)

    exit_code = main(["publication-registry-summary", str(registry_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"component_count":3' in captured.out
    assert '"publication_descriptor_index_publication":' in captured.out
    assert '"publication_metadata_catalog_publication":' in captured.out


def test_cli_publication_registry_lint_accepts_clean_registry(tmp_path, capsys):
    registry_dir = make_publication_registry_dir(tmp_path)

    exit_code = main(["publication-registry-lint", str(registry_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"ok":true' in captured.out
    assert '"component_lint_failures":[]' in captured.out


def test_cli_publication_registry_lint_reports_findings(tmp_path, capsys):
    registry_dir = make_publication_registry_dir(tmp_path)

    registry_path = registry_dir / "publication_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["publication_descriptor_index_publication"]["publication_descriptor_index_manifest_path"] = "tampered.json"
    write_json(registry_path, registry)
    (registry_dir.parent / "publication_descriptor_index_publication" / "publication_descriptor_index_manifest.json").unlink()

    exit_code = main(["publication-registry-lint", str(registry_dir)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert '"ok":false' in captured.out
    assert '"missing_component_manifests":["tampered.json"]' in captured.out


def test_cli_validate_publication_stack_summary(tmp_path, capsys):
    stack_dir = make_demo_publication_stack_dir(tmp_path)

    exit_code = main(["validate-publication-stack-summary", str(stack_dir / "summary.json")])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "valid SATROOT publication stack summary: 1 record(s)" in captured.out


def test_cli_validate_publication_network_summary(tmp_path, capsys):
    network_dir = make_demo_publication_network_dir(tmp_path)

    exit_code = main(["validate-publication-network-summary", str(network_dir / "summary.json")])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "valid SATROOT publication network summary: 1 record(s)" in captured.out


def test_cli_validate_demo_catalog_summary(tmp_path, capsys):
    output_dir = make_demo_catalog_workspace_dir(tmp_path)
    capsys.readouterr()

    exit_code = main(["validate-demo-catalog-summary", str(output_dir / "summary.json")])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "valid SATROOT demo catalog summary: 1 record(s)" in captured.out


def test_cli_build_bundle_index(tmp_path):
    events_path = tmp_path / "events.json"
    bundle_dir = tmp_path / "bundle"
    index_path = tmp_path / "bundle_index.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    bootstrap_exit_code = main(
        [
            "bootstrap-signed-ledger",
            str(events_path),
            "--scheme",
            "hmac-sha256",
            "--output-dir",
            str(bundle_dir),
        ]
    )
    assert bootstrap_exit_code == 0

    build_exit_code = main(["build-bundle-index", str(bundle_dir), "--output", str(index_path)])
    assert build_exit_code == 0

    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["bundle_count"] == 1
    assert index["bundles"][0]["bundle_path"] == "bundle"
    assert index["bundles"][0]["manifest_path"] == "bundle/bundle_manifest.json"
    assert index["bundles"][0]["scheme"] == "hmac-sha256"


def test_cli_build_bundle_index_with_release_metadata(tmp_path):
    events_path = tmp_path / "events.json"
    bundle_dir = tmp_path / "bundle"
    index_path = tmp_path / "bundle_index.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    bootstrap_exit_code = main(
        [
            "bootstrap-signed-ledger",
            str(events_path),
            "--scheme",
            "hmac-sha256",
            "--output-dir",
            str(bundle_dir),
        ]
    )
    assert bootstrap_exit_code == 0

    build_exit_code = main(
        [
            "build-bundle-index",
            str(bundle_dir),
            "--channel",
            "stable",
            "--label",
            "SATROOT FLOOR1 Demo",
            "--published-at",
            "2026-06-22T12:00:00Z",
            "--output",
            str(index_path),
        ]
    )
    assert build_exit_code == 0

    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["release"] == {
        "channel": "stable",
        "label": "SATROOT FLOOR1 Demo",
        "published_at": "2026-06-22T12:00:00Z",
    }


def test_cli_build_bundle_index_with_discovery_root(tmp_path):
    floor_events_path = tmp_path / "floor_events.json"
    machine_events_path = tmp_path / "machine_events.json"
    bundle_root = tmp_path / "bundles"
    floor_bundle_dir = bundle_root / "floor_bundle"
    machine_bundle_dir = bundle_root / "machine_bundle"
    index_path = tmp_path / "bundle_index.json"
    floor_events_path.write_text(json.dumps(load_events()), encoding="utf-8")
    machine_events_path.write_text(json.dumps(load_events("events_apicredit1.json")), encoding="utf-8")

    assert main(["bootstrap-signed-ledger", str(floor_events_path), "--scheme", "hmac-sha256", "--output-dir", str(floor_bundle_dir)]) == 0
    assert main(["bootstrap-signed-ledger", str(machine_events_path), "--scheme", "hmac-sha256", "--output-dir", str(machine_bundle_dir)]) == 0

    build_exit_code = main(
        [
            "build-bundle-index",
            "--discover-under",
            str(bundle_root),
            "--output",
            str(index_path),
        ]
    )
    assert build_exit_code == 0

    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["bundle_count"] == 2
    assert {entry["symbol"] for entry in index["bundles"]} == {"FLOOR1", "APICREDIT1"}
    assert {entry["bundle_path"] for entry in index["bundles"]} == {"bundles/floor_bundle", "bundles/machine_bundle"}


def test_cli_validate_bundle_index(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    bundle_dir = tmp_path / "bundle"
    index_path = tmp_path / "bundle_index.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    bootstrap_exit_code = main(
        [
            "bootstrap-signed-ledger",
            str(events_path),
            "--scheme",
            "hmac-sha256",
            "--output-dir",
            str(bundle_dir),
        ]
    )
    assert bootstrap_exit_code == 0
    build_exit_code = main(["build-bundle-index", str(bundle_dir), "--output", str(index_path)])
    assert build_exit_code == 0
    capsys.readouterr()

    validate_exit_code = main(["validate-bundle-index", str(index_path)])
    assert validate_exit_code == 0

    captured = capsys.readouterr()
    assert "valid SATROOT-1 bundle index: 1 record(s)" in captured.out


def test_cli_build_release_manifest(tmp_path):
    events_path = tmp_path / "events.json"
    bundle_dir = tmp_path / "bundle"
    index_path = tmp_path / "bundle_index.json"
    release_manifest_path = tmp_path / "release_manifest.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    assert main(["bootstrap-signed-ledger", str(events_path), "--scheme", "hmac-sha256", "--output-dir", str(bundle_dir)]) == 0
    assert main(["build-bundle-index", str(bundle_dir), "--output", str(index_path)]) == 0
    exit_code = main(
        [
            "build-release-manifest",
            str(index_path),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "release-key",
            "--secret",
            "release-secret",
            "--output",
            str(release_manifest_path),
        ]
    )
    assert exit_code == 0

    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    assert release_manifest["manifest_type"] == "release-manifest"
    assert release_manifest["signature_scheme"] == "hmac-sha256"
    assert release_manifest["signature_key_id"] == "release-key"


def test_cli_bootstrap_release_hmac_and_sign_manifest(tmp_path):
    events_path = tmp_path / "events.json"
    bundle_dir = tmp_path / "bundle"
    index_path = tmp_path / "bundle_index.json"
    release_dir = tmp_path / "release_hmac"
    release_manifest_path = tmp_path / "release_manifest.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    assert main(["bootstrap-signed-ledger", str(events_path), "--scheme", "hmac-sha256", "--output-dir", str(bundle_dir)]) == 0
    assert main(["build-bundle-index", str(bundle_dir), "--output", str(index_path)]) == 0
    assert main(["bootstrap-release-hmac", "--key-id", "release-key", "--output-dir", str(release_dir)]) == 0

    exit_code = main(
        [
            "build-release-manifest",
            str(index_path),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "release-key",
            "--secrets-json",
            str(release_dir / "release_secrets.json"),
            "--output",
            str(release_manifest_path),
        ]
    )
    assert exit_code == 0

    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    assert release_manifest["signature_scheme"] == "hmac-sha256"
    assert release_manifest["signature_key_id"] == "release-key"


def test_cli_validate_release_manifest(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    bundle_dir = tmp_path / "bundle"
    index_path = tmp_path / "bundle_index.json"
    release_manifest_path = tmp_path / "release_manifest.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    assert main(["bootstrap-signed-ledger", str(events_path), "--scheme", "hmac-sha256", "--output-dir", str(bundle_dir)]) == 0
    assert main(["build-bundle-index", str(bundle_dir), "--output", str(index_path)]) == 0
    assert main(
        [
            "build-release-manifest",
            str(index_path),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "release-key",
            "--secret",
            "release-secret",
            "--output",
            str(release_manifest_path),
        ]
    ) == 0
    capsys.readouterr()

    exit_code = main(["validate-release-manifest", str(release_manifest_path)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "valid SATROOT-1 release manifest: 1 record(s)" in captured.out


def test_cli_verify_release_manifest(tmp_path, capsys):
    events_path = tmp_path / "events.json"
    bundle_dir = tmp_path / "bundle"
    index_path = tmp_path / "bundle_index.json"
    release_manifest_path = tmp_path / "release_manifest.json"
    secrets_path = tmp_path / "release_secrets.json"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")
    write_json(secrets_path, {"release-key": "release-secret"})

    assert main(["bootstrap-signed-ledger", str(events_path), "--scheme", "hmac-sha256", "--output-dir", str(bundle_dir)]) == 0
    assert main(
        [
            "build-bundle-index",
            str(bundle_dir),
            "--channel",
            "stable",
            "--label",
            "SATROOT FLOOR1 Demo",
            "--published-at",
            "2026-06-26T12:00:00Z",
            "--output",
            str(index_path),
        ]
    ) == 0
    assert main(
        [
            "build-release-manifest",
            str(index_path),
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "release-key",
            "--secret",
            "release-secret",
            "--output",
            str(release_manifest_path),
        ]
    ) == 0
    capsys.readouterr()

    exit_code = main(["verify-release-manifest", str(release_manifest_path), "--secrets-json", str(secrets_path)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert '"signature_scheme":"hmac-sha256"' in captured.out
    assert '"signature_key_id":"release-key"' in captured.out
    assert '"bundle_index_path":"bundle_index.json"' in captured.out


def test_cli_publish_release(tmp_path):
    events_path = tmp_path / "events.json"
    bundle_dir = tmp_path / "bundle"
    release_material_dir = tmp_path / "release_hmac"
    release_dir = tmp_path / "release"
    events_path.write_text(json.dumps(load_events()), encoding="utf-8")

    assert main(["bootstrap-signed-ledger", str(events_path), "--scheme", "hmac-sha256", "--output-dir", str(bundle_dir)]) == 0
    assert main(["bootstrap-release-hmac", "--key-id", "release-key", "--output-dir", str(release_material_dir)]) == 0
    assert (
        main(
            [
                "publish-release",
                str(bundle_dir),
                "--output-dir",
                str(release_dir),
                "--channel",
                "stable",
                "--label",
                "SATROOT FLOOR1 Demo",
                "--published-at",
                "2026-06-26T12:00:00Z",
                "--scheme",
                "hmac-sha256",
                "--key-id",
                "release-key",
                "--secrets-json",
                str(release_material_dir / "release_secrets.json"),
            ]
        )
        == 0
    )

    bundle_index = json.loads((release_dir / "bundle_index.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    assert bundle_index["release"] == {
        "channel": "stable",
        "label": "SATROOT FLOOR1 Demo",
        "published_at": "2026-06-26T12:00:00Z",
    }
    assert bundle_index["bundles"][0]["bundle_path"] == "../bundle"
    assert release_manifest["bundle_index_path"] == "bundle_index.json"

    summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(
            json.loads((release_material_dir / "release_secrets.json").read_text(encoding="utf-8"))
        ),
    )
    assert summary["bundle_count"] == 1
    assert summary["release"] == bundle_index["release"]


def test_cli_publish_release_with_discovery_root(tmp_path):
    floor_events_path = tmp_path / "floor_events.json"
    machine_events_path = tmp_path / "machine_events.json"
    bundle_root = tmp_path / "bundles"
    floor_bundle_dir = bundle_root / "floor_bundle"
    machine_bundle_dir = bundle_root / "machine_bundle"
    release_material_dir = tmp_path / "release_hmac"
    release_dir = tmp_path / "release"
    floor_events_path.write_text(json.dumps(load_events()), encoding="utf-8")
    machine_events_path.write_text(json.dumps(load_events("events_apicredit1.json")), encoding="utf-8")

    assert main(["bootstrap-signed-ledger", str(floor_events_path), "--scheme", "hmac-sha256", "--output-dir", str(floor_bundle_dir)]) == 0
    assert main(["bootstrap-signed-ledger", str(machine_events_path), "--scheme", "hmac-sha256", "--output-dir", str(machine_bundle_dir)]) == 0
    assert main(["bootstrap-release-hmac", "--key-id", "release-key", "--output-dir", str(release_material_dir)]) == 0

    assert (
        main(
            [
                "publish-release",
                "--discover-under",
                str(bundle_root),
                "--output-dir",
                str(release_dir),
                "--channel",
                "stable",
                "--label",
                "SATROOT Multi Bundle Demo",
                "--published-at",
                "2026-06-28T18:00:00Z",
                "--scheme",
                "hmac-sha256",
                "--key-id",
                "release-key",
                "--secrets-json",
                str(release_material_dir / "release_secrets.json"),
            ]
        )
        == 0
    )

    bundle_index = json.loads((release_dir / "bundle_index.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    assert bundle_index["bundle_count"] == 2
    assert {entry["symbol"] for entry in bundle_index["bundles"]} == {"FLOOR1", "APICREDIT1"}
    assert bundle_index["release"]["label"] == "SATROOT Multi Bundle Demo"
    assert release_manifest["bundle_count"] == 2


def test_cli_bootstrap_release_publication(tmp_path, capsys):
    bundle_dir = tmp_path / "bundle"
    release_dir = tmp_path / "release"

    assert (
        main(
            [
                "bootstrap-genesis-bundle",
                "--symbol",
                "RELCLI1",
                "--name",
                "SATROOT Release CLI Asset",
                "--scheme",
                "hmac-sha256",
                "--profile",
                "SATROOT-STABLE-1",
                "--output-dir",
                str(bundle_dir),
            ]
        )
        == 0
    )

    exit_code = main(
        [
            "bootstrap-release-publication",
            str(bundle_dir),
            "--output-dir",
            str(release_dir),
            "--channel",
            "stable",
            "--label",
            "SATROOT Release CLI",
            "--published-at",
            "2026-06-26T12:00:00Z",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "release-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT release publication to" in captured.out
    bundle_index = json.loads((release_dir / "bundle_index.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    secrets = json.loads((release_dir / "release_secrets.json").read_text(encoding="utf-8"))
    assert bundle_index["release"]["channel"] == "stable"
    assert release_manifest["signature_key_id"] == "release-key"
    assert set(secrets) == {"release-key"}

    summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(secrets),
    )
    assert summary["bundle_count"] == 1
    assert summary["release"] == bundle_index["release"]


def test_cli_bootstrap_release_publication_with_discovery_root(tmp_path, capsys):
    floor_events_path = tmp_path / "floor_events.json"
    machine_events_path = tmp_path / "machine_events.json"
    bundle_root = tmp_path / "bundles"
    floor_bundle_dir = bundle_root / "floor_bundle"
    machine_bundle_dir = bundle_root / "machine_bundle"
    release_dir = tmp_path / "release"
    floor_events_path.write_text(json.dumps(load_events()), encoding="utf-8")
    machine_events_path.write_text(json.dumps(load_events("events_apicredit1.json")), encoding="utf-8")

    assert main(["bootstrap-signed-ledger", str(floor_events_path), "--scheme", "hmac-sha256", "--output-dir", str(floor_bundle_dir)]) == 0
    assert main(["bootstrap-signed-ledger", str(machine_events_path), "--scheme", "hmac-sha256", "--output-dir", str(machine_bundle_dir)]) == 0

    exit_code = main(
        [
            "bootstrap-release-publication",
            "--discover-under",
            str(bundle_root),
            "--output-dir",
            str(release_dir),
            "--channel",
            "stable",
            "--label",
            "SATROOT Catalog Release",
            "--published-at",
            "2026-06-28T19:00:00Z",
            "--scheme",
            "hmac-sha256",
            "--key-id",
            "release-key",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote bootstrapped SATROOT release publication to" in captured.out

    bundle_index = json.loads((release_dir / "bundle_index.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    release_secrets = json.loads((release_dir / "release_secrets.json").read_text(encoding="utf-8"))
    assert bundle_index["bundle_count"] == 2
    assert {entry["symbol"] for entry in bundle_index["bundles"]} == {"FLOOR1", "APICREDIT1"}
    assert release_manifest["bundle_count"] == 2

    summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(release_secrets),
    )
    assert summary["bundle_count"] == 2
    assert summary["release"] == bundle_index["release"]


def test_cli_bootstrap_demo_catalog(tmp_path, capsys):
    output_dir = tmp_path / "catalog_workspace"

    exit_code = main(
        [
            "bootstrap-demo-catalog",
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--output-dir",
            str(output_dir),
            "--channel",
            "stable",
            "--label",
            "SATROOT Demo Catalog",
            "--published-at",
            "2026-06-28T22:00:00Z",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT demo catalog workspace to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    release_dir = output_dir / "release"
    bundle_index = json.loads((release_dir / "bundle_index.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    release_secrets = json.loads((release_dir / "release_secrets.json").read_text(encoding="utf-8"))
    assert summary["bundle_count"] == 5
    assert len(summary["bundles"]) == 5
    assert {entry["bundle_name"] for entry in summary["bundles"]} == {"stable", "machine", "receipt", "identity", "license"}
    assert summary["release"] == bundle_index["release"]
    assert bundle_index["bundle_count"] == 5
    assert {entry["symbol"] for entry in bundle_index["bundles"]} == {"USDCAT1", "APICAT1", "RECCAT1", "IDCAT1", "LICCAT1"}
    assert bundle_index["release"]["label"] == "SATROOT Demo Catalog"
    assert release_manifest["signature_key_id"] == "release-key"

    for entry in summary["bundles"]:
        assert (Path(entry["bundle_dir"]) / "bundle_manifest.json").exists()

    lint_exit_code = main(["release-lint", str(release_dir)])
    assert lint_exit_code == 0
    capsys.readouterr()

    verified = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(release_secrets),
    )
    assert verified["bundle_count"] == 5
    assert verified["release"] == bundle_index["release"]


def test_cli_bootstrap_demo_catalog_subset_with_overrides(tmp_path, capsys):
    output_dir = tmp_path / "catalog_workspace_subset"

    exit_code = main(
        [
            "bootstrap-demo-catalog",
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--output-dir",
            str(output_dir),
            "--profile",
            "SATROOT-MACHINE-1",
            "--profile",
            "SATROOT-IDENTITY-1",
            "--symbol-override",
            "SATROOT-MACHINE-1=APISET2",
            "--name-override",
            "SATROOT-IDENTITY-1=SATROOT Identity Subset",
            "--channel",
            "stable",
            "--label",
            "SATROOT Subset Catalog",
            "--published-at",
            "2026-06-28T22:30:00Z",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT demo catalog workspace to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    release_dir = output_dir / "release"
    bundle_index = json.loads((release_dir / "bundle_index.json").read_text(encoding="utf-8"))
    release_secrets = json.loads((release_dir / "release_secrets.json").read_text(encoding="utf-8"))
    assert summary["bundle_count"] == 2
    assert [entry["bundle_name"] for entry in summary["bundles"]] == ["machine", "identity"]
    assert {entry["symbol"] for entry in summary["bundles"]} == {"APISET2", "IDCAT1"}
    assert {entry["name"] for entry in summary["bundles"]} == {"SATROOT Machine Catalog", "SATROOT Identity Subset"}
    assert bundle_index["bundle_count"] == 2
    assert {entry["symbol"] for entry in bundle_index["bundles"]} == {"APISET2", "IDCAT1"}
    assert (output_dir / "bundles" / "machine" / "bundle_manifest.json").exists()
    assert (output_dir / "bundles" / "identity" / "bundle_manifest.json").exists()
    assert not (output_dir / "bundles" / "stable").exists()

    verified = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(release_secrets),
    )
    assert verified["bundle_count"] == 2
    assert verified["release"] == bundle_index["release"]


def test_cli_bootstrap_demo_catalog_subset_with_profile_field_overrides(tmp_path, capsys):
    output_dir = tmp_path / "catalog_workspace_fields"

    exit_code = main(
        [
            "bootstrap-demo-catalog",
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--output-dir",
            str(output_dir),
            "--profile",
            "SATROOT-STABLE-1",
            "--profile",
            "SATROOT-MACHINE-1",
            "--profile-field-override",
            "SATROOT-STABLE-1:reference_unit=EUR",
            "--profile-field-override",
            "SATROOT-STABLE-1:intended_use=treasury-ledger",
            "--profile-field-override",
            "SATROOT-MACHINE-1:service_scope=batch-inference",
            "--profile-field-override",
            "SATROOT-MACHINE-1:billing_unit=job",
            "--profile-field-override",
            "SATROOT-MACHINE-1:intended_use=compute-credit",
            "--channel",
            "stable",
            "--label",
            "SATROOT Field Override Catalog",
            "--published-at",
            "2026-06-28T23:00:00Z",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT demo catalog workspace to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    stable_genesis = json.loads((output_dir / "bundles" / "stable" / "genesis.json").read_text(encoding="utf-8"))
    machine_genesis = json.loads((output_dir / "bundles" / "machine" / "genesis.json").read_text(encoding="utf-8"))
    assert summary["bundle_count"] == 2
    assert stable_genesis["reference_unit"] == "EUR"
    assert stable_genesis["intended_use"] == "treasury-ledger"
    assert stable_genesis["redemption"] == "none"
    assert stable_genesis["reserve_model"] == "none"
    assert machine_genesis["service_scope"] == "batch-inference"
    assert machine_genesis["billing_unit"] == "job"
    assert machine_genesis["intended_use"] == "compute-credit"


def test_cli_bootstrap_demo_catalog_subset_with_structure_overrides(tmp_path, capsys):
    output_dir = tmp_path / "catalog_workspace_structure"

    exit_code = main(
        [
            "bootstrap-demo-catalog",
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--output-dir",
            str(output_dir),
            "--profile",
            "SATROOT-STABLE-1",
            "--profile",
            "SATROOT-MACHINE-1",
            "--profile",
            "SATROOT-IDENTITY-1",
            "--profile-structure-override",
            "SATROOT-STABLE-1:merchant_account=merchant_beta",
            "--profile-structure-override",
            "SATROOT-STABLE-1:service_account=settlement_node",
            "--profile-structure-override",
            "SATROOT-STABLE-1:initial_balance=30000000",
            "--profile-structure-override",
            "SATROOT-STABLE-1:merchant_amount=1400000",
            "--profile-structure-override",
            "SATROOT-STABLE-1:service_amount=350000",
            "--profile-structure-override",
            "SATROOT-STABLE-1:merchant_burn_amount=0",
            "--profile-structure-override",
            "SATROOT-MACHINE-1:tenant_account=tenant_b",
            "--profile-structure-override",
            "SATROOT-MACHINE-1:worker_account=worker_beta",
            "--profile-structure-override",
            "SATROOT-MACHINE-1:max_supply=150000000",
            "--profile-structure-override",
            "SATROOT-MACHINE-1:initial_balance=120000000",
            "--profile-structure-override",
            "SATROOT-MACHINE-1:tenant_amount=7000000",
            "--profile-structure-override",
            "SATROOT-MACHINE-1:worker_amount=1500000",
            "--profile-structure-override",
            "SATROOT-MACHINE-1:worker_burn_amount=0",
            "--profile-structure-override",
            "SATROOT-IDENTITY-1:holder_account=controller_a",
            "--profile-structure-override",
            "SATROOT-IDENTITY-1:next_holder=none",
            "--profile-structure-override",
            "SATROOT-IDENTITY-1:retire=false",
            "--channel",
            "stable",
            "--label",
            "SATROOT Structure Override Catalog",
            "--published-at",
            "2026-06-29T00:00:00Z",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT demo catalog workspace to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    stable_genesis = json.loads((output_dir / "bundles" / "stable" / "genesis.json").read_text(encoding="utf-8"))
    stable_events = json.loads((output_dir / "bundles" / "stable" / "signed_events.json").read_text(encoding="utf-8"))
    machine_genesis = json.loads((output_dir / "bundles" / "machine" / "genesis.json").read_text(encoding="utf-8"))
    machine_events = json.loads((output_dir / "bundles" / "machine" / "signed_events.json").read_text(encoding="utf-8"))
    identity_events = json.loads((output_dir / "bundles" / "identity" / "signed_events.json").read_text(encoding="utf-8"))
    release_dir = output_dir / "release"
    release_secrets = json.loads((release_dir / "release_secrets.json").read_text(encoding="utf-8"))

    assert summary["bundle_count"] == 3
    assert stable_genesis["initial_balances"] == {"issuer": "30000000"}
    assert len(stable_events) == 3
    assert stable_events[1]["to"] == "merchant_beta"
    assert stable_events[1]["amount"] == "1400000"
    assert stable_events[2]["to"] == "settlement_node"
    assert stable_events[2]["amount"] == "350000"

    assert machine_genesis["max_supply"] == "150000000"
    assert machine_genesis["initial_balances"] == {"issuer": "120000000"}
    assert len(machine_events) == 3
    assert machine_events[1]["to"] == "tenant_b"
    assert machine_events[1]["amount"] == "7000000"
    assert machine_events[2]["to"] == "worker_beta"
    assert machine_events[2]["amount"] == "1500000"

    assert len(identity_events) == 2
    assert identity_events[1]["to"] == "controller_a"

    identity_summary = next(entry for entry in summary["bundles"] if entry["profile"] == "SATROOT-IDENTITY-1")
    assert identity_summary["structure_overrides"]["next_holder"] is None
    assert identity_summary["structure_overrides"]["retire"] is False

    verified = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(release_secrets),
    )
    assert verified["bundle_count"] == 3


def test_cli_bootstrap_demo_catalog_with_preset_json_and_cli_overrides(tmp_path, capsys):
    preset_path = tmp_path / "catalog_preset.json"
    write_json(
        preset_path,
        {
            "type": "SATROOT-DEMO-CATALOG-PRESET",
            "version": "0.1",
            "profiles": ["SATROOT-STABLE-1", "SATROOT-MACHINE-1"],
            "symbol_overrides": {"SATROOT-MACHINE-1": "APIPRESET1"},
            "name_overrides": {"SATROOT-STABLE-1": "SATROOT Preset Stable"},
            "profile_field_overrides": {
                "SATROOT-STABLE-1": {"reference_unit": "EUR"},
                "SATROOT-MACHINE-1": {"service_scope": "batch-inference", "intended_use": "preset-credit"},
            },
            "profile_structure_overrides": {
                "SATROOT-STABLE-1": {
                    "merchant_account": "merchant_preset",
                    "merchant_burn_amount": "0",
                },
                "SATROOT-MACHINE-1": {
                    "tenant_account": "tenant_preset",
                    "worker_burn_amount": 0,
                },
            },
            "release": {
                "channel": "beta",
                "label": "SATROOT Preset Catalog",
                "published_at": "2026-06-30T01:00:00Z",
            },
        },
    )
    output_dir = tmp_path / "catalog_workspace_preset"

    exit_code = main(
        [
            "bootstrap-demo-catalog",
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--output-dir",
            str(output_dir),
            "--preset-json",
            str(preset_path),
            "--symbol-override",
            "SATROOT-MACHINE-1=APIMERGE1",
            "--profile-field-override",
            "SATROOT-MACHINE-1:intended_use=cli-credit",
            "--label",
            "SATROOT Preset Override Catalog",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT demo catalog workspace to" in captured.out

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    release_dir = output_dir / "release"
    bundle_index = json.loads((release_dir / "bundle_index.json").read_text(encoding="utf-8"))
    stable_genesis = json.loads((output_dir / "bundles" / "stable" / "genesis.json").read_text(encoding="utf-8"))
    machine_genesis = json.loads((output_dir / "bundles" / "machine" / "genesis.json").read_text(encoding="utf-8"))

    assert summary["bundle_count"] == 2
    assert summary["preset_path"] == str(preset_path.resolve())
    assert summary["release"]["channel"] == "beta"
    assert summary["release"]["label"] == "SATROOT Preset Override Catalog"
    assert summary["release"]["published_at"] == "2026-06-30T01:00:00Z"
    assert bundle_index["release"] == summary["release"]
    assert {entry["symbol"] for entry in summary["bundles"]} == {"USDCAT1", "APIMERGE1"}
    assert stable_genesis["reference_unit"] == "EUR"
    assert machine_genesis["service_scope"] == "batch-inference"
    assert machine_genesis["intended_use"] == "cli-credit"

    stable_summary = next(entry for entry in summary["bundles"] if entry["profile"] == "SATROOT-STABLE-1")
    machine_summary = next(entry for entry in summary["bundles"] if entry["profile"] == "SATROOT-MACHINE-1")
    assert stable_summary["structure_overrides"]["merchant_account"] == "merchant_preset"
    assert stable_summary["structure_overrides"]["merchant_burn_amount"] == "0"
    assert machine_summary["structure_overrides"]["tenant_account"] == "tenant_preset"
    assert machine_summary["structure_overrides"]["worker_burn_amount"] == "0"


def test_cli_bootstrap_stable_demo(tmp_path, capsys):
    output_dir = tmp_path / "stable_demo"

    exit_code = main(
        [
            "bootstrap-stable-demo",
            "--symbol",
            "USDCLI2",
            "--name",
            "Stable CLI Demo",
            "--reference-unit",
            "EUR",
            "--merchant-burn-amount",
            "0",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-STABLE-1 demo ledger to" in captured.out

    events = json.loads((output_dir / "events.json").read_text(encoding="utf-8"))
    annotated = json.loads((output_dir / "annotated_events.json").read_text(encoding="utf-8"))
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    state = replay(events)
    assert len(events) == 3
    assert len(annotated) == 3
    assert summary["profile"] == "SATROOT-STABLE-1"
    assert summary["reference_unit"] == "EUR"
    assert summary["event_count"] == 3
    assert state.symbol == "USDCLI2"
    assert state.genesis_metadata["reference_unit"] == "EUR"
    assert state.balances["merchant"] == 1_250_000
    assert state.balances["api_node"] == 250_000


def test_cli_bootstrap_machine_demo(tmp_path, capsys):
    output_dir = tmp_path / "machine_demo"

    exit_code = main(
        [
            "bootstrap-machine-demo",
            "--symbol",
            "APIDEMO2",
            "--name",
            "Machine CLI Demo",
            "--service-scope",
            "inference-api",
            "--billing-unit",
            "token",
            "--worker-burn-amount",
            "50000",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-MACHINE-1 demo ledger to" in captured.out

    events = json.loads((output_dir / "events.json").read_text(encoding="utf-8"))
    annotated = json.loads((output_dir / "annotated_events.json").read_text(encoding="utf-8"))
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    state = replay(events)
    assert len(events) == 4
    assert len(annotated) == 4
    assert summary["profile"] == "SATROOT-MACHINE-1"
    assert summary["service_scope"] == "inference-api"
    assert summary["billing_unit"] == "token"
    assert state.symbol == "APIDEMO2"
    assert state.genesis_metadata["service_scope"] == "inference-api"
    assert state.genesis_metadata["billing_unit"] == "token"
    assert state.balances["tenant_a"] == 3_800_000
    assert state.balances["worker_node"] == 1_150_000


def test_cli_bootstrap_machine_demo_bundle_hmac(tmp_path, capsys):
    output_dir = tmp_path / "machine_bundle"

    exit_code = main(
        [
            "bootstrap-machine-demo-bundle",
            "--symbol",
            "APIBUNDLE2",
            "--name",
            "Machine Bundle CLI",
            "--scheme",
            "hmac-sha256",
            "--service-scope",
            "batch-jobs",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-MACHINE-1 hmac-sha256 demo bundle to" in captured.out

    genesis = json.loads((output_dir / "genesis.json").read_text(encoding="utf-8"))
    signer_key_map = json.loads((output_dir / "signer_key_map.json").read_text(encoding="utf-8"))
    secrets = json.loads((output_dir / "secrets.json").read_text(encoding="utf-8"))
    signed_events = json.loads((output_dir / "signed_events.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    verifier = make_hmac_sha256_verifier(secrets)
    state = replay(signed_events, verifier=verifier)
    assert genesis["profile"] == "SATROOT-MACHINE-1"
    assert genesis["service_scope"] == "batch-jobs"
    assert signer_key_map == {
        "issuer": "issuer-key",
        "tenant_a": "tenant_a-key",
        "worker_node": "worker_node-key",
    }
    assert state.symbol == "APIBUNDLE2"
    assert manifest["scheme"] == "hmac-sha256"
    assert manifest["files"]["genesis"] == "genesis.json"

    summary = verify_signed_ledger_bundle(output_dir)
    assert summary["symbol"] == "APIBUNDLE2"
    assert summary["record_count"] == 4


def test_cli_bootstrap_machine_demo_bundle_ed25519_verifier_only(tmp_path):
    output_dir = tmp_path / "machine_bundle_ed25519"

    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            main(
                [
                    "bootstrap-machine-demo-bundle",
                    "--symbol",
                    "APIEDCLI1",
                    "--name",
                    "Machine Bundle Ed25519",
                    "--scheme",
                    "ed25519",
                    "--output-dir",
                    str(output_dir),
                    "--verifier-only",
                ]
            )
        return

    exit_code = main(
        [
            "bootstrap-machine-demo-bundle",
            "--symbol",
            "APIEDCLI1",
            "--name",
            "Machine Bundle Ed25519",
            "--scheme",
            "ed25519",
            "--output-dir",
            str(output_dir),
            "--verifier-only",
        ]
    )
    assert exit_code == 0
    assert not (output_dir / "private_keys.json").exists()
    assert (output_dir / "public_keys.json").exists()

    manifest = json.loads((output_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    assert manifest["verification_material_scope"] == "public-only"
    assert manifest["final_state_snapshot"]["profile"] == "SATROOT-MACHINE-1"
    assert "private_keys" not in manifest["files"]
    assert "private_keys" not in manifest["file_hashes"]

    verify_exit_code = main(["verify-bundle", str(output_dir)])
    assert verify_exit_code == 0


def test_cli_bootstrap_machine_demo_release_hmac(tmp_path, capsys):
    output_dir = tmp_path / "machine_release"

    exit_code = main(
        [
            "bootstrap-machine-demo-release",
            "--symbol",
            "APIRELCLI1",
            "--name",
            "Machine Release CLI",
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--service-scope",
            "render-farm",
            "--channel",
            "stable",
            "--label",
            "SATROOT Machine Release",
            "--published-at",
            "2026-06-28T06:00:00Z",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-MACHINE-1 demo release to" in captured.out

    bundle_dir = output_dir / "bundle"
    release_dir = output_dir / "release"
    bundle_manifest = json.loads((bundle_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    bundle_index = json.loads((release_dir / "bundle_index.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    release_secrets = json.loads((release_dir / "release_secrets.json").read_text(encoding="utf-8"))
    assert bundle_manifest["symbol"] == "APIRELCLI1"
    assert bundle_manifest["final_state_snapshot"]["genesis_metadata"]["service_scope"] == "render-farm"
    assert bundle_index["release"]["label"] == "SATROOT Machine Release"
    assert release_manifest["signature_key_id"] == "release-key"

    summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(release_secrets),
    )
    assert summary["bundle_count"] == 1
    assert summary["release"] == bundle_index["release"]


def test_cli_bootstrap_machine_demo_release_ed25519(tmp_path, capsys):
    output_dir = tmp_path / "machine_release_ed25519"

    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            main(
                [
                    "bootstrap-machine-demo-release",
                    "--symbol",
                    "APIRELCLI2",
                    "--name",
                    "Machine Release Ed25519",
                    "--scheme",
                    "ed25519",
                    "--release-key-id",
                    "release-key",
                    "--output-dir",
                    str(output_dir),
                    "--verifier-only",
                ]
            )
        return

    exit_code = main(
        [
            "bootstrap-machine-demo-release",
            "--symbol",
            "APIRELCLI2",
            "--name",
            "Machine Release Ed25519",
            "--scheme",
            "ed25519",
            "--release-key-id",
            "release-key",
            "--service-scope",
            "gpu-cluster",
            "--channel",
            "stable",
            "--label",
            "SATROOT Machine Release Ed25519",
            "--published-at",
            "2026-06-28T08:00:00Z",
            "--output-dir",
            str(output_dir),
            "--verifier-only",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-MACHINE-1 demo release to" in captured.out

    bundle_dir = output_dir / "bundle"
    release_dir = output_dir / "release"
    bundle_manifest = json.loads((bundle_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    bundle_public_keys = json.loads((bundle_dir / "public_keys.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    release_public_keys = json.loads((release_dir / "release_public_keys.json").read_text(encoding="utf-8"))
    assert not (bundle_dir / "private_keys.json").exists()
    assert bundle_manifest["verification_material_scope"] == "public-only"
    assert bundle_manifest["final_state_snapshot"]["genesis_metadata"]["service_scope"] == "gpu-cluster"
    assert release_manifest["signature_scheme"] == "ed25519"
    assert release_manifest["signature_key_id"] == "release-key"

    bundle_summary = verify_signed_ledger_bundle(bundle_dir)
    assert bundle_summary["symbol"] == "APIRELCLI2"
    assert bundle_summary["annotated_verified"] is True
    assert set(bundle_public_keys) == {"issuer-key", "tenant_a-key", "worker_node-key"}

    release_summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_ed25519_verifier(release_public_keys),
    )
    assert release_summary["bundle_count"] == 1
    assert release_summary["release"]["label"] == "SATROOT Machine Release Ed25519"


def test_cli_bootstrap_singleton_demo_receipt(tmp_path, capsys):
    output_dir = tmp_path / "singleton_receipt"

    exit_code = main(
        [
            "bootstrap-singleton-demo",
            "--profile",
            "SATROOT-RECEIPT-1",
            "--symbol",
            "RECDEMO2",
            "--name",
            "Receipt CLI Demo",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-RECEIPT-1 singleton demo ledger to" in captured.out

    events = json.loads((output_dir / "events.json").read_text(encoding="utf-8"))
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    state = replay(events)
    assert len(events) == 4
    assert summary["profile"] == "SATROOT-RECEIPT-1"
    assert state.supply == 0
    assert state.balances["archive"] == 0


def test_cli_bootstrap_singleton_demo_identity_custom_flow(tmp_path, capsys):
    output_dir = tmp_path / "singleton_identity"

    exit_code = main(
        [
            "bootstrap-singleton-demo",
            "--profile",
            "SATROOT-IDENTITY-1",
            "--symbol",
            "IDDEMO2",
            "--name",
            "Identity CLI Demo",
            "--next-holder",
            "controller_v2",
            "--no-archive",
            "--no-retire",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-IDENTITY-1 singleton demo ledger to" in captured.out

    events = json.loads((output_dir / "events.json").read_text(encoding="utf-8"))
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    state = replay(events)
    assert len(events) == 3
    assert summary["profile"] == "SATROOT-IDENTITY-1"
    assert state.supply == 1
    assert state.balances["controller_v2"] == 1


def test_cli_bootstrap_singleton_demo_bundle_hmac(tmp_path, capsys):
    output_dir = tmp_path / "singleton_bundle"

    exit_code = main(
        [
            "bootstrap-singleton-demo-bundle",
            "--profile",
            "SATROOT-RECEIPT-1",
            "--symbol",
            "RECBUNDLE2",
            "--name",
            "Receipt Bundle CLI",
            "--scheme",
            "hmac-sha256",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-RECEIPT-1 hmac-sha256 singleton demo bundle to" in captured.out

    genesis = json.loads((output_dir / "genesis.json").read_text(encoding="utf-8"))
    signer_key_map = json.loads((output_dir / "signer_key_map.json").read_text(encoding="utf-8"))
    secrets = json.loads((output_dir / "secrets.json").read_text(encoding="utf-8"))
    signed_events = json.loads((output_dir / "signed_events.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    verifier = make_hmac_sha256_verifier(secrets)
    state = replay(signed_events, verifier=verifier)
    assert genesis["profile"] == "SATROOT-RECEIPT-1"
    assert signer_key_map == {"issuer": "issuer-key", "buyer": "buyer-key", "archive": "archive-key"}
    assert state.symbol == "RECBUNDLE2"
    assert manifest["scheme"] == "hmac-sha256"
    assert manifest["files"]["genesis"] == "genesis.json"

    summary = verify_signed_ledger_bundle(output_dir)
    assert summary["symbol"] == "RECBUNDLE2"
    assert summary["record_count"] == 4


def test_cli_bootstrap_singleton_demo_bundle_ed25519_verifier_only(tmp_path):
    output_dir = tmp_path / "singleton_bundle_ed25519"

    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            main(
                [
                    "bootstrap-singleton-demo-bundle",
                    "--profile",
                    "SATROOT-IDENTITY-1",
                    "--symbol",
                    "IDBUNDLE3",
                    "--name",
                    "Identity Bundle Ed25519",
                    "--scheme",
                    "ed25519",
                    "--output-dir",
                    str(output_dir),
                    "--verifier-only",
                ]
            )
        return

    exit_code = main(
        [
            "bootstrap-singleton-demo-bundle",
            "--profile",
            "SATROOT-IDENTITY-1",
            "--symbol",
            "IDBUNDLE3",
            "--name",
            "Identity Bundle Ed25519",
            "--scheme",
            "ed25519",
            "--output-dir",
            str(output_dir),
            "--verifier-only",
        ]
    )
    assert exit_code == 0
    assert not (output_dir / "private_keys.json").exists()
    assert (output_dir / "public_keys.json").exists()

    manifest = json.loads((output_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    assert manifest["verification_material_scope"] == "public-only"
    assert manifest["final_state_snapshot"]["profile"] == "SATROOT-IDENTITY-1"
    assert "private_keys" not in manifest["files"]

    verify_exit_code = main(["verify-bundle", str(output_dir)])
    assert verify_exit_code == 0


def test_cli_bootstrap_singleton_demo_release_hmac(tmp_path, capsys):
    output_dir = tmp_path / "singleton_release"

    exit_code = main(
        [
            "bootstrap-singleton-demo-release",
            "--profile",
            "SATROOT-LICENSE-1",
            "--symbol",
            "LICRELCLI1",
            "--name",
            "License Release CLI",
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--channel",
            "stable",
            "--label",
            "SATROOT License Release",
            "--published-at",
            "2026-06-28T12:00:00Z",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-LICENSE-1 singleton demo release to" in captured.out

    bundle_dir = output_dir / "bundle"
    release_dir = output_dir / "release"
    bundle_manifest = json.loads((bundle_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    bundle_index = json.loads((release_dir / "bundle_index.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    release_secrets = json.loads((release_dir / "release_secrets.json").read_text(encoding="utf-8"))
    assert bundle_manifest["symbol"] == "LICRELCLI1"
    assert bundle_manifest["final_state_snapshot"]["profile"] == "SATROOT-LICENSE-1"
    assert bundle_index["release"]["label"] == "SATROOT License Release"
    assert release_manifest["signature_key_id"] == "release-key"

    summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(release_secrets),
    )
    assert summary["bundle_count"] == 1
    assert summary["release"] == bundle_index["release"]


def test_cli_bootstrap_singleton_demo_release_ed25519(tmp_path, capsys):
    output_dir = tmp_path / "singleton_release_ed25519"

    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            main(
                [
                    "bootstrap-singleton-demo-release",
                    "--profile",
                    "SATROOT-IDENTITY-1",
                    "--symbol",
                    "IDRELCLI2",
                    "--name",
                    "Identity Release Ed25519",
                    "--scheme",
                    "ed25519",
                    "--release-key-id",
                    "release-key",
                    "--output-dir",
                    str(output_dir),
                    "--verifier-only",
                ]
            )
        return

    exit_code = main(
        [
            "bootstrap-singleton-demo-release",
            "--profile",
            "SATROOT-IDENTITY-1",
            "--symbol",
            "IDRELCLI2",
            "--name",
            "Identity Release Ed25519",
            "--scheme",
            "ed25519",
            "--release-key-id",
            "release-key",
            "--channel",
            "stable",
            "--label",
            "SATROOT Identity Release Ed25519",
            "--published-at",
            "2026-06-28T18:00:00Z",
            "--output-dir",
            str(output_dir),
            "--verifier-only",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-IDENTITY-1 singleton demo release to" in captured.out

    bundle_dir = output_dir / "bundle"
    release_dir = output_dir / "release"
    bundle_manifest = json.loads((bundle_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    release_public_keys = json.loads((release_dir / "release_public_keys.json").read_text(encoding="utf-8"))
    assert not (bundle_dir / "private_keys.json").exists()
    assert bundle_manifest["verification_material_scope"] == "public-only"
    assert bundle_manifest["final_state_snapshot"]["profile"] == "SATROOT-IDENTITY-1"
    assert release_manifest["signature_scheme"] == "ed25519"
    assert release_manifest["signature_key_id"] == "release-key"

    bundle_summary = verify_signed_ledger_bundle(bundle_dir)
    assert bundle_summary["symbol"] == "IDRELCLI2"
    assert bundle_summary["annotated_verified"] is True

    release_summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_ed25519_verifier(release_public_keys),
    )
    assert release_summary["bundle_count"] == 1
    assert release_summary["release"]["label"] == "SATROOT Identity Release Ed25519"


def test_cli_bootstrap_stable_demo_bundle_hmac(tmp_path, capsys):
    output_dir = tmp_path / "stable_bundle"

    exit_code = main(
        [
            "bootstrap-stable-demo-bundle",
            "--symbol",
            "USDBUNDLE2",
            "--name",
            "Stable Bundle CLI",
            "--scheme",
            "hmac-sha256",
            "--reference-unit",
            "CHF",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-STABLE-1 hmac-sha256 demo bundle to" in captured.out

    genesis = json.loads((output_dir / "genesis.json").read_text(encoding="utf-8"))
    signer_key_map = json.loads((output_dir / "signer_key_map.json").read_text(encoding="utf-8"))
    secrets = json.loads((output_dir / "secrets.json").read_text(encoding="utf-8"))
    signed_events = json.loads((output_dir / "signed_events.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    verifier = make_hmac_sha256_verifier(secrets)
    state = replay(signed_events, verifier=verifier)
    assert genesis["profile"] == "SATROOT-STABLE-1"
    assert genesis["reference_unit"] == "CHF"
    assert signer_key_map == {"issuer": "issuer-key", "merchant": "merchant-key"}
    assert state.symbol == "USDBUNDLE2"
    assert manifest["scheme"] == "hmac-sha256"
    assert manifest["files"]["genesis"] == "genesis.json"

    summary = verify_signed_ledger_bundle(output_dir)
    assert summary["symbol"] == "USDBUNDLE2"
    assert summary["record_count"] == 4


def test_cli_bootstrap_stable_demo_bundle_ed25519_verifier_only(tmp_path):
    output_dir = tmp_path / "stable_bundle_ed25519"

    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            main(
                [
                    "bootstrap-stable-demo-bundle",
                    "--symbol",
                    "USDEDCLI1",
                    "--name",
                    "Stable Bundle Ed25519",
                    "--scheme",
                    "ed25519",
                    "--reference-unit",
                    "AUD",
                    "--output-dir",
                    str(output_dir),
                    "--verifier-only",
                ]
            )
        return

    exit_code = main(
        [
            "bootstrap-stable-demo-bundle",
            "--symbol",
            "USDEDCLI1",
            "--name",
            "Stable Bundle Ed25519",
            "--scheme",
            "ed25519",
            "--reference-unit",
            "AUD",
            "--output-dir",
            str(output_dir),
            "--verifier-only",
        ]
    )
    assert exit_code == 0
    assert not (output_dir / "private_keys.json").exists()
    assert (output_dir / "public_keys.json").exists()

    manifest = json.loads((output_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    assert manifest["verification_material_scope"] == "public-only"
    assert manifest["final_state_snapshot"]["genesis_metadata"]["reference_unit"] == "AUD"
    assert "private_keys" not in manifest["files"]
    assert "private_keys" not in manifest["file_hashes"]

    verify_exit_code = main(["verify-bundle", str(output_dir)])
    assert verify_exit_code == 0


def test_cli_bootstrap_stable_demo_release_hmac(tmp_path, capsys):
    output_dir = tmp_path / "stable_release"

    exit_code = main(
        [
            "bootstrap-stable-demo-release",
            "--symbol",
            "USDRELCLI1",
            "--name",
            "Stable Release CLI",
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--reference-unit",
            "JPY",
            "--channel",
            "stable",
            "--label",
            "SATROOT Stable Release",
            "--published-at",
            "2026-06-27T12:00:00Z",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-STABLE-1 demo release to" in captured.out

    bundle_dir = output_dir / "bundle"
    release_dir = output_dir / "release"
    bundle_manifest = json.loads((bundle_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    bundle_index = json.loads((release_dir / "bundle_index.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    release_secrets = json.loads((release_dir / "release_secrets.json").read_text(encoding="utf-8"))
    assert bundle_manifest["symbol"] == "USDRELCLI1"
    assert bundle_manifest["final_state_snapshot"]["genesis_metadata"]["reference_unit"] == "JPY"
    assert bundle_index["release"]["label"] == "SATROOT Stable Release"
    assert release_manifest["signature_key_id"] == "release-key"

    summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(release_secrets),
    )
    assert summary["bundle_count"] == 1
    assert summary["release"] == bundle_index["release"]


def test_cli_bootstrap_machine_demo_release_hmac(tmp_path, capsys):
    output_dir = tmp_path / "machine_release"

    exit_code = main(
        [
            "bootstrap-machine-demo-release",
            "--symbol",
            "APIRELCLI1",
            "--name",
            "Machine Release CLI",
            "--scheme",
            "hmac-sha256",
            "--release-key-id",
            "release-key",
            "--service-scope",
            "render-cluster",
            "--channel",
            "stable",
            "--label",
            "SATROOT Machine Release",
            "--published-at",
            "2026-06-28T12:00:00Z",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-MACHINE-1 demo release to" in captured.out

    bundle_dir = output_dir / "bundle"
    release_dir = output_dir / "release"
    bundle_manifest = json.loads((bundle_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    bundle_index = json.loads((release_dir / "bundle_index.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    release_secrets = json.loads((release_dir / "release_secrets.json").read_text(encoding="utf-8"))
    assert bundle_manifest["symbol"] == "APIRELCLI1"
    assert bundle_manifest["final_state_snapshot"]["genesis_metadata"]["service_scope"] == "render-cluster"
    assert bundle_index["release"]["label"] == "SATROOT Machine Release"
    assert release_manifest["signature_key_id"] == "release-key"

    summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_hmac_sha256_verifier(release_secrets),
    )
    assert summary["bundle_count"] == 1
    assert summary["release"] == bundle_index["release"]


def test_cli_bootstrap_stable_demo_release_ed25519(tmp_path, capsys):
    output_dir = tmp_path / "stable_release_ed25519"

    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            main(
                [
                    "bootstrap-stable-demo-release",
                    "--symbol",
                    "USDRELCLI2",
                    "--name",
                    "Stable Release Ed25519",
                    "--scheme",
                    "ed25519",
                    "--release-key-id",
                    "release-key",
                    "--reference-unit",
                    "SGD",
                    "--output-dir",
                    str(output_dir),
                    "--verifier-only",
                ]
            )
        return

    exit_code = main(
        [
            "bootstrap-stable-demo-release",
            "--symbol",
            "USDRELCLI2",
            "--name",
            "Stable Release Ed25519",
            "--scheme",
            "ed25519",
            "--release-key-id",
            "release-key",
            "--reference-unit",
            "SGD",
            "--channel",
            "stable",
            "--label",
            "SATROOT Stable Release Ed25519",
            "--published-at",
            "2026-06-27T18:00:00Z",
            "--output-dir",
            str(output_dir),
            "--verifier-only",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "wrote SATROOT-STABLE-1 demo release to" in captured.out

    bundle_dir = output_dir / "bundle"
    release_dir = output_dir / "release"
    bundle_manifest = json.loads((bundle_dir / "bundle_manifest.json").read_text(encoding="utf-8"))
    bundle_public_keys = json.loads((bundle_dir / "public_keys.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8"))
    release_public_keys = json.loads((release_dir / "release_public_keys.json").read_text(encoding="utf-8"))
    assert not (bundle_dir / "private_keys.json").exists()
    assert bundle_manifest["verification_material_scope"] == "public-only"
    assert bundle_manifest["final_state_snapshot"]["genesis_metadata"]["reference_unit"] == "SGD"
    assert release_manifest["signature_scheme"] == "ed25519"
    assert release_manifest["signature_key_id"] == "release-key"

    bundle_summary = verify_signed_ledger_bundle(bundle_dir)
    assert bundle_summary["symbol"] == "USDRELCLI2"
    assert bundle_summary["annotated_verified"] is True
    assert set(bundle_public_keys) == {"issuer-key", "merchant-key"}

    release_summary = verify_signed_release_manifest(
        release_dir / "release_manifest.json",
        verifier=make_ed25519_verifier(release_public_keys),
    )
    assert release_summary["bundle_count"] == 1
    assert release_summary["release"]["label"] == "SATROOT Stable Release Ed25519"


def test_cli_bootstrap_release_ed25519_material(tmp_path):
    output_dir = tmp_path / "release_ed25519"
    if not ed25519_available():
        assert ed25519_available() is False
        with pytest.raises(SatRootError):
            main(["bootstrap-release-ed25519", "--key-id", "release-key", "--output-dir", str(output_dir)])
        return

    exit_code = main(["bootstrap-release-ed25519", "--key-id", "release-key", "--output-dir", str(output_dir)])
    assert exit_code == 0

    private_keys = json.loads((output_dir / "release_private_keys.json").read_text(encoding="utf-8"))
    public_keys = json.loads((output_dir / "release_public_keys.json").read_text(encoding="utf-8"))
    assert set(private_keys) == {"release-key"}
    assert set(public_keys) == {"release-key"}


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
