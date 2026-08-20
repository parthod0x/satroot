from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot_federated_registry_collection_smoke import run_federated_registry_collection_smoke


def test_run_federated_registry_collection_smoke_builds_collection_backed_registry_publications(tmp_path):
    report = run_federated_registry_collection_smoke(tmp_path / "federated_registry_collection_smoke")

    source_collection_dir = report["publication_registry_workspace_collection"]["collection_dir"]

    assert report["ok"] is True
    assert report["profile_federation"]["profile_count"] == 6
    assert report["publication_registry_workspace_collection"]["workspace_count"] == 1
    assert report["publication_registry_publication"]["component_count"] == 3
    assert report["publication_registry_publication"]["source_publication_registry_workspace_collection_dir"] == (
        source_collection_dir
    )
    assert (
        report["roundtrip_publication_registry_publication"][
            "source_publication_registry_workspace_collection_dir"
        ]
        == source_collection_dir
    )
    assert report["publication_registry_workspace_collection_lint"]["ok"] is True
    assert report["publication_registry_publication_lint"]["ok"] is True
    assert report["roundtrip_publication_registry_publication_lint"]["ok"] is True
    assert Path(report["publication_registry_preset_path"]).is_file()
    assert Path(report["exported_publication_registry_preset_path"]).is_file()
    assert Path(report["report_path"]).is_file()


def test_repo_local_federated_registry_collection_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_federated_registry_collection_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_federated_registry_collection_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_federated_registry_collection_smoke",
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
