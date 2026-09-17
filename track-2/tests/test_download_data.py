import zipfile
from pathlib import Path
from scripts.download_data import NAMES, download_data

def test_download_validates_and_extracts_exact_archive(tmp_path):
    archive=tmp_path/'source.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for name in NAMES: z.writestr(name,name)
    calls=[]
    def transport(url,target): calls.append(url); Path(target).write_bytes(archive.read_bytes())
    destination=tmp_path/'raw'; download_data(destination,transport); download_data(destination,transport)
    assert {p.name for p in destination.iterdir()}==NAMES and len(calls)==1


def test_make_download_uses_prep_container_without_host_python(tmp_path):
    import json
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[2]
    capture = tmp_path / "capture_docker.py"
    capture.write_text("import json, sys\nprint(json.dumps(sys.argv[1:]))\n")
    result = subprocess.run(
        ["make", "-s", "download-data", "PYRUN=false", f"DOCKER={sys.executable} {capture}"],
        cwd=root, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        "compose", "-f", str(root / "docker-compose.yml"), "run", "--rm", "prep",
        "python", "scripts/download_data.py", "--destination", "/app/data/raw",
    ]
