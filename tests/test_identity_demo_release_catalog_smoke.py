from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot_identity_demo_release_catalog_smoke import run_identity_demo_release_catalog_smoke


def test_run_identity_demo_release_catalog_smoke_builds_collection_and_catalog(tmp_path):
    report = run_identity_demo_release_catalog_smoke(tmp_path / "identity_demo_release_catalog_smoke")

    assert report["ok"] is True
    assert report["profile"] == "SATROOT-IDENTITY-1"
    assert report["generated_release_count"] == 2
    assert report["generated_profiles"] == ["SATROOT-IDENTITY-1"]
    assert report["release_collection"]["release_count"] == 2
    assert report["release_collection"]["bundle_symbols"] == ["IDCAT01", "IDCAT02"]
    assert report["release_catalog_publication"]["release_count"] == 2
    assert report["release_catalog_publication"]["catalog"]["label"] == "Identity Demo Release Catalog Smoke"
    assert report["release_collection_lint"]["ok"] is True
    assert report["release_catalog_publication_lint"]["ok"] is True
    assert Path(report["release_catalog_publication"]["release_catalog_manifest_path"]).is_file()
    assert Path(report["report_path"]).is_file()


def test_repo_local_identity_demo_release_catalog_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_identity_demo_release_catalog_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_identity_demo_release_catalog_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_identity_demo_release_catalog_smoke",
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
