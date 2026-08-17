from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence


def duplicate_nonempty_strings(values: Iterable[Any]) -> list[str]:
    counts: Dict[str, int] = {}
    for value in values:
        if isinstance(value, str) and value.strip():
            counts[value] = counts.get(value, 0) + 1
    return sorted(value for value, count in counts.items() if count > 1)


def append_collection_member_metadata_mismatch(
    mismatches: list[Dict[str, Any]],
    *,
    member_label: str,
    fields: Sequence[str],
) -> None:
    if fields:
        mismatches.append({"member": member_label, "fields": sorted(fields)})


def resolve_collection_member_dir(
    collection_path: Path,
    entry: Mapping[str, Any],
    *,
    name_key: str,
    dir_name_key: Optional[str] = None,
) -> Optional[Path]:
    member_name = entry.get(name_key)
    if not isinstance(member_name, str) or not member_name.strip():
        return None
    if dir_name_key is not None:
        member_dir_name = entry.get(dir_name_key)
        if isinstance(member_dir_name, str) and member_dir_name.strip():
            return (collection_path / member_name / member_dir_name).resolve()
    return (collection_path / member_name).resolve()


def lint_reusable_collection(
    collection_dir: str | Path,
    *,
    load_workspace_summary: Callable[..., tuple[Path, Dict[str, Any]]],
    label: str,
    validate_summary: Callable[[Mapping[str, Any]], None],
    count_key: str,
    source_dirs_key: str,
    member_dirs_key: str,
    members_key: str,
    member_name_key: str,
    member_dir_key: str,
    dir_name_key: Optional[str],
    child_lint: Callable[[str | Path], Dict[str, Any]],
    member_summary: Callable[[Path], Mapping[str, Any]],
    metadata_fields: Sequence[str],
    path_specs: Sequence[tuple[str, str, str, str]],
    duplicate_source_key: str,
    duplicate_member_dirs_key: str,
    duplicate_names_key: str,
    dir_path_mismatches_key: str,
    missing_member_dirs_key: str,
    metadata_mismatches_key: str,
    lint_failures_key: str,
) -> Dict[str, Any]:
    collection_path, summary = load_workspace_summary(collection_dir, label=label)
    validate_summary(summary)
    source_dirs = summary.get(source_dirs_key)
    member_dirs = summary.get(member_dirs_key)
    members = summary.get(members_key)
    assert isinstance(source_dirs, list)
    assert isinstance(member_dirs, list)
    assert isinstance(members, list)

    count_matches = isinstance(summary.get(count_key), int) and summary.get(count_key) == len(source_dirs) == len(member_dirs) == len(members)
    report: Dict[str, Any] = {
        "collection_dir": str(collection_path.resolve()),
        "summary_path": str((collection_path / "summary.json").resolve()),
        count_key: len(members),
        f"{count_key}_matches": count_matches,
        duplicate_source_key: duplicate_nonempty_strings(source_dirs),
        duplicate_member_dirs_key: duplicate_nonempty_strings(member_dirs),
        duplicate_names_key: duplicate_nonempty_strings(entry.get(member_name_key) for entry in members if isinstance(entry, Mapping)),
        dir_path_mismatches_key: [],
        missing_member_dirs_key: [],
        metadata_mismatches_key: [],
        lint_failures_key: [],
    }
    for field_name, _relative_path, duplicate_key, missing_key in path_specs:
        report[duplicate_key] = duplicate_nonempty_strings(entry.get(field_name) for entry in members if isinstance(entry, Mapping))
        report[f"{field_name}_mismatches"] = []
        report[missing_key] = []

    for entry in members:
        if not isinstance(entry, Mapping):
            continue
        member_name = entry.get(member_name_key)
        if not isinstance(member_name, str) or not member_name.strip():
            continue
        member_dir = resolve_collection_member_dir(collection_path, entry, name_key=member_name_key, dir_name_key=dir_name_key)
        if member_dir is None:
            continue
        if entry.get(member_dir_key) != str(member_dir):
            report[dir_path_mismatches_key].append(member_name)
        if not member_dir.is_dir():
            report[missing_member_dirs_key].append(member_name)
            continue

        missing_nested_path = False
        for field_name, relative_path, _duplicate_key, missing_key in path_specs:
            expected_path = (member_dir / relative_path).resolve()
            mismatch_key = f"{field_name}_mismatches"
            if entry.get(field_name) != str(expected_path):
                report[mismatch_key].append(member_name)
            if not expected_path.exists():
                report[missing_key].append(member_name)
                missing_nested_path = True
        if missing_nested_path:
            continue

        actual_summary = member_summary(member_dir)
        mismatched_fields = [field_name for field_name in metadata_fields if entry.get(field_name) != actual_summary.get(field_name)]
        append_collection_member_metadata_mismatch(
            report[metadata_mismatches_key],
            member_label=member_name,
            fields=mismatched_fields,
        )
        nested_report = child_lint(member_dir)
        if not nested_report["ok"]:
            report[lint_failures_key].append(member_name)

    report["ok"] = count_matches and not any(
        value for key, value in report.items() if key not in {"ok", "collection_dir", "summary_path", count_key, f"{count_key}_matches"}
    )
    return report
