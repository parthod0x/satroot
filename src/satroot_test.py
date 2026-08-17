from __future__ import annotations

import argparse
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pytest nodeids in ordered chunks to avoid long single-process runs."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["tests"],
        help="Test paths to collect from. Defaults to the full tests/ tree.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100,
        help="Maximum number of collected nodeids to run per pytest invocation.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="1-based starting test index after collection.",
    )
    parser.add_argument(
        "--stop",
        type=int,
        default=None,
        help="1-based ending test index after collection.",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="Extra argument to pass through to each pytest run. Repeat as needed.",
    )
    return parser.parse_args()


def collect_nodeids(paths: list[str]) -> list[str]:
    command = [sys.executable, "-m", "pytest", "--collect-only", *paths]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)

    nodeids = [line.strip() for line in result.stdout.splitlines() if "::" in line]
    if not nodeids:
        raise SystemExit("no pytest nodeids collected")
    return nodeids


def select_nodeids(nodeids: list[str], *, start: int, stop: int | None) -> tuple[list[str], int, int]:
    total = len(nodeids)
    if start <= 0:
        raise ValueError("--start must be >= 1")
    if stop is not None and stop < start:
        raise ValueError("--stop must be >= --start")

    start_index = start - 1
    stop_index = total if stop is None else min(stop, total)
    if start_index >= total:
        raise ValueError(f"--start {start} is beyond collected test count {total}")

    return nodeids[start_index:stop_index], total, start_index


def build_pytest_command(*, extra_args: list[str], nodeids: list[str]) -> list[str]:
    return [sys.executable, "-m", "pytest", "-q", *extra_args, *nodeids]


def main() -> int:
    args = parse_args()
    if args.chunk_size <= 0:
        raise SystemExit("--chunk-size must be positive")

    nodeids = collect_nodeids(args.paths)
    try:
        selected, total, start_index = select_nodeids(nodeids, start=args.start, stop=args.stop)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print(
        f"collected {total} tests, running {len(selected)} "
        f"from {args.start} to {start_index + len(selected)} in chunks of {args.chunk_size}",
        flush=True,
    )

    for offset in range(0, len(selected), args.chunk_size):
        chunk = selected[offset : offset + args.chunk_size]
        chunk_start = args.start + offset
        chunk_stop = chunk_start + len(chunk) - 1
        print(f"running chunk {chunk_start}-{chunk_stop}", flush=True)
        command = build_pytest_command(extra_args=args.pytest_arg, nodeids=chunk)
        result = subprocess.run(command)
        if result.returncode != 0:
            rerun = " ".join(command)
            print(f"chunk failed: {chunk_start}-{chunk_stop}", flush=True)
            print(f"rerun with: {rerun}", flush=True)
            return result.returncode

    print("all chunks passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
