from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from satroot1 import SatRootError, replay, scaffold_genesis_record
from satroot_event_profile_smoke import run_event_profile_smoke


def test_run_event_profile_smoke_builds_full_registry_workspace(tmp_path):
    report = run_event_profile_smoke(tmp_path / "event_profile_smoke")

    assert report["ok"] is True
    assert report["ledger_replay"]["profile"] == "SATROOT-EVENT-1"
    assert report["ledger_replay"]["profile_mode"] == "single-stream"
    assert report["ledger_replay"]["symbol"] == "EVENT1"
    assert report["ledger_replay"]["stream_type"] == "telemetry-stream"
    assert report["ledger_replay"]["sequence_policy"] == "append-only"
    assert report["ledger_replay"]["balances"]["successor_publisher"] == 1
    assert report["demo_catalog_workspace_lint"]["ok"] is True
    assert report["publication_catalog_workspace_lint"]["ok"] is True
    assert report["publication_network_workspace_lint"]["ok"] is True
    assert report["publication_registry_workspace_lint"]["ok"] is True
    assert Path(report["publication_registry_workspace"]["publication_registry_manifest_path"]).is_file()
    assert Path(report["report_path"]).is_file()


def test_event_example_ledger_validates_against_schema():
    repo_root = Path(__file__).resolve().parents[1]
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (repo_root / "protocol" / "satroot1.schema.json").read_text(encoding="utf-8")
    )
    events = json.loads(
        (repo_root / "examples" / "events_event1.json").read_text(encoding="utf-8")
    )
    for event in events:
        jsonschema.validate(event, schema)
    state = replay(events)
    assert state.profile == "SATROOT-EVENT-1"
    assert state.profile_mode == "single-stream"


def test_event_profile_genesis_rejects_bad_fields():
    with pytest.raises(SatRootError):
        scaffold_genesis_record(
            symbol="EVENT1",
            name="SATROOT Telemetry Stream",
            profile="SATROOT-EVENT-1",
            profile_fields={
                "stream_type": "NOT VALID!",
                "stream_subject": "stream-0001",
                "publisher_entity": "issuer-co",
                "sequence_policy": "append-only",
                "intended_use": "event-stream-ledger",
            },
        )


def test_repo_local_event_profile_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_event_profile_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_event_profile_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_event_profile_smoke",
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
