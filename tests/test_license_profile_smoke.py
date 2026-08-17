from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot_license_profile_smoke import run_license_profile_smoke


def test_run_license_profile_smoke_builds_full_registry_workspace(tmp_path):
    report = run_license_profile_smoke(tmp_path / "license_profile_smoke")

    assert report["ok"] is True
    assert report["ledger_replay"]["profile"] == "SATROOT-LICENSE-1"
    assert report["ledger_replay"]["profile_mode"] == "single-license"
    assert report["ledger_replay"]["license_type"] == "software-license"
    assert report["ledger_replay"]["asset_id"] == "sdk-pro-2026"
    assert report["ledger_replay"]["usage_scope"] == "production-api"
    assert report["demo_catalog_workspace_lint"]["ok"] is True
    assert report["publication_catalog_workspace_lint"]["ok"] is True
    assert report["publication_network_workspace_lint"]["ok"] is True
    assert report["publication_registry_workspace_lint"]["ok"] is True
    assert Path(report["publication_registry_workspace"]["publication_registry_manifest_path"]).is_file()
    assert Path(report["report_path"]).is_file()


def test_repo_local_license_profile_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_license_profile_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_license_profile_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_license_profile_smoke",
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
