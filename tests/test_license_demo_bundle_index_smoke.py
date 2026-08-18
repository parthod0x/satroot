from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot_license_demo_bundle_index_smoke import run_license_demo_bundle_index_smoke


def test_run_license_demo_bundle_index_smoke_builds_collection_and_index(tmp_path):
    report = run_license_demo_bundle_index_smoke(tmp_path / "license_demo_bundle_index_smoke")

    assert report["ok"] is True
    assert report["profile"] == "SATROOT-LICENSE-1"
    assert report["generated_workspace_count"] == 2
    assert report["generated_bundle_count"] == 2
    assert report["bundle_collection"]["bundle_count"] == 2
    assert report["bundle_collection"]["bundle_symbols"] == ["LICBIDX01", "LICBIDX02"]
    assert report["bundle_index"]["bundle_count"] == 2
    assert report["bundle_index"]["release"]["label"] == "License Demo Bundle Index Smoke"
    assert report["bundle_collection_lint"]["ok"] is True
    assert report["bundle_index_lint"]["ok"] is True
    assert Path(report["bundle_index"]["bundle_index_path"]).is_file()
    assert Path(report["report_path"]).is_file()


def test_repo_local_license_demo_bundle_index_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_license_demo_bundle_index_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_license_demo_bundle_index_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_license_demo_bundle_index_smoke",
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
