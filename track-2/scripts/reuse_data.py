#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

ALLOWED = [Path("raw/dcgm.csv"), Path("raw/scheduler_data.csv"), Path("raw/LICENSE"), Path("raw/README.md"), Path("prepped/jobs.parquet"), Path("prepped/gpus.parquet"), Path("synthetic/resources.parquet"), Path("synthetic/edges.parquet"), Path("synthetic/findings.json")]


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reuse_data(source: Path, destination: Path, paths: list[Path] = ALLOWED) -> None:
    source, destination = source.resolve(), destination.resolve()
    copies = []
    for rel in paths:
        src, dst = source / rel, destination / rel
        if not src.is_file() or src.is_symlink():
            raise ValueError(f"missing or unsafe source: {rel}")
        if dst.exists():
            if not dst.is_file() or dst.is_symlink() or _digest(src) != _digest(dst):
                raise ValueError(f"destination conflict: {rel}")
        else:
            copies.append((src, dst))
    for src, dst in copies:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        reuse_data(args.source, args.destination)
    except ValueError as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__": main()
