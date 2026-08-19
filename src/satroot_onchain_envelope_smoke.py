from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from satroot1 import SatRootError, validate_root_id
from satroot_anchored_demo_smoke import PLACEHOLDER_ROOT_ID


PROTOCOL_TAG = b"SATROOT1"
CONTENT_TYPE = "application/satroot1+json"
OP_FALSE = 0x00
OP_RETURN = 0x6A
OP_PUSHDATA1 = 0x4C
OP_PUSHDATA2 = 0x4D
PLACEHOLDER_STATE_HASH = "sha256:" + "0" * 64


def encode_push(data: bytes) -> bytes:
    length = len(data)
    if length == 0:
        raise SatRootError("empty envelope push")
    if length <= 0x4B:
        return bytes([length]) + data
    if length <= 0xFF:
        return bytes([OP_PUSHDATA1, length]) + data
    if length <= 0xFFFF:
        return bytes([OP_PUSHDATA2]) + length.to_bytes(2, "little") + data
    raise SatRootError("envelope push larger than 65535 bytes is not supported")


def build_envelope_payload(root_id: str, state_hash: str) -> bytes:
    validate_root_id(root_id)
    if not (
        state_hash.startswith("sha256:")
        and len(state_hash) == len("sha256:") + 64
        and all(c in "0123456789abcdef" for c in state_hash[len("sha256:"):])
    ):
        raise SatRootError(f"invalid state_hash for envelope payload: {state_hash}")
    payload = {
        "protocol": "SATROOT-1",
        "root_id": root_id,
        "state_hash": state_hash,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_envelope_script(content_type: str, payload: bytes) -> bytes:
    return (
        bytes([OP_FALSE, OP_RETURN])
        + encode_push(PROTOCOL_TAG)
        + encode_push(content_type.encode("utf-8"))
        + encode_push(payload)
    )


def parse_envelope_script(script: bytes) -> dict[str, Any]:
    if len(script) < 2 or script[0] != OP_FALSE or script[1] != OP_RETURN:
        raise SatRootError("envelope script must start with OP_FALSE OP_RETURN")
    pushes: list[bytes] = []
    index = 2
    while index < len(script):
        opcode = script[index]
        index += 1
        if 1 <= opcode <= 0x4B:
            length = opcode
        elif opcode == OP_PUSHDATA1:
            length = script[index]
            index += 1
        elif opcode == OP_PUSHDATA2:
            length = int.from_bytes(script[index : index + 2], "little")
            index += 2
        else:
            raise SatRootError(f"unsupported opcode in envelope script: {opcode}")
        if index + length > len(script):
            raise SatRootError("truncated push in envelope script")
        pushes.append(script[index : index + length])
        index += length
    if len(pushes) != 3:
        raise SatRootError(f"envelope script must carry exactly 3 pushes, found {len(pushes)}")
    if pushes[0] != PROTOCOL_TAG:
        raise SatRootError("envelope script protocol tag is not SATROOT1")
    return {
        "protocol_tag": pushes[0].decode("utf-8"),
        "content_type": pushes[1].decode("utf-8"),
        "payload": json.loads(pushes[2].decode("utf-8")),
    }


def run_onchain_envelope_smoke(
    output_dir: str | Path,
    *,
    root_id: str = PLACEHOLDER_ROOT_ID,
    state_hash: str = PLACEHOLDER_STATE_HASH,
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    payload = build_envelope_payload(root_id, state_hash)
    script = build_envelope_script(CONTENT_TYPE, payload)
    decoded = parse_envelope_script(script)
    rebuilt = build_envelope_script(CONTENT_TYPE, build_envelope_payload(root_id, state_hash))

    checks = {
        "script_starts_with_op_false_op_return": script[:2] == bytes([OP_FALSE, OP_RETURN]),
        "roundtrip_protocol_tag": decoded["protocol_tag"] == PROTOCOL_TAG.decode("utf-8"),
        "roundtrip_content_type": decoded["content_type"] == CONTENT_TYPE,
        "roundtrip_payload_matches": decoded["payload"]
        == {"protocol": "SATROOT-1", "root_id": root_id, "state_hash": state_hash},
        "deterministic_rebuild": rebuilt == script,
    }

    report: dict[str, Any] = {
        "lane": "onchain-envelope",
        "content_type": CONTENT_TYPE,
        "root_id": root_id,
        "root_is_placeholder": root_id == PLACEHOLDER_ROOT_ID,
        "state_hash": state_hash,
        "envelope_script_hex": script.hex(),
        "envelope_script_length": len(script),
        "decoded_payload": decoded["payload"],
        "checks": checks,
    }
    report["ok"] = all(checks.values())

    (output_path / "envelope_script.hex").write_text(script.hex() + "\n", encoding="utf-8")
    (output_path / "envelope_payload.json").write_text(
        payload.decode("utf-8") + "\n", encoding="utf-8"
    )
    report_path = output_path / "onchain_envelope_smoke_report.json"
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
            "Build the SPEC section 4 on-chain envelope script (OP_FALSE OP_RETURN "
            '"SATROOT1" <content-type> <payload>) for a SATROOT namespace state '
            "commitment, fully offline and deterministically, and verify it decodes "
            "back to the same commitment."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_onchain_envelope_smoke_run",
        help="Directory where the envelope script, payload, and report will be written.",
    )
    parser.add_argument(
        "--root-id",
        default=PLACEHOLDER_ROOT_ID,
        help=(
            "Namespace root_id as <txid>:<vout>. Defaults to the demo placeholder; "
            "pass a real one-satoshi outpoint only when intentionally anchoring."
        ),
    )
    parser.add_argument(
        "--state-hash",
        default=PLACEHOLDER_STATE_HASH,
        help="Namespace semantic state hash to commit, as sha256:<64 hex>. Defaults to a placeholder.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_onchain_envelope_smoke(
        args.output_dir,
        root_id=args.root_id,
        state_hash=args.state_hash,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
