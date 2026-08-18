from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot_operator_proof_smoke import run_operator_proof_smoke


DEFAULT_IMPORT_MODULES = [
    "satroot1",
    "satroot_collection_lint",
    "satroot_test",
    "satroot_release_gate_smoke",
    "satroot_operator_proof_smoke",
    "satroot_publication_ladder_smoke",
    "satroot_singleton_publication_ladder_smoke",
    "satroot_federated_registry_collection_smoke",
    "satroot_singleton_demo_bundle_index_matrix_smoke",
    "satroot_receipt_demo_bundle_index_smoke",
    "satroot_identity_demo_bundle_index_smoke",
    "satroot_license_demo_bundle_index_smoke",
    "satroot_singleton_demo_release_smoke_support",
    "satroot_singleton_demo_release_catalog_matrix_smoke",
    "satroot_receipt_demo_release_catalog_smoke",
    "satroot_identity_demo_release_catalog_smoke",
    "satroot_license_demo_release_catalog_smoke",
    "satroot_singleton_demo_release_catalog_index_matrix_smoke",
    "satroot_receipt_demo_release_catalog_index_smoke",
    "satroot_identity_demo_release_catalog_index_smoke",
    "satroot_license_demo_release_catalog_index_smoke",
    "satroot_demo_bundle_index_matrix_smoke",
    "satroot_stable_demo_bundle_index_smoke",
    "satroot_machine_demo_bundle_index_smoke",
    "satroot_demo_release_catalog_index_matrix_smoke",
    "satroot_stable_demo_release_catalog_index_smoke",
    "satroot_machine_demo_release_catalog_index_smoke",
    "satroot_demo_release_catalog_matrix_smoke",
    "satroot_stable_demo_release_catalog_smoke",
    "satroot_machine_demo_release_catalog_smoke",
    "satroot_profile_federation_smoke",
    "satroot_profile_matrix_smoke",
    "satroot_stable_profile_smoke",
    "satroot_machine_profile_smoke",
    "satroot_receipt_profile_smoke",
    "satroot_identity_profile_smoke",
    "satroot_license_profile_smoke",
]


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_import_smoke(module_names: Sequence[str]) -> dict[str, Any]:
    imported_modules: list[str] = []
    failed_modules: list[dict[str, str]] = []

    for module_name in module_names:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - exercised through failure handling
            failed_modules.append(
                {
                    "module": module_name,
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                }
            )
        else:
            imported_modules.append(module_name)

    return {
        "ok": not failed_modules,
        "module_count": len(module_names),
        "imported_modules": imported_modules,
        "failed_modules": failed_modules,
    }


def _run_chunked_pytest(
    *,
    repo_root: Path,
    output_dir: Path,
    chunk_size: int,
    start: int,
    stop: int | None,
    pytest_paths: Sequence[str],
    pytest_args: Sequence[str],
) -> dict[str, Any]:
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "chunked_pytest.log"

    command = [sys.executable, "-m", "satroot_test", *pytest_paths, "--chunk-size", str(chunk_size)]
    if start != 1:
        command.extend(["--start", str(start)])
    if stop is not None:
        command.extend(["--stop", str(stop)])
    for pytest_arg in pytest_args:
        command.extend(["--pytest-arg", pytest_arg])

    result = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    log_path.write_text(result.stdout + result.stderr, encoding="utf-8")

    return {
        "ok": result.returncode == 0,
        "command": command,
        "cwd": str(repo_root),
        "chunk_size": chunk_size,
        "start": start,
        "stop": stop,
        "pytest_paths": list(pytest_paths),
        "pytest_args": list(pytest_args),
        "returncode": result.returncode,
        "log_path": str(log_path.resolve()),
    }


def run_release_gate_smoke(
    output_dir: str | Path,
    *,
    bundle_scheme: str = "hmac-sha256",
    chunk_size: int = 100,
    start: int = 1,
    stop: int | None = None,
    pytest_paths: Sequence[str] | None = None,
    pytest_args: Sequence[str] | None = None,
    run_import_smoke: bool = True,
    run_operator_proof: bool = True,
    run_chunked_pytest: bool = True,
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[1]
    resolved_pytest_paths = list(pytest_paths or ["tests"])
    resolved_pytest_args = list(pytest_args or [])

    report: dict[str, Any] = {
        "bundle_scheme": bundle_scheme,
        "chunk_size": chunk_size,
        "start": start,
        "stop": stop,
        "pytest_paths": resolved_pytest_paths,
        "pytest_args": resolved_pytest_args,
        "repo_root": str(repo_root),
    }

    if run_import_smoke:
        report["import_smoke"] = _run_import_smoke(DEFAULT_IMPORT_MODULES)
    else:
        report["import_smoke"] = {"ok": True, "skipped": True}

    if run_operator_proof:
        report["operator_proof"] = run_operator_proof_smoke(
            output_path / "operator_proof",
            bundle_scheme=bundle_scheme,
        )
    else:
        report["operator_proof"] = {"ok": True, "skipped": True}

    if run_chunked_pytest:
        report["chunked_pytest"] = _run_chunked_pytest(
            repo_root=repo_root,
            output_dir=output_path,
            chunk_size=chunk_size,
            start=start,
            stop=stop,
            pytest_paths=resolved_pytest_paths,
            pytest_args=resolved_pytest_args,
        )
    else:
        report["chunked_pytest"] = {"ok": True, "skipped": True}

    report["ok"] = all(
        [
            report["import_smoke"]["ok"] is True,
            report["operator_proof"]["ok"] is True,
            report["chunked_pytest"]["ok"] is True,
        ]
    )

    report_path = output_path / "release_gate_smoke_report.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local SATROOT release gate: installed-module import smoke, "
            "top-level operator proof, and chunked pytest."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_release_gate_smoke_run",
        help="Directory where release-gate artifacts, logs, and the consolidated report will be written.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signature scheme for generated bundle and publication artifacts.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100,
        help="Maximum number of collected pytest nodeids to run per chunk.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="1-based starting test index passed through to satroot_test.",
    )
    parser.add_argument(
        "--stop",
        type=int,
        default=None,
        help="1-based ending test index passed through to satroot_test.",
    )
    parser.add_argument(
        "--pytest-path",
        action="append",
        default=[],
        help="Test path to pass through to satroot_test. Repeat as needed. Defaults to tests when omitted.",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="Extra argument to pass through to each chunked pytest invocation. Repeat as needed.",
    )
    parser.add_argument(
        "--skip-import-smoke",
        action="store_true",
        help="Skip the installed-module import smoke phase.",
    )
    parser.add_argument(
        "--skip-operator-proof",
        action="store_true",
        help="Skip the top-level operator-proof smoke phase.",
    )
    parser.add_argument(
        "--skip-chunked-pytest",
        action="store_true",
        help="Skip the chunked pytest phase.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_release_gate_smoke(
        args.output_dir,
        bundle_scheme=args.bundle_scheme,
        chunk_size=args.chunk_size,
        start=args.start,
        stop=args.stop,
        pytest_paths=args.pytest_path or None,
        pytest_args=args.pytest_arg or None,
        run_import_smoke=not args.skip_import_smoke,
        run_operator_proof=not args.skip_operator_proof,
        run_chunked_pytest=not args.skip_chunked_pytest,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
