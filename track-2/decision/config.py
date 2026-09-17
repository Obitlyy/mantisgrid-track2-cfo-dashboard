from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RuntimePaths:
    data_dir: Path
    output_dir: Path


def resolve_paths() -> RuntimePaths:
    official = Path(os.environ.get("MGAI_DATA_DIR", REPO_ROOT / "data")).expanduser().resolve()
    decision = Path(os.environ.get("TRACK2_DATA_DIR", official)).expanduser().resolve()
    if official != decision:
        raise ValueError("MGAI_DATA_DIR and TRACK2_DATA_DIR must resolve to the same directory")
    output = Path(os.environ.get("TRACK2_OUTPUT_DIR", REPO_ROOT / "out")).expanduser().resolve()
    return RuntimePaths(data_dir=decision, output_dir=output)
