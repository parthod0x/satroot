"""SATROOT-1 v0.1 reference balance engine.

This is intentionally small and dependency-free.
It validates ledger arithmetic, sequence order, root consistency,
and basic authority placeholders. Real deployments must replace
`verify_signature_placeholder` with actual signature verification.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import hmac
import importlib
import importlib.util
import json
import os
import re
import secrets
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence


class SatRootError(ValueError):
    pass


ROOT_ID_RE = re.compile(r"^[a-fA-F0-9]{64}:[0-9]+$")
REFERENCE_UNIT_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{1,15}$")
COMPACT_IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
PROFILE_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.profile-registry.json"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.schema.json"
BUNDLE_MANIFEST_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.bundle-manifest.schema.json"
BUNDLE_INDEX_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.bundle-index.schema.json"
RELEASE_MANIFEST_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.release-manifest.schema.json"
RELEASE_CATALOG_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.release-catalog.schema.json"
RELEASE_CATALOG_MANIFEST_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.release-catalog-manifest.schema.json"
RELEASE_CATALOG_INDEX_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.release-catalog-index.schema.json"
RELEASE_CATALOG_INDEX_MANIFEST_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.release-catalog-index-manifest.schema.json"
DEMO_CATALOG_SUMMARY_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.demo-catalog-summary.schema.json"
PUBLICATION_STACK_SUMMARY_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.publication-stack-summary.schema.json"
PUBLICATION_NETWORK_SUMMARY_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.publication-network-summary.schema.json"
PUBLICATION_DESCRIPTOR_INDEX_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.publication-descriptor-index.schema.json"
PUBLICATION_DESCRIPTOR_INDEX_MANIFEST_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.publication-descriptor-index-manifest.schema.json"
PUBLICATION_METADATA_MANIFEST_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.publication-metadata-manifest.schema.json"
PUBLICATION_METADATA_CATALOG_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.publication-metadata-catalog.schema.json"
PUBLICATION_METADATA_CATALOG_MANIFEST_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.publication-metadata-catalog-manifest.schema.json"
PUBLICATION_REGISTRY_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.publication-registry.schema.json"
PUBLICATION_REGISTRY_MANIFEST_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.publication-registry-manifest.schema.json"
SignatureVerifier = Callable[[Dict[str, Any], str], bool]
SignerFunction = Callable[[str, str], str]
SUPPORTED_SIGNATURE_SCHEMES = {"demo", "hmac-sha256", "ed25519"}
CORE_GENESIS_FIELDS = {
    "protocol",
    "version",
    "action",
    "root_id",
    "sequence",
    "symbol",
    "name",
    "decimals",
    "max_supply",
    "mint_authority",
    "transfer_model",
    "initial_balances",
}
PROFILE_SCAFFOLD_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "SATROOT-STABLE-1": {
        "decimals": 2,
        "max_supply": "1000000000",
        "initial_balance": "1000000",
        "fields": {
            "reference_unit": "USD",
            "redemption": "none",
            "reserve_model": "none",
            "intended_use": "reference-value-accounting",
        },
    },
    "SATROOT-MACHINE-1": {
        "decimals": 0,
        "max_supply": "1000000",
        "initial_balance": "1000000",
        "fields": {
            "service_scope": "api-compute",
            "billing_unit": "request",
            "consumption_model": "burn-on-use",
            "intended_use": "machine-credit",
        },
    },
    "SATROOT-RECEIPT-1": {
        "decimals": 0,
        "max_supply": "1",
        "initial_balance": "1",
        "fields": {
            "document_type": "invoice-receipt",
            "reference_id": "receipt-0001",
            "issuer_entity": "issuer-co",
            "counterparty_entity": "counterparty-co",
            "settlement_unit": "USD",
            "intended_use": "receipt-ledger",
        },
    },
    "SATROOT-IDENTITY-1": {
        "decimals": 0,
        "max_supply": "1",
        "initial_balance": "1",
        "fields": {
            "identity_type": "service-identity",
            "subject_id": "subject-0001",
            "controller_entity": "issuer-co",
            "authority_scope": "api-signing",
            "intended_use": "identity-ledger",
        },
    },
    "SATROOT-LICENSE-1": {
        "decimals": 0,
        "max_supply": "1",
        "initial_balance": "1",
        "fields": {
            "license_type": "software-license",
            "asset_id": "asset-0001",
            "licensor_entity": "issuer-co",
            "licensee_entity": "customer-co",
            "usage_scope": "production-api",
            "intended_use": "license-ledger",
        },
    },
}
SINGLETON_DEMO_PROFILE_DEFAULTS: Dict[str, Dict[str, Optional[str]]] = {
    "SATROOT-RECEIPT-1": {
        "holder_account": "buyer",
        "next_holder": None,
        "archive_account": "archive",
    },
    "SATROOT-IDENTITY-1": {
        "holder_account": "node_alpha",
        "next_holder": "rotated_controller",
        "archive_account": None,
    },
    "SATROOT-LICENSE-1": {
        "holder_account": "customer",
        "next_holder": None,
        "archive_account": "archive",
    },
}
DEMO_CATALOG_BUNDLE_SPECS: tuple[Dict[str, str], ...] = (
    {
        "bundle_name": "stable",
        "profile": "SATROOT-STABLE-1",
        "symbol": "USDCAT1",
        "name": "SATROOT Stable Catalog",
    },
    {
        "bundle_name": "machine",
        "profile": "SATROOT-MACHINE-1",
        "symbol": "APICAT1",
        "name": "SATROOT Machine Catalog",
    },
    {
        "bundle_name": "receipt",
        "profile": "SATROOT-RECEIPT-1",
        "symbol": "RECCAT1",
        "name": "SATROOT Receipt Catalog",
    },
    {
        "bundle_name": "identity",
        "profile": "SATROOT-IDENTITY-1",
        "symbol": "IDCAT1",
        "name": "SATROOT Identity Catalog",
    },
    {
        "bundle_name": "license",
        "profile": "SATROOT-LICENSE-1",
        "symbol": "LICCAT1",
        "name": "SATROOT License Catalog",
    },
)
DEMO_CATALOG_PROFILES: tuple[str, ...] = tuple(spec["profile"] for spec in DEMO_CATALOG_BUNDLE_SPECS)
DEMO_CATALOG_STRUCTURE_OVERRIDE_SPECS: Dict[str, Dict[str, str]] = {
    "SATROOT-STABLE-1": {
        "merchant_account": "account",
        "service_account": "account",
        "initial_balance": "positive_amount",
        "merchant_amount": "positive_amount",
        "service_amount": "positive_amount",
        "merchant_burn_amount": "amount",
    },
    "SATROOT-MACHINE-1": {
        "tenant_account": "account",
        "worker_account": "account",
        "max_supply": "positive_amount",
        "initial_balance": "positive_amount",
        "tenant_amount": "positive_amount",
        "worker_amount": "positive_amount",
        "worker_burn_amount": "amount",
    },
    "SATROOT-RECEIPT-1": {
        "holder_account": "account",
        "next_holder": "optional_account",
        "archive_account": "optional_account",
        "retire": "bool",
    },
    "SATROOT-IDENTITY-1": {
        "holder_account": "account",
        "next_holder": "optional_account",
        "archive_account": "optional_account",
        "retire": "bool",
    },
    "SATROOT-LICENSE-1": {
        "holder_account": "account",
        "next_holder": "optional_account",
        "archive_account": "optional_account",
        "retire": "bool",
    },
}


def _resolve_singleton_demo_accounts(
    profile: str,
    *,
    holder_account: Optional[str] = None,
    next_holder: Optional[str] = None,
    archive_account: Optional[str] = None,
    no_archive: bool = False,
) -> tuple[str, Optional[str], Optional[str]]:
    preset = SINGLETON_DEMO_PROFILE_DEFAULTS[profile]
    resolved_holder = holder_account or preset["holder_account"]
    resolved_next_holder = next_holder if next_holder is not None else preset["next_holder"]
    resolved_archive_account = None if no_archive else (archive_account if archive_account is not None else preset["archive_account"])
    assert resolved_holder is not None
    return resolved_holder, resolved_next_holder, resolved_archive_account


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@functools.lru_cache(maxsize=1)
def load_profile_registry() -> Dict[str, Dict[str, Any]]:
    with PROFILE_REGISTRY_PATH.open("r", encoding="utf-8") as f:
        registry = json.load(f)

    if registry.get("protocol") != "SATROOT-1" or registry.get("version") != "0.1":
        raise SatRootError("unsupported profile registry version")

    profiles = registry.get("profiles")
    if not isinstance(profiles, list):
        raise SatRootError("invalid profile registry format")

    loaded: Dict[str, Dict[str, Any]] = {}
    for entry in profiles:
        if not isinstance(entry, dict):
            raise SatRootError("invalid profile registry entry")
        require_fields(entry, ["profile", "profile_mode", "required_genesis_fields"])
        profile = entry["profile"]
        profile_mode = entry["profile_mode"]
        required_fields = entry["required_genesis_fields"]
        if not isinstance(required_fields, list) or not all(isinstance(field, str) for field in required_fields):
            raise SatRootError(f"invalid required_genesis_fields for {profile!r}")
        loaded[profile] = {
            "profile_mode": profile_mode,
            "required_fields": required_fields,
        }
    return loaded


@functools.lru_cache(maxsize=1)
def load_protocol_schema() -> Dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_bundle_manifest_schema() -> Dict[str, Any]:
    with BUNDLE_MANIFEST_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_bundle_index_schema() -> Dict[str, Any]:
    with BUNDLE_INDEX_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_release_manifest_schema() -> Dict[str, Any]:
    with RELEASE_MANIFEST_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_release_catalog_schema() -> Dict[str, Any]:
    with RELEASE_CATALOG_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_release_catalog_manifest_schema() -> Dict[str, Any]:
    with RELEASE_CATALOG_MANIFEST_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_release_catalog_index_schema() -> Dict[str, Any]:
    with RELEASE_CATALOG_INDEX_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_release_catalog_index_manifest_schema() -> Dict[str, Any]:
    with RELEASE_CATALOG_INDEX_MANIFEST_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_demo_catalog_summary_schema() -> Dict[str, Any]:
    with DEMO_CATALOG_SUMMARY_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_publication_stack_summary_schema() -> Dict[str, Any]:
    with PUBLICATION_STACK_SUMMARY_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_publication_network_summary_schema() -> Dict[str, Any]:
    with PUBLICATION_NETWORK_SUMMARY_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_publication_descriptor_index_schema() -> Dict[str, Any]:
    with PUBLICATION_DESCRIPTOR_INDEX_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_publication_descriptor_index_manifest_schema() -> Dict[str, Any]:
    with PUBLICATION_DESCRIPTOR_INDEX_MANIFEST_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_publication_metadata_manifest_schema() -> Dict[str, Any]:
    with PUBLICATION_METADATA_MANIFEST_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_publication_metadata_catalog_schema() -> Dict[str, Any]:
    with PUBLICATION_METADATA_CATALOG_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_publication_metadata_catalog_manifest_schema() -> Dict[str, Any]:
    with PUBLICATION_METADATA_CATALOG_MANIFEST_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_publication_registry_schema() -> Dict[str, Any]:
    with PUBLICATION_REGISTRY_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_publication_registry_manifest_schema() -> Dict[str, Any]:
    with PUBLICATION_REGISTRY_MANIFEST_SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_scaffold_root_id() -> str:
    return f"{secrets.token_hex(32)}:0"


def build_scaffold_nonce() -> str:
    return f"satroot-scaffold-{secrets.token_hex(8)}"


def scaffold_genesis_record(
    *,
    symbol: str,
    name: str,
    root_id: Optional[str] = None,
    mint_authority: str = "issuer",
    initial_owner: Optional[str] = None,
    decimals: Optional[int] = None,
    max_supply: Optional[str] = None,
    initial_balance: Optional[str] = None,
    profile: Optional[str] = None,
    profile_fields: Optional[Mapping[str, str]] = None,
    rules_hash: Optional[str] = None,
    nonce: Optional[str] = None,
) -> Dict[str, Any]:
    require_account_name(symbol, "symbol")
    require_account_name(name, "name")
    chosen_root_id = root_id or build_scaffold_root_id()
    validate_root_id(chosen_root_id)
    require_account_name(mint_authority, "mint_authority")

    registry = load_profile_registry()
    selected_profile_fields: Dict[str, Any] = {}
    profile_mode: Optional[str] = None
    default_decimals = 0
    default_max_supply = "1000000"
    default_initial_balance = "1000000"

    if profile is not None:
        rules = registry.get(profile)
        if rules is None:
            raise SatRootError(f"unsupported profile: {profile}")
        defaults = PROFILE_SCAFFOLD_DEFAULTS.get(profile)
        if defaults is None:
            raise SatRootError(f"missing scaffold defaults for profile: {profile}")
        profile_mode = rules["profile_mode"]
        selected_profile_fields = copy.deepcopy(defaults["fields"])
        default_decimals = defaults["decimals"]
        default_max_supply = defaults["max_supply"]
        default_initial_balance = defaults["initial_balance"]
        for field_name, value in (profile_fields or {}).items():
            if field_name not in rules["required_fields"]:
                raise SatRootError(f"unsupported profile field override for {profile}: {field_name}")
            selected_profile_fields[field_name] = value
    elif profile_fields:
        raise SatRootError("profile field overrides require --profile")

    chosen_decimals = default_decimals if decimals is None else decimals
    chosen_max_supply = default_max_supply if max_supply is None else max_supply
    chosen_initial_balance = default_initial_balance if initial_balance is None else initial_balance
    owner = mint_authority if initial_owner is None else initial_owner

    genesis = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "action": "genesis",
        "root_id": chosen_root_id,
        "sequence": 0,
        "symbol": symbol,
        "name": name,
        "decimals": chosen_decimals,
        "max_supply": chosen_max_supply,
        "mint_authority": mint_authority,
        "transfer_model": "account-ledger",
        "initial_balances": {
            owner: chosen_initial_balance,
        },
        "nonce": nonce or build_scaffold_nonce(),
    }
    if rules_hash is not None:
        genesis["rules_hash"] = rules_hash
    if profile is not None:
        genesis["profile"] = profile
        genesis["profile_mode"] = profile_mode
        genesis.update(selected_profile_fields)

    apply_genesis(copy.deepcopy(genesis))
    return genesis


def parse_profile_field_overrides(values: Optional[Sequence[str]]) -> Dict[str, str]:
    overrides: Dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise SatRootError(f"invalid profile field override: {value!r}")
        field_name, field_value = value.split("=", 1)
        field_name = field_name.strip()
        if not field_name:
            raise SatRootError(f"invalid profile field override: {value!r}")
        if field_name in overrides:
            raise SatRootError(f"duplicate profile field override: {field_name}")
        overrides[field_name] = field_value
    return overrides


def parse_named_string_overrides(
    values: Optional[Sequence[str]],
    *,
    label: str,
    allowed_keys: Sequence[str],
) -> Dict[str, str]:
    allowed_key_set = set(allowed_keys)
    overrides: Dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise SatRootError(f"invalid {label}: {value!r}")
        key, override_value = value.split("=", 1)
        key = key.strip()
        if not key or key not in allowed_key_set:
            raise SatRootError(f"unsupported {label} key: {key!r}")
        if key in overrides:
            raise SatRootError(f"duplicate {label} key: {key}")
        overrides[key] = override_value
    return overrides


def validate_named_string_override_map(
    values: Optional[Mapping[str, Any]],
    *,
    label: str,
    allowed_keys: Sequence[str],
) -> Dict[str, str]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise SatRootError(f"{label} must contain an object")
    allowed_key_set = set(allowed_keys)
    overrides: Dict[str, str] = {}
    for key, override_value in values.items():
        if not isinstance(key, str) or not key.strip() or key not in allowed_key_set:
            raise SatRootError(f"unsupported {label} key: {key!r}")
        if not isinstance(override_value, str):
            raise SatRootError(f"invalid {label} value for {key}: {override_value!r}")
        if key in overrides:
            raise SatRootError(f"duplicate {label} key: {key}")
        overrides[key] = override_value
    return overrides


def parse_profile_field_override_map(
    values: Optional[Sequence[str]],
    *,
    allowed_profiles: Sequence[str],
) -> Dict[str, Dict[str, str]]:
    allowed_profile_set = set(allowed_profiles)
    registry = load_profile_registry()
    overrides: Dict[str, Dict[str, str]] = {}
    for value in values or []:
        if "=" not in value or ":" not in value:
            raise SatRootError(f"invalid demo catalog profile field override: {value!r}")
        profile_and_field, field_value = value.split("=", 1)
        profile, field_name = profile_and_field.split(":", 1)
        profile = profile.strip()
        field_name = field_name.strip()
        if profile not in allowed_profile_set:
            raise SatRootError(f"unsupported demo catalog profile field override profile: {profile!r}")
        if not field_name:
            raise SatRootError(f"invalid demo catalog profile field override: {value!r}")
        required_fields = registry[profile]["required_fields"]
        if field_name not in required_fields:
            raise SatRootError(f"unsupported demo catalog profile field override for {profile}: {field_name}")
        profile_overrides = overrides.setdefault(profile, {})
        if field_name in profile_overrides:
            raise SatRootError(f"duplicate demo catalog profile field override: {profile}:{field_name}")
        profile_overrides[field_name] = field_value
    return overrides


def validate_profile_field_override_mapping(
    values: Optional[Mapping[str, Any]],
    *,
    allowed_profiles: Sequence[str],
) -> Dict[str, Dict[str, str]]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise SatRootError("demo catalog profile_field_overrides must contain an object")
    allowed_profile_set = set(allowed_profiles)
    registry = load_profile_registry()
    overrides: Dict[str, Dict[str, str]] = {}
    for profile, profile_values in values.items():
        if not isinstance(profile, str) or profile not in allowed_profile_set:
            raise SatRootError(f"unsupported demo catalog profile field override profile: {profile!r}")
        if not isinstance(profile_values, Mapping):
            raise SatRootError(f"demo catalog profile field overrides for {profile} must contain an object")
        required_fields = registry[profile]["required_fields"]
        profile_overrides: Dict[str, str] = {}
        for field_name, field_value in profile_values.items():
            if not isinstance(field_name, str) or not field_name.strip():
                raise SatRootError(f"invalid demo catalog profile field override for {profile}: {field_name!r}")
            if field_name not in required_fields:
                raise SatRootError(f"unsupported demo catalog profile field override for {profile}: {field_name}")
            if not isinstance(field_value, str):
                raise SatRootError(f"invalid demo catalog profile field override for {profile}:{field_name}")
            profile_overrides[field_name] = field_value
        overrides[profile] = profile_overrides
    return overrides


def _parse_demo_catalog_structure_override_value(kind: str, value: Any, *, label: str) -> Any:
    if kind == "account":
        if not isinstance(value, str):
            raise SatRootError(f"invalid {label}: {value!r}")
        return require_account_name(value.strip(), label)
    if kind == "optional_account":
        if value is None:
            return None
        if not isinstance(value, str):
            raise SatRootError(f"invalid {label}: {value!r}")
        normalized = value.strip()
        if normalized.lower() in {"none", "null"}:
            return None
        return require_account_name(normalized, label)
    if kind == "positive_amount":
        if isinstance(value, int) and not isinstance(value, bool):
            return str(parse_positive_amount(str(value)))
        if isinstance(value, str):
            return str(parse_positive_amount(value))
        raise SatRootError(f"invalid {label}: {value!r}")
    if kind == "amount":
        if isinstance(value, int) and not isinstance(value, bool):
            return str(parse_amount(str(value)))
        if isinstance(value, str):
            return str(parse_amount(value))
        raise SatRootError(f"invalid {label}: {value!r}")
    if kind == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in {0, 1}:
                return bool(value)
            raise SatRootError(f"invalid {label}: {value!r}")
        if not isinstance(value, str):
            raise SatRootError(f"invalid {label}: {value!r}")
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
        raise SatRootError(f"invalid {label}: {value!r}")
    raise SatRootError(f"unsupported demo catalog structure override kind: {kind}")


def parse_profile_structure_override_map(
    values: Optional[Sequence[str]],
    *,
    allowed_profiles: Sequence[str],
) -> Dict[str, Dict[str, Any]]:
    allowed_profile_set = set(allowed_profiles)
    overrides: Dict[str, Dict[str, Any]] = {}
    for value in values or []:
        if "=" not in value or ":" not in value:
            raise SatRootError(f"invalid demo catalog structure override: {value!r}")
        profile_and_key, override_value = value.split("=", 1)
        profile, override_key = profile_and_key.split(":", 1)
        profile = profile.strip()
        override_key = override_key.strip()
        if profile not in allowed_profile_set:
            raise SatRootError(f"unsupported demo catalog structure override profile: {profile!r}")
        if not override_key:
            raise SatRootError(f"invalid demo catalog structure override: {value!r}")
        profile_specs = DEMO_CATALOG_STRUCTURE_OVERRIDE_SPECS.get(profile, {})
        if override_key not in profile_specs:
            raise SatRootError(f"unsupported demo catalog structure override for {profile}: {override_key}")
        profile_overrides = overrides.setdefault(profile, {})
        if override_key in profile_overrides:
            raise SatRootError(f"duplicate demo catalog structure override: {profile}:{override_key}")
        profile_overrides[override_key] = _parse_demo_catalog_structure_override_value(
            profile_specs[override_key],
            override_value,
            label=f"demo catalog structure override {profile}:{override_key}",
        )
    return overrides


def validate_profile_structure_override_mapping(
    values: Optional[Mapping[str, Any]],
    *,
    allowed_profiles: Sequence[str],
) -> Dict[str, Dict[str, Any]]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise SatRootError("demo catalog profile_structure_overrides must contain an object")
    allowed_profile_set = set(allowed_profiles)
    overrides: Dict[str, Dict[str, Any]] = {}
    for profile, profile_values in values.items():
        if not isinstance(profile, str) or profile not in allowed_profile_set:
            raise SatRootError(f"unsupported demo catalog structure override profile: {profile!r}")
        if not isinstance(profile_values, Mapping):
            raise SatRootError(f"demo catalog structure overrides for {profile} must contain an object")
        profile_specs = DEMO_CATALOG_STRUCTURE_OVERRIDE_SPECS.get(profile, {})
        profile_overrides: Dict[str, Any] = {}
        for override_key, override_value in profile_values.items():
            if not isinstance(override_key, str) or not override_key.strip():
                raise SatRootError(f"invalid demo catalog structure override for {profile}: {override_key!r}")
            if override_key not in profile_specs:
                raise SatRootError(f"unsupported demo catalog structure override for {profile}: {override_key}")
            profile_overrides[override_key] = _parse_demo_catalog_structure_override_value(
                profile_specs[override_key],
                override_value,
                label=f"demo catalog structure override {profile}:{override_key}",
            )
        overrides[profile] = profile_overrides
    return overrides


def validate_release_metadata_mapping(values: Optional[Mapping[str, Any]]) -> Dict[str, str]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise SatRootError("demo catalog release metadata must contain an object")
    allowed_keys = {"channel", "label", "published_at"}
    metadata: Dict[str, str] = {}
    for key, value in values.items():
        if not isinstance(key, str) or key not in allowed_keys:
            raise SatRootError(f"unsupported demo catalog release metadata key: {key!r}")
        if not isinstance(value, str):
            raise SatRootError(f"invalid demo catalog release metadata value for {key}: {value!r}")
        metadata[key] = value
    return metadata


def _validate_string_sequence(values: Any, *, label: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values):
        raise SatRootError(f"{label} must contain an array of non-empty strings")
    return list(values)


def load_demo_catalog_preset(path: str | Path) -> Dict[str, Any]:
    preset = _load_json_object_file(str(path), label="demo catalog preset")
    if preset.get("type") != "SATROOT-DEMO-CATALOG-PRESET":
        raise SatRootError("unsupported demo catalog preset type")
    if preset.get("version") != "0.1":
        raise SatRootError("unsupported demo catalog preset version")

    allowed_keys = {
        "type",
        "version",
        "profiles",
        "symbol_overrides",
        "name_overrides",
        "profile_field_overrides",
        "profile_structure_overrides",
        "release",
    }
    unexpected = set(preset) - allowed_keys
    if unexpected:
        raise SatRootError(f"unsupported demo catalog preset keys: {sorted(unexpected)}")

    profiles = preset.get("profiles")
    if profiles is not None:
        if not isinstance(profiles, list) or not all(isinstance(value, str) for value in profiles):
            raise SatRootError("demo catalog preset profiles must contain an array of strings")
        if len(set(profiles)) != len(profiles):
            raise SatRootError("demo catalog preset profiles must not contain duplicates")

    return {
        "profiles": profiles,
        "symbol_overrides": validate_named_string_override_map(
            preset.get("symbol_overrides"),
            label="demo catalog symbol override",
            allowed_keys=DEMO_CATALOG_PROFILES,
        ),
        "name_overrides": validate_named_string_override_map(
            preset.get("name_overrides"),
            label="demo catalog name override",
            allowed_keys=DEMO_CATALOG_PROFILES,
        ),
        "profile_field_overrides": validate_profile_field_override_mapping(
            preset.get("profile_field_overrides"),
            allowed_profiles=DEMO_CATALOG_PROFILES,
        ),
        "profile_structure_overrides": validate_profile_structure_override_mapping(
            preset.get("profile_structure_overrides"),
            allowed_profiles=DEMO_CATALOG_PROFILES,
        ),
        "release_metadata": validate_release_metadata_mapping(preset.get("release")),
    }


def load_release_catalog_preset(path: str | Path) -> Dict[str, Any]:
    preset_path = Path(path).resolve()
    preset = _load_json_object_file(str(preset_path), label="release catalog preset")
    if preset.get("type") != "SATROOT-RELEASE-CATALOG-PRESET":
        raise SatRootError("unsupported release catalog preset type")
    if preset.get("version") != "0.1":
        raise SatRootError("unsupported release catalog preset version")

    allowed_keys = {
        "type",
        "version",
        "release_dirs",
        "discover_under",
        "recursive",
        "catalog",
    }
    unexpected = set(preset) - allowed_keys
    if unexpected:
        raise SatRootError(f"unsupported release catalog preset keys: {sorted(unexpected)}")

    release_dirs = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(preset.get("release_dirs"), label="release catalog preset release_dirs")
    ]
    discover_under = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(preset.get("discover_under"), label="release catalog preset discover_under")
    ]
    recursive = preset.get("recursive", True)
    if not isinstance(recursive, bool):
        raise SatRootError("release catalog preset recursive must be a boolean")

    return {
        "release_dirs": release_dirs,
        "discover_under": discover_under,
        "recursive": recursive,
        "catalog_metadata": validate_release_metadata_mapping(preset.get("catalog")),
    }


def load_publication_stack_preset(path: str | Path) -> Dict[str, Any]:
    preset_path = Path(path).resolve()
    preset = _load_json_object_file(str(preset_path), label="publication stack preset")
    if preset.get("type") != "SATROOT-PUBLICATION-STACK-PRESET":
        raise SatRootError("unsupported publication stack preset type")
    if preset.get("version") != "0.1":
        raise SatRootError("unsupported publication stack preset version")

    allowed_keys = {
        "type",
        "version",
        "catalog_presets",
        "release_catalog",
    }
    unexpected = set(preset) - allowed_keys
    if unexpected:
        raise SatRootError(f"unsupported publication stack preset keys: {sorted(unexpected)}")

    catalog_preset_paths = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(preset.get("catalog_presets"), label="publication stack preset catalog_presets")
    ]
    if not catalog_preset_paths:
        raise SatRootError("publication stack preset must contain at least one catalog_preset")

    return {
        "catalog_preset_paths": catalog_preset_paths,
        "release_catalog_metadata": validate_release_metadata_mapping(preset.get("release_catalog")),
    }


def load_publication_network_preset(path: str | Path) -> Dict[str, Any]:
    preset_path = Path(path).resolve()
    preset = _load_json_object_file(str(preset_path), label="publication network preset")
    if preset.get("type") != "SATROOT-PUBLICATION-NETWORK-PRESET":
        raise SatRootError("unsupported publication network preset type")
    if preset.get("version") != "0.1":
        raise SatRootError("unsupported publication network preset version")

    allowed_keys = {
        "type",
        "version",
        "stack_presets",
        "release_catalog_index",
    }
    unexpected = set(preset) - allowed_keys
    if unexpected:
        raise SatRootError(f"unsupported publication network preset keys: {sorted(unexpected)}")

    stack_preset_paths = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(preset.get("stack_presets"), label="publication network preset stack_presets")
    ]
    if not stack_preset_paths:
        raise SatRootError("publication network preset must contain at least one stack_preset")

    return {
        "stack_preset_paths": stack_preset_paths,
        "release_catalog_index_metadata": validate_release_metadata_mapping(preset.get("release_catalog_index")),
    }


def load_release_catalog_index_preset(path: str | Path) -> Dict[str, Any]:
    preset_path = Path(path).resolve()
    preset = _load_json_object_file(str(preset_path), label="release catalog index preset")
    if preset.get("type") != "SATROOT-RELEASE-CATALOG-INDEX-PRESET":
        raise SatRootError("unsupported release catalog index preset type")
    if preset.get("version") != "0.1":
        raise SatRootError("unsupported release catalog index preset version")

    allowed_keys = {
        "type",
        "version",
        "release_catalog_dirs",
        "discover_under",
        "recursive",
        "index",
    }
    unexpected = set(preset) - allowed_keys
    if unexpected:
        raise SatRootError(f"unsupported release catalog index preset keys: {sorted(unexpected)}")

    release_catalog_dirs = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(
            preset.get("release_catalog_dirs"),
            label="release catalog index preset release_catalog_dirs",
        )
    ]
    discover_under = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(
            preset.get("discover_under"),
            label="release catalog index preset discover_under",
        )
    ]
    recursive = preset.get("recursive", True)
    if not isinstance(recursive, bool):
        raise SatRootError("release catalog index preset recursive must be a boolean")

    return {
        "release_catalog_dirs": release_catalog_dirs,
        "discover_under": discover_under,
        "recursive": recursive,
        "index_metadata": validate_release_metadata_mapping(preset.get("index")),
    }


def load_publication_descriptor_index_preset(path: str | Path) -> Dict[str, Any]:
    preset_path = Path(path).resolve()
    preset = _load_json_object_file(str(preset_path), label="publication descriptor index preset")
    if preset.get("type") != "SATROOT-PUBLICATION-DESCRIPTOR-INDEX-PRESET":
        raise SatRootError("unsupported publication descriptor index preset type")
    if preset.get("version") != "0.1":
        raise SatRootError("unsupported publication descriptor index preset version")

    allowed_keys = {
        "type",
        "version",
        "artifact_paths",
        "discover_under",
        "recursive",
        "index",
    }
    unexpected = set(preset) - allowed_keys
    if unexpected:
        raise SatRootError(f"unsupported publication descriptor index preset keys: {sorted(unexpected)}")

    artifact_paths = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(
            preset.get("artifact_paths"),
            label="publication descriptor index preset artifact_paths",
        )
    ]
    discover_under = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(
            preset.get("discover_under"),
            label="publication descriptor index preset discover_under",
        )
    ]
    recursive = preset.get("recursive", True)
    if not isinstance(recursive, bool):
        raise SatRootError("publication descriptor index preset recursive must be a boolean")
    if not artifact_paths and not discover_under:
        raise SatRootError("publication descriptor index preset must contain at least one artifact_path or discover_under path")

    return {
        "artifact_paths": artifact_paths,
        "discover_under": discover_under,
        "recursive": recursive,
        "index_metadata": validate_release_metadata_mapping(preset.get("index")),
    }


def load_publication_metadata_catalog_preset(path: str | Path) -> Dict[str, Any]:
    preset_path = Path(path).resolve()
    preset = _load_json_object_file(str(preset_path), label="publication metadata catalog preset")
    if preset.get("type") != "SATROOT-PUBLICATION-METADATA-CATALOG-PRESET":
        raise SatRootError("unsupported publication metadata catalog preset type")
    if preset.get("version") != "0.1":
        raise SatRootError("unsupported publication metadata catalog preset version")

    allowed_keys = {
        "type",
        "version",
        "publication_metadata_bundle_dirs",
        "discover_under",
        "recursive",
        "catalog",
    }
    unexpected = set(preset) - allowed_keys
    if unexpected:
        raise SatRootError(f"unsupported publication metadata catalog preset keys: {sorted(unexpected)}")

    publication_metadata_bundle_dirs = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(
            preset.get("publication_metadata_bundle_dirs"),
            label="publication metadata catalog preset publication_metadata_bundle_dirs",
        )
    ]
    discover_under = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(
            preset.get("discover_under"),
            label="publication metadata catalog preset discover_under",
        )
    ]
    recursive = preset.get("recursive", True)
    if not isinstance(recursive, bool):
        raise SatRootError("publication metadata catalog preset recursive must be a boolean")
    if not publication_metadata_bundle_dirs and not discover_under:
        raise SatRootError(
            "publication metadata catalog preset must contain at least one publication_metadata_bundle_dir or discover_under path"
        )

    return {
        "publication_metadata_bundle_dirs": publication_metadata_bundle_dirs,
        "discover_under": discover_under,
        "recursive": recursive,
        "catalog_metadata": validate_release_metadata_mapping(preset.get("catalog")),
    }


def load_publication_registry_preset(path: str | Path) -> Dict[str, Any]:
    preset_path = Path(path).resolve()
    preset = _load_json_object_file(str(preset_path), label="publication registry preset")
    if preset.get("type") != "SATROOT-PUBLICATION-REGISTRY-PRESET":
        raise SatRootError("unsupported publication registry preset type")
    if preset.get("version") != "0.1":
        raise SatRootError("unsupported publication registry preset version")

    allowed_keys = {
        "type",
        "version",
        "release_catalog_index_dir",
        "publication_descriptor_index_dir",
        "publication_metadata_catalog_dir",
        "registry",
    }
    unexpected = set(preset) - allowed_keys
    if unexpected:
        raise SatRootError(f"unsupported publication registry preset keys: {sorted(unexpected)}")

    def resolve_optional_path(key: str) -> Optional[str]:
        value = preset.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise SatRootError(f"publication registry preset {key} must be a non-empty string when provided")
        return str((preset_path.parent / value).resolve())

    release_catalog_index_dir = resolve_optional_path("release_catalog_index_dir")
    publication_descriptor_index_dir = resolve_optional_path("publication_descriptor_index_dir")
    publication_metadata_catalog_dir = resolve_optional_path("publication_metadata_catalog_dir")
    if not any((release_catalog_index_dir, publication_descriptor_index_dir, publication_metadata_catalog_dir)):
        raise SatRootError("publication registry preset must contain at least one publication component directory")

    return {
        "release_catalog_index_dir": release_catalog_index_dir,
        "publication_descriptor_index_dir": publication_descriptor_index_dir,
        "publication_metadata_catalog_dir": publication_metadata_catalog_dir,
        "registry_metadata": validate_release_metadata_mapping(preset.get("registry")),
    }


def load_publication_registry_workspace_preset(path: str | Path) -> Dict[str, Any]:
    preset_path = Path(path).resolve()
    preset = _load_json_object_file(str(preset_path), label="publication registry workspace preset")
    if preset.get("type") != "SATROOT-PUBLICATION-REGISTRY-WORKSPACE-PRESET":
        raise SatRootError("unsupported publication registry workspace preset type")
    if preset.get("version") != "0.1":
        raise SatRootError("unsupported publication registry workspace preset version")

    allowed_keys = {
        "type",
        "version",
        "artifact_paths",
        "discover_under",
        "recursive",
        "publication_network_dir",
        "release_catalog_index_dir",
        "publication_descriptor_index",
        "publication_metadata_catalog",
        "publication_registry",
    }
    unexpected = set(preset) - allowed_keys
    if unexpected:
        raise SatRootError(f"unsupported publication registry workspace preset keys: {sorted(unexpected)}")

    artifact_paths = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(
            preset.get("artifact_paths"),
            label="publication registry workspace preset artifact_paths",
        )
    ]
    discover_under = [
        str((preset_path.parent / entry).resolve())
        for entry in _validate_string_sequence(
            preset.get("discover_under"),
            label="publication registry workspace preset discover_under",
        )
    ]
    recursive = preset.get("recursive", True)
    if not isinstance(recursive, bool):
        raise SatRootError("publication registry workspace preset recursive must be a boolean")

    def resolve_optional_path(key: str) -> Optional[str]:
        value = preset.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise SatRootError(f"publication registry workspace preset {key} must be a non-empty string when provided")
        return str((preset_path.parent / value).resolve())

    publication_network_dir = resolve_optional_path("publication_network_dir")
    release_catalog_index_dir = resolve_optional_path("release_catalog_index_dir")
    if not artifact_paths and not discover_under and publication_network_dir is None:
        raise SatRootError(
            "publication registry workspace preset must contain artifact_paths, discover_under, or publication_network_dir"
        )
    if release_catalog_index_dir is None and publication_network_dir is None:
        raise SatRootError(
            "publication registry workspace preset must contain release_catalog_index_dir or publication_network_dir"
        )

    return {
        "artifact_paths": artifact_paths,
        "discover_under": discover_under,
        "recursive": recursive,
        "publication_network_dir": publication_network_dir,
        "release_catalog_index_dir": release_catalog_index_dir,
        "descriptor_index_metadata": validate_release_metadata_mapping(preset.get("publication_descriptor_index")),
        "publication_metadata_catalog_metadata": validate_release_metadata_mapping(preset.get("publication_metadata_catalog")),
        "publication_registry_metadata": validate_release_metadata_mapping(preset.get("publication_registry")),
    }


def _unique_workspace_names(paths: Sequence[str | Path]) -> list[str]:
    used: Dict[str, int] = {}
    names: list[str] = []
    for value in paths:
        stem = Path(value).stem or "workspace"
        count = used.get(stem, 0)
        used[stem] = count + 1
        names.append(stem if count == 0 else f"{stem}-{count + 1}")
    return names


def _copy_workspace_directory(source_dir: str | Path, target_dir: str | Path, *, label: str) -> Path:
    source_path = Path(source_dir).resolve()
    target_path = Path(target_dir).resolve()
    if not source_path.is_dir():
        raise SatRootError(f"{label} directory must be an existing directory")
    if target_path.exists():
        raise SatRootError(f"refusing to overwrite existing {label} target directory: {target_path}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_path, target_path)
    return target_path


def _require_consistent_workspace_scheme(
    summaries: Sequence[Mapping[str, Any]],
    *,
    field_name: str,
    label: str,
) -> str:
    values = {
        str(summary.get(field_name))
        for summary in summaries
        if isinstance(summary.get(field_name), str) and str(summary.get(field_name)).strip()
    }
    if not values:
        raise SatRootError(f"{label} requires at least one non-empty {field_name}")
    if len(values) != 1:
        raise SatRootError(f"{label} requires a consistent {field_name} across all nested workspaces")
    return next(iter(values))


def scaffold_event_record(
    *,
    action: str,
    root_id: str,
    sequence: int,
    prev_event_id: str,
    signer: str,
    from_account: Optional[str] = None,
    to_account: Optional[str] = None,
    amount: Optional[str] = None,
    new_mint_authority: Optional[str] = None,
    profile: Optional[str] = None,
    profile_mode: Optional[str] = None,
) -> Dict[str, Any]:
    validate_root_id(root_id)
    if not isinstance(sequence, int) or sequence <= 0:
        raise SatRootError(f"invalid event sequence: {sequence!r}")
    if not isinstance(prev_event_id, str) or not prev_event_id.startswith("sha256:"):
        raise SatRootError(f"invalid prev_event_id: {prev_event_id!r}")
    require_account_name(signer, "signer")

    event: Dict[str, Any] = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "action": action,
        "root_id": root_id,
        "sequence": sequence,
        "prev_event_id": prev_event_id,
        "signer": signer,
        "signature": "demo",
    }
    if profile is not None:
        event["profile"] = profile
    if profile_mode is not None:
        event["profile_mode"] = profile_mode

    if action == "mint":
        require_account_name(to_account, "to")
        parse_positive_amount(amount or "")
        event["to"] = to_account
        event["amount"] = amount
    elif action == "transfer":
        require_account_name(from_account, "from")
        require_account_name(to_account, "to")
        parse_positive_amount(amount or "")
        event["from"] = from_account
        event["to"] = to_account
        event["amount"] = amount
    elif action == "burn":
        require_account_name(from_account, "from")
        parse_positive_amount(amount or "")
        event["from"] = from_account
        event["amount"] = amount
    elif action == "rotate-authority":
        require_account_name(new_mint_authority, "new_mint_authority")
        event["new_mint_authority"] = new_mint_authority
    else:
        raise SatRootError(f"unsupported scaffold action: {action}")

    return event


def scaffold_event_from_ledger(
    events: Sequence[Dict[str, Any]],
    *,
    action: str,
    signer: str,
    from_account: Optional[str] = None,
    to_account: Optional[str] = None,
    amount: Optional[str] = None,
    new_mint_authority: Optional[str] = None,
    verifier: Optional[SignatureVerifier] = None,
) -> Dict[str, Any]:
    if not events:
        raise SatRootError("empty ledger")
    if verifier is None:
        verifier = demo_signature_verifier
    state = replay(events, verifier=verifier)
    last_event = events[-1]
    profile = state.profile
    profile_mode = state.profile_mode
    return scaffold_event_record(
        action=action,
        root_id=state.root_id,
        sequence=state.sequence + 1,
        prev_event_id=event_id(last_event),
        signer=signer,
        from_account=from_account,
        to_account=to_account,
        amount=amount,
        new_mint_authority=new_mint_authority,
        profile=profile,
        profile_mode=profile_mode,
    )


def scaffold_machine_credit_consumption_event(
    events: Sequence[Dict[str, Any]],
    *,
    signer: str,
    amount: str,
    from_account: Optional[str] = None,
    verifier: Optional[SignatureVerifier] = None,
) -> Dict[str, Any]:
    if verifier is None:
        verifier = demo_signature_verifier
    state = replay(events, verifier=verifier)
    if state.profile != "SATROOT-MACHINE-1" or state.profile_mode != "prepaid-credit":
        raise SatRootError("machine credit consumption requires a SATROOT-MACHINE-1 prepaid-credit ledger")
    consumption_model = state.genesis_metadata.get("consumption_model")
    if consumption_model != "burn-on-use":
        raise SatRootError("machine credit consumption requires consumption_model=burn-on-use")
    burner = signer if from_account is None else from_account
    return scaffold_event_from_ledger(
        events,
        action="burn",
        signer=signer,
        from_account=burner,
        amount=amount,
        verifier=verifier,
    )


_SINGLETON_OBJECT_PROFILES = {
    ("SATROOT-RECEIPT-1", "single-receipt"),
    ("SATROOT-IDENTITY-1", "single-identity"),
    ("SATROOT-LICENSE-1", "single-license"),
}


def _resolve_singleton_object_holder(
    events: Sequence[Dict[str, Any]],
    *,
    verifier: Optional[SignatureVerifier] = None,
    operation_label: str,
) -> str:
    if verifier is None:
        verifier = demo_signature_verifier
    state = replay(events, verifier=verifier)
    if (state.profile, state.profile_mode) not in _SINGLETON_OBJECT_PROFILES:
        raise SatRootError(f"singleton object {operation_label} requires a SATROOT receipt, identity, or license ledger")
    if state.supply != 1:
        raise SatRootError(f"singleton object {operation_label} requires exactly one live unit")

    holders = [account for account, balance in state.balances.items() if balance != 0]
    if len(holders) != 1 or state.balances.get(holders[0]) != 1:
        raise SatRootError(f"singleton object {operation_label} requires exactly one active holder with one unit")
    return holders[0]


def scaffold_singleton_object_transfer_event(
    events: Sequence[Dict[str, Any]],
    *,
    signer: str,
    to_account: str,
    from_account: Optional[str] = None,
    verifier: Optional[SignatureVerifier] = None,
) -> Dict[str, Any]:
    current_holder = _resolve_singleton_object_holder(events, verifier=verifier, operation_label="transfer")
    source = current_holder if from_account is None else require_account_name(from_account, "from_account")
    target = require_account_name(to_account, "to_account")
    if source != current_holder:
        raise SatRootError("transfer source must match the current active holder")
    if signer != source:
        raise SatRootError("transfer helper requires signer to match the current active holder")
    if target == current_holder:
        raise SatRootError("singleton object is already held by the requested account")

    return scaffold_event_from_ledger(
        events,
        action="transfer",
        signer=signer,
        from_account=source,
        to_account=target,
        amount="1",
        verifier=verifier,
    )


def scaffold_singleton_object_archive_event(
    events: Sequence[Dict[str, Any]],
    *,
    signer: str,
    archive_account: str = "archive",
    from_account: Optional[str] = None,
    verifier: Optional[SignatureVerifier] = None,
) -> Dict[str, Any]:
    current_holder = _resolve_singleton_object_holder(events, verifier=verifier, operation_label="archival")
    source = current_holder if from_account is None else require_account_name(from_account, "from_account")
    target = require_account_name(archive_account, "archive_account")
    if source != current_holder:
        raise SatRootError("archive source must match the current active holder")
    if signer != source:
        raise SatRootError("archive helper requires signer to match the current active holder")
    if target == current_holder:
        raise SatRootError("singleton object is already archived to the requested account")

    return scaffold_event_from_ledger(
        events,
        action="transfer",
        signer=signer,
        from_account=source,
        to_account=target,
        amount="1",
        verifier=verifier,
    )


def scaffold_singleton_object_retirement_event(
    events: Sequence[Dict[str, Any]],
    *,
    signer: str,
    from_account: str = "archive",
    verifier: Optional[SignatureVerifier] = None,
) -> Dict[str, Any]:
    current_holder = _resolve_singleton_object_holder(events, verifier=verifier, operation_label="retirement")
    source = require_account_name(from_account, "from_account")
    if current_holder != source:
        raise SatRootError("singleton object retirement requires the archived unit to be held by the requested source account")
    if signer != source:
        raise SatRootError("retirement helper requires signer to match the current archived holder")

    return scaffold_event_from_ledger(
        events,
        action="burn",
        signer=signer,
        from_account=source,
        amount="1",
        verifier=verifier,
    )


def _resolve_event_signing_key_id(
    event: Mapping[str, Any],
    *,
    explicit_key_id: Optional[str] = None,
    signer_key_ids: Optional[Mapping[str, str]] = None,
) -> str:
    if isinstance(explicit_key_id, str) and explicit_key_id.strip():
        return explicit_key_id
    signer_name = event.get("signer")
    if isinstance(signer_name, str) and signer_key_ids is not None:
        key_id = signer_key_ids.get(signer_name)
        if isinstance(key_id, str) and key_id.strip():
            return key_id
    raise SatRootError("non-demo event append requires --key-id or --signer-key-map-json")


def append_signed_event_to_ledger(
    events: Sequence[Dict[str, Any]],
    event: Mapping[str, Any],
    *,
    scheme: str,
    explicit_key_id: Optional[str] = None,
    signer_key_ids: Optional[Mapping[str, str]] = None,
    signer: Optional[SignerFunction] = None,
    verifier: Optional[SignatureVerifier] = None,
    include_state_hash: bool = False,
) -> list[Dict[str, Any]]:
    if not events:
        raise SatRootError("empty ledger")
    if verifier is None:
        verifier = demo_signature_verifier

    appended_events = copy.deepcopy(list(events))
    unsigned_event = copy.deepcopy(dict(event))
    if scheme == "demo":
        signed_event = sign_event_record(unsigned_event, scheme="demo")
    else:
        key_id = _resolve_event_signing_key_id(unsigned_event, explicit_key_id=explicit_key_id, signer_key_ids=signer_key_ids)
        signed_event = sign_event_record(unsigned_event, scheme=scheme, key_id=key_id, signer=signer)

    state = replay(appended_events, verifier=verifier)
    next_state = apply_event(state, signed_event, verifier=verifier)
    if include_state_hash:
        signed_event["state_hash"] = next_state.state_hash()
    appended_events.append(signed_event)
    return appended_events


def event_id(event: Dict[str, Any]) -> str:
    """Return the canonical event hash.

    The event_id excludes `event_id` and `state_hash` if present so records can
    carry their own ID while still attaching a post-application state commitment.
    """
    cleaned = {k: v for k, v in event.items() if k not in {"event_id", "state_hash"}}
    return "sha256:" + sha256_hex(canonical_json(cleaned))


def signing_payload(event: Dict[str, Any]) -> str:
    """Return the canonical payload that should be signed for an event.

    Signature material excludes fields that are either transport metadata or
    post-application commitments.
    """
    cleaned = {k: v for k, v in event.items() if k not in {"signature", "event_id", "state_hash"}}
    return canonical_json(cleaned)


def parse_amount(value: str) -> int:
    if not isinstance(value, str) or not value.isdigit():
        raise SatRootError(f"invalid amount: {value!r}")
    return int(value)


def demo_signature_verifier(event: Dict[str, Any], payload: str) -> bool:
    """Default demo verifier used by the reference engine.

    v0.1 test records may use signature='demo'. Production records must use
    a real signature scheme over `signing_payload(event)`.
    """
    return event.get("signature_scheme", "demo") == "demo" and event.get("signature") == "demo"


def _coerce_secret(secret: str | bytes) -> bytes:
    if isinstance(secret, bytes):
        return secret
    if isinstance(secret, str):
        return secret.encode("utf-8")
    raise SatRootError("unsupported secret type")


def hmac_sha256_sign(payload: str, secret: str | bytes) -> str:
    secret_bytes = _coerce_secret(secret)
    digest = hmac.new(secret_bytes, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return "hmac-sha256:" + digest


def make_hmac_sha256_verifier(shared_secrets: Mapping[str, str | bytes]) -> SignatureVerifier:
    """Build a reference verifier for shared-secret HMAC signatures.

    This is useful for controlled environments and integration testing.
    It is not a public-key signature scheme.
    """

    def verifier(event: Dict[str, Any], payload: str) -> bool:
        if event.get("signature_scheme") != "hmac-sha256":
            return False
        key_id = event.get("signature_key_id")
        if not isinstance(key_id, str) or not key_id:
            return False
        secret = shared_secrets.get(key_id)
        if secret is None:
            return False
        expected = hmac_sha256_sign(payload, secret)
        signature = event.get("signature")
        return isinstance(signature, str) and hmac.compare_digest(signature, expected)

    return verifier


def ed25519_available() -> bool:
    return importlib.util.find_spec("cryptography") is not None


def _load_ed25519_primitives() -> tuple[Any, Any, Any]:
    if not ed25519_available():
        raise SatRootError("cryptography package is required for ed25519 support")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

    return Ed25519PrivateKey, Ed25519PublicKey, serialization


def _coerce_hex_bytes(value: str, label: str, expected_length: Optional[int] = None) -> bytes:
    if not isinstance(value, str):
        raise SatRootError(f"{label} must be a hex string")
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise SatRootError(f"invalid hex for {label}") from exc
    if expected_length is not None and len(raw) != expected_length:
        raise SatRootError(f"invalid byte length for {label}")
    return raw


def ed25519_public_key_hex(private_key_hex: str) -> str:
    Ed25519PrivateKey, _, serialization = _load_ed25519_primitives()
    private_key = Ed25519PrivateKey.from_private_bytes(_coerce_hex_bytes(private_key_hex, "private_key_hex", 32))
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return public_bytes.hex()


def ed25519_sign(payload: str, private_key_hex: str) -> str:
    Ed25519PrivateKey, _, _ = _load_ed25519_primitives()
    private_key = Ed25519PrivateKey.from_private_bytes(_coerce_hex_bytes(private_key_hex, "private_key_hex", 32))
    signature = private_key.sign(payload.encode("utf-8"))
    return "ed25519:" + signature.hex()


def make_ed25519_verifier(public_keys: Mapping[str, str]) -> SignatureVerifier:
    """Build a reference verifier for Ed25519 signatures.

    This path requires the optional `cryptography` dependency and uses raw
    32-byte public keys encoded as lowercase hex strings.
    """
    _, Ed25519PublicKey, _ = _load_ed25519_primitives()

    def verifier(event: Dict[str, Any], payload: str) -> bool:
        if event.get("signature_scheme") != "ed25519":
            return False
        key_id = event.get("signature_key_id")
        if not isinstance(key_id, str) or not key_id:
            return False
        public_key_hex = public_keys.get(key_id)
        if public_key_hex is None:
            return False
        signature = event.get("signature")
        if not isinstance(signature, str) or not signature.startswith("ed25519:"):
            return False
        try:
            public_key = Ed25519PublicKey.from_public_bytes(_coerce_hex_bytes(public_key_hex, "public_key_hex", 32))
            signature_bytes = _coerce_hex_bytes(signature.split(":", 1)[1], "signature", 64)
            public_key.verify(signature_bytes, payload.encode("utf-8"))
            return True
        except Exception:
            return False

    return verifier


def make_hmac_sha256_signer(shared_secrets: Mapping[str, str | bytes]) -> SignerFunction:
    def signer(payload: str, key_id: str) -> str:
        secret = shared_secrets.get(key_id)
        if secret is None:
            raise SatRootError(f"missing secret for key_id: {key_id}")
        return hmac_sha256_sign(payload, secret)

    return signer


def make_ed25519_signer(private_keys: Mapping[str, str]) -> SignerFunction:
    def signer(payload: str, key_id: str) -> str:
        private_key_hex = private_keys.get(key_id)
        if private_key_hex is None:
            raise SatRootError(f"missing private key for key_id: {key_id}")
        return ed25519_sign(payload, private_key_hex)

    return signer


def derive_ed25519_public_keys(private_keys: Mapping[str, str]) -> Dict[str, str]:
    return {key_id: ed25519_public_key_hex(private_key_hex) for key_id, private_key_hex in private_keys.items()}


def generate_ed25519_private_keys(key_ids: Iterable[str]) -> Dict[str, str]:
    generated: Dict[str, str] = {}
    for key_id in key_ids:
        if not isinstance(key_id, str) or not key_id.strip():
            raise SatRootError(f"invalid key_id: {key_id!r}")
        if key_id in generated:
            raise SatRootError(f"duplicate key_id: {key_id}")
        generated[key_id] = secrets.token_bytes(32).hex()
    if not generated:
        raise SatRootError("at least one key_id is required")
    return generated


def generate_hmac_shared_secrets(key_ids: Iterable[str]) -> Dict[str, str]:
    generated: Dict[str, str] = {}
    for key_id in key_ids:
        if not isinstance(key_id, str) or not key_id.strip():
            raise SatRootError(f"invalid key_id: {key_id!r}")
        if key_id in generated:
            raise SatRootError(f"duplicate key_id: {key_id}")
        generated[key_id] = secrets.token_hex(32)
    if not generated:
        raise SatRootError("at least one key_id is required")
    return generated


def bootstrap_release_hmac_material(key_ids: Iterable[str]) -> Dict[str, Dict[str, str]]:
    shared_secrets = generate_hmac_shared_secrets(key_ids)
    return {"shared_secrets": shared_secrets}


def bootstrap_release_ed25519_material(key_ids: Iterable[str]) -> Dict[str, Dict[str, str]]:
    private_keys = generate_ed25519_private_keys(key_ids)
    public_keys = derive_ed25519_public_keys(private_keys)
    return {
        "private_keys": private_keys,
        "public_keys": public_keys,
    }


def build_signer_key_map(
    events: Sequence[Dict[str, Any]],
    *,
    key_prefix: str = "",
    key_suffix: str = "-key",
) -> Dict[str, str]:
    if not events:
        raise SatRootError("empty ledger")

    signer_key_map: Dict[str, str] = {}
    for index, event in enumerate(events[1:], start=1):
        signer = event.get("signer")
        if not isinstance(signer, str) or not signer.strip():
            raise SatRootError(f"missing or invalid signer at record {index}")
        signer_key_map.setdefault(signer, f"{key_prefix}{signer}{key_suffix}")

    if not signer_key_map:
        raise SatRootError("no non-genesis signer records found")
    return signer_key_map


def bootstrap_ed25519_workflow(
    events: Sequence[Dict[str, Any]],
    *,
    key_prefix: str = "",
    key_suffix: str = "-key",
) -> Dict[str, Dict[str, str]]:
    signer_key_map = build_signer_key_map(events, key_prefix=key_prefix, key_suffix=key_suffix)
    private_keys = generate_ed25519_private_keys(signer_key_map.values())
    public_keys = derive_ed25519_public_keys(private_keys)
    return {
        "signer_key_map": signer_key_map,
        "private_keys": private_keys,
        "public_keys": public_keys,
    }


def bootstrap_hmac_workflow(
    events: Sequence[Dict[str, Any]],
    *,
    key_prefix: str = "",
    key_suffix: str = "-key",
) -> Dict[str, Dict[str, str]]:
    signer_key_map = build_signer_key_map(events, key_prefix=key_prefix, key_suffix=key_suffix)
    shared_secrets = generate_hmac_shared_secrets(signer_key_map.values())
    return {
        "signer_key_map": signer_key_map,
        "shared_secrets": shared_secrets,
    }


def bootstrap_stable_reference_demo_ledger(
    *,
    symbol: str,
    name: str,
    reference_unit: str = "USD",
    root_id: Optional[str] = None,
    issuer: str = "issuer",
    merchant_account: str = "merchant",
    service_account: str = "api_node",
    initial_balance: str = "25000000",
    merchant_amount: str = "1250000",
    service_amount: str = "250000",
    merchant_burn_amount: str = "5000",
    intended_use: str = "invoice-credit-accounting",
    profile_fields: Optional[Mapping[str, str]] = None,
    rules_hash: Optional[str] = None,
    nonce: Optional[str] = None,
    include_annotation: bool = True,
) -> Dict[str, Any]:
    require_account_name(issuer, "issuer")
    require_account_name(merchant_account, "merchant_account")
    require_account_name(service_account, "service_account")

    initial_balance_value = parse_positive_amount(initial_balance)
    merchant_amount_value = parse_positive_amount(merchant_amount)
    service_amount_value = parse_positive_amount(service_amount)
    burn_amount_value = parse_amount(merchant_burn_amount)
    distributed_total = merchant_amount_value + service_amount_value
    if distributed_total > initial_balance_value:
        raise SatRootError("stable demo distribution exceeds initial issued balance")
    if burn_amount_value > merchant_amount_value:
        raise SatRootError("stable demo burn amount cannot exceed the merchant allocation")
    resolved_profile_fields = {
        "reference_unit": reference_unit,
        "intended_use": intended_use,
    }
    if profile_fields:
        resolved_profile_fields.update(profile_fields)

    genesis = scaffold_genesis_record(
        symbol=symbol,
        name=name,
        root_id=root_id,
        mint_authority=issuer,
        initial_owner=issuer,
        initial_balance=initial_balance,
        profile="SATROOT-STABLE-1",
        profile_fields=resolved_profile_fields,
        rules_hash=rules_hash,
        nonce=nonce,
    )

    events: list[Dict[str, Any]] = [genesis]
    merchant_transfer = scaffold_event_from_ledger(
        events,
        action="transfer",
        signer=issuer,
        from_account=issuer,
        to_account=merchant_account,
        amount=merchant_amount,
    )
    events.append(sign_event_record(merchant_transfer, scheme="demo"))

    service_transfer = scaffold_event_from_ledger(
        events,
        action="transfer",
        signer=issuer,
        from_account=issuer,
        to_account=service_account,
        amount=service_amount,
    )
    events.append(sign_event_record(service_transfer, scheme="demo"))

    if burn_amount_value > 0:
        merchant_burn = scaffold_event_from_ledger(
            events,
            action="burn",
            signer=merchant_account,
            from_account=merchant_account,
            amount=merchant_burn_amount,
        )
        events.append(sign_event_record(merchant_burn, scheme="demo"))

    final_state = replay(events)
    return {
        "events": events,
        "annotated_events": annotate_ledger_events(events) if include_annotation else None,
        "final_state_snapshot": final_state.snapshot(),
        "final_state_hash": final_state.state_hash(),
    }


def bootstrap_machine_credit_demo_ledger(
    *,
    symbol: str,
    name: str,
    service_scope: str = "api-compute",
    billing_unit: str = "request",
    consumption_model: str = "burn-on-use",
    root_id: Optional[str] = None,
    issuer: str = "issuer",
    tenant_account: str = "tenant_a",
    worker_account: str = "worker_node",
    max_supply: Optional[str] = None,
    initial_balance: str = "100000000",
    tenant_amount: str = "5000000",
    worker_amount: str = "1200000",
    worker_burn_amount: str = "200000",
    intended_use: str = "machine-api-credit",
    profile_fields: Optional[Mapping[str, str]] = None,
    rules_hash: Optional[str] = None,
    nonce: Optional[str] = None,
    include_annotation: bool = True,
) -> Dict[str, Any]:
    require_account_name(issuer, "issuer")
    require_account_name(tenant_account, "tenant_account")
    require_account_name(worker_account, "worker_account")

    initial_balance_value = parse_positive_amount(initial_balance)
    tenant_amount_value = parse_positive_amount(tenant_amount)
    worker_amount_value = parse_positive_amount(worker_amount)
    burn_amount_value = parse_amount(worker_burn_amount)
    resolved_max_supply = initial_balance if max_supply is None else max_supply

    if tenant_amount_value > initial_balance_value:
        raise SatRootError("machine demo tenant allocation exceeds initial issued balance")
    if worker_amount_value > tenant_amount_value:
        raise SatRootError("machine demo worker allocation cannot exceed the tenant allocation")
    if burn_amount_value > worker_amount_value:
        raise SatRootError("machine demo burn amount cannot exceed the worker allocation")
    resolved_profile_fields = {
        "service_scope": service_scope,
        "billing_unit": billing_unit,
        "consumption_model": consumption_model,
        "intended_use": intended_use,
    }
    if profile_fields:
        resolved_profile_fields.update(profile_fields)

    genesis = scaffold_genesis_record(
        symbol=symbol,
        name=name,
        root_id=root_id,
        mint_authority=issuer,
        initial_owner=issuer,
        max_supply=resolved_max_supply,
        initial_balance=initial_balance,
        profile="SATROOT-MACHINE-1",
        profile_fields=resolved_profile_fields,
        rules_hash=rules_hash,
        nonce=nonce,
    )

    events: list[Dict[str, Any]] = [genesis]
    tenant_transfer = scaffold_event_from_ledger(
        events,
        action="transfer",
        signer=issuer,
        from_account=issuer,
        to_account=tenant_account,
        amount=tenant_amount,
    )
    events.append(sign_event_record(tenant_transfer, scheme="demo"))

    worker_transfer = scaffold_event_from_ledger(
        events,
        action="transfer",
        signer=tenant_account,
        from_account=tenant_account,
        to_account=worker_account,
        amount=worker_amount,
    )
    events.append(sign_event_record(worker_transfer, scheme="demo"))

    if burn_amount_value > 0:
        if resolved_profile_fields["consumption_model"] != "burn-on-use":
            raise SatRootError("machine demo burn step requires consumption_model=burn-on-use")
        worker_burn = scaffold_machine_credit_consumption_event(
            events,
            signer=worker_account,
            from_account=worker_account,
            amount=worker_burn_amount,
        )
        events.append(sign_event_record(worker_burn, scheme="demo"))

    final_state = replay(events)
    return {
        "events": events,
        "annotated_events": annotate_ledger_events(events) if include_annotation else None,
        "final_state_snapshot": final_state.snapshot(),
        "final_state_hash": final_state.state_hash(),
    }


def bootstrap_singleton_object_demo_ledger(
    *,
    profile: str,
    symbol: str,
    name: str,
    root_id: Optional[str] = None,
    issuer: str = "issuer",
    holder_account: str,
    next_holder: Optional[str] = None,
    archive_account: Optional[str] = None,
    profile_fields: Optional[Mapping[str, str]] = None,
    rules_hash: Optional[str] = None,
    nonce: Optional[str] = None,
    retire: bool = True,
    include_annotation: bool = True,
) -> Dict[str, Any]:
    if profile not in SINGLETON_DEMO_PROFILE_DEFAULTS:
        raise SatRootError("singleton demo bootstrap requires a SATROOT receipt, identity, or license profile")

    issuer_account = require_account_name(issuer, "issuer")
    current_holder = require_account_name(holder_account, "holder_account")
    resolved_next_holder = None if next_holder is None else require_account_name(next_holder, "next_holder")
    resolved_archive_account = None if archive_account is None else require_account_name(archive_account, "archive_account")

    genesis = scaffold_genesis_record(
        symbol=symbol,
        name=name,
        root_id=root_id,
        mint_authority=issuer_account,
        initial_owner=issuer_account,
        profile=profile,
        profile_fields=profile_fields,
        rules_hash=rules_hash,
        nonce=nonce,
    )

    events: list[Dict[str, Any]] = [genesis]
    issue_event = scaffold_event_from_ledger(
        events,
        action="transfer",
        signer=issuer_account,
        from_account=issuer_account,
        to_account=current_holder,
        amount="1",
    )
    events.append(sign_event_record(issue_event, scheme="demo"))

    if resolved_next_holder is not None:
        transfer_event = scaffold_singleton_object_transfer_event(
            events,
            signer=current_holder,
            to_account=resolved_next_holder,
        )
        events.append(sign_event_record(transfer_event, scheme="demo"))
        current_holder = resolved_next_holder

    if resolved_archive_account is not None:
        archive_event = scaffold_singleton_object_archive_event(
            events,
            signer=current_holder,
            archive_account=resolved_archive_account,
        )
        events.append(sign_event_record(archive_event, scheme="demo"))
        current_holder = resolved_archive_account

    if retire:
        retire_event = scaffold_singleton_object_retirement_event(
            events,
            signer=current_holder,
            from_account=current_holder,
        )
        events.append(sign_event_record(retire_event, scheme="demo"))

    final_state = replay(events)
    return {
        "events": events,
        "annotated_events": annotate_ledger_events(events) if include_annotation else None,
        "final_state_snapshot": final_state.snapshot(),
        "final_state_hash": final_state.state_hash(),
    }


def bootstrap_singleton_object_demo_bundle(
    *,
    profile: str,
    symbol: str,
    name: str,
    scheme: str,
    root_id: Optional[str] = None,
    issuer: str = "issuer",
    holder_account: str,
    next_holder: Optional[str] = None,
    archive_account: Optional[str] = None,
    profile_fields: Optional[Mapping[str, str]] = None,
    rules_hash: Optional[str] = None,
    nonce: Optional[str] = None,
    retire: bool = True,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
) -> Dict[str, Any]:
    demo = bootstrap_singleton_object_demo_ledger(
        profile=profile,
        symbol=symbol,
        name=name,
        root_id=root_id,
        issuer=issuer,
        holder_account=holder_account,
        next_holder=next_holder,
        archive_account=archive_account,
        profile_fields=profile_fields,
        rules_hash=rules_hash,
        nonce=nonce,
        retire=retire,
        include_annotation=False,
    )
    bundle = bootstrap_signed_ledger_bundle(
        demo["events"],
        scheme=scheme,
        key_prefix=key_prefix,
        key_suffix=key_suffix,
        include_state_hash=include_state_hash,
        include_annotation=include_annotation,
    )
    result = dict(bundle)
    result["genesis"] = copy.deepcopy(demo["events"][0])
    result["events"] = copy.deepcopy(demo["events"])
    result["profile"] = profile
    return result


def bootstrap_singleton_object_demo_release(
    *,
    profile: str,
    symbol: str,
    name: str,
    bundle_scheme: str,
    output_dir: str | Path,
    release_key_id: str,
    release_scheme: Optional[str] = None,
    root_id: Optional[str] = None,
    issuer: str = "issuer",
    holder_account: str,
    next_holder: Optional[str] = None,
    archive_account: Optional[str] = None,
    profile_fields: Optional[Mapping[str, str]] = None,
    rules_hash: Optional[str] = None,
    nonce: Optional[str] = None,
    retire: bool = True,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
    verifier_only: bool = False,
    release_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    resolved_release_scheme = release_scheme or bundle_scheme
    if verifier_only and bundle_scheme != "ed25519":
        raise SatRootError("--verifier-only is only supported for ed25519 bundles")

    root_output_dir = Path(output_dir).resolve()
    bundle_dir = root_output_dir / "bundle"
    release_dir = root_output_dir / "release"
    bundle = bootstrap_singleton_object_demo_bundle(
        profile=profile,
        symbol=symbol,
        name=name,
        scheme=bundle_scheme,
        root_id=root_id,
        issuer=issuer,
        holder_account=holder_account,
        next_holder=next_holder,
        archive_account=archive_account,
        profile_fields=profile_fields,
        rules_hash=rules_hash,
        nonce=nonce,
        retire=retire,
        key_prefix=key_prefix,
        key_suffix=key_suffix,
        include_state_hash=include_state_hash,
        include_annotation=include_annotation,
    )
    bundle_output = _write_bundle_output_dir(
        bundle,
        output_dir=bundle_dir,
        include_private_keys=not verifier_only,
        genesis=bundle["genesis"],
    )
    published = bootstrap_release_publication(
        [bundle_dir],
        output_dir=release_dir,
        signature_scheme=resolved_release_scheme,
        key_id=release_key_id,
        release_metadata=release_metadata,
    )
    return {
        "bundle": bundle,
        "bundle_output": bundle_output,
        "bundle_dir": str(bundle_dir.resolve()),
        "release_dir": str(release_dir.resolve()),
        "release_publication": published,
        "release_material": published["release_material"],
    }


def bootstrap_stable_reference_demo_bundle(
    *,
    symbol: str,
    name: str,
    scheme: str,
    reference_unit: str = "USD",
    root_id: Optional[str] = None,
    issuer: str = "issuer",
    merchant_account: str = "merchant",
    service_account: str = "api_node",
    initial_balance: str = "25000000",
    merchant_amount: str = "1250000",
    service_amount: str = "250000",
    merchant_burn_amount: str = "5000",
    intended_use: str = "invoice-credit-accounting",
    profile_fields: Optional[Mapping[str, str]] = None,
    rules_hash: Optional[str] = None,
    nonce: Optional[str] = None,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
) -> Dict[str, Any]:
    demo = bootstrap_stable_reference_demo_ledger(
        symbol=symbol,
        name=name,
        reference_unit=reference_unit,
        root_id=root_id,
        issuer=issuer,
        merchant_account=merchant_account,
        service_account=service_account,
        initial_balance=initial_balance,
        merchant_amount=merchant_amount,
        service_amount=service_amount,
        merchant_burn_amount=merchant_burn_amount,
        intended_use=intended_use,
        profile_fields=profile_fields,
        rules_hash=rules_hash,
        nonce=nonce,
        include_annotation=False,
    )
    bundle = bootstrap_signed_ledger_bundle(
        demo["events"],
        scheme=scheme,
        key_prefix=key_prefix,
        key_suffix=key_suffix,
        include_state_hash=include_state_hash,
        include_annotation=include_annotation,
    )
    result = dict(bundle)
    result["genesis"] = copy.deepcopy(demo["events"][0])
    result["events"] = copy.deepcopy(demo["events"])
    return result


def bootstrap_signed_ledger_bundle(
    events: Sequence[Dict[str, Any]],
    *,
    scheme: str,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
) -> Dict[str, Any]:
    if not events:
        raise SatRootError("empty ledger")

    if scheme == "hmac-sha256":
        if len(events) == 1:
            material = {"signer_key_map": {}, "shared_secrets": {}}
        else:
            material = bootstrap_hmac_workflow(events, key_prefix=key_prefix, key_suffix=key_suffix)
        verifier = make_hmac_sha256_verifier(material["shared_secrets"])
        signer = make_hmac_sha256_signer(material["shared_secrets"])
    elif scheme == "ed25519":
        if len(events) == 1:
            material = {"signer_key_map": {}, "private_keys": {}, "public_keys": {}}
        else:
            material = bootstrap_ed25519_workflow(events, key_prefix=key_prefix, key_suffix=key_suffix)
        verifier = make_ed25519_verifier(material["public_keys"])
        signer = make_ed25519_signer(material["private_keys"])
    else:
        raise SatRootError(f"unsupported bootstrap signing scheme: {scheme}")

    signed_events = sign_ledger_events(
        events,
        scheme=scheme,
        signer_key_ids=material["signer_key_map"],
        signer=signer,
        verifier=verifier,
        include_state_hash=include_state_hash,
    )
    annotated_events = annotate_ledger_events(signed_events, verifier=verifier) if include_annotation else None
    final_state = replay(signed_events, verifier=verifier)
    return {
        "scheme": scheme,
        "material": material,
        "signed_events": signed_events,
        "annotated_events": annotated_events,
        "final_state_snapshot": final_state.snapshot(),
        "final_state_hash": final_state.state_hash(),
    }


def bootstrap_genesis_bundle(
    *,
    symbol: str,
    name: str,
    scheme: str,
    root_id: Optional[str] = None,
    mint_authority: str = "issuer",
    initial_owner: Optional[str] = None,
    decimals: Optional[int] = None,
    max_supply: Optional[str] = None,
    initial_balance: Optional[str] = None,
    profile: Optional[str] = None,
    profile_fields: Optional[Mapping[str, str]] = None,
    rules_hash: Optional[str] = None,
    nonce: Optional[str] = None,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
) -> Dict[str, Any]:
    genesis = scaffold_genesis_record(
        symbol=symbol,
        name=name,
        root_id=root_id,
        mint_authority=mint_authority,
        initial_owner=initial_owner,
        decimals=decimals,
        max_supply=max_supply,
        initial_balance=initial_balance,
        profile=profile,
        profile_fields=profile_fields,
        rules_hash=rules_hash,
        nonce=nonce,
    )
    bundle = bootstrap_signed_ledger_bundle(
        [genesis],
        scheme=scheme,
        key_prefix=key_prefix,
        key_suffix=key_suffix,
        include_state_hash=include_state_hash,
        include_annotation=include_annotation,
    )
    result = dict(bundle)
    result["genesis"] = copy.deepcopy(genesis)
    return result


def build_signed_ledger_bundle_manifest(
    bundle: Mapping[str, Any],
    *,
    output_files: Mapping[str, str],
    output_file_hashes: Mapping[str, str],
) -> Dict[str, Any]:
    final_snapshot = bundle["final_state_snapshot"]
    verification_material_scope = "shared-secret"
    if bundle["scheme"] == "ed25519":
        verification_material_scope = "private-and-public" if "private_keys" in output_files else "public-only"
    return {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "bundle_type": "signed-ledger",
        "scheme": bundle["scheme"],
        "verification_material_scope": verification_material_scope,
        "record_count": len(bundle["signed_events"]),
        "root_id": final_snapshot["root_id"],
        "symbol": final_snapshot["symbol"],
        "final_event_id": final_snapshot["last_event_id"],
        "final_state_snapshot": copy.deepcopy(final_snapshot),
        "final_state_hash": bundle["final_state_hash"],
        "annotated_output": bundle["annotated_events"] is not None,
        "files": dict(output_files),
        "file_hashes": dict(output_file_hashes),
    }


def _load_validated_bundle_manifest(bundle_path: Path) -> Dict[str, Any]:
    manifest_path = bundle_path / "bundle_manifest.json"
    if not manifest_path.exists():
        raise SatRootError("bundle_manifest.json is required for bundle operations")
    manifest = _load_json_object_file(str(manifest_path), label="bundle_manifest")
    validate_instance_against_schema(manifest, load_bundle_manifest_schema())
    return manifest


def summarize_signed_ledger_bundle(bundle_dir: str | Path) -> Dict[str, Any]:
    bundle_path = Path(bundle_dir)
    manifest = _load_validated_bundle_manifest(bundle_path)
    final_snapshot = manifest.get("final_state_snapshot")
    if not isinstance(final_snapshot, dict):
        raise SatRootError("bundle manifest final_state_snapshot must be an object")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise SatRootError("bundle manifest files must be an object")

    return {
        "scheme": manifest.get("scheme"),
        "verification_material_scope": manifest.get("verification_material_scope"),
        "record_count": manifest.get("record_count"),
        "root_id": manifest.get("root_id"),
        "symbol": manifest.get("symbol"),
        "final_event_id": manifest.get("final_event_id"),
        "final_state_hash": manifest.get("final_state_hash"),
        "annotated_output": bool(manifest.get("annotated_output")),
        "final_state_snapshot": copy.deepcopy(final_snapshot),
        "files": copy.deepcopy(files),
    }


def lint_signed_ledger_bundle(bundle_dir: str | Path) -> Dict[str, Any]:
    bundle_path = Path(bundle_dir)
    manifest = _load_validated_bundle_manifest(bundle_path)
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise SatRootError("bundle manifest files must be an object")
    file_hashes = manifest.get("file_hashes")
    if not isinstance(file_hashes, dict):
        raise SatRootError("bundle manifest file_hashes must be an object")

    declared_paths = {
        key: relative
        for key, relative in files.items()
        if isinstance(relative, str) and relative.strip()
    }
    path_counts: Dict[str, int] = {}
    for relative in declared_paths.values():
        path_counts[relative] = path_counts.get(relative, 0) + 1

    missing_files = sorted(
        key for key, relative in declared_paths.items() if not (bundle_path / relative).is_file()
    )
    unhashed_declared_files = sorted(
        key for key in declared_paths if key != "bundle_manifest" and key not in file_hashes
    )
    dangling_hash_entries = sorted(key for key in file_hashes if key not in declared_paths)
    duplicate_declared_paths = sorted(relative for relative, count in path_counts.items() if count > 1)
    actual_files = sorted(path.name for path in bundle_path.iterdir() if path.is_file())
    extra_files = sorted(name for name in actual_files if name not in set(declared_paths.values()))

    return {
        "ok": not any(
            [
                missing_files,
                unhashed_declared_files,
                dangling_hash_entries,
                duplicate_declared_paths,
                extra_files,
            ]
        ),
        "scheme": manifest.get("scheme"),
        "verification_material_scope": manifest.get("verification_material_scope"),
        "declared_file_count": len(declared_paths),
        "actual_file_count": len(actual_files),
        "missing_files": missing_files,
        "unhashed_declared_files": unhashed_declared_files,
        "dangling_hash_entries": dangling_hash_entries,
        "duplicate_declared_paths": duplicate_declared_paths,
        "extra_files": extra_files,
    }


def build_signed_ledger_bundle_index(
    bundle_dirs: Sequence[str | Path],
    *,
    base_dir: str | Path = ".",
    release_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    if not bundle_dirs:
        raise SatRootError("at least one bundle directory is required")

    bundles: list[Dict[str, Any]] = []
    for bundle_dir in bundle_dirs:
        bundle_path = Path(bundle_dir).resolve()
        manifest = _load_validated_bundle_manifest(bundle_path)
        manifest_path = bundle_path / "bundle_manifest.json"
        relative_bundle_path = _relative_output_path(bundle_path, base_dir=base_dir)
        entry = {
            "bundle_id": "sha256:" + sha256_hex(relative_bundle_path),
            "bundle_path": relative_bundle_path,
            "manifest_path": (
                f"{relative_bundle_path}/bundle_manifest.json"
                if relative_bundle_path not in {"", "."}
                else "bundle_manifest.json"
            ),
            "manifest_hash": "sha256:" + sha256_hex_bytes(manifest_path.read_bytes()),
            "scheme": manifest.get("scheme"),
            "verification_material_scope": manifest.get("verification_material_scope"),
            "record_count": manifest.get("record_count"),
            "root_id": manifest.get("root_id"),
            "symbol": manifest.get("symbol"),
            "final_event_id": manifest.get("final_event_id"),
            "final_state_hash": manifest.get("final_state_hash"),
            "annotated_output": bool(manifest.get("annotated_output")),
        }
        bundles.append(entry)

    bundles.sort(key=lambda entry: (str(entry["symbol"]), str(entry["bundle_path"]), str(entry["manifest_hash"])))
    index = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "index_type": "bundle-index",
        "bundle_count": len(bundles),
        "bundles": bundles,
    }
    if release_metadata:
        index["release"] = {key: value for key, value in release_metadata.items() if isinstance(value, str) and value.strip()}
    return index


def discover_signed_ledger_bundle_dirs(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> list[str]:
    if not search_roots:
        raise SatRootError("at least one bundle discovery root is required")

    discovered: Dict[str, str] = {}
    for search_root in search_roots:
        root_path = Path(search_root).resolve()
        if not root_path.exists():
            raise SatRootError(f"bundle discovery root not found: {search_root}")
        if not root_path.is_dir():
            raise SatRootError(f"bundle discovery root must be a directory: {search_root}")

        manifest_paths = root_path.rglob("bundle_manifest.json") if recursive else root_path.glob("bundle_manifest.json")
        for manifest_path in manifest_paths:
            bundle_dir = str(manifest_path.parent.resolve())
            discovered.setdefault(bundle_dir, bundle_dir)

    if not discovered:
        raise SatRootError("no signed bundle directories found under the provided discovery roots")
    return sorted(discovered.values())


def resolve_bundle_directory_inputs(
    bundle_dirs: Sequence[str | Path],
    *,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
) -> list[str | Path]:
    resolved: list[str | Path] = []
    seen: set[str] = set()

    for bundle_dir in bundle_dirs:
        bundle_path = str(Path(bundle_dir).resolve())
        if bundle_path not in seen:
            resolved.append(bundle_dir)
            seen.add(bundle_path)

    if discover_under:
        for bundle_dir in discover_signed_ledger_bundle_dirs(discover_under, recursive=recursive):
            if bundle_dir not in seen:
                resolved.append(bundle_dir)
                seen.add(bundle_dir)

    if not resolved:
        raise SatRootError("at least one bundle directory or --discover-under path is required")
    return resolved


def validate_bundle_index_consistency(index: Mapping[str, Any]) -> None:
    bundles = index.get("bundles")
    bundle_count = index.get("bundle_count")
    if not isinstance(bundles, list):
        raise SatRootError("bundle index bundles must be an array")
    if not isinstance(bundle_count, int) or bundle_count != len(bundles):
        raise SatRootError("bundle index bundle_count mismatch")


def _relative_output_path(path: str | Path, *, base_dir: str | Path) -> str:
    target_path = Path(path).resolve()
    base_path = Path(base_dir).resolve()
    try:
        return target_path.relative_to(base_path).as_posix()
    except ValueError:
        try:
            return Path(os.path.relpath(target_path, base_path)).as_posix()
        except ValueError:
            return target_path.as_posix()


def release_manifest_signing_payload(manifest: Mapping[str, Any]) -> str:
    cleaned = {k: v for k, v in manifest.items() if k != "signature"}
    return canonical_json(cleaned)


def build_signed_release_manifest(
    bundle_index_json: str | Path,
    *,
    signature_scheme: str,
    key_id: str,
    signer: SignerFunction,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    if signature_scheme not in {"hmac-sha256", "ed25519"}:
        raise SatRootError(f"unsupported release signature scheme: {signature_scheme}")
    bundle_index_path = Path(bundle_index_json).resolve()
    index = _load_json_file(str(bundle_index_path))
    validate_instance_against_schema(index, load_bundle_index_schema())
    if not isinstance(index, dict):
        raise SatRootError("bundle index must contain an object")
    validate_bundle_index_consistency(index)

    relative_index_path = _relative_output_path(bundle_index_path, base_dir=base_dir)

    manifest = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "manifest_type": "release-manifest",
        "bundle_index_path": relative_index_path,
        "bundle_index_hash": "sha256:" + sha256_hex_bytes(bundle_index_path.read_bytes()),
        "bundle_count": index.get("bundle_count"),
        "signature_scheme": signature_scheme,
        "signature_key_id": key_id,
    }
    release = index.get("release")
    if isinstance(release, dict) and release:
        manifest["release"] = copy.deepcopy(release)
    manifest["signature"] = signer(release_manifest_signing_payload(manifest), key_id)
    return manifest


def verify_signed_release_manifest(
    release_manifest_json: str | Path,
    *,
    verifier: SignatureVerifier,
) -> Dict[str, Any]:
    manifest_path = Path(release_manifest_json).resolve()
    manifest = _load_json_object_file(str(manifest_path), label="release-manifest")
    validate_instance_against_schema(manifest, load_release_manifest_schema())

    bundle_index_ref = manifest.get("bundle_index_path")
    if not isinstance(bundle_index_ref, str) or not bundle_index_ref.strip():
        raise SatRootError("release manifest bundle_index_path must be a non-empty string")
    bundle_index_path = (manifest_path.parent / bundle_index_ref).resolve()
    if not bundle_index_path.exists():
        raise SatRootError(f"bundle index file not found: {bundle_index_ref}")

    index = _load_json_file(str(bundle_index_path))
    validate_instance_against_schema(index, load_bundle_index_schema())
    if not isinstance(index, dict):
        raise SatRootError("bundle index must contain an object")
    validate_bundle_index_consistency(index)

    actual_index_hash = "sha256:" + sha256_hex_bytes(bundle_index_path.read_bytes())
    if manifest.get("bundle_index_hash") != actual_index_hash:
        raise SatRootError("release manifest bundle_index_hash mismatch")
    if manifest.get("bundle_count") != index.get("bundle_count"):
        raise SatRootError("release manifest bundle_count mismatch")
    if manifest.get("release") != index.get("release"):
        raise SatRootError("release manifest release metadata mismatch")
    if not verifier(manifest, release_manifest_signing_payload(manifest)):
        raise SatRootError("release manifest signature verification failed")

    return {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "bundle_index_path": bundle_index_ref,
        "bundle_index_hash": actual_index_hash,
        "bundle_count": index.get("bundle_count"),
        "release": copy.deepcopy(index.get("release")),
    }


def _load_release_publication(
    release_dir: str | Path,
) -> tuple[Path, Path, Dict[str, Any], Dict[str, Any]]:
    release_path = Path(release_dir).resolve()
    if not release_path.is_dir():
        raise SatRootError("release directory must be an existing directory")

    manifest_path = release_path / "release_manifest.json"
    if not manifest_path.is_file():
        raise SatRootError("release_manifest.json is required for release publication operations")
    manifest = _load_json_object_file(str(manifest_path), label="release-manifest")
    validate_instance_against_schema(manifest, load_release_manifest_schema())

    bundle_index_ref = manifest.get("bundle_index_path")
    if not isinstance(bundle_index_ref, str) or not bundle_index_ref.strip():
        raise SatRootError("release manifest bundle_index_path must be a non-empty string")
    bundle_index_path = (manifest_path.parent / bundle_index_ref).resolve()
    if not bundle_index_path.is_file():
        raise SatRootError(f"bundle index file not found: {bundle_index_ref}")

    index = _load_json_file(str(bundle_index_path))
    validate_instance_against_schema(index, load_bundle_index_schema())
    if not isinstance(index, dict):
        raise SatRootError("bundle index must contain an object")
    validate_bundle_index_consistency(index)
    return manifest_path, bundle_index_path, manifest, index


def summarize_signed_release_publication(release_dir: str | Path) -> Dict[str, Any]:
    _, bundle_index_path, manifest, index = _load_release_publication(release_dir)
    bundles = index.get("bundles")
    assert isinstance(bundles, list)
    return {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "bundle_index_path": manifest.get("bundle_index_path"),
        "bundle_index_hash": manifest.get("bundle_index_hash"),
        "bundle_index_resolved_path": str(bundle_index_path),
        "bundle_count": index.get("bundle_count"),
        "release": copy.deepcopy(index.get("release")),
        "bundle_symbols": sorted({str(entry.get("symbol")) for entry in bundles}),
        "bundles": copy.deepcopy(bundles),
    }


def lint_signed_release_publication(release_dir: str | Path) -> Dict[str, Any]:
    manifest_path, bundle_index_path, manifest, index = _load_release_publication(release_dir)
    bundles = index.get("bundles")
    assert isinstance(bundles, list)

    actual_index_hash = "sha256:" + sha256_hex_bytes(bundle_index_path.read_bytes())
    bundle_index_hash_matches = manifest.get("bundle_index_hash") == actual_index_hash
    bundle_count_matches = manifest.get("bundle_count") == index.get("bundle_count")
    release_metadata_matches = manifest.get("release") == index.get("release")

    bundle_id_counts: Dict[str, int] = {}
    bundle_path_counts: Dict[str, int] = {}
    manifest_path_counts: Dict[str, int] = {}
    for entry in bundles:
        bundle_id = entry.get("bundle_id")
        bundle_path_ref = entry.get("bundle_path")
        manifest_path_ref = entry.get("manifest_path")
        if isinstance(bundle_id, str):
            bundle_id_counts[bundle_id] = bundle_id_counts.get(bundle_id, 0) + 1
        if isinstance(bundle_path_ref, str):
            bundle_path_counts[bundle_path_ref] = bundle_path_counts.get(bundle_path_ref, 0) + 1
        if isinstance(manifest_path_ref, str):
            manifest_path_counts[manifest_path_ref] = manifest_path_counts.get(manifest_path_ref, 0) + 1

    duplicate_bundle_ids = sorted(bundle_id for bundle_id, count in bundle_id_counts.items() if count > 1)
    duplicate_bundle_paths = sorted(bundle_path for bundle_path, count in bundle_path_counts.items() if count > 1)
    duplicate_manifest_paths = sorted(path for path, count in manifest_path_counts.items() if count > 1)

    bundle_manifest_path_mismatches: list[str] = []
    missing_bundle_directories: list[str] = []
    missing_bundle_manifests: list[str] = []
    manifest_hash_mismatches: list[str] = []
    bundle_manifest_metadata_mismatches: list[Dict[str, Any]] = []

    for entry in bundles:
        bundle_path_ref = entry.get("bundle_path")
        manifest_path_ref = entry.get("manifest_path")
        if not isinstance(bundle_path_ref, str) or not bundle_path_ref.strip():
            continue
        if not isinstance(manifest_path_ref, str) or not manifest_path_ref.strip():
            continue

        expected_manifest_path = (
            "bundle_manifest.json"
            if bundle_path_ref in {"", "."}
            else f"{bundle_path_ref}/bundle_manifest.json"
        )
        if manifest_path_ref != expected_manifest_path:
            bundle_manifest_path_mismatches.append(bundle_path_ref)

        resolved_bundle_dir = (manifest_path.parent / bundle_path_ref).resolve()
        resolved_manifest_path = (manifest_path.parent / manifest_path_ref).resolve()
        if not resolved_bundle_dir.is_dir():
            missing_bundle_directories.append(bundle_path_ref)
        if not resolved_manifest_path.is_file():
            missing_bundle_manifests.append(manifest_path_ref)
            continue

        actual_manifest_hash = "sha256:" + sha256_hex_bytes(resolved_manifest_path.read_bytes())
        if entry.get("manifest_hash") != actual_manifest_hash:
            manifest_hash_mismatches.append(manifest_path_ref)

        bundle_manifest = _load_json_object_file(str(resolved_manifest_path), label="bundle-manifest")
        validate_instance_against_schema(bundle_manifest, load_bundle_manifest_schema())
        mismatched_fields = [
            field_name
            for field_name in [
                "scheme",
                "verification_material_scope",
                "record_count",
                "root_id",
                "symbol",
                "final_event_id",
                "final_state_hash",
                "annotated_output",
            ]
            if entry.get(field_name) != bundle_manifest.get(field_name)
        ]
        if mismatched_fields:
            bundle_manifest_metadata_mismatches.append(
                {
                    "bundle_path": bundle_path_ref,
                    "fields": mismatched_fields,
                }
            )

    return {
        "ok": not any(
            [
                not bundle_index_hash_matches,
                not bundle_count_matches,
                not release_metadata_matches,
                duplicate_bundle_ids,
                duplicate_bundle_paths,
                duplicate_manifest_paths,
                bundle_manifest_path_mismatches,
                missing_bundle_directories,
                missing_bundle_manifests,
                manifest_hash_mismatches,
                bundle_manifest_metadata_mismatches,
            ]
        ),
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "bundle_index_path": manifest.get("bundle_index_path"),
        "bundle_index_hash_matches": bundle_index_hash_matches,
        "bundle_count_matches": bundle_count_matches,
        "release_metadata_matches": release_metadata_matches,
        "declared_bundle_count": len(bundles),
        "bundle_count": index.get("bundle_count"),
        "duplicate_bundle_ids": duplicate_bundle_ids,
        "duplicate_bundle_paths": duplicate_bundle_paths,
        "duplicate_manifest_paths": duplicate_manifest_paths,
        "bundle_manifest_path_mismatches": sorted(bundle_manifest_path_mismatches),
        "missing_bundle_directories": sorted(missing_bundle_directories),
        "missing_bundle_manifests": sorted(missing_bundle_manifests),
        "manifest_hash_mismatches": sorted(manifest_hash_mismatches),
        "bundle_manifest_metadata_mismatches": bundle_manifest_metadata_mismatches,
    }


def publish_signed_release(
    bundle_dirs: Sequence[str | Path],
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
    signer: SignerFunction,
    release_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    bundle_index = build_signed_ledger_bundle_index(
        bundle_dirs,
        base_dir=output_path,
        release_metadata=release_metadata,
    )
    bundle_index_path = output_path / "bundle_index.json"
    _write_json_file(bundle_index_path, bundle_index)

    release_manifest = build_signed_release_manifest(
        bundle_index_path,
        signature_scheme=signature_scheme,
        key_id=key_id,
        signer=signer,
        base_dir=output_path,
    )
    release_manifest_path = output_path / "release_manifest.json"
    _write_json_file(release_manifest_path, release_manifest)

    return {
        "bundle_index": bundle_index,
        "bundle_index_path": str(bundle_index_path),
        "release_manifest": release_manifest,
        "release_manifest_path": str(release_manifest_path),
    }


def bootstrap_release_publication(
    bundle_dirs: Sequence[str | Path],
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
    release_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    if signature_scheme == "hmac-sha256":
        material = bootstrap_release_hmac_material([key_id])
        signer = make_hmac_sha256_signer(material["shared_secrets"])
        _write_json_file(output_path / "release_secrets.json", material["shared_secrets"])
    elif signature_scheme == "ed25519":
        material = bootstrap_release_ed25519_material([key_id])
        signer = make_ed25519_signer(material["private_keys"])
        _write_json_file(output_path / "release_private_keys.json", material["private_keys"])
        _write_json_file(output_path / "release_public_keys.json", material["public_keys"])
    else:
        raise SatRootError(f"unsupported release signature scheme: {signature_scheme}")

    published = publish_signed_release(
        bundle_dirs,
        output_dir=output_path,
        signature_scheme=signature_scheme,
        key_id=key_id,
        signer=signer,
        release_metadata=release_metadata,
    )
    published["release_material"] = material
    return published


def build_signed_release_catalog(
    release_dirs: Sequence[str | Path],
    *,
    base_dir: str | Path = ".",
    catalog_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    if not release_dirs:
        raise SatRootError("at least one release directory is required")

    releases: list[Dict[str, Any]] = []
    for release_dir in release_dirs:
        release_path = Path(release_dir).resolve()
        manifest_path, bundle_index_path, manifest, index = _load_release_publication(release_path)
        release_ref = _relative_output_path(release_path, base_dir=base_dir)
        bundles = index.get("bundles")
        assert isinstance(bundles, list)
        entry = {
            "release_id": "sha256:" + sha256_hex(release_ref),
            "release_path": release_ref,
            "release_manifest_path": _relative_output_path(manifest_path, base_dir=base_dir),
            "release_manifest_hash": "sha256:" + sha256_hex_bytes(manifest_path.read_bytes()),
            "bundle_index_path": _relative_output_path(bundle_index_path, base_dir=base_dir),
            "bundle_index_hash": "sha256:" + sha256_hex_bytes(bundle_index_path.read_bytes()),
            "signature_scheme": manifest.get("signature_scheme"),
            "signature_key_id": manifest.get("signature_key_id"),
            "bundle_count": index.get("bundle_count"),
            "bundle_symbols": sorted({str(bundle.get("symbol")) for bundle in bundles}),
        }
        if isinstance(index.get("release"), dict) and index.get("release"):
            entry["release"] = copy.deepcopy(index["release"])
        releases.append(entry)

    releases.sort(key=lambda entry: (str(entry["release_path"]), str(entry["release_manifest_hash"])))
    catalog = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "catalog_type": "release-catalog",
        "release_count": len(releases),
        "releases": releases,
    }
    if catalog_metadata:
        catalog["catalog"] = {
            key: value for key, value in catalog_metadata.items() if isinstance(value, str) and value.strip()
        }
    return catalog


def discover_signed_release_publication_dirs(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> list[str]:
    if not search_roots:
        raise SatRootError("at least one release discovery root is required")

    discovered: Dict[str, str] = {}
    for search_root in search_roots:
        root_path = Path(search_root).resolve()
        if not root_path.exists():
            raise SatRootError(f"release discovery root not found: {search_root}")
        if not root_path.is_dir():
            raise SatRootError(f"release discovery root must be a directory: {search_root}")

        manifest_paths = root_path.rglob("release_manifest.json") if recursive else root_path.glob("release_manifest.json")
        for manifest_path in manifest_paths:
            release_dir = str(manifest_path.parent.resolve())
            discovered.setdefault(release_dir, release_dir)

    if not discovered:
        raise SatRootError("no signed release directories found under the provided discovery roots")
    return sorted(discovered.values())


def resolve_release_directory_inputs(
    release_dirs: Sequence[str | Path],
    *,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
) -> list[str | Path]:
    resolved: list[str | Path] = []
    seen: set[str] = set()

    for release_dir in release_dirs:
        release_path = str(Path(release_dir).resolve())
        if release_path not in seen:
            resolved.append(release_dir)
            seen.add(release_path)

    if discover_under:
        for release_dir in discover_signed_release_publication_dirs(discover_under, recursive=recursive):
            if release_dir not in seen:
                resolved.append(release_dir)
                seen.add(release_dir)

    if not resolved:
        raise SatRootError("at least one release directory or --discover-under path is required")
    return resolved


def validate_release_catalog_consistency(catalog: Mapping[str, Any]) -> None:
    releases = catalog.get("releases")
    release_count = catalog.get("release_count")
    if not isinstance(releases, list):
        raise SatRootError("release catalog releases must be an array")
    if not isinstance(release_count, int) or release_count != len(releases):
        raise SatRootError("release catalog release_count mismatch")


def release_catalog_manifest_signing_payload(manifest: Mapping[str, Any]) -> str:
    cleaned = {k: v for k, v in manifest.items() if k != "signature"}
    return canonical_json(cleaned)


def build_signed_release_catalog_manifest(
    release_catalog_json: str | Path,
    *,
    signature_scheme: str,
    key_id: str,
    signer: SignerFunction,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    if signature_scheme not in {"hmac-sha256", "ed25519"}:
        raise SatRootError(f"unsupported release catalog signature scheme: {signature_scheme}")
    release_catalog_path = Path(release_catalog_json).resolve()
    catalog = _load_json_file(str(release_catalog_path))
    validate_instance_against_schema(catalog, load_release_catalog_schema())
    if not isinstance(catalog, dict):
        raise SatRootError("release catalog must contain an object")
    validate_release_catalog_consistency(catalog)

    relative_catalog_path = _relative_output_path(release_catalog_path, base_dir=base_dir)
    manifest = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "manifest_type": "release-catalog-manifest",
        "release_catalog_path": relative_catalog_path,
        "release_catalog_hash": "sha256:" + sha256_hex_bytes(release_catalog_path.read_bytes()),
        "release_count": catalog.get("release_count"),
        "signature_scheme": signature_scheme,
        "signature_key_id": key_id,
    }
    catalog_metadata = catalog.get("catalog")
    if isinstance(catalog_metadata, dict) and catalog_metadata:
        manifest["catalog"] = copy.deepcopy(catalog_metadata)
    manifest["signature"] = signer(release_catalog_manifest_signing_payload(manifest), key_id)
    return manifest


def verify_signed_release_catalog_manifest(
    release_catalog_manifest_json: str | Path,
    *,
    verifier: SignatureVerifier,
) -> Dict[str, Any]:
    manifest_path = Path(release_catalog_manifest_json).resolve()
    manifest = _load_json_object_file(str(manifest_path), label="release-catalog-manifest")
    validate_instance_against_schema(manifest, load_release_catalog_manifest_schema())

    release_catalog_ref = manifest.get("release_catalog_path")
    if not isinstance(release_catalog_ref, str) or not release_catalog_ref.strip():
        raise SatRootError("release catalog manifest release_catalog_path must be a non-empty string")
    release_catalog_path = (manifest_path.parent / release_catalog_ref).resolve()
    if not release_catalog_path.exists():
        raise SatRootError(f"release catalog file not found: {release_catalog_ref}")

    catalog = _load_json_file(str(release_catalog_path))
    validate_instance_against_schema(catalog, load_release_catalog_schema())
    if not isinstance(catalog, dict):
        raise SatRootError("release catalog must contain an object")
    validate_release_catalog_consistency(catalog)

    actual_catalog_hash = "sha256:" + sha256_hex_bytes(release_catalog_path.read_bytes())
    if manifest.get("release_catalog_hash") != actual_catalog_hash:
        raise SatRootError("release catalog manifest release_catalog_hash mismatch")
    if manifest.get("release_count") != catalog.get("release_count"):
        raise SatRootError("release catalog manifest release_count mismatch")
    if manifest.get("catalog") != catalog.get("catalog"):
        raise SatRootError("release catalog manifest catalog metadata mismatch")
    if not verifier(manifest, release_catalog_manifest_signing_payload(manifest)):
        raise SatRootError("release catalog manifest signature verification failed")

    return {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "release_catalog_path": release_catalog_ref,
        "release_catalog_hash": actual_catalog_hash,
        "release_count": catalog.get("release_count"),
        "catalog": copy.deepcopy(catalog.get("catalog")),
    }


def publish_signed_release_catalog(
    release_dirs: Sequence[str | Path],
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
    signer: SignerFunction,
    catalog_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    release_catalog = build_signed_release_catalog(
        release_dirs,
        base_dir=output_path,
        catalog_metadata=catalog_metadata,
    )
    release_catalog_path = output_path / "release_catalog.json"
    _write_json_file(release_catalog_path, release_catalog)

    release_catalog_manifest = build_signed_release_catalog_manifest(
        release_catalog_path,
        signature_scheme=signature_scheme,
        key_id=key_id,
        signer=signer,
        base_dir=output_path,
    )
    release_catalog_manifest_path = output_path / "release_catalog_manifest.json"
    _write_json_file(release_catalog_manifest_path, release_catalog_manifest)

    return {
        "release_catalog": release_catalog,
        "release_catalog_path": str(release_catalog_path),
        "release_catalog_manifest": release_catalog_manifest,
        "release_catalog_manifest_path": str(release_catalog_manifest_path),
    }


def bootstrap_release_catalog_publication(
    release_dirs: Sequence[str | Path],
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
    catalog_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    if signature_scheme == "hmac-sha256":
        material = bootstrap_release_hmac_material([key_id])
        signer = make_hmac_sha256_signer(material["shared_secrets"])
        _write_json_file(output_path / "release_catalog_secrets.json", material["shared_secrets"])
    elif signature_scheme == "ed25519":
        material = bootstrap_release_ed25519_material([key_id])
        signer = make_ed25519_signer(material["private_keys"])
        _write_json_file(output_path / "release_catalog_private_keys.json", material["private_keys"])
        _write_json_file(output_path / "release_catalog_public_keys.json", material["public_keys"])
    else:
        raise SatRootError(f"unsupported release catalog signature scheme: {signature_scheme}")

    published = publish_signed_release_catalog(
        release_dirs,
        output_dir=output_path,
        signature_scheme=signature_scheme,
        key_id=key_id,
        signer=signer,
        catalog_metadata=catalog_metadata,
    )
    published["release_catalog_material"] = material
    return published


def _load_release_catalog_publication(
    release_catalog_dir: str | Path,
) -> tuple[Path, Path, Dict[str, Any], Dict[str, Any]]:
    catalog_path = Path(release_catalog_dir).resolve()
    if not catalog_path.is_dir():
        raise SatRootError("release catalog directory must be an existing directory")

    manifest_path = catalog_path / "release_catalog_manifest.json"
    if not manifest_path.is_file():
        raise SatRootError("release_catalog_manifest.json is required for release catalog publication operations")
    manifest = _load_json_object_file(str(manifest_path), label="release-catalog-manifest")
    validate_instance_against_schema(manifest, load_release_catalog_manifest_schema())

    release_catalog_ref = manifest.get("release_catalog_path")
    if not isinstance(release_catalog_ref, str) or not release_catalog_ref.strip():
        raise SatRootError("release catalog manifest release_catalog_path must be a non-empty string")
    release_catalog_path = (manifest_path.parent / release_catalog_ref).resolve()
    if not release_catalog_path.is_file():
        raise SatRootError(f"release catalog file not found: {release_catalog_ref}")

    catalog = _load_json_file(str(release_catalog_path))
    validate_instance_against_schema(catalog, load_release_catalog_schema())
    if not isinstance(catalog, dict):
        raise SatRootError("release catalog must contain an object")
    validate_release_catalog_consistency(catalog)
    return manifest_path, release_catalog_path, manifest, catalog


def summarize_signed_release_catalog_publication(release_catalog_dir: str | Path) -> Dict[str, Any]:
    _, release_catalog_path, manifest, catalog = _load_release_catalog_publication(release_catalog_dir)
    releases = catalog.get("releases")
    assert isinstance(releases, list)
    return {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "release_catalog_path": manifest.get("release_catalog_path"),
        "release_catalog_hash": manifest.get("release_catalog_hash"),
        "release_catalog_resolved_path": str(release_catalog_path),
        "release_count": catalog.get("release_count"),
        "catalog": copy.deepcopy(catalog.get("catalog")),
        "release_paths": sorted(str(entry.get("release_path")) for entry in releases),
        "release_labels": sorted(
            {
                str(entry["release"].get("label"))
                for entry in releases
                if isinstance(entry.get("release"), dict) and isinstance(entry["release"].get("label"), str)
            }
        ),
        "releases": copy.deepcopy(releases),
    }


def lint_signed_release_catalog_publication(release_catalog_dir: str | Path) -> Dict[str, Any]:
    manifest_path, release_catalog_path, manifest, catalog = _load_release_catalog_publication(release_catalog_dir)
    releases = catalog.get("releases")
    assert isinstance(releases, list)

    actual_catalog_hash = "sha256:" + sha256_hex_bytes(release_catalog_path.read_bytes())
    release_catalog_hash_matches = manifest.get("release_catalog_hash") == actual_catalog_hash
    release_count_matches = manifest.get("release_count") == catalog.get("release_count")
    catalog_metadata_matches = manifest.get("catalog") == catalog.get("catalog")

    release_id_counts: Dict[str, int] = {}
    release_path_counts: Dict[str, int] = {}
    release_manifest_path_counts: Dict[str, int] = {}
    bundle_index_path_counts: Dict[str, int] = {}
    for entry in releases:
        release_id = entry.get("release_id")
        release_path_ref = entry.get("release_path")
        release_manifest_path_ref = entry.get("release_manifest_path")
        bundle_index_path_ref = entry.get("bundle_index_path")
        if isinstance(release_id, str):
            release_id_counts[release_id] = release_id_counts.get(release_id, 0) + 1
        if isinstance(release_path_ref, str):
            release_path_counts[release_path_ref] = release_path_counts.get(release_path_ref, 0) + 1
        if isinstance(release_manifest_path_ref, str):
            release_manifest_path_counts[release_manifest_path_ref] = release_manifest_path_counts.get(release_manifest_path_ref, 0) + 1
        if isinstance(bundle_index_path_ref, str):
            bundle_index_path_counts[bundle_index_path_ref] = bundle_index_path_counts.get(bundle_index_path_ref, 0) + 1

    duplicate_release_ids = sorted(value for value, count in release_id_counts.items() if count > 1)
    duplicate_release_paths = sorted(value for value, count in release_path_counts.items() if count > 1)
    duplicate_release_manifest_paths = sorted(value for value, count in release_manifest_path_counts.items() if count > 1)
    duplicate_bundle_index_paths = sorted(value for value, count in bundle_index_path_counts.items() if count > 1)

    release_manifest_path_mismatches: list[str] = []
    missing_release_directories: list[str] = []
    missing_release_manifests: list[str] = []
    missing_bundle_indexes: list[str] = []
    release_manifest_hash_mismatches: list[str] = []
    bundle_index_hash_mismatches: list[str] = []
    release_publication_metadata_mismatches: list[Dict[str, Any]] = []

    for entry in releases:
        release_path_ref = entry.get("release_path")
        release_manifest_path_ref = entry.get("release_manifest_path")
        bundle_index_path_ref = entry.get("bundle_index_path")
        if not isinstance(release_path_ref, str) or not release_path_ref.strip():
            continue
        if not isinstance(release_manifest_path_ref, str) or not release_manifest_path_ref.strip():
            continue
        if not isinstance(bundle_index_path_ref, str) or not bundle_index_path_ref.strip():
            continue

        expected_manifest_path = (
            "release_manifest.json"
            if release_path_ref in {"", "."}
            else f"{release_path_ref}/release_manifest.json"
        )
        if release_manifest_path_ref != expected_manifest_path:
            release_manifest_path_mismatches.append(release_path_ref)

        resolved_release_dir = (manifest_path.parent / release_path_ref).resolve()
        resolved_manifest_path = (manifest_path.parent / release_manifest_path_ref).resolve()
        resolved_bundle_index_path = (manifest_path.parent / bundle_index_path_ref).resolve()
        if not resolved_release_dir.is_dir():
            missing_release_directories.append(release_path_ref)
        if not resolved_manifest_path.is_file():
            missing_release_manifests.append(release_manifest_path_ref)
            continue
        if not resolved_bundle_index_path.is_file():
            missing_bundle_indexes.append(bundle_index_path_ref)
            continue

        actual_manifest_hash = "sha256:" + sha256_hex_bytes(resolved_manifest_path.read_bytes())
        if entry.get("release_manifest_hash") != actual_manifest_hash:
            release_manifest_hash_mismatches.append(release_manifest_path_ref)

        actual_bundle_index_hash = "sha256:" + sha256_hex_bytes(resolved_bundle_index_path.read_bytes())
        if entry.get("bundle_index_hash") != actual_bundle_index_hash:
            bundle_index_hash_mismatches.append(bundle_index_path_ref)

        _, _, release_manifest, release_index = _load_release_publication(resolved_release_dir)
        release_bundles = release_index.get("bundles")
        assert isinstance(release_bundles, list)
        mismatched_fields = [
            field_name
            for field_name in [
                "signature_scheme",
                "signature_key_id",
                "bundle_count",
                "release",
            ]
            if entry.get(field_name) != release_manifest.get(field_name if field_name.startswith("signature_") else field_name, release_index.get(field_name))
        ]
        if sorted({str(bundle.get("symbol")) for bundle in release_bundles}) != sorted(entry.get("bundle_symbols", [])):
            mismatched_fields.append("bundle_symbols")
        if entry.get("signature_scheme") != release_manifest.get("signature_scheme") and "signature_scheme" not in mismatched_fields:
            mismatched_fields.append("signature_scheme")
        if entry.get("signature_key_id") != release_manifest.get("signature_key_id") and "signature_key_id" not in mismatched_fields:
            mismatched_fields.append("signature_key_id")
        if entry.get("bundle_count") != release_index.get("bundle_count") and "bundle_count" not in mismatched_fields:
            mismatched_fields.append("bundle_count")
        if entry.get("release") != release_index.get("release") and "release" not in mismatched_fields:
            mismatched_fields.append("release")

        if mismatched_fields:
            release_publication_metadata_mismatches.append(
                {
                    "release_path": release_path_ref,
                    "fields": sorted(set(mismatched_fields)),
                }
            )

    return {
        "ok": not any(
            [
                not release_catalog_hash_matches,
                not release_count_matches,
                not catalog_metadata_matches,
                duplicate_release_ids,
                duplicate_release_paths,
                duplicate_release_manifest_paths,
                duplicate_bundle_index_paths,
                release_manifest_path_mismatches,
                missing_release_directories,
                missing_release_manifests,
                missing_bundle_indexes,
                release_manifest_hash_mismatches,
                bundle_index_hash_mismatches,
                release_publication_metadata_mismatches,
            ]
        ),
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "release_catalog_path": manifest.get("release_catalog_path"),
        "release_catalog_hash_matches": release_catalog_hash_matches,
        "release_count_matches": release_count_matches,
        "catalog_metadata_matches": catalog_metadata_matches,
        "declared_release_count": len(releases),
        "release_count": catalog.get("release_count"),
        "duplicate_release_ids": duplicate_release_ids,
        "duplicate_release_paths": duplicate_release_paths,
        "duplicate_release_manifest_paths": duplicate_release_manifest_paths,
        "duplicate_bundle_index_paths": duplicate_bundle_index_paths,
        "release_manifest_path_mismatches": sorted(release_manifest_path_mismatches),
        "missing_release_directories": sorted(missing_release_directories),
        "missing_release_manifests": sorted(missing_release_manifests),
        "missing_bundle_indexes": sorted(missing_bundle_indexes),
        "release_manifest_hash_mismatches": sorted(release_manifest_hash_mismatches),
        "bundle_index_hash_mismatches": sorted(bundle_index_hash_mismatches),
        "release_publication_metadata_mismatches": release_publication_metadata_mismatches,
    }


def build_signed_release_catalog_index(
    release_catalog_dirs: Sequence[str | Path],
    *,
    base_dir: str | Path = ".",
    index_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    if not release_catalog_dirs:
        raise SatRootError("at least one release catalog directory is required")

    release_catalogs: list[Dict[str, Any]] = []
    for release_catalog_dir in release_catalog_dirs:
        release_catalog_dir_path = Path(release_catalog_dir).resolve()
        manifest_path, release_catalog_path, manifest, catalog = _load_release_catalog_publication(release_catalog_dir_path)
        release_catalog_ref = _relative_output_path(release_catalog_dir_path, base_dir=base_dir)
        releases = catalog.get("releases")
        assert isinstance(releases, list)
        entry = {
            "release_catalog_id": "sha256:" + sha256_hex(release_catalog_ref),
            "release_catalog_path": release_catalog_ref,
            "release_catalog_manifest_path": _relative_output_path(manifest_path, base_dir=base_dir),
            "release_catalog_manifest_hash": "sha256:" + sha256_hex_bytes(manifest_path.read_bytes()),
            "release_catalog_json_path": _relative_output_path(release_catalog_path, base_dir=base_dir),
            "release_catalog_hash": "sha256:" + sha256_hex_bytes(release_catalog_path.read_bytes()),
            "signature_scheme": manifest.get("signature_scheme"),
            "signature_key_id": manifest.get("signature_key_id"),
            "release_count": catalog.get("release_count"),
            "release_paths": sorted(str(release.get("release_path")) for release in releases),
            "release_labels": sorted(
                {
                    str(release["release"].get("label"))
                    for release in releases
                    if isinstance(release.get("release"), dict) and isinstance(release["release"].get("label"), str)
                }
            ),
        }
        if isinstance(catalog.get("catalog"), dict) and catalog.get("catalog"):
            entry["catalog"] = copy.deepcopy(catalog["catalog"])
        release_catalogs.append(entry)

    release_catalogs.sort(key=lambda entry: (str(entry["release_catalog_path"]), str(entry["release_catalog_manifest_hash"])))
    index = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "index_type": "release-catalog-index",
        "release_catalog_count": len(release_catalogs),
        "release_catalogs": release_catalogs,
    }
    if index_metadata:
        index["index"] = {
            key: value for key, value in index_metadata.items() if isinstance(value, str) and value.strip()
        }
    return index


def discover_signed_release_catalog_publication_dirs(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> list[str]:
    if not search_roots:
        raise SatRootError("at least one release catalog discovery root is required")

    discovered: Dict[str, str] = {}
    for search_root in search_roots:
        root_path = Path(search_root).resolve()
        if not root_path.exists():
            raise SatRootError(f"release catalog discovery root not found: {search_root}")
        if not root_path.is_dir():
            raise SatRootError(f"release catalog discovery root must be a directory: {search_root}")

        manifest_paths = root_path.rglob("release_catalog_manifest.json") if recursive else root_path.glob("release_catalog_manifest.json")
        for manifest_path in manifest_paths:
            release_catalog_dir = str(manifest_path.parent.resolve())
            discovered.setdefault(release_catalog_dir, release_catalog_dir)

    if not discovered:
        raise SatRootError("no signed release catalog directories found under the provided discovery roots")
    return sorted(discovered.values())


def resolve_release_catalog_directory_inputs(
    release_catalog_dirs: Sequence[str | Path],
    *,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
) -> list[str | Path]:
    resolved: list[str | Path] = []
    seen: set[str] = set()

    for release_catalog_dir in release_catalog_dirs:
        release_catalog_path = str(Path(release_catalog_dir).resolve())
        if release_catalog_path not in seen:
            resolved.append(release_catalog_dir)
            seen.add(release_catalog_path)

    if discover_under:
        for release_catalog_dir in discover_signed_release_catalog_publication_dirs(discover_under, recursive=recursive):
            if release_catalog_dir not in seen:
                resolved.append(release_catalog_dir)
                seen.add(release_catalog_dir)

    if not resolved:
        raise SatRootError("at least one release catalog directory or --discover-under path is required")
    return resolved


def discover_signed_release_catalog_index_publication_dirs(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> list[str]:
    if not search_roots:
        raise SatRootError("at least one release catalog index discovery root is required")

    discovered: Dict[str, str] = {}
    for search_root in search_roots:
        root_path = Path(search_root).resolve()
        if not root_path.exists():
            raise SatRootError(f"release catalog index discovery root not found: {search_root}")
        if not root_path.is_dir():
            raise SatRootError(f"release catalog index discovery root must be a directory: {search_root}")

        manifest_paths = root_path.rglob("release_catalog_index_manifest.json") if recursive else root_path.glob("release_catalog_index_manifest.json")
        for manifest_path in manifest_paths:
            release_catalog_index_dir = str(manifest_path.parent.resolve())
            discovered.setdefault(release_catalog_index_dir, release_catalog_index_dir)

    if not discovered:
        raise SatRootError("no signed release catalog index directories found under the provided discovery roots")
    return sorted(discovered.values())


def discover_signed_publication_registry_publication_dirs(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> list[str]:
    if not search_roots:
        raise SatRootError("at least one publication registry discovery root is required")

    discovered: Dict[str, str] = {}
    for search_root in search_roots:
        root_path = Path(search_root).resolve()
        if not root_path.exists():
            raise SatRootError(f"publication registry discovery root not found: {search_root}")
        if not root_path.is_dir():
            raise SatRootError(f"publication registry discovery root must be a directory: {search_root}")

        manifest_paths = root_path.rglob("publication_registry_manifest.json") if recursive else root_path.glob("publication_registry_manifest.json")
        for manifest_path in manifest_paths:
            publication_registry_dir = str(manifest_path.parent.resolve())
            discovered.setdefault(publication_registry_dir, publication_registry_dir)

    if not discovered:
        raise SatRootError("no publication registry directories found under the provided discovery roots")
    return sorted(discovered.values())


def _discover_workspace_dirs(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool,
    label: str,
    summary_validator: Callable[[Mapping[str, Any]], None],
) -> list[str]:
    if not search_roots:
        raise SatRootError(f"at least one {label} discovery root is required")

    discovered: Dict[str, str] = {}
    for search_root in search_roots:
        root_path = Path(search_root).resolve()
        if not root_path.exists():
            raise SatRootError(f"{label} discovery root not found: {search_root}")
        if not root_path.is_dir():
            raise SatRootError(f"{label} discovery root must be a directory: {search_root}")

        summary_paths = root_path.rglob("summary.json") if recursive else root_path.glob("summary.json")
        for summary_path in summary_paths:
            try:
                summary = _load_json_object_file(str(summary_path), label=f"{label} summary")
                summary_validator(summary)
            except SatRootError:
                continue
            workspace_dir = str(summary_path.parent.resolve())
            discovered.setdefault(workspace_dir, workspace_dir)

    if not discovered:
        raise SatRootError(f"no {label} directories found under the provided discovery roots")
    return sorted(discovered.values())


def discover_demo_catalog_workspace_dirs(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> list[str]:
    return _discover_workspace_dirs(
        search_roots,
        recursive=recursive,
        label="demo catalog workspace",
        summary_validator=validate_demo_catalog_summary_consistency,
    )


def discover_publication_stack_workspace_dirs(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> list[str]:
    return _discover_workspace_dirs(
        search_roots,
        recursive=recursive,
        label="publication stack workspace",
        summary_validator=validate_publication_stack_summary_consistency,
    )


def discover_publication_network_workspace_dirs(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> list[str]:
    return _discover_workspace_dirs(
        search_roots,
        recursive=recursive,
        label="publication network workspace",
        summary_validator=validate_publication_network_summary_consistency,
    )


def discover_publication_registry_workspace_dirs(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> list[str]:
    return _discover_workspace_dirs(
        search_roots,
        recursive=recursive,
        label="publication registry workspace",
        summary_validator=validate_publication_registry_workspace_summary_consistency,
    )


def resolve_demo_catalog_workspace_inputs(
    workspace_dirs: Sequence[str | Path],
    *,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
) -> list[str | Path]:
    resolved: list[str | Path] = []
    seen: set[str] = set()

    for workspace_dir in workspace_dirs:
        workspace_path = str(Path(workspace_dir).resolve())
        if workspace_path not in seen:
            resolved.append(workspace_dir)
            seen.add(workspace_path)

    if discover_under:
        for workspace_dir in discover_demo_catalog_workspace_dirs(discover_under, recursive=recursive):
            if workspace_dir not in seen:
                resolved.append(workspace_dir)
                seen.add(workspace_dir)

    if not resolved:
        raise SatRootError("at least one demo catalog workspace directory or --discover-under path is required")
    return resolved


def resolve_publication_stack_workspace_inputs(
    workspace_dirs: Sequence[str | Path],
    *,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
) -> list[str | Path]:
    resolved: list[str | Path] = []
    seen: set[str] = set()

    for workspace_dir in workspace_dirs:
        workspace_path = str(Path(workspace_dir).resolve())
        if workspace_path not in seen:
            resolved.append(workspace_dir)
            seen.add(workspace_path)

    if discover_under:
        for workspace_dir in discover_publication_stack_workspace_dirs(discover_under, recursive=recursive):
            if workspace_dir not in seen:
                resolved.append(workspace_dir)
                seen.add(workspace_dir)

    if not resolved:
        raise SatRootError("at least one publication stack workspace directory or --discover-under path is required")
    return resolved


def _discover_optional_paths(
    discoverer: Callable[..., list[str]],
    search_roots: Sequence[str | Path],
    *,
    recursive: bool,
) -> list[str]:
    try:
        return discoverer(search_roots, recursive=recursive)
    except SatRootError as exc:
        if str(exc).startswith("no "):
            return []
        raise


def validate_release_catalog_index_consistency(index: Mapping[str, Any]) -> None:
    release_catalogs = index.get("release_catalogs")
    release_catalog_count = index.get("release_catalog_count")
    if not isinstance(release_catalogs, list):
        raise SatRootError("release catalog index release_catalogs must be an array")
    if not isinstance(release_catalog_count, int) or release_catalog_count != len(release_catalogs):
        raise SatRootError("release catalog index release_catalog_count mismatch")


def release_catalog_index_manifest_signing_payload(manifest: Mapping[str, Any]) -> str:
    cleaned = {k: v for k, v in manifest.items() if k != "signature"}
    return canonical_json(cleaned)


def build_signed_release_catalog_index_manifest(
    release_catalog_index_json: str | Path,
    *,
    signature_scheme: str,
    key_id: str,
    signer: SignerFunction,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    if signature_scheme not in {"hmac-sha256", "ed25519"}:
        raise SatRootError(f"unsupported release catalog index signature scheme: {signature_scheme}")
    release_catalog_index_path = Path(release_catalog_index_json).resolve()
    index = _load_json_file(str(release_catalog_index_path))
    validate_instance_against_schema(index, load_release_catalog_index_schema())
    if not isinstance(index, dict):
        raise SatRootError("release catalog index must contain an object")
    validate_release_catalog_index_consistency(index)

    relative_index_path = _relative_output_path(release_catalog_index_path, base_dir=base_dir)
    manifest = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "manifest_type": "release-catalog-index-manifest",
        "release_catalog_index_path": relative_index_path,
        "release_catalog_index_hash": "sha256:" + sha256_hex_bytes(release_catalog_index_path.read_bytes()),
        "release_catalog_count": index.get("release_catalog_count"),
        "signature_scheme": signature_scheme,
        "signature_key_id": key_id,
    }
    index_metadata = index.get("index")
    if isinstance(index_metadata, dict) and index_metadata:
        manifest["index"] = copy.deepcopy(index_metadata)
    manifest["signature"] = signer(release_catalog_index_manifest_signing_payload(manifest), key_id)
    return manifest


def verify_signed_release_catalog_index_manifest(
    release_catalog_index_manifest_json: str | Path,
    *,
    verifier: SignatureVerifier,
) -> Dict[str, Any]:
    manifest_path = Path(release_catalog_index_manifest_json).resolve()
    manifest = _load_json_object_file(str(manifest_path), label="release-catalog-index-manifest")
    validate_instance_against_schema(manifest, load_release_catalog_index_manifest_schema())

    release_catalog_index_ref = manifest.get("release_catalog_index_path")
    if not isinstance(release_catalog_index_ref, str) or not release_catalog_index_ref.strip():
        raise SatRootError("release catalog index manifest release_catalog_index_path must be a non-empty string")
    release_catalog_index_path = (manifest_path.parent / release_catalog_index_ref).resolve()
    if not release_catalog_index_path.exists():
        raise SatRootError(f"release catalog index file not found: {release_catalog_index_ref}")

    index = _load_json_file(str(release_catalog_index_path))
    validate_instance_against_schema(index, load_release_catalog_index_schema())
    if not isinstance(index, dict):
        raise SatRootError("release catalog index must contain an object")
    validate_release_catalog_index_consistency(index)

    actual_index_hash = "sha256:" + sha256_hex_bytes(release_catalog_index_path.read_bytes())
    if manifest.get("release_catalog_index_hash") != actual_index_hash:
        raise SatRootError("release catalog index manifest release_catalog_index_hash mismatch")
    if manifest.get("release_catalog_count") != index.get("release_catalog_count"):
        raise SatRootError("release catalog index manifest release_catalog_count mismatch")
    if manifest.get("index") != index.get("index"):
        raise SatRootError("release catalog index manifest index metadata mismatch")
    if not verifier(manifest, release_catalog_index_manifest_signing_payload(manifest)):
        raise SatRootError("release catalog index manifest signature verification failed")

    return {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "release_catalog_index_path": release_catalog_index_ref,
        "release_catalog_index_hash": actual_index_hash,
        "release_catalog_count": index.get("release_catalog_count"),
        "index": copy.deepcopy(index.get("index")),
    }


def publish_signed_release_catalog_index(
    release_catalog_dirs: Sequence[str | Path],
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
    signer: SignerFunction,
    index_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    release_catalog_index = build_signed_release_catalog_index(
        release_catalog_dirs,
        base_dir=output_path,
        index_metadata=index_metadata,
    )
    release_catalog_index_path = output_path / "release_catalog_index.json"
    _write_json_file(release_catalog_index_path, release_catalog_index)

    release_catalog_index_manifest = build_signed_release_catalog_index_manifest(
        release_catalog_index_path,
        signature_scheme=signature_scheme,
        key_id=key_id,
        signer=signer,
        base_dir=output_path,
    )
    release_catalog_index_manifest_path = output_path / "release_catalog_index_manifest.json"
    _write_json_file(release_catalog_index_manifest_path, release_catalog_index_manifest)

    return {
        "release_catalog_index": release_catalog_index,
        "release_catalog_index_path": str(release_catalog_index_path),
        "release_catalog_index_manifest": release_catalog_index_manifest,
        "release_catalog_index_manifest_path": str(release_catalog_index_manifest_path),
    }


def bootstrap_release_catalog_index_publication(
    release_catalog_dirs: Sequence[str | Path],
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
    index_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    if signature_scheme == "hmac-sha256":
        material = bootstrap_release_hmac_material([key_id])
        signer = make_hmac_sha256_signer(material["shared_secrets"])
        _write_json_file(output_path / "release_catalog_index_secrets.json", material["shared_secrets"])
    elif signature_scheme == "ed25519":
        material = bootstrap_release_ed25519_material([key_id])
        signer = make_ed25519_signer(material["private_keys"])
        _write_json_file(output_path / "release_catalog_index_private_keys.json", material["private_keys"])
        _write_json_file(output_path / "release_catalog_index_public_keys.json", material["public_keys"])
    else:
        raise SatRootError(f"unsupported release catalog index signature scheme: {signature_scheme}")

    published = publish_signed_release_catalog_index(
        release_catalog_dirs,
        output_dir=output_path,
        signature_scheme=signature_scheme,
        key_id=key_id,
        signer=signer,
        index_metadata=index_metadata,
    )
    published["release_catalog_index_material"] = material
    return published


def _load_release_catalog_index_publication(
    release_catalog_index_dir: str | Path,
) -> tuple[Path, Path, Dict[str, Any], Dict[str, Any]]:
    index_path = Path(release_catalog_index_dir).resolve()
    if not index_path.is_dir():
        raise SatRootError("release catalog index directory must be an existing directory")

    manifest_path = index_path / "release_catalog_index_manifest.json"
    if not manifest_path.is_file():
        raise SatRootError("release_catalog_index_manifest.json is required for release catalog index publication operations")
    manifest = _load_json_object_file(str(manifest_path), label="release-catalog-index-manifest")
    validate_instance_against_schema(manifest, load_release_catalog_index_manifest_schema())

    release_catalog_index_ref = manifest.get("release_catalog_index_path")
    if not isinstance(release_catalog_index_ref, str) or not release_catalog_index_ref.strip():
        raise SatRootError("release catalog index manifest release_catalog_index_path must be a non-empty string")
    release_catalog_index_path = (manifest_path.parent / release_catalog_index_ref).resolve()
    if not release_catalog_index_path.is_file():
        raise SatRootError(f"release catalog index file not found: {release_catalog_index_ref}")

    index = _load_json_file(str(release_catalog_index_path))
    validate_instance_against_schema(index, load_release_catalog_index_schema())
    if not isinstance(index, dict):
        raise SatRootError("release catalog index must contain an object")
    validate_release_catalog_index_consistency(index)
    return manifest_path, release_catalog_index_path, manifest, index


def _load_publication_registry_publication(
    publication_registry_dir: str | Path,
) -> tuple[Path, Path, Dict[str, Any], Dict[str, Any]]:
    registry_dir = Path(publication_registry_dir).resolve()
    if not registry_dir.is_dir():
        raise SatRootError("publication registry directory must be an existing directory")

    manifest_path = registry_dir / "publication_registry_manifest.json"
    if not manifest_path.is_file():
        raise SatRootError("publication_registry_manifest.json is required for publication registry operations")
    manifest = _load_json_object_file(str(manifest_path), label="publication-registry-manifest")
    validate_instance_against_schema(manifest, load_publication_registry_manifest_schema())

    registry_ref = manifest.get("publication_registry_path")
    if not isinstance(registry_ref, str) or not registry_ref.strip():
        raise SatRootError("publication registry manifest publication_registry_path must be a non-empty string")
    registry_path = (manifest_path.parent / registry_ref).resolve()
    if not registry_path.is_file():
        raise SatRootError(f"publication registry file not found: {registry_ref}")

    registry = _load_json_file(str(registry_path))
    validate_instance_against_schema(registry, load_publication_registry_schema())
    if not isinstance(registry, dict):
        raise SatRootError("publication registry must contain an object")
    validate_publication_registry_consistency(registry)
    return manifest_path, registry_path, manifest, registry


def summarize_signed_release_catalog_index_publication(release_catalog_index_dir: str | Path) -> Dict[str, Any]:
    _, release_catalog_index_path, manifest, index = _load_release_catalog_index_publication(release_catalog_index_dir)
    release_catalogs = index.get("release_catalogs")
    assert isinstance(release_catalogs, list)
    return {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "release_catalog_index_path": manifest.get("release_catalog_index_path"),
        "release_catalog_index_hash": manifest.get("release_catalog_index_hash"),
        "release_catalog_index_resolved_path": str(release_catalog_index_path),
        "release_catalog_count": index.get("release_catalog_count"),
        "index": copy.deepcopy(index.get("index")),
        "release_catalog_paths": sorted(str(entry.get("release_catalog_path")) for entry in release_catalogs),
        "catalog_labels": sorted(
            {
                str(entry["catalog"].get("label"))
                for entry in release_catalogs
                if isinstance(entry.get("catalog"), dict) and isinstance(entry["catalog"].get("label"), str)
            }
        ),
        "release_catalogs": copy.deepcopy(release_catalogs),
    }


def summarize_publication_descriptor_index_publication(publication_descriptor_index_dir: str | Path) -> Dict[str, Any]:
    _, descriptor_index_path, manifest, index = _load_publication_descriptor_index_publication(publication_descriptor_index_dir)
    artifacts = index.get("artifacts")
    assert isinstance(artifacts, list)
    return {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "publication_descriptor_index_path": manifest.get("publication_descriptor_index_path"),
        "publication_descriptor_index_hash": manifest.get("publication_descriptor_index_hash"),
        "publication_descriptor_index_resolved_path": str(descriptor_index_path),
        "artifact_count": index.get("artifact_count"),
        "index": copy.deepcopy(index.get("index")),
        "artifact_paths": sorted(str(entry.get("artifact_path")) for entry in artifacts),
        "artifact_kinds": sorted(
            {
                str(entry.get("artifact_kind"))
                for entry in artifacts
                if isinstance(entry.get("artifact_kind"), str)
            }
        ),
        "artifacts": copy.deepcopy(artifacts),
    }


def summarize_publication_registry_publication(publication_registry_dir: str | Path) -> Dict[str, Any]:
    _, registry_path, manifest, registry = _load_publication_registry_publication(publication_registry_dir)
    summary: Dict[str, Any] = {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "publication_registry_path": manifest.get("publication_registry_path"),
        "publication_registry_hash": manifest.get("publication_registry_hash"),
        "publication_registry_resolved_path": str(registry_path),
        "component_count": registry.get("component_count"),
        "index": copy.deepcopy(registry.get("index")),
    }
    for component_name in (
        "release_catalog_index_publication",
        "publication_descriptor_index_publication",
        "publication_metadata_catalog_publication",
    ):
        component = registry.get(component_name)
        if isinstance(component, Mapping):
            summary[component_name] = copy.deepcopy(component)
    return summary


def lint_publication_descriptor_index_publication(publication_descriptor_index_dir: str | Path) -> Dict[str, Any]:
    _manifest_path, descriptor_index_path, manifest, index = _load_publication_descriptor_index_publication(publication_descriptor_index_dir)
    artifacts = index.get("artifacts")
    assert isinstance(artifacts, list)

    actual_index_hash = "sha256:" + sha256_hex_bytes(descriptor_index_path.read_bytes())
    publication_descriptor_index_hash_matches = manifest.get("publication_descriptor_index_hash") == actual_index_hash
    artifact_count_matches = manifest.get("artifact_count") == index.get("artifact_count")
    index_metadata_matches = manifest.get("index") == index.get("index")

    artifact_path_counts: Dict[str, int] = {}
    for entry in artifacts:
        artifact_path_ref = entry.get("artifact_path")
        if isinstance(artifact_path_ref, str):
            artifact_path_counts[artifact_path_ref] = artifact_path_counts.get(artifact_path_ref, 0) + 1
    duplicate_artifact_paths = sorted(value for value, count in artifact_path_counts.items() if count > 1)

    missing_artifact_paths: list[str] = []
    artifact_descriptor_mismatches: list[Dict[str, Any]] = []
    for entry in artifacts:
        artifact_path_ref = entry.get("artifact_path")
        if not isinstance(artifact_path_ref, str) or not artifact_path_ref.strip():
            continue
        resolved_artifact_path = Path(artifact_path_ref).resolve()
        if not resolved_artifact_path.exists():
            missing_artifact_paths.append(artifact_path_ref)
            continue
        current_descriptor = build_satroot_artifact_descriptor(resolved_artifact_path)
        if dict(entry) != current_descriptor:
            artifact_descriptor_mismatches.append(
                {
                    "artifact_path": artifact_path_ref,
                    "fields": sorted(
                        key
                        for key in set(entry.keys()) | set(current_descriptor.keys())
                        if entry.get(key) != current_descriptor.get(key)
                    ),
                }
            )

    return {
        "ok": not any(
            [
                not publication_descriptor_index_hash_matches,
                not artifact_count_matches,
                not index_metadata_matches,
                duplicate_artifact_paths,
                missing_artifact_paths,
                artifact_descriptor_mismatches,
            ]
        ),
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "publication_descriptor_index_path": manifest.get("publication_descriptor_index_path"),
        "publication_descriptor_index_hash_matches": publication_descriptor_index_hash_matches,
        "artifact_count_matches": artifact_count_matches,
        "index_metadata_matches": index_metadata_matches,
        "artifact_count": index.get("artifact_count"),
        "duplicate_artifact_paths": duplicate_artifact_paths,
        "missing_artifact_paths": sorted(missing_artifact_paths),
        "artifact_descriptor_mismatches": artifact_descriptor_mismatches,
    }


def lint_signed_release_catalog_index_publication(release_catalog_index_dir: str | Path) -> Dict[str, Any]:
    manifest_path, release_catalog_index_path, manifest, index = _load_release_catalog_index_publication(release_catalog_index_dir)
    release_catalogs = index.get("release_catalogs")
    assert isinstance(release_catalogs, list)

    actual_index_hash = "sha256:" + sha256_hex_bytes(release_catalog_index_path.read_bytes())
    release_catalog_index_hash_matches = manifest.get("release_catalog_index_hash") == actual_index_hash
    release_catalog_count_matches = manifest.get("release_catalog_count") == index.get("release_catalog_count")
    index_metadata_matches = manifest.get("index") == index.get("index")

    release_catalog_id_counts: Dict[str, int] = {}
    release_catalog_path_counts: Dict[str, int] = {}
    release_catalog_manifest_path_counts: Dict[str, int] = {}
    release_catalog_json_path_counts: Dict[str, int] = {}
    for entry in release_catalogs:
        release_catalog_id = entry.get("release_catalog_id")
        release_catalog_path_ref = entry.get("release_catalog_path")
        release_catalog_manifest_path_ref = entry.get("release_catalog_manifest_path")
        release_catalog_json_path_ref = entry.get("release_catalog_json_path")
        if isinstance(release_catalog_id, str):
            release_catalog_id_counts[release_catalog_id] = release_catalog_id_counts.get(release_catalog_id, 0) + 1
        if isinstance(release_catalog_path_ref, str):
            release_catalog_path_counts[release_catalog_path_ref] = release_catalog_path_counts.get(release_catalog_path_ref, 0) + 1
        if isinstance(release_catalog_manifest_path_ref, str):
            release_catalog_manifest_path_counts[release_catalog_manifest_path_ref] = release_catalog_manifest_path_counts.get(release_catalog_manifest_path_ref, 0) + 1
        if isinstance(release_catalog_json_path_ref, str):
            release_catalog_json_path_counts[release_catalog_json_path_ref] = release_catalog_json_path_counts.get(release_catalog_json_path_ref, 0) + 1

    duplicate_release_catalog_ids = sorted(value for value, count in release_catalog_id_counts.items() if count > 1)
    duplicate_release_catalog_paths = sorted(value for value, count in release_catalog_path_counts.items() if count > 1)
    duplicate_release_catalog_manifest_paths = sorted(value for value, count in release_catalog_manifest_path_counts.items() if count > 1)
    duplicate_release_catalog_json_paths = sorted(value for value, count in release_catalog_json_path_counts.items() if count > 1)

    release_catalog_manifest_path_mismatches: list[str] = []
    release_catalog_json_path_mismatches: list[str] = []
    missing_release_catalog_directories: list[str] = []
    missing_release_catalog_manifests: list[str] = []
    missing_release_catalog_json_files: list[str] = []
    release_catalog_manifest_hash_mismatches: list[str] = []
    release_catalog_hash_mismatches: list[str] = []
    release_catalog_publication_metadata_mismatches: list[Dict[str, Any]] = []

    for entry in release_catalogs:
        release_catalog_path_ref = entry.get("release_catalog_path")
        release_catalog_manifest_path_ref = entry.get("release_catalog_manifest_path")
        release_catalog_json_path_ref = entry.get("release_catalog_json_path")
        if not isinstance(release_catalog_path_ref, str) or not release_catalog_path_ref.strip():
            continue
        if not isinstance(release_catalog_manifest_path_ref, str) or not release_catalog_manifest_path_ref.strip():
            continue
        if not isinstance(release_catalog_json_path_ref, str) or not release_catalog_json_path_ref.strip():
            continue

        expected_manifest_path = (
            "release_catalog_manifest.json"
            if release_catalog_path_ref in {"", "."}
            else f"{release_catalog_path_ref}/release_catalog_manifest.json"
        )
        if release_catalog_manifest_path_ref != expected_manifest_path:
            release_catalog_manifest_path_mismatches.append(release_catalog_path_ref)

        expected_catalog_json_path = (
            "release_catalog.json"
            if release_catalog_path_ref in {"", "."}
            else f"{release_catalog_path_ref}/release_catalog.json"
        )
        if release_catalog_json_path_ref != expected_catalog_json_path:
            release_catalog_json_path_mismatches.append(release_catalog_path_ref)

        resolved_release_catalog_dir = (manifest_path.parent / release_catalog_path_ref).resolve()
        resolved_manifest_path = (manifest_path.parent / release_catalog_manifest_path_ref).resolve()
        resolved_catalog_json_path = (manifest_path.parent / release_catalog_json_path_ref).resolve()
        if not resolved_release_catalog_dir.is_dir():
            missing_release_catalog_directories.append(release_catalog_path_ref)
        if not resolved_manifest_path.is_file():
            missing_release_catalog_manifests.append(release_catalog_manifest_path_ref)
            continue
        if not resolved_catalog_json_path.is_file():
            missing_release_catalog_json_files.append(release_catalog_json_path_ref)
            continue

        actual_manifest_hash = "sha256:" + sha256_hex_bytes(resolved_manifest_path.read_bytes())
        if entry.get("release_catalog_manifest_hash") != actual_manifest_hash:
            release_catalog_manifest_hash_mismatches.append(release_catalog_manifest_path_ref)

        actual_catalog_hash = "sha256:" + sha256_hex_bytes(resolved_catalog_json_path.read_bytes())
        if entry.get("release_catalog_hash") != actual_catalog_hash:
            release_catalog_hash_mismatches.append(release_catalog_json_path_ref)

        _, _, release_catalog_manifest, release_catalog = _load_release_catalog_publication(resolved_release_catalog_dir)
        nested_releases = release_catalog.get("releases")
        assert isinstance(nested_releases, list)
        expected_release_paths = sorted(str(release.get("release_path")) for release in nested_releases)
        expected_release_labels = sorted(
            {
                str(release["release"].get("label"))
                for release in nested_releases
                if isinstance(release.get("release"), dict) and isinstance(release["release"].get("label"), str)
            }
        )
        mismatched_fields = []
        if entry.get("signature_scheme") != release_catalog_manifest.get("signature_scheme"):
            mismatched_fields.append("signature_scheme")
        if entry.get("signature_key_id") != release_catalog_manifest.get("signature_key_id"):
            mismatched_fields.append("signature_key_id")
        if entry.get("release_count") != release_catalog.get("release_count"):
            mismatched_fields.append("release_count")
        if entry.get("catalog") != release_catalog.get("catalog"):
            mismatched_fields.append("catalog")
        if sorted(entry.get("release_paths", [])) != expected_release_paths:
            mismatched_fields.append("release_paths")
        if sorted(entry.get("release_labels", [])) != expected_release_labels:
            mismatched_fields.append("release_labels")

        if mismatched_fields:
            release_catalog_publication_metadata_mismatches.append(
                {
                    "release_catalog_path": release_catalog_path_ref,
                    "fields": sorted(set(mismatched_fields)),
                }
            )

    return {
        "ok": not any(
            [
                not release_catalog_index_hash_matches,
                not release_catalog_count_matches,
                not index_metadata_matches,
                duplicate_release_catalog_ids,
                duplicate_release_catalog_paths,
                duplicate_release_catalog_manifest_paths,
                duplicate_release_catalog_json_paths,
                release_catalog_manifest_path_mismatches,
                release_catalog_json_path_mismatches,
                missing_release_catalog_directories,
                missing_release_catalog_manifests,
                missing_release_catalog_json_files,
                release_catalog_manifest_hash_mismatches,
                release_catalog_hash_mismatches,
                release_catalog_publication_metadata_mismatches,
            ]
        ),
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "release_catalog_index_path": manifest.get("release_catalog_index_path"),
        "release_catalog_index_hash_matches": release_catalog_index_hash_matches,
        "release_catalog_count_matches": release_catalog_count_matches,
        "index_metadata_matches": index_metadata_matches,
        "declared_release_catalog_count": len(release_catalogs),
        "release_catalog_count": index.get("release_catalog_count"),
        "duplicate_release_catalog_ids": duplicate_release_catalog_ids,
        "duplicate_release_catalog_paths": duplicate_release_catalog_paths,
        "duplicate_release_catalog_manifest_paths": duplicate_release_catalog_manifest_paths,
        "duplicate_release_catalog_json_paths": duplicate_release_catalog_json_paths,
        "release_catalog_manifest_path_mismatches": sorted(release_catalog_manifest_path_mismatches),
        "release_catalog_json_path_mismatches": sorted(release_catalog_json_path_mismatches),
        "missing_release_catalog_directories": sorted(missing_release_catalog_directories),
        "missing_release_catalog_manifests": sorted(missing_release_catalog_manifests),
        "missing_release_catalog_json_files": sorted(missing_release_catalog_json_files),
        "release_catalog_manifest_hash_mismatches": sorted(release_catalog_manifest_hash_mismatches),
        "release_catalog_hash_mismatches": sorted(release_catalog_hash_mismatches),
        "release_catalog_publication_metadata_mismatches": release_catalog_publication_metadata_mismatches,
    }


def lint_publication_registry_publication(publication_registry_dir: str | Path) -> Dict[str, Any]:
    manifest_path, registry_path, manifest, registry = _load_publication_registry_publication(publication_registry_dir)

    actual_registry_hash = "sha256:" + sha256_hex_bytes(registry_path.read_bytes())
    publication_registry_hash_matches = manifest.get("publication_registry_hash") == actual_registry_hash
    component_count_matches = manifest.get("component_count") == registry.get("component_count")
    index_metadata_matches = manifest.get("index") == registry.get("index")

    missing_component_directories: list[str] = []
    missing_component_manifests: list[str] = []
    missing_component_payloads: list[str] = []
    component_hash_mismatches: list[str] = []
    component_publication_metadata_mismatches: list[str] = []
    component_lint_failures: list[str] = []

    release_catalog_index_component = registry.get("release_catalog_index_publication")
    if isinstance(release_catalog_index_component, Mapping):
        publication_dir_ref = str(release_catalog_index_component.get("publication_directory_path"))
        publication_dir = (registry_path.parent / publication_dir_ref).resolve()
        manifest_ref = str(release_catalog_index_component.get("release_catalog_index_manifest_path"))
        manifest_file = (registry_path.parent / manifest_ref).resolve()
        payload_ref = str(release_catalog_index_component.get("release_catalog_index_json_path"))
        payload_file = (registry_path.parent / payload_ref).resolve()
        if not publication_dir.is_dir():
            missing_component_directories.append(publication_dir_ref)
        if not manifest_file.is_file():
            missing_component_manifests.append(manifest_ref)
        if not payload_file.is_file():
            missing_component_payloads.append(payload_ref)
        if manifest_file.is_file():
            actual_manifest_hash = "sha256:" + sha256_hex_bytes(manifest_file.read_bytes())
            if release_catalog_index_component.get("release_catalog_index_manifest_hash") != actual_manifest_hash:
                component_hash_mismatches.append("release_catalog_index_manifest_hash")
        if payload_file.is_file():
            actual_payload_hash = "sha256:" + sha256_hex_bytes(payload_file.read_bytes())
            if release_catalog_index_component.get("release_catalog_index_hash") != actual_payload_hash:
                component_hash_mismatches.append("release_catalog_index_hash")
        if publication_dir.is_dir() and manifest_file.is_file() and payload_file.is_file():
            lint_report = lint_signed_release_catalog_index_publication(publication_dir)
            if not lint_report.get("ok"):
                component_lint_failures.append("release_catalog_index_publication")
            loaded_manifest_path, loaded_payload_path, loaded_manifest, loaded_index = _load_release_catalog_index_publication(publication_dir)
            if manifest_file != loaded_manifest_path or payload_file != loaded_payload_path:
                component_publication_metadata_mismatches.append("release_catalog_index_publication.paths")
            if release_catalog_index_component.get("signature_scheme") != loaded_manifest.get("signature_scheme"):
                component_publication_metadata_mismatches.append("release_catalog_index_publication.signature_scheme")
            if release_catalog_index_component.get("signature_key_id") != loaded_manifest.get("signature_key_id"):
                component_publication_metadata_mismatches.append("release_catalog_index_publication.signature_key_id")
            if release_catalog_index_component.get("release_catalog_count") != loaded_index.get("release_catalog_count"):
                component_publication_metadata_mismatches.append("release_catalog_index_publication.release_catalog_count")

    descriptor_component = registry.get("publication_descriptor_index_publication")
    if isinstance(descriptor_component, Mapping):
        publication_dir_ref = str(descriptor_component.get("publication_directory_path"))
        publication_dir = (registry_path.parent / publication_dir_ref).resolve()
        manifest_ref = str(descriptor_component.get("publication_descriptor_index_manifest_path"))
        manifest_file = (registry_path.parent / manifest_ref).resolve()
        payload_ref = str(descriptor_component.get("publication_descriptor_index_json_path"))
        payload_file = (registry_path.parent / payload_ref).resolve()
        if not publication_dir.is_dir():
            missing_component_directories.append(publication_dir_ref)
        if not manifest_file.is_file():
            missing_component_manifests.append(manifest_ref)
        if not payload_file.is_file():
            missing_component_payloads.append(payload_ref)
        if manifest_file.is_file():
            actual_manifest_hash = "sha256:" + sha256_hex_bytes(manifest_file.read_bytes())
            if descriptor_component.get("publication_descriptor_index_manifest_hash") != actual_manifest_hash:
                component_hash_mismatches.append("publication_descriptor_index_manifest_hash")
        if payload_file.is_file():
            actual_payload_hash = "sha256:" + sha256_hex_bytes(payload_file.read_bytes())
            if descriptor_component.get("publication_descriptor_index_hash") != actual_payload_hash:
                component_hash_mismatches.append("publication_descriptor_index_hash")
        if publication_dir.is_dir() and manifest_file.is_file() and payload_file.is_file():
            lint_report = lint_publication_descriptor_index_publication(publication_dir)
            if not lint_report.get("ok"):
                component_lint_failures.append("publication_descriptor_index_publication")
            loaded_manifest_path, loaded_payload_path, loaded_manifest, loaded_index = _load_publication_descriptor_index_publication(publication_dir)
            if manifest_file != loaded_manifest_path or payload_file != loaded_payload_path:
                component_publication_metadata_mismatches.append("publication_descriptor_index_publication.paths")
            if descriptor_component.get("signature_scheme") != loaded_manifest.get("signature_scheme"):
                component_publication_metadata_mismatches.append("publication_descriptor_index_publication.signature_scheme")
            if descriptor_component.get("signature_key_id") != loaded_manifest.get("signature_key_id"):
                component_publication_metadata_mismatches.append("publication_descriptor_index_publication.signature_key_id")
            if descriptor_component.get("artifact_count") != loaded_index.get("artifact_count"):
                component_publication_metadata_mismatches.append("publication_descriptor_index_publication.artifact_count")

    metadata_component = registry.get("publication_metadata_catalog_publication")
    if isinstance(metadata_component, Mapping):
        publication_dir_ref = str(metadata_component.get("publication_directory_path"))
        publication_dir = (registry_path.parent / publication_dir_ref).resolve()
        manifest_ref = str(metadata_component.get("publication_metadata_catalog_manifest_path"))
        manifest_file = (registry_path.parent / manifest_ref).resolve()
        payload_ref = str(metadata_component.get("publication_metadata_catalog_json_path"))
        payload_file = (registry_path.parent / payload_ref).resolve()
        if not publication_dir.is_dir():
            missing_component_directories.append(publication_dir_ref)
        if not manifest_file.is_file():
            missing_component_manifests.append(manifest_ref)
        if not payload_file.is_file():
            missing_component_payloads.append(payload_ref)
        if manifest_file.is_file():
            actual_manifest_hash = "sha256:" + sha256_hex_bytes(manifest_file.read_bytes())
            if metadata_component.get("publication_metadata_catalog_manifest_hash") != actual_manifest_hash:
                component_hash_mismatches.append("publication_metadata_catalog_manifest_hash")
        if payload_file.is_file():
            actual_payload_hash = "sha256:" + sha256_hex_bytes(payload_file.read_bytes())
            if metadata_component.get("publication_metadata_catalog_hash") != actual_payload_hash:
                component_hash_mismatches.append("publication_metadata_catalog_hash")
        if publication_dir.is_dir() and manifest_file.is_file() and payload_file.is_file():
            loaded_manifest_path, loaded_payload_path, loaded_manifest, loaded_catalog = _load_publication_metadata_catalog_publication(publication_dir)
            if manifest_file != loaded_manifest_path or payload_file != loaded_payload_path:
                component_publication_metadata_mismatches.append("publication_metadata_catalog_publication.paths")
            if metadata_component.get("signature_scheme") != loaded_manifest.get("signature_scheme"):
                component_publication_metadata_mismatches.append("publication_metadata_catalog_publication.signature_scheme")
            if metadata_component.get("signature_key_id") != loaded_manifest.get("signature_key_id"):
                component_publication_metadata_mismatches.append("publication_metadata_catalog_publication.signature_key_id")
            if metadata_component.get("bundle_count") != loaded_catalog.get("bundle_count"):
                component_publication_metadata_mismatches.append("publication_metadata_catalog_publication.bundle_count")

    return {
        "ok": not any(
            [
                not publication_registry_hash_matches,
                not component_count_matches,
                not index_metadata_matches,
                missing_component_directories,
                missing_component_manifests,
                missing_component_payloads,
                component_hash_mismatches,
                component_publication_metadata_mismatches,
                component_lint_failures,
            ]
        ),
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "publication_registry_path": manifest.get("publication_registry_path"),
        "publication_registry_hash_matches": publication_registry_hash_matches,
        "component_count_matches": component_count_matches,
        "index_metadata_matches": index_metadata_matches,
        "component_count": registry.get("component_count"),
        "missing_component_directories": sorted(missing_component_directories),
        "missing_component_manifests": sorted(missing_component_manifests),
        "missing_component_payloads": sorted(missing_component_payloads),
        "component_hash_mismatches": sorted(component_hash_mismatches),
        "component_publication_metadata_mismatches": sorted(component_publication_metadata_mismatches),
        "component_lint_failures": sorted(component_lint_failures),
    }


def _load_workspace_summary(
    workspace_dir: str | Path,
    *,
    label: str,
) -> tuple[Path, Dict[str, Any]]:
    workspace_path = Path(workspace_dir).resolve()
    if not workspace_path.is_dir():
        raise SatRootError(f"{label} directory must be an existing directory")
    summary_path = workspace_path / "summary.json"
    if not summary_path.is_file():
        raise SatRootError(f"summary.json is required for {label} operations")
    summary = _load_json_object_file(str(summary_path), label=f"{label} summary")
    return workspace_path, summary


def validate_demo_catalog_summary_consistency(summary: Mapping[str, Any]) -> None:
    bundles = summary.get("bundles")
    bundle_count = summary.get("bundle_count")
    if not isinstance(bundles, list):
        raise SatRootError("demo catalog summary bundles must be an array")
    if not isinstance(bundle_count, int) or bundle_count != len(bundles):
        raise SatRootError("demo catalog summary bundle_count mismatch")


def validate_publication_stack_summary_consistency(summary: Mapping[str, Any]) -> None:
    workspaces = summary.get("workspaces")
    workspace_count = summary.get("workspace_count")
    if not isinstance(workspaces, list):
        raise SatRootError("publication stack summary workspaces must be an array")
    if not isinstance(workspace_count, int) or workspace_count != len(workspaces):
        raise SatRootError("publication stack summary workspace_count mismatch")


def validate_publication_network_summary_consistency(summary: Mapping[str, Any]) -> None:
    workspaces = summary.get("workspaces")
    stack_count = summary.get("stack_count")
    if not isinstance(workspaces, list):
        raise SatRootError("publication network summary workspaces must be an array")
    if not isinstance(stack_count, int) or stack_count != len(workspaces):
        raise SatRootError("publication network summary stack_count mismatch")


def validate_publication_registry_workspace_summary_consistency(summary: Mapping[str, Any]) -> None:
    artifact_paths = summary.get("artifact_paths")
    metadata_bundles = summary.get("publication_metadata_bundles")
    artifact_count = summary.get("artifact_count")
    metadata_bundle_count = summary.get("publication_metadata_bundle_count")
    if not isinstance(artifact_paths, list):
        raise SatRootError("publication registry workspace summary artifact_paths must be an array")
    if not isinstance(metadata_bundles, list):
        raise SatRootError("publication registry workspace summary publication_metadata_bundles must be an array")
    if not isinstance(artifact_count, int) or artifact_count != len(artifact_paths):
        raise SatRootError("publication registry workspace summary artifact_count mismatch")
    if not isinstance(metadata_bundle_count, int) or metadata_bundle_count != len(metadata_bundles):
        raise SatRootError("publication registry workspace summary publication_metadata_bundle_count mismatch")


def _resolve_publication_registry_workspace_component_dirs(workspace_path: Path) -> Dict[str, Path]:
    publication_network_dir = (workspace_path / "publication_network").resolve()
    root_release_catalog_index_dir = (workspace_path / "release_catalog_index").resolve()
    nested_release_catalog_index_dir = (publication_network_dir / "release_catalog_index").resolve()
    if root_release_catalog_index_dir.is_dir():
        release_catalog_index_dir = root_release_catalog_index_dir
    elif nested_release_catalog_index_dir.is_dir():
        release_catalog_index_dir = nested_release_catalog_index_dir
    else:
        release_catalog_index_dir = root_release_catalog_index_dir

    return {
        "publication_network_dir": publication_network_dir,
        "release_catalog_index_dir": release_catalog_index_dir,
        "publication_descriptor_index_dir": (workspace_path / "publication_descriptor_index").resolve(),
        "publication_metadata_bundles_dir": (workspace_path / "publication_metadata_bundles").resolve(),
        "publication_metadata_catalog_dir": (workspace_path / "publication_metadata_catalog").resolve(),
        "publication_registry_dir": (workspace_path / "publication_registry").resolve(),
    }


def summarize_demo_catalog_workspace(demo_catalog_dir: str | Path) -> Dict[str, Any]:
    catalog_path, summary = _load_workspace_summary(demo_catalog_dir, label="demo catalog workspace")
    validate_demo_catalog_summary_consistency(summary)
    bundles = summary.get("bundles")
    assert isinstance(bundles, list)
    release_dir = catalog_path / "release"
    release_summary = summarize_signed_release_publication(release_dir)
    return {
        "bundle_scheme": summary.get("bundle_scheme"),
        "release_scheme": summary.get("release_scheme"),
        "bundle_count": summary.get("bundle_count"),
        "bundles_dir": summary.get("bundles_dir"),
        "release_dir": summary.get("release_dir"),
        "preset_path": summary.get("preset_path"),
        "release": copy.deepcopy(summary.get("release")),
        "release_manifest_path": summary.get("release_manifest_path"),
        "bundle_index_path": summary.get("bundle_index_path"),
        "bundle_names": sorted(
            str(entry.get("bundle_name"))
            for entry in bundles
            if isinstance(entry, dict) and isinstance(entry.get("bundle_name"), str)
        ),
        "bundle_profiles": sorted(
            str(entry.get("profile"))
            for entry in bundles
            if isinstance(entry, dict) and isinstance(entry.get("profile"), str)
        ),
        "bundle_symbols": sorted(
            str(entry.get("symbol"))
            for entry in bundles
            if isinstance(entry, dict) and isinstance(entry.get("symbol"), str)
        ),
        "release_summary": release_summary,
        "bundles": copy.deepcopy(bundles),
    }


def lint_demo_catalog_workspace(demo_catalog_dir: str | Path) -> Dict[str, Any]:
    catalog_path, summary = _load_workspace_summary(demo_catalog_dir, label="demo catalog workspace")
    validate_demo_catalog_summary_consistency(summary)
    bundles = summary.get("bundles")
    assert isinstance(bundles, list)
    bundle_count_matches = isinstance(summary.get("bundle_count"), int) and summary.get("bundle_count") == len(bundles)

    actual_bundles_dir = (catalog_path / "bundles").resolve()
    actual_release_dir = (catalog_path / "release").resolve()
    actual_release_manifest_path = (actual_release_dir / "release_manifest.json").resolve()
    actual_bundle_index_path = (actual_release_dir / "bundle_index.json").resolve()

    bundles_dir_matches = summary.get("bundles_dir") == str(actual_bundles_dir)
    release_dir_matches = summary.get("release_dir") == str(actual_release_dir)
    release_manifest_path_matches = summary.get("release_manifest_path") == str(actual_release_manifest_path)
    bundle_index_path_matches = summary.get("bundle_index_path") == str(actual_bundle_index_path)

    release_summary = summarize_signed_release_publication(actual_release_dir)
    release_lint = lint_signed_release_publication(actual_release_dir)
    release_metadata_matches = summary.get("release") == release_summary.get("release")

    bundle_name_counts: Dict[str, int] = {}
    bundle_dir_counts: Dict[str, int] = {}
    for entry in bundles:
        if not isinstance(entry, dict):
            continue
        bundle_name = entry.get("bundle_name")
        bundle_dir = entry.get("bundle_dir")
        if isinstance(bundle_name, str):
            bundle_name_counts[bundle_name] = bundle_name_counts.get(bundle_name, 0) + 1
        if isinstance(bundle_dir, str):
            bundle_dir_counts[bundle_dir] = bundle_dir_counts.get(bundle_dir, 0) + 1

    duplicate_bundle_names = sorted(value for value, count in bundle_name_counts.items() if count > 1)
    duplicate_bundle_dirs = sorted(value for value, count in bundle_dir_counts.items() if count > 1)

    bundle_dir_path_mismatches: list[str] = []
    missing_bundle_dirs: list[str] = []
    missing_bundle_manifests: list[str] = []
    bundle_summary_metadata_mismatches: list[Dict[str, Any]] = []
    bundle_lint_failures: list[str] = []

    for entry in bundles:
        if not isinstance(entry, dict):
            continue
        bundle_name = entry.get("bundle_name")
        bundle_dir_ref = entry.get("bundle_dir")
        if not isinstance(bundle_name, str) or not bundle_name.strip():
            continue
        if not isinstance(bundle_dir_ref, str) or not bundle_dir_ref.strip():
            continue

        resolved_bundle_dir = Path(bundle_dir_ref).resolve()
        expected_bundle_dir = (actual_bundles_dir / bundle_name).resolve()
        if resolved_bundle_dir != expected_bundle_dir:
            bundle_dir_path_mismatches.append(bundle_name)
        if not resolved_bundle_dir.is_dir():
            missing_bundle_dirs.append(bundle_name)
            continue

        manifest_path = resolved_bundle_dir / "bundle_manifest.json"
        if not manifest_path.is_file():
            missing_bundle_manifests.append(bundle_name)
            continue

        bundle_summary = summarize_signed_ledger_bundle(resolved_bundle_dir)
        snapshot = bundle_summary.get("final_state_snapshot")
        assert isinstance(snapshot, dict)

        mismatched_fields: list[str] = []
        if entry.get("symbol") != bundle_summary.get("symbol"):
            mismatched_fields.append("symbol")
        if entry.get("profile") != snapshot.get("profile"):
            mismatched_fields.append("profile")
        if entry.get("name") != snapshot.get("name"):
            mismatched_fields.append("name")

        profile_fields = entry.get("profile_fields")
        if isinstance(profile_fields, dict):
            for field_name, field_value in profile_fields.items():
                if snapshot.get(field_name) != field_value:
                    mismatched_fields.append("profile_fields")
                    break

        structure_overrides = entry.get("structure_overrides")
        if isinstance(structure_overrides, dict):
            for field_name, field_value in structure_overrides.items():
                if snapshot.get(field_name) != field_value:
                    mismatched_fields.append("structure_overrides")
                    break

        if mismatched_fields:
            bundle_summary_metadata_mismatches.append(
                {
                    "bundle_name": bundle_name,
                    "fields": sorted(set(mismatched_fields)),
                }
            )

        if not lint_signed_ledger_bundle(resolved_bundle_dir).get("ok", False):
            bundle_lint_failures.append(bundle_name)

    return {
        "ok": not any(
            [
                not bundle_count_matches,
                not bundles_dir_matches,
                not release_dir_matches,
                not release_manifest_path_matches,
                not bundle_index_path_matches,
                not release_metadata_matches,
                not release_lint["ok"],
                duplicate_bundle_names,
                duplicate_bundle_dirs,
                bundle_dir_path_mismatches,
                missing_bundle_dirs,
                missing_bundle_manifests,
                bundle_summary_metadata_mismatches,
                bundle_lint_failures,
            ]
        ),
        "bundle_count_matches": bundle_count_matches,
        "bundles_dir_matches": bundles_dir_matches,
        "release_dir_matches": release_dir_matches,
        "release_manifest_path_matches": release_manifest_path_matches,
        "bundle_index_path_matches": bundle_index_path_matches,
        "release_metadata_matches": release_metadata_matches,
        "duplicate_bundle_names": duplicate_bundle_names,
        "duplicate_bundle_dirs": duplicate_bundle_dirs,
        "bundle_dir_path_mismatches": sorted(bundle_dir_path_mismatches),
        "missing_bundle_dirs": sorted(missing_bundle_dirs),
        "missing_bundle_manifests": sorted(missing_bundle_manifests),
        "bundle_summary_metadata_mismatches": bundle_summary_metadata_mismatches,
        "bundle_lint_failures": sorted(bundle_lint_failures),
        "release_lint": release_lint,
    }


def summarize_publication_stack_workspace(publication_stack_dir: str | Path) -> Dict[str, Any]:
    stack_path, summary = _load_workspace_summary(publication_stack_dir, label="publication stack")
    validate_publication_stack_summary_consistency(summary)
    workspaces = summary.get("workspaces")
    assert isinstance(workspaces, list)
    release_catalog_dir = stack_path / "release_catalog"
    release_catalog_summary = summarize_signed_release_catalog_publication(release_catalog_dir)
    return {
        "bundle_scheme": summary.get("bundle_scheme"),
        "release_scheme": summary.get("release_scheme"),
        "release_catalog_scheme": summary.get("release_catalog_scheme"),
        "workspace_count": summary.get("workspace_count"),
        "catalog_workspaces_dir": summary.get("catalog_workspaces_dir"),
        "release_catalog_dir": summary.get("release_catalog_dir"),
        "stack_preset_path": summary.get("stack_preset_path"),
        "release_catalog_preset_path": summary.get("release_catalog_preset_path"),
        "workspace_names": sorted(
            str(entry.get("workspace_name"))
            for entry in workspaces
            if isinstance(entry, dict) and isinstance(entry.get("workspace_name"), str)
        ),
        "workspace_preset_paths": sorted(
            str(entry.get("preset_path"))
            for entry in workspaces
            if isinstance(entry, dict) and isinstance(entry.get("preset_path"), str)
        ),
        "release_catalog_summary": release_catalog_summary,
        "workspaces": copy.deepcopy(workspaces),
    }


def lint_publication_stack_workspace(publication_stack_dir: str | Path) -> Dict[str, Any]:
    stack_path, summary = _load_workspace_summary(publication_stack_dir, label="publication stack")
    validate_publication_stack_summary_consistency(summary)
    workspaces = summary.get("workspaces")
    assert isinstance(workspaces, list)
    workspace_count_matches = isinstance(summary.get("workspace_count"), int) and summary.get("workspace_count") == len(workspaces)

    actual_catalog_workspaces_dir = (stack_path / "catalog_workspaces").resolve()
    actual_release_catalog_dir = (stack_path / "release_catalog").resolve()
    actual_release_catalog_manifest_path = (actual_release_catalog_dir / "release_catalog_manifest.json").resolve()

    catalog_workspaces_dir_matches = summary.get("catalog_workspaces_dir") == str(actual_catalog_workspaces_dir)
    release_catalog_dir_matches = summary.get("release_catalog_dir") == str(actual_release_catalog_dir)
    release_catalog_manifest_path_matches = summary.get("release_catalog_manifest_path") == str(actual_release_catalog_manifest_path)

    release_catalog_lint = lint_signed_release_catalog_publication(actual_release_catalog_dir)

    workspace_name_counts: Dict[str, int] = {}
    summary_path_counts: Dict[str, int] = {}
    workspace_dir_counts: Dict[str, int] = {}
    for entry in workspaces:
        if not isinstance(entry, dict):
            continue
        workspace_name = entry.get("workspace_name")
        workspace_dir = entry.get("workspace_dir")
        summary_path = entry.get("summary_path")
        if isinstance(workspace_name, str):
            workspace_name_counts[workspace_name] = workspace_name_counts.get(workspace_name, 0) + 1
        if isinstance(workspace_dir, str):
            workspace_dir_counts[workspace_dir] = workspace_dir_counts.get(workspace_dir, 0) + 1
        if isinstance(summary_path, str):
            summary_path_counts[summary_path] = summary_path_counts.get(summary_path, 0) + 1

    duplicate_workspace_names = sorted(value for value, count in workspace_name_counts.items() if count > 1)
    duplicate_workspace_dirs = sorted(value for value, count in workspace_dir_counts.items() if count > 1)
    duplicate_workspace_summary_paths = sorted(value for value, count in summary_path_counts.items() if count > 1)

    workspace_summary_path_mismatches: list[str] = []
    missing_workspace_dirs: list[str] = []
    missing_workspace_summaries: list[str] = []
    workspace_summary_metadata_mismatches: list[Dict[str, Any]] = []
    workspace_lint_failures: list[str] = []

    for entry in workspaces:
        if not isinstance(entry, dict):
            continue
        workspace_name = entry.get("workspace_name")
        workspace_dir_ref = entry.get("workspace_dir")
        summary_path_ref = entry.get("summary_path")
        if not isinstance(workspace_name, str):
            continue
        if not isinstance(workspace_dir_ref, str) or not workspace_dir_ref.strip():
            continue
        if not isinstance(summary_path_ref, str) or not summary_path_ref.strip():
            continue

        resolved_workspace_dir = Path(workspace_dir_ref).resolve()
        resolved_summary_path = Path(summary_path_ref).resolve()
        expected_summary_path = resolved_workspace_dir / "summary.json"
        if resolved_summary_path != expected_summary_path:
            workspace_summary_path_mismatches.append(workspace_name)
        if not resolved_workspace_dir.is_dir():
            missing_workspace_dirs.append(workspace_name)
            continue
        if not resolved_summary_path.is_file():
            missing_workspace_summaries.append(workspace_name)
            continue

        workspace_summary = _load_json_object_file(str(resolved_summary_path), label="demo catalog workspace summary")
        mismatched_fields = []
        if entry.get("bundle_count") != workspace_summary.get("bundle_count"):
            mismatched_fields.append("bundle_count")
        if entry.get("release_dir") != workspace_summary.get("release_dir"):
            mismatched_fields.append("release_dir")
        if entry.get("release_manifest_path") != workspace_summary.get("release_manifest_path"):
            mismatched_fields.append("release_manifest_path")
        if entry.get("preset_path") != workspace_summary.get("preset_path"):
            mismatched_fields.append("preset_path")
        if mismatched_fields:
            workspace_summary_metadata_mismatches.append(
                {
                    "workspace_name": workspace_name,
                    "fields": sorted(mismatched_fields),
                }
            )

        if not lint_demo_catalog_workspace(resolved_workspace_dir).get("ok", False):
            workspace_lint_failures.append(workspace_name)

    return {
        "ok": not any(
            [
                not workspace_count_matches,
                not catalog_workspaces_dir_matches,
                not release_catalog_dir_matches,
                not release_catalog_manifest_path_matches,
                not release_catalog_lint["ok"],
                duplicate_workspace_names,
                duplicate_workspace_dirs,
                duplicate_workspace_summary_paths,
                workspace_summary_path_mismatches,
                missing_workspace_dirs,
                missing_workspace_summaries,
                workspace_summary_metadata_mismatches,
                workspace_lint_failures,
            ]
        ),
        "workspace_count_matches": workspace_count_matches,
        "catalog_workspaces_dir_matches": catalog_workspaces_dir_matches,
        "release_catalog_dir_matches": release_catalog_dir_matches,
        "release_catalog_manifest_path_matches": release_catalog_manifest_path_matches,
        "duplicate_workspace_names": duplicate_workspace_names,
        "duplicate_workspace_dirs": duplicate_workspace_dirs,
        "duplicate_workspace_summary_paths": duplicate_workspace_summary_paths,
        "workspace_summary_path_mismatches": sorted(workspace_summary_path_mismatches),
        "missing_workspace_dirs": sorted(missing_workspace_dirs),
        "missing_workspace_summaries": sorted(missing_workspace_summaries),
        "workspace_summary_metadata_mismatches": workspace_summary_metadata_mismatches,
        "workspace_lint_failures": sorted(workspace_lint_failures),
        "release_catalog_lint": release_catalog_lint,
    }


def summarize_publication_network_workspace(publication_network_dir: str | Path) -> Dict[str, Any]:
    network_path, summary = _load_workspace_summary(publication_network_dir, label="publication network")
    validate_publication_network_summary_consistency(summary)
    workspaces = summary.get("workspaces")
    assert isinstance(workspaces, list)
    release_catalog_index_dir = network_path / "release_catalog_index"
    release_catalog_index_summary = summarize_signed_release_catalog_index_publication(release_catalog_index_dir)
    return {
        "bundle_scheme": summary.get("bundle_scheme"),
        "release_scheme": summary.get("release_scheme"),
        "release_catalog_scheme": summary.get("release_catalog_scheme"),
        "release_catalog_index_scheme": summary.get("release_catalog_index_scheme"),
        "stack_count": summary.get("stack_count"),
        "stack_workspaces_dir": summary.get("stack_workspaces_dir"),
        "release_catalog_index_dir": summary.get("release_catalog_index_dir"),
        "network_preset_path": summary.get("network_preset_path"),
        "release_catalog_index_preset_path": summary.get("release_catalog_index_preset_path"),
        "workspace_names": sorted(
            str(entry.get("workspace_name"))
            for entry in workspaces
            if isinstance(entry, dict) and isinstance(entry.get("workspace_name"), str)
        ),
        "workspace_preset_paths": sorted(
            str(entry.get("preset_path"))
            for entry in workspaces
            if isinstance(entry, dict) and isinstance(entry.get("preset_path"), str)
        ),
        "release_catalog_index_summary": release_catalog_index_summary,
        "workspaces": copy.deepcopy(workspaces),
    }


def lint_publication_network_workspace(publication_network_dir: str | Path) -> Dict[str, Any]:
    network_path, summary = _load_workspace_summary(publication_network_dir, label="publication network")
    validate_publication_network_summary_consistency(summary)
    workspaces = summary.get("workspaces")
    assert isinstance(workspaces, list)
    stack_count_matches = isinstance(summary.get("stack_count"), int) and summary.get("stack_count") == len(workspaces)

    actual_stack_workspaces_dir = (network_path / "stack_workspaces").resolve()
    actual_release_catalog_index_dir = (network_path / "release_catalog_index").resolve()
    actual_release_catalog_index_manifest_path = (actual_release_catalog_index_dir / "release_catalog_index_manifest.json").resolve()

    stack_workspaces_dir_matches = summary.get("stack_workspaces_dir") == str(actual_stack_workspaces_dir)
    release_catalog_index_dir_matches = summary.get("release_catalog_index_dir") == str(actual_release_catalog_index_dir)
    release_catalog_index_manifest_path_matches = summary.get("release_catalog_index_manifest_path") == str(actual_release_catalog_index_manifest_path)

    release_catalog_index_lint = lint_signed_release_catalog_index_publication(actual_release_catalog_index_dir)

    workspace_name_counts: Dict[str, int] = {}
    summary_path_counts: Dict[str, int] = {}
    workspace_dir_counts: Dict[str, int] = {}
    for entry in workspaces:
        if not isinstance(entry, dict):
            continue
        workspace_name = entry.get("workspace_name")
        workspace_dir = entry.get("workspace_dir")
        summary_path = entry.get("summary_path")
        if isinstance(workspace_name, str):
            workspace_name_counts[workspace_name] = workspace_name_counts.get(workspace_name, 0) + 1
        if isinstance(workspace_dir, str):
            workspace_dir_counts[workspace_dir] = workspace_dir_counts.get(workspace_dir, 0) + 1
        if isinstance(summary_path, str):
            summary_path_counts[summary_path] = summary_path_counts.get(summary_path, 0) + 1

    duplicate_workspace_names = sorted(value for value, count in workspace_name_counts.items() if count > 1)
    duplicate_workspace_dirs = sorted(value for value, count in workspace_dir_counts.items() if count > 1)
    duplicate_workspace_summary_paths = sorted(value for value, count in summary_path_counts.items() if count > 1)

    workspace_summary_path_mismatches: list[str] = []
    missing_workspace_dirs: list[str] = []
    missing_workspace_summaries: list[str] = []
    workspace_summary_metadata_mismatches: list[Dict[str, Any]] = []
    workspace_lint_failures: list[str] = []

    for entry in workspaces:
        if not isinstance(entry, dict):
            continue
        workspace_name = entry.get("workspace_name")
        workspace_dir_ref = entry.get("workspace_dir")
        summary_path_ref = entry.get("summary_path")
        if not isinstance(workspace_name, str):
            continue
        if not isinstance(workspace_dir_ref, str) or not workspace_dir_ref.strip():
            continue
        if not isinstance(summary_path_ref, str) or not summary_path_ref.strip():
            continue

        resolved_workspace_dir = Path(workspace_dir_ref).resolve()
        resolved_summary_path = Path(summary_path_ref).resolve()
        expected_summary_path = resolved_workspace_dir / "summary.json"
        if resolved_summary_path != expected_summary_path:
            workspace_summary_path_mismatches.append(workspace_name)
        if not resolved_workspace_dir.is_dir():
            missing_workspace_dirs.append(workspace_name)
            continue
        if not resolved_summary_path.is_file():
            missing_workspace_summaries.append(workspace_name)
            continue

        workspace_summary = _load_json_object_file(str(resolved_summary_path), label="publication stack summary")
        mismatched_fields = []
        if entry.get("catalog_workspace_count") != workspace_summary.get("workspace_count"):
            mismatched_fields.append("catalog_workspace_count")
        if entry.get("release_catalog_dir") != workspace_summary.get("release_catalog_dir"):
            mismatched_fields.append("release_catalog_dir")
        if entry.get("release_catalog_manifest_path") != workspace_summary.get("release_catalog_manifest_path"):
            mismatched_fields.append("release_catalog_manifest_path")
        if entry.get("preset_path") != workspace_summary.get("stack_preset_path"):
            mismatched_fields.append("preset_path")
        if mismatched_fields:
            workspace_summary_metadata_mismatches.append(
                {
                    "workspace_name": workspace_name,
                    "fields": sorted(mismatched_fields),
                }
            )

        if not lint_publication_stack_workspace(resolved_workspace_dir).get("ok", False):
            workspace_lint_failures.append(workspace_name)

    return {
        "ok": not any(
            [
                not stack_count_matches,
                not stack_workspaces_dir_matches,
                not release_catalog_index_dir_matches,
                not release_catalog_index_manifest_path_matches,
                not release_catalog_index_lint["ok"],
                duplicate_workspace_names,
                duplicate_workspace_dirs,
                duplicate_workspace_summary_paths,
                workspace_summary_path_mismatches,
                missing_workspace_dirs,
                missing_workspace_summaries,
                workspace_summary_metadata_mismatches,
                workspace_lint_failures,
            ]
        ),
        "stack_count_matches": stack_count_matches,
        "stack_workspaces_dir_matches": stack_workspaces_dir_matches,
        "release_catalog_index_dir_matches": release_catalog_index_dir_matches,
        "release_catalog_index_manifest_path_matches": release_catalog_index_manifest_path_matches,
        "duplicate_workspace_names": duplicate_workspace_names,
        "duplicate_workspace_dirs": duplicate_workspace_dirs,
        "duplicate_workspace_summary_paths": duplicate_workspace_summary_paths,
        "workspace_summary_path_mismatches": sorted(workspace_summary_path_mismatches),
        "missing_workspace_dirs": sorted(missing_workspace_dirs),
        "missing_workspace_summaries": sorted(missing_workspace_summaries),
        "workspace_summary_metadata_mismatches": workspace_summary_metadata_mismatches,
        "workspace_lint_failures": sorted(workspace_lint_failures),
        "release_catalog_index_lint": release_catalog_index_lint,
    }


def summarize_publication_registry_workspace(publication_registry_workspace_dir: str | Path) -> Dict[str, Any]:
    workspace_path, summary = _load_workspace_summary(publication_registry_workspace_dir, label="publication registry workspace")
    validate_publication_registry_workspace_summary_consistency(summary)
    metadata_bundles = summary.get("publication_metadata_bundles")
    assert isinstance(metadata_bundles, list)

    component_dirs = _resolve_publication_registry_workspace_component_dirs(workspace_path)
    publication_network_dir = component_dirs["publication_network_dir"]
    release_catalog_index_dir = component_dirs["release_catalog_index_dir"]
    publication_descriptor_index_dir = component_dirs["publication_descriptor_index_dir"]
    publication_metadata_catalog_dir = component_dirs["publication_metadata_catalog_dir"]
    publication_registry_dir = component_dirs["publication_registry_dir"]

    release_catalog_index_summary = summarize_signed_release_catalog_index_publication(release_catalog_index_dir)
    publication_descriptor_index_summary = summarize_publication_descriptor_index_publication(publication_descriptor_index_dir)
    _catalog_manifest_path, _catalog_path, _catalog_manifest, publication_metadata_catalog = _load_publication_metadata_catalog_publication(
        publication_metadata_catalog_dir
    )
    publication_registry_summary = summarize_publication_registry_publication(publication_registry_dir)

    summary_payload: Dict[str, Any] = {
        "signature_scheme": summary.get("signature_scheme"),
        "source_publication_network_dir": summary.get("source_publication_network_dir"),
        "publication_network_dir": summary.get("publication_network_dir"),
        "artifact_count": summary.get("artifact_count"),
        "artifact_paths": copy.deepcopy(summary.get("artifact_paths")),
        "release_catalog_index_source_dir": summary.get("release_catalog_index_source_dir"),
        "release_catalog_index_dir": summary.get("release_catalog_index_dir"),
        "publication_descriptor_index_dir": summary.get("publication_descriptor_index_dir"),
        "publication_metadata_bundles_dir": summary.get("publication_metadata_bundles_dir"),
        "publication_metadata_bundle_count": summary.get("publication_metadata_bundle_count"),
        "publication_metadata_catalog_dir": summary.get("publication_metadata_catalog_dir"),
        "publication_registry_dir": summary.get("publication_registry_dir"),
        "publication_descriptor_index_manifest_path": summary.get("publication_descriptor_index_manifest_path"),
        "publication_metadata_catalog_manifest_path": summary.get("publication_metadata_catalog_manifest_path"),
        "publication_registry_manifest_path": summary.get("publication_registry_manifest_path"),
        "publication_metadata_bundle_names": sorted(
            str(entry.get("bundle_name"))
            for entry in metadata_bundles
            if isinstance(entry, dict) and isinstance(entry.get("bundle_name"), str)
        ),
        "publication_metadata_artifact_kinds": sorted(
            {
                str(entry.get("artifact_kind"))
                for entry in metadata_bundles
                if isinstance(entry, dict) and isinstance(entry.get("artifact_kind"), str)
            }
        ),
        "release_catalog_index_summary": release_catalog_index_summary,
        "publication_descriptor_index_summary": publication_descriptor_index_summary,
        "publication_metadata_catalog": copy.deepcopy(publication_metadata_catalog),
        "publication_registry_summary": publication_registry_summary,
        "publication_metadata_bundles": copy.deepcopy(metadata_bundles),
    }
    if publication_network_dir.is_dir():
        summary_payload["publication_network_summary"] = summarize_publication_network_workspace(publication_network_dir)
    return summary_payload


def lint_publication_registry_workspace(publication_registry_workspace_dir: str | Path) -> Dict[str, Any]:
    workspace_path, summary = _load_workspace_summary(publication_registry_workspace_dir, label="publication registry workspace")
    validate_publication_registry_workspace_summary_consistency(summary)
    metadata_bundles = summary.get("publication_metadata_bundles")
    artifact_paths = summary.get("artifact_paths")
    assert isinstance(metadata_bundles, list)
    assert isinstance(artifact_paths, list)

    component_dirs = _resolve_publication_registry_workspace_component_dirs(workspace_path)
    publication_network_dir = component_dirs["publication_network_dir"]
    actual_release_catalog_index_dir = component_dirs["release_catalog_index_dir"]
    actual_publication_descriptor_index_dir = component_dirs["publication_descriptor_index_dir"]
    actual_publication_metadata_bundles_dir = component_dirs["publication_metadata_bundles_dir"]
    actual_publication_metadata_catalog_dir = component_dirs["publication_metadata_catalog_dir"]
    actual_publication_registry_dir = component_dirs["publication_registry_dir"]

    artifact_count_matches = isinstance(summary.get("artifact_count"), int) and summary.get("artifact_count") == len(artifact_paths)
    publication_metadata_bundle_count_matches = (
        isinstance(summary.get("publication_metadata_bundle_count"), int)
        and summary.get("publication_metadata_bundle_count") == len(metadata_bundles)
    )
    publication_network_dir_matches = summary.get("publication_network_dir") == (
        str(publication_network_dir) if publication_network_dir.is_dir() else None
    )
    release_catalog_index_dir_matches = summary.get("release_catalog_index_dir") == str(actual_release_catalog_index_dir)
    publication_descriptor_index_dir_matches = summary.get("publication_descriptor_index_dir") == str(actual_publication_descriptor_index_dir)
    publication_metadata_bundles_dir_matches = summary.get("publication_metadata_bundles_dir") == str(actual_publication_metadata_bundles_dir)
    publication_metadata_catalog_dir_matches = summary.get("publication_metadata_catalog_dir") == str(actual_publication_metadata_catalog_dir)
    publication_registry_dir_matches = summary.get("publication_registry_dir") == str(actual_publication_registry_dir)
    publication_descriptor_index_manifest_path_matches = summary.get("publication_descriptor_index_manifest_path") == str(
        (actual_publication_descriptor_index_dir / "publication_descriptor_index_manifest.json").resolve()
    )
    publication_metadata_catalog_manifest_path_matches = summary.get("publication_metadata_catalog_manifest_path") == str(
        (actual_publication_metadata_catalog_dir / "publication_metadata_catalog_manifest.json").resolve()
    )
    publication_registry_manifest_path_matches = summary.get("publication_registry_manifest_path") == str(
        (actual_publication_registry_dir / "publication_registry_manifest.json").resolve()
    )

    release_catalog_index_summary = summarize_signed_release_catalog_index_publication(actual_release_catalog_index_dir)
    release_catalog_index_lint = lint_signed_release_catalog_index_publication(actual_release_catalog_index_dir)
    _descriptor_manifest_path, _descriptor_index_path, _descriptor_manifest, publication_descriptor_index = _load_publication_descriptor_index_publication(
        actual_publication_descriptor_index_dir
    )
    publication_descriptor_index_summary = summarize_publication_descriptor_index_publication(actual_publication_descriptor_index_dir)
    publication_descriptor_index_lint = lint_publication_descriptor_index_publication(actual_publication_descriptor_index_dir)
    _catalog_manifest_path, _catalog_path, _catalog_manifest, publication_metadata_catalog = _load_publication_metadata_catalog_publication(
        actual_publication_metadata_catalog_dir
    )
    _registry_manifest_path, _registry_path, _registry_manifest, publication_registry = _load_publication_registry_publication(
        actual_publication_registry_dir
    )
    publication_registry_lint = lint_publication_registry_publication(actual_publication_registry_dir)
    publication_network_lint = (
        lint_publication_network_workspace(publication_network_dir)
        if publication_network_dir.is_dir()
        else None
    )

    artifact_paths_match_descriptor_index = sorted(str(value) for value in artifact_paths) == sorted(
        str(value) for value in publication_descriptor_index_summary.get("artifact_paths", [])
    )
    publication_descriptor_index_metadata_matches = summary.get("publication_descriptor_index") == publication_descriptor_index
    publication_metadata_catalog_matches = summary.get("publication_metadata_catalog") == publication_metadata_catalog
    publication_registry_matches = summary.get("publication_registry") == publication_registry

    bundle_name_counts: Dict[str, int] = {}
    bundle_dir_counts: Dict[str, int] = {}
    bundle_manifest_path_counts: Dict[str, int] = {}
    bundle_report_path_counts: Dict[str, int] = {}
    bundle_descriptor_path_counts: Dict[str, int] = {}
    for entry in metadata_bundles:
        if not isinstance(entry, dict):
            continue
        bundle_name = entry.get("bundle_name")
        bundle_dir = entry.get("bundle_dir")
        manifest_path = entry.get("publication_metadata_manifest_path")
        report_path = entry.get("publication_report_path")
        descriptor_path = entry.get("publication_descriptor_path")
        if isinstance(bundle_name, str):
            bundle_name_counts[bundle_name] = bundle_name_counts.get(bundle_name, 0) + 1
        if isinstance(bundle_dir, str):
            bundle_dir_counts[bundle_dir] = bundle_dir_counts.get(bundle_dir, 0) + 1
        if isinstance(manifest_path, str):
            bundle_manifest_path_counts[manifest_path] = bundle_manifest_path_counts.get(manifest_path, 0) + 1
        if isinstance(report_path, str):
            bundle_report_path_counts[report_path] = bundle_report_path_counts.get(report_path, 0) + 1
        if isinstance(descriptor_path, str):
            bundle_descriptor_path_counts[descriptor_path] = bundle_descriptor_path_counts.get(descriptor_path, 0) + 1

    duplicate_bundle_names = sorted(value for value, count in bundle_name_counts.items() if count > 1)
    duplicate_bundle_dirs = sorted(value for value, count in bundle_dir_counts.items() if count > 1)
    duplicate_bundle_manifest_paths = sorted(value for value, count in bundle_manifest_path_counts.items() if count > 1)
    duplicate_bundle_report_paths = sorted(value for value, count in bundle_report_path_counts.items() if count > 1)
    duplicate_bundle_descriptor_paths = sorted(value for value, count in bundle_descriptor_path_counts.items() if count > 1)

    bundle_dir_path_mismatches: list[str] = []
    missing_bundle_dirs: list[str] = []
    missing_bundle_manifests: list[str] = []
    missing_bundle_reports: list[str] = []
    missing_bundle_descriptors: list[str] = []
    bundle_summary_metadata_mismatches: list[Dict[str, Any]] = []
    metadata_bundle_lint_failures: list[str] = []

    for entry in metadata_bundles:
        if not isinstance(entry, dict):
            continue
        bundle_name = entry.get("bundle_name")
        bundle_dir_ref = entry.get("bundle_dir")
        if not isinstance(bundle_name, str) or not bundle_name.strip():
            continue
        if not isinstance(bundle_dir_ref, str) or not bundle_dir_ref.strip():
            continue

        resolved_bundle_dir = Path(bundle_dir_ref).resolve()
        expected_bundle_dir = (actual_publication_metadata_bundles_dir / bundle_name).resolve()
        if resolved_bundle_dir != expected_bundle_dir:
            bundle_dir_path_mismatches.append(bundle_name)
        if not resolved_bundle_dir.is_dir():
            missing_bundle_dirs.append(bundle_name)
            continue

        manifest_path = resolved_bundle_dir / "publication_metadata_manifest.json"
        report_path = resolved_bundle_dir / "publication_report.md"
        descriptor_path = resolved_bundle_dir / "publication_descriptor.json"
        if not manifest_path.is_file():
            missing_bundle_manifests.append(bundle_name)
            continue
        if not report_path.is_file():
            missing_bundle_reports.append(bundle_name)
            continue
        if not descriptor_path.is_file():
            missing_bundle_descriptors.append(bundle_name)
            continue

        mismatched_fields: list[str] = []
        if entry.get("publication_metadata_manifest_path") != str(manifest_path.resolve()):
            mismatched_fields.append("publication_metadata_manifest_path")
        if entry.get("publication_report_path") != str(report_path.resolve()):
            mismatched_fields.append("publication_report_path")
        if entry.get("publication_descriptor_path") != str(descriptor_path.resolve()):
            mismatched_fields.append("publication_descriptor_path")

        try:
            _loaded_manifest_path, _loaded_report_path, _loaded_descriptor_path, manifest, descriptor = _load_publication_metadata_bundle_publication(
                resolved_bundle_dir
            )
        except SatRootError:
            metadata_bundle_lint_failures.append(bundle_name)
            continue

        if entry.get("artifact_kind") != manifest.get("artifact_kind"):
            mismatched_fields.append("artifact_kind")
        if entry.get("artifact_path") != manifest.get("artifact_path"):
            mismatched_fields.append("artifact_path")
        if entry.get("artifact_kind") != descriptor.get("artifact_kind"):
            mismatched_fields.append("descriptor.artifact_kind")
        if entry.get("artifact_path") != descriptor.get("artifact_path"):
            mismatched_fields.append("descriptor.artifact_path")

        if mismatched_fields:
            bundle_summary_metadata_mismatches.append(
                {
                    "bundle_name": bundle_name,
                    "fields": sorted(set(mismatched_fields)),
                }
            )

    return {
        "ok": not any(
            [
                not artifact_count_matches,
                not publication_metadata_bundle_count_matches,
                not publication_network_dir_matches,
                not release_catalog_index_dir_matches,
                not publication_descriptor_index_dir_matches,
                not publication_metadata_bundles_dir_matches,
                not publication_metadata_catalog_dir_matches,
                not publication_registry_dir_matches,
                not publication_descriptor_index_manifest_path_matches,
                not publication_metadata_catalog_manifest_path_matches,
                not publication_registry_manifest_path_matches,
                not artifact_paths_match_descriptor_index,
                not publication_descriptor_index_metadata_matches,
                not publication_metadata_catalog_matches,
                not publication_registry_matches,
                not release_catalog_index_lint["ok"],
                not publication_descriptor_index_lint["ok"],
                not publication_registry_lint["ok"],
                publication_network_lint is not None and not publication_network_lint["ok"],
                duplicate_bundle_names,
                duplicate_bundle_dirs,
                duplicate_bundle_manifest_paths,
                duplicate_bundle_report_paths,
                duplicate_bundle_descriptor_paths,
                bundle_dir_path_mismatches,
                missing_bundle_dirs,
                missing_bundle_manifests,
                missing_bundle_reports,
                missing_bundle_descriptors,
                bundle_summary_metadata_mismatches,
                metadata_bundle_lint_failures,
            ]
        ),
        "artifact_count_matches": artifact_count_matches,
        "publication_metadata_bundle_count_matches": publication_metadata_bundle_count_matches,
        "publication_network_dir_matches": publication_network_dir_matches,
        "release_catalog_index_dir_matches": release_catalog_index_dir_matches,
        "publication_descriptor_index_dir_matches": publication_descriptor_index_dir_matches,
        "publication_metadata_bundles_dir_matches": publication_metadata_bundles_dir_matches,
        "publication_metadata_catalog_dir_matches": publication_metadata_catalog_dir_matches,
        "publication_registry_dir_matches": publication_registry_dir_matches,
        "publication_descriptor_index_manifest_path_matches": publication_descriptor_index_manifest_path_matches,
        "publication_metadata_catalog_manifest_path_matches": publication_metadata_catalog_manifest_path_matches,
        "publication_registry_manifest_path_matches": publication_registry_manifest_path_matches,
        "artifact_paths_match_descriptor_index": artifact_paths_match_descriptor_index,
        "publication_descriptor_index_metadata_matches": publication_descriptor_index_metadata_matches,
        "publication_metadata_catalog_matches": publication_metadata_catalog_matches,
        "publication_registry_matches": publication_registry_matches,
        "duplicate_bundle_names": duplicate_bundle_names,
        "duplicate_bundle_dirs": duplicate_bundle_dirs,
        "duplicate_bundle_manifest_paths": duplicate_bundle_manifest_paths,
        "duplicate_bundle_report_paths": duplicate_bundle_report_paths,
        "duplicate_bundle_descriptor_paths": duplicate_bundle_descriptor_paths,
        "bundle_dir_path_mismatches": sorted(bundle_dir_path_mismatches),
        "missing_bundle_dirs": sorted(missing_bundle_dirs),
        "missing_bundle_manifests": sorted(missing_bundle_manifests),
        "missing_bundle_reports": sorted(missing_bundle_reports),
        "missing_bundle_descriptors": sorted(missing_bundle_descriptors),
        "bundle_summary_metadata_mismatches": bundle_summary_metadata_mismatches,
        "metadata_bundle_lint_failures": sorted(metadata_bundle_lint_failures),
        "release_catalog_index_lint": release_catalog_index_lint,
        "publication_descriptor_index_lint": publication_descriptor_index_lint,
        "publication_network_lint": publication_network_lint,
        "publication_registry_lint": publication_registry_lint,
    }


def verify_signed_ledger_bundle(bundle_dir: str | Path) -> Dict[str, Any]:
    bundle_path = Path(bundle_dir)
    manifest = _load_validated_bundle_manifest(bundle_path)

    scheme = manifest.get("scheme")

    files = manifest.get("files")
    assert isinstance(files, dict)
    file_hashes = manifest.get("file_hashes")
    if not isinstance(file_hashes, dict):
        raise SatRootError("bundle manifest file_hashes must be an object")

    def require_bundle_file(key: str) -> Path:
        relative = files.get(key)
        if not isinstance(relative, str) or not relative.strip():
            raise SatRootError(f"bundle manifest missing file entry for {key}")
        path = bundle_path / relative
        if not path.exists():
            raise SatRootError(f"bundle file not found for {key}: {relative}")
        expected_hash = file_hashes.get(key)
        if expected_hash is not None:
            actual_hash = "sha256:" + sha256_hex_bytes(path.read_bytes())
            if actual_hash != expected_hash:
                raise SatRootError(f"bundle file hash mismatch for {key}")
        return path

    signed_events_path = require_bundle_file("signed_events")
    signed_events = _load_json_file(str(signed_events_path))
    if not isinstance(signed_events, list):
        raise SatRootError("signed_events bundle file must contain a JSON array")

    if scheme == "hmac-sha256":
        secrets_path = require_bundle_file("secrets")
        secrets = _load_json_object_file(str(secrets_path), label="secrets")
        verifier = make_hmac_sha256_verifier(secrets)
    else:
        public_keys_path = require_bundle_file("public_keys")
        public_keys = _load_json_object_file(str(public_keys_path), label="public_keys")
        verifier = make_ed25519_verifier(public_keys)

    final_state = replay(signed_events, verifier=verifier)
    final_snapshot = final_state.snapshot()

    record_count = manifest.get("record_count")
    if not isinstance(record_count, int) or record_count != len(signed_events):
        raise SatRootError("bundle record_count mismatch")
    if manifest.get("root_id") != final_snapshot["root_id"]:
        raise SatRootError("bundle root_id mismatch")
    if manifest.get("symbol") != final_snapshot["symbol"]:
        raise SatRootError("bundle symbol mismatch")
    if manifest.get("final_event_id") != final_snapshot["last_event_id"]:
        raise SatRootError("bundle final_event_id mismatch")
    if manifest.get("final_state_snapshot") != final_snapshot:
        raise SatRootError("bundle final_state_snapshot mismatch")
    if manifest.get("final_state_hash") != final_state.state_hash():
        raise SatRootError("bundle final_state_hash mismatch")

    annotated_expected = bool(manifest.get("annotated_output"))
    annotated_verified = False
    if annotated_expected:
        annotated_path = require_bundle_file("annotated_signed_events")
        annotated_events = _load_json_file(str(annotated_path))
        if not isinstance(annotated_events, list):
            raise SatRootError("annotated_signed_events bundle file must contain a JSON array")
        annotated_state = replay(annotated_events, verifier=verifier)
        if annotated_state.state_hash() != final_state.state_hash():
            raise SatRootError("annotated bundle final_state_hash mismatch")
        annotated_verified = True

    return {
        "scheme": scheme,
        "verification_material_scope": manifest.get("verification_material_scope"),
        "record_count": len(signed_events),
        "root_id": final_snapshot["root_id"],
        "symbol": final_snapshot["symbol"],
        "final_event_id": final_snapshot["last_event_id"],
        "final_state_hash": final_state.state_hash(),
        "annotated_verified": annotated_verified,
    }


def require_fields(event: Dict[str, Any], fields: Iterable[str]) -> None:
    missing = [field for field in fields if field not in event]
    if missing:
        raise SatRootError("missing required field(s): " + ", ".join(missing))


def parse_positive_amount(value: str) -> int:
    amount = parse_amount(value)
    if amount <= 0:
        raise SatRootError(f"amount must be positive: {value!r}")
    return amount


def validate_root_id(root_id: str) -> None:
    if not isinstance(root_id, str) or not ROOT_ID_RE.fullmatch(root_id):
        raise SatRootError(f"invalid root_id: {root_id!r}")


def parse_decimals(value: Any) -> int:
    if not isinstance(value, int) or value < 0 or value > 18:
        raise SatRootError(f"invalid decimals: {value!r}")
    return value


def require_account_name(name: Any, field_name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise SatRootError(f"invalid account name for {field_name}: {name!r}")
    return name


def validate_signature_metadata(event: Dict[str, Any]) -> None:
    scheme = event.get("signature_scheme", "demo")
    if not isinstance(scheme, str) or scheme not in SUPPORTED_SIGNATURE_SCHEMES:
        raise SatRootError(f"unsupported signature_scheme: {scheme!r}")

    key_id = event.get("signature_key_id")
    if scheme == "demo":
        if key_id is not None:
            raise SatRootError("signature_key_id is not allowed for demo signatures")
        return

    if not isinstance(key_id, str) or not key_id.strip():
        raise SatRootError(f"signature_key_id is required for {scheme}")


def validate_stated_event_id(event: Dict[str, Any]) -> None:
    stated = event.get("event_id")
    if stated is not None and stated != event_id(event):
        raise SatRootError("event_id mismatch")


def validate_profile_genesis(event: Dict[str, Any]) -> None:
    profile = event.get("profile")
    if profile is None:
        return

    rules = load_profile_registry().get(profile)
    if rules is None:
        raise SatRootError(f"unsupported profile: {profile}")

    require_fields(event, ["profile_mode", *rules["required_fields"]])
    if event.get("profile_mode") != rules["profile_mode"]:
        raise SatRootError(f"bad profile_mode for {profile}")
    _validate_profile_metadata_fields(event, ["profile_mode", *rules["required_fields"]])
    _validate_profile_specific_genesis(profile, event)


def _validate_profile_metadata_fields(event: Mapping[str, Any], field_names: Sequence[str]) -> None:
    for field_name in field_names:
        value = event.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise SatRootError(f"invalid profile field {field_name}: expected non-empty string")


def _validate_profile_specific_genesis(profile: str, event: Mapping[str, Any]) -> None:
    if profile == "SATROOT-STABLE-1":
        _validate_stable_profile_genesis(event)
    elif profile == "SATROOT-MACHINE-1":
        _validate_machine_profile_genesis(event)
    elif profile == "SATROOT-RECEIPT-1":
        _validate_receipt_profile_genesis(event)
    elif profile == "SATROOT-IDENTITY-1":
        _validate_identity_profile_genesis(event)
    elif profile == "SATROOT-LICENSE-1":
        _validate_license_profile_genesis(event)


def _validate_stable_profile_genesis(event: Mapping[str, Any]) -> None:
    reference_unit = event.get("reference_unit")
    assert isinstance(reference_unit, str)
    if not REFERENCE_UNIT_RE.fullmatch(reference_unit):
        raise SatRootError(f"invalid stable reference_unit: {reference_unit!r}")
    if event.get("profile_mode") == "reference-only":
        if event.get("redemption") != "none":
            raise SatRootError("reference-only stable profile requires redemption=none")
        if event.get("reserve_model") != "none":
            raise SatRootError("reference-only stable profile requires reserve_model=none")


def _validate_machine_profile_genesis(event: Mapping[str, Any]) -> None:
    _validate_compact_identifier_field(event, "service_scope")
    _validate_compact_identifier_field(event, "billing_unit")
    _validate_compact_identifier_field(event, "consumption_model")
    _validate_compact_identifier_field(event, "intended_use")


def _validate_receipt_profile_genesis(event: Mapping[str, Any]) -> None:
    _validate_compact_identifier_field(event, "document_type")
    _validate_compact_identifier_field(event, "intended_use")
    settlement_unit = event.get("settlement_unit")
    assert isinstance(settlement_unit, str)
    if not REFERENCE_UNIT_RE.fullmatch(settlement_unit):
        raise SatRootError(f"invalid receipt settlement_unit: {settlement_unit!r}")
    _validate_singleton_object_profile(event, profile_label="receipt")


def _validate_identity_profile_genesis(event: Mapping[str, Any]) -> None:
    _validate_compact_identifier_field(event, "identity_type")
    _validate_compact_identifier_field(event, "authority_scope")
    _validate_compact_identifier_field(event, "intended_use")
    _validate_singleton_object_profile(event, profile_label="identity")


def _validate_license_profile_genesis(event: Mapping[str, Any]) -> None:
    _validate_compact_identifier_field(event, "license_type")
    _validate_compact_identifier_field(event, "usage_scope")
    _validate_compact_identifier_field(event, "intended_use")
    _validate_singleton_object_profile(event, profile_label="license")


def _validate_compact_identifier_field(event: Mapping[str, Any], field_name: str) -> None:
    value = event.get(field_name)
    assert isinstance(value, str)
    if not COMPACT_IDENTIFIER_RE.fullmatch(value):
        raise SatRootError(f"invalid profile field {field_name}: expected compact identifier")


def _validate_singleton_object_profile(event: Mapping[str, Any], *, profile_label: str) -> None:
    if parse_decimals(event.get("decimals")) != 0:
        raise SatRootError(f"{profile_label} profile requires decimals=0")
    if parse_amount(event.get("max_supply")) != 1:
        raise SatRootError(f"{profile_label} profile requires max_supply=1")
    initial_balances = event.get("initial_balances")
    if not isinstance(initial_balances, dict):
        raise SatRootError(f"{profile_label} profile initial_balances must be an object")
    if sum(parse_amount(amount) for amount in initial_balances.values()) != 1:
        raise SatRootError(f"{profile_label} profile requires exactly one issued unit at genesis")


def validate_state_hash(event: Dict[str, Any], state: "SatRootState") -> None:
    stated = event.get("state_hash")
    if stated is not None and stated != state.state_hash():
        raise SatRootError("state_hash mismatch")


def extract_genesis_metadata(event: Dict[str, Any]) -> Dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in event.items() if key not in CORE_GENESIS_FIELDS}


@dataclass
class SatRootState:
    root_id: str
    symbol: str
    name: str
    decimals: int
    max_supply: Optional[int]
    mint_authority: str
    transfer_model: str
    profile: Optional[str] = None
    profile_mode: Optional[str] = None
    genesis_metadata: Dict[str, Any] = field(default_factory=dict)
    balances: Dict[str, int] = field(default_factory=dict)
    supply: int = 0
    sequence: int = 0
    last_event_id: Optional[str] = None

    def commitment_snapshot(self) -> Dict[str, Any]:
        return {
            "root_id": self.root_id,
            "symbol": self.symbol,
            "name": self.name,
            "decimals": self.decimals,
            "max_supply": str(self.max_supply) if self.max_supply is not None else None,
            "mint_authority": self.mint_authority,
            "profile": self.profile,
            "profile_mode": self.profile_mode,
            "balances": {k: str(v) for k, v in sorted(self.balances.items()) if v != 0},
            "supply": str(self.supply),
            "sequence": self.sequence,
            "last_event_id": self.last_event_id,
        }

    def snapshot(self) -> Dict[str, Any]:
        snapshot = self.commitment_snapshot()
        snapshot["transfer_model"] = self.transfer_model
        snapshot["genesis_metadata"] = copy.deepcopy(self.genesis_metadata)
        return snapshot

    def state_hash(self) -> str:
        return "sha256:" + sha256_hex(canonical_json(self.commitment_snapshot()))


def apply_genesis(event: Dict[str, Any]) -> SatRootState:
    require_fields(
        event,
        [
            "protocol",
            "version",
            "action",
            "root_id",
            "sequence",
            "symbol",
            "name",
            "decimals",
            "max_supply",
            "mint_authority",
            "initial_balances",
        ],
    )
    if event.get("protocol") != "SATROOT-1" or event.get("version") != "0.1":
        raise SatRootError("unsupported protocol/version")
    if event.get("action") != "genesis":
        raise SatRootError("first event must be genesis")
    if event.get("sequence") != 0:
        raise SatRootError("genesis sequence must be 0")
    validate_root_id(event["root_id"])
    validate_stated_event_id(event)
    validate_profile_genesis(event)
    if event.get("transfer_model") != "account-ledger":
        raise SatRootError("unsupported transfer_model")

    initial = {
        require_account_name(acct, "initial_balances"): parse_amount(amount)
        for acct, amount in event.get("initial_balances", {}).items()
    }
    supply = sum(initial.values())
    max_supply = parse_amount(event["max_supply"]) if event.get("max_supply") is not None else None
    if max_supply is not None and supply > max_supply:
        raise SatRootError("initial supply exceeds max supply")

    state = SatRootState(
        root_id=event["root_id"],
        symbol=event["symbol"],
        name=event["name"],
        decimals=parse_decimals(event.get("decimals", 0)),
        max_supply=max_supply,
        mint_authority=event["mint_authority"],
        transfer_model=event["transfer_model"],
        profile=event.get("profile"),
        profile_mode=event.get("profile_mode"),
        genesis_metadata=extract_genesis_metadata(event),
        balances=initial,
        supply=supply,
        sequence=0,
        last_event_id=event_id(event),
    )
    validate_state_hash(event, state)
    return state


def verify_signature(event: Dict[str, Any], verifier: SignatureVerifier) -> None:
    payload = signing_payload(event)
    if not verifier(event, payload):
        raise SatRootError("signature verification failed")


def require_next_event(state: SatRootState, event: Dict[str, Any], verifier: SignatureVerifier) -> None:
    require_fields(event, ["protocol", "version", "action", "root_id", "sequence", "prev_event_id", "signer", "signature"])
    if event.get("protocol") != "SATROOT-1" or event.get("version") != "0.1":
        raise SatRootError("unsupported protocol/version")
    if event.get("root_id") != state.root_id:
        raise SatRootError("root_id mismatch")
    if event.get("sequence") != state.sequence + 1:
        raise SatRootError("bad sequence")
    if event.get("prev_event_id") != state.last_event_id:
        raise SatRootError("bad prev_event_id")
    validate_stated_event_id(event)
    validate_signature_metadata(event)
    if event.get("profile") not in (None, state.profile):
        raise SatRootError("profile mismatch")
    if event.get("profile_mode") not in (None, state.profile_mode):
        raise SatRootError("profile_mode mismatch")
    verify_signature(event, verifier)


def apply_event(state: SatRootState, event: Dict[str, Any], verifier: SignatureVerifier = demo_signature_verifier) -> SatRootState:
    next_state = copy.deepcopy(state)
    require_next_event(next_state, event, verifier)

    action = event.get("action")

    if action == "mint":
        require_fields(event, ["to", "amount"])
        amount = parse_positive_amount(event["amount"])
        if event.get("signer") != next_state.mint_authority:
            raise SatRootError("unauthorized mint")
        to = require_account_name(event["to"], "to")
        if next_state.max_supply is not None and next_state.supply + amount > next_state.max_supply:
            raise SatRootError("mint exceeds max supply")
        next_state.balances[to] = next_state.balances.get(to, 0) + amount
        next_state.supply += amount

    elif action == "transfer":
        require_fields(event, ["from", "to", "amount"])
        amount = parse_positive_amount(event["amount"])
        sender = require_account_name(event["from"], "from")
        recipient = require_account_name(event["to"], "to")
        # v0.1 placeholder: signer must equal sender account string.
        if event.get("signer") != sender:
            raise SatRootError("unauthorized transfer")
        if next_state.balances.get(sender, 0) < amount:
            raise SatRootError("insufficient balance")
        next_state.balances[sender] -= amount
        next_state.balances[recipient] = next_state.balances.get(recipient, 0) + amount

    elif action == "burn":
        require_fields(event, ["from", "amount"])
        amount = parse_positive_amount(event["amount"])
        burner = require_account_name(event["from"], "from")
        if event.get("signer") != burner:
            raise SatRootError("unauthorized burn")
        if next_state.balances.get(burner, 0) < amount:
            raise SatRootError("insufficient balance")
        next_state.balances[burner] -= amount
        next_state.supply -= amount

    elif action == "rotate-authority":
        require_fields(event, ["new_mint_authority"])
        if event.get("signer") != next_state.mint_authority:
            raise SatRootError("unauthorized authority rotation")
        next_state.mint_authority = require_account_name(event["new_mint_authority"], "new_mint_authority")

    else:
        raise SatRootError(f"unsupported action: {action}")

    next_state.sequence = event["sequence"]
    next_state.last_event_id = event_id(event)
    validate_state_hash(event, next_state)
    return next_state


def replay(events: Iterable[Dict[str, Any]], verifier: SignatureVerifier = demo_signature_verifier) -> SatRootState:
    iterator = iter(events)
    try:
        first = next(iterator)
    except StopIteration as exc:
        raise SatRootError("empty ledger") from exc

    state = apply_genesis(first)
    for event in iterator:
        state = apply_event(state, event, verifier=verifier)
    return state


def sign_event_record(
    event: Dict[str, Any],
    *,
    scheme: str,
    key_id: Optional[str] = None,
    signer: Optional[SignerFunction] = None,
) -> Dict[str, Any]:
    signed = copy.deepcopy(event)
    if scheme == "demo":
        signed.pop("signature_key_id", None)
        signed["signature_scheme"] = "demo"
        signed["signature"] = "demo"
    else:
        if signer is None:
            raise SatRootError("signer function is required for non-demo signatures")
        if not isinstance(key_id, str) or not key_id.strip():
            raise SatRootError("key_id is required for non-demo signatures")
        signed["signature_scheme"] = scheme
        signed["signature_key_id"] = key_id
        signed["signature"] = signer(signing_payload(signed), key_id)
    signed["event_id"] = event_id(signed)
    return signed


def sign_ledger_events(
    events: Sequence[Dict[str, Any]],
    *,
    scheme: str,
    signer_key_ids: Optional[Mapping[str, str]] = None,
    signer: Optional[SignerFunction] = None,
    verifier: SignatureVerifier = demo_signature_verifier,
    include_state_hash: bool = False,
) -> list[Dict[str, Any]]:
    if not events:
        raise SatRootError("empty ledger")

    signed_events = copy.deepcopy(list(events))
    state = apply_genesis(signed_events[0])
    previous_event_id = state.last_event_id

    for event in signed_events[1:]:
        event["prev_event_id"] = previous_event_id
        if scheme == "demo":
            signed = sign_event_record(event, scheme="demo")
        else:
            signer_name = event.get("signer")
            if not isinstance(signer_name, str) or not signer_name:
                raise SatRootError("signer is required for non-demo signatures")
            if signer_key_ids is None:
                raise SatRootError("signer_key_ids are required for non-demo signatures")
            key_id = signer_key_ids.get(signer_name)
            if key_id is None:
                raise SatRootError(f"missing signer_key_id for signer: {signer_name}")
            signed = sign_event_record(event, scheme=scheme, key_id=key_id, signer=signer)

        next_state = apply_event(state, signed, verifier=verifier)
        if include_state_hash:
            signed["state_hash"] = next_state.state_hash()
        event.clear()
        event.update(signed)
        state = next_state
        previous_event_id = state.last_event_id

    return signed_events


def annotate_ledger_events(
    events: Sequence[Dict[str, Any]],
    *,
    verifier: SignatureVerifier = demo_signature_verifier,
    include_event_id: bool = True,
    include_state_hash: bool = True,
) -> list[Dict[str, Any]]:
    if not events:
        raise SatRootError("empty ledger")

    annotated_events = copy.deepcopy(list(events))
    genesis = annotated_events[0]
    if include_event_id:
        genesis["event_id"] = event_id(genesis)
    state = apply_genesis(genesis)
    if include_state_hash:
        genesis["state_hash"] = state.state_hash()

    for index in range(1, len(annotated_events)):
        event = annotated_events[index]
        if include_event_id:
            event["event_id"] = event_id(event)
        state = apply_event(state, event, verifier=verifier)
        if include_state_hash:
            event["state_hash"] = state.state_hash()

    return annotated_events


def _load_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_json_object_file(path: str, *, label: str) -> Dict[str, Any]:
    data = _load_json_file(path)
    if not isinstance(data, dict):
        raise SatRootError(f"{label} must contain an object")
    return data


def _dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def rendered_json_sha256(data: Any) -> str:
    return "sha256:" + sha256_hex_bytes(_dump_json(data).encode("utf-8"))


def _write_output(data: Any, output_path: Optional[str]) -> None:
    rendered = _dump_json(data)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
    else:
        sys.stdout.write(rendered)


def _write_text_output(text: str, output_path: Optional[str]) -> None:
    if output_path:
        with open(output_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


def _write_json_file(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(_dump_json(data))


def _bundle_output_artifacts(
    bundle: Mapping[str, Any],
    *,
    include_private_keys: bool,
    genesis: Optional[Mapping[str, Any]] = None,
) -> tuple[Dict[str, str], Dict[str, Any]]:
    output_files: Dict[str, str] = {
        "signer_key_map": "signer_key_map.json",
        "signed_events": "signed_events.json",
    }
    output_payloads: Dict[str, Any] = {
        "signer_key_map": bundle["material"]["signer_key_map"],
        "signed_events": bundle["signed_events"],
    }
    if genesis is not None:
        output_files["genesis"] = "genesis.json"
        output_payloads["genesis"] = copy.deepcopy(dict(genesis))

    scheme = bundle["scheme"]
    if scheme == "hmac-sha256":
        output_files["secrets"] = "secrets.json"
        output_payloads["secrets"] = bundle["material"]["shared_secrets"]
    elif scheme == "ed25519":
        output_files["public_keys"] = "public_keys.json"
        output_payloads["public_keys"] = bundle["material"]["public_keys"]
        if include_private_keys:
            output_files["private_keys"] = "private_keys.json"
            output_payloads["private_keys"] = bundle["material"]["private_keys"]
    else:
        raise SatRootError(f"unsupported bundle scheme: {scheme}")

    if bundle["annotated_events"] is not None:
        output_files["annotated_signed_events"] = "annotated_signed_events.json"
        output_payloads["annotated_signed_events"] = bundle["annotated_events"]

    output_files["bundle_manifest"] = "bundle_manifest.json"
    output_file_hashes = {key: rendered_json_sha256(data) for key, data in output_payloads.items()}
    manifest = build_signed_ledger_bundle_manifest(bundle, output_files=output_files, output_file_hashes=output_file_hashes)
    output_payloads["bundle_manifest"] = manifest
    return output_files, output_payloads


def _write_bundle_output_dir(
    bundle: Mapping[str, Any],
    *,
    output_dir: str | Path,
    include_private_keys: bool,
    genesis: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    output_files, output_payloads = _bundle_output_artifacts(
        bundle,
        include_private_keys=include_private_keys,
        genesis=genesis,
    )
    for key, data in output_payloads.items():
        _write_json_file(output_path / output_files[key], data)
    return {
        "output_dir": str(output_path),
        "files": output_files,
        "bundle_manifest_path": str(output_path / output_files["bundle_manifest"]),
    }


def bootstrap_stable_reference_demo_release(
    *,
    symbol: str,
    name: str,
    bundle_scheme: str,
    output_dir: str | Path,
    release_key_id: str,
    release_scheme: Optional[str] = None,
    reference_unit: str = "USD",
    root_id: Optional[str] = None,
    issuer: str = "issuer",
    merchant_account: str = "merchant",
    service_account: str = "api_node",
    initial_balance: str = "25000000",
    merchant_amount: str = "1250000",
    service_amount: str = "250000",
    merchant_burn_amount: str = "5000",
    intended_use: str = "invoice-credit-accounting",
    rules_hash: Optional[str] = None,
    nonce: Optional[str] = None,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
    verifier_only: bool = False,
    release_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    resolved_release_scheme = release_scheme or bundle_scheme
    if verifier_only and bundle_scheme != "ed25519":
        raise SatRootError("--verifier-only is only supported for ed25519 bundles")

    root_output_dir = Path(output_dir).resolve()
    bundle_dir = root_output_dir / "bundle"
    release_dir = root_output_dir / "release"
    bundle = bootstrap_stable_reference_demo_bundle(
        symbol=symbol,
        name=name,
        scheme=bundle_scheme,
        reference_unit=reference_unit,
        root_id=root_id,
        issuer=issuer,
        merchant_account=merchant_account,
        service_account=service_account,
        initial_balance=initial_balance,
        merchant_amount=merchant_amount,
        service_amount=service_amount,
        merchant_burn_amount=merchant_burn_amount,
        intended_use=intended_use,
        rules_hash=rules_hash,
        nonce=nonce,
        key_prefix=key_prefix,
        key_suffix=key_suffix,
        include_state_hash=include_state_hash,
        include_annotation=include_annotation,
    )
    bundle_output = _write_bundle_output_dir(
        bundle,
        output_dir=bundle_dir,
        include_private_keys=not verifier_only,
        genesis=bundle["genesis"],
    )
    published = bootstrap_release_publication(
        [bundle_dir],
        output_dir=release_dir,
        signature_scheme=resolved_release_scheme,
        key_id=release_key_id,
        release_metadata=release_metadata,
    )
    return {
        "bundle": bundle,
        "bundle_output": bundle_output,
        "bundle_dir": str(bundle_dir.resolve()),
        "release_dir": str(release_dir.resolve()),
        "release_publication": published,
        "release_material": published["release_material"],
    }


def bootstrap_machine_credit_demo_bundle(
    *,
    symbol: str,
    name: str,
    scheme: str,
    service_scope: str = "api-compute",
    billing_unit: str = "request",
    consumption_model: str = "burn-on-use",
    root_id: Optional[str] = None,
    issuer: str = "issuer",
    tenant_account: str = "tenant_a",
    worker_account: str = "worker_node",
    max_supply: Optional[str] = None,
    initial_balance: str = "100000000",
    tenant_amount: str = "5000000",
    worker_amount: str = "1200000",
    worker_burn_amount: str = "200000",
    intended_use: str = "machine-api-credit",
    profile_fields: Optional[Mapping[str, str]] = None,
    rules_hash: Optional[str] = None,
    nonce: Optional[str] = None,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
) -> Dict[str, Any]:
    demo = bootstrap_machine_credit_demo_ledger(
        symbol=symbol,
        name=name,
        service_scope=service_scope,
        billing_unit=billing_unit,
        consumption_model=consumption_model,
        root_id=root_id,
        issuer=issuer,
        tenant_account=tenant_account,
        worker_account=worker_account,
        max_supply=max_supply,
        initial_balance=initial_balance,
        tenant_amount=tenant_amount,
        worker_amount=worker_amount,
        worker_burn_amount=worker_burn_amount,
        intended_use=intended_use,
        profile_fields=profile_fields,
        rules_hash=rules_hash,
        nonce=nonce,
        include_annotation=False,
    )
    bundle = bootstrap_signed_ledger_bundle(
        demo["events"],
        scheme=scheme,
        key_prefix=key_prefix,
        key_suffix=key_suffix,
        include_state_hash=include_state_hash,
        include_annotation=include_annotation,
    )
    result = dict(bundle)
    result["genesis"] = copy.deepcopy(demo["events"][0])
    result["events"] = copy.deepcopy(demo["events"])
    return result


def bootstrap_machine_credit_demo_release(
    *,
    symbol: str,
    name: str,
    bundle_scheme: str,
    output_dir: str | Path,
    release_key_id: str,
    release_scheme: Optional[str] = None,
    service_scope: str = "api-compute",
    billing_unit: str = "request",
    consumption_model: str = "burn-on-use",
    root_id: Optional[str] = None,
    issuer: str = "issuer",
    tenant_account: str = "tenant_a",
    worker_account: str = "worker_node",
    max_supply: Optional[str] = None,
    initial_balance: str = "100000000",
    tenant_amount: str = "5000000",
    worker_amount: str = "1200000",
    worker_burn_amount: str = "200000",
    intended_use: str = "machine-api-credit",
    rules_hash: Optional[str] = None,
    nonce: Optional[str] = None,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
    verifier_only: bool = False,
    release_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    resolved_release_scheme = release_scheme or bundle_scheme
    if verifier_only and bundle_scheme != "ed25519":
        raise SatRootError("--verifier-only is only supported for ed25519 bundles")

    root_output_dir = Path(output_dir).resolve()
    bundle_dir = root_output_dir / "bundle"
    release_dir = root_output_dir / "release"
    bundle = bootstrap_machine_credit_demo_bundle(
        symbol=symbol,
        name=name,
        scheme=bundle_scheme,
        service_scope=service_scope,
        billing_unit=billing_unit,
        consumption_model=consumption_model,
        root_id=root_id,
        issuer=issuer,
        tenant_account=tenant_account,
        worker_account=worker_account,
        max_supply=max_supply,
        initial_balance=initial_balance,
        tenant_amount=tenant_amount,
        worker_amount=worker_amount,
        worker_burn_amount=worker_burn_amount,
        intended_use=intended_use,
        rules_hash=rules_hash,
        nonce=nonce,
        key_prefix=key_prefix,
        key_suffix=key_suffix,
        include_state_hash=include_state_hash,
        include_annotation=include_annotation,
    )
    bundle_output = _write_bundle_output_dir(
        bundle,
        output_dir=bundle_dir,
        include_private_keys=not verifier_only,
        genesis=bundle["genesis"],
    )
    published = bootstrap_release_publication(
        [bundle_dir],
        output_dir=release_dir,
        signature_scheme=resolved_release_scheme,
        key_id=release_key_id,
        release_metadata=release_metadata,
    )
    return {
        "bundle": bundle,
        "bundle_output": bundle_output,
        "bundle_dir": str(bundle_dir.resolve()),
        "release_dir": str(release_dir.resolve()),
        "release_publication": published,
        "release_material": published["release_material"],
    }


def bootstrap_demo_catalog_release(
    *,
    bundle_scheme: str,
    output_dir: str | Path,
    release_key_id: str,
    release_scheme: Optional[str] = None,
    profiles: Optional[Sequence[str]] = None,
    symbol_overrides: Optional[Mapping[str, str]] = None,
    name_overrides: Optional[Mapping[str, str]] = None,
    profile_field_overrides: Optional[Mapping[str, Mapping[str, str]]] = None,
    profile_structure_overrides: Optional[Mapping[str, Mapping[str, Any]]] = None,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
    verifier_only: bool = False,
    release_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    resolved_release_scheme = release_scheme or bundle_scheme
    if verifier_only and bundle_scheme != "ed25519":
        raise SatRootError("--verifier-only is only supported for ed25519 bundles")

    root_output_dir = Path(output_dir).resolve()
    bundles_dir = root_output_dir / "bundles"
    release_dir = root_output_dir / "release"
    spec_map = {spec["profile"]: copy.deepcopy(spec) for spec in DEMO_CATALOG_BUNDLE_SPECS}
    selected_profiles = list(DEMO_CATALOG_PROFILES if profiles is None else profiles)
    selected_profile_set: set[str] = set()
    ordered_profiles: list[str] = []
    for profile in selected_profiles:
        if profile not in spec_map:
            raise SatRootError(f"unsupported demo catalog profile: {profile}")
        if profile in selected_profile_set:
            raise SatRootError(f"duplicate demo catalog profile: {profile}")
        selected_profile_set.add(profile)
        ordered_profiles.append(profile)

    resolved_symbol_overrides = dict(symbol_overrides or {})
    resolved_name_overrides = dict(name_overrides or {})
    resolved_profile_field_overrides = {profile: dict(fields) for profile, fields in (profile_field_overrides or {}).items()}
    resolved_profile_structure_overrides = {
        profile: dict(fields) for profile, fields in (profile_structure_overrides or {}).items()
    }
    for profile in resolved_symbol_overrides:
        if profile not in selected_profile_set:
            raise SatRootError(f"symbol override requires selected demo catalog profile: {profile}")
    for profile in resolved_name_overrides:
        if profile not in selected_profile_set:
            raise SatRootError(f"name override requires selected demo catalog profile: {profile}")
    for profile in resolved_profile_field_overrides:
        if profile not in selected_profile_set:
            raise SatRootError(f"profile field override requires selected demo catalog profile: {profile}")
    for profile in resolved_profile_structure_overrides:
        if profile not in selected_profile_set:
            raise SatRootError(f"profile structure override requires selected demo catalog profile: {profile}")

    bundle_entries: list[Dict[str, Any]] = []
    bundle_dirs: list[str] = []
    for profile in ordered_profiles:
        spec = spec_map[profile]
        bundle_name = spec["bundle_name"]
        symbol = resolved_symbol_overrides.get(profile, spec["symbol"])
        name = resolved_name_overrides.get(profile, spec["name"])
        profile_fields = resolved_profile_field_overrides.get(profile)
        structure_overrides = resolved_profile_structure_overrides.get(profile, {})
        bundle_dir = bundles_dir / bundle_name

        if profile == "SATROOT-STABLE-1":
            bundle = bootstrap_stable_reference_demo_bundle(
                symbol=symbol,
                name=name,
                scheme=bundle_scheme,
                profile_fields=profile_fields,
                **structure_overrides,
                key_prefix=key_prefix,
                key_suffix=key_suffix,
                include_state_hash=include_state_hash,
                include_annotation=include_annotation,
            )
        elif profile == "SATROOT-MACHINE-1":
            bundle = bootstrap_machine_credit_demo_bundle(
                symbol=symbol,
                name=name,
                scheme=bundle_scheme,
                profile_fields=profile_fields,
                **structure_overrides,
                key_prefix=key_prefix,
                key_suffix=key_suffix,
                include_state_hash=include_state_hash,
                include_annotation=include_annotation,
            )
        else:
            holder_account, next_holder, archive_account = _resolve_singleton_demo_accounts(profile)
            bundle = bootstrap_singleton_object_demo_bundle(
                profile=profile,
                symbol=symbol,
                name=name,
                scheme=bundle_scheme,
                holder_account=structure_overrides.get("holder_account", holder_account),
                next_holder=structure_overrides.get("next_holder", next_holder),
                archive_account=structure_overrides.get("archive_account", archive_account),
                profile_fields=profile_fields,
                retire=structure_overrides.get("retire", True),
                key_prefix=key_prefix,
                key_suffix=key_suffix,
                include_state_hash=include_state_hash,
                include_annotation=include_annotation,
            )

        bundle_output = _write_bundle_output_dir(
            bundle,
            output_dir=bundle_dir,
            include_private_keys=not verifier_only,
            genesis=bundle["genesis"],
        )
        bundle_dirs.append(str(bundle_dir.resolve()))
        bundle_entries.append(
            {
                "bundle_name": bundle_name,
                "profile": profile,
                "symbol": symbol,
                "name": name,
                "profile_fields": copy.deepcopy(profile_fields),
                "structure_overrides": copy.deepcopy(structure_overrides),
                "bundle_dir": str(bundle_dir.resolve()),
                "bundle_output": bundle_output,
            }
        )

    published = bootstrap_release_publication(
        bundle_dirs,
        output_dir=release_dir,
        signature_scheme=resolved_release_scheme,
        key_id=release_key_id,
        release_metadata=release_metadata,
    )
    return {
        "bundle_scheme": bundle_scheme,
        "release_scheme": resolved_release_scheme,
        "bundle_count": len(bundle_entries),
        "bundles_dir": str(bundles_dir.resolve()),
        "release_dir": str(release_dir.resolve()),
        "bundles": bundle_entries,
        "release_publication": published,
        "release_material": published["release_material"],
    }


def _merge_nested_override_maps(
    base: Optional[Mapping[str, Mapping[str, Any]]],
    override: Optional[Mapping[str, Mapping[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {
        key: dict(value) for key, value in (base or {}).items()
    }
    for key, value in (override or {}).items():
        merged.setdefault(key, {})
        merged[key].update(value)
    return merged


def write_demo_catalog_workspace(
    *,
    bundle_scheme: str,
    output_dir: str | Path,
    release_key_id: str,
    release_scheme: Optional[str] = None,
    profiles: Optional[Sequence[str]] = None,
    symbol_overrides: Optional[Mapping[str, str]] = None,
    name_overrides: Optional[Mapping[str, str]] = None,
    profile_field_overrides: Optional[Mapping[str, Mapping[str, str]]] = None,
    profile_structure_overrides: Optional[Mapping[str, Mapping[str, Any]]] = None,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
    verifier_only: bool = False,
    release_metadata: Optional[Mapping[str, str]] = None,
    preset_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    catalog = bootstrap_demo_catalog_release(
        bundle_scheme=bundle_scheme,
        release_scheme=release_scheme,
        release_key_id=release_key_id,
        output_dir=output_dir,
        profiles=profiles,
        symbol_overrides=symbol_overrides,
        name_overrides=name_overrides,
        profile_field_overrides=profile_field_overrides,
        profile_structure_overrides=profile_structure_overrides,
        key_prefix=key_prefix,
        key_suffix=key_suffix,
        include_state_hash=include_state_hash,
        include_annotation=include_annotation,
        verifier_only=verifier_only,
        release_metadata=release_metadata,
    )
    summary = {
        "bundle_scheme": catalog["bundle_scheme"],
        "release_scheme": catalog["release_scheme"],
        "bundle_count": catalog["bundle_count"],
        "bundles_dir": catalog["bundles_dir"],
        "release_dir": catalog["release_dir"],
        "preset_path": None if preset_path is None else str(Path(preset_path).resolve()),
        "release": {key: value for key, value in (release_metadata or {}).items() if isinstance(value, str) and value.strip()},
        "bundles": [
            {
                "bundle_name": entry["bundle_name"],
                "profile": entry["profile"],
                "symbol": entry["symbol"],
                "name": entry["name"],
                "profile_fields": entry["profile_fields"],
                "structure_overrides": entry["structure_overrides"],
                "bundle_dir": entry["bundle_dir"],
            }
            for entry in catalog["bundles"]
        ],
        "release_manifest_path": catalog["release_publication"]["release_manifest_path"],
        "bundle_index_path": catalog["release_publication"]["bundle_index_path"],
    }
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    summary_path = output_path / "summary.json"
    _write_json_file(summary_path, summary)
    return {
        "catalog": catalog,
        "summary": summary,
        "summary_path": str(summary_path.resolve()),
    }


def relocate_demo_catalog_workspace_summary(demo_catalog_dir: str | Path) -> Dict[str, Any]:
    workspace_path, summary = _load_workspace_summary(demo_catalog_dir, label="demo catalog workspace")
    validate_demo_catalog_summary_consistency(summary)
    bundles = summary.get("bundles")
    assert isinstance(bundles, list)

    summary["bundles_dir"] = str((workspace_path / "bundles").resolve())
    summary["release_dir"] = str((workspace_path / "release").resolve())
    summary["release_manifest_path"] = str((workspace_path / "release" / "release_manifest.json").resolve())
    summary["bundle_index_path"] = str((workspace_path / "release" / "bundle_index.json").resolve())

    for entry in bundles:
        if not isinstance(entry, dict):
            continue
        bundle_name = entry.get("bundle_name")
        if isinstance(bundle_name, str) and bundle_name.strip():
            entry["bundle_dir"] = str((workspace_path / "bundles" / bundle_name).resolve())

    _write_json_file(workspace_path / "summary.json", summary)
    return summary


def write_publication_stack_workspace(
    *,
    bundle_scheme: str,
    output_dir: str | Path,
    release_key_id: str,
    release_catalog_key_id: str,
    catalog_preset_paths: Sequence[str | Path],
    release_catalog_metadata: Optional[Mapping[str, str]] = None,
    release_scheme: Optional[str] = None,
    release_catalog_scheme: Optional[str] = None,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
    verifier_only: bool = False,
    stack_preset_path: Optional[str | Path] = None,
    release_catalog_preset_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    resolved_catalog_preset_paths = [Path(value).resolve() for value in catalog_preset_paths]
    if not resolved_catalog_preset_paths:
        raise SatRootError("publication stack workspace requires at least one catalog preset path")

    catalog_workspace_names = _unique_workspace_names(resolved_catalog_preset_paths)
    root_output_dir = Path(output_dir).resolve()
    catalog_workspaces_dir = root_output_dir / "catalog_workspaces"
    release_catalog_dir = root_output_dir / "release_catalog"
    release_dirs: list[str] = []
    workspace_entries: list[Dict[str, Any]] = []

    for preset_path, workspace_name in zip(resolved_catalog_preset_paths, catalog_workspace_names):
        preset = load_demo_catalog_preset(preset_path)
        workspace_dir = catalog_workspaces_dir / workspace_name
        workspace = write_demo_catalog_workspace(
            bundle_scheme=bundle_scheme,
            release_scheme=release_scheme,
            release_key_id=release_key_id,
            output_dir=workspace_dir,
            profiles=preset.get("profiles"),
            symbol_overrides=preset.get("symbol_overrides"),
            name_overrides=preset.get("name_overrides"),
            profile_field_overrides=preset.get("profile_field_overrides"),
            profile_structure_overrides=preset.get("profile_structure_overrides"),
            key_prefix=key_prefix,
            key_suffix=key_suffix,
            include_state_hash=include_state_hash,
            include_annotation=include_annotation,
            verifier_only=verifier_only,
            release_metadata=preset.get("release_metadata"),
            preset_path=preset_path,
        )
        release_dirs.append(workspace["summary"]["release_dir"])
        workspace_entries.append(
            {
                "workspace_name": workspace_name,
                "preset_path": str(preset_path),
                "workspace_dir": str(workspace_dir.resolve()),
                "summary_path": workspace["summary_path"],
                "bundle_count": workspace["summary"]["bundle_count"],
                "release_dir": workspace["summary"]["release_dir"],
                "release_manifest_path": workspace["summary"]["release_manifest_path"],
            }
        )

    published = bootstrap_release_catalog_publication(
        release_dirs,
        output_dir=release_catalog_dir,
        signature_scheme=release_catalog_scheme or bundle_scheme,
        key_id=release_catalog_key_id,
        catalog_metadata=release_catalog_metadata,
    )
    summary = {
        "bundle_scheme": bundle_scheme,
        "release_scheme": release_scheme or bundle_scheme,
        "release_catalog_scheme": release_catalog_scheme or bundle_scheme,
        "workspace_count": len(workspace_entries),
        "catalog_workspaces_dir": str(catalog_workspaces_dir.resolve()),
        "release_catalog_dir": str(release_catalog_dir.resolve()),
        "catalog_preset_paths": [str(path) for path in resolved_catalog_preset_paths],
        "stack_preset_path": None if stack_preset_path is None else str(Path(stack_preset_path).resolve()),
        "release_catalog_preset_path": None if release_catalog_preset_path is None else str(Path(release_catalog_preset_path).resolve()),
        "release_catalog": copy.deepcopy(published["release_catalog"]),
        "release_catalog_manifest_path": published["release_catalog_manifest_path"],
        "workspaces": workspace_entries,
    }
    root_output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = root_output_dir / "summary.json"
    _write_json_file(summary_path, summary)
    return {
        "summary": summary,
        "summary_path": str(summary_path.resolve()),
        "release_catalog_dir": str(release_catalog_dir.resolve()),
        "release_catalog_publication": published,
    }


def relocate_publication_stack_workspace_summary(publication_stack_dir: str | Path) -> Dict[str, Any]:
    stack_path, summary = _load_workspace_summary(publication_stack_dir, label="publication stack")
    validate_publication_stack_summary_consistency(summary)
    workspaces = summary.get("workspaces")
    assert isinstance(workspaces, list)

    summary["catalog_workspaces_dir"] = str((stack_path / "catalog_workspaces").resolve())
    summary["release_catalog_dir"] = str((stack_path / "release_catalog").resolve())
    summary["release_catalog_manifest_path"] = str((stack_path / "release_catalog" / "release_catalog_manifest.json").resolve())

    for entry in workspaces:
        if not isinstance(entry, dict):
            continue
        workspace_name = entry.get("workspace_name")
        if not isinstance(workspace_name, str) or not workspace_name.strip():
            continue
        workspace_dir = (stack_path / "catalog_workspaces" / workspace_name).resolve()
        nested_summary = relocate_demo_catalog_workspace_summary(workspace_dir)
        entry["workspace_dir"] = str(workspace_dir)
        entry["summary_path"] = str((workspace_dir / "summary.json").resolve())
        entry["bundle_count"] = nested_summary.get("bundle_count")
        entry["release_dir"] = nested_summary.get("release_dir")
        entry["release_manifest_path"] = nested_summary.get("release_manifest_path")

    _write_json_file(stack_path / "summary.json", summary)
    return summary


def write_publication_network_workspace(
    *,
    bundle_scheme: str,
    output_dir: str | Path,
    release_key_id: str,
    release_catalog_key_id: str,
    release_catalog_index_key_id: str,
    stack_preset_paths: Sequence[str | Path],
    release_catalog_index_metadata: Optional[Mapping[str, str]] = None,
    release_scheme: Optional[str] = None,
    release_catalog_scheme: Optional[str] = None,
    release_catalog_index_scheme: Optional[str] = None,
    key_prefix: str = "",
    key_suffix: str = "-key",
    include_state_hash: bool = True,
    include_annotation: bool = True,
    verifier_only: bool = False,
    network_preset_path: Optional[str | Path] = None,
    release_catalog_index_preset_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    resolved_stack_preset_paths = [Path(value).resolve() for value in stack_preset_paths]
    if not resolved_stack_preset_paths:
        raise SatRootError("publication network workspace requires at least one stack preset path")

    stack_workspace_names = _unique_workspace_names(resolved_stack_preset_paths)
    root_output_dir = Path(output_dir).resolve()
    stack_workspaces_dir = root_output_dir / "stack_workspaces"
    release_catalog_index_dir = root_output_dir / "release_catalog_index"
    release_catalog_dirs: list[str] = []
    workspace_entries: list[Dict[str, Any]] = []

    for preset_path, workspace_name in zip(resolved_stack_preset_paths, stack_workspace_names):
        stack_preset = load_publication_stack_preset(preset_path)
        workspace_dir = stack_workspaces_dir / workspace_name
        workspace = write_publication_stack_workspace(
            bundle_scheme=bundle_scheme,
            release_scheme=release_scheme,
            release_key_id=release_key_id,
            release_catalog_scheme=release_catalog_scheme,
            release_catalog_key_id=release_catalog_key_id,
            output_dir=workspace_dir,
            catalog_preset_paths=stack_preset.get("catalog_preset_paths", []),
            release_catalog_metadata=stack_preset.get("release_catalog_metadata"),
            key_prefix=key_prefix,
            key_suffix=key_suffix,
            include_state_hash=include_state_hash,
            include_annotation=include_annotation,
            verifier_only=verifier_only,
            stack_preset_path=preset_path,
        )
        release_catalog_dirs.append(workspace["summary"]["release_catalog_dir"])
        workspace_entries.append(
            {
                "workspace_name": workspace_name,
                "preset_path": str(preset_path),
                "workspace_dir": str(workspace_dir.resolve()),
                "summary_path": workspace["summary_path"],
                "catalog_workspace_count": workspace["summary"]["workspace_count"],
                "release_catalog_dir": workspace["summary"]["release_catalog_dir"],
                "release_catalog_manifest_path": workspace["summary"]["release_catalog_manifest_path"],
            }
        )

    published = bootstrap_release_catalog_index_publication(
        release_catalog_dirs,
        output_dir=release_catalog_index_dir,
        signature_scheme=release_catalog_index_scheme or bundle_scheme,
        key_id=release_catalog_index_key_id,
        index_metadata=release_catalog_index_metadata,
    )
    summary = {
        "bundle_scheme": bundle_scheme,
        "release_scheme": release_scheme or bundle_scheme,
        "release_catalog_scheme": release_catalog_scheme or bundle_scheme,
        "release_catalog_index_scheme": release_catalog_index_scheme or bundle_scheme,
        "stack_count": len(workspace_entries),
        "stack_workspaces_dir": str(stack_workspaces_dir.resolve()),
        "release_catalog_index_dir": str(release_catalog_index_dir.resolve()),
        "stack_preset_paths": [str(path) for path in resolved_stack_preset_paths],
        "network_preset_path": None if network_preset_path is None else str(Path(network_preset_path).resolve()),
        "release_catalog_index_preset_path": None if release_catalog_index_preset_path is None else str(Path(release_catalog_index_preset_path).resolve()),
        "release_catalog_index": copy.deepcopy(published["release_catalog_index"]),
        "release_catalog_index_manifest_path": published["release_catalog_index_manifest_path"],
        "workspaces": workspace_entries,
    }
    root_output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = root_output_dir / "summary.json"
    _write_json_file(summary_path, summary)
    return {
        "summary": summary,
        "summary_path": str(summary_path.resolve()),
        "release_catalog_index_dir": str(release_catalog_index_dir.resolve()),
        "release_catalog_index_publication": published,
    }


def relocate_publication_network_workspace_summary(publication_network_dir: str | Path) -> Dict[str, Any]:
    network_path, summary = _load_workspace_summary(publication_network_dir, label="publication network")
    validate_publication_network_summary_consistency(summary)
    workspaces = summary.get("workspaces")
    assert isinstance(workspaces, list)

    summary["stack_workspaces_dir"] = str((network_path / "stack_workspaces").resolve())
    summary["release_catalog_index_dir"] = str((network_path / "release_catalog_index").resolve())
    summary["release_catalog_index_manifest_path"] = str((network_path / "release_catalog_index" / "release_catalog_index_manifest.json").resolve())

    for entry in workspaces:
        if not isinstance(entry, dict):
            continue
        workspace_name = entry.get("workspace_name")
        if not isinstance(workspace_name, str) or not workspace_name.strip():
            continue
        workspace_dir = (network_path / "stack_workspaces" / workspace_name).resolve()
        nested_summary = relocate_publication_stack_workspace_summary(workspace_dir)
        entry["workspace_dir"] = str(workspace_dir)
        entry["summary_path"] = str((workspace_dir / "summary.json").resolve())
        entry["catalog_workspace_count"] = nested_summary.get("workspace_count")
        entry["release_catalog_dir"] = nested_summary.get("release_catalog_dir")
        entry["release_catalog_manifest_path"] = nested_summary.get("release_catalog_manifest_path")

    _write_json_file(network_path / "summary.json", summary)
    return summary


def publish_publication_stack_workspace(
    workspace_dirs: Sequence[str | Path],
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
    release_catalog_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    resolved_workspace_dirs = [Path(value).resolve() for value in workspace_dirs]
    if not resolved_workspace_dirs:
        raise SatRootError("publication stack publishing requires at least one demo catalog workspace")

    source_summaries: list[Dict[str, Any]] = []
    for workspace_dir in resolved_workspace_dirs:
        _, summary = _load_workspace_summary(workspace_dir, label="demo catalog workspace")
        validate_demo_catalog_summary_consistency(summary)
        source_summaries.append(summary)

    bundle_scheme = _require_consistent_workspace_scheme(
        source_summaries,
        field_name="bundle_scheme",
        label="publication stack publishing",
    )
    release_scheme = _require_consistent_workspace_scheme(
        source_summaries,
        field_name="release_scheme",
        label="publication stack publishing",
    )

    workspace_names = _unique_workspace_names(resolved_workspace_dirs)
    root_output_dir = Path(output_dir).resolve()
    catalog_workspaces_dir = root_output_dir / "catalog_workspaces"
    release_catalog_dir = root_output_dir / "release_catalog"
    release_dirs: list[str] = []
    workspace_entries: list[Dict[str, Any]] = []

    for source_dir, workspace_name in zip(resolved_workspace_dirs, workspace_names):
        target_dir = _copy_workspace_directory(
            source_dir,
            catalog_workspaces_dir / workspace_name,
            label="demo catalog workspace",
        )
        copied_summary = relocate_demo_catalog_workspace_summary(target_dir)
        release_dirs.append(str((target_dir / "release").resolve()))
        workspace_entries.append(
            {
                "workspace_name": workspace_name,
                "preset_path": copied_summary.get("preset_path"),
                "workspace_dir": str(target_dir.resolve()),
                "summary_path": str((target_dir / "summary.json").resolve()),
                "bundle_count": copied_summary.get("bundle_count"),
                "release_dir": copied_summary.get("release_dir"),
                "release_manifest_path": copied_summary.get("release_manifest_path"),
            }
        )

    published = bootstrap_release_catalog_publication(
        release_dirs,
        output_dir=release_catalog_dir,
        signature_scheme=signature_scheme,
        key_id=key_id,
        catalog_metadata=release_catalog_metadata,
    )
    summary = {
        "bundle_scheme": bundle_scheme,
        "release_scheme": release_scheme,
        "release_catalog_scheme": signature_scheme,
        "workspace_count": len(workspace_entries),
        "catalog_workspaces_dir": str(catalog_workspaces_dir.resolve()),
        "release_catalog_dir": str(release_catalog_dir.resolve()),
        "catalog_preset_paths": [],
        "stack_preset_path": None,
        "release_catalog_preset_path": None,
        "release_catalog": copy.deepcopy(published["release_catalog"]),
        "release_catalog_manifest_path": published["release_catalog_manifest_path"],
        "workspaces": workspace_entries,
    }
    root_output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = root_output_dir / "summary.json"
    _write_json_file(summary_path, summary)
    return {
        "summary": summary,
        "summary_path": str(summary_path.resolve()),
        "release_catalog_dir": str(release_catalog_dir.resolve()),
        "release_catalog_publication": published,
    }


def publish_publication_network_workspace(
    workspace_dirs: Sequence[str | Path],
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
    release_catalog_index_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    resolved_workspace_dirs = [Path(value).resolve() for value in workspace_dirs]
    if not resolved_workspace_dirs:
        raise SatRootError("publication network publishing requires at least one publication stack workspace")

    source_summaries: list[Dict[str, Any]] = []
    for workspace_dir in resolved_workspace_dirs:
        _, summary = _load_workspace_summary(workspace_dir, label="publication stack")
        validate_publication_stack_summary_consistency(summary)
        source_summaries.append(summary)

    bundle_scheme = _require_consistent_workspace_scheme(
        source_summaries,
        field_name="bundle_scheme",
        label="publication network publishing",
    )
    release_scheme = _require_consistent_workspace_scheme(
        source_summaries,
        field_name="release_scheme",
        label="publication network publishing",
    )
    release_catalog_scheme = _require_consistent_workspace_scheme(
        source_summaries,
        field_name="release_catalog_scheme",
        label="publication network publishing",
    )

    workspace_names = _unique_workspace_names(resolved_workspace_dirs)
    root_output_dir = Path(output_dir).resolve()
    stack_workspaces_dir = root_output_dir / "stack_workspaces"
    release_catalog_index_dir = root_output_dir / "release_catalog_index"
    release_catalog_dirs: list[str] = []
    workspace_entries: list[Dict[str, Any]] = []

    for source_dir, workspace_name in zip(resolved_workspace_dirs, workspace_names):
        target_dir = _copy_workspace_directory(
            source_dir,
            stack_workspaces_dir / workspace_name,
            label="publication stack workspace",
        )
        copied_summary = relocate_publication_stack_workspace_summary(target_dir)
        release_catalog_dirs.append(str((target_dir / "release_catalog").resolve()))
        workspace_entries.append(
            {
                "workspace_name": workspace_name,
                "preset_path": copied_summary.get("stack_preset_path"),
                "workspace_dir": str(target_dir.resolve()),
                "summary_path": str((target_dir / "summary.json").resolve()),
                "catalog_workspace_count": copied_summary.get("workspace_count"),
                "release_catalog_dir": copied_summary.get("release_catalog_dir"),
                "release_catalog_manifest_path": copied_summary.get("release_catalog_manifest_path"),
            }
        )

    published = bootstrap_release_catalog_index_publication(
        release_catalog_dirs,
        output_dir=release_catalog_index_dir,
        signature_scheme=signature_scheme,
        key_id=key_id,
        index_metadata=release_catalog_index_metadata,
    )
    summary = {
        "bundle_scheme": bundle_scheme,
        "release_scheme": release_scheme,
        "release_catalog_scheme": release_catalog_scheme,
        "release_catalog_index_scheme": signature_scheme,
        "stack_count": len(workspace_entries),
        "stack_workspaces_dir": str(stack_workspaces_dir.resolve()),
        "release_catalog_index_dir": str(release_catalog_index_dir.resolve()),
        "stack_preset_paths": [],
        "network_preset_path": None,
        "release_catalog_index_preset_path": None,
        "release_catalog_index": copy.deepcopy(published["release_catalog_index"]),
        "release_catalog_index_manifest_path": published["release_catalog_index_manifest_path"],
        "workspaces": workspace_entries,
    }
    root_output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = root_output_dir / "summary.json"
    _write_json_file(summary_path, summary)
    return {
        "summary": summary,
        "summary_path": str(summary_path.resolve()),
        "release_catalog_index_dir": str(release_catalog_index_dir.resolve()),
        "release_catalog_index_publication": published,
    }


def write_publication_registry_workspace(
    *,
    artifact_paths: Sequence[str | Path],
    release_catalog_index_dir: str | Path,
    output_dir: str | Path,
    signature_scheme: str,
    publication_descriptor_index_key_id: str,
    publication_metadata_key_id: str,
    publication_metadata_catalog_key_id: str,
    publication_registry_key_id: str,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
    publication_network_dir: Optional[str | Path] = None,
    descriptor_index_metadata: Optional[Mapping[str, str]] = None,
    publication_metadata_catalog_metadata: Optional[Mapping[str, str]] = None,
    publication_registry_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    resolved_artifact_paths = resolve_satroot_artifact_inputs(
        artifact_paths,
        discover_under=discover_under,
        recursive=recursive,
    )
    root_output_dir = Path(output_dir).resolve()
    root_output_dir.mkdir(parents=True, exist_ok=True)

    copied_publication_network_dir: Optional[Path] = None
    resolved_release_catalog_index_dir = Path(release_catalog_index_dir).resolve()
    if publication_network_dir is not None:
        resolved_publication_network_dir = Path(publication_network_dir).resolve()
        copied_publication_network_dir = _copy_workspace_directory(
            resolved_publication_network_dir,
            root_output_dir / "publication_network",
            label="publication network workspace",
        )
        relocate_publication_network_workspace_summary(copied_publication_network_dir)
        if resolved_release_catalog_index_dir == (resolved_publication_network_dir / "release_catalog_index").resolve():
            copied_release_catalog_index_dir = copied_publication_network_dir / "release_catalog_index"
        else:
            copied_release_catalog_index_dir = _copy_workspace_directory(
                resolved_release_catalog_index_dir,
                root_output_dir / "release_catalog_index",
                label="release catalog index publication",
            )
    else:
        copied_release_catalog_index_dir = _copy_workspace_directory(
            resolved_release_catalog_index_dir,
            root_output_dir / "release_catalog_index",
            label="release catalog index publication",
        )
    descriptor_index_dir = root_output_dir / "publication_descriptor_index"
    metadata_bundles_dir = root_output_dir / "publication_metadata_bundles"
    metadata_catalog_dir = root_output_dir / "publication_metadata_catalog"
    registry_dir = root_output_dir / "publication_registry"

    descriptor_index_publication = bootstrap_publication_descriptor_index_publication(
        resolved_artifact_paths,
        output_dir=descriptor_index_dir,
        signature_scheme=signature_scheme,
        key_id=publication_descriptor_index_key_id,
        index_metadata=descriptor_index_metadata,
    )
    metadata_bundle_collection = bootstrap_publication_metadata_bundle_collection(
        resolved_artifact_paths,
        output_dir=metadata_bundles_dir,
        signature_scheme=signature_scheme,
        key_id=publication_metadata_key_id,
    )
    metadata_catalog_publication = bootstrap_publication_metadata_catalog_publication(
        metadata_bundle_collection["bundle_dirs"],
        output_dir=metadata_catalog_dir,
        signature_scheme=signature_scheme,
        key_id=publication_metadata_catalog_key_id,
        catalog_metadata=publication_metadata_catalog_metadata,
    )
    publication_registry_publication = bootstrap_publication_registry_publication(
        release_catalog_index_dir=copied_release_catalog_index_dir,
        publication_descriptor_index_dir=descriptor_index_dir,
        publication_metadata_catalog_dir=metadata_catalog_dir,
        output_dir=registry_dir,
        signature_scheme=signature_scheme,
        key_id=publication_registry_key_id,
        registry_metadata=publication_registry_metadata,
    )

    summary = {
        "signature_scheme": signature_scheme,
        "source_publication_network_dir": None if publication_network_dir is None else str(Path(publication_network_dir).resolve()),
        "publication_network_dir": None if copied_publication_network_dir is None else str(copied_publication_network_dir.resolve()),
        "artifact_count": len(resolved_artifact_paths),
        "artifact_paths": resolved_artifact_paths,
        "release_catalog_index_source_dir": str(resolved_release_catalog_index_dir),
        "release_catalog_index_dir": str(copied_release_catalog_index_dir.resolve()),
        "publication_descriptor_index_dir": str(descriptor_index_dir.resolve()),
        "publication_metadata_bundles_dir": str(metadata_bundles_dir.resolve()),
        "publication_metadata_bundle_count": len(metadata_bundle_collection["bundles"]),
        "publication_metadata_catalog_dir": str(metadata_catalog_dir.resolve()),
        "publication_registry_dir": str(registry_dir.resolve()),
        "publication_descriptor_index_manifest_path": descriptor_index_publication["publication_descriptor_index_manifest_path"],
        "publication_metadata_catalog_manifest_path": metadata_catalog_publication["publication_metadata_catalog_manifest_path"],
        "publication_registry_manifest_path": publication_registry_publication["publication_registry_manifest_path"],
        "publication_descriptor_index": copy.deepcopy(descriptor_index_publication["publication_descriptor_index"]),
        "publication_metadata_bundles": copy.deepcopy(metadata_bundle_collection["bundles"]),
        "publication_metadata_catalog": copy.deepcopy(metadata_catalog_publication["publication_metadata_catalog"]),
        "publication_registry": copy.deepcopy(publication_registry_publication["publication_registry"]),
    }
    summary_path = root_output_dir / "summary.json"
    _write_json_file(summary_path, summary)
    return {
        "summary": summary,
        "summary_path": str(summary_path.resolve()),
        "release_catalog_index_dir": str(copied_release_catalog_index_dir.resolve()),
        "publication_descriptor_index_dir": str(descriptor_index_dir.resolve()),
        "publication_metadata_bundles_dir": str(metadata_bundles_dir.resolve()),
        "publication_metadata_catalog_dir": str(metadata_catalog_dir.resolve()),
        "publication_registry_dir": str(registry_dir.resolve()),
        "publication_descriptor_index_publication": descriptor_index_publication,
        "publication_metadata_bundle_collection": metadata_bundle_collection,
        "publication_metadata_catalog_publication": metadata_catalog_publication,
        "publication_registry_publication": publication_registry_publication,
    }


def inventory_workspace_artifacts(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> Dict[str, Any]:
    resolved_search_roots = [str(Path(value).resolve()) for value in search_roots]
    if not resolved_search_roots:
        raise SatRootError("inventory-artifacts requires at least one directory path or --discover-under root")

    bundle_dirs = _discover_optional_paths(discover_signed_ledger_bundle_dirs, resolved_search_roots, recursive=recursive)
    release_dirs = _discover_optional_paths(discover_signed_release_publication_dirs, resolved_search_roots, recursive=recursive)
    release_catalog_dirs = _discover_optional_paths(discover_signed_release_catalog_publication_dirs, resolved_search_roots, recursive=recursive)
    release_catalog_index_dirs = _discover_optional_paths(discover_signed_release_catalog_index_publication_dirs, resolved_search_roots, recursive=recursive)
    publication_registry_dirs = _discover_optional_paths(discover_signed_publication_registry_publication_dirs, resolved_search_roots, recursive=recursive)
    demo_catalog_workspace_dirs = _discover_optional_paths(discover_demo_catalog_workspace_dirs, resolved_search_roots, recursive=recursive)
    publication_stack_dirs = _discover_optional_paths(discover_publication_stack_workspace_dirs, resolved_search_roots, recursive=recursive)
    publication_network_dirs = _discover_optional_paths(discover_publication_network_workspace_dirs, resolved_search_roots, recursive=recursive)
    publication_registry_workspace_dirs = _discover_optional_paths(
        discover_publication_registry_workspace_dirs,
        resolved_search_roots,
        recursive=recursive,
    )

    bundle_entries: list[Dict[str, Any]] = []
    for bundle_dir in bundle_dirs:
        bundle_summary = summarize_signed_ledger_bundle(bundle_dir)
        final_snapshot = bundle_summary.get("final_state_snapshot")
        assert isinstance(final_snapshot, dict)
        bundle_entries.append(
            {
                "bundle_dir": str(Path(bundle_dir).resolve()),
                "scheme": bundle_summary.get("scheme"),
                "symbol": bundle_summary.get("symbol"),
                "profile": final_snapshot.get("profile"),
                "record_count": bundle_summary.get("record_count"),
                "verification_material_scope": bundle_summary.get("verification_material_scope"),
            }
        )

    release_entries: list[Dict[str, Any]] = []
    for release_dir in release_dirs:
        release_summary = summarize_signed_release_publication(release_dir)
        release_entries.append(
            {
                "release_dir": str(Path(release_dir).resolve()),
                "signature_scheme": release_summary.get("signature_scheme"),
                "signature_key_id": release_summary.get("signature_key_id"),
                "bundle_count": release_summary.get("bundle_count"),
                "release": copy.deepcopy(release_summary.get("release")),
                "bundle_symbols": copy.deepcopy(release_summary.get("bundle_symbols")),
            }
        )

    release_catalog_entries: list[Dict[str, Any]] = []
    for release_catalog_dir in release_catalog_dirs:
        release_catalog_summary = summarize_signed_release_catalog_publication(release_catalog_dir)
        release_catalog_entries.append(
            {
                "release_catalog_dir": str(Path(release_catalog_dir).resolve()),
                "signature_scheme": release_catalog_summary.get("signature_scheme"),
                "signature_key_id": release_catalog_summary.get("signature_key_id"),
                "release_count": release_catalog_summary.get("release_count"),
                "catalog": copy.deepcopy(release_catalog_summary.get("catalog")),
                "release_labels": copy.deepcopy(release_catalog_summary.get("release_labels")),
            }
        )

    release_catalog_index_entries: list[Dict[str, Any]] = []
    for release_catalog_index_dir in release_catalog_index_dirs:
        release_catalog_index_summary = summarize_signed_release_catalog_index_publication(release_catalog_index_dir)
        release_catalog_index_entries.append(
            {
                "release_catalog_index_dir": str(Path(release_catalog_index_dir).resolve()),
                "signature_scheme": release_catalog_index_summary.get("signature_scheme"),
                "signature_key_id": release_catalog_index_summary.get("signature_key_id"),
                "release_catalog_count": release_catalog_index_summary.get("release_catalog_count"),
                "index": copy.deepcopy(release_catalog_index_summary.get("index")),
                "catalog_labels": copy.deepcopy(release_catalog_index_summary.get("catalog_labels")),
            }
        )

    publication_registry_entries: list[Dict[str, Any]] = []
    for publication_registry_dir in publication_registry_dirs:
        registry_summary = summarize_publication_registry_publication(publication_registry_dir)
        publication_registry_entries.append(
            {
                "publication_registry_dir": str(Path(publication_registry_dir).resolve()),
                "signature_scheme": registry_summary.get("signature_scheme"),
                "signature_key_id": registry_summary.get("signature_key_id"),
                "component_count": registry_summary.get("component_count"),
                "index": copy.deepcopy(registry_summary.get("index")),
                "components": sorted(
                    key
                    for key in (
                        "release_catalog_index_publication",
                        "publication_descriptor_index_publication",
                        "publication_metadata_catalog_publication",
                    )
                    if isinstance(registry_summary.get(key), Mapping)
                ),
            }
        )

    demo_catalog_workspace_entries: list[Dict[str, Any]] = []
    for workspace_dir in demo_catalog_workspace_dirs:
        workspace_summary = summarize_demo_catalog_workspace(workspace_dir)
        demo_catalog_workspace_entries.append(
            {
                "workspace_dir": str(Path(workspace_dir).resolve()),
                "bundle_scheme": workspace_summary.get("bundle_scheme"),
                "release_scheme": workspace_summary.get("release_scheme"),
                "bundle_count": workspace_summary.get("bundle_count"),
                "bundle_names": copy.deepcopy(workspace_summary.get("bundle_names")),
                "bundle_profiles": copy.deepcopy(workspace_summary.get("bundle_profiles")),
                "release": copy.deepcopy(workspace_summary.get("release")),
            }
        )

    publication_stack_entries: list[Dict[str, Any]] = []
    for workspace_dir in publication_stack_dirs:
        workspace_summary = summarize_publication_stack_workspace(workspace_dir)
        publication_stack_entries.append(
            {
                "workspace_dir": str(Path(workspace_dir).resolve()),
                "bundle_scheme": workspace_summary.get("bundle_scheme"),
                "release_scheme": workspace_summary.get("release_scheme"),
                "release_catalog_scheme": workspace_summary.get("release_catalog_scheme"),
                "workspace_count": workspace_summary.get("workspace_count"),
                "workspace_names": copy.deepcopy(workspace_summary.get("workspace_names")),
                "release_catalog": copy.deepcopy(workspace_summary.get("release_catalog_summary", {}).get("catalog")),
            }
        )

    publication_network_entries: list[Dict[str, Any]] = []
    for workspace_dir in publication_network_dirs:
        workspace_summary = summarize_publication_network_workspace(workspace_dir)
        publication_network_entries.append(
            {
                "workspace_dir": str(Path(workspace_dir).resolve()),
                "bundle_scheme": workspace_summary.get("bundle_scheme"),
                "release_scheme": workspace_summary.get("release_scheme"),
                "release_catalog_scheme": workspace_summary.get("release_catalog_scheme"),
                "release_catalog_index_scheme": workspace_summary.get("release_catalog_index_scheme"),
                "stack_count": workspace_summary.get("stack_count"),
                "workspace_names": copy.deepcopy(workspace_summary.get("workspace_names")),
                "release_catalog_index": copy.deepcopy(workspace_summary.get("release_catalog_index_summary", {}).get("index")),
            }
        )

    publication_registry_workspace_entries: list[Dict[str, Any]] = []
    for workspace_dir in publication_registry_workspace_dirs:
        workspace_summary = summarize_publication_registry_workspace(workspace_dir)
        publication_registry_workspace_entries.append(
            {
                "workspace_dir": str(Path(workspace_dir).resolve()),
                "signature_scheme": workspace_summary.get("signature_scheme"),
                "artifact_count": workspace_summary.get("artifact_count"),
                "publication_metadata_bundle_count": workspace_summary.get("publication_metadata_bundle_count"),
                "publication_metadata_artifact_kinds": copy.deepcopy(workspace_summary.get("publication_metadata_artifact_kinds")),
                "publication_registry": copy.deepcopy(workspace_summary.get("publication_registry_summary", {}).get("index")),
            }
        )

    return {
        "search_roots": resolved_search_roots,
        "recursive": recursive,
        "bundle_count": len(bundle_entries),
        "release_count": len(release_entries),
        "release_catalog_count": len(release_catalog_entries),
        "release_catalog_index_count": len(release_catalog_index_entries),
        "publication_registry_count": len(publication_registry_entries),
        "demo_catalog_workspace_count": len(demo_catalog_workspace_entries),
        "publication_stack_count": len(publication_stack_entries),
        "publication_network_count": len(publication_network_entries),
        "publication_registry_workspace_count": len(publication_registry_workspace_entries),
        "bundles": bundle_entries,
        "releases": release_entries,
        "release_catalogs": release_catalog_entries,
        "release_catalog_indexes": release_catalog_index_entries,
        "publication_registries": publication_registry_entries,
        "demo_catalog_workspaces": demo_catalog_workspace_entries,
        "publication_stacks": publication_stack_entries,
        "publication_networks": publication_network_entries,
        "publication_registry_workspaces": publication_registry_workspace_entries,
    }


def _filtered_string_mapping(value: Any) -> Dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): str(entry)
        for key, entry in value.items()
        if isinstance(key, str) and key.strip() and isinstance(entry, str) and entry.strip()
    }


def export_demo_catalog_preset_from_workspace(demo_catalog_dir: str | Path) -> Dict[str, Any]:
    _, summary = _load_workspace_summary(demo_catalog_dir, label="demo catalog workspace")
    validate_demo_catalog_summary_consistency(summary)
    bundles = summary.get("bundles")
    assert isinstance(bundles, list)
    spec_map = {spec["profile"]: spec for spec in DEMO_CATALOG_BUNDLE_SPECS}

    profiles: list[str] = []
    symbol_overrides: Dict[str, str] = {}
    name_overrides: Dict[str, str] = {}
    profile_field_overrides: Dict[str, Dict[str, str]] = {}
    profile_structure_overrides: Dict[str, Dict[str, Any]] = {}

    for entry in bundles:
        if not isinstance(entry, Mapping):
            continue
        profile = entry.get("profile")
        if not isinstance(profile, str) or profile not in spec_map:
            continue
        profiles.append(profile)

        symbol = entry.get("symbol")
        if isinstance(symbol, str) and symbol != spec_map[profile]["symbol"]:
            symbol_overrides[profile] = symbol

        name = entry.get("name")
        if isinstance(name, str) and name != spec_map[profile]["name"]:
            name_overrides[profile] = name

        profile_fields = _filtered_string_mapping(entry.get("profile_fields"))
        if profile_fields:
            profile_field_overrides[profile] = profile_fields

        structure_overrides = entry.get("structure_overrides")
        if isinstance(structure_overrides, Mapping) and structure_overrides:
            profile_structure_overrides[profile] = copy.deepcopy(dict(structure_overrides))

    preset: Dict[str, Any] = {
        "type": "SATROOT-DEMO-CATALOG-PRESET",
        "version": "0.1",
        "profiles": profiles,
    }
    if symbol_overrides:
        preset["symbol_overrides"] = symbol_overrides
    if name_overrides:
        preset["name_overrides"] = name_overrides
    if profile_field_overrides:
        preset["profile_field_overrides"] = profile_field_overrides
    if profile_structure_overrides:
        preset["profile_structure_overrides"] = profile_structure_overrides

    release_metadata = _filtered_string_mapping(summary.get("release"))
    if release_metadata:
        preset["release"] = release_metadata
    return preset


def export_publication_stack_preset_from_workspace(
    publication_stack_dir: str | Path,
    *,
    output_path: Optional[str | Path] = None,
    catalog_preset_dir: Optional[str | Path] = None,
) -> Dict[str, Any]:
    _, summary = _load_workspace_summary(publication_stack_dir, label="publication stack")
    validate_publication_stack_summary_consistency(summary)
    workspaces = summary.get("workspaces")
    assert isinstance(workspaces, list)

    base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
    export_catalog_dir = None if catalog_preset_dir is None else Path(catalog_preset_dir).resolve()
    catalog_preset_paths: list[str] = []

    for entry in workspaces:
        if not isinstance(entry, Mapping):
            continue
        workspace_name = entry.get("workspace_name")
        workspace_dir = entry.get("workspace_dir")
        preset_path = entry.get("preset_path")
        if not isinstance(workspace_name, str) or not workspace_name.strip():
            continue

        if export_catalog_dir is not None:
            if not isinstance(workspace_dir, str) or not workspace_dir.strip():
                raise SatRootError("publication stack preset export requires workspace_dir for each nested workspace")
            catalog_output_path = export_catalog_dir / f"{workspace_name}.json"
            catalog_output_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json_file(
                catalog_output_path,
                export_demo_catalog_preset_from_workspace(workspace_dir),
            )
            catalog_preset_paths.append(_relative_output_path(catalog_output_path, base_dir=base_dir))
            continue

        if not isinstance(preset_path, str) or not preset_path.strip():
            raise SatRootError("publication stack preset export requires --catalog-preset-dir when nested workspaces do not preserve preset_path")
        catalog_preset_paths.append(_relative_output_path(preset_path, base_dir=base_dir))

    release_catalog = summary.get("release_catalog")
    release_catalog_metadata = {}
    if isinstance(release_catalog, Mapping):
        release_catalog_metadata = _filtered_string_mapping(release_catalog.get("catalog"))

    preset = {
        "type": "SATROOT-PUBLICATION-STACK-PRESET",
        "version": "0.1",
        "catalog_presets": catalog_preset_paths,
    }
    if release_catalog_metadata:
        preset["release_catalog"] = release_catalog_metadata
    return preset


def export_publication_network_preset_from_workspace(
    publication_network_dir: str | Path,
    *,
    output_path: Optional[str | Path] = None,
    stack_preset_dir: Optional[str | Path] = None,
    catalog_preset_dir: Optional[str | Path] = None,
) -> Dict[str, Any]:
    _, summary = _load_workspace_summary(publication_network_dir, label="publication network")
    validate_publication_network_summary_consistency(summary)
    workspaces = summary.get("workspaces")
    assert isinstance(workspaces, list)

    base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
    export_stack_dir = None if stack_preset_dir is None else Path(stack_preset_dir).resolve()
    export_catalog_dir = None if catalog_preset_dir is None else Path(catalog_preset_dir).resolve()
    stack_preset_paths: list[str] = []

    for entry in workspaces:
        if not isinstance(entry, Mapping):
            continue
        workspace_name = entry.get("workspace_name")
        workspace_dir = entry.get("workspace_dir")
        preset_path = entry.get("preset_path")
        if not isinstance(workspace_name, str) or not workspace_name.strip():
            continue

        if export_stack_dir is not None:
            if not isinstance(workspace_dir, str) or not workspace_dir.strip():
                raise SatRootError("publication network preset export requires workspace_dir for each nested stack")
            stack_output_path = export_stack_dir / f"{workspace_name}.json"
            stack_output_path.parent.mkdir(parents=True, exist_ok=True)
            nested_catalog_dir = None
            if export_catalog_dir is not None:
                nested_catalog_dir = export_catalog_dir / workspace_name
            _write_json_file(
                stack_output_path,
                export_publication_stack_preset_from_workspace(
                    workspace_dir,
                    output_path=stack_output_path,
                    catalog_preset_dir=nested_catalog_dir,
                ),
            )
            stack_preset_paths.append(_relative_output_path(stack_output_path, base_dir=base_dir))
            continue

        if not isinstance(preset_path, str) or not preset_path.strip():
            raise SatRootError("publication network preset export requires --stack-preset-dir when nested workspaces do not preserve preset_path")
        stack_preset_paths.append(_relative_output_path(preset_path, base_dir=base_dir))

    release_catalog_index = summary.get("release_catalog_index")
    release_catalog_index_metadata = {}
    if isinstance(release_catalog_index, Mapping):
        release_catalog_index_metadata = _filtered_string_mapping(release_catalog_index.get("index"))

    preset = {
        "type": "SATROOT-PUBLICATION-NETWORK-PRESET",
        "version": "0.1",
        "stack_presets": stack_preset_paths,
    }
    if release_catalog_index_metadata:
        preset["release_catalog_index"] = release_catalog_index_metadata
    return preset


def export_publication_registry_workspace_preset_from_workspace(
    publication_registry_workspace_dir: str | Path,
    *,
    output_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    _, summary = _load_workspace_summary(publication_registry_workspace_dir, label="publication registry workspace")
    validate_publication_registry_workspace_summary_consistency(summary)

    base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
    preset: Dict[str, Any] = {
        "type": "SATROOT-PUBLICATION-REGISTRY-WORKSPACE-PRESET",
        "version": "0.1",
    }

    artifact_paths = [
        _relative_output_path(Path(value).resolve(), base_dir=base_dir)
        for value in summary.get("artifact_paths", [])
        if isinstance(value, str) and value.strip()
    ]
    if artifact_paths:
        preset["artifact_paths"] = artifact_paths

    source_publication_network_dir = summary.get("source_publication_network_dir")
    if isinstance(source_publication_network_dir, str) and source_publication_network_dir.strip():
        preset["publication_network_dir"] = _relative_output_path(Path(source_publication_network_dir).resolve(), base_dir=base_dir)

    release_catalog_index_source_dir = summary.get("release_catalog_index_source_dir")
    if isinstance(release_catalog_index_source_dir, str) and release_catalog_index_source_dir.strip():
        source_network_path = Path(source_publication_network_dir).resolve() if isinstance(source_publication_network_dir, str) and source_publication_network_dir.strip() else None
        source_release_catalog_index_path = Path(release_catalog_index_source_dir).resolve()
        if source_network_path is None or source_release_catalog_index_path != (source_network_path / "release_catalog_index").resolve():
            preset["release_catalog_index_dir"] = _relative_output_path(source_release_catalog_index_path, base_dir=base_dir)

    descriptor_index = summary.get("publication_descriptor_index")
    if isinstance(descriptor_index, Mapping):
        descriptor_index_metadata = _filtered_string_mapping(descriptor_index.get("index"))
        if descriptor_index_metadata:
            preset["publication_descriptor_index"] = descriptor_index_metadata

    publication_metadata_catalog = summary.get("publication_metadata_catalog")
    if isinstance(publication_metadata_catalog, Mapping):
        publication_metadata_catalog_metadata = _filtered_string_mapping(publication_metadata_catalog.get("index"))
        if publication_metadata_catalog_metadata:
            preset["publication_metadata_catalog"] = publication_metadata_catalog_metadata

    publication_registry = summary.get("publication_registry")
    if isinstance(publication_registry, Mapping):
        publication_registry_metadata = _filtered_string_mapping(publication_registry.get("index"))
        if publication_registry_metadata:
            preset["publication_registry"] = publication_registry_metadata

    return preset


def export_publication_descriptor_index_preset_from_workspace(
    publication_descriptor_index_dir: str | Path,
    *,
    output_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    _manifest_path, _descriptor_index_path, _manifest, index = _load_publication_descriptor_index_publication(
        publication_descriptor_index_dir
    )
    base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
    preset: Dict[str, Any] = {
        "type": "SATROOT-PUBLICATION-DESCRIPTOR-INDEX-PRESET",
        "version": "0.1",
    }

    artifact_paths: list[str] = []
    for entry in index.get("artifacts", []):
        if not isinstance(entry, Mapping):
            continue
        artifact_path = entry.get("artifact_path")
        if not isinstance(artifact_path, str) or not artifact_path.strip():
            continue
        artifact_paths.append(_relative_output_path(Path(artifact_path).resolve(), base_dir=base_dir))
    if artifact_paths:
        preset["artifact_paths"] = artifact_paths

    index_metadata = _filtered_string_mapping(index.get("index"))
    if index_metadata:
        preset["index"] = index_metadata
    return preset


def export_publication_metadata_catalog_preset_from_workspace(
    publication_metadata_catalog_dir: str | Path,
    *,
    output_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    _manifest_path, catalog_path, _manifest, catalog = _load_publication_metadata_catalog_publication(publication_metadata_catalog_dir)
    base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
    preset: Dict[str, Any] = {
        "type": "SATROOT-PUBLICATION-METADATA-CATALOG-PRESET",
        "version": "0.1",
    }

    bundle_dirs: list[str] = []
    for entry in catalog.get("bundles", []):
        if not isinstance(entry, Mapping):
            continue
        bundle_ref = entry.get("publication_metadata_bundle_path")
        if not isinstance(bundle_ref, str) or not bundle_ref.strip():
            continue
        resolved_bundle_dir = (catalog_path.parent / bundle_ref).resolve()
        bundle_dirs.append(_relative_output_path(resolved_bundle_dir, base_dir=base_dir))
    if bundle_dirs:
        preset["publication_metadata_bundle_dirs"] = bundle_dirs

    catalog_metadata = _filtered_string_mapping(catalog.get("index"))
    if catalog_metadata:
        preset["catalog"] = catalog_metadata
    return preset


def export_publication_registry_preset_from_workspace(
    publication_registry_dir: str | Path,
    *,
    output_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    _, registry_path, _manifest, registry = _load_publication_registry_publication(publication_registry_dir)
    validate_publication_registry_consistency(registry)

    base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
    preset: Dict[str, Any] = {
        "type": "SATROOT-PUBLICATION-REGISTRY-PRESET",
        "version": "0.1",
    }

    release_catalog_index_component = registry.get("release_catalog_index_publication")
    if isinstance(release_catalog_index_component, Mapping):
        publication_directory_path = release_catalog_index_component.get("publication_directory_path")
        if isinstance(publication_directory_path, str) and publication_directory_path.strip():
            resolved_path = (registry_path.parent / publication_directory_path).resolve()
            preset["release_catalog_index_dir"] = _relative_output_path(resolved_path, base_dir=base_dir)

    publication_descriptor_index_component = registry.get("publication_descriptor_index_publication")
    if isinstance(publication_descriptor_index_component, Mapping):
        publication_directory_path = publication_descriptor_index_component.get("publication_directory_path")
        if isinstance(publication_directory_path, str) and publication_directory_path.strip():
            resolved_path = (registry_path.parent / publication_directory_path).resolve()
            preset["publication_descriptor_index_dir"] = _relative_output_path(resolved_path, base_dir=base_dir)

    publication_metadata_catalog_component = registry.get("publication_metadata_catalog_publication")
    if isinstance(publication_metadata_catalog_component, Mapping):
        publication_directory_path = publication_metadata_catalog_component.get("publication_directory_path")
        if isinstance(publication_directory_path, str) and publication_directory_path.strip():
            resolved_path = (registry_path.parent / publication_directory_path).resolve()
            preset["publication_metadata_catalog_dir"] = _relative_output_path(resolved_path, base_dir=base_dir)

    registry_metadata = _filtered_string_mapping(registry.get("index"))
    if registry_metadata:
        preset["registry"] = registry_metadata
    return preset


def _detect_satroot_artifact_kind(path: str | Path) -> tuple[str, Path]:
    resolved_path = Path(path).resolve()
    if resolved_path.is_file():
        parent = resolved_path.parent
        name = resolved_path.name
        if name == "publication_registry_manifest.json":
            return "publication-registry", parent
        if name == "summary.json":
            if (parent / "publication_registry").is_dir() and (parent / "publication_descriptor_index").is_dir() and (parent / "publication_metadata_catalog").is_dir():
                return "publication-registry-workspace", parent
            if (parent / "release_catalog_index").is_dir():
                return "publication-network", parent
            if (parent / "release_catalog").is_dir():
                return "publication-stack", parent
            if (parent / "bundles").is_dir() and (parent / "release").is_dir():
                return "demo-catalog", parent
        if name == "bundle_manifest.json":
            return "bundle", parent
        if name == "release_manifest.json":
            return "release", parent
        if name == "release_catalog_manifest.json":
            return "release-catalog", parent
        if name == "release_catalog_index_manifest.json":
            return "release-catalog-index", parent
        raise SatRootError(f"unsupported SATROOT artifact file: {resolved_path}")

    if not resolved_path.is_dir():
        raise SatRootError("report path must be an existing file or directory")

    if (resolved_path / "summary.json").is_file():
        if (resolved_path / "publication_registry").is_dir() and (resolved_path / "publication_descriptor_index").is_dir() and (resolved_path / "publication_metadata_catalog").is_dir():
            return "publication-registry-workspace", resolved_path
        if (resolved_path / "release_catalog_index").is_dir():
            return "publication-network", resolved_path
        if (resolved_path / "release_catalog").is_dir():
            return "publication-stack", resolved_path
        if (resolved_path / "bundles").is_dir() and (resolved_path / "release").is_dir():
            return "demo-catalog", resolved_path
    if (resolved_path / "publication_registry_manifest.json").is_file():
        return "publication-registry", resolved_path
    if (resolved_path / "release_catalog_index_manifest.json").is_file():
        return "release-catalog-index", resolved_path
    if (resolved_path / "release_catalog_manifest.json").is_file():
        return "release-catalog", resolved_path
    if (resolved_path / "release_manifest.json").is_file():
        return "release", resolved_path
    if (resolved_path / "bundle_manifest.json").is_file():
        return "bundle", resolved_path
    raise SatRootError(f"unable to detect SATROOT artifact kind at: {resolved_path}")


def _append_metadata_lines(lines: list[str], metadata: Mapping[str, Any], fields: Sequence[tuple[str, str]]) -> None:
    for field_name, label in fields:
        value = metadata.get(field_name)
        if isinstance(value, str) and value.strip():
            lines.append(f"- {label}: `{value}`")


def build_satroot_artifact_descriptor(path: str | Path) -> Dict[str, Any]:
    kind, artifact_path = _detect_satroot_artifact_kind(path)
    descriptor: Dict[str, Any] = {
        "descriptor_type": "SATROOT-ARTIFACT-DESCRIPTOR",
        "descriptor_version": "0.1",
        "artifact_kind": kind,
        "artifact_path": str(artifact_path),
    }

    if kind == "bundle":
        summary = summarize_signed_ledger_bundle(artifact_path)
        snapshot = summary.get("final_state_snapshot")
        assert isinstance(snapshot, dict)
        descriptor.update(
            {
                "scheme": summary.get("scheme"),
                "symbol": summary.get("symbol"),
                "profile": snapshot.get("profile"),
                "record_count": summary.get("record_count"),
                "root_id": summary.get("root_id"),
                "verification_material_scope": summary.get("verification_material_scope"),
                "final_event_id": summary.get("final_event_id"),
                "final_state_hash": summary.get("final_state_hash"),
            }
        )
        return descriptor

    if kind == "release":
        summary = summarize_signed_release_publication(artifact_path)
        descriptor.update(
            {
                "signature_scheme": summary.get("signature_scheme"),
                "signature_key_id": summary.get("signature_key_id"),
                "bundle_count": summary.get("bundle_count"),
                "release": copy.deepcopy(summary.get("release")),
                "bundle_symbols": copy.deepcopy(summary.get("bundle_symbols")),
                "bundle_index_path": summary.get("bundle_index_path"),
                "bundle_index_hash": summary.get("bundle_index_hash"),
            }
        )
        return descriptor

    if kind == "release-catalog":
        summary = summarize_signed_release_catalog_publication(artifact_path)
        descriptor.update(
            {
                "signature_scheme": summary.get("signature_scheme"),
                "signature_key_id": summary.get("signature_key_id"),
                "release_count": summary.get("release_count"),
                "catalog": copy.deepcopy(summary.get("catalog")),
                "release_labels": copy.deepcopy(summary.get("release_labels")),
                "release_paths": copy.deepcopy(summary.get("release_paths")),
            }
        )
        return descriptor

    if kind == "release-catalog-index":
        summary = summarize_signed_release_catalog_index_publication(artifact_path)
        descriptor.update(
            {
                "signature_scheme": summary.get("signature_scheme"),
                "signature_key_id": summary.get("signature_key_id"),
                "release_catalog_count": summary.get("release_catalog_count"),
                "index": copy.deepcopy(summary.get("index")),
                "catalog_labels": copy.deepcopy(summary.get("catalog_labels")),
                "release_catalog_paths": copy.deepcopy(summary.get("release_catalog_paths")),
            }
        )
        return descriptor

    if kind == "demo-catalog":
        summary = summarize_demo_catalog_workspace(artifact_path)
        descriptor.update(
            {
                "bundle_scheme": summary.get("bundle_scheme"),
                "release_scheme": summary.get("release_scheme"),
                "bundle_count": summary.get("bundle_count"),
                "release": copy.deepcopy(summary.get("release")),
                "bundle_names": copy.deepcopy(summary.get("bundle_names")),
                "bundle_profiles": copy.deepcopy(summary.get("bundle_profiles")),
                "bundle_symbols": copy.deepcopy(summary.get("bundle_symbols")),
            }
        )
        return descriptor

    if kind == "publication-stack":
        summary = summarize_publication_stack_workspace(artifact_path)
        descriptor.update(
            {
                "bundle_scheme": summary.get("bundle_scheme"),
                "release_scheme": summary.get("release_scheme"),
                "release_catalog_scheme": summary.get("release_catalog_scheme"),
                "workspace_count": summary.get("workspace_count"),
                "workspace_names": copy.deepcopy(summary.get("workspace_names")),
                "workspace_preset_paths": copy.deepcopy(summary.get("workspace_preset_paths")),
                "release_catalog": copy.deepcopy((summary.get("release_catalog_summary") or {}).get("catalog")),
            }
        )
        return descriptor

    if kind == "publication-network":
        summary = summarize_publication_network_workspace(artifact_path)
        descriptor.update(
            {
                "bundle_scheme": summary.get("bundle_scheme"),
                "release_scheme": summary.get("release_scheme"),
                "release_catalog_scheme": summary.get("release_catalog_scheme"),
                "release_catalog_index_scheme": summary.get("release_catalog_index_scheme"),
                "stack_count": summary.get("stack_count"),
                "workspace_names": copy.deepcopy(summary.get("workspace_names")),
                "workspace_preset_paths": copy.deepcopy(summary.get("workspace_preset_paths")),
                "release_catalog_index": copy.deepcopy((summary.get("release_catalog_index_summary") or {}).get("index")),
            }
        )
        return descriptor

    if kind == "publication-registry-workspace":
        summary = summarize_publication_registry_workspace(artifact_path)
        descriptor.update(
            {
                "signature_scheme": summary.get("signature_scheme"),
                "artifact_count": summary.get("artifact_count"),
                "publication_metadata_bundle_count": summary.get("publication_metadata_bundle_count"),
                "publication_metadata_artifact_kinds": copy.deepcopy(summary.get("publication_metadata_artifact_kinds")),
                "publication_registry": copy.deepcopy((summary.get("publication_registry_summary") or {}).get("index")),
                "publication_descriptor_index": copy.deepcopy((summary.get("publication_descriptor_index_summary") or {}).get("index")),
            }
        )
        return descriptor

    if kind == "publication-registry":
        summary = summarize_publication_registry_publication(artifact_path)
        descriptor.update(
            {
                "signature_scheme": summary.get("signature_scheme"),
                "signature_key_id": summary.get("signature_key_id"),
                "component_count": summary.get("component_count"),
                "index": copy.deepcopy(summary.get("index")),
                "components": sorted(
                    key
                    for key in (
                        "release_catalog_index_publication",
                        "publication_descriptor_index_publication",
                        "publication_metadata_catalog_publication",
                    )
                    if isinstance(summary.get(key), Mapping)
                ),
            }
        )
        return descriptor

    raise SatRootError(f"unsupported SATROOT artifact kind: {kind}")


def validate_publication_descriptor_consistency(descriptor: Mapping[str, Any]) -> None:
    if descriptor.get("descriptor_type") != "SATROOT-ARTIFACT-DESCRIPTOR":
        raise SatRootError("publication descriptor must declare descriptor_type=SATROOT-ARTIFACT-DESCRIPTOR")
    if descriptor.get("descriptor_version") != "0.1":
        raise SatRootError("publication descriptor must declare descriptor_version=0.1")
    artifact_kind = descriptor.get("artifact_kind")
    if artifact_kind not in {
        "bundle",
        "release",
        "release-catalog",
        "release-catalog-index",
        "demo-catalog",
        "publication-stack",
        "publication-network",
        "publication-registry-workspace",
        "publication-registry",
    }:
        raise SatRootError("publication descriptor artifact_kind must be a supported descriptor kind")
    artifact_path = descriptor.get("artifact_path")
    if not isinstance(artifact_path, str) or not artifact_path.strip():
        raise SatRootError("publication descriptor artifact_path must be a non-empty string")


def discover_satroot_artifact_paths(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> list[str]:
    resolved_search_roots = [Path(value).resolve() for value in search_roots]
    if not resolved_search_roots:
        raise SatRootError("at least one SATROOT artifact discovery root is required")

    artifact_paths: list[str] = []
    seen: set[tuple[str, str]] = set()

    def add_artifact(kind: str, path: str | Path) -> None:
        resolved_path = str(Path(path).resolve())
        key = (kind, resolved_path)
        if key not in seen:
            artifact_paths.append(resolved_path)
            seen.add(key)

    for artifact_path in _discover_optional_paths(discover_signed_ledger_bundle_dirs, resolved_search_roots, recursive=recursive):
        add_artifact("bundle", artifact_path)
    for artifact_path in _discover_optional_paths(discover_signed_release_publication_dirs, resolved_search_roots, recursive=recursive):
        add_artifact("release", artifact_path)
    for artifact_path in _discover_optional_paths(discover_signed_release_catalog_publication_dirs, resolved_search_roots, recursive=recursive):
        add_artifact("release-catalog", artifact_path)
    for artifact_path in _discover_optional_paths(discover_signed_release_catalog_index_publication_dirs, resolved_search_roots, recursive=recursive):
        add_artifact("release-catalog-index", artifact_path)
    for artifact_path in _discover_optional_paths(discover_signed_publication_registry_publication_dirs, resolved_search_roots, recursive=recursive):
        add_artifact("publication-registry", artifact_path)
    for artifact_path in _discover_optional_paths(discover_demo_catalog_workspace_dirs, resolved_search_roots, recursive=recursive):
        add_artifact("demo-catalog", artifact_path)
    for artifact_path in _discover_optional_paths(discover_publication_stack_workspace_dirs, resolved_search_roots, recursive=recursive):
        add_artifact("publication-stack", artifact_path)
    for artifact_path in _discover_optional_paths(discover_publication_network_workspace_dirs, resolved_search_roots, recursive=recursive):
        add_artifact("publication-network", artifact_path)
    for artifact_path in _discover_optional_paths(discover_publication_registry_workspace_dirs, resolved_search_roots, recursive=recursive):
        add_artifact("publication-registry-workspace", artifact_path)

    return sorted(artifact_paths)


def resolve_satroot_artifact_inputs(
    artifact_paths: Sequence[str | Path],
    *,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
) -> list[str]:
    resolved_paths: list[str] = []
    seen_paths: set[str] = set()

    for path in artifact_paths:
        resolved_path = str(Path(path).resolve())
        if resolved_path not in seen_paths:
            resolved_paths.append(resolved_path)
            seen_paths.add(resolved_path)

    if discover_under:
        for path in discover_satroot_artifact_paths(discover_under, recursive=recursive):
            if path not in seen_paths:
                resolved_paths.append(path)
                seen_paths.add(path)

    if not resolved_paths:
        raise SatRootError("at least one SATROOT artifact path or --discover-under root is required")
    return resolved_paths


def build_satroot_publication_descriptor_index(
    artifact_paths: Sequence[str | Path],
    *,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
    index_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    resolved_paths = resolve_satroot_artifact_inputs(
        artifact_paths,
        discover_under=discover_under,
        recursive=recursive,
    )

    descriptors = [build_satroot_artifact_descriptor(path) for path in resolved_paths]
    descriptors.sort(key=lambda entry: (str(entry.get("artifact_kind")), str(entry.get("artifact_path"))))

    kind_order = [
        "bundle",
        "release",
        "release-catalog",
        "release-catalog-index",
        "demo-catalog",
        "publication-stack",
        "publication-network",
        "publication-registry-workspace",
        "publication-registry",
    ]
    artifact_kind_counts = {
        kind: sum(1 for entry in descriptors if entry.get("artifact_kind") == kind)
        for kind in kind_order
    }

    index = {
        "type": "SATROOT-PUBLICATION-DESCRIPTOR-INDEX",
        "version": "0.1",
        "artifact_count": len(descriptors),
        "artifact_kind_counts": artifact_kind_counts,
        "artifacts": descriptors,
    }
    cleaned_metadata = {
        key: value
        for key, value in (index_metadata or {}).items()
        if isinstance(key, str) and key.strip() and isinstance(value, str) and value.strip()
    }
    if cleaned_metadata:
        index["index"] = cleaned_metadata
    return index


def validate_publication_descriptor_index_consistency(index: Mapping[str, Any]) -> None:
    artifacts = index.get("artifacts")
    artifact_count = index.get("artifact_count")
    artifact_kind_counts = index.get("artifact_kind_counts")
    if not isinstance(artifacts, list):
        raise SatRootError("publication descriptor index artifacts must be an array")
    if not isinstance(artifact_count, int) or artifact_count != len(artifacts):
        raise SatRootError("publication descriptor index artifact_count mismatch")
    if not isinstance(artifact_kind_counts, Mapping):
        raise SatRootError("publication descriptor index artifact_kind_counts must be an object")

    required_kinds = [
        "bundle",
        "release",
        "release-catalog",
        "release-catalog-index",
        "demo-catalog",
        "publication-stack",
        "publication-network",
        "publication-registry-workspace",
        "publication-registry",
    ]
    for kind in required_kinds:
        count = artifact_kind_counts.get(kind)
        if not isinstance(count, int) or count < 0:
            raise SatRootError(f"publication descriptor index artifact_kind_counts.{kind} must be a non-negative integer")

    actual_counts = {kind: 0 for kind in required_kinds}
    for entry in artifacts:
        if not isinstance(entry, Mapping):
            raise SatRootError("publication descriptor index artifacts must contain objects")
        validate_publication_descriptor_consistency(entry)
        artifact_kind = entry.get("artifact_kind")
        assert isinstance(artifact_kind, str)
        actual_counts[artifact_kind] += 1

    for kind, count in actual_counts.items():
        if artifact_kind_counts.get(kind) != count:
            raise SatRootError(f"publication descriptor index artifact_kind_counts.{kind} mismatch")


def publication_descriptor_index_manifest_signing_payload(manifest: Mapping[str, Any]) -> str:
    cleaned = {k: v for k, v in manifest.items() if k != "signature"}
    return canonical_json(cleaned)


def build_signed_publication_descriptor_index_manifest(
    publication_descriptor_index_json: str | Path,
    *,
    signature_scheme: str,
    key_id: str,
    signer: SignerFunction,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    if signature_scheme not in {"hmac-sha256", "ed25519"}:
        raise SatRootError(f"unsupported publication descriptor index signature scheme: {signature_scheme}")
    descriptor_index_path = Path(publication_descriptor_index_json).resolve()
    index = _load_json_file(str(descriptor_index_path))
    validate_instance_against_schema(index, load_publication_descriptor_index_schema())
    if not isinstance(index, dict):
        raise SatRootError("publication descriptor index must contain an object")
    validate_publication_descriptor_index_consistency(index)

    relative_index_path = _relative_output_path(descriptor_index_path, base_dir=base_dir)
    manifest = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "manifest_type": "publication-descriptor-index-manifest",
        "publication_descriptor_index_path": relative_index_path,
        "publication_descriptor_index_hash": "sha256:" + sha256_hex_bytes(descriptor_index_path.read_bytes()),
        "artifact_count": index.get("artifact_count"),
        "signature_scheme": signature_scheme,
        "signature_key_id": key_id,
    }
    index_metadata = index.get("index")
    if isinstance(index_metadata, dict) and index_metadata:
        manifest["index"] = copy.deepcopy(index_metadata)
    manifest["signature"] = signer(publication_descriptor_index_manifest_signing_payload(manifest), key_id)
    return manifest


def verify_signed_publication_descriptor_index_manifest(
    publication_descriptor_index_manifest_json: str | Path,
    *,
    verifier: SignatureVerifier,
) -> Dict[str, Any]:
    manifest_path = Path(publication_descriptor_index_manifest_json).resolve()
    manifest = _load_json_object_file(str(manifest_path), label="publication-descriptor-index-manifest")
    validate_instance_against_schema(manifest, load_publication_descriptor_index_manifest_schema())

    descriptor_index_ref = manifest.get("publication_descriptor_index_path")
    if not isinstance(descriptor_index_ref, str) or not descriptor_index_ref.strip():
        raise SatRootError("publication descriptor index manifest publication_descriptor_index_path must be a non-empty string")
    descriptor_index_path = (manifest_path.parent / descriptor_index_ref).resolve()
    if not descriptor_index_path.exists():
        raise SatRootError(f"publication descriptor index file not found: {descriptor_index_ref}")

    index = _load_json_file(str(descriptor_index_path))
    validate_instance_against_schema(index, load_publication_descriptor_index_schema())
    if not isinstance(index, dict):
        raise SatRootError("publication descriptor index must contain an object")
    validate_publication_descriptor_index_consistency(index)

    actual_index_hash = "sha256:" + sha256_hex_bytes(descriptor_index_path.read_bytes())
    if manifest.get("publication_descriptor_index_hash") != actual_index_hash:
        raise SatRootError("publication descriptor index manifest publication_descriptor_index_hash mismatch")
    if manifest.get("artifact_count") != index.get("artifact_count"):
        raise SatRootError("publication descriptor index manifest artifact_count mismatch")
    if manifest.get("index") != index.get("index"):
        raise SatRootError("publication descriptor index manifest index metadata mismatch")
    if not verifier(manifest, publication_descriptor_index_manifest_signing_payload(manifest)):
        raise SatRootError("publication descriptor index manifest signature verification failed")

    return {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "publication_descriptor_index_path": descriptor_index_ref,
        "publication_descriptor_index_hash": actual_index_hash,
        "artifact_count": index.get("artifact_count"),
        "index": copy.deepcopy(index.get("index")),
    }


def _load_publication_descriptor_index_publication(
    publication_descriptor_index_dir: str | Path,
) -> tuple[Path, Path, Dict[str, Any], Dict[str, Any]]:
    index_path = Path(publication_descriptor_index_dir).resolve()
    if not index_path.is_dir():
        raise SatRootError("publication descriptor index directory must be an existing directory")

    manifest_path = index_path / "publication_descriptor_index_manifest.json"
    if not manifest_path.is_file():
        raise SatRootError("publication_descriptor_index_manifest.json is required for publication descriptor index operations")
    manifest = _load_json_object_file(str(manifest_path), label="publication-descriptor-index-manifest")
    validate_instance_against_schema(manifest, load_publication_descriptor_index_manifest_schema())

    descriptor_index_ref = manifest.get("publication_descriptor_index_path")
    if not isinstance(descriptor_index_ref, str) or not descriptor_index_ref.strip():
        raise SatRootError("publication descriptor index manifest publication_descriptor_index_path must be a non-empty string")
    descriptor_index_path = (manifest_path.parent / descriptor_index_ref).resolve()
    if not descriptor_index_path.is_file():
        raise SatRootError(f"publication descriptor index file not found: {descriptor_index_ref}")

    index = _load_json_file(str(descriptor_index_path))
    validate_instance_against_schema(index, load_publication_descriptor_index_schema())
    if not isinstance(index, dict):
        raise SatRootError("publication descriptor index must contain an object")
    validate_publication_descriptor_index_consistency(index)
    return manifest_path, descriptor_index_path, manifest, index


def bootstrap_publication_descriptor_index_publication(
    artifact_paths: Sequence[str | Path],
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
    index_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    if signature_scheme == "hmac-sha256":
        material = bootstrap_release_hmac_material([key_id])
        signer = make_hmac_sha256_signer(material["shared_secrets"])
        _write_json_file(output_path / "publication_descriptor_index_secrets.json", material["shared_secrets"])
    elif signature_scheme == "ed25519":
        material = bootstrap_release_ed25519_material([key_id])
        signer = make_ed25519_signer(material["private_keys"])
        _write_json_file(output_path / "publication_descriptor_index_private_keys.json", material["private_keys"])
        _write_json_file(output_path / "publication_descriptor_index_public_keys.json", material["public_keys"])
    else:
        raise SatRootError(f"unsupported publication descriptor index signature scheme: {signature_scheme}")

    descriptor_index = build_satroot_publication_descriptor_index(
        artifact_paths,
        discover_under=discover_under,
        recursive=recursive,
        index_metadata=index_metadata,
    )
    descriptor_index_path = output_path / "publication_descriptor_index.json"
    _write_json_file(descriptor_index_path, descriptor_index)

    descriptor_index_manifest = build_signed_publication_descriptor_index_manifest(
        descriptor_index_path,
        signature_scheme=signature_scheme,
        key_id=key_id,
        signer=signer,
        base_dir=output_path,
    )
    descriptor_index_manifest_path = output_path / "publication_descriptor_index_manifest.json"
    _write_json_file(descriptor_index_manifest_path, descriptor_index_manifest)

    return {
        "publication_descriptor_index": descriptor_index,
        "publication_descriptor_index_path": str(descriptor_index_path),
        "publication_descriptor_index_manifest": descriptor_index_manifest,
        "publication_descriptor_index_manifest_path": str(descriptor_index_manifest_path),
        "publication_descriptor_index_material": material,
    }


def publication_metadata_manifest_signing_payload(manifest: Mapping[str, Any]) -> str:
    cleaned = {k: v for k, v in manifest.items() if k != "signature"}
    return canonical_json(cleaned)


def build_signed_publication_metadata_manifest(
    publication_report_path: str | Path,
    publication_descriptor_json: str | Path,
    *,
    signature_scheme: str,
    key_id: str,
    signer: SignerFunction,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    if signature_scheme not in {"hmac-sha256", "ed25519"}:
        raise SatRootError(f"unsupported publication metadata signature scheme: {signature_scheme}")
    report_path = Path(publication_report_path).resolve()
    descriptor_path = Path(publication_descriptor_json).resolve()
    if not report_path.is_file():
        raise SatRootError("publication report file must exist")
    descriptor = _load_json_object_file(str(descriptor_path), label="publication descriptor")
    validate_publication_descriptor_consistency(descriptor)

    relative_report_path = _relative_output_path(report_path, base_dir=base_dir)
    relative_descriptor_path = _relative_output_path(descriptor_path, base_dir=base_dir)
    manifest = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "manifest_type": "publication-metadata-manifest",
        "artifact_kind": descriptor.get("artifact_kind"),
        "artifact_path": descriptor.get("artifact_path"),
        "publication_report_path": relative_report_path,
        "publication_report_hash": "sha256:" + sha256_hex_bytes(report_path.read_bytes()),
        "publication_descriptor_path": relative_descriptor_path,
        "publication_descriptor_hash": "sha256:" + sha256_hex_bytes(descriptor_path.read_bytes()),
        "signature_scheme": signature_scheme,
        "signature_key_id": key_id,
    }
    manifest["signature"] = signer(publication_metadata_manifest_signing_payload(manifest), key_id)
    return manifest


def verify_signed_publication_metadata_manifest(
    publication_metadata_manifest_json: str | Path,
    *,
    verifier: SignatureVerifier,
) -> Dict[str, Any]:
    manifest_path = Path(publication_metadata_manifest_json).resolve()
    manifest = _load_json_object_file(str(manifest_path), label="publication-metadata-manifest")
    validate_instance_against_schema(manifest, load_publication_metadata_manifest_schema())

    report_ref = manifest.get("publication_report_path")
    if not isinstance(report_ref, str) or not report_ref.strip():
        raise SatRootError("publication metadata manifest publication_report_path must be a non-empty string")
    descriptor_ref = manifest.get("publication_descriptor_path")
    if not isinstance(descriptor_ref, str) or not descriptor_ref.strip():
        raise SatRootError("publication metadata manifest publication_descriptor_path must be a non-empty string")

    report_path = (manifest_path.parent / report_ref).resolve()
    descriptor_path = (manifest_path.parent / descriptor_ref).resolve()
    if not report_path.is_file():
        raise SatRootError(f"publication report file not found: {report_ref}")
    if not descriptor_path.is_file():
        raise SatRootError(f"publication descriptor file not found: {descriptor_ref}")

    descriptor = _load_json_object_file(str(descriptor_path), label="publication descriptor")
    validate_publication_descriptor_consistency(descriptor)

    actual_report_hash = "sha256:" + sha256_hex_bytes(report_path.read_bytes())
    actual_descriptor_hash = "sha256:" + sha256_hex_bytes(descriptor_path.read_bytes())
    if manifest.get("publication_report_hash") != actual_report_hash:
        raise SatRootError("publication metadata manifest publication_report_hash mismatch")
    if manifest.get("publication_descriptor_hash") != actual_descriptor_hash:
        raise SatRootError("publication metadata manifest publication_descriptor_hash mismatch")
    if manifest.get("artifact_kind") != descriptor.get("artifact_kind"):
        raise SatRootError("publication metadata manifest artifact_kind mismatch")
    if manifest.get("artifact_path") != descriptor.get("artifact_path"):
        raise SatRootError("publication metadata manifest artifact_path mismatch")
    if not verifier(manifest, publication_metadata_manifest_signing_payload(manifest)):
        raise SatRootError("publication metadata manifest signature verification failed")

    return {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "artifact_kind": manifest.get("artifact_kind"),
        "artifact_path": manifest.get("artifact_path"),
        "publication_report_path": report_ref,
        "publication_report_hash": actual_report_hash,
        "publication_descriptor_path": descriptor_ref,
        "publication_descriptor_hash": actual_descriptor_hash,
    }


def bootstrap_publication_metadata_bundle(
    artifact_path: str | Path,
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
) -> Dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    if signature_scheme == "hmac-sha256":
        material = bootstrap_release_hmac_material([key_id])
        signer = make_hmac_sha256_signer(material["shared_secrets"])
        _write_json_file(output_path / "publication_metadata_secrets.json", material["shared_secrets"])
    elif signature_scheme == "ed25519":
        material = bootstrap_release_ed25519_material([key_id])
        signer = make_ed25519_signer(material["private_keys"])
        _write_json_file(output_path / "publication_metadata_private_keys.json", material["private_keys"])
        _write_json_file(output_path / "publication_metadata_public_keys.json", material["public_keys"])
    else:
        raise SatRootError(f"unsupported publication metadata signature scheme: {signature_scheme}")

    report = render_satroot_artifact_report(artifact_path)
    descriptor = build_satroot_artifact_descriptor(artifact_path)
    report_path = output_path / "publication_report.md"
    descriptor_path = output_path / "publication_descriptor.json"
    _write_text_output(report, str(report_path))
    _write_json_file(descriptor_path, descriptor)

    manifest = build_signed_publication_metadata_manifest(
        report_path,
        descriptor_path,
        signature_scheme=signature_scheme,
        key_id=key_id,
        signer=signer,
        base_dir=output_path,
    )
    manifest_path = output_path / "publication_metadata_manifest.json"
    _write_json_file(manifest_path, manifest)

    return {
        "publication_report_path": str(report_path),
        "publication_descriptor_path": str(descriptor_path),
        "publication_metadata_manifest": manifest,
        "publication_metadata_manifest_path": str(manifest_path),
        "publication_metadata_material": material,
    }


def bootstrap_publication_metadata_bundle_collection(
    artifact_paths: Sequence[str | Path],
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
) -> Dict[str, Any]:
    resolved_artifact_paths = resolve_satroot_artifact_inputs(artifact_paths)
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    bundle_names = _unique_workspace_names(resolved_artifact_paths)
    bundle_dirs: list[str] = []
    bundles: list[Dict[str, Any]] = []

    for artifact_path, bundle_name in zip(resolved_artifact_paths, bundle_names):
        descriptor = build_satroot_artifact_descriptor(artifact_path)
        bundle_dir = output_path / bundle_name
        bundle = bootstrap_publication_metadata_bundle(
            artifact_path,
            output_dir=bundle_dir,
            signature_scheme=signature_scheme,
            key_id=key_id,
        )
        bundle_dirs.append(str(bundle_dir.resolve()))
        bundles.append(
            {
                "bundle_name": bundle_name,
                "artifact_path": artifact_path,
                "artifact_kind": descriptor.get("artifact_kind"),
                "bundle_dir": str(bundle_dir.resolve()),
                "publication_metadata_manifest_path": bundle.get("publication_metadata_manifest_path"),
                "publication_report_path": bundle.get("publication_report_path"),
                "publication_descriptor_path": bundle.get("publication_descriptor_path"),
            }
        )

    return {
        "bundle_dirs": bundle_dirs,
        "bundles": bundles,
    }


def discover_publication_metadata_bundle_dirs(
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
) -> list[str]:
    if not search_roots:
        raise SatRootError("at least one publication metadata bundle discovery root is required")

    discovered: Dict[str, str] = {}
    for search_root in search_roots:
        root_path = Path(search_root).resolve()
        if not root_path.exists():
            raise SatRootError(f"publication metadata bundle discovery root not found: {search_root}")
        if not root_path.is_dir():
            raise SatRootError(f"publication metadata bundle discovery root must be a directory: {search_root}")

        manifest_paths = root_path.rglob("publication_metadata_manifest.json") if recursive else root_path.glob("publication_metadata_manifest.json")
        for manifest_path in manifest_paths:
            bundle_dir = str(manifest_path.parent.resolve())
            discovered.setdefault(bundle_dir, bundle_dir)

    if not discovered:
        raise SatRootError("no publication metadata bundle directories found under the provided discovery roots")
    return sorted(discovered.values())


def resolve_publication_metadata_bundle_inputs(
    bundle_dirs: Sequence[str | Path],
    *,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
) -> list[str | Path]:
    resolved: list[str | Path] = []
    seen: set[str] = set()

    for bundle_dir in bundle_dirs:
        bundle_path = str(Path(bundle_dir).resolve())
        if bundle_path not in seen:
            resolved.append(bundle_dir)
            seen.add(bundle_path)

    if discover_under:
        for bundle_dir in discover_publication_metadata_bundle_dirs(discover_under, recursive=recursive):
            if bundle_dir not in seen:
                resolved.append(bundle_dir)
                seen.add(bundle_dir)

    if not resolved:
        raise SatRootError("at least one publication metadata bundle directory or --discover-under path is required")
    return resolved


def _load_publication_metadata_bundle_publication(
    publication_metadata_bundle_dir: str | Path,
) -> tuple[Path, Path, Path, Dict[str, Any], Dict[str, Any]]:
    bundle_path = Path(publication_metadata_bundle_dir).resolve()
    if not bundle_path.is_dir():
        raise SatRootError(f"publication metadata bundle directory not found: {publication_metadata_bundle_dir}")

    manifest_path = bundle_path / "publication_metadata_manifest.json"
    if not manifest_path.is_file():
        raise SatRootError("publication_metadata_manifest.json is required for publication metadata bundle operations")

    manifest = _load_json_object_file(str(manifest_path), label="publication-metadata-manifest")
    validate_instance_against_schema(manifest, load_publication_metadata_manifest_schema())

    report_ref = manifest.get("publication_report_path")
    if not isinstance(report_ref, str) or not report_ref.strip():
        raise SatRootError("publication metadata manifest publication_report_path must be a non-empty string")
    descriptor_ref = manifest.get("publication_descriptor_path")
    if not isinstance(descriptor_ref, str) or not descriptor_ref.strip():
        raise SatRootError("publication metadata manifest publication_descriptor_path must be a non-empty string")

    report_path = (manifest_path.parent / report_ref).resolve()
    descriptor_path = (manifest_path.parent / descriptor_ref).resolve()
    if not report_path.is_file():
        raise SatRootError(f"publication report file not found: {report_ref}")
    if not descriptor_path.is_file():
        raise SatRootError(f"publication descriptor file not found: {descriptor_ref}")

    descriptor = _load_json_object_file(str(descriptor_path), label="publication descriptor")
    validate_publication_descriptor_consistency(descriptor)

    actual_report_hash = "sha256:" + sha256_hex_bytes(report_path.read_bytes())
    actual_descriptor_hash = "sha256:" + sha256_hex_bytes(descriptor_path.read_bytes())
    if manifest.get("publication_report_hash") != actual_report_hash:
        raise SatRootError("publication metadata manifest publication_report_hash mismatch")
    if manifest.get("publication_descriptor_hash") != actual_descriptor_hash:
        raise SatRootError("publication metadata manifest publication_descriptor_hash mismatch")
    if manifest.get("artifact_kind") != descriptor.get("artifact_kind"):
        raise SatRootError("publication metadata manifest artifact_kind mismatch")
    if manifest.get("artifact_path") != descriptor.get("artifact_path"):
        raise SatRootError("publication metadata manifest artifact_path mismatch")

    return manifest_path, report_path, descriptor_path, manifest, descriptor


def build_publication_metadata_catalog(
    bundle_dirs: Sequence[str | Path],
    *,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
    base_dir: str | Path = ".",
    catalog_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    resolved_bundle_dirs = resolve_publication_metadata_bundle_inputs(
        bundle_dirs,
        discover_under=discover_under,
        recursive=recursive,
    )

    bundles: list[Dict[str, Any]] = []
    for bundle_dir in resolved_bundle_dirs:
        bundle_path = Path(bundle_dir).resolve()
        manifest_path, report_path, descriptor_path, manifest, _descriptor = _load_publication_metadata_bundle_publication(bundle_path)
        bundle_ref = _relative_output_path(bundle_path, base_dir=base_dir)
        manifest_ref = _relative_output_path(manifest_path, base_dir=base_dir)
        report_ref = _relative_output_path(report_path, base_dir=base_dir)
        descriptor_ref = _relative_output_path(descriptor_path, base_dir=base_dir)

        bundles.append(
            {
                "publication_metadata_bundle_id": "sha256:" + sha256_hex(bundle_ref),
                "publication_metadata_bundle_path": bundle_ref,
                "publication_metadata_manifest_path": manifest_ref,
                "publication_metadata_manifest_hash": "sha256:" + sha256_hex_bytes(manifest_path.read_bytes()),
                "publication_report_path": report_ref,
                "publication_report_hash": manifest.get("publication_report_hash"),
                "publication_descriptor_path": descriptor_ref,
                "publication_descriptor_hash": manifest.get("publication_descriptor_hash"),
                "artifact_kind": manifest.get("artifact_kind"),
                "artifact_path": manifest.get("artifact_path"),
                "signature_scheme": manifest.get("signature_scheme"),
                "signature_key_id": manifest.get("signature_key_id"),
            }
        )

    bundles.sort(
        key=lambda entry: (
            str(entry.get("artifact_kind")),
            str(entry.get("artifact_path")),
            str(entry.get("publication_metadata_manifest_path")),
        )
    )

    kind_order = [
        "bundle",
        "release",
        "release-catalog",
        "release-catalog-index",
        "demo-catalog",
        "publication-stack",
        "publication-network",
        "publication-registry-workspace",
        "publication-registry",
    ]
    artifact_kind_counts = {
        kind: sum(1 for entry in bundles if entry.get("artifact_kind") == kind)
        for kind in kind_order
    }

    catalog = {
        "type": "SATROOT-PUBLICATION-METADATA-CATALOG",
        "version": "0.1",
        "bundle_count": len(bundles),
        "artifact_kind_counts": artifact_kind_counts,
        "bundles": bundles,
    }
    cleaned_metadata = {
        key: value
        for key, value in (catalog_metadata or {}).items()
        if isinstance(key, str) and key.strip() and isinstance(value, str) and value.strip()
    }
    if cleaned_metadata:
        catalog["index"] = cleaned_metadata
    return catalog


def validate_publication_metadata_catalog_consistency(catalog: Mapping[str, Any]) -> None:
    bundles = catalog.get("bundles")
    bundle_count = catalog.get("bundle_count")
    artifact_kind_counts = catalog.get("artifact_kind_counts")
    if not isinstance(bundles, list):
        raise SatRootError("publication metadata catalog bundles must be an array")
    if not isinstance(bundle_count, int) or bundle_count != len(bundles):
        raise SatRootError("publication metadata catalog bundle_count mismatch")
    if not isinstance(artifact_kind_counts, Mapping):
        raise SatRootError("publication metadata catalog artifact_kind_counts must be an object")

    required_kinds = [
        "bundle",
        "release",
        "release-catalog",
        "release-catalog-index",
        "demo-catalog",
        "publication-stack",
        "publication-network",
        "publication-registry-workspace",
        "publication-registry",
    ]
    for kind in required_kinds:
        count = artifact_kind_counts.get(kind)
        if not isinstance(count, int) or count < 0:
            raise SatRootError(f"publication metadata catalog artifact_kind_counts.{kind} must be a non-negative integer")

    actual_counts = {kind: 0 for kind in required_kinds}
    required_fields = [
        "publication_metadata_bundle_id",
        "publication_metadata_bundle_path",
        "publication_metadata_manifest_path",
        "publication_metadata_manifest_hash",
        "publication_report_path",
        "publication_report_hash",
        "publication_descriptor_path",
        "publication_descriptor_hash",
        "artifact_kind",
        "artifact_path",
        "signature_scheme",
        "signature_key_id",
    ]
    for entry in bundles:
        if not isinstance(entry, Mapping):
            raise SatRootError("publication metadata catalog bundles must contain objects")
        for field_name in required_fields:
            field_value = entry.get(field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                raise SatRootError(f"publication metadata catalog bundles.{field_name} must be a non-empty string")
        artifact_kind = entry.get("artifact_kind")
        assert isinstance(artifact_kind, str)
        if artifact_kind not in actual_counts:
            raise SatRootError("publication metadata catalog bundles.artifact_kind must be a supported descriptor kind")
        actual_counts[artifact_kind] += 1

    for kind, count in actual_counts.items():
        if artifact_kind_counts.get(kind) != count:
            raise SatRootError(f"publication metadata catalog artifact_kind_counts.{kind} mismatch")


def publication_metadata_catalog_manifest_signing_payload(manifest: Mapping[str, Any]) -> str:
    cleaned = {k: v for k, v in manifest.items() if k != "signature"}
    return canonical_json(cleaned)


def build_signed_publication_metadata_catalog_manifest(
    publication_metadata_catalog_json: str | Path,
    *,
    signature_scheme: str,
    key_id: str,
    signer: SignerFunction,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    if signature_scheme not in {"hmac-sha256", "ed25519"}:
        raise SatRootError(f"unsupported publication metadata catalog signature scheme: {signature_scheme}")
    catalog_path = Path(publication_metadata_catalog_json).resolve()
    catalog = _load_json_file(str(catalog_path))
    validate_instance_against_schema(catalog, load_publication_metadata_catalog_schema())
    if not isinstance(catalog, dict):
        raise SatRootError("publication metadata catalog must contain an object")
    validate_publication_metadata_catalog_consistency(catalog)

    relative_catalog_path = _relative_output_path(catalog_path, base_dir=base_dir)
    manifest = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "manifest_type": "publication-metadata-catalog-manifest",
        "publication_metadata_catalog_path": relative_catalog_path,
        "publication_metadata_catalog_hash": "sha256:" + sha256_hex_bytes(catalog_path.read_bytes()),
        "bundle_count": catalog.get("bundle_count"),
        "signature_scheme": signature_scheme,
        "signature_key_id": key_id,
    }
    index_metadata = catalog.get("index")
    if isinstance(index_metadata, dict) and index_metadata:
        manifest["index"] = copy.deepcopy(index_metadata)
    manifest["signature"] = signer(publication_metadata_catalog_manifest_signing_payload(manifest), key_id)
    return manifest


def verify_signed_publication_metadata_catalog_manifest(
    publication_metadata_catalog_manifest_json: str | Path,
    *,
    verifier: SignatureVerifier,
) -> Dict[str, Any]:
    manifest_path = Path(publication_metadata_catalog_manifest_json).resolve()
    manifest = _load_json_object_file(str(manifest_path), label="publication-metadata-catalog-manifest")
    validate_instance_against_schema(manifest, load_publication_metadata_catalog_manifest_schema())

    catalog_ref = manifest.get("publication_metadata_catalog_path")
    if not isinstance(catalog_ref, str) or not catalog_ref.strip():
        raise SatRootError("publication metadata catalog manifest publication_metadata_catalog_path must be a non-empty string")
    catalog_path = (manifest_path.parent / catalog_ref).resolve()
    if not catalog_path.is_file():
        raise SatRootError(f"publication metadata catalog file not found: {catalog_ref}")

    catalog = _load_json_file(str(catalog_path))
    validate_instance_against_schema(catalog, load_publication_metadata_catalog_schema())
    if not isinstance(catalog, dict):
        raise SatRootError("publication metadata catalog must contain an object")
    validate_publication_metadata_catalog_consistency(catalog)

    actual_catalog_hash = "sha256:" + sha256_hex_bytes(catalog_path.read_bytes())
    if manifest.get("publication_metadata_catalog_hash") != actual_catalog_hash:
        raise SatRootError("publication metadata catalog manifest publication_metadata_catalog_hash mismatch")
    if manifest.get("bundle_count") != catalog.get("bundle_count"):
        raise SatRootError("publication metadata catalog manifest bundle_count mismatch")
    if manifest.get("index") != catalog.get("index"):
        raise SatRootError("publication metadata catalog manifest index metadata mismatch")

    bundles = catalog.get("bundles")
    assert isinstance(bundles, list)
    for entry in bundles:
        assert isinstance(entry, Mapping)
        bundle_dir = (catalog_path.parent / str(entry.get("publication_metadata_bundle_path"))).resolve()
        manifest_entry_path = (catalog_path.parent / str(entry.get("publication_metadata_manifest_path"))).resolve()
        report_path = (catalog_path.parent / str(entry.get("publication_report_path"))).resolve()
        descriptor_path = (catalog_path.parent / str(entry.get("publication_descriptor_path"))).resolve()
        if not bundle_dir.is_dir():
            raise SatRootError(f"publication metadata bundle directory not found: {entry.get('publication_metadata_bundle_path')}")
        if not manifest_entry_path.is_file():
            raise SatRootError(f"publication metadata manifest file not found: {entry.get('publication_metadata_manifest_path')}")
        if not report_path.is_file():
            raise SatRootError(f"publication report file not found: {entry.get('publication_report_path')}")
        if not descriptor_path.is_file():
            raise SatRootError(f"publication descriptor file not found: {entry.get('publication_descriptor_path')}")

        actual_manifest_hash = "sha256:" + sha256_hex_bytes(manifest_entry_path.read_bytes())
        actual_report_hash = "sha256:" + sha256_hex_bytes(report_path.read_bytes())
        actual_descriptor_hash = "sha256:" + sha256_hex_bytes(descriptor_path.read_bytes())
        if entry.get("publication_metadata_manifest_hash") != actual_manifest_hash:
            raise SatRootError("publication metadata catalog publication_metadata_manifest_hash mismatch")
        if entry.get("publication_report_hash") != actual_report_hash:
            raise SatRootError("publication metadata catalog publication_report_hash mismatch")
        if entry.get("publication_descriptor_hash") != actual_descriptor_hash:
            raise SatRootError("publication metadata catalog publication_descriptor_hash mismatch")

        nested_manifest = _load_json_object_file(str(manifest_entry_path), label="publication-metadata-manifest")
        validate_instance_against_schema(nested_manifest, load_publication_metadata_manifest_schema())
        descriptor = _load_json_object_file(str(descriptor_path), label="publication descriptor")
        validate_publication_descriptor_consistency(descriptor)

        nested_report_path = (manifest_entry_path.parent / str(nested_manifest.get("publication_report_path"))).resolve()
        nested_descriptor_path = (manifest_entry_path.parent / str(nested_manifest.get("publication_descriptor_path"))).resolve()
        if nested_report_path != report_path:
            raise SatRootError("publication metadata catalog publication_report_path does not match nested manifest")
        if nested_descriptor_path != descriptor_path:
            raise SatRootError("publication metadata catalog publication_descriptor_path does not match nested manifest")
        if entry.get("artifact_kind") != nested_manifest.get("artifact_kind"):
            raise SatRootError("publication metadata catalog artifact_kind mismatch")
        if entry.get("artifact_path") != nested_manifest.get("artifact_path"):
            raise SatRootError("publication metadata catalog artifact_path mismatch")
        if entry.get("signature_scheme") != nested_manifest.get("signature_scheme"):
            raise SatRootError("publication metadata catalog signature_scheme mismatch")
        if entry.get("signature_key_id") != nested_manifest.get("signature_key_id"):
            raise SatRootError("publication metadata catalog signature_key_id mismatch")
        if entry.get("publication_report_hash") != nested_manifest.get("publication_report_hash"):
            raise SatRootError("publication metadata catalog publication_report_hash does not match nested manifest")
        if entry.get("publication_descriptor_hash") != nested_manifest.get("publication_descriptor_hash"):
            raise SatRootError("publication metadata catalog publication_descriptor_hash does not match nested manifest")

    if not verifier(manifest, publication_metadata_catalog_manifest_signing_payload(manifest)):
        raise SatRootError("publication metadata catalog manifest signature verification failed")

    return {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "publication_metadata_catalog_path": catalog_ref,
        "publication_metadata_catalog_hash": actual_catalog_hash,
        "bundle_count": catalog.get("bundle_count"),
        "index": copy.deepcopy(catalog.get("index")),
    }


def bootstrap_publication_metadata_catalog_publication(
    bundle_dirs: Sequence[str | Path],
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
    discover_under: Optional[Sequence[str | Path]] = None,
    recursive: bool = True,
    catalog_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    if signature_scheme == "hmac-sha256":
        material = bootstrap_release_hmac_material([key_id])
        signer = make_hmac_sha256_signer(material["shared_secrets"])
        _write_json_file(output_path / "publication_metadata_catalog_secrets.json", material["shared_secrets"])
    elif signature_scheme == "ed25519":
        material = bootstrap_release_ed25519_material([key_id])
        signer = make_ed25519_signer(material["private_keys"])
        _write_json_file(output_path / "publication_metadata_catalog_private_keys.json", material["private_keys"])
        _write_json_file(output_path / "publication_metadata_catalog_public_keys.json", material["public_keys"])
    else:
        raise SatRootError(f"unsupported publication metadata catalog signature scheme: {signature_scheme}")

    catalog = build_publication_metadata_catalog(
        bundle_dirs,
        discover_under=discover_under,
        recursive=recursive,
        base_dir=output_path,
        catalog_metadata=catalog_metadata,
    )
    catalog_path = output_path / "publication_metadata_catalog.json"
    _write_json_file(catalog_path, catalog)

    catalog_manifest = build_signed_publication_metadata_catalog_manifest(
        catalog_path,
        signature_scheme=signature_scheme,
        key_id=key_id,
        signer=signer,
        base_dir=output_path,
    )
    catalog_manifest_path = output_path / "publication_metadata_catalog_manifest.json"
    _write_json_file(catalog_manifest_path, catalog_manifest)

    return {
        "publication_metadata_catalog": catalog,
        "publication_metadata_catalog_path": str(catalog_path),
        "publication_metadata_catalog_manifest": catalog_manifest,
        "publication_metadata_catalog_manifest_path": str(catalog_manifest_path),
        "publication_metadata_catalog_material": material,
    }


def _load_publication_metadata_catalog_publication(
    publication_metadata_catalog_dir: str | Path,
) -> tuple[Path, Path, Dict[str, Any], Dict[str, Any]]:
    catalog_dir = Path(publication_metadata_catalog_dir).resolve()
    if not catalog_dir.is_dir():
        raise SatRootError("publication metadata catalog directory must be an existing directory")

    manifest_path = catalog_dir / "publication_metadata_catalog_manifest.json"
    if not manifest_path.is_file():
        raise SatRootError("publication_metadata_catalog_manifest.json is required for publication metadata catalog operations")
    manifest = _load_json_object_file(str(manifest_path), label="publication-metadata-catalog-manifest")
    validate_instance_against_schema(manifest, load_publication_metadata_catalog_manifest_schema())

    catalog_ref = manifest.get("publication_metadata_catalog_path")
    if not isinstance(catalog_ref, str) or not catalog_ref.strip():
        raise SatRootError("publication metadata catalog manifest publication_metadata_catalog_path must be a non-empty string")
    catalog_path = (manifest_path.parent / catalog_ref).resolve()
    if not catalog_path.is_file():
        raise SatRootError(f"publication metadata catalog file not found: {catalog_ref}")

    catalog = _load_json_file(str(catalog_path))
    validate_instance_against_schema(catalog, load_publication_metadata_catalog_schema())
    if not isinstance(catalog, dict):
        raise SatRootError("publication metadata catalog must contain an object")
    validate_publication_metadata_catalog_consistency(catalog)
    return manifest_path, catalog_path, manifest, catalog


def build_publication_registry(
    *,
    release_catalog_index_dir: Optional[str | Path] = None,
    publication_descriptor_index_dir: Optional[str | Path] = None,
    publication_metadata_catalog_dir: Optional[str | Path] = None,
    base_dir: str | Path = ".",
    registry_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    registry: Dict[str, Any] = {
        "type": "SATROOT-PUBLICATION-REGISTRY",
        "version": "0.1",
    }
    component_count = 0

    if release_catalog_index_dir is not None:
        publication_dir = Path(release_catalog_index_dir).resolve()
        manifest_path, index_path, manifest, index = _load_release_catalog_index_publication(publication_dir)
        registry["release_catalog_index_publication"] = {
            "publication_directory_path": _relative_output_path(publication_dir, base_dir=base_dir),
            "release_catalog_index_manifest_path": _relative_output_path(manifest_path, base_dir=base_dir),
            "release_catalog_index_manifest_hash": "sha256:" + sha256_hex_bytes(manifest_path.read_bytes()),
            "release_catalog_index_json_path": _relative_output_path(index_path, base_dir=base_dir),
            "release_catalog_index_hash": "sha256:" + sha256_hex_bytes(index_path.read_bytes()),
            "signature_scheme": manifest.get("signature_scheme"),
            "signature_key_id": manifest.get("signature_key_id"),
            "release_catalog_count": index.get("release_catalog_count"),
            "index": copy.deepcopy(index.get("index")),
        }
        component_count += 1

    if publication_descriptor_index_dir is not None:
        publication_dir = Path(publication_descriptor_index_dir).resolve()
        manifest_path, index_path, manifest, index = _load_publication_descriptor_index_publication(publication_dir)
        registry["publication_descriptor_index_publication"] = {
            "publication_directory_path": _relative_output_path(publication_dir, base_dir=base_dir),
            "publication_descriptor_index_manifest_path": _relative_output_path(manifest_path, base_dir=base_dir),
            "publication_descriptor_index_manifest_hash": "sha256:" + sha256_hex_bytes(manifest_path.read_bytes()),
            "publication_descriptor_index_json_path": _relative_output_path(index_path, base_dir=base_dir),
            "publication_descriptor_index_hash": "sha256:" + sha256_hex_bytes(index_path.read_bytes()),
            "signature_scheme": manifest.get("signature_scheme"),
            "signature_key_id": manifest.get("signature_key_id"),
            "artifact_count": index.get("artifact_count"),
            "index": copy.deepcopy(index.get("index")),
        }
        component_count += 1

    if publication_metadata_catalog_dir is not None:
        publication_dir = Path(publication_metadata_catalog_dir).resolve()
        manifest_path, catalog_path, manifest, catalog = _load_publication_metadata_catalog_publication(publication_dir)
        registry["publication_metadata_catalog_publication"] = {
            "publication_directory_path": _relative_output_path(publication_dir, base_dir=base_dir),
            "publication_metadata_catalog_manifest_path": _relative_output_path(manifest_path, base_dir=base_dir),
            "publication_metadata_catalog_manifest_hash": "sha256:" + sha256_hex_bytes(manifest_path.read_bytes()),
            "publication_metadata_catalog_json_path": _relative_output_path(catalog_path, base_dir=base_dir),
            "publication_metadata_catalog_hash": "sha256:" + sha256_hex_bytes(catalog_path.read_bytes()),
            "signature_scheme": manifest.get("signature_scheme"),
            "signature_key_id": manifest.get("signature_key_id"),
            "bundle_count": catalog.get("bundle_count"),
            "index": copy.deepcopy(catalog.get("index")),
        }
        component_count += 1

    if component_count == 0:
        raise SatRootError("build-publication-registry requires at least one publication component directory")

    registry["component_count"] = component_count
    cleaned_metadata = {
        key: value
        for key, value in (registry_metadata or {}).items()
        if isinstance(key, str) and key.strip() and isinstance(value, str) and value.strip()
    }
    if cleaned_metadata:
        registry["index"] = cleaned_metadata
    return registry


def validate_publication_registry_consistency(registry: Mapping[str, Any]) -> None:
    component_count = registry.get("component_count")
    if not isinstance(component_count, int) or component_count < 1:
        raise SatRootError("publication registry component_count must be a positive integer")

    component_names = [
        "release_catalog_index_publication",
        "publication_descriptor_index_publication",
        "publication_metadata_catalog_publication",
    ]
    required_fields = {
        "release_catalog_index_publication": [
            "publication_directory_path",
            "release_catalog_index_manifest_path",
            "release_catalog_index_manifest_hash",
            "release_catalog_index_json_path",
            "release_catalog_index_hash",
            "signature_scheme",
            "signature_key_id",
            "release_catalog_count",
        ],
        "publication_descriptor_index_publication": [
            "publication_directory_path",
            "publication_descriptor_index_manifest_path",
            "publication_descriptor_index_manifest_hash",
            "publication_descriptor_index_json_path",
            "publication_descriptor_index_hash",
            "signature_scheme",
            "signature_key_id",
            "artifact_count",
        ],
        "publication_metadata_catalog_publication": [
            "publication_directory_path",
            "publication_metadata_catalog_manifest_path",
            "publication_metadata_catalog_manifest_hash",
            "publication_metadata_catalog_json_path",
            "publication_metadata_catalog_hash",
            "signature_scheme",
            "signature_key_id",
            "bundle_count",
        ],
    }

    present_count = 0
    for component_name in component_names:
        component = registry.get(component_name)
        if component is None:
            continue
        present_count += 1
        if not isinstance(component, Mapping):
            raise SatRootError(f"publication registry {component_name} must be an object")
        for field_name in required_fields[component_name]:
            field_value = component.get(field_name)
            if field_name.endswith("_count"):
                if not isinstance(field_value, int) or field_value < 1:
                    raise SatRootError(f"publication registry {component_name}.{field_name} must be a positive integer")
            else:
                if not isinstance(field_value, str) or not field_value.strip():
                    raise SatRootError(f"publication registry {component_name}.{field_name} must be a non-empty string")
    if present_count != component_count:
        raise SatRootError("publication registry component_count mismatch")


def publication_registry_manifest_signing_payload(manifest: Mapping[str, Any]) -> str:
    cleaned = {k: v for k, v in manifest.items() if k != "signature"}
    return canonical_json(cleaned)


def build_signed_publication_registry_manifest(
    publication_registry_json: str | Path,
    *,
    signature_scheme: str,
    key_id: str,
    signer: SignerFunction,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    if signature_scheme not in {"hmac-sha256", "ed25519"}:
        raise SatRootError(f"unsupported publication registry signature scheme: {signature_scheme}")
    registry_path = Path(publication_registry_json).resolve()
    registry = _load_json_file(str(registry_path))
    validate_instance_against_schema(registry, load_publication_registry_schema())
    if not isinstance(registry, dict):
        raise SatRootError("publication registry must contain an object")
    validate_publication_registry_consistency(registry)

    relative_registry_path = _relative_output_path(registry_path, base_dir=base_dir)
    manifest = {
        "protocol": "SATROOT-1",
        "version": "0.1",
        "manifest_type": "publication-registry-manifest",
        "publication_registry_path": relative_registry_path,
        "publication_registry_hash": "sha256:" + sha256_hex_bytes(registry_path.read_bytes()),
        "component_count": registry.get("component_count"),
        "signature_scheme": signature_scheme,
        "signature_key_id": key_id,
    }
    registry_index = registry.get("index")
    if isinstance(registry_index, dict) and registry_index:
        manifest["index"] = copy.deepcopy(registry_index)
    manifest["signature"] = signer(publication_registry_manifest_signing_payload(manifest), key_id)
    return manifest


def verify_signed_publication_registry_manifest(
    publication_registry_manifest_json: str | Path,
    *,
    verifier: SignatureVerifier,
) -> Dict[str, Any]:
    manifest_path = Path(publication_registry_manifest_json).resolve()
    manifest = _load_json_object_file(str(manifest_path), label="publication-registry-manifest")
    validate_instance_against_schema(manifest, load_publication_registry_manifest_schema())

    registry_ref = manifest.get("publication_registry_path")
    if not isinstance(registry_ref, str) or not registry_ref.strip():
        raise SatRootError("publication registry manifest publication_registry_path must be a non-empty string")
    registry_path = (manifest_path.parent / registry_ref).resolve()
    if not registry_path.is_file():
        raise SatRootError(f"publication registry file not found: {registry_ref}")

    registry = _load_json_file(str(registry_path))
    validate_instance_against_schema(registry, load_publication_registry_schema())
    if not isinstance(registry, dict):
        raise SatRootError("publication registry must contain an object")
    validate_publication_registry_consistency(registry)

    actual_registry_hash = "sha256:" + sha256_hex_bytes(registry_path.read_bytes())
    if manifest.get("publication_registry_hash") != actual_registry_hash:
        raise SatRootError("publication registry manifest publication_registry_hash mismatch")
    if manifest.get("component_count") != registry.get("component_count"):
        raise SatRootError("publication registry manifest component_count mismatch")
    if manifest.get("index") != registry.get("index"):
        raise SatRootError("publication registry manifest index metadata mismatch")

    release_catalog_component = registry.get("release_catalog_index_publication")
    if isinstance(release_catalog_component, Mapping):
        publication_dir = (registry_path.parent / str(release_catalog_component.get("publication_directory_path"))).resolve()
        manifest_entry_path = (registry_path.parent / str(release_catalog_component.get("release_catalog_index_manifest_path"))).resolve()
        index_entry_path = (registry_path.parent / str(release_catalog_component.get("release_catalog_index_json_path"))).resolve()
        loaded_manifest_path, loaded_index_path, loaded_manifest, loaded_index = _load_release_catalog_index_publication(publication_dir)
        if manifest_entry_path != loaded_manifest_path or index_entry_path != loaded_index_path:
            raise SatRootError("publication registry release catalog index paths do not match nested publication")
        if release_catalog_component.get("release_catalog_index_manifest_hash") != "sha256:" + sha256_hex_bytes(loaded_manifest_path.read_bytes()):
            raise SatRootError("publication registry release_catalog_index_manifest_hash mismatch")
        if release_catalog_component.get("release_catalog_index_hash") != "sha256:" + sha256_hex_bytes(loaded_index_path.read_bytes()):
            raise SatRootError("publication registry release_catalog_index_hash mismatch")
        if release_catalog_component.get("signature_scheme") != loaded_manifest.get("signature_scheme"):
            raise SatRootError("publication registry release catalog index signature_scheme mismatch")
        if release_catalog_component.get("signature_key_id") != loaded_manifest.get("signature_key_id"):
            raise SatRootError("publication registry release catalog index signature_key_id mismatch")
        if release_catalog_component.get("release_catalog_count") != loaded_index.get("release_catalog_count"):
            raise SatRootError("publication registry release catalog index release_catalog_count mismatch")

    descriptor_component = registry.get("publication_descriptor_index_publication")
    if isinstance(descriptor_component, Mapping):
        publication_dir = (registry_path.parent / str(descriptor_component.get("publication_directory_path"))).resolve()
        manifest_entry_path = (registry_path.parent / str(descriptor_component.get("publication_descriptor_index_manifest_path"))).resolve()
        index_entry_path = (registry_path.parent / str(descriptor_component.get("publication_descriptor_index_json_path"))).resolve()
        loaded_manifest_path, loaded_index_path, loaded_manifest, loaded_index = _load_publication_descriptor_index_publication(publication_dir)
        if manifest_entry_path != loaded_manifest_path or index_entry_path != loaded_index_path:
            raise SatRootError("publication registry publication descriptor index paths do not match nested publication")
        if descriptor_component.get("publication_descriptor_index_manifest_hash") != "sha256:" + sha256_hex_bytes(loaded_manifest_path.read_bytes()):
            raise SatRootError("publication registry publication_descriptor_index_manifest_hash mismatch")
        if descriptor_component.get("publication_descriptor_index_hash") != "sha256:" + sha256_hex_bytes(loaded_index_path.read_bytes()):
            raise SatRootError("publication registry publication_descriptor_index_hash mismatch")
        if descriptor_component.get("signature_scheme") != loaded_manifest.get("signature_scheme"):
            raise SatRootError("publication registry publication descriptor index signature_scheme mismatch")
        if descriptor_component.get("signature_key_id") != loaded_manifest.get("signature_key_id"):
            raise SatRootError("publication registry publication descriptor index signature_key_id mismatch")
        if descriptor_component.get("artifact_count") != loaded_index.get("artifact_count"):
            raise SatRootError("publication registry publication descriptor index artifact_count mismatch")

    metadata_component = registry.get("publication_metadata_catalog_publication")
    if isinstance(metadata_component, Mapping):
        publication_dir = (registry_path.parent / str(metadata_component.get("publication_directory_path"))).resolve()
        manifest_entry_path = (registry_path.parent / str(metadata_component.get("publication_metadata_catalog_manifest_path"))).resolve()
        catalog_entry_path = (registry_path.parent / str(metadata_component.get("publication_metadata_catalog_json_path"))).resolve()
        loaded_manifest_path, loaded_catalog_path, loaded_manifest, loaded_catalog = _load_publication_metadata_catalog_publication(publication_dir)
        if manifest_entry_path != loaded_manifest_path or catalog_entry_path != loaded_catalog_path:
            raise SatRootError("publication registry publication metadata catalog paths do not match nested publication")
        if metadata_component.get("publication_metadata_catalog_manifest_hash") != "sha256:" + sha256_hex_bytes(loaded_manifest_path.read_bytes()):
            raise SatRootError("publication registry publication_metadata_catalog_manifest_hash mismatch")
        if metadata_component.get("publication_metadata_catalog_hash") != "sha256:" + sha256_hex_bytes(loaded_catalog_path.read_bytes()):
            raise SatRootError("publication registry publication_metadata_catalog_hash mismatch")
        if metadata_component.get("signature_scheme") != loaded_manifest.get("signature_scheme"):
            raise SatRootError("publication registry publication metadata catalog signature_scheme mismatch")
        if metadata_component.get("signature_key_id") != loaded_manifest.get("signature_key_id"):
            raise SatRootError("publication registry publication metadata catalog signature_key_id mismatch")
        if metadata_component.get("bundle_count") != loaded_catalog.get("bundle_count"):
            raise SatRootError("publication registry publication metadata catalog bundle_count mismatch")

    if not verifier(manifest, publication_registry_manifest_signing_payload(manifest)):
        raise SatRootError("publication registry manifest signature verification failed")

    return {
        "signature_scheme": manifest.get("signature_scheme"),
        "signature_key_id": manifest.get("signature_key_id"),
        "publication_registry_path": registry_ref,
        "publication_registry_hash": actual_registry_hash,
        "component_count": registry.get("component_count"),
        "index": copy.deepcopy(registry.get("index")),
    }


def bootstrap_publication_registry_publication(
    *,
    output_dir: str | Path,
    signature_scheme: str,
    key_id: str,
    release_catalog_index_dir: Optional[str | Path] = None,
    publication_descriptor_index_dir: Optional[str | Path] = None,
    publication_metadata_catalog_dir: Optional[str | Path] = None,
    registry_metadata: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    if signature_scheme == "hmac-sha256":
        material = bootstrap_release_hmac_material([key_id])
        signer = make_hmac_sha256_signer(material["shared_secrets"])
        _write_json_file(output_path / "publication_registry_secrets.json", material["shared_secrets"])
    elif signature_scheme == "ed25519":
        material = bootstrap_release_ed25519_material([key_id])
        signer = make_ed25519_signer(material["private_keys"])
        _write_json_file(output_path / "publication_registry_private_keys.json", material["private_keys"])
        _write_json_file(output_path / "publication_registry_public_keys.json", material["public_keys"])
    else:
        raise SatRootError(f"unsupported publication registry signature scheme: {signature_scheme}")

    registry = build_publication_registry(
        release_catalog_index_dir=release_catalog_index_dir,
        publication_descriptor_index_dir=publication_descriptor_index_dir,
        publication_metadata_catalog_dir=publication_metadata_catalog_dir,
        base_dir=output_path,
        registry_metadata=registry_metadata,
    )
    registry_path = output_path / "publication_registry.json"
    _write_json_file(registry_path, registry)

    registry_manifest = build_signed_publication_registry_manifest(
        registry_path,
        signature_scheme=signature_scheme,
        key_id=key_id,
        signer=signer,
        base_dir=output_path,
    )
    registry_manifest_path = output_path / "publication_registry_manifest.json"
    _write_json_file(registry_manifest_path, registry_manifest)

    return {
        "publication_registry": registry,
        "publication_registry_path": str(registry_path),
        "publication_registry_manifest": registry_manifest,
        "publication_registry_manifest_path": str(registry_manifest_path),
        "publication_registry_material": material,
    }


def render_satroot_artifact_report(path: str | Path) -> str:
    kind, artifact_path = _detect_satroot_artifact_kind(path)
    lines: list[str] = []

    if kind == "bundle":
        summary = summarize_signed_ledger_bundle(artifact_path)
        snapshot = summary.get("final_state_snapshot")
        assert isinstance(snapshot, dict)
        lines.extend(
            [
                "# SATROOT Bundle Report",
                "",
                f"- Path: `{artifact_path}`",
                f"- Scheme: `{summary.get('scheme')}`",
                f"- Symbol: `{summary.get('symbol')}`",
                f"- Profile: `{snapshot.get('profile')}`",
                f"- Record count: `{summary.get('record_count')}`",
                f"- Root ID: `{summary.get('root_id')}`",
                f"- Verification material scope: `{summary.get('verification_material_scope')}`",
                "",
            ]
        )
        return "\n".join(lines)

    if kind == "release":
        summary = summarize_signed_release_publication(artifact_path)
        release_metadata = summary.get("release")
        lines.extend(
            [
                "# SATROOT Release Report",
                "",
                f"- Path: `{artifact_path}`",
                f"- Signature scheme: `{summary.get('signature_scheme')}`",
                f"- Signature key ID: `{summary.get('signature_key_id')}`",
                f"- Bundle count: `{summary.get('bundle_count')}`",
            ]
        )
        if isinstance(release_metadata, Mapping):
            _append_metadata_lines(lines, release_metadata, [("channel", "Channel"), ("label", "Label"), ("published_at", "Published at")])
        bundle_symbols = summary.get("bundle_symbols")
        if isinstance(bundle_symbols, list):
            lines.extend(["", "## Bundles", ""])
            lines.extend(f"- `{symbol}`" for symbol in bundle_symbols if isinstance(symbol, str))
        lines.append("")
        return "\n".join(lines)

    if kind == "release-catalog":
        summary = summarize_signed_release_catalog_publication(artifact_path)
        catalog_metadata = summary.get("catalog")
        lines.extend(
            [
                "# SATROOT Release Catalog Report",
                "",
                f"- Path: `{artifact_path}`",
                f"- Signature scheme: `{summary.get('signature_scheme')}`",
                f"- Signature key ID: `{summary.get('signature_key_id')}`",
                f"- Release count: `{summary.get('release_count')}`",
            ]
        )
        if isinstance(catalog_metadata, Mapping):
            _append_metadata_lines(lines, catalog_metadata, [("channel", "Channel"), ("label", "Label"), ("published_at", "Published at")])
        releases = summary.get("releases")
        if isinstance(releases, list):
            lines.extend(["", "## Releases", ""])
            for entry in releases:
                if not isinstance(entry, Mapping):
                    continue
                release_metadata = entry.get("release")
                label = None
                channel = None
                if isinstance(release_metadata, Mapping):
                    label = release_metadata.get("label")
                    channel = release_metadata.get("channel")
                release_path = entry.get("release_path")
                parts = [f"path `{release_path}`"] if isinstance(release_path, str) else []
                if isinstance(label, str) and label.strip():
                    parts.append(f"label `{label}`")
                if isinstance(channel, str) and channel.strip():
                    parts.append(f"channel `{channel}`")
                lines.append(f"- {', '.join(parts) if parts else 'release'}")
        lines.append("")
        return "\n".join(lines)

    if kind == "release-catalog-index":
        summary = summarize_signed_release_catalog_index_publication(artifact_path)
        index_metadata = summary.get("index")
        lines.extend(
            [
                "# SATROOT Release Catalog Index Report",
                "",
                f"- Path: `{artifact_path}`",
                f"- Signature scheme: `{summary.get('signature_scheme')}`",
                f"- Signature key ID: `{summary.get('signature_key_id')}`",
                f"- Release catalog count: `{summary.get('release_catalog_count')}`",
            ]
        )
        if isinstance(index_metadata, Mapping):
            _append_metadata_lines(lines, index_metadata, [("channel", "Channel"), ("label", "Label"), ("published_at", "Published at")])
        release_catalogs = summary.get("release_catalogs")
        if isinstance(release_catalogs, list):
            lines.extend(["", "## Release Catalogs", ""])
            for entry in release_catalogs:
                if not isinstance(entry, Mapping):
                    continue
                catalog_metadata = entry.get("catalog")
                label = None
                channel = None
                if isinstance(catalog_metadata, Mapping):
                    label = catalog_metadata.get("label")
                    channel = catalog_metadata.get("channel")
                release_catalog_path = entry.get("release_catalog_path")
                parts = [f"path `{release_catalog_path}`"] if isinstance(release_catalog_path, str) else []
                if isinstance(label, str) and label.strip():
                    parts.append(f"label `{label}`")
                if isinstance(channel, str) and channel.strip():
                    parts.append(f"channel `{channel}`")
                lines.append(f"- {', '.join(parts) if parts else 'release catalog'}")
        lines.append("")
        return "\n".join(lines)

    if kind == "demo-catalog":
        summary = summarize_demo_catalog_workspace(artifact_path)
        release_metadata = summary.get("release")
        lines.extend(
            [
                "# SATROOT Demo Catalog Report",
                "",
                f"- Path: `{artifact_path}`",
                f"- Bundle scheme: `{summary.get('bundle_scheme')}`",
                f"- Release scheme: `{summary.get('release_scheme')}`",
                f"- Bundle count: `{summary.get('bundle_count')}`",
            ]
        )
        if isinstance(release_metadata, Mapping):
            _append_metadata_lines(lines, release_metadata, [("channel", "Channel"), ("label", "Label"), ("published_at", "Published at")])
        bundles = summary.get("bundles")
        if isinstance(bundles, list):
            lines.extend(["", "## Bundles", ""])
            for entry in bundles:
                if not isinstance(entry, Mapping):
                    continue
                lines.append(
                    f"- `{entry.get('bundle_name')}`: profile `{entry.get('profile')}`, symbol `{entry.get('symbol')}`, name `{entry.get('name')}`"
                )
        lines.append("")
        return "\n".join(lines)

    if kind == "publication-stack":
        summary = summarize_publication_stack_workspace(artifact_path)
        release_catalog_summary = summary.get("release_catalog_summary")
        lines.extend(
            [
                "# SATROOT Publication Stack Report",
                "",
                f"- Path: `{artifact_path}`",
                f"- Bundle scheme: `{summary.get('bundle_scheme')}`",
                f"- Release scheme: `{summary.get('release_scheme')}`",
                f"- Release catalog scheme: `{summary.get('release_catalog_scheme')}`",
                f"- Workspace count: `{summary.get('workspace_count')}`",
            ]
        )
        if isinstance(release_catalog_summary, Mapping):
            catalog_metadata = release_catalog_summary.get("catalog")
            if isinstance(catalog_metadata, Mapping):
                _append_metadata_lines(lines, catalog_metadata, [("channel", "Channel"), ("label", "Label"), ("published_at", "Published at")])
        workspaces = summary.get("workspaces")
        if isinstance(workspaces, list):
            lines.extend(["", "## Catalog Workspaces", ""])
            for entry in workspaces:
                if not isinstance(entry, Mapping):
                    continue
                lines.append(
                    f"- `{entry.get('workspace_name')}`: bundles `{entry.get('bundle_count')}`, release manifest `{entry.get('release_manifest_path')}`"
                )
        lines.append("")
        return "\n".join(lines)

    if kind == "publication-network":
        summary = summarize_publication_network_workspace(artifact_path)
        release_catalog_index_summary = summary.get("release_catalog_index_summary")
        lines.extend(
            [
                "# SATROOT Publication Network Report",
                "",
                f"- Path: `{artifact_path}`",
                f"- Bundle scheme: `{summary.get('bundle_scheme')}`",
                f"- Release scheme: `{summary.get('release_scheme')}`",
                f"- Release catalog scheme: `{summary.get('release_catalog_scheme')}`",
                f"- Release catalog index scheme: `{summary.get('release_catalog_index_scheme')}`",
                f"- Stack count: `{summary.get('stack_count')}`",
            ]
        )
        if isinstance(release_catalog_index_summary, Mapping):
            index_metadata = release_catalog_index_summary.get("index")
            if isinstance(index_metadata, Mapping):
                _append_metadata_lines(lines, index_metadata, [("channel", "Channel"), ("label", "Label"), ("published_at", "Published at")])
        workspaces = summary.get("workspaces")
        if isinstance(workspaces, list):
            lines.extend(["", "## Stack Workspaces", ""])
            for entry in workspaces:
                if not isinstance(entry, Mapping):
                    continue
                lines.append(
                    f"- `{entry.get('workspace_name')}`: catalog workspaces `{entry.get('catalog_workspace_count')}`, release catalog manifest `{entry.get('release_catalog_manifest_path')}`"
                )
        lines.append("")
        return "\n".join(lines)

    if kind == "publication-registry-workspace":
        summary = summarize_publication_registry_workspace(artifact_path)
        publication_registry_summary = summary.get("publication_registry_summary")
        lines.extend(
            [
                "# SATROOT Publication Registry Workspace Report",
                "",
                f"- Path: `{artifact_path}`",
                f"- Signature scheme: `{summary.get('signature_scheme')}`",
                f"- Artifact count: `{summary.get('artifact_count')}`",
                f"- Publication metadata bundle count: `{summary.get('publication_metadata_bundle_count')}`",
            ]
        )
        if isinstance(publication_registry_summary, Mapping):
            index_metadata = publication_registry_summary.get("index")
            if isinstance(index_metadata, Mapping):
                _append_metadata_lines(lines, index_metadata, [("channel", "Channel"), ("label", "Label"), ("published_at", "Published at")])
        artifact_kinds = summary.get("publication_metadata_artifact_kinds")
        if isinstance(artifact_kinds, list):
            lines.extend(["", "## Artifact Kinds", ""])
            lines.extend(f"- `{kind}`" for kind in artifact_kinds if isinstance(kind, str))
        lines.extend(["", "## Component Lanes", ""])
        for label, component_summary, count_field in (
            ("Publication Network", summary.get("publication_network_summary"), "stack_count"),
            ("Release Catalog Index", summary.get("release_catalog_index_summary"), "release_catalog_count"),
            ("Publication Descriptor Index", summary.get("publication_descriptor_index_summary"), "artifact_count"),
            ("Publication Registry", publication_registry_summary, "component_count"),
        ):
            if not isinstance(component_summary, Mapping):
                continue
            index_metadata = component_summary.get("index")
            label_parts = [label]
            if isinstance(index_metadata, Mapping) and isinstance(index_metadata.get("label"), str) and index_metadata.get("label"):
                label_parts.append(f"label `{index_metadata.get('label')}`")
            component_count = component_summary.get(count_field)
            if isinstance(component_count, int):
                label_parts.append(f"count `{component_count}`")
            lines.append(f"- {', '.join(label_parts)}")
        lines.append("")
        return "\n".join(lines)

    if kind == "publication-registry":
        summary = summarize_publication_registry_publication(artifact_path)
        index_metadata = summary.get("index")
        lines.extend(
            [
                "# SATROOT Publication Registry Report",
                "",
                f"- Path: `{artifact_path}`",
                f"- Signature scheme: `{summary.get('signature_scheme')}`",
                f"- Signature key ID: `{summary.get('signature_key_id')}`",
                f"- Component count: `{summary.get('component_count')}`",
            ]
        )
        if isinstance(index_metadata, Mapping):
            _append_metadata_lines(lines, index_metadata, [("channel", "Channel"), ("label", "Label"), ("published_at", "Published at")])
        lines.extend(["", "## Components", ""])
        for component_name, label in (
            ("release_catalog_index_publication", "Release Catalog Index"),
            ("publication_descriptor_index_publication", "Publication Descriptor Index"),
            ("publication_metadata_catalog_publication", "Publication Metadata Catalog"),
        ):
            component = summary.get(component_name)
            if not isinstance(component, Mapping):
                continue
            publication_directory_path = component.get("publication_directory_path")
            signature_scheme = component.get("signature_scheme")
            signature_key_id = component.get("signature_key_id")
            lines.append(
                f"- {label}: path `{publication_directory_path}`, scheme `{signature_scheme}`, key `{signature_key_id}`"
            )
        lines.append("")
        return "\n".join(lines)

    raise SatRootError(f"unsupported SATROOT artifact kind: {kind}")


def validate_instance_against_schema(instance: Any, schema: Optional[Dict[str, Any]] = None) -> int:
    if schema is None:
        schema = load_protocol_schema()

    if importlib.util.find_spec("jsonschema") is None:
        raise SatRootError("jsonschema package is required for schema validation; install with `pip install -e .[validation]`")

    from jsonschema import validators as jsonschema_validators

    validator_class = getattr(jsonschema_validators, "Draft202012Validator", None)
    if validator_class is None:
        validator_class = jsonschema_validators.Draft7Validator
    validator = validator_class(schema)
    records = instance if isinstance(instance, list) else [instance]
    if not all(isinstance(record, dict) for record in records):
        raise SatRootError("schema validation expects a JSON object or an array of objects")

    for index, record in enumerate(records):
        errors = sorted(validator.iter_errors(record), key=lambda err: list(err.path))
        if errors:
            error = errors[0]
            location = "$" if not error.path else "$." + ".".join(str(part) for part in error.path)
            raise SatRootError(f"schema validation failed at record {index} {location}: {error.message}")

    return len(records)


def build_cli_parser() -> Any:
    import argparse

    parser = argparse.ArgumentParser(description="SATROOT-1 utilities")
    subparsers = parser.add_subparsers(dest="command")

    replay_parser = subparsers.add_parser("replay", help="Replay a SATROOT-1 JSON event file")
    replay_parser.add_argument("events_json", help="Path to JSON array of SATROOT-1 events")
    replay_parser.add_argument("--scheme", choices=["demo", "hmac-sha256", "ed25519"], default="demo")
    replay_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 replay")
    replay_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for replay")
    replay_parser.add_argument("--private-keys-json", help="Optional path to JSON mapping key_id -> Ed25519 private key hex for replay")

    validate_parser = subparsers.add_parser("validate", help="Validate SATROOT-1 JSON against the protocol schema")
    validate_parser.add_argument("input_json", help="Path to a JSON object or array of SATROOT-1 records")
    validate_parser.add_argument("--schema-json", help="Optional path to a JSON Schema file")

    validate_bundle_manifest_parser = subparsers.add_parser("validate-bundle-manifest", help="Validate a SATROOT-1 signed bundle manifest against the bundle-manifest schema")
    validate_bundle_manifest_parser.add_argument("bundle_manifest_json", help="Path to bundle_manifest.json")
    validate_bundle_manifest_parser.add_argument("--schema-json", help="Optional path to a bundle-manifest JSON Schema file")

    validate_bundle_index_parser = subparsers.add_parser("validate-bundle-index", help="Validate a SATROOT-1 bundle index against the bundle-index schema")
    validate_bundle_index_parser.add_argument("bundle_index_json", help="Path to bundle-index.json")
    validate_bundle_index_parser.add_argument("--schema-json", help="Optional path to a bundle-index JSON Schema file")

    validate_release_manifest_parser = subparsers.add_parser("validate-release-manifest", help="Validate a SATROOT-1 release manifest against the release-manifest schema")
    validate_release_manifest_parser.add_argument("release_manifest_json", help="Path to release-manifest.json")
    validate_release_manifest_parser.add_argument("--schema-json", help="Optional path to a release-manifest JSON Schema file")

    validate_release_catalog_parser = subparsers.add_parser("validate-release-catalog", help="Validate a SATROOT-1 release catalog against the release-catalog schema")
    validate_release_catalog_parser.add_argument("release_catalog_json", help="Path to release_catalog.json")
    validate_release_catalog_parser.add_argument("--schema-json", help="Optional path to a release-catalog JSON Schema file")

    validate_release_catalog_manifest_parser = subparsers.add_parser("validate-release-catalog-manifest", help="Validate a SATROOT-1 release catalog manifest against the release-catalog-manifest schema")
    validate_release_catalog_manifest_parser.add_argument("release_catalog_manifest_json", help="Path to release_catalog_manifest.json")
    validate_release_catalog_manifest_parser.add_argument("--schema-json", help="Optional path to a release-catalog-manifest JSON Schema file")

    validate_release_catalog_index_parser = subparsers.add_parser("validate-release-catalog-index", help="Validate a SATROOT-1 release catalog index against the release-catalog-index schema")
    validate_release_catalog_index_parser.add_argument("release_catalog_index_json", help="Path to release_catalog_index.json")
    validate_release_catalog_index_parser.add_argument("--schema-json", help="Optional path to a release-catalog-index JSON Schema file")

    validate_release_catalog_index_manifest_parser = subparsers.add_parser("validate-release-catalog-index-manifest", help="Validate a SATROOT-1 release catalog index manifest against the release-catalog-index-manifest schema")
    validate_release_catalog_index_manifest_parser.add_argument("release_catalog_index_manifest_json", help="Path to release_catalog_index_manifest.json")
    validate_release_catalog_index_manifest_parser.add_argument("--schema-json", help="Optional path to a release-catalog-index-manifest JSON Schema file")

    validate_demo_catalog_summary_parser = subparsers.add_parser("validate-demo-catalog-summary", help="Validate a SATROOT demo catalog summary against the demo-catalog-summary schema")
    validate_demo_catalog_summary_parser.add_argument("demo_catalog_summary_json", help="Path to demo catalog summary.json")
    validate_demo_catalog_summary_parser.add_argument("--schema-json", help="Optional path to a demo-catalog-summary JSON Schema file")

    validate_publication_stack_summary_parser = subparsers.add_parser("validate-publication-stack-summary", help="Validate a SATROOT publication stack summary against the publication-stack-summary schema")
    validate_publication_stack_summary_parser.add_argument("publication_stack_summary_json", help="Path to publication stack summary.json")
    validate_publication_stack_summary_parser.add_argument("--schema-json", help="Optional path to a publication-stack-summary JSON Schema file")

    validate_publication_network_summary_parser = subparsers.add_parser("validate-publication-network-summary", help="Validate a SATROOT publication network summary against the publication-network-summary schema")
    validate_publication_network_summary_parser.add_argument("publication_network_summary_json", help="Path to publication network summary.json")
    validate_publication_network_summary_parser.add_argument("--schema-json", help="Optional path to a publication-network-summary JSON Schema file")

    validate_publication_descriptor_index_parser = subparsers.add_parser("validate-publication-descriptor-index", help="Validate a SATROOT publication descriptor index against the publication-descriptor-index schema")
    validate_publication_descriptor_index_parser.add_argument("publication_descriptor_index_json", help="Path to publication_descriptor_index.json")
    validate_publication_descriptor_index_parser.add_argument("--schema-json", help="Optional path to a publication-descriptor-index JSON Schema file")

    validate_publication_descriptor_index_manifest_parser = subparsers.add_parser("validate-publication-descriptor-index-manifest", help="Validate a SATROOT publication descriptor index manifest against the publication-descriptor-index-manifest schema")
    validate_publication_descriptor_index_manifest_parser.add_argument("publication_descriptor_index_manifest_json", help="Path to publication_descriptor_index_manifest.json")
    validate_publication_descriptor_index_manifest_parser.add_argument("--schema-json", help="Optional path to a publication-descriptor-index-manifest JSON Schema file")

    validate_publication_metadata_manifest_parser = subparsers.add_parser("validate-publication-metadata-manifest", help="Validate a SATROOT publication metadata manifest against the publication-metadata-manifest schema")
    validate_publication_metadata_manifest_parser.add_argument("publication_metadata_manifest_json", help="Path to publication_metadata_manifest.json")
    validate_publication_metadata_manifest_parser.add_argument("--schema-json", help="Optional path to a publication-metadata-manifest JSON Schema file")

    validate_publication_metadata_catalog_parser = subparsers.add_parser("validate-publication-metadata-catalog", help="Validate a SATROOT publication metadata catalog against the publication-metadata-catalog schema")
    validate_publication_metadata_catalog_parser.add_argument("publication_metadata_catalog_json", help="Path to publication_metadata_catalog.json")
    validate_publication_metadata_catalog_parser.add_argument("--schema-json", help="Optional path to a publication-metadata-catalog JSON Schema file")

    validate_publication_metadata_catalog_manifest_parser = subparsers.add_parser("validate-publication-metadata-catalog-manifest", help="Validate a SATROOT publication metadata catalog manifest against the publication-metadata-catalog-manifest schema")
    validate_publication_metadata_catalog_manifest_parser.add_argument("publication_metadata_catalog_manifest_json", help="Path to publication_metadata_catalog_manifest.json")
    validate_publication_metadata_catalog_manifest_parser.add_argument("--schema-json", help="Optional path to a publication-metadata-catalog-manifest JSON Schema file")

    validate_publication_registry_parser = subparsers.add_parser("validate-publication-registry", help="Validate a SATROOT publication registry against the publication-registry schema")
    validate_publication_registry_parser.add_argument("publication_registry_json", help="Path to publication_registry.json")
    validate_publication_registry_parser.add_argument("--schema-json", help="Optional path to a publication-registry JSON Schema file")

    validate_publication_registry_manifest_parser = subparsers.add_parser("validate-publication-registry-manifest", help="Validate a SATROOT publication registry manifest against the publication-registry-manifest schema")
    validate_publication_registry_manifest_parser.add_argument("publication_registry_manifest_json", help="Path to publication_registry_manifest.json")
    validate_publication_registry_manifest_parser.add_argument("--schema-json", help="Optional path to a publication-registry-manifest JSON Schema file")

    init_genesis_parser = subparsers.add_parser("init-genesis", help="Scaffold a SATROOT-1 genesis record with optional profile-aware defaults")
    init_genesis_parser.add_argument("--symbol", required=True, help="Asset symbol for the genesis record")
    init_genesis_parser.add_argument("--name", required=True, help="Human-readable asset name for the genesis record")
    init_genesis_parser.add_argument("--root-id", help="Optional explicit root_id; defaults to a generated placeholder root")
    init_genesis_parser.add_argument("--mint-authority", default="issuer", help="Mint authority account name")
    init_genesis_parser.add_argument("--initial-owner", help="Initial holder account name; defaults to the mint authority")
    init_genesis_parser.add_argument("--decimals", type=int, help="Optional explicit decimals override")
    init_genesis_parser.add_argument("--max-supply", help="Optional explicit max_supply override")
    init_genesis_parser.add_argument("--initial-balance", help="Optional explicit initial issued balance override")
    init_genesis_parser.add_argument("--profile", choices=sorted(load_profile_registry()), help="Optional SATROOT profile to scaffold")
    init_genesis_parser.add_argument("--profile-field", action="append", dest="profile_fields", help="Profile field override in key=value form; may be repeated")
    init_genesis_parser.add_argument("--rules-hash", help="Optional rules_hash metadata")
    init_genesis_parser.add_argument("--nonce", help="Optional nonce metadata")
    init_genesis_parser.add_argument("--output", help="Optional output path")

    bootstrap_stable_demo_parser = subparsers.add_parser("bootstrap-stable-demo", help="Generate a reference-only SATROOT-STABLE-1 demo ledger plus annotated artifacts")
    bootstrap_stable_demo_parser.add_argument("--symbol", required=True, help="Asset symbol for the stable reference demo")
    bootstrap_stable_demo_parser.add_argument("--name", required=True, help="Human-readable asset name for the stable reference demo")
    bootstrap_stable_demo_parser.add_argument("--output-dir", required=True, help="Directory where events.json, annotated_events.json, and summary.json will be written")
    bootstrap_stable_demo_parser.add_argument("--reference-unit", default="USD", help="External reference unit; defaults to USD")
    bootstrap_stable_demo_parser.add_argument("--root-id", help="Optional explicit root_id; defaults to a generated placeholder root")
    bootstrap_stable_demo_parser.add_argument("--issuer", default="issuer", help="Issuer account name for genesis and distribution events")
    bootstrap_stable_demo_parser.add_argument("--merchant-account", default="merchant", help="Merchant account for the first reference distribution leg")
    bootstrap_stable_demo_parser.add_argument("--service-account", default="api_node", help="Service account for the second reference distribution leg")
    bootstrap_stable_demo_parser.add_argument("--initial-balance", default="25000000", help="Initial issued balance allocated to the issuer")
    bootstrap_stable_demo_parser.add_argument("--merchant-amount", default="1250000", help="Amount transferred from the issuer to the merchant account")
    bootstrap_stable_demo_parser.add_argument("--service-amount", default="250000", help="Amount transferred from the issuer to the service account")
    bootstrap_stable_demo_parser.add_argument("--merchant-burn-amount", default="5000", help="Optional merchant-side burn amount; use 0 to skip the burn event")
    bootstrap_stable_demo_parser.add_argument("--intended-use", default="invoice-credit-accounting", help="Reference-only intended_use metadata")
    bootstrap_stable_demo_parser.add_argument("--rules-hash", help="Optional rules_hash metadata")
    bootstrap_stable_demo_parser.add_argument("--nonce", help="Optional nonce metadata")
    bootstrap_stable_demo_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_events.json")

    bootstrap_machine_demo_parser = subparsers.add_parser("bootstrap-machine-demo", help="Generate a SATROOT-MACHINE-1 machine-credit demo ledger plus annotated artifacts")
    bootstrap_machine_demo_parser.add_argument("--symbol", required=True, help="Asset symbol for the machine-credit demo")
    bootstrap_machine_demo_parser.add_argument("--name", required=True, help="Human-readable asset name for the machine-credit demo")
    bootstrap_machine_demo_parser.add_argument("--output-dir", required=True, help="Directory where events.json, annotated_events.json, and summary.json will be written")
    bootstrap_machine_demo_parser.add_argument("--service-scope", default="api-compute", help="Compact machine service scope metadata")
    bootstrap_machine_demo_parser.add_argument("--billing-unit", default="request", help="Compact machine billing unit metadata")
    bootstrap_machine_demo_parser.add_argument("--consumption-model", default="burn-on-use", help="Compact machine consumption model metadata")
    bootstrap_machine_demo_parser.add_argument("--root-id", help="Optional explicit root_id; defaults to a generated placeholder root")
    bootstrap_machine_demo_parser.add_argument("--issuer", default="issuer", help="Issuer account name for genesis and tenant allocation events")
    bootstrap_machine_demo_parser.add_argument("--tenant-account", default="tenant_a", help="Tenant account receiving the primary machine-credit allocation")
    bootstrap_machine_demo_parser.add_argument("--worker-account", default="worker_node", help="Machine worker account receiving consumable execution credits")
    bootstrap_machine_demo_parser.add_argument("--max-supply", help="Optional explicit max_supply override; defaults to the initial issued balance")
    bootstrap_machine_demo_parser.add_argument("--initial-balance", default="100000000", help="Initial issued balance allocated to the issuer")
    bootstrap_machine_demo_parser.add_argument("--tenant-amount", default="5000000", help="Amount transferred from the issuer to the tenant account")
    bootstrap_machine_demo_parser.add_argument("--worker-amount", default="1200000", help="Amount transferred from the tenant account to the worker account")
    bootstrap_machine_demo_parser.add_argument("--worker-burn-amount", default="200000", help="Optional worker-side burn amount; use 0 to skip the burn event")
    bootstrap_machine_demo_parser.add_argument("--intended-use", default="machine-api-credit", help="Compact machine intended_use metadata")
    bootstrap_machine_demo_parser.add_argument("--rules-hash", help="Optional rules_hash metadata")
    bootstrap_machine_demo_parser.add_argument("--nonce", help="Optional nonce metadata")
    bootstrap_machine_demo_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_events.json")

    bootstrap_singleton_demo_parser = subparsers.add_parser("bootstrap-singleton-demo", help="Generate a receipt, identity, or license singleton demo ledger plus annotated artifacts")
    bootstrap_singleton_demo_parser.add_argument("--profile", required=True, choices=sorted(SINGLETON_DEMO_PROFILE_DEFAULTS), help="Singleton SATROOT profile to scaffold")
    bootstrap_singleton_demo_parser.add_argument("--symbol", required=True, help="Asset symbol for the singleton demo")
    bootstrap_singleton_demo_parser.add_argument("--name", required=True, help="Human-readable asset name for the singleton demo")
    bootstrap_singleton_demo_parser.add_argument("--output-dir", required=True, help="Directory where events.json, annotated_events.json, and summary.json will be written")
    bootstrap_singleton_demo_parser.add_argument("--root-id", help="Optional explicit root_id; defaults to a generated placeholder root")
    bootstrap_singleton_demo_parser.add_argument("--issuer", default="issuer", help="Issuer account name for genesis and lifecycle events")
    bootstrap_singleton_demo_parser.add_argument("--holder-account", help="Initial non-issuer holder; defaults to the profile demo preset")
    bootstrap_singleton_demo_parser.add_argument("--next-holder", help="Optional intermediate reassignment target before archival or retirement")
    bootstrap_singleton_demo_parser.add_argument("--archive-account", help="Optional archive destination; defaults to the profile demo preset when present")
    bootstrap_singleton_demo_parser.add_argument("--no-archive", action="store_true", help="Skip the archive transfer step even if the profile preset defines one")
    bootstrap_singleton_demo_parser.add_argument("--no-retire", action="store_true", help="Skip the final burn retirement step")
    bootstrap_singleton_demo_parser.add_argument("--profile-field", action="append", dest="profile_fields", help="Profile field override in key=value form; may be repeated")
    bootstrap_singleton_demo_parser.add_argument("--rules-hash", help="Optional rules_hash metadata")
    bootstrap_singleton_demo_parser.add_argument("--nonce", help="Optional nonce metadata")
    bootstrap_singleton_demo_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_events.json")

    bootstrap_singleton_demo_bundle_parser = subparsers.add_parser("bootstrap-singleton-demo-bundle", help="Generate a signed receipt, identity, or license singleton demo bundle from profile parameters")
    bootstrap_singleton_demo_bundle_parser.add_argument("--profile", required=True, choices=sorted(SINGLETON_DEMO_PROFILE_DEFAULTS), help="Singleton SATROOT profile to scaffold")
    bootstrap_singleton_demo_bundle_parser.add_argument("--symbol", required=True, help="Asset symbol for the singleton demo bundle")
    bootstrap_singleton_demo_bundle_parser.add_argument("--name", required=True, help="Human-readable asset name for the singleton demo bundle")
    bootstrap_singleton_demo_bundle_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_singleton_demo_bundle_parser.add_argument("--output-dir", required=True, help="Directory where signed bundle files will be written")
    bootstrap_singleton_demo_bundle_parser.add_argument("--root-id", help="Optional explicit root_id; defaults to a generated placeholder root")
    bootstrap_singleton_demo_bundle_parser.add_argument("--issuer", default="issuer", help="Issuer account name for genesis and lifecycle events")
    bootstrap_singleton_demo_bundle_parser.add_argument("--holder-account", help="Initial non-issuer holder; defaults to the profile demo preset")
    bootstrap_singleton_demo_bundle_parser.add_argument("--next-holder", help="Optional intermediate reassignment target before archival or retirement")
    bootstrap_singleton_demo_bundle_parser.add_argument("--archive-account", help="Optional archive destination; defaults to the profile demo preset when present")
    bootstrap_singleton_demo_bundle_parser.add_argument("--no-archive", action="store_true", help="Skip the archive transfer step even if the profile preset defines one")
    bootstrap_singleton_demo_bundle_parser.add_argument("--no-retire", action="store_true", help="Skip the final burn retirement step")
    bootstrap_singleton_demo_bundle_parser.add_argument("--profile-field", action="append", dest="profile_fields", help="Profile field override in key=value form; may be repeated")
    bootstrap_singleton_demo_bundle_parser.add_argument("--rules-hash", help="Optional rules_hash metadata")
    bootstrap_singleton_demo_bundle_parser.add_argument("--nonce", help="Optional nonce metadata")
    bootstrap_singleton_demo_bundle_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated key IDs")
    bootstrap_singleton_demo_bundle_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated key IDs")
    bootstrap_singleton_demo_bundle_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash during signing")
    bootstrap_singleton_demo_bundle_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_signed_events.json")
    bootstrap_singleton_demo_bundle_parser.add_argument("--verifier-only", action="store_true", help="For ed25519 bundles, omit private_keys.json and emit verifier-only material")

    bootstrap_singleton_demo_release_parser = subparsers.add_parser("bootstrap-singleton-demo-release", help="Generate a signed receipt, identity, or license singleton demo bundle plus signed release directory from profile parameters")
    bootstrap_singleton_demo_release_parser.add_argument("--profile", required=True, choices=sorted(SINGLETON_DEMO_PROFILE_DEFAULTS), help="Singleton SATROOT profile to scaffold")
    bootstrap_singleton_demo_release_parser.add_argument("--symbol", required=True, help="Asset symbol for the singleton demo release")
    bootstrap_singleton_demo_release_parser.add_argument("--name", required=True, help="Human-readable asset name for the singleton demo release")
    bootstrap_singleton_demo_release_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True, help="Signing scheme for the singleton demo bundle")
    bootstrap_singleton_demo_release_parser.add_argument("--release-scheme", choices=["hmac-sha256", "ed25519"], help="Optional override for release-manifest signing; defaults to --scheme")
    bootstrap_singleton_demo_release_parser.add_argument("--release-key-id", required=True, help="Signature key identifier to generate and use for the release manifest")
    bootstrap_singleton_demo_release_parser.add_argument("--output-dir", required=True, help="Directory where bundle/ and release/ outputs will be written")
    bootstrap_singleton_demo_release_parser.add_argument("--root-id", help="Optional explicit root_id; defaults to a generated placeholder root")
    bootstrap_singleton_demo_release_parser.add_argument("--issuer", default="issuer", help="Issuer account name for genesis and lifecycle events")
    bootstrap_singleton_demo_release_parser.add_argument("--holder-account", help="Initial non-issuer holder; defaults to the profile demo preset")
    bootstrap_singleton_demo_release_parser.add_argument("--next-holder", help="Optional intermediate reassignment target before archival or retirement")
    bootstrap_singleton_demo_release_parser.add_argument("--archive-account", help="Optional archive destination; defaults to the profile demo preset when present")
    bootstrap_singleton_demo_release_parser.add_argument("--no-archive", action="store_true", help="Skip the archive transfer step even if the profile preset defines one")
    bootstrap_singleton_demo_release_parser.add_argument("--no-retire", action="store_true", help="Skip the final burn retirement step")
    bootstrap_singleton_demo_release_parser.add_argument("--profile-field", action="append", dest="profile_fields", help="Profile field override in key=value form; may be repeated")
    bootstrap_singleton_demo_release_parser.add_argument("--rules-hash", help="Optional rules_hash metadata")
    bootstrap_singleton_demo_release_parser.add_argument("--nonce", help="Optional nonce metadata")
    bootstrap_singleton_demo_release_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated key IDs")
    bootstrap_singleton_demo_release_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated key IDs")
    bootstrap_singleton_demo_release_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash during bundle signing")
    bootstrap_singleton_demo_release_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_signed_events.json")
    bootstrap_singleton_demo_release_parser.add_argument("--verifier-only", action="store_true", help="For ed25519 bundles, omit private_keys.json and emit verifier-only material")
    bootstrap_singleton_demo_release_parser.add_argument("--channel", help="Optional release channel metadata for the bundle index")
    bootstrap_singleton_demo_release_parser.add_argument("--label", help="Optional human-readable release label for the bundle index")
    bootstrap_singleton_demo_release_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the bundle index")

    bootstrap_stable_demo_bundle_parser = subparsers.add_parser("bootstrap-stable-demo-bundle", help="Generate a signed SATROOT-STABLE-1 reference-demo bundle from profile parameters")
    bootstrap_stable_demo_bundle_parser.add_argument("--symbol", required=True, help="Asset symbol for the stable reference demo bundle")
    bootstrap_stable_demo_bundle_parser.add_argument("--name", required=True, help="Human-readable asset name for the stable reference demo bundle")
    bootstrap_stable_demo_bundle_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_stable_demo_bundle_parser.add_argument("--output-dir", required=True, help="Directory where signed bundle files will be written")
    bootstrap_stable_demo_bundle_parser.add_argument("--reference-unit", default="USD", help="External reference unit; defaults to USD")
    bootstrap_stable_demo_bundle_parser.add_argument("--root-id", help="Optional explicit root_id; defaults to a generated placeholder root")
    bootstrap_stable_demo_bundle_parser.add_argument("--issuer", default="issuer", help="Issuer account name for genesis and distribution events")
    bootstrap_stable_demo_bundle_parser.add_argument("--merchant-account", default="merchant", help="Merchant account for the first reference distribution leg")
    bootstrap_stable_demo_bundle_parser.add_argument("--service-account", default="api_node", help="Service account for the second reference distribution leg")
    bootstrap_stable_demo_bundle_parser.add_argument("--initial-balance", default="25000000", help="Initial issued balance allocated to the issuer")
    bootstrap_stable_demo_bundle_parser.add_argument("--merchant-amount", default="1250000", help="Amount transferred from the issuer to the merchant account")
    bootstrap_stable_demo_bundle_parser.add_argument("--service-amount", default="250000", help="Amount transferred from the issuer to the service account")
    bootstrap_stable_demo_bundle_parser.add_argument("--merchant-burn-amount", default="5000", help="Optional merchant-side burn amount; use 0 to skip the burn event")
    bootstrap_stable_demo_bundle_parser.add_argument("--intended-use", default="invoice-credit-accounting", help="Reference-only intended_use metadata")
    bootstrap_stable_demo_bundle_parser.add_argument("--rules-hash", help="Optional rules_hash metadata")
    bootstrap_stable_demo_bundle_parser.add_argument("--nonce", help="Optional nonce metadata")
    bootstrap_stable_demo_bundle_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated key IDs")
    bootstrap_stable_demo_bundle_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated key IDs")
    bootstrap_stable_demo_bundle_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash during signing")
    bootstrap_stable_demo_bundle_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_signed_events.json")
    bootstrap_stable_demo_bundle_parser.add_argument("--verifier-only", action="store_true", help="For ed25519 bundles, omit private_keys.json and emit verifier-only material")

    bootstrap_stable_demo_release_parser = subparsers.add_parser("bootstrap-stable-demo-release", help="Generate a signed SATROOT-STABLE-1 demo bundle plus signed release directory from profile parameters")
    bootstrap_stable_demo_release_parser.add_argument("--symbol", required=True, help="Asset symbol for the stable reference demo release")
    bootstrap_stable_demo_release_parser.add_argument("--name", required=True, help="Human-readable asset name for the stable reference demo release")
    bootstrap_stable_demo_release_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True, help="Signing scheme for the stable demo bundle")
    bootstrap_stable_demo_release_parser.add_argument("--release-scheme", choices=["hmac-sha256", "ed25519"], help="Optional override for release-manifest signing; defaults to --scheme")
    bootstrap_stable_demo_release_parser.add_argument("--release-key-id", required=True, help="Signature key identifier to generate and use for the release manifest")
    bootstrap_stable_demo_release_parser.add_argument("--output-dir", required=True, help="Directory where bundle/ and release/ outputs will be written")
    bootstrap_stable_demo_release_parser.add_argument("--reference-unit", default="USD", help="External reference unit; defaults to USD")
    bootstrap_stable_demo_release_parser.add_argument("--root-id", help="Optional explicit root_id; defaults to a generated placeholder root")
    bootstrap_stable_demo_release_parser.add_argument("--issuer", default="issuer", help="Issuer account name for genesis and distribution events")
    bootstrap_stable_demo_release_parser.add_argument("--merchant-account", default="merchant", help="Merchant account for the first reference distribution leg")
    bootstrap_stable_demo_release_parser.add_argument("--service-account", default="api_node", help="Service account for the second reference distribution leg")
    bootstrap_stable_demo_release_parser.add_argument("--initial-balance", default="25000000", help="Initial issued balance allocated to the issuer")
    bootstrap_stable_demo_release_parser.add_argument("--merchant-amount", default="1250000", help="Amount transferred from the issuer to the merchant account")
    bootstrap_stable_demo_release_parser.add_argument("--service-amount", default="250000", help="Amount transferred from the issuer to the service account")
    bootstrap_stable_demo_release_parser.add_argument("--merchant-burn-amount", default="5000", help="Optional merchant-side burn amount; use 0 to skip the burn event")
    bootstrap_stable_demo_release_parser.add_argument("--intended-use", default="invoice-credit-accounting", help="Reference-only intended_use metadata")
    bootstrap_stable_demo_release_parser.add_argument("--rules-hash", help="Optional rules_hash metadata")
    bootstrap_stable_demo_release_parser.add_argument("--nonce", help="Optional nonce metadata")
    bootstrap_stable_demo_release_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated key IDs")
    bootstrap_stable_demo_release_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated key IDs")
    bootstrap_stable_demo_release_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash during bundle signing")
    bootstrap_stable_demo_release_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_signed_events.json")
    bootstrap_stable_demo_release_parser.add_argument("--verifier-only", action="store_true", help="For ed25519 bundles, omit private_keys.json and emit verifier-only material")
    bootstrap_stable_demo_release_parser.add_argument("--channel", help="Optional release channel metadata for the bundle index")
    bootstrap_stable_demo_release_parser.add_argument("--label", help="Optional human-readable release label for the bundle index")
    bootstrap_stable_demo_release_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the bundle index")

    bootstrap_machine_demo_bundle_parser = subparsers.add_parser("bootstrap-machine-demo-bundle", help="Generate a signed SATROOT-MACHINE-1 machine-credit demo bundle from profile parameters")
    bootstrap_machine_demo_bundle_parser.add_argument("--symbol", required=True, help="Asset symbol for the machine-credit demo bundle")
    bootstrap_machine_demo_bundle_parser.add_argument("--name", required=True, help="Human-readable asset name for the machine-credit demo bundle")
    bootstrap_machine_demo_bundle_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_machine_demo_bundle_parser.add_argument("--output-dir", required=True, help="Directory where signed bundle files will be written")
    bootstrap_machine_demo_bundle_parser.add_argument("--service-scope", default="api-compute", help="Compact machine service scope metadata")
    bootstrap_machine_demo_bundle_parser.add_argument("--billing-unit", default="request", help="Compact machine billing unit metadata")
    bootstrap_machine_demo_bundle_parser.add_argument("--consumption-model", default="burn-on-use", help="Compact machine consumption model metadata")
    bootstrap_machine_demo_bundle_parser.add_argument("--root-id", help="Optional explicit root_id; defaults to a generated placeholder root")
    bootstrap_machine_demo_bundle_parser.add_argument("--issuer", default="issuer", help="Issuer account name for genesis and tenant allocation events")
    bootstrap_machine_demo_bundle_parser.add_argument("--tenant-account", default="tenant_a", help="Tenant account receiving the primary machine-credit allocation")
    bootstrap_machine_demo_bundle_parser.add_argument("--worker-account", default="worker_node", help="Machine worker account receiving consumable execution credits")
    bootstrap_machine_demo_bundle_parser.add_argument("--max-supply", help="Optional explicit max_supply override; defaults to the initial issued balance")
    bootstrap_machine_demo_bundle_parser.add_argument("--initial-balance", default="100000000", help="Initial issued balance allocated to the issuer")
    bootstrap_machine_demo_bundle_parser.add_argument("--tenant-amount", default="5000000", help="Amount transferred from the issuer to the tenant account")
    bootstrap_machine_demo_bundle_parser.add_argument("--worker-amount", default="1200000", help="Amount transferred from the tenant account to the worker account")
    bootstrap_machine_demo_bundle_parser.add_argument("--worker-burn-amount", default="200000", help="Optional worker-side burn amount; use 0 to skip the burn event")
    bootstrap_machine_demo_bundle_parser.add_argument("--intended-use", default="machine-api-credit", help="Compact machine intended_use metadata")
    bootstrap_machine_demo_bundle_parser.add_argument("--rules-hash", help="Optional rules_hash metadata")
    bootstrap_machine_demo_bundle_parser.add_argument("--nonce", help="Optional nonce metadata")
    bootstrap_machine_demo_bundle_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated key IDs")
    bootstrap_machine_demo_bundle_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated key IDs")
    bootstrap_machine_demo_bundle_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash during signing")
    bootstrap_machine_demo_bundle_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_signed_events.json")
    bootstrap_machine_demo_bundle_parser.add_argument("--verifier-only", action="store_true", help="For ed25519 bundles, omit private_keys.json and emit verifier-only material")

    bootstrap_machine_demo_release_parser = subparsers.add_parser("bootstrap-machine-demo-release", help="Generate a signed SATROOT-MACHINE-1 machine-credit demo bundle plus signed release directory from profile parameters")
    bootstrap_machine_demo_release_parser.add_argument("--symbol", required=True, help="Asset symbol for the machine-credit demo release")
    bootstrap_machine_demo_release_parser.add_argument("--name", required=True, help="Human-readable asset name for the machine-credit demo release")
    bootstrap_machine_demo_release_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True, help="Signing scheme for the machine-credit demo bundle")
    bootstrap_machine_demo_release_parser.add_argument("--release-scheme", choices=["hmac-sha256", "ed25519"], help="Optional override for release-manifest signing; defaults to --scheme")
    bootstrap_machine_demo_release_parser.add_argument("--release-key-id", required=True, help="Signature key identifier to generate and use for the release manifest")
    bootstrap_machine_demo_release_parser.add_argument("--output-dir", required=True, help="Directory where bundle/ and release/ outputs will be written")
    bootstrap_machine_demo_release_parser.add_argument("--service-scope", default="api-compute", help="Compact machine service scope metadata")
    bootstrap_machine_demo_release_parser.add_argument("--billing-unit", default="request", help="Compact machine billing unit metadata")
    bootstrap_machine_demo_release_parser.add_argument("--consumption-model", default="burn-on-use", help="Compact machine consumption model metadata")
    bootstrap_machine_demo_release_parser.add_argument("--root-id", help="Optional explicit root_id; defaults to a generated placeholder root")
    bootstrap_machine_demo_release_parser.add_argument("--issuer", default="issuer", help="Issuer account name for genesis and tenant allocation events")
    bootstrap_machine_demo_release_parser.add_argument("--tenant-account", default="tenant_a", help="Tenant account receiving the primary machine-credit allocation")
    bootstrap_machine_demo_release_parser.add_argument("--worker-account", default="worker_node", help="Machine worker account receiving consumable execution credits")
    bootstrap_machine_demo_release_parser.add_argument("--max-supply", help="Optional explicit max_supply override; defaults to the initial issued balance")
    bootstrap_machine_demo_release_parser.add_argument("--initial-balance", default="100000000", help="Initial issued balance allocated to the issuer")
    bootstrap_machine_demo_release_parser.add_argument("--tenant-amount", default="5000000", help="Amount transferred from the issuer to the tenant account")
    bootstrap_machine_demo_release_parser.add_argument("--worker-amount", default="1200000", help="Amount transferred from the tenant account to the worker account")
    bootstrap_machine_demo_release_parser.add_argument("--worker-burn-amount", default="200000", help="Optional worker-side burn amount; use 0 to skip the burn event")
    bootstrap_machine_demo_release_parser.add_argument("--intended-use", default="machine-api-credit", help="Compact machine intended_use metadata")
    bootstrap_machine_demo_release_parser.add_argument("--rules-hash", help="Optional rules_hash metadata")
    bootstrap_machine_demo_release_parser.add_argument("--nonce", help="Optional nonce metadata")
    bootstrap_machine_demo_release_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated key IDs")
    bootstrap_machine_demo_release_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated key IDs")
    bootstrap_machine_demo_release_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash during bundle signing")
    bootstrap_machine_demo_release_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_signed_events.json")
    bootstrap_machine_demo_release_parser.add_argument("--verifier-only", action="store_true", help="For ed25519 bundles, omit private_keys.json and emit verifier-only material")
    bootstrap_machine_demo_release_parser.add_argument("--channel", help="Optional release channel metadata for the bundle index")
    bootstrap_machine_demo_release_parser.add_argument("--label", help="Optional human-readable release label for the bundle index")
    bootstrap_machine_demo_release_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the bundle index")

    bootstrap_demo_catalog_parser = subparsers.add_parser("bootstrap-demo-catalog", help="Generate stable, machine, and singleton demo bundles plus a signed catalog release workspace")
    bootstrap_demo_catalog_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True, help="Signing scheme for the generated demo bundles")
    bootstrap_demo_catalog_parser.add_argument("--release-scheme", choices=["hmac-sha256", "ed25519"], help="Optional override for release-manifest signing; defaults to --scheme")
    bootstrap_demo_catalog_parser.add_argument("--release-key-id", required=True, help="Signature key identifier to generate and use for the catalog release manifest")
    bootstrap_demo_catalog_parser.add_argument("--output-dir", required=True, help="Directory where bundles/, release/, and summary.json will be written")
    bootstrap_demo_catalog_parser.add_argument("--preset-json", help="Optional SATROOT demo catalog preset JSON file with profiles, overrides, and release metadata defaults")
    bootstrap_demo_catalog_parser.add_argument("--profile", action="append", choices=sorted(DEMO_CATALOG_PROFILES), help="Limit the workspace to selected demo catalog profiles; may be repeated")
    bootstrap_demo_catalog_parser.add_argument("--symbol-override", action="append", dest="symbol_overrides", help="Per-profile symbol override in PROFILE=SYMBOL form; may be repeated")
    bootstrap_demo_catalog_parser.add_argument("--name-override", action="append", dest="name_overrides", help="Per-profile name override in PROFILE=NAME form; may be repeated")
    bootstrap_demo_catalog_parser.add_argument("--profile-field-override", action="append", dest="profile_field_overrides", help="Per-profile metadata override in PROFILE:field=value form; may be repeated")
    bootstrap_demo_catalog_parser.add_argument("--profile-structure-override", action="append", dest="profile_structure_overrides", help="Per-profile structural override in PROFILE:key=value form; use none/null for optional singleton accounts")
    bootstrap_demo_catalog_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated bundle key IDs")
    bootstrap_demo_catalog_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated bundle key IDs")
    bootstrap_demo_catalog_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash during bundle signing")
    bootstrap_demo_catalog_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_signed_events.json inside bundle directories")
    bootstrap_demo_catalog_parser.add_argument("--verifier-only", action="store_true", help="For ed25519 bundles, omit private_keys.json inside bundle directories")
    bootstrap_demo_catalog_parser.add_argument("--channel", help="Optional release channel metadata for the catalog bundle index")
    bootstrap_demo_catalog_parser.add_argument("--label", help="Optional human-readable release label for the catalog bundle index")
    bootstrap_demo_catalog_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the catalog bundle index")

    bootstrap_publication_stack_parser = subparsers.add_parser("bootstrap-publication-stack", help="Generate one or more demo catalog workspaces from presets and publish them as a signed release catalog stack")
    bootstrap_publication_stack_parser.add_argument("--stack-preset-json", help="Optional SATROOT publication stack preset JSON file with catalog preset paths and release-catalog metadata defaults")
    bootstrap_publication_stack_parser.add_argument("--catalog-preset-json", action="append", dest="catalog_preset_jsons", help="SATROOT demo catalog preset JSON file; may be repeated")
    bootstrap_publication_stack_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True, help="Signing scheme for generated demo bundles")
    bootstrap_publication_stack_parser.add_argument("--release-scheme", choices=["hmac-sha256", "ed25519"], help="Optional override for per-workspace release-manifest signing; defaults to --scheme")
    bootstrap_publication_stack_parser.add_argument("--release-key-id", required=True, help="Signature key identifier to generate and use for each workspace release manifest")
    bootstrap_publication_stack_parser.add_argument("--release-catalog-preset-json", help="Optional SATROOT release catalog preset JSON file for top-level catalog metadata defaults")
    bootstrap_publication_stack_parser.add_argument("--release-catalog-scheme", choices=["hmac-sha256", "ed25519"], help="Optional override for release-catalog-manifest signing; defaults to --scheme")
    bootstrap_publication_stack_parser.add_argument("--release-catalog-key-id", required=True, help="Signature key identifier to generate and use for the top-level release catalog manifest")
    bootstrap_publication_stack_parser.add_argument("--output-dir", required=True, help="Directory where catalog_workspaces/, release_catalog/, and summary.json will be written")
    bootstrap_publication_stack_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated bundle key IDs")
    bootstrap_publication_stack_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated bundle key IDs")
    bootstrap_publication_stack_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash during bundle signing")
    bootstrap_publication_stack_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_signed_events.json inside bundle directories")
    bootstrap_publication_stack_parser.add_argument("--verifier-only", action="store_true", help="For ed25519 bundles, omit private_keys.json inside bundle directories")
    bootstrap_publication_stack_parser.add_argument("--channel", help="Optional release catalog channel metadata override")
    bootstrap_publication_stack_parser.add_argument("--label", help="Optional human-readable release catalog label override")
    bootstrap_publication_stack_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata override")

    bootstrap_publication_network_parser = subparsers.add_parser("bootstrap-publication-network", help="Generate one or more publication stacks from presets and publish them as a signed release-catalog index")
    bootstrap_publication_network_parser.add_argument("--network-preset-json", help="Optional SATROOT publication network preset JSON file with stack preset paths and release-catalog-index metadata defaults")
    bootstrap_publication_network_parser.add_argument("--stack-preset-json", action="append", dest="stack_preset_jsons", help="SATROOT publication stack preset JSON file; may be repeated")
    bootstrap_publication_network_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True, help="Signing scheme for generated demo bundles")
    bootstrap_publication_network_parser.add_argument("--release-scheme", choices=["hmac-sha256", "ed25519"], help="Optional override for per-workspace release-manifest signing; defaults to --scheme")
    bootstrap_publication_network_parser.add_argument("--release-key-id", required=True, help="Signature key identifier to generate and use for each workspace release manifest")
    bootstrap_publication_network_parser.add_argument("--release-catalog-scheme", choices=["hmac-sha256", "ed25519"], help="Optional override for per-stack release-catalog-manifest signing; defaults to --scheme")
    bootstrap_publication_network_parser.add_argument("--release-catalog-key-id", required=True, help="Signature key identifier to generate and use for each stack release catalog manifest")
    bootstrap_publication_network_parser.add_argument("--release-catalog-index-preset-json", help="Optional SATROOT release catalog index preset JSON file for top-level index metadata defaults")
    bootstrap_publication_network_parser.add_argument("--release-catalog-index-scheme", choices=["hmac-sha256", "ed25519"], help="Optional override for release-catalog-index-manifest signing; defaults to --scheme")
    bootstrap_publication_network_parser.add_argument("--release-catalog-index-key-id", required=True, help="Signature key identifier to generate and use for the top-level release catalog index manifest")
    bootstrap_publication_network_parser.add_argument("--output-dir", required=True, help="Directory where stack_workspaces/, release_catalog_index/, and summary.json will be written")
    bootstrap_publication_network_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated bundle key IDs")
    bootstrap_publication_network_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated bundle key IDs")
    bootstrap_publication_network_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash during bundle signing")
    bootstrap_publication_network_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_signed_events.json inside bundle directories")
    bootstrap_publication_network_parser.add_argument("--verifier-only", action="store_true", help="For ed25519 bundles, omit private_keys.json inside bundle directories")
    bootstrap_publication_network_parser.add_argument("--channel", help="Optional release catalog index channel metadata override")
    bootstrap_publication_network_parser.add_argument("--label", help="Optional human-readable release catalog index label override")
    bootstrap_publication_network_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata override")

    bootstrap_publication_registry_workspace_parser = subparsers.add_parser("bootstrap-publication-registry-workspace", help="Copy a release-catalog-index publication, derive descriptor and metadata publication lanes, and emit a full signed SATROOT publication registry workspace")
    bootstrap_publication_registry_workspace_parser.add_argument("--preset-json", help="Optional SATROOT publication registry workspace preset JSON file with artifact paths, discovery roots, source publication references, and metadata defaults")
    bootstrap_publication_registry_workspace_parser.add_argument("path", nargs="*", help="Path to a SATROOT artifact file or directory to include in the descriptor and metadata lanes")
    bootstrap_publication_registry_workspace_parser.add_argument("--publication-network-dir", help="Optional publication network workspace directory to use as a default discovery root and release-catalog-index source")
    bootstrap_publication_registry_workspace_parser.add_argument("--release-catalog-index-dir", help="Optional release catalog index publication directory; defaults to <publication-network-dir>/release_catalog_index when --publication-network-dir is provided")
    bootstrap_publication_registry_workspace_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested SATROOT artifacts; may be repeated")
    bootstrap_publication_registry_workspace_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each discovery root")
    bootstrap_publication_registry_workspace_parser.add_argument("--descriptor-index-channel", help="Optional descriptor-index channel metadata")
    bootstrap_publication_registry_workspace_parser.add_argument("--descriptor-index-label", help="Optional human-readable descriptor-index label")
    bootstrap_publication_registry_workspace_parser.add_argument("--descriptor-index-published-at", help="Optional descriptor-index published_at metadata")
    bootstrap_publication_registry_workspace_parser.add_argument("--publication-metadata-catalog-channel", help="Optional publication-metadata-catalog channel metadata")
    bootstrap_publication_registry_workspace_parser.add_argument("--publication-metadata-catalog-label", help="Optional human-readable publication-metadata-catalog label")
    bootstrap_publication_registry_workspace_parser.add_argument("--publication-metadata-catalog-published-at", help="Optional publication-metadata-catalog published_at metadata")
    bootstrap_publication_registry_workspace_parser.add_argument("--publication-registry-channel", help="Optional publication-registry channel metadata")
    bootstrap_publication_registry_workspace_parser.add_argument("--publication-registry-label", help="Optional human-readable publication-registry label")
    bootstrap_publication_registry_workspace_parser.add_argument("--publication-registry-published-at", help="Optional publication-registry published_at metadata")
    bootstrap_publication_registry_workspace_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True, help="Signing scheme for generated descriptor, metadata, and registry publications")
    bootstrap_publication_registry_workspace_parser.add_argument("--publication-descriptor-index-key-id", required=True, help="Signature key identifier to generate and use for the publication descriptor index manifest")
    bootstrap_publication_registry_workspace_parser.add_argument("--publication-metadata-key-id", required=True, help="Signature key identifier to generate and use for each publication metadata manifest")
    bootstrap_publication_registry_workspace_parser.add_argument("--publication-metadata-catalog-key-id", required=True, help="Signature key identifier to generate and use for the publication metadata catalog manifest")
    bootstrap_publication_registry_workspace_parser.add_argument("--publication-registry-key-id", required=True, help="Signature key identifier to generate and use for the publication registry manifest")
    bootstrap_publication_registry_workspace_parser.add_argument("--output-dir", required=True, help="Directory where a copied publication_network/ or release_catalog_index/ plus publication_descriptor_index/, publication_metadata_bundles/, publication_metadata_catalog/, publication_registry/, and summary.json will be written")

    publish_publication_stack_parser = subparsers.add_parser("publish-publication-stack", help="Copy existing demo catalog workspaces into one SATROOT publication stack and publish a signed release catalog")
    publish_publication_stack_parser.add_argument("catalog_workspace_dir", nargs="*", help="Path to an existing SATROOT demo catalog workspace directory")
    publish_publication_stack_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested demo catalog workspaces; may be repeated")
    publish_publication_stack_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each --discover-under directory")
    publish_publication_stack_parser.add_argument("--output-dir", required=True, help="Directory where copied catalog workspaces, release_catalog/, and summary.json will be written")
    publish_publication_stack_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True, help="Signing scheme for the generated release-catalog manifest")
    publish_publication_stack_parser.add_argument("--release-catalog-key-id", required=True, help="Signature key identifier to generate and use for the top-level release catalog manifest")
    publish_publication_stack_parser.add_argument("--channel", help="Optional release catalog channel metadata")
    publish_publication_stack_parser.add_argument("--label", help="Optional human-readable release catalog label metadata")
    publish_publication_stack_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata")

    publish_publication_network_parser = subparsers.add_parser("publish-publication-network", help="Copy existing publication stack workspaces into one SATROOT publication network and publish a signed release-catalog index")
    publish_publication_network_parser.add_argument("publication_stack_dir", nargs="*", help="Path to an existing SATROOT publication stack workspace directory")
    publish_publication_network_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested publication stack workspaces; may be repeated")
    publish_publication_network_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each --discover-under directory")
    publish_publication_network_parser.add_argument("--output-dir", required=True, help="Directory where copied stack workspaces, release_catalog_index/, and summary.json will be written")
    publish_publication_network_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True, help="Signing scheme for the generated release-catalog-index manifest")
    publish_publication_network_parser.add_argument("--release-catalog-index-key-id", required=True, help="Signature key identifier to generate and use for the top-level release catalog index manifest")
    publish_publication_network_parser.add_argument("--channel", help="Optional release catalog index channel metadata")
    publish_publication_network_parser.add_argument("--label", help="Optional human-readable release catalog index label metadata")
    publish_publication_network_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata")

    inventory_artifacts_parser = subparsers.add_parser("inventory-artifacts", help="Scan one or more directories and summarize discovered SATROOT artifacts and workspaces")
    inventory_artifacts_parser.add_argument("search_root", nargs="*", help="Directory root to scan for SATROOT artifacts")
    inventory_artifacts_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Additional directory root to scan for SATROOT artifacts; may be repeated")
    inventory_artifacts_parser.add_argument("--non-recursive", action="store_true", help="Do not descend into nested directories while scanning")

    export_demo_catalog_preset_parser = subparsers.add_parser("export-demo-catalog-preset", help="Export a SATROOT demo catalog workspace back into a reusable demo catalog preset")
    export_demo_catalog_preset_parser.add_argument("demo_catalog_dir", help="Path to a SATROOT demo catalog workspace directory")
    export_demo_catalog_preset_parser.add_argument("--output", help="Optional output path")

    export_publication_stack_preset_parser = subparsers.add_parser("export-publication-stack-preset", help="Export a SATROOT publication stack workspace back into a reusable publication stack preset")
    export_publication_stack_preset_parser.add_argument("publication_stack_dir", help="Path to a SATROOT publication stack workspace directory")
    export_publication_stack_preset_parser.add_argument("--catalog-preset-dir", help="Optional directory where nested demo catalog presets will also be exported")
    export_publication_stack_preset_parser.add_argument("--output", help="Optional output path")

    export_publication_network_preset_parser = subparsers.add_parser("export-publication-network-preset", help="Export a SATROOT publication network workspace back into a reusable publication network preset")
    export_publication_network_preset_parser.add_argument("publication_network_dir", help="Path to a SATROOT publication network workspace directory")
    export_publication_network_preset_parser.add_argument("--stack-preset-dir", help="Optional directory where nested publication stack presets will also be exported")
    export_publication_network_preset_parser.add_argument("--catalog-preset-dir", help="Optional directory where nested demo catalog presets will also be exported alongside generated stack presets")
    export_publication_network_preset_parser.add_argument("--output", help="Optional output path")

    export_publication_registry_workspace_preset_parser = subparsers.add_parser("export-publication-registry-workspace-preset", help="Export a SATROOT publication registry workspace back into a reusable publication registry workspace preset")
    export_publication_registry_workspace_preset_parser.add_argument("publication_registry_workspace_dir", help="Path to a SATROOT publication registry workspace directory")
    export_publication_registry_workspace_preset_parser.add_argument("--output", help="Optional output path")

    export_publication_descriptor_index_preset_parser = subparsers.add_parser("export-publication-descriptor-index-preset", help="Export a SATROOT publication descriptor index back into a reusable publication descriptor index preset")
    export_publication_descriptor_index_preset_parser.add_argument("publication_descriptor_index_dir", help="Path to a SATROOT publication descriptor index directory")
    export_publication_descriptor_index_preset_parser.add_argument("--output", help="Optional output path")

    export_publication_metadata_catalog_preset_parser = subparsers.add_parser("export-publication-metadata-catalog-preset", help="Export a SATROOT publication metadata catalog back into a reusable publication metadata catalog preset")
    export_publication_metadata_catalog_preset_parser.add_argument("publication_metadata_catalog_dir", help="Path to a SATROOT publication metadata catalog directory")
    export_publication_metadata_catalog_preset_parser.add_argument("--output", help="Optional output path")

    export_publication_registry_preset_parser = subparsers.add_parser("export-publication-registry-preset", help="Export a SATROOT publication registry back into a reusable publication registry preset")
    export_publication_registry_preset_parser.add_argument("publication_registry_dir", help="Path to a SATROOT publication registry directory")
    export_publication_registry_preset_parser.add_argument("--output", help="Optional output path")

    render_publication_report_parser = subparsers.add_parser("render-publication-report", help="Render a human-readable markdown report for a SATROOT bundle, release, catalog, index, or workspace")
    render_publication_report_parser.add_argument("path", help="Path to a SATROOT artifact file or directory")
    render_publication_report_parser.add_argument("--output", help="Optional output path")

    export_publication_descriptor_parser = subparsers.add_parser("export-publication-descriptor", help="Export a normalized JSON descriptor for a SATROOT bundle, release, catalog, index, or workspace")
    export_publication_descriptor_parser.add_argument("path", help="Path to a SATROOT artifact file or directory")
    export_publication_descriptor_parser.add_argument("--output", help="Optional output path")

    build_publication_descriptor_index_parser = subparsers.add_parser("build-publication-descriptor-index", help="Build a machine-readable SATROOT publication descriptor index from explicit artifact paths and/or discovery roots")
    build_publication_descriptor_index_parser.add_argument("--preset-json", help="Optional SATROOT publication descriptor index preset JSON file with artifact paths, discovery roots, and index metadata defaults")
    build_publication_descriptor_index_parser.add_argument("path", nargs="*", help="Path to a SATROOT artifact file or directory")
    build_publication_descriptor_index_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested SATROOT artifacts; may be repeated")
    build_publication_descriptor_index_parser.add_argument("--non-recursive", action="store_true", help="Do not descend into nested directories while discovering artifacts")
    build_publication_descriptor_index_parser.add_argument("--channel", help="Optional descriptor-index channel metadata")
    build_publication_descriptor_index_parser.add_argument("--label", help="Optional human-readable descriptor-index label metadata")
    build_publication_descriptor_index_parser.add_argument("--published-at", help="Optional descriptor-index published_at metadata")
    build_publication_descriptor_index_parser.add_argument("--output", help="Optional output path")

    build_publication_descriptor_index_manifest_parser = subparsers.add_parser("build-publication-descriptor-index-manifest", help="Build a signed SATROOT publication descriptor index manifest from a descriptor index")
    build_publication_descriptor_index_manifest_parser.add_argument("publication_descriptor_index_json", help="Path to publication_descriptor_index.json")
    build_publication_descriptor_index_manifest_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    build_publication_descriptor_index_manifest_parser.add_argument("--key-id", required=True, help="Signature key identifier for the publication descriptor index manifest")
    build_publication_descriptor_index_manifest_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    build_publication_descriptor_index_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 publication-descriptor-index-manifest signing")
    build_publication_descriptor_index_manifest_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    build_publication_descriptor_index_manifest_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex for ed25519 publication-descriptor-index-manifest signing")
    build_publication_descriptor_index_manifest_parser.add_argument("--output", help="Optional output path")

    build_publication_metadata_manifest_parser = subparsers.add_parser("build-publication-metadata-manifest", help="Build a signed SATROOT publication metadata manifest from a report and descriptor pair")
    build_publication_metadata_manifest_parser.add_argument("publication_report_path", help="Path to publication_report.md")
    build_publication_metadata_manifest_parser.add_argument("publication_descriptor_json", help="Path to publication_descriptor.json")
    build_publication_metadata_manifest_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    build_publication_metadata_manifest_parser.add_argument("--key-id", required=True, help="Signature key identifier for the publication metadata manifest")
    build_publication_metadata_manifest_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    build_publication_metadata_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 publication-metadata-manifest signing")
    build_publication_metadata_manifest_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    build_publication_metadata_manifest_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex for ed25519 publication-metadata-manifest signing")
    build_publication_metadata_manifest_parser.add_argument("--output", help="Optional output path")

    build_publication_metadata_catalog_parser = subparsers.add_parser("build-publication-metadata-catalog", help="Build a SATROOT publication metadata catalog from one or more publication metadata bundle directories")
    build_publication_metadata_catalog_parser.add_argument("--preset-json", help="Optional SATROOT publication metadata catalog preset JSON file with bundle paths, discovery roots, and catalog metadata defaults")
    build_publication_metadata_catalog_parser.add_argument("publication_metadata_bundle_dir", nargs="*", help="Path to a publication metadata bundle directory")
    build_publication_metadata_catalog_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested publication_metadata_manifest.json files; may be repeated")
    build_publication_metadata_catalog_parser.add_argument("--non-recursive", action="store_true", help="Do not descend into nested directories while discovering publication metadata bundles")
    build_publication_metadata_catalog_parser.add_argument("--channel", help="Optional publication-metadata-catalog channel metadata")
    build_publication_metadata_catalog_parser.add_argument("--label", help="Optional human-readable publication metadata catalog label")
    build_publication_metadata_catalog_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the publication metadata catalog")
    build_publication_metadata_catalog_parser.add_argument("--output", help="Optional output path")

    build_publication_metadata_catalog_manifest_parser = subparsers.add_parser("build-publication-metadata-catalog-manifest", help="Build a signed SATROOT publication metadata catalog manifest from a publication metadata catalog")
    build_publication_metadata_catalog_manifest_parser.add_argument("publication_metadata_catalog_json", help="Path to publication_metadata_catalog.json")
    build_publication_metadata_catalog_manifest_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    build_publication_metadata_catalog_manifest_parser.add_argument("--key-id", required=True, help="Signature key identifier for the publication metadata catalog manifest")
    build_publication_metadata_catalog_manifest_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    build_publication_metadata_catalog_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 publication-metadata-catalog-manifest signing")
    build_publication_metadata_catalog_manifest_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    build_publication_metadata_catalog_manifest_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex for ed25519 publication-metadata-catalog-manifest signing")
    build_publication_metadata_catalog_manifest_parser.add_argument("--output", help="Optional output path")

    build_publication_registry_parser = subparsers.add_parser("build-publication-registry", help="Build a top-level SATROOT publication registry from existing published component directories")
    build_publication_registry_parser.add_argument("--preset-json", help="Optional SATROOT publication registry preset JSON file with component paths and registry metadata defaults")
    build_publication_registry_parser.add_argument("--release-catalog-index-dir", help="Path to a release catalog index publication directory")
    build_publication_registry_parser.add_argument("--publication-descriptor-index-dir", help="Path to a publication descriptor index publication directory")
    build_publication_registry_parser.add_argument("--publication-metadata-catalog-dir", help="Path to a publication metadata catalog publication directory")
    build_publication_registry_parser.add_argument("--channel", help="Optional publication-registry channel metadata")
    build_publication_registry_parser.add_argument("--label", help="Optional human-readable publication registry label")
    build_publication_registry_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the publication registry")
    build_publication_registry_parser.add_argument("--output", help="Optional output path")

    build_publication_registry_manifest_parser = subparsers.add_parser("build-publication-registry-manifest", help="Build a signed SATROOT publication registry manifest from a publication registry")
    build_publication_registry_manifest_parser.add_argument("publication_registry_json", help="Path to publication_registry.json")
    build_publication_registry_manifest_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    build_publication_registry_manifest_parser.add_argument("--key-id", required=True, help="Signature key identifier for the publication registry manifest")
    build_publication_registry_manifest_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    build_publication_registry_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 publication-registry-manifest signing")
    build_publication_registry_manifest_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    build_publication_registry_manifest_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex for ed25519 publication-registry-manifest signing")
    build_publication_registry_manifest_parser.add_argument("--output", help="Optional output path")

    bootstrap_publication_descriptor_index_publication_parser = subparsers.add_parser("bootstrap-publication-descriptor-index-publication", help="Generate signing material and write a ready-to-verify SATROOT publication descriptor index directory")
    bootstrap_publication_descriptor_index_publication_parser.add_argument("--preset-json", help="Optional SATROOT publication descriptor index preset JSON file with artifact paths, discovery roots, and index metadata defaults")
    bootstrap_publication_descriptor_index_publication_parser.add_argument("path", nargs="*", help="Path to a SATROOT artifact file or directory")
    bootstrap_publication_descriptor_index_publication_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested SATROOT artifacts; may be repeated")
    bootstrap_publication_descriptor_index_publication_parser.add_argument("--non-recursive", action="store_true", help="Do not descend into nested directories while discovering artifacts")
    bootstrap_publication_descriptor_index_publication_parser.add_argument("--output-dir", required=True, help="Directory where index material plus publication_descriptor_index.json and publication_descriptor_index_manifest.json will be written")
    bootstrap_publication_descriptor_index_publication_parser.add_argument("--channel", help="Optional descriptor-index channel metadata")
    bootstrap_publication_descriptor_index_publication_parser.add_argument("--label", help="Optional human-readable descriptor-index label")
    bootstrap_publication_descriptor_index_publication_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the descriptor index")
    bootstrap_publication_descriptor_index_publication_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_publication_descriptor_index_publication_parser.add_argument("--key-id", required=True, help="Signature key identifier to generate and use for the publication descriptor index manifest")

    bootstrap_publication_metadata_bundle_parser = subparsers.add_parser("bootstrap-publication-metadata-bundle", help="Generate signing material, a publication report, a publication descriptor, and a ready-to-verify publication metadata manifest")
    bootstrap_publication_metadata_bundle_parser.add_argument("path", help="Path to a SATROOT artifact file or directory")
    bootstrap_publication_metadata_bundle_parser.add_argument("--output-dir", required=True, help="Directory where publication_report.md, publication_descriptor.json, and publication_metadata_manifest.json will be written")
    bootstrap_publication_metadata_bundle_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_publication_metadata_bundle_parser.add_argument("--key-id", required=True, help="Signature key identifier to generate and use for the publication metadata manifest")

    bootstrap_publication_metadata_catalog_publication_parser = subparsers.add_parser("bootstrap-publication-metadata-catalog-publication", help="Generate signing material and write a ready-to-verify SATROOT publication metadata catalog directory")
    bootstrap_publication_metadata_catalog_publication_parser.add_argument("--preset-json", help="Optional SATROOT publication metadata catalog preset JSON file with bundle paths, discovery roots, and catalog metadata defaults")
    bootstrap_publication_metadata_catalog_publication_parser.add_argument("publication_metadata_bundle_dir", nargs="*", help="Path to a publication metadata bundle directory")
    bootstrap_publication_metadata_catalog_publication_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested publication_metadata_manifest.json files; may be repeated")
    bootstrap_publication_metadata_catalog_publication_parser.add_argument("--non-recursive", action="store_true", help="Do not descend into nested directories while discovering publication metadata bundles")
    bootstrap_publication_metadata_catalog_publication_parser.add_argument("--output-dir", required=True, help="Directory where publication_metadata_catalog.json and publication_metadata_catalog_manifest.json will be written")
    bootstrap_publication_metadata_catalog_publication_parser.add_argument("--channel", help="Optional publication-metadata-catalog channel metadata")
    bootstrap_publication_metadata_catalog_publication_parser.add_argument("--label", help="Optional human-readable publication metadata catalog label")
    bootstrap_publication_metadata_catalog_publication_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the publication metadata catalog")
    bootstrap_publication_metadata_catalog_publication_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_publication_metadata_catalog_publication_parser.add_argument("--key-id", required=True, help="Signature key identifier to generate and use for the publication metadata catalog manifest")

    bootstrap_publication_registry_publication_parser = subparsers.add_parser("bootstrap-publication-registry-publication", help="Generate signing material and write a ready-to-verify SATROOT publication registry directory")
    bootstrap_publication_registry_publication_parser.add_argument("--preset-json", help="Optional SATROOT publication registry preset JSON file with component paths and registry metadata defaults")
    bootstrap_publication_registry_publication_parser.add_argument("--release-catalog-index-dir", help="Path to a release catalog index publication directory")
    bootstrap_publication_registry_publication_parser.add_argument("--publication-descriptor-index-dir", help="Path to a publication descriptor index publication directory")
    bootstrap_publication_registry_publication_parser.add_argument("--publication-metadata-catalog-dir", help="Path to a publication metadata catalog publication directory")
    bootstrap_publication_registry_publication_parser.add_argument("--output-dir", required=True, help="Directory where publication_registry.json and publication_registry_manifest.json will be written")
    bootstrap_publication_registry_publication_parser.add_argument("--channel", help="Optional publication-registry channel metadata")
    bootstrap_publication_registry_publication_parser.add_argument("--label", help="Optional human-readable publication registry label")
    bootstrap_publication_registry_publication_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the publication registry")
    bootstrap_publication_registry_publication_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_publication_registry_publication_parser.add_argument("--key-id", required=True, help="Signature key identifier to generate and use for the publication registry manifest")

    init_event_parser = subparsers.add_parser("init-event", help="Scaffold a SATROOT-1 non-genesis event record")
    init_event_parser.add_argument("--action", choices=["mint", "transfer", "burn", "rotate-authority"], required=True)
    init_event_parser.add_argument("--events-json", help="Optional path to an existing SATROOT-1 ledger array; derives root_id, sequence, prev_event_id, and profile metadata")
    init_event_parser.add_argument("--root-id", help="Explicit root_id when not deriving from --events-json")
    init_event_parser.add_argument("--sequence", type=int, help="Explicit sequence when not deriving from --events-json")
    init_event_parser.add_argument("--prev-event-id", help="Explicit prev_event_id when not deriving from --events-json")
    init_event_parser.add_argument("--signer", required=True, help="Signer account name for the new event")
    init_event_parser.add_argument("--from", dest="from_account", help="Source account for transfer/burn actions")
    init_event_parser.add_argument("--to", dest="to_account", help="Destination account for mint/transfer actions")
    init_event_parser.add_argument("--amount", help="Positive amount for mint/transfer/burn actions")
    init_event_parser.add_argument("--new-mint-authority", help="New mint authority for rotate-authority actions")
    init_event_parser.add_argument("--output", help="Optional output path")

    append_event_parser = subparsers.add_parser("append-event", help="Append a scaffolded or supplied SATROOT-1 event to an existing ledger and optionally sign it")
    append_event_parser.add_argument("events_json", help="Path to an existing SATROOT-1 ledger array")
    append_event_parser.add_argument("--event-json", help="Optional path to an event object to append; otherwise scaffold from the ledger tip")
    append_event_parser.add_argument("--action", choices=["mint", "transfer", "burn", "rotate-authority"], help="Action to scaffold when --event-json is not provided")
    append_event_parser.add_argument("--signer", help="Signer account name for the appended event")
    append_event_parser.add_argument("--from", dest="from_account", help="Source account for transfer/burn actions")
    append_event_parser.add_argument("--to", dest="to_account", help="Destination account for mint/transfer actions")
    append_event_parser.add_argument("--amount", help="Positive amount for mint/transfer/burn actions")
    append_event_parser.add_argument("--new-mint-authority", help="New mint authority for rotate-authority actions")
    append_event_parser.add_argument("--scheme", choices=["demo", "hmac-sha256", "ed25519"], default="demo")
    append_event_parser.add_argument("--key-id", help="Explicit signature key identifier for non-demo event signing")
    append_event_parser.add_argument("--signer-key-map-json", help="Optional path to JSON mapping signer -> key_id for non-demo event signing")
    append_event_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification/signing")
    append_event_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    append_event_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> Ed25519 private key hex for signing")
    append_event_parser.add_argument("--include-state-hash", action="store_true", help="Attach state_hash to the appended event")
    append_event_parser.add_argument("--output", help="Optional output path")

    consume_machine_credit_parser = subparsers.add_parser("consume-machine-credit", help="Append a burn-on-use SATROOT-MACHINE-1 consumption event to an existing ledger")
    consume_machine_credit_parser.add_argument("events_json", help="Path to an existing SATROOT-MACHINE-1 ledger array")
    consume_machine_credit_parser.add_argument("--signer", required=True, help="Signer account name for the consumption event")
    consume_machine_credit_parser.add_argument("--amount", required=True, help="Positive machine-credit amount to consume")
    consume_machine_credit_parser.add_argument("--from", dest="from_account", help="Optional source account; defaults to the signer")
    consume_machine_credit_parser.add_argument("--scheme", choices=["demo", "hmac-sha256", "ed25519"], default="demo")
    consume_machine_credit_parser.add_argument("--key-id", help="Explicit signature key identifier for non-demo event signing")
    consume_machine_credit_parser.add_argument("--signer-key-map-json", help="Optional path to JSON mapping signer -> key_id for non-demo event signing")
    consume_machine_credit_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification/signing")
    consume_machine_credit_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    consume_machine_credit_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> Ed25519 private key hex for signing")
    consume_machine_credit_parser.add_argument("--include-state-hash", action="store_true", help="Attach state_hash to the appended event")
    consume_machine_credit_parser.add_argument("--output", help="Optional output path")

    transfer_singleton_object_parser = subparsers.add_parser("transfer-singleton-object", help="Append a profile-aware transfer for SATROOT receipt, identity, or license ledgers")
    transfer_singleton_object_parser.add_argument("events_json", help="Path to an existing SATROOT singleton-object ledger array")
    transfer_singleton_object_parser.add_argument("--signer", required=True, help="Signer account name for the singleton transfer")
    transfer_singleton_object_parser.add_argument("--to", dest="to_account", required=True, help="Destination account for the singleton transfer")
    transfer_singleton_object_parser.add_argument("--from", dest="from_account", help="Optional source account; defaults to the current active holder")
    transfer_singleton_object_parser.add_argument("--scheme", choices=["demo", "hmac-sha256", "ed25519"], default="demo")
    transfer_singleton_object_parser.add_argument("--key-id", help="Explicit signature key identifier for non-demo event signing")
    transfer_singleton_object_parser.add_argument("--signer-key-map-json", help="Optional path to JSON mapping signer -> key_id for non-demo event signing")
    transfer_singleton_object_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification/signing")
    transfer_singleton_object_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    transfer_singleton_object_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> Ed25519 private key hex for signing")
    transfer_singleton_object_parser.add_argument("--include-state-hash", action="store_true", help="Attach state_hash to the appended event")
    transfer_singleton_object_parser.add_argument("--output", help="Optional output path")

    archive_singleton_object_parser = subparsers.add_parser("archive-singleton-object", help="Append an archival transfer for SATROOT receipt, identity, or license ledgers")
    archive_singleton_object_parser.add_argument("events_json", help="Path to an existing SATROOT singleton-object ledger array")
    archive_singleton_object_parser.add_argument("--signer", required=True, help="Signer account name for the archival transfer")
    archive_singleton_object_parser.add_argument("--archive-account", default="archive", help="Archive account destination; defaults to archive")
    archive_singleton_object_parser.add_argument("--from", dest="from_account", help="Optional source account; defaults to the current active holder")
    archive_singleton_object_parser.add_argument("--scheme", choices=["demo", "hmac-sha256", "ed25519"], default="demo")
    archive_singleton_object_parser.add_argument("--key-id", help="Explicit signature key identifier for non-demo event signing")
    archive_singleton_object_parser.add_argument("--signer-key-map-json", help="Optional path to JSON mapping signer -> key_id for non-demo event signing")
    archive_singleton_object_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification/signing")
    archive_singleton_object_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    archive_singleton_object_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> Ed25519 private key hex for signing")
    archive_singleton_object_parser.add_argument("--include-state-hash", action="store_true", help="Attach state_hash to the appended event")
    archive_singleton_object_parser.add_argument("--output", help="Optional output path")

    retire_singleton_object_parser = subparsers.add_parser("retire-singleton-object", help="Append a burn retirement event for archived SATROOT receipt, identity, or license ledgers")
    retire_singleton_object_parser.add_argument("events_json", help="Path to an existing archived SATROOT singleton-object ledger array")
    retire_singleton_object_parser.add_argument("--signer", required=True, help="Signer account name for the retirement burn")
    retire_singleton_object_parser.add_argument("--from", dest="from_account", default="archive", help="Archived source account to retire from; defaults to archive")
    retire_singleton_object_parser.add_argument("--scheme", choices=["demo", "hmac-sha256", "ed25519"], default="demo")
    retire_singleton_object_parser.add_argument("--key-id", help="Explicit signature key identifier for non-demo event signing")
    retire_singleton_object_parser.add_argument("--signer-key-map-json", help="Optional path to JSON mapping signer -> key_id for non-demo event signing")
    retire_singleton_object_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification/signing")
    retire_singleton_object_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    retire_singleton_object_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> Ed25519 private key hex for signing")
    retire_singleton_object_parser.add_argument("--include-state-hash", action="store_true", help="Attach state_hash to the appended event")
    retire_singleton_object_parser.add_argument("--output", help="Optional output path")

    bootstrap_genesis_bundle_parser = subparsers.add_parser("bootstrap-genesis-bundle", help="Scaffold a genesis record and emit a signed SATROOT-1 starter bundle")
    bootstrap_genesis_bundle_parser.add_argument("--symbol", required=True, help="Asset symbol for the genesis record")
    bootstrap_genesis_bundle_parser.add_argument("--name", required=True, help="Human-readable asset name for the genesis record")
    bootstrap_genesis_bundle_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_genesis_bundle_parser.add_argument("--output-dir", required=True, help="Directory where starter bundle files will be written")
    bootstrap_genesis_bundle_parser.add_argument("--root-id", help="Optional explicit root_id; defaults to a generated placeholder root")
    bootstrap_genesis_bundle_parser.add_argument("--mint-authority", default="issuer", help="Mint authority account name")
    bootstrap_genesis_bundle_parser.add_argument("--initial-owner", help="Initial holder account name; defaults to the mint authority")
    bootstrap_genesis_bundle_parser.add_argument("--decimals", type=int, help="Optional explicit decimals override")
    bootstrap_genesis_bundle_parser.add_argument("--max-supply", help="Optional explicit max_supply override")
    bootstrap_genesis_bundle_parser.add_argument("--initial-balance", help="Optional explicit initial issued balance override")
    bootstrap_genesis_bundle_parser.add_argument("--profile", choices=sorted(load_profile_registry()), help="Optional SATROOT profile to scaffold")
    bootstrap_genesis_bundle_parser.add_argument("--profile-field", action="append", dest="profile_fields", help="Profile field override in key=value form; may be repeated")
    bootstrap_genesis_bundle_parser.add_argument("--rules-hash", help="Optional rules_hash metadata")
    bootstrap_genesis_bundle_parser.add_argument("--nonce", help="Optional nonce metadata")
    bootstrap_genesis_bundle_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated key IDs")
    bootstrap_genesis_bundle_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated key IDs")
    bootstrap_genesis_bundle_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash during annotation")
    bootstrap_genesis_bundle_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_signed_events.json")
    bootstrap_genesis_bundle_parser.add_argument("--verifier-only", action="store_true", help="For ed25519 bundles, omit private_keys.json and emit verifier-only material")

    signer_map_parser = subparsers.add_parser("init-signer-key-map", help="Build signer -> key_id mappings from a SATROOT-1 ledger")
    signer_map_parser.add_argument("events_json", help="Path to JSON array of SATROOT-1 events")
    signer_map_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated key IDs")
    signer_map_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated key IDs")
    signer_map_parser.add_argument("--output", help="Optional output path")

    generate_hmac_parser = subparsers.add_parser("generate-hmac-secrets", help="Generate HMAC shared-secret mappings")
    generate_hmac_parser.add_argument("--key-id", action="append", dest="key_ids", help="Key identifier to generate")
    generate_hmac_parser.add_argument("--signer-key-map-json", help="Optional path to JSON mapping signer -> key_id")
    generate_hmac_parser.add_argument("--output", help="Optional output path")

    bootstrap_hmac_parser = subparsers.add_parser("bootstrap-hmac-workflow", help="Generate signer map plus HMAC shared secrets for a SATROOT-1 ledger")
    bootstrap_hmac_parser.add_argument("events_json", help="Path to JSON array of SATROOT-1 events")
    bootstrap_hmac_parser.add_argument("--output-dir", required=True, help="Directory where signer_key_map.json and secrets.json will be written")
    bootstrap_hmac_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated key IDs")
    bootstrap_hmac_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated key IDs")

    bootstrap_release_hmac_parser = subparsers.add_parser("bootstrap-release-hmac", help="Generate HMAC shared-secret material for SATROOT release-manifest signing")
    bootstrap_release_hmac_parser.add_argument("--key-id", action="append", dest="key_ids", help="Release key identifier to generate")
    bootstrap_release_hmac_parser.add_argument("--output-dir", required=True, help="Directory where release_secrets.json will be written")

    bootstrap_signed_parser = subparsers.add_parser("bootstrap-signed-ledger", help="Bootstrap signing material and emit signed SATROOT-1 ledger artifacts")
    bootstrap_signed_parser.add_argument("events_json", help="Path to JSON array of SATROOT-1 events")
    bootstrap_signed_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_signed_parser.add_argument("--output-dir", required=True, help="Directory where workflow files and signed ledgers will be written")
    bootstrap_signed_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated key IDs")
    bootstrap_signed_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated key IDs")
    bootstrap_signed_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash during the signing step")
    bootstrap_signed_parser.add_argument("--no-annotated-output", action="store_true", help="Do not emit annotated_signed_events.json")
    bootstrap_signed_parser.add_argument("--verifier-only", action="store_true", help="For ed25519 bundles, omit private_keys.json and emit verifier-only material")

    bundle_summary_parser = subparsers.add_parser("bundle-summary", help="Read bundle_manifest.json and print a manifest-level bundle summary without replaying")
    bundle_summary_parser.add_argument("bundle_dir", help="Path to a signed SATROOT-1 bundle directory")

    bundle_lint_parser = subparsers.add_parser("bundle-lint", help="Check bundle_manifest.json plus bundle file layout without replaying")
    bundle_lint_parser.add_argument("bundle_dir", help="Path to a signed SATROOT-1 bundle directory")

    release_summary_parser = subparsers.add_parser("release-summary", help="Read release_manifest.json plus bundle_index.json and print a release-level summary without signature verification")
    release_summary_parser.add_argument("release_dir", help="Path to a SATROOT release directory")

    release_lint_parser = subparsers.add_parser("release-lint", help="Check release_manifest.json, bundle_index.json, and referenced bundle manifests without signature verification")
    release_lint_parser.add_argument("release_dir", help="Path to a SATROOT release directory")

    release_catalog_summary_parser = subparsers.add_parser("release-catalog-summary", help="Read release_catalog_manifest.json plus release_catalog.json and print a catalog-level summary without signature verification")
    release_catalog_summary_parser.add_argument("release_catalog_dir", help="Path to a SATROOT release catalog directory")

    release_catalog_lint_parser = subparsers.add_parser("release-catalog-lint", help="Check release_catalog_manifest.json, release_catalog.json, and referenced release publications without signature verification")
    release_catalog_lint_parser.add_argument("release_catalog_dir", help="Path to a SATROOT release catalog directory")

    release_catalog_index_summary_parser = subparsers.add_parser("release-catalog-index-summary", help="Read release_catalog_index_manifest.json plus release_catalog_index.json and print an index-level summary without signature verification")
    release_catalog_index_summary_parser.add_argument("release_catalog_index_dir", help="Path to a SATROOT release catalog index directory")

    release_catalog_index_lint_parser = subparsers.add_parser("release-catalog-index-lint", help="Check release_catalog_index_manifest.json, release_catalog_index.json, and referenced release catalog publications without signature verification")
    release_catalog_index_lint_parser.add_argument("release_catalog_index_dir", help="Path to a SATROOT release catalog index directory")

    publication_descriptor_index_summary_parser = subparsers.add_parser("publication-descriptor-index-summary", help="Read publication_descriptor_index_manifest.json plus publication_descriptor_index.json and print a descriptor-index summary without signature verification")
    publication_descriptor_index_summary_parser.add_argument("publication_descriptor_index_dir", help="Path to a SATROOT publication descriptor index directory")

    publication_descriptor_index_lint_parser = subparsers.add_parser("publication-descriptor-index-lint", help="Check publication_descriptor_index_manifest.json, publication_descriptor_index.json, and referenced SATROOT artifacts without signature verification")
    publication_descriptor_index_lint_parser.add_argument("publication_descriptor_index_dir", help="Path to a SATROOT publication descriptor index directory")

    demo_catalog_summary_parser = subparsers.add_parser("demo-catalog-summary", help="Read summary.json plus release/ and print a demo-catalog workspace summary without signature verification")
    demo_catalog_summary_parser.add_argument("demo_catalog_dir", help="Path to a SATROOT demo catalog workspace directory")

    demo_catalog_lint_parser = subparsers.add_parser("demo-catalog-lint", help="Check summary.json, release/, and referenced bundle directories without signature verification")
    demo_catalog_lint_parser.add_argument("demo_catalog_dir", help="Path to a SATROOT demo catalog workspace directory")

    publication_stack_summary_parser = subparsers.add_parser("publication-stack-summary", help="Read summary.json plus release_catalog/ and print a publication-stack summary without signature verification")
    publication_stack_summary_parser.add_argument("publication_stack_dir", help="Path to a SATROOT publication stack directory")

    publication_stack_lint_parser = subparsers.add_parser("publication-stack-lint", help="Check summary.json, release_catalog/, and referenced catalog workspace summaries without signature verification")
    publication_stack_lint_parser.add_argument("publication_stack_dir", help="Path to a SATROOT publication stack directory")

    publication_network_summary_parser = subparsers.add_parser("publication-network-summary", help="Read summary.json plus release_catalog_index/ and print a publication-network summary without signature verification")
    publication_network_summary_parser.add_argument("publication_network_dir", help="Path to a SATROOT publication network directory")

    publication_network_lint_parser = subparsers.add_parser("publication-network-lint", help="Check summary.json, release_catalog_index/, and referenced publication stack summaries without signature verification")
    publication_network_lint_parser.add_argument("publication_network_dir", help="Path to a SATROOT publication network directory")

    publication_registry_workspace_summary_parser = subparsers.add_parser("publication-registry-workspace-summary", help="Read summary.json plus copied/generated publication components and print a publication-registry workspace summary without signature verification")
    publication_registry_workspace_summary_parser.add_argument("publication_registry_workspace_dir", help="Path to a SATROOT publication registry workspace directory")

    publication_registry_workspace_lint_parser = subparsers.add_parser("publication-registry-workspace-lint", help="Check summary.json, copied/generated publication components, and referenced publication metadata bundles without signature verification")
    publication_registry_workspace_lint_parser.add_argument("publication_registry_workspace_dir", help="Path to a SATROOT publication registry workspace directory")

    publication_registry_summary_parser = subparsers.add_parser("publication-registry-summary", help="Read publication_registry_manifest.json plus publication_registry.json and print a publication-registry summary without signature verification")
    publication_registry_summary_parser.add_argument("publication_registry_dir", help="Path to a SATROOT publication registry directory")

    publication_registry_lint_parser = subparsers.add_parser("publication-registry-lint", help="Check publication_registry_manifest.json, publication_registry.json, and referenced publication components without signature verification")
    publication_registry_lint_parser.add_argument("publication_registry_dir", help="Path to a SATROOT publication registry directory")

    bundle_index_parser = subparsers.add_parser("build-bundle-index", help="Build a SATROOT-1 bundle index from one or more bundle directories")
    bundle_index_parser.add_argument("bundle_dir", nargs="*", help="Path to a signed SATROOT-1 bundle directory")
    bundle_index_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested bundle_manifest.json files; may be repeated")
    bundle_index_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each --discover-under directory")
    bundle_index_parser.add_argument("--channel", help="Optional release channel metadata for the bundle index")
    bundle_index_parser.add_argument("--label", help="Optional human-readable release label for the bundle index")
    bundle_index_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the bundle index")
    bundle_index_parser.add_argument("--output", help="Optional output path")

    release_manifest_parser = subparsers.add_parser("build-release-manifest", help="Build a signed SATROOT-1 release manifest from a bundle index")
    release_manifest_parser.add_argument("bundle_index_json", help="Path to bundle_index.json")
    release_manifest_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    release_manifest_parser.add_argument("--key-id", required=True, help="Signature key identifier for the release manifest")
    release_manifest_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    release_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 release-manifest signing")
    release_manifest_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    release_manifest_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex for ed25519 release-manifest signing")
    release_manifest_parser.add_argument("--output", help="Optional output path")

    publish_release_parser = subparsers.add_parser("publish-release", help="Build bundle_index.json plus release_manifest.json in one SATROOT-1 release directory")
    publish_release_parser.add_argument("bundle_dir", nargs="*", help="Path to a signed SATROOT-1 bundle directory")
    publish_release_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested bundle_manifest.json files; may be repeated")
    publish_release_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each --discover-under directory")
    publish_release_parser.add_argument("--output-dir", required=True, help="Directory where bundle_index.json and release_manifest.json will be written")
    publish_release_parser.add_argument("--channel", help="Optional release channel metadata for the bundle index")
    publish_release_parser.add_argument("--label", help="Optional human-readable release label for the bundle index")
    publish_release_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the bundle index")
    publish_release_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    publish_release_parser.add_argument("--key-id", required=True, help="Signature key identifier for the release manifest")
    publish_release_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    publish_release_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 release-manifest signing")
    publish_release_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    publish_release_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex for ed25519 release-manifest signing")

    bootstrap_release_publication_parser = subparsers.add_parser("bootstrap-release-publication", help="Generate release signing material and write a ready-to-verify SATROOT-1 release directory")
    bootstrap_release_publication_parser.add_argument("bundle_dir", nargs="*", help="Path to a signed SATROOT-1 bundle directory")
    bootstrap_release_publication_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested bundle_manifest.json files; may be repeated")
    bootstrap_release_publication_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each --discover-under directory")
    bootstrap_release_publication_parser.add_argument("--output-dir", required=True, help="Directory where release material plus bundle_index.json and release_manifest.json will be written")
    bootstrap_release_publication_parser.add_argument("--channel", help="Optional release channel metadata for the bundle index")
    bootstrap_release_publication_parser.add_argument("--label", help="Optional human-readable release label for the bundle index")
    bootstrap_release_publication_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the bundle index")
    bootstrap_release_publication_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_release_publication_parser.add_argument("--key-id", required=True, help="Signature key identifier to generate and use for the release manifest")

    release_catalog_parser = subparsers.add_parser("build-release-catalog", help="Build a SATROOT-1 release catalog from one or more signed release directories")
    release_catalog_parser.add_argument("release_dir", nargs="*", help="Path to a signed SATROOT-1 release directory")
    release_catalog_parser.add_argument("--preset-json", help="Optional SATROOT release catalog preset JSON file with release roots and catalog metadata defaults")
    release_catalog_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested release_manifest.json files; may be repeated")
    release_catalog_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each --discover-under directory")
    release_catalog_parser.add_argument("--channel", help="Optional catalog channel metadata")
    release_catalog_parser.add_argument("--label", help="Optional human-readable catalog label")
    release_catalog_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the release catalog")
    release_catalog_parser.add_argument("--output", help="Optional output path")

    release_catalog_manifest_parser = subparsers.add_parser("build-release-catalog-manifest", help="Build a signed SATROOT-1 release catalog manifest from a release catalog")
    release_catalog_manifest_parser.add_argument("release_catalog_json", help="Path to release_catalog.json")
    release_catalog_manifest_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    release_catalog_manifest_parser.add_argument("--key-id", required=True, help="Signature key identifier for the release catalog manifest")
    release_catalog_manifest_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    release_catalog_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 release-catalog-manifest signing")
    release_catalog_manifest_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    release_catalog_manifest_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex for ed25519 release-catalog-manifest signing")
    release_catalog_manifest_parser.add_argument("--output", help="Optional output path")

    release_catalog_index_parser = subparsers.add_parser("build-release-catalog-index", help="Build a SATROOT-1 release catalog index from one or more signed release catalog directories")
    release_catalog_index_parser.add_argument("release_catalog_dir", nargs="*", help="Path to a signed SATROOT-1 release catalog directory")
    release_catalog_index_parser.add_argument("--preset-json", help="Optional SATROOT release catalog index preset JSON file with release catalog roots and index metadata defaults")
    release_catalog_index_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested release_catalog_manifest.json files; may be repeated")
    release_catalog_index_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each --discover-under directory")
    release_catalog_index_parser.add_argument("--channel", help="Optional index channel metadata")
    release_catalog_index_parser.add_argument("--label", help="Optional human-readable index label")
    release_catalog_index_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the release catalog index")
    release_catalog_index_parser.add_argument("--output", help="Optional output path")

    release_catalog_index_manifest_parser = subparsers.add_parser("build-release-catalog-index-manifest", help="Build a signed SATROOT-1 release catalog index manifest from a release catalog index")
    release_catalog_index_manifest_parser.add_argument("release_catalog_index_json", help="Path to release_catalog_index.json")
    release_catalog_index_manifest_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    release_catalog_index_manifest_parser.add_argument("--key-id", required=True, help="Signature key identifier for the release catalog index manifest")
    release_catalog_index_manifest_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    release_catalog_index_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 release-catalog-index-manifest signing")
    release_catalog_index_manifest_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    release_catalog_index_manifest_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex for ed25519 release-catalog-index-manifest signing")
    release_catalog_index_manifest_parser.add_argument("--output", help="Optional output path")

    publish_release_catalog_parser = subparsers.add_parser("publish-release-catalog", help="Build release_catalog.json plus release_catalog_manifest.json in one SATROOT-1 catalog directory")
    publish_release_catalog_parser.add_argument("release_dir", nargs="*", help="Path to a signed SATROOT-1 release directory")
    publish_release_catalog_parser.add_argument("--preset-json", help="Optional SATROOT release catalog preset JSON file with release roots and catalog metadata defaults")
    publish_release_catalog_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested release_manifest.json files; may be repeated")
    publish_release_catalog_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each --discover-under directory")
    publish_release_catalog_parser.add_argument("--output-dir", required=True, help="Directory where release_catalog.json and release_catalog_manifest.json will be written")
    publish_release_catalog_parser.add_argument("--channel", help="Optional catalog channel metadata")
    publish_release_catalog_parser.add_argument("--label", help="Optional human-readable catalog label")
    publish_release_catalog_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the release catalog")
    publish_release_catalog_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    publish_release_catalog_parser.add_argument("--key-id", required=True, help="Signature key identifier for the release catalog manifest")
    publish_release_catalog_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    publish_release_catalog_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 release-catalog-manifest signing")
    publish_release_catalog_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    publish_release_catalog_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex for ed25519 release-catalog-manifest signing")

    publish_release_catalog_index_parser = subparsers.add_parser("publish-release-catalog-index", help="Build release_catalog_index.json plus release_catalog_index_manifest.json in one SATROOT-1 index directory")
    publish_release_catalog_index_parser.add_argument("release_catalog_dir", nargs="*", help="Path to a signed SATROOT-1 release catalog directory")
    publish_release_catalog_index_parser.add_argument("--preset-json", help="Optional SATROOT release catalog index preset JSON file with release catalog roots and index metadata defaults")
    publish_release_catalog_index_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested release_catalog_manifest.json files; may be repeated")
    publish_release_catalog_index_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each --discover-under directory")
    publish_release_catalog_index_parser.add_argument("--output-dir", required=True, help="Directory where release_catalog_index.json and release_catalog_index_manifest.json will be written")
    publish_release_catalog_index_parser.add_argument("--channel", help="Optional index channel metadata")
    publish_release_catalog_index_parser.add_argument("--label", help="Optional human-readable index label")
    publish_release_catalog_index_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the release catalog index")
    publish_release_catalog_index_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    publish_release_catalog_index_parser.add_argument("--key-id", required=True, help="Signature key identifier for the release catalog index manifest")
    publish_release_catalog_index_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    publish_release_catalog_index_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 release-catalog-index-manifest signing")
    publish_release_catalog_index_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    publish_release_catalog_index_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex for ed25519 release-catalog-index-manifest signing")

    bootstrap_release_catalog_publication_parser = subparsers.add_parser("bootstrap-release-catalog-publication", help="Generate signing material and write a ready-to-verify SATROOT-1 release catalog directory")
    bootstrap_release_catalog_publication_parser.add_argument("release_dir", nargs="*", help="Path to a signed SATROOT-1 release directory")
    bootstrap_release_catalog_publication_parser.add_argument("--preset-json", help="Optional SATROOT release catalog preset JSON file with release roots and catalog metadata defaults")
    bootstrap_release_catalog_publication_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested release_manifest.json files; may be repeated")
    bootstrap_release_catalog_publication_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each --discover-under directory")
    bootstrap_release_catalog_publication_parser.add_argument("--output-dir", required=True, help="Directory where catalog material plus release_catalog.json and release_catalog_manifest.json will be written")
    bootstrap_release_catalog_publication_parser.add_argument("--channel", help="Optional catalog channel metadata")
    bootstrap_release_catalog_publication_parser.add_argument("--label", help="Optional human-readable catalog label")
    bootstrap_release_catalog_publication_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the release catalog")
    bootstrap_release_catalog_publication_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_release_catalog_publication_parser.add_argument("--key-id", required=True, help="Signature key identifier to generate and use for the release catalog manifest")

    bootstrap_release_catalog_index_publication_parser = subparsers.add_parser("bootstrap-release-catalog-index-publication", help="Generate signing material and write a ready-to-verify SATROOT-1 release catalog index directory")
    bootstrap_release_catalog_index_publication_parser.add_argument("release_catalog_dir", nargs="*", help="Path to a signed SATROOT-1 release catalog directory")
    bootstrap_release_catalog_index_publication_parser.add_argument("--preset-json", help="Optional SATROOT release catalog index preset JSON file with release catalog roots and index metadata defaults")
    bootstrap_release_catalog_index_publication_parser.add_argument("--discover-under", action="append", dest="discover_under", help="Directory to scan for nested release_catalog_manifest.json files; may be repeated")
    bootstrap_release_catalog_index_publication_parser.add_argument("--non-recursive", action="store_true", help="Only scan immediate children of each --discover-under directory")
    bootstrap_release_catalog_index_publication_parser.add_argument("--output-dir", required=True, help="Directory where index material plus release_catalog_index.json and release_catalog_index_manifest.json will be written")
    bootstrap_release_catalog_index_publication_parser.add_argument("--channel", help="Optional index channel metadata")
    bootstrap_release_catalog_index_publication_parser.add_argument("--label", help="Optional human-readable index label")
    bootstrap_release_catalog_index_publication_parser.add_argument("--published-at", help="Optional ISO-8601 style published-at metadata for the release catalog index")
    bootstrap_release_catalog_index_publication_parser.add_argument("--scheme", choices=["hmac-sha256", "ed25519"], required=True)
    bootstrap_release_catalog_index_publication_parser.add_argument("--key-id", required=True, help="Signature key identifier to generate and use for the release catalog index manifest")

    verify_bundle_parser = subparsers.add_parser("verify-bundle", help="Verify a signed SATROOT-1 bundle directory against its manifest")
    verify_bundle_parser.add_argument("bundle_dir", help="Path to a signed SATROOT-1 bundle directory")

    verify_release_manifest_parser = subparsers.add_parser("verify-release-manifest", help="Verify a signed SATROOT-1 release manifest against its bundle index")
    verify_release_manifest_parser.add_argument("release_manifest_json", help="Path to release-manifest.json")
    verify_release_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification")
    verify_release_manifest_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    verify_release_manifest_parser.add_argument("--private-keys-json", help="Optional path to JSON mapping key_id -> Ed25519 private key hex for verification")

    verify_release_catalog_manifest_parser = subparsers.add_parser("verify-release-catalog-manifest", help="Verify a signed SATROOT-1 release catalog manifest against its release catalog")
    verify_release_catalog_manifest_parser.add_argument("release_catalog_manifest_json", help="Path to release_catalog_manifest.json")
    verify_release_catalog_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification")
    verify_release_catalog_manifest_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    verify_release_catalog_manifest_parser.add_argument("--private-keys-json", help="Optional path to JSON mapping key_id -> Ed25519 private key hex for verification")

    verify_release_catalog_index_manifest_parser = subparsers.add_parser("verify-release-catalog-index-manifest", help="Verify a signed SATROOT-1 release catalog index manifest against its release catalog index")
    verify_release_catalog_index_manifest_parser.add_argument("release_catalog_index_manifest_json", help="Path to release_catalog_index_manifest.json")
    verify_release_catalog_index_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification")
    verify_release_catalog_index_manifest_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    verify_release_catalog_index_manifest_parser.add_argument("--private-keys-json", help="Optional path to JSON mapping key_id -> Ed25519 private key hex for verification")

    verify_publication_descriptor_index_manifest_parser = subparsers.add_parser("verify-publication-descriptor-index-manifest", help="Verify a signed SATROOT publication descriptor index manifest against its descriptor index")
    verify_publication_descriptor_index_manifest_parser.add_argument("publication_descriptor_index_manifest_json", help="Path to publication_descriptor_index_manifest.json")
    verify_publication_descriptor_index_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification")
    verify_publication_descriptor_index_manifest_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    verify_publication_descriptor_index_manifest_parser.add_argument("--private-keys-json", help="Optional path to JSON mapping key_id -> Ed25519 private key hex for verification")

    verify_publication_metadata_manifest_parser = subparsers.add_parser("verify-publication-metadata-manifest", help="Verify a signed SATROOT publication metadata manifest against its report and descriptor files")
    verify_publication_metadata_manifest_parser.add_argument("publication_metadata_manifest_json", help="Path to publication_metadata_manifest.json")
    verify_publication_metadata_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification")
    verify_publication_metadata_manifest_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    verify_publication_metadata_manifest_parser.add_argument("--private-keys-json", help="Optional path to JSON mapping key_id -> Ed25519 private key hex for verification")

    verify_publication_metadata_catalog_manifest_parser = subparsers.add_parser("verify-publication-metadata-catalog-manifest", help="Verify a signed SATROOT publication metadata catalog manifest against its publication metadata catalog")
    verify_publication_metadata_catalog_manifest_parser.add_argument("publication_metadata_catalog_manifest_json", help="Path to publication_metadata_catalog_manifest.json")
    verify_publication_metadata_catalog_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification")
    verify_publication_metadata_catalog_manifest_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    verify_publication_metadata_catalog_manifest_parser.add_argument("--private-keys-json", help="Optional path to JSON mapping key_id -> Ed25519 private key hex for verification")

    verify_publication_registry_manifest_parser = subparsers.add_parser("verify-publication-registry-manifest", help="Verify a signed SATROOT publication registry manifest against its publication registry")
    verify_publication_registry_manifest_parser.add_argument("publication_registry_manifest_json", help="Path to publication_registry_manifest.json")
    verify_publication_registry_manifest_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification")
    verify_publication_registry_manifest_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    verify_publication_registry_manifest_parser.add_argument("--private-keys-json", help="Optional path to JSON mapping key_id -> Ed25519 private key hex for verification")

    generate_keys_parser = subparsers.add_parser("generate-ed25519-private-keys", help="Generate Ed25519 private key hex mappings")
    generate_keys_parser.add_argument("--key-id", action="append", dest="key_ids", help="Key identifier to generate")
    generate_keys_parser.add_argument("--signer-key-map-json", help="Optional path to JSON mapping signer -> key_id")
    generate_keys_parser.add_argument("--output", help="Optional output path")

    bootstrap_ed25519_parser = subparsers.add_parser("bootstrap-ed25519-workflow", help="Generate signer map plus Ed25519 private and public key material for a SATROOT-1 ledger")
    bootstrap_ed25519_parser.add_argument("events_json", help="Path to JSON array of SATROOT-1 events")
    bootstrap_ed25519_parser.add_argument("--output-dir", required=True, help="Directory where signer_key_map.json, private_keys.json, and public_keys.json will be written")
    bootstrap_ed25519_parser.add_argument("--key-prefix", default="", help="Optional prefix for generated key IDs")
    bootstrap_ed25519_parser.add_argument("--key-suffix", default="-key", help="Optional suffix for generated key IDs")

    bootstrap_release_ed25519_parser = subparsers.add_parser("bootstrap-release-ed25519", help="Generate Ed25519 signing and verification material for SATROOT release-manifest signing")
    bootstrap_release_ed25519_parser.add_argument("--key-id", action="append", dest="key_ids", help="Release key identifier to generate")
    bootstrap_release_ed25519_parser.add_argument("--output-dir", required=True, help="Directory where release_private_keys.json and release_public_keys.json will be written")

    derive_keys_parser = subparsers.add_parser("derive-ed25519-public-keys", help="Derive Ed25519 public keys from private key hex mappings")
    derive_keys_parser.add_argument("private_keys_json", help="Path to JSON mapping key_id -> Ed25519 private key hex")
    derive_keys_parser.add_argument("--output", help="Optional output path")

    annotate_parser = subparsers.add_parser("annotate-ledger", help="Add event_id and state_hash commitments to a SATROOT-1 ledger")
    annotate_parser.add_argument("events_json", help="Path to JSON array of SATROOT-1 events")
    annotate_parser.add_argument("--scheme", choices=["demo", "hmac-sha256", "ed25519"], default="demo")
    annotate_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret for hmac-sha256 verification")
    annotate_parser.add_argument("--public-keys-json", help="Path to JSON mapping key_id -> Ed25519 public key hex for verification")
    annotate_parser.add_argument("--private-keys-json", help="Optional path to JSON mapping key_id -> Ed25519 private key hex for verification")
    annotate_parser.add_argument("--no-event-id", action="store_true", help="Do not attach event_id fields")
    annotate_parser.add_argument("--no-state-hash", action="store_true", help="Do not attach state_hash fields")
    annotate_parser.add_argument("--output", help="Optional output path")

    sign_event_parser = subparsers.add_parser("sign-event", help="Sign a single SATROOT-1 event record")
    sign_event_parser.add_argument("event_json", help="Path to a JSON event object")
    sign_event_parser.add_argument("--scheme", choices=["demo", "hmac-sha256", "ed25519"], required=True)
    sign_event_parser.add_argument("--key-id", help="Signature key identifier for non-demo schemes")
    sign_event_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    sign_event_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    sign_event_parser.add_argument("--output", help="Optional output path")

    sign_ledger_parser = subparsers.add_parser("sign-ledger", help="Sign a SATROOT-1 ledger array")
    sign_ledger_parser.add_argument("events_json", help="Path to JSON array of SATROOT-1 events")
    sign_ledger_parser.add_argument("--scheme", choices=["demo", "hmac-sha256", "ed25519"], required=True)
    sign_ledger_parser.add_argument("--signer-key-map-json", help="Path to JSON mapping signer -> key_id")
    sign_ledger_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret")
    sign_ledger_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex")
    sign_ledger_parser.add_argument("--include-state-hash", action="store_true", help="Attach state_hash to each signed event")
    sign_ledger_parser.add_argument("--output", help="Optional output path")

    return parser


def _verifier_from_args(args: Any, *, allow_private_keys_for_ed25519: bool = False) -> SignatureVerifier:
    if args.scheme == "demo":
        return demo_signature_verifier
    if args.scheme == "hmac-sha256":
        if not args.secrets_json:
            raise SatRootError("--secrets-json is required for hmac-sha256")
        secrets = _load_json_object_file(args.secrets_json, label="secrets-json")
        return make_hmac_sha256_verifier(secrets)
    if args.scheme == "ed25519":
        public_keys_json = getattr(args, "public_keys_json", None)
        if public_keys_json:
            public_keys = _load_json_object_file(public_keys_json, label="public-keys-json")
            return make_ed25519_verifier(public_keys)
        if allow_private_keys_for_ed25519:
            private_keys_json = getattr(args, "private_keys_json", None)
            if not private_keys_json:
                raise SatRootError("--public-keys-json or --private-keys-json is required for ed25519")
            private_keys = _load_json_object_file(private_keys_json, label="private-keys-json")
            public_keys = {key_id: ed25519_public_key_hex(private_key_hex) for key_id, private_key_hex in private_keys.items()}
            return make_ed25519_verifier(public_keys)
        raise SatRootError("--public-keys-json is required for ed25519 replay")
    raise SatRootError(f"unsupported scheme: {args.scheme}")


def _signer_and_verifier_from_args(args: Any) -> tuple[Optional[SignerFunction], SignatureVerifier, Optional[Mapping[str, str]]]:
    if args.scheme == "demo":
        return None, demo_signature_verifier, None
    if args.scheme == "hmac-sha256":
        secrets = _load_json_object_file(args.secrets_json, label="secrets-json")
        return make_hmac_sha256_signer(secrets), _verifier_from_args(args), secrets
    if args.scheme == "ed25519":
        if not args.private_keys_json:
            raise SatRootError("--private-keys-json is required for ed25519")
        private_keys = _load_json_object_file(args.private_keys_json, label="private-keys-json")
        return make_ed25519_signer(private_keys), _verifier_from_args(args, allow_private_keys_for_ed25519=True), private_keys
    raise SatRootError(f"unsupported scheme: {args.scheme}")


def _release_manifest_signer_from_args(args: Any) -> SignerFunction:
    if args.scheme == "hmac-sha256":
        if getattr(args, "secrets_json", None):
            secrets = _load_json_object_file(args.secrets_json, label="secrets-json")
            return make_hmac_sha256_signer(secrets)
        if not args.secret:
            raise SatRootError("--secret is required for hmac-sha256 release-manifest signing")
        return make_hmac_sha256_signer({args.key_id: args.secret})
    if args.scheme == "ed25519":
        if getattr(args, "private_keys_json", None):
            private_keys = _load_json_object_file(args.private_keys_json, label="private-keys-json")
            return make_ed25519_signer(private_keys)
        if not args.private_key_hex:
            raise SatRootError("--private-key-hex is required for ed25519 release-manifest signing")
        return make_ed25519_signer({args.key_id: args.private_key_hex})
    raise SatRootError(f"unsupported release signature scheme: {args.scheme}")


def _release_manifest_verifier_from_args(args: Any, manifest: Mapping[str, Any]) -> SignatureVerifier:
    scheme = manifest.get("signature_scheme")
    if scheme == "hmac-sha256":
        if not args.secrets_json:
            raise SatRootError("--secrets-json is required for hmac-sha256 release-manifest verification")
        secrets = _load_json_object_file(args.secrets_json, label="secrets-json")
        return make_hmac_sha256_verifier(secrets)
    if scheme == "ed25519":
        if args.public_keys_json:
            public_keys = _load_json_object_file(args.public_keys_json, label="public-keys-json")
            return make_ed25519_verifier(public_keys)
        if args.private_keys_json:
            private_keys = _load_json_object_file(args.private_keys_json, label="private-keys-json")
            public_keys = derive_ed25519_public_keys(private_keys)
            return make_ed25519_verifier(public_keys)
        raise SatRootError("--public-keys-json or --private-keys-json is required for ed25519 release-manifest verification")
    raise SatRootError(f"unsupported release signature scheme: {scheme!r}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        if argv is None and len(sys.argv) == 2:
            args = parser.parse_args(["replay", sys.argv[1]])
        else:
            parser.print_help()
            return 2

    if args.command == "init-genesis":
        genesis = scaffold_genesis_record(
            symbol=args.symbol,
            name=args.name,
            root_id=args.root_id,
            mint_authority=args.mint_authority,
            initial_owner=args.initial_owner,
            decimals=args.decimals,
            max_supply=args.max_supply,
            initial_balance=args.initial_balance,
            profile=args.profile,
            profile_fields=parse_profile_field_overrides(args.profile_fields),
            rules_hash=args.rules_hash,
            nonce=args.nonce,
        )
        _write_output(genesis, args.output)
        return 0

    if args.command == "bootstrap-stable-demo":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        demo = bootstrap_stable_reference_demo_ledger(
            symbol=args.symbol,
            name=args.name,
            reference_unit=args.reference_unit,
            root_id=args.root_id,
            issuer=args.issuer,
            merchant_account=args.merchant_account,
            service_account=args.service_account,
            initial_balance=args.initial_balance,
            merchant_amount=args.merchant_amount,
            service_amount=args.service_amount,
            merchant_burn_amount=args.merchant_burn_amount,
            intended_use=args.intended_use,
            rules_hash=args.rules_hash,
            nonce=args.nonce,
            include_annotation=not args.no_annotated_output,
        )
        _write_json_file(output_dir / "events.json", demo["events"])
        if demo["annotated_events"] is not None:
            _write_json_file(output_dir / "annotated_events.json", demo["annotated_events"])
        summary = {
            "profile": "SATROOT-STABLE-1",
            "profile_mode": "reference-only",
            "reference_unit": args.reference_unit,
            "event_count": len(demo["events"]),
            "final_state_hash": demo["final_state_hash"],
            "final_state_snapshot": demo["final_state_snapshot"],
        }
        _write_json_file(output_dir / "summary.json", summary)
        print(f"wrote SATROOT-STABLE-1 demo ledger to {output_dir}")
        return 0

    if args.command == "bootstrap-machine-demo":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        demo = bootstrap_machine_credit_demo_ledger(
            symbol=args.symbol,
            name=args.name,
            service_scope=args.service_scope,
            billing_unit=args.billing_unit,
            consumption_model=args.consumption_model,
            root_id=args.root_id,
            issuer=args.issuer,
            tenant_account=args.tenant_account,
            worker_account=args.worker_account,
            max_supply=args.max_supply,
            initial_balance=args.initial_balance,
            tenant_amount=args.tenant_amount,
            worker_amount=args.worker_amount,
            worker_burn_amount=args.worker_burn_amount,
            intended_use=args.intended_use,
            rules_hash=args.rules_hash,
            nonce=args.nonce,
            include_annotation=not args.no_annotated_output,
        )
        _write_json_file(output_dir / "events.json", demo["events"])
        if demo["annotated_events"] is not None:
            _write_json_file(output_dir / "annotated_events.json", demo["annotated_events"])
        summary = {
            "profile": "SATROOT-MACHINE-1",
            "profile_mode": "prepaid-credit",
            "service_scope": args.service_scope,
            "billing_unit": args.billing_unit,
            "consumption_model": args.consumption_model,
            "event_count": len(demo["events"]),
            "final_state_hash": demo["final_state_hash"],
            "final_state_snapshot": demo["final_state_snapshot"],
        }
        _write_json_file(output_dir / "summary.json", summary)
        print(f"wrote SATROOT-MACHINE-1 demo ledger to {output_dir}")
        return 0

    if args.command == "bootstrap-singleton-demo":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        holder_account, next_holder, archive_account = _resolve_singleton_demo_accounts(
            args.profile,
            holder_account=args.holder_account,
            next_holder=args.next_holder,
            archive_account=args.archive_account,
            no_archive=args.no_archive,
        )
        demo = bootstrap_singleton_object_demo_ledger(
            profile=args.profile,
            symbol=args.symbol,
            name=args.name,
            root_id=args.root_id,
            issuer=args.issuer,
            holder_account=holder_account,
            next_holder=next_holder,
            archive_account=archive_account,
            profile_fields=parse_profile_field_overrides(args.profile_fields),
            rules_hash=args.rules_hash,
            nonce=args.nonce,
            retire=not args.no_retire,
            include_annotation=not args.no_annotated_output,
        )
        _write_json_file(output_dir / "events.json", demo["events"])
        if demo["annotated_events"] is not None:
            _write_json_file(output_dir / "annotated_events.json", demo["annotated_events"])
        summary = {
            "profile": args.profile,
            "profile_mode": demo["final_state_snapshot"]["profile_mode"],
            "event_count": len(demo["events"]),
            "final_state_hash": demo["final_state_hash"],
            "final_state_snapshot": demo["final_state_snapshot"],
        }
        _write_json_file(output_dir / "summary.json", summary)
        print(f"wrote {args.profile} singleton demo ledger to {output_dir}")
        return 0

    if args.command == "bootstrap-singleton-demo-bundle":
        if args.verifier_only and args.scheme != "ed25519":
            raise SatRootError("--verifier-only is only supported for ed25519 bundles")
        holder_account, next_holder, archive_account = _resolve_singleton_demo_accounts(
            args.profile,
            holder_account=args.holder_account,
            next_holder=args.next_holder,
            archive_account=args.archive_account,
            no_archive=args.no_archive,
        )
        bundle = bootstrap_singleton_object_demo_bundle(
            profile=args.profile,
            symbol=args.symbol,
            name=args.name,
            scheme=args.scheme,
            root_id=args.root_id,
            issuer=args.issuer,
            holder_account=holder_account,
            next_holder=next_holder,
            archive_account=archive_account,
            profile_fields=parse_profile_field_overrides(args.profile_fields),
            rules_hash=args.rules_hash,
            nonce=args.nonce,
            retire=not args.no_retire,
            key_prefix=args.key_prefix,
            key_suffix=args.key_suffix,
            include_state_hash=not args.no_state_hash,
            include_annotation=not args.no_annotated_output,
        )
        output = _write_bundle_output_dir(
            bundle,
            output_dir=args.output_dir,
            include_private_keys=not args.verifier_only,
            genesis=bundle["genesis"],
        )
        print(f"wrote {args.profile} {args.scheme} singleton demo bundle to {Path(output['output_dir'])}")
        return 0

    if args.command == "bootstrap-singleton-demo-release":
        release_metadata = {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }
        holder_account, next_holder, archive_account = _resolve_singleton_demo_accounts(
            args.profile,
            holder_account=args.holder_account,
            next_holder=args.next_holder,
            archive_account=args.archive_account,
            no_archive=args.no_archive,
        )
        released = bootstrap_singleton_object_demo_release(
            profile=args.profile,
            symbol=args.symbol,
            name=args.name,
            bundle_scheme=args.scheme,
            release_scheme=args.release_scheme,
            release_key_id=args.release_key_id,
            output_dir=args.output_dir,
            root_id=args.root_id,
            issuer=args.issuer,
            holder_account=holder_account,
            next_holder=next_holder,
            archive_account=archive_account,
            profile_fields=parse_profile_field_overrides(args.profile_fields),
            rules_hash=args.rules_hash,
            nonce=args.nonce,
            retire=not args.no_retire,
            key_prefix=args.key_prefix,
            key_suffix=args.key_suffix,
            include_state_hash=not args.no_state_hash,
            include_annotation=not args.no_annotated_output,
            verifier_only=args.verifier_only,
            release_metadata=release_metadata,
        )
        print(f"wrote {args.profile} singleton demo release to {Path(released['release_dir'])}")
        return 0

    if args.command == "init-event":
        if args.events_json:
            events = _load_json_file(args.events_json)
            if not isinstance(events, list):
                raise SatRootError("events_json must contain a JSON array")
            event = scaffold_event_from_ledger(
                events,
                action=args.action,
                signer=args.signer,
                from_account=args.from_account,
                to_account=args.to_account,
                amount=args.amount,
                new_mint_authority=args.new_mint_authority,
            )
        else:
            if args.root_id is None or args.sequence is None or args.prev_event_id is None:
                raise SatRootError("--root-id, --sequence, and --prev-event-id are required when --events-json is not provided")
            event = scaffold_event_record(
                action=args.action,
                root_id=args.root_id,
                sequence=args.sequence,
                prev_event_id=args.prev_event_id,
                signer=args.signer,
                from_account=args.from_account,
                to_account=args.to_account,
                amount=args.amount,
                new_mint_authority=args.new_mint_authority,
            )
        _write_output(event, args.output)
        return 0

    if args.command == "append-event":
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        signer_key_ids = None
        signer_function: Optional[SignerFunction] = None
        verifier = demo_signature_verifier
        if args.scheme != "demo":
            signer_function, verifier, _ = _signer_and_verifier_from_args(args)
            if args.signer_key_map_json:
                signer_key_ids = _load_json_object_file(args.signer_key_map_json, label="signer-key-map-json")
        if args.event_json:
            event = _load_json_file(args.event_json)
            if not isinstance(event, dict):
                raise SatRootError("event_json must contain a JSON object")
        else:
            if not args.action or not args.signer:
                raise SatRootError("--action and --signer are required when --event-json is not provided")
            event = scaffold_event_from_ledger(
                events,
                action=args.action,
                signer=args.signer,
                from_account=args.from_account,
                to_account=args.to_account,
                amount=args.amount,
                new_mint_authority=args.new_mint_authority,
                verifier=verifier,
            )
        appended = append_signed_event_to_ledger(
            events,
            event,
            scheme=args.scheme,
            explicit_key_id=args.key_id,
            signer_key_ids=signer_key_ids,
            signer=signer_function,
            verifier=verifier,
            include_state_hash=args.include_state_hash,
        )
        _write_output(appended, args.output)
        return 0

    if args.command == "consume-machine-credit":
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        signer_key_ids = None
        signer_function: Optional[SignerFunction] = None
        verifier = demo_signature_verifier
        if args.scheme != "demo":
            signer_function, verifier, _ = _signer_and_verifier_from_args(args)
            if args.signer_key_map_json:
                signer_key_ids = _load_json_object_file(args.signer_key_map_json, label="signer-key-map-json")
        event = scaffold_machine_credit_consumption_event(
            events,
            signer=args.signer,
            amount=args.amount,
            from_account=args.from_account,
            verifier=verifier,
        )
        appended = append_signed_event_to_ledger(
            events,
            event,
            scheme=args.scheme,
            explicit_key_id=args.key_id,
            signer_key_ids=signer_key_ids,
            signer=signer_function,
            verifier=verifier,
            include_state_hash=args.include_state_hash,
        )
        _write_output(appended, args.output)
        return 0

    if args.command == "archive-singleton-object":
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        signer_key_ids = None
        signer_function: Optional[SignerFunction] = None
        verifier = demo_signature_verifier
        if args.scheme != "demo":
            signer_function, verifier, _ = _signer_and_verifier_from_args(args)
            if args.signer_key_map_json:
                signer_key_ids = _load_json_object_file(args.signer_key_map_json, label="signer-key-map-json")
        event = scaffold_singleton_object_archive_event(
            events,
            signer=args.signer,
            archive_account=args.archive_account,
            from_account=args.from_account,
            verifier=verifier,
        )
        appended = append_signed_event_to_ledger(
            events,
            event,
            scheme=args.scheme,
            explicit_key_id=args.key_id,
            signer_key_ids=signer_key_ids,
            signer=signer_function,
            verifier=verifier,
            include_state_hash=args.include_state_hash,
        )
        _write_output(appended, args.output)
        return 0

    if args.command == "transfer-singleton-object":
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        signer_key_ids = None
        signer_function: Optional[SignerFunction] = None
        verifier = demo_signature_verifier
        if args.scheme != "demo":
            signer_function, verifier, _ = _signer_and_verifier_from_args(args)
            if args.signer_key_map_json:
                signer_key_ids = _load_json_object_file(args.signer_key_map_json, label="signer-key-map-json")
        event = scaffold_singleton_object_transfer_event(
            events,
            signer=args.signer,
            to_account=args.to_account,
            from_account=args.from_account,
            verifier=verifier,
        )
        appended = append_signed_event_to_ledger(
            events,
            event,
            scheme=args.scheme,
            explicit_key_id=args.key_id,
            signer_key_ids=signer_key_ids,
            signer=signer_function,
            verifier=verifier,
            include_state_hash=args.include_state_hash,
        )
        _write_output(appended, args.output)
        return 0

    if args.command == "retire-singleton-object":
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        signer_key_ids = None
        signer_function: Optional[SignerFunction] = None
        verifier = demo_signature_verifier
        if args.scheme != "demo":
            signer_function, verifier, _ = _signer_and_verifier_from_args(args)
            if args.signer_key_map_json:
                signer_key_ids = _load_json_object_file(args.signer_key_map_json, label="signer-key-map-json")
        event = scaffold_singleton_object_retirement_event(
            events,
            signer=args.signer,
            from_account=args.from_account,
            verifier=verifier,
        )
        appended = append_signed_event_to_ledger(
            events,
            event,
            scheme=args.scheme,
            explicit_key_id=args.key_id,
            signer_key_ids=signer_key_ids,
            signer=signer_function,
            verifier=verifier,
            include_state_hash=args.include_state_hash,
        )
        _write_output(appended, args.output)
        return 0

    if args.command == "bootstrap-stable-demo-bundle":
        if args.verifier_only and args.scheme != "ed25519":
            raise SatRootError("--verifier-only is only supported for ed25519 bundles")
        bundle = bootstrap_stable_reference_demo_bundle(
            symbol=args.symbol,
            name=args.name,
            scheme=args.scheme,
            reference_unit=args.reference_unit,
            root_id=args.root_id,
            issuer=args.issuer,
            merchant_account=args.merchant_account,
            service_account=args.service_account,
            initial_balance=args.initial_balance,
            merchant_amount=args.merchant_amount,
            service_amount=args.service_amount,
            merchant_burn_amount=args.merchant_burn_amount,
            intended_use=args.intended_use,
            rules_hash=args.rules_hash,
            nonce=args.nonce,
            key_prefix=args.key_prefix,
            key_suffix=args.key_suffix,
            include_state_hash=not args.no_state_hash,
            include_annotation=not args.no_annotated_output,
        )
        output = _write_bundle_output_dir(
            bundle,
            output_dir=args.output_dir,
            include_private_keys=not args.verifier_only,
            genesis=bundle["genesis"],
        )
        print(f"wrote SATROOT-STABLE-1 {args.scheme} demo bundle to {Path(output['output_dir'])}")
        return 0

    if args.command == "bootstrap-stable-demo-release":
        release_metadata = {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }
        released = bootstrap_stable_reference_demo_release(
            symbol=args.symbol,
            name=args.name,
            bundle_scheme=args.scheme,
            release_scheme=args.release_scheme,
            release_key_id=args.release_key_id,
            output_dir=args.output_dir,
            reference_unit=args.reference_unit,
            root_id=args.root_id,
            issuer=args.issuer,
            merchant_account=args.merchant_account,
            service_account=args.service_account,
            initial_balance=args.initial_balance,
            merchant_amount=args.merchant_amount,
            service_amount=args.service_amount,
            merchant_burn_amount=args.merchant_burn_amount,
            intended_use=args.intended_use,
            rules_hash=args.rules_hash,
            nonce=args.nonce,
            key_prefix=args.key_prefix,
            key_suffix=args.key_suffix,
            include_state_hash=not args.no_state_hash,
            include_annotation=not args.no_annotated_output,
            verifier_only=args.verifier_only,
            release_metadata=release_metadata,
        )
        print(f"wrote SATROOT-STABLE-1 demo release to {Path(released['release_dir'])}")
        return 0

    if args.command == "bootstrap-machine-demo-bundle":
        if args.verifier_only and args.scheme != "ed25519":
            raise SatRootError("--verifier-only is only supported for ed25519 bundles")
        bundle = bootstrap_machine_credit_demo_bundle(
            symbol=args.symbol,
            name=args.name,
            scheme=args.scheme,
            service_scope=args.service_scope,
            billing_unit=args.billing_unit,
            consumption_model=args.consumption_model,
            root_id=args.root_id,
            issuer=args.issuer,
            tenant_account=args.tenant_account,
            worker_account=args.worker_account,
            max_supply=args.max_supply,
            initial_balance=args.initial_balance,
            tenant_amount=args.tenant_amount,
            worker_amount=args.worker_amount,
            worker_burn_amount=args.worker_burn_amount,
            intended_use=args.intended_use,
            rules_hash=args.rules_hash,
            nonce=args.nonce,
            key_prefix=args.key_prefix,
            key_suffix=args.key_suffix,
            include_state_hash=not args.no_state_hash,
            include_annotation=not args.no_annotated_output,
        )
        output = _write_bundle_output_dir(
            bundle,
            output_dir=args.output_dir,
            include_private_keys=not args.verifier_only,
            genesis=bundle["genesis"],
        )
        print(f"wrote SATROOT-MACHINE-1 {args.scheme} demo bundle to {Path(output['output_dir'])}")
        return 0

    if args.command == "bootstrap-machine-demo-release":
        release_metadata = {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }
        released = bootstrap_machine_credit_demo_release(
            symbol=args.symbol,
            name=args.name,
            bundle_scheme=args.scheme,
            release_scheme=args.release_scheme,
            release_key_id=args.release_key_id,
            output_dir=args.output_dir,
            service_scope=args.service_scope,
            billing_unit=args.billing_unit,
            consumption_model=args.consumption_model,
            root_id=args.root_id,
            issuer=args.issuer,
            tenant_account=args.tenant_account,
            worker_account=args.worker_account,
            max_supply=args.max_supply,
            initial_balance=args.initial_balance,
            tenant_amount=args.tenant_amount,
            worker_amount=args.worker_amount,
            worker_burn_amount=args.worker_burn_amount,
            intended_use=args.intended_use,
            rules_hash=args.rules_hash,
            nonce=args.nonce,
            key_prefix=args.key_prefix,
            key_suffix=args.key_suffix,
            include_state_hash=not args.no_state_hash,
            include_annotation=not args.no_annotated_output,
            verifier_only=args.verifier_only,
            release_metadata=release_metadata,
        )
        print(f"wrote SATROOT-MACHINE-1 demo release to {Path(released['release_dir'])}")
        return 0

    if args.command == "bootstrap-demo-catalog":
        preset_path = None if not args.preset_json else Path(args.preset_json).resolve()
        preset = load_demo_catalog_preset(preset_path) if preset_path is not None else None
        release_metadata = dict((preset or {}).get("release_metadata", {}))
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                release_metadata[key] = value
        symbol_overrides = dict((preset or {}).get("symbol_overrides", {}))
        symbol_overrides.update(
            parse_named_string_overrides(
                args.symbol_overrides,
                label="demo catalog symbol override",
                allowed_keys=DEMO_CATALOG_PROFILES,
            )
        )
        name_overrides = dict((preset or {}).get("name_overrides", {}))
        name_overrides.update(
            parse_named_string_overrides(
                args.name_overrides,
                label="demo catalog name override",
                allowed_keys=DEMO_CATALOG_PROFILES,
            )
        )
        profile_field_overrides = _merge_nested_override_maps(
            (preset or {}).get("profile_field_overrides"),
            parse_profile_field_override_map(
                args.profile_field_overrides,
                allowed_profiles=DEMO_CATALOG_PROFILES,
            ),
        )
        profile_structure_overrides = _merge_nested_override_maps(
            (preset or {}).get("profile_structure_overrides"),
            parse_profile_structure_override_map(
                args.profile_structure_overrides,
                allowed_profiles=DEMO_CATALOG_PROFILES,
            ),
        )
        workspace = write_demo_catalog_workspace(
            bundle_scheme=args.scheme,
            release_scheme=args.release_scheme,
            release_key_id=args.release_key_id,
            output_dir=args.output_dir,
            profiles=args.profile or (preset or {}).get("profiles"),
            symbol_overrides=symbol_overrides,
            name_overrides=name_overrides,
            profile_field_overrides=profile_field_overrides,
            profile_structure_overrides=profile_structure_overrides,
            key_prefix=args.key_prefix,
            key_suffix=args.key_suffix,
            include_state_hash=not args.no_state_hash,
            include_annotation=not args.no_annotated_output,
            verifier_only=args.verifier_only,
            release_metadata=release_metadata,
            preset_path=preset_path,
        )
        output_dir = Path(args.output_dir)
        print(f"wrote SATROOT demo catalog workspace to {output_dir}")
        return 0

    if args.command == "bootstrap-publication-stack":
        stack_preset_path = None if not args.stack_preset_json else Path(args.stack_preset_json).resolve()
        stack_preset = load_publication_stack_preset(stack_preset_path) if stack_preset_path is not None else None
        catalog_preset_paths = [
            Path(value).resolve()
            for value in [*((stack_preset or {}).get("catalog_preset_paths", [])), *((args.catalog_preset_jsons or []))]
        ]
        if not catalog_preset_paths:
            raise SatRootError("bootstrap-publication-stack requires at least one --catalog-preset-json or a --stack-preset-json")
        release_catalog_preset_path = None if not args.release_catalog_preset_json else Path(args.release_catalog_preset_json).resolve()
        release_catalog_preset = (
            load_release_catalog_preset(release_catalog_preset_path)
            if release_catalog_preset_path is not None
            else None
        )
        catalog_metadata = dict((stack_preset or {}).get("release_catalog_metadata", {}))
        catalog_metadata.update(dict((release_catalog_preset or {}).get("catalog_metadata", {})))
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                catalog_metadata[key] = value

        write_publication_stack_workspace(
            bundle_scheme=args.scheme,
            release_scheme=args.release_scheme,
            release_key_id=args.release_key_id,
            release_catalog_scheme=args.release_catalog_scheme,
            release_catalog_key_id=args.release_catalog_key_id,
            output_dir=args.output_dir,
            catalog_preset_paths=catalog_preset_paths,
            release_catalog_metadata=catalog_metadata,
            key_prefix=args.key_prefix,
            key_suffix=args.key_suffix,
            include_state_hash=not args.no_state_hash,
            include_annotation=not args.no_annotated_output,
            verifier_only=args.verifier_only,
            stack_preset_path=stack_preset_path,
            release_catalog_preset_path=release_catalog_preset_path,
        )
        print(f"wrote SATROOT publication stack to {Path(args.output_dir).resolve()}")
        return 0

    if args.command == "bootstrap-publication-network":
        network_preset_path = None if not args.network_preset_json else Path(args.network_preset_json).resolve()
        network_preset = load_publication_network_preset(network_preset_path) if network_preset_path is not None else None
        stack_preset_paths = [
            Path(value).resolve()
            for value in [*((network_preset or {}).get("stack_preset_paths", [])), *((args.stack_preset_jsons or []))]
        ]
        if not stack_preset_paths:
            raise SatRootError("bootstrap-publication-network requires at least one --stack-preset-json or a --network-preset-json")

        release_catalog_index_preset_path = None if not args.release_catalog_index_preset_json else Path(args.release_catalog_index_preset_json).resolve()
        release_catalog_index_preset = (
            load_release_catalog_index_preset(release_catalog_index_preset_path)
            if release_catalog_index_preset_path is not None
            else None
        )
        index_metadata = dict((network_preset or {}).get("release_catalog_index_metadata", {}))
        index_metadata.update(dict((release_catalog_index_preset or {}).get("index_metadata", {})))
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                index_metadata[key] = value

        write_publication_network_workspace(
            bundle_scheme=args.scheme,
            release_scheme=args.release_scheme,
            release_key_id=args.release_key_id,
            release_catalog_scheme=args.release_catalog_scheme,
            release_catalog_key_id=args.release_catalog_key_id,
            release_catalog_index_scheme=args.release_catalog_index_scheme,
            release_catalog_index_key_id=args.release_catalog_index_key_id,
            output_dir=args.output_dir,
            stack_preset_paths=stack_preset_paths,
            release_catalog_index_metadata=index_metadata,
            key_prefix=args.key_prefix,
            key_suffix=args.key_suffix,
            include_state_hash=not args.no_state_hash,
            include_annotation=not args.no_annotated_output,
            verifier_only=args.verifier_only,
            network_preset_path=network_preset_path,
            release_catalog_index_preset_path=release_catalog_index_preset_path,
        )
        print(f"wrote SATROOT publication network to {Path(args.output_dir).resolve()}")
        return 0

    if args.command == "bootstrap-publication-registry-workspace":
        preset_path = None if not args.preset_json else Path(args.preset_json).resolve()
        preset = load_publication_registry_workspace_preset(preset_path) if preset_path is not None else None
        publication_network_dir = Path((preset or {}).get("publication_network_dir")).resolve() if (preset or {}).get("publication_network_dir") else None
        if args.publication_network_dir:
            publication_network_dir = Path(args.publication_network_dir).resolve()
        discover_under = [*((preset or {}).get("discover_under", [])), *((args.discover_under or []))]
        if publication_network_dir is not None:
            discover_under.append(str(publication_network_dir))
        release_catalog_index_dir = args.release_catalog_index_dir or (preset or {}).get("release_catalog_index_dir")
        if release_catalog_index_dir is None and publication_network_dir is not None:
            release_catalog_index_dir = str((publication_network_dir / "release_catalog_index").resolve())
        if release_catalog_index_dir is None:
            raise SatRootError("bootstrap-publication-registry-workspace requires --release-catalog-index-dir or --publication-network-dir")

        descriptor_index_metadata = dict((preset or {}).get("descriptor_index_metadata", {}))
        for key, value in {
            "channel": args.descriptor_index_channel,
            "label": args.descriptor_index_label,
            "published_at": args.descriptor_index_published_at,
        }.items():
            if value is not None:
                descriptor_index_metadata[key] = value
        publication_metadata_catalog_metadata = dict((preset or {}).get("publication_metadata_catalog_metadata", {}))
        for key, value in {
            "channel": args.publication_metadata_catalog_channel,
            "label": args.publication_metadata_catalog_label,
            "published_at": args.publication_metadata_catalog_published_at,
        }.items():
            if value is not None:
                publication_metadata_catalog_metadata[key] = value
        publication_registry_metadata = dict((preset or {}).get("publication_registry_metadata", {}))
        for key, value in {
            "channel": args.publication_registry_channel,
            "label": args.publication_registry_label,
            "published_at": args.publication_registry_published_at,
        }.items():
            if value is not None:
                publication_registry_metadata[key] = value
        write_publication_registry_workspace(
            artifact_paths=[*((preset or {}).get("artifact_paths", [])), *((args.path or []))],
            discover_under=discover_under,
            recursive=False if args.non_recursive else (preset or {}).get("recursive", True),
            release_catalog_index_dir=release_catalog_index_dir,
            publication_network_dir=publication_network_dir,
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            publication_descriptor_index_key_id=args.publication_descriptor_index_key_id,
            publication_metadata_key_id=args.publication_metadata_key_id,
            publication_metadata_catalog_key_id=args.publication_metadata_catalog_key_id,
            publication_registry_key_id=args.publication_registry_key_id,
            descriptor_index_metadata=descriptor_index_metadata,
            publication_metadata_catalog_metadata=publication_metadata_catalog_metadata,
            publication_registry_metadata=publication_registry_metadata,
        )
        print(f"wrote SATROOT publication registry workspace to {Path(args.output_dir).resolve()}")
        return 0

    if args.command == "publish-publication-stack":
        catalog_metadata = {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }
        workspace_dirs = resolve_demo_catalog_workspace_inputs(
            args.catalog_workspace_dir,
            discover_under=args.discover_under,
            recursive=not args.non_recursive,
        )
        publish_publication_stack_workspace(
            workspace_dirs,
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.release_catalog_key_id,
            release_catalog_metadata=catalog_metadata,
        )
        print(f"wrote SATROOT publication stack from existing workspaces to {Path(args.output_dir).resolve()}")
        return 0

    if args.command == "publish-publication-network":
        index_metadata = {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }
        workspace_dirs = resolve_publication_stack_workspace_inputs(
            args.publication_stack_dir,
            discover_under=args.discover_under,
            recursive=not args.non_recursive,
        )
        publish_publication_network_workspace(
            workspace_dirs,
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.release_catalog_index_key_id,
            release_catalog_index_metadata=index_metadata,
        )
        print(f"wrote SATROOT publication network from existing workspaces to {Path(args.output_dir).resolve()}")
        return 0

    if args.command == "inventory-artifacts":
        search_roots = [*(args.search_root or []), *((args.discover_under or []))]
        if not search_roots:
            raise SatRootError("inventory-artifacts requires at least one search_root or --discover-under path")
        inventory = inventory_workspace_artifacts(search_roots, recursive=not args.non_recursive)
        print(canonical_json(inventory))
        return 0

    if args.command == "export-demo-catalog-preset":
        preset = export_demo_catalog_preset_from_workspace(args.demo_catalog_dir)
        _write_output(preset, args.output)
        return 0

    if args.command == "export-publication-stack-preset":
        preset = export_publication_stack_preset_from_workspace(
            args.publication_stack_dir,
            output_path=args.output,
            catalog_preset_dir=args.catalog_preset_dir,
        )
        _write_output(preset, args.output)
        return 0

    if args.command == "export-publication-network-preset":
        preset = export_publication_network_preset_from_workspace(
            args.publication_network_dir,
            output_path=args.output,
            stack_preset_dir=args.stack_preset_dir,
            catalog_preset_dir=args.catalog_preset_dir,
        )
        _write_output(preset, args.output)
        return 0

    if args.command == "export-publication-registry-workspace-preset":
        preset = export_publication_registry_workspace_preset_from_workspace(
            args.publication_registry_workspace_dir,
            output_path=args.output,
        )
        _write_output(preset, args.output)
        return 0

    if args.command == "export-publication-descriptor-index-preset":
        preset = export_publication_descriptor_index_preset_from_workspace(
            args.publication_descriptor_index_dir,
            output_path=args.output,
        )
        _write_output(preset, args.output)
        return 0

    if args.command == "export-publication-metadata-catalog-preset":
        preset = export_publication_metadata_catalog_preset_from_workspace(
            args.publication_metadata_catalog_dir,
            output_path=args.output,
        )
        _write_output(preset, args.output)
        return 0

    if args.command == "export-publication-registry-preset":
        preset = export_publication_registry_preset_from_workspace(
            args.publication_registry_dir,
            output_path=args.output,
        )
        _write_output(preset, args.output)
        return 0

    if args.command == "render-publication-report":
        report = render_satroot_artifact_report(args.path)
        _write_text_output(report, args.output)
        return 0

    if args.command == "export-publication-descriptor":
        descriptor = build_satroot_artifact_descriptor(args.path)
        _write_output(descriptor, args.output)
        return 0

    if args.command == "build-publication-descriptor-index":
        preset = load_publication_descriptor_index_preset(args.preset_json) if args.preset_json else None
        index_metadata = {
            **dict((preset or {}).get("index_metadata", {})),
        }
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                index_metadata[key] = value
        index = build_satroot_publication_descriptor_index(
            [*(preset or {}).get("artifact_paths", []), *args.path],
            discover_under=[*((preset or {}).get("discover_under", [])), *((args.discover_under or []))],
            recursive=(preset or {}).get("recursive", True) and not args.non_recursive,
            index_metadata=index_metadata,
        )
        _write_output(index, args.output)
        return 0

    if args.command == "build-publication-descriptor-index-manifest":
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        signer = _release_manifest_signer_from_args(args)
        manifest = build_signed_publication_descriptor_index_manifest(
            args.publication_descriptor_index_json,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            signer=signer,
            base_dir=base_dir,
        )
        _write_output(manifest, output_path)
        return 0

    if args.command == "build-publication-metadata-manifest":
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        signer = _release_manifest_signer_from_args(args)
        manifest = build_signed_publication_metadata_manifest(
            args.publication_report_path,
            args.publication_descriptor_json,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            signer=signer,
            base_dir=base_dir,
        )
        _write_output(manifest, output_path)
        return 0

    if args.command == "build-publication-metadata-catalog":
        preset = load_publication_metadata_catalog_preset(args.preset_json) if args.preset_json else None
        catalog_metadata = {
            **dict((preset or {}).get("catalog_metadata", {})),
        }
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                catalog_metadata[key] = value
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        catalog = build_publication_metadata_catalog(
            [*(preset or {}).get("publication_metadata_bundle_dirs", []), *args.publication_metadata_bundle_dir],
            discover_under=[*((preset or {}).get("discover_under", [])), *((args.discover_under or []))],
            recursive=(preset or {}).get("recursive", True) and not args.non_recursive,
            base_dir=base_dir,
            catalog_metadata=catalog_metadata,
        )
        _write_output(catalog, output_path)
        return 0

    if args.command == "build-publication-metadata-catalog-manifest":
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        signer = _release_manifest_signer_from_args(args)
        manifest = build_signed_publication_metadata_catalog_manifest(
            args.publication_metadata_catalog_json,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            signer=signer,
            base_dir=base_dir,
        )
        _write_output(manifest, output_path)
        return 0

    if args.command == "build-publication-registry":
        preset = load_publication_registry_preset(args.preset_json) if args.preset_json else None
        registry_metadata = {
            **dict((preset or {}).get("registry_metadata", {})),
        }
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                registry_metadata[key] = value
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        registry = build_publication_registry(
            release_catalog_index_dir=args.release_catalog_index_dir or (preset or {}).get("release_catalog_index_dir"),
            publication_descriptor_index_dir=args.publication_descriptor_index_dir or (preset or {}).get("publication_descriptor_index_dir"),
            publication_metadata_catalog_dir=args.publication_metadata_catalog_dir or (preset or {}).get("publication_metadata_catalog_dir"),
            base_dir=base_dir,
            registry_metadata=registry_metadata,
        )
        _write_output(registry, output_path)
        return 0

    if args.command == "build-publication-registry-manifest":
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        signer = _release_manifest_signer_from_args(args)
        manifest = build_signed_publication_registry_manifest(
            args.publication_registry_json,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            signer=signer,
            base_dir=base_dir,
        )
        _write_output(manifest, output_path)
        return 0

    if args.command == "bootstrap-publication-descriptor-index-publication":
        preset = load_publication_descriptor_index_preset(args.preset_json) if args.preset_json else None
        index_metadata = {
            **dict((preset or {}).get("index_metadata", {})),
        }
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                index_metadata[key] = value
        output = bootstrap_publication_descriptor_index_publication(
            [*(preset or {}).get("artifact_paths", []), *args.path],
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            discover_under=[*((preset or {}).get("discover_under", [])), *((args.discover_under or []))],
            recursive=(preset or {}).get("recursive", True) and not args.non_recursive,
            index_metadata=index_metadata,
        )
        print(f"wrote bootstrapped SATROOT publication descriptor index to {Path(args.output_dir).resolve()}")
        return 0

    if args.command == "bootstrap-publication-metadata-bundle":
        output = bootstrap_publication_metadata_bundle(
            args.path,
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.key_id,
        )
        print(f"wrote bootstrapped SATROOT publication metadata bundle to {Path(args.output_dir).resolve()}")
        return 0

    if args.command == "bootstrap-publication-metadata-catalog-publication":
        preset = load_publication_metadata_catalog_preset(args.preset_json) if args.preset_json else None
        catalog_metadata = {
            **dict((preset or {}).get("catalog_metadata", {})),
        }
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                catalog_metadata[key] = value
        output = bootstrap_publication_metadata_catalog_publication(
            [*(preset or {}).get("publication_metadata_bundle_dirs", []), *args.publication_metadata_bundle_dir],
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            discover_under=[*((preset or {}).get("discover_under", [])), *((args.discover_under or []))],
            recursive=(preset or {}).get("recursive", True) and not args.non_recursive,
            catalog_metadata=catalog_metadata,
        )
        print(f"wrote bootstrapped SATROOT publication metadata catalog to {Path(args.output_dir).resolve()}")
        return 0

    if args.command == "bootstrap-publication-registry-publication":
        preset = load_publication_registry_preset(args.preset_json) if args.preset_json else None
        registry_metadata = {
            **dict((preset or {}).get("registry_metadata", {})),
        }
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                registry_metadata[key] = value
        output = bootstrap_publication_registry_publication(
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            release_catalog_index_dir=args.release_catalog_index_dir or (preset or {}).get("release_catalog_index_dir"),
            publication_descriptor_index_dir=args.publication_descriptor_index_dir or (preset or {}).get("publication_descriptor_index_dir"),
            publication_metadata_catalog_dir=args.publication_metadata_catalog_dir or (preset or {}).get("publication_metadata_catalog_dir"),
            registry_metadata=registry_metadata,
        )
        print(f"wrote bootstrapped SATROOT publication registry to {Path(args.output_dir).resolve()}")
        return 0

    if args.command == "bootstrap-genesis-bundle":
        if args.verifier_only and args.scheme != "ed25519":
            raise SatRootError("--verifier-only is only supported for ed25519 bundles")
        bundle = bootstrap_genesis_bundle(
            symbol=args.symbol,
            name=args.name,
            scheme=args.scheme,
            root_id=args.root_id,
            mint_authority=args.mint_authority,
            initial_owner=args.initial_owner,
            decimals=args.decimals,
            max_supply=args.max_supply,
            initial_balance=args.initial_balance,
            profile=args.profile,
            profile_fields=parse_profile_field_overrides(args.profile_fields),
            rules_hash=args.rules_hash,
            nonce=args.nonce,
            key_prefix=args.key_prefix,
            key_suffix=args.key_suffix,
            include_state_hash=not args.no_state_hash,
            include_annotation=not args.no_annotated_output,
        )
        output = _write_bundle_output_dir(
            bundle,
            output_dir=args.output_dir,
            include_private_keys=not args.verifier_only,
            genesis=bundle["genesis"],
        )
        print(f"wrote scaffolded SATROOT-1 {args.scheme} genesis bundle to {Path(output['output_dir'])}")
        return 0

    if args.command == "replay":
        events = _load_json_file(args.events_json)
        result = replay(events, verifier=_verifier_from_args(args))
        print(canonical_json(result.snapshot()))
        print("state_hash=" + result.state_hash())
        return 0

    if args.command == "validate":
        instance = _load_json_file(args.input_json)
        schema = load_protocol_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(instance, schema)
        print(f"valid SATROOT-1 JSON: {count} record(s)")
        return 0

    if args.command == "validate-bundle-manifest":
        manifest = _load_json_file(args.bundle_manifest_json)
        schema = load_bundle_manifest_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(manifest, schema)
        print(f"valid SATROOT-1 bundle manifest: {count} record(s)")
        return 0

    if args.command == "validate-bundle-index":
        index = _load_json_file(args.bundle_index_json)
        schema = load_bundle_index_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(index, schema)
        if not isinstance(index, dict):
            raise SatRootError("bundle index must contain an object")
        validate_bundle_index_consistency(index)
        print(f"valid SATROOT-1 bundle index: {count} record(s)")
        return 0

    if args.command == "validate-release-manifest":
        manifest = _load_json_file(args.release_manifest_json)
        schema = load_release_manifest_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(manifest, schema)
        print(f"valid SATROOT-1 release manifest: {count} record(s)")
        return 0

    if args.command == "validate-release-catalog":
        catalog = _load_json_file(args.release_catalog_json)
        schema = load_release_catalog_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(catalog, schema)
        if not isinstance(catalog, dict):
            raise SatRootError("release catalog must contain an object")
        validate_release_catalog_consistency(catalog)
        print(f"valid SATROOT-1 release catalog: {count} record(s)")
        return 0

    if args.command == "validate-release-catalog-manifest":
        manifest = _load_json_file(args.release_catalog_manifest_json)
        schema = load_release_catalog_manifest_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(manifest, schema)
        print(f"valid SATROOT-1 release catalog manifest: {count} record(s)")
        return 0

    if args.command == "validate-release-catalog-index":
        index = _load_json_file(args.release_catalog_index_json)
        schema = load_release_catalog_index_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(index, schema)
        if not isinstance(index, dict):
            raise SatRootError("release catalog index must contain an object")
        validate_release_catalog_index_consistency(index)
        print(f"valid SATROOT-1 release catalog index: {count} record(s)")
        return 0

    if args.command == "validate-release-catalog-index-manifest":
        manifest = _load_json_file(args.release_catalog_index_manifest_json)
        schema = load_release_catalog_index_manifest_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(manifest, schema)
        print(f"valid SATROOT-1 release catalog index manifest: {count} record(s)")
        return 0

    if args.command == "validate-demo-catalog-summary":
        summary = _load_json_file(args.demo_catalog_summary_json)
        schema = load_demo_catalog_summary_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(summary, schema)
        if not isinstance(summary, dict):
            raise SatRootError("demo catalog summary must contain an object")
        validate_demo_catalog_summary_consistency(summary)
        print(f"valid SATROOT demo catalog summary: {count} record(s)")
        return 0

    if args.command == "validate-publication-stack-summary":
        summary = _load_json_file(args.publication_stack_summary_json)
        schema = load_publication_stack_summary_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(summary, schema)
        if not isinstance(summary, dict):
            raise SatRootError("publication stack summary must contain an object")
        validate_publication_stack_summary_consistency(summary)
        print(f"valid SATROOT publication stack summary: {count} record(s)")
        return 0

    if args.command == "validate-publication-network-summary":
        summary = _load_json_file(args.publication_network_summary_json)
        schema = load_publication_network_summary_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(summary, schema)
        if not isinstance(summary, dict):
            raise SatRootError("publication network summary must contain an object")
        validate_publication_network_summary_consistency(summary)
        print(f"valid SATROOT publication network summary: {count} record(s)")
        return 0

    if args.command == "validate-publication-descriptor-index":
        index = _load_json_file(args.publication_descriptor_index_json)
        schema = load_publication_descriptor_index_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(index, schema)
        if not isinstance(index, dict):
            raise SatRootError("publication descriptor index must contain an object")
        validate_publication_descriptor_index_consistency(index)
        print(f"valid SATROOT publication descriptor index: {count} record(s)")
        return 0

    if args.command == "validate-publication-descriptor-index-manifest":
        manifest = _load_json_file(args.publication_descriptor_index_manifest_json)
        schema = load_publication_descriptor_index_manifest_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(manifest, schema)
        print(f"valid SATROOT publication descriptor index manifest: {count} record(s)")
        return 0

    if args.command == "validate-publication-metadata-manifest":
        manifest = _load_json_file(args.publication_metadata_manifest_json)
        schema = load_publication_metadata_manifest_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(manifest, schema)
        print(f"valid SATROOT publication metadata manifest: {count} record(s)")
        return 0

    if args.command == "validate-publication-metadata-catalog":
        catalog = _load_json_file(args.publication_metadata_catalog_json)
        schema = load_publication_metadata_catalog_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(catalog, schema)
        if not isinstance(catalog, dict):
            raise SatRootError("publication metadata catalog must contain an object")
        validate_publication_metadata_catalog_consistency(catalog)
        print(f"valid SATROOT publication metadata catalog: {count} record(s)")
        return 0

    if args.command == "validate-publication-metadata-catalog-manifest":
        manifest = _load_json_file(args.publication_metadata_catalog_manifest_json)
        schema = load_publication_metadata_catalog_manifest_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(manifest, schema)
        print(f"valid SATROOT publication metadata catalog manifest: {count} record(s)")
        return 0

    if args.command == "validate-publication-registry":
        registry = _load_json_file(args.publication_registry_json)
        schema = load_publication_registry_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(registry, schema)
        if not isinstance(registry, dict):
            raise SatRootError("publication registry must contain an object")
        validate_publication_registry_consistency(registry)
        print(f"valid SATROOT publication registry: {count} record(s)")
        return 0

    if args.command == "validate-publication-registry-manifest":
        manifest = _load_json_file(args.publication_registry_manifest_json)
        schema = load_publication_registry_manifest_schema() if not args.schema_json else _load_json_object_file(args.schema_json, label="schema-json")
        count = validate_instance_against_schema(manifest, schema)
        print(f"valid SATROOT publication registry manifest: {count} record(s)")
        return 0

    if args.command == "init-signer-key-map":
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        signer_key_map = build_signer_key_map(events, key_prefix=args.key_prefix, key_suffix=args.key_suffix)
        _write_output(signer_key_map, args.output)
        return 0

    if args.command == "generate-hmac-secrets":
        key_ids = list(args.key_ids or [])
        if args.signer_key_map_json:
            signer_key_map = _load_json_object_file(args.signer_key_map_json, label="signer-key-map-json")
            for key_id in signer_key_map.values():
                if key_id not in key_ids:
                    key_ids.append(key_id)
        shared_secrets = generate_hmac_shared_secrets(key_ids)
        _write_output(shared_secrets, args.output)
        return 0

    if args.command == "bootstrap-hmac-workflow":
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        material = bootstrap_hmac_workflow(events, key_prefix=args.key_prefix, key_suffix=args.key_suffix)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json_file(output_dir / "signer_key_map.json", material["signer_key_map"])
        _write_json_file(output_dir / "secrets.json", material["shared_secrets"])
        print(f"wrote HMAC workflow files to {output_dir}")
        return 0

    if args.command == "bootstrap-release-hmac":
        key_ids = list(args.key_ids or [])
        material = bootstrap_release_hmac_material(key_ids)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json_file(output_dir / "release_secrets.json", material["shared_secrets"])
        print(f"wrote release HMAC material to {output_dir}")
        return 0

    if args.command == "bootstrap-signed-ledger":
        if args.verifier_only and args.scheme != "ed25519":
            raise SatRootError("--verifier-only is only supported for ed25519 bundles")
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        bundle = bootstrap_signed_ledger_bundle(
            events,
            scheme=args.scheme,
            key_prefix=args.key_prefix,
            key_suffix=args.key_suffix,
            include_state_hash=not args.no_state_hash,
            include_annotation=not args.no_annotated_output,
        )
        output = _write_bundle_output_dir(
            bundle,
            output_dir=args.output_dir,
            include_private_keys=not args.verifier_only,
        )
        print(f"wrote signed SATROOT-1 {args.scheme} bundle to {Path(output['output_dir'])}")
        return 0

    if args.command == "bundle-summary":
        summary = summarize_signed_ledger_bundle(args.bundle_dir)
        print(canonical_json(summary))
        return 0

    if args.command == "bundle-lint":
        report = lint_signed_ledger_bundle(args.bundle_dir)
        print(canonical_json(report))
        return 0 if report["ok"] else 1

    if args.command == "release-summary":
        summary = summarize_signed_release_publication(args.release_dir)
        print(canonical_json(summary))
        return 0

    if args.command == "release-lint":
        report = lint_signed_release_publication(args.release_dir)
        print(canonical_json(report))
        return 0 if report["ok"] else 1

    if args.command == "release-catalog-summary":
        summary = summarize_signed_release_catalog_publication(args.release_catalog_dir)
        print(canonical_json(summary))
        return 0

    if args.command == "release-catalog-lint":
        report = lint_signed_release_catalog_publication(args.release_catalog_dir)
        print(canonical_json(report))
        return 0 if report["ok"] else 1

    if args.command == "release-catalog-index-summary":
        summary = summarize_signed_release_catalog_index_publication(args.release_catalog_index_dir)
        print(canonical_json(summary))
        return 0

    if args.command == "release-catalog-index-lint":
        report = lint_signed_release_catalog_index_publication(args.release_catalog_index_dir)
        print(canonical_json(report))
        return 0 if report["ok"] else 1

    if args.command == "publication-descriptor-index-summary":
        summary = summarize_publication_descriptor_index_publication(args.publication_descriptor_index_dir)
        print(canonical_json(summary))
        return 0

    if args.command == "publication-descriptor-index-lint":
        report = lint_publication_descriptor_index_publication(args.publication_descriptor_index_dir)
        print(canonical_json(report))
        return 0 if report["ok"] else 1

    if args.command == "demo-catalog-summary":
        summary = summarize_demo_catalog_workspace(args.demo_catalog_dir)
        print(canonical_json(summary))
        return 0

    if args.command == "demo-catalog-lint":
        report = lint_demo_catalog_workspace(args.demo_catalog_dir)
        print(canonical_json(report))
        return 0 if report["ok"] else 1

    if args.command == "publication-stack-summary":
        summary = summarize_publication_stack_workspace(args.publication_stack_dir)
        print(canonical_json(summary))
        return 0

    if args.command == "publication-stack-lint":
        report = lint_publication_stack_workspace(args.publication_stack_dir)
        print(canonical_json(report))
        return 0 if report["ok"] else 1

    if args.command == "publication-network-summary":
        summary = summarize_publication_network_workspace(args.publication_network_dir)
        print(canonical_json(summary))
        return 0

    if args.command == "publication-network-lint":
        report = lint_publication_network_workspace(args.publication_network_dir)
        print(canonical_json(report))
        return 0 if report["ok"] else 1

    if args.command == "publication-registry-workspace-summary":
        summary = summarize_publication_registry_workspace(args.publication_registry_workspace_dir)
        print(canonical_json(summary))
        return 0

    if args.command == "publication-registry-workspace-lint":
        report = lint_publication_registry_workspace(args.publication_registry_workspace_dir)
        print(canonical_json(report))
        return 0 if report["ok"] else 1

    if args.command == "publication-registry-summary":
        summary = summarize_publication_registry_publication(args.publication_registry_dir)
        print(canonical_json(summary))
        return 0

    if args.command == "publication-registry-lint":
        report = lint_publication_registry_publication(args.publication_registry_dir)
        print(canonical_json(report))
        return 0 if report["ok"] else 1

    if args.command == "build-bundle-index":
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        release_metadata = {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }
        bundle_dirs = resolve_bundle_directory_inputs(
            args.bundle_dir,
            discover_under=args.discover_under,
            recursive=not args.non_recursive,
        )
        index = build_signed_ledger_bundle_index(bundle_dirs, base_dir=base_dir, release_metadata=release_metadata)
        _write_output(index, output_path)
        return 0

    if args.command == "build-release-manifest":
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        signer = _release_manifest_signer_from_args(args)
        manifest = build_signed_release_manifest(
            args.bundle_index_json,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            signer=signer,
            base_dir=base_dir,
        )
        _write_output(manifest, output_path)
        return 0

    if args.command == "build-release-catalog":
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        preset = load_release_catalog_preset(args.preset_json) if args.preset_json else None
        catalog_metadata = dict((preset or {}).get("catalog_metadata", {}))
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                catalog_metadata[key] = value
        release_dirs = resolve_release_directory_inputs(
            [*(preset or {}).get("release_dirs", []), *args.release_dir],
            discover_under=[*((preset or {}).get("discover_under", [])), *(args.discover_under or [])],
            recursive=False if args.non_recursive else (preset or {}).get("recursive", True),
        )
        catalog = build_signed_release_catalog(release_dirs, base_dir=base_dir, catalog_metadata=catalog_metadata)
        _write_output(catalog, output_path)
        return 0

    if args.command == "build-release-catalog-manifest":
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        signer = _release_manifest_signer_from_args(args)
        manifest = build_signed_release_catalog_manifest(
            args.release_catalog_json,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            signer=signer,
            base_dir=base_dir,
        )
        _write_output(manifest, output_path)
        return 0

    if args.command == "build-release-catalog-index":
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        preset = load_release_catalog_index_preset(args.preset_json) if args.preset_json else None
        index_metadata = dict((preset or {}).get("index_metadata", {}))
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                index_metadata[key] = value
        release_catalog_dirs = resolve_release_catalog_directory_inputs(
            [*(preset or {}).get("release_catalog_dirs", []), *args.release_catalog_dir],
            discover_under=[*((preset or {}).get("discover_under", [])), *(args.discover_under or [])],
            recursive=False if args.non_recursive else (preset or {}).get("recursive", True),
        )
        index = build_signed_release_catalog_index(
            release_catalog_dirs,
            base_dir=base_dir,
            index_metadata=index_metadata,
        )
        _write_output(index, output_path)
        return 0

    if args.command == "build-release-catalog-index-manifest":
        output_path = args.output
        base_dir = Path(output_path).resolve().parent if output_path else Path.cwd()
        signer = _release_manifest_signer_from_args(args)
        manifest = build_signed_release_catalog_index_manifest(
            args.release_catalog_index_json,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            signer=signer,
            base_dir=base_dir,
        )
        _write_output(manifest, output_path)
        return 0

    if args.command == "publish-release":
        signer = _release_manifest_signer_from_args(args)
        release_metadata = {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }
        bundle_dirs = resolve_bundle_directory_inputs(
            args.bundle_dir,
            discover_under=args.discover_under,
            recursive=not args.non_recursive,
        )
        published = publish_signed_release(
            bundle_dirs,
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            signer=signer,
            release_metadata=release_metadata,
        )
        print(f"wrote SATROOT release publication to {Path(published['release_manifest_path']).parent}")
        return 0

    if args.command == "publish-release-catalog":
        signer = _release_manifest_signer_from_args(args)
        preset = load_release_catalog_preset(args.preset_json) if args.preset_json else None
        catalog_metadata = dict((preset or {}).get("catalog_metadata", {}))
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                catalog_metadata[key] = value
        release_dirs = resolve_release_directory_inputs(
            [*(preset or {}).get("release_dirs", []), *args.release_dir],
            discover_under=[*((preset or {}).get("discover_under", [])), *(args.discover_under or [])],
            recursive=False if args.non_recursive else (preset or {}).get("recursive", True),
        )
        published = publish_signed_release_catalog(
            release_dirs,
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            signer=signer,
            catalog_metadata=catalog_metadata,
        )
        print(f"wrote SATROOT release catalog publication to {Path(published['release_catalog_manifest_path']).parent}")
        return 0

    if args.command == "publish-release-catalog-index":
        signer = _release_manifest_signer_from_args(args)
        preset = load_release_catalog_index_preset(args.preset_json) if args.preset_json else None
        index_metadata = dict((preset or {}).get("index_metadata", {}))
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                index_metadata[key] = value
        release_catalog_dirs = resolve_release_catalog_directory_inputs(
            [*(preset or {}).get("release_catalog_dirs", []), *args.release_catalog_dir],
            discover_under=[*((preset or {}).get("discover_under", [])), *(args.discover_under or [])],
            recursive=False if args.non_recursive else (preset or {}).get("recursive", True),
        )
        published = publish_signed_release_catalog_index(
            release_catalog_dirs,
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            signer=signer,
            index_metadata=index_metadata,
        )
        print(f"wrote SATROOT release catalog index publication to {Path(published['release_catalog_index_manifest_path']).parent}")
        return 0

    if args.command == "bootstrap-release-publication":
        release_metadata = {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }
        bundle_dirs = resolve_bundle_directory_inputs(
            args.bundle_dir,
            discover_under=args.discover_under,
            recursive=not args.non_recursive,
        )
        published = bootstrap_release_publication(
            bundle_dirs,
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            release_metadata=release_metadata,
        )
        print(f"wrote bootstrapped SATROOT release publication to {Path(published['release_manifest_path']).parent}")
        return 0

    if args.command == "bootstrap-release-catalog-publication":
        preset = load_release_catalog_preset(args.preset_json) if args.preset_json else None
        catalog_metadata = dict((preset or {}).get("catalog_metadata", {}))
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                catalog_metadata[key] = value
        release_dirs = resolve_release_directory_inputs(
            [*(preset or {}).get("release_dirs", []), *args.release_dir],
            discover_under=[*((preset or {}).get("discover_under", [])), *(args.discover_under or [])],
            recursive=False if args.non_recursive else (preset or {}).get("recursive", True),
        )
        published = bootstrap_release_catalog_publication(
            release_dirs,
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            catalog_metadata=catalog_metadata,
        )
        print(f"wrote bootstrapped SATROOT release catalog publication to {Path(published['release_catalog_manifest_path']).parent}")
        return 0

    if args.command == "bootstrap-release-catalog-index-publication":
        preset = load_release_catalog_index_preset(args.preset_json) if args.preset_json else None
        index_metadata = dict((preset or {}).get("index_metadata", {}))
        for key, value in {
            "channel": args.channel,
            "label": args.label,
            "published_at": args.published_at,
        }.items():
            if value is not None:
                index_metadata[key] = value
        release_catalog_dirs = resolve_release_catalog_directory_inputs(
            [*(preset or {}).get("release_catalog_dirs", []), *args.release_catalog_dir],
            discover_under=[*((preset or {}).get("discover_under", [])), *(args.discover_under or [])],
            recursive=False if args.non_recursive else (preset or {}).get("recursive", True),
        )
        published = bootstrap_release_catalog_index_publication(
            release_catalog_dirs,
            output_dir=args.output_dir,
            signature_scheme=args.scheme,
            key_id=args.key_id,
            index_metadata=index_metadata,
        )
        print(f"wrote bootstrapped SATROOT release catalog index publication to {Path(published['release_catalog_index_manifest_path']).parent}")
        return 0

    if args.command == "verify-bundle":
        summary = verify_signed_ledger_bundle(args.bundle_dir)
        print(canonical_json(summary))
        return 0

    if args.command == "verify-release-manifest":
        manifest = _load_json_object_file(args.release_manifest_json, label="release-manifest")
        verifier = _release_manifest_verifier_from_args(args, manifest)
        summary = verify_signed_release_manifest(args.release_manifest_json, verifier=verifier)
        print(canonical_json(summary))
        return 0

    if args.command == "verify-release-catalog-manifest":
        manifest = _load_json_object_file(args.release_catalog_manifest_json, label="release-catalog-manifest")
        verifier = _release_manifest_verifier_from_args(args, manifest)
        summary = verify_signed_release_catalog_manifest(args.release_catalog_manifest_json, verifier=verifier)
        print(canonical_json(summary))
        return 0

    if args.command == "verify-release-catalog-index-manifest":
        manifest = _load_json_object_file(args.release_catalog_index_manifest_json, label="release-catalog-index-manifest")
        verifier = _release_manifest_verifier_from_args(args, manifest)
        summary = verify_signed_release_catalog_index_manifest(args.release_catalog_index_manifest_json, verifier=verifier)
        print(canonical_json(summary))
        return 0

    if args.command == "verify-publication-descriptor-index-manifest":
        manifest = _load_json_object_file(args.publication_descriptor_index_manifest_json, label="publication-descriptor-index-manifest")
        verifier = _release_manifest_verifier_from_args(args, manifest)
        summary = verify_signed_publication_descriptor_index_manifest(args.publication_descriptor_index_manifest_json, verifier=verifier)
        print(canonical_json(summary))
        return 0

    if args.command == "verify-publication-metadata-manifest":
        manifest = _load_json_object_file(args.publication_metadata_manifest_json, label="publication-metadata-manifest")
        verifier = _release_manifest_verifier_from_args(args, manifest)
        summary = verify_signed_publication_metadata_manifest(args.publication_metadata_manifest_json, verifier=verifier)
        print(canonical_json(summary))
        return 0

    if args.command == "verify-publication-metadata-catalog-manifest":
        manifest = _load_json_object_file(args.publication_metadata_catalog_manifest_json, label="publication-metadata-catalog-manifest")
        verifier = _release_manifest_verifier_from_args(args, manifest)
        summary = verify_signed_publication_metadata_catalog_manifest(args.publication_metadata_catalog_manifest_json, verifier=verifier)
        print(canonical_json(summary))
        return 0

    if args.command == "verify-publication-registry-manifest":
        manifest = _load_json_object_file(args.publication_registry_manifest_json, label="publication-registry-manifest")
        verifier = _release_manifest_verifier_from_args(args, manifest)
        summary = verify_signed_publication_registry_manifest(args.publication_registry_manifest_json, verifier=verifier)
        print(canonical_json(summary))
        return 0

    if args.command == "bootstrap-ed25519-workflow":
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        material = bootstrap_ed25519_workflow(events, key_prefix=args.key_prefix, key_suffix=args.key_suffix)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json_file(output_dir / "signer_key_map.json", material["signer_key_map"])
        _write_json_file(output_dir / "private_keys.json", material["private_keys"])
        _write_json_file(output_dir / "public_keys.json", material["public_keys"])
        print(f"wrote Ed25519 workflow files to {output_dir}")
        return 0

    if args.command == "bootstrap-release-ed25519":
        key_ids = list(args.key_ids or [])
        material = bootstrap_release_ed25519_material(key_ids)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json_file(output_dir / "release_private_keys.json", material["private_keys"])
        _write_json_file(output_dir / "release_public_keys.json", material["public_keys"])
        print(f"wrote release Ed25519 material to {output_dir}")
        return 0

    if args.command == "generate-ed25519-private-keys":
        key_ids = list(args.key_ids or [])
        if args.signer_key_map_json:
            signer_key_map = _load_json_object_file(args.signer_key_map_json, label="signer-key-map-json")
            for key_id in signer_key_map.values():
                if key_id not in key_ids:
                    key_ids.append(key_id)
        private_keys = generate_ed25519_private_keys(key_ids)
        _write_output(private_keys, args.output)
        return 0

    if args.command == "derive-ed25519-public-keys":
        private_keys = _load_json_object_file(args.private_keys_json, label="private-keys-json")
        public_keys = derive_ed25519_public_keys(private_keys)
        _write_output(public_keys, args.output)
        return 0

    if args.command == "annotate-ledger":
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        annotated_ledger = annotate_ledger_events(
            events,
            verifier=_verifier_from_args(args),
            include_event_id=not args.no_event_id,
            include_state_hash=not args.no_state_hash,
        )
        _write_output(annotated_ledger, args.output)
        return 0

    if args.command == "sign-event":
        event = _load_json_file(args.event_json)
        if not isinstance(event, dict):
            raise SatRootError("event_json must contain a JSON object")
        if args.scheme == "demo":
            signed = sign_event_record(event, scheme="demo")
        elif args.scheme == "hmac-sha256":
            if not args.secret or not args.key_id:
                raise SatRootError("--secret and --key-id are required for hmac-sha256")
            signed = sign_event_record(
                event,
                scheme="hmac-sha256",
                key_id=args.key_id,
                signer=make_hmac_sha256_signer({args.key_id: args.secret}),
            )
        elif args.scheme == "ed25519":
            if not args.private_key_hex or not args.key_id:
                raise SatRootError("--private-key-hex and --key-id are required for ed25519")
            signed = sign_event_record(
                event,
                scheme="ed25519",
                key_id=args.key_id,
                signer=make_ed25519_signer({args.key_id: args.private_key_hex}),
            )
        else:
            raise SatRootError(f"unsupported scheme: {args.scheme}")
        _write_output(signed, args.output)
        return 0

    if args.command == "sign-ledger":
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        signer, verifier, _ = _signer_and_verifier_from_args(args)
        signer_key_ids = None
        if args.scheme != "demo":
            if not args.signer_key_map_json:
                raise SatRootError("--signer-key-map-json is required for non-demo ledger signing")
            signer_key_ids = _load_json_file(args.signer_key_map_json)
            if not isinstance(signer_key_ids, dict):
                raise SatRootError("signer-key-map-json must contain an object")
        signed_ledger = sign_ledger_events(
            events,
            scheme=args.scheme,
            signer_key_ids=signer_key_ids,
            signer=signer,
            verifier=verifier,
            include_state_hash=args.include_state_hash,
        )
        _write_output(signed_ledger, args.output)
        return 0

    raise SatRootError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
