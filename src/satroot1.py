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


def _unique_workspace_names(paths: Sequence[str | Path]) -> list[str]:
    used: Dict[str, int] = {}
    names: list[str] = []
    for value in paths:
        stem = Path(value).stem or "workspace"
        count = used.get(stem, 0)
        used[stem] = count + 1
        names.append(stem if count == 0 else f"{stem}-{count + 1}")
    return names


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


def summarize_publication_stack_workspace(publication_stack_dir: str | Path) -> Dict[str, Any]:
    stack_path, summary = _load_workspace_summary(publication_stack_dir, label="publication stack")
    workspaces = summary.get("workspaces")
    if not isinstance(workspaces, list):
        raise SatRootError("publication stack summary workspaces must be an array")
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
    workspaces = summary.get("workspaces")
    if not isinstance(workspaces, list):
        raise SatRootError("publication stack summary workspaces must be an array")
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
        "release_catalog_lint": release_catalog_lint,
    }


def summarize_publication_network_workspace(publication_network_dir: str | Path) -> Dict[str, Any]:
    network_path, summary = _load_workspace_summary(publication_network_dir, label="publication network")
    workspaces = summary.get("workspaces")
    if not isinstance(workspaces, list):
        raise SatRootError("publication network summary workspaces must be an array")
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
    workspaces = summary.get("workspaces")
    if not isinstance(workspaces, list):
        raise SatRootError("publication network summary workspaces must be an array")
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

    publication_stack_summary_parser = subparsers.add_parser("publication-stack-summary", help="Read summary.json plus release_catalog/ and print a publication-stack summary without signature verification")
    publication_stack_summary_parser.add_argument("publication_stack_dir", help="Path to a SATROOT publication stack directory")

    publication_stack_lint_parser = subparsers.add_parser("publication-stack-lint", help="Check summary.json, release_catalog/, and referenced catalog workspace summaries without signature verification")
    publication_stack_lint_parser.add_argument("publication_stack_dir", help="Path to a SATROOT publication stack directory")

    publication_network_summary_parser = subparsers.add_parser("publication-network-summary", help="Read summary.json plus release_catalog_index/ and print a publication-network summary without signature verification")
    publication_network_summary_parser.add_argument("publication_network_dir", help="Path to a SATROOT publication network directory")

    publication_network_lint_parser = subparsers.add_parser("publication-network-lint", help="Check summary.json, release_catalog_index/, and referenced publication stack summaries without signature verification")
    publication_network_lint_parser.add_argument("publication_network_dir", help="Path to a SATROOT publication network directory")

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
