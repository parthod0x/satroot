from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot_receipt_profile_smoke import run_receipt_profile_smoke


def test_run_receipt_profile_smoke_builds_full_registry_workspace(tmp_path):
    report = run_receipt_profile_smoke(tmp_path / "receipt_profile_smoke")

    assert report["ok"] is True
    assert report["ledger_replay"]["profile"] == "SATROOT-RECEIPT-1"
    assert report["ledger_replay"]["profile_mode"] == "single-receipt"
    assert report["ledger_replay"]["document_type"] == "invoice-receipt"
    assert report["ledger_replay"]["reference_id"] == "INV-2026-0001"
    assert report["ledger_replay"]["settlement_unit"] == "USD"
    assert report["demo_catalog_workspace_lint"]["ok"] is True
    assert report["publication_catalog_workspace_lint"]["ok"] is True
    assert report["publication_network_workspace_lint"]["ok"] is True
    assert report["publication_registry_workspace_lint"]["ok"] is True
    assert Path(report["publication_registry_workspace"]["publication_registry_manifest_path"]).is_file()
    assert Path(report["report_path"]).is_file()


def test_repo_local_receipt_profile_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_receipt_profile_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_receipt_profile_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_receipt_profile_smoke",
            "--output-dir",
            str(tmp_path / "module_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(repo_root / "src"),
        },
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout
