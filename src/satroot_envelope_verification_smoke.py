from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from satroot1 import SatRootError
from satroot_anchored_demo_smoke import PLACEHOLDER_ROOT_ID
from satroot_onchain_envelope_smoke import (
    CONTENT_TYPE,
    OP_FALSE,
    OP_RETURN,
    PLACEHOLDER_STATE_HASH,
    build_envelope_payload,
    build_envelope_script,
    parse_envelope_script,
)


def _read_varint(data: bytes, index: int) -> tuple[int, int]:
    prefix = data[index]
    index += 1
    if prefix < 0xFD:
        return prefix, index
    if prefix == 0xFD:
        return int.from_bytes(data[index : index + 2], "little"), index + 2
    if prefix == 0xFE:
        return int.from_bytes(data[index : index + 4], "little"), index + 4
    return int.from_bytes(data[index : index + 8], "little"), index + 8


def parse_raw_transaction(raw: bytes) -> dict[str, Any]:
    """Parse the outputs of a serialized Bitcoin transaction, fully offline."""
    try:
        index = 4  # version
        input_count, index = _read_varint(raw, index)
        for _ in range(input_count):
            index += 36  # previous outpoint
            script_length, index = _read_varint(raw, index)
            index += script_length + 4  # script + sequence
        output_count, index = _read_varint(raw, index)
        outputs: list[dict[str, Any]] = []
        for n in range(output_count):
            value = int.from_bytes(raw[index : index + 8], "little")
            index += 8
            script_length, index = _read_varint(raw, index)
            script = raw[index : index + script_length]
            index += script_length
            outputs.append({"n": n, "satoshis": value, "script": script})
        index += 4  # locktime
    except IndexError as exc:
        raise SatRootError("truncated raw transaction") from exc
    if index != len(raw):
        raise SatRootError("trailing bytes after raw transaction")
    txid = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[::-1].hex()
    return {"txid": txid, "outputs": outputs}


def build_demo_transaction(envelope_script: bytes) -> bytes:
    """Build a minimal, offline demo transaction carrying the envelope in output 0."""
    raw = (1).to_bytes(4, "little")
    raw += b"\x01" + b"\x00" * 32 + (0xFFFFFFFF).to_bytes(4, "little") + b"\x00"
    raw += (0xFFFFFFFF).to_bytes(4, "little")
    raw += b"\x02"
    raw += (0).to_bytes(8, "little") + len(envelope_script).to_bytes(1, "little") + envelope_script
    dummy_p2pkh = bytes.fromhex("76a914") + b"\x00" * 20 + bytes.fromhex("88ac")
    raw += (1).to_bytes(8, "little") + len(dummy_p2pkh).to_bytes(1, "little") + dummy_p2pkh
    raw += (0).to_bytes(4, "little")
    return raw


def run_envelope_verification_smoke(
    output_dir: str | Path,
    *,
    raw_tx_hex: str | None = None,
    root_id: str = PLACEHOLDER_ROOT_ID,
    state_hash: str = PLACEHOLDER_STATE_HASH,
    expected_txid: str | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    expected_payload = build_envelope_payload(root_id, state_hash)
    expected_script = build_envelope_script(CONTENT_TYPE, expected_payload)

    synthetic = raw_tx_hex is None
    if synthetic:
        raw = build_demo_transaction(expected_script)
    else:
        raw = bytes.fromhex(raw_tx_hex.strip())

    parsed = parse_raw_transaction(raw)
    envelope_outputs = [
        entry
        for entry in parsed["outputs"]
        if entry["script"][:2] == bytes([OP_FALSE, OP_RETURN])
    ]
    decoded = None
    decode_error = None
    if len(envelope_outputs) == 1:
        try:
            decoded = parse_envelope_script(envelope_outputs[0]["script"])
        except SatRootError as exc:
            decode_error = str(exc)

    checks = {
        "raw_transaction_parsed": True,
        "exactly_one_envelope_output": len(envelope_outputs) == 1,
        "envelope_output_value_zero": bool(envelope_outputs)
        and envelope_outputs[0]["satoshis"] == 0,
        "envelope_decodes": decoded is not None,
        "commitment_matches": decoded is not None
        and decoded["payload"]
        == {"protocol": "SATROOT-1", "root_id": root_id, "state_hash": state_hash}
        and decoded["content_type"] == CONTENT_TYPE,
        "script_byte_identical_to_rebuild": bool(envelope_outputs)
        and envelope_outputs[0]["script"] == expected_script,
        "txid_matches_expected": expected_txid is None
        or parsed["txid"] == expected_txid.lower(),
    }

    report: dict[str, Any] = {
        "lane": "envelope-verification",
        "synthetic_transaction": synthetic,
        "root_id": root_id,
        "root_is_placeholder": root_id == PLACEHOLDER_ROOT_ID,
        "state_hash": state_hash,
        "computed_txid": parsed["txid"],
        "expected_txid": expected_txid,
        "output_count": len(parsed["outputs"]),
        "envelope_output_index": envelope_outputs[0]["n"] if envelope_outputs else None,
        "decode_error": decode_error,
        "checks": checks,
    }
    report["ok"] = all(checks.values())

    report_path = output_path / "envelope_verification_smoke_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report["report_path"] = str(report_path)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify, fully offline, that a serialized transaction carries the SPEC "
            "section 4 SATROOT1 envelope committing a namespace root_id and state "
            "hash. With no raw transaction supplied, a synthetic demo transaction "
            "is built and verified in place."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_envelope_verification_smoke_run",
        help="Directory where the verification report will be written.",
    )
    parser.add_argument(
        "--raw-tx-hex-file",
        default=None,
        help=(
            "Path to a file holding the raw transaction hex, fetched by the operator "
            "out-of-band. Omit to verify a synthetic offline demo transaction."
        ),
    )
    parser.add_argument(
        "--root-id",
        default=PLACEHOLDER_ROOT_ID,
        help=(
            "Namespace root_id as <txid>:<vout>. Defaults to the demo placeholder; "
            "pass a real one-satoshi outpoint only when verifying a real envelope."
        ),
    )
    parser.add_argument(
        "--state-hash",
        default=PLACEHOLDER_STATE_HASH,
        help="Committed semantic state hash, as sha256:<64 hex>. Defaults to a placeholder.",
    )
    parser.add_argument(
        "--expected-txid",
        default=None,
        help="Optional transaction id the raw bytes must hash to.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    raw_tx_hex = None
    if args.raw_tx_hex_file is not None:
        raw_tx_hex = Path(args.raw_tx_hex_file).read_text(encoding="utf-8")
    report = run_envelope_verification_smoke(
        args.output_dir,
        raw_tx_hex=raw_tx_hex,
        root_id=args.root_id,
        state_hash=args.state_hash,
        expected_txid=args.expected_txid,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
