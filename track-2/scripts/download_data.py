#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

URL = "https://mantisgrid-hackathon.s3.us-east-1.amazonaws.com/track-2-raw.zip"
NAMES = {"dcgm.csv", "scheduler_data.csv", "LICENSE", "README.md"}


def download_data(destination: Path, transport=urllib.request.urlretrieve) -> None:
    destination = destination.resolve()
    if all((destination / name).is_file() and (destination / name).stat().st_size for name in NAMES):
        return
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp)
        archive = tmp / "track-2-raw.zip"
        transport(URL, archive)
        with zipfile.ZipFile(archive) as bundle:
            if bundle.testzip() is not None:
                raise ValueError("downloaded ZIP is corrupt")
            infos = bundle.infolist()
            names = {item.filename for item in infos}
            if names != NAMES:
                raise ValueError("ZIP must contain exactly the four official top-level files")
            for item in infos:
                path = PurePosixPath(item.filename)
                mode = item.external_attr >> 16
                if path.is_absolute() or ".." in path.parts or len(path.parts) != 1 or stat.S_ISLNK(mode):
                    raise ValueError(f"unsafe ZIP member: {item.filename}")
            extracted = tmp / "extracted"
            bundle.extractall(extracted)
        for name in NAMES:
            target = destination / name
            if target.exists() and target.read_bytes() != (extracted / name).read_bytes():
                raise ValueError(f"destination conflict: {name}")
        destination.mkdir(parents=True, exist_ok=True)
        for name in NAMES:
            target = destination / name
            if not target.exists(): shutil.copy2(extracted / name, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try: download_data(args.destination)
    except (OSError, ValueError, zipfile.BadZipFile) as exc: parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__": main()
