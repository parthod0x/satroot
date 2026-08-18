from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot_profile_federation_smoke import run_profile_federation_smoke


def test_run_profile_federation_smoke_builds_federated_outputs_and_collections(tmp_path):
    report = run_profile_federation_smoke(tmp_path / "profile_federation_smoke")

    assert report["ok"] is True
    assert report["profile_matrix"]["ok"] is True
    assert report["profile_matrix"]["profile_count"] == 5
    assert report["demo_catalog_workspace_collection"]["workspace_count"] == 5
    assert report["publication_stack_workspace"]["workspace_count"] == 5
    assert report["publication_stack_collection"]["stack_count"] == 5
    assert report["publication_network_workspace"]["stack_count"] == 1
    assert report["publication_catalog_workspace"]["artifact_count"] == 15
    assert report["federated_publication_catalog_workspace_collection"]["workspace_count"] == 1
    assert report["publication_registry_workspace"]["artifact_count"] == 15
    assert report["federated_publication_registry_workspace_collection"]["workspace_count"] == 1
    assert report["publication_network_collection"]["network_count"] == 5
    assert report["publication_catalog_workspace_collection"]["workspace_count"] == 5
    assert report["publication_registry_workspace_collection"]["workspace_count"] == 5
    assert report["demo_catalog_workspace_collection_lint"]["ok"] is True
    assert report["publication_stack_workspace_lint"]["ok"] is True
    assert report["publication_stack_collection_lint"]["ok"] is True
    assert report["publication_network_workspace_lint"]["ok"] is True
    assert report["publication_catalog_workspace_lint"]["ok"] is True
    assert report["federated_publication_catalog_workspace_collection_lint"]["ok"] is True
    assert report["publication_registry_workspace_lint"]["ok"] is True
    assert report["federated_publication_registry_workspace_collection_lint"]["ok"] is True
    assert report["publication_network_collection_lint"]["ok"] is True
    assert report["publication_catalog_workspace_collection_lint"]["ok"] is True
    assert report["publication_registry_workspace_collection_lint"]["ok"] is True
    assert Path(report["report_path"]).is_file()


def test_repo_local_profile_federation_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_profile_federation_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_profile_federation_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_profile_federation_smoke",
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
