import json
from pathlib import Path

import pytest

from decision import cli
from factories import default_request, golden_snapshot


def setup_snapshot(monkeypatch):
    monkeypatch.setattr("decision.data.load_snapshot", lambda path: golden_snapshot())


def test_export_and_validate_roundtrip_and_tamper(tmp_path, monkeypatch, capsys):
    setup_snapshot(monkeypatch)
    output = tmp_path / "claims.json"
    request = tmp_path / "request.json"
    payload = default_request().model_dump(mode="json")
    payload["pricing"]["usd_per_gpu_hour"] = 4
    request.write_text(json.dumps(payload))
    assert cli.main(["export-claims", "--team", "Fixture Team", "--request", str(request), "--output", str(output)]) == 0
    claims = json.loads(output.read_text())
    assert claims["recoverable_usd"]["point"] == 60
    assert cli.main(["validate", "--claims", str(output)]) == 0
    assert "semantic" in capsys.readouterr().out
    claims["recoverable_gpu_hours"]["point"] += 1
    output.write_text(json.dumps(claims))
    assert cli.main(["validate", "--claims", str(output)]) == 1


@pytest.mark.parametrize("team", ["", " ", "Your Team", "TODO", "Integration Test Team"])
def test_export_rejects_placeholder_to_final_claims(team, tmp_path, monkeypatch):
    setup_snapshot(monkeypatch)
    monkeypatch.chdir(tmp_path)
    # Explicit test teams are allowed only in test/output locations.
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path, raising=False)
    output = tmp_path / "claims.json"
    assert cli.main(["export-claims", "--team", team, "--output", str(output)]) == 1
    assert not output.exists()


def test_export_cannot_write_official_data(tmp_path, monkeypatch):
    setup_snapshot(monkeypatch)
    assert cli.main(["export-claims", "--team", "Fixture Team", "--data-dir", str(tmp_path), "--output", str(tmp_path / "claims.json")]) == 1
    assert not (tmp_path / "claims.json").exists()


def test_validate_rejects_non_http_url(tmp_path, monkeypatch):
    setup_snapshot(monkeypatch)
    assert cli.main(["validate", "--claims", str(tmp_path / "absent"), "--dashboard-url", "file:///etc/passwd"]) == 1


def test_atomic_failure_preserves_existing_output(tmp_path, monkeypatch):
    setup_snapshot(monkeypatch)
    output = tmp_path / "claims.json"
    output.write_text("original")
    def fail_replace(*args):
        raise OSError("replacement failed")
    monkeypatch.setattr(cli.os, "replace", fail_replace)
    assert cli.main(["export-claims", "--team", "Fixture Team", "--output", str(output)]) == 1
    assert output.read_text() == "original"
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize("status,code", [("completed", 0), ("partial", 0), ("failed", 1), ("running", 1)])
def test_audit_exit_status(status, code, tmp_path, monkeypatch):
    from decision.investigation import not_run_investigation
    async def audit(data_dir, output_dir):
        return not_run_investigation("fixture-dataset-v1").model_copy(update={"status": status})
    monkeypatch.setattr("decision.investigation.run_investigation", audit)
    assert cli.main(["audit", "--data-dir", str(tmp_path), "--output-dir", str(tmp_path)]) == code


def test_container_mapping_requires_host_check_and_preserves_other_urls(monkeypatch):
    monkeypatch.delenv("TRACK2_HOST_DASHBOARD_CHECKED", raising=False)
    with pytest.raises(ValueError, match="host curl"):
        cli.dashboard_check_url("http://localhost:3000", container=True)
    monkeypatch.setenv("TRACK2_HOST_DASHBOARD_CHECKED", "http://localhost:3000")
    assert cli.dashboard_check_url("http://localhost:3000", container=True) == "http://dashboard:3000"
    assert cli.dashboard_check_url("https://example.org", container=True) == "https://example.org"
    assert cli.dashboard_check_url("http://127.0.0.1:3000", container=False) == "http://127.0.0.1:3000"


def test_loopback_validation_runs_host_curl_before_official_validator(tmp_path, monkeypatch):
    import subprocess
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 7)
    monkeypatch.setattr(cli.subprocess, "run", run)
    monkeypatch.setattr(cli, "dashboard_check_url", lambda url: url)
    assert cli.main(["validate", "--claims", str(tmp_path / "claims.json"), "--dashboard-url", "http://localhost:3000"]) == 1
    assert len(calls) == 1
    assert calls[0][0] == "curl"
    assert calls[0][-1] == "http://localhost:3000"


def test_make_forwards_literal_team_and_request_as_safe_argv(tmp_path):
    import subprocess
    import sys
    capture = tmp_path / "capture.py"
    capture.write_text("import json, os, sys\nprint(json.dumps({'argv':sys.argv[1:], 'path':os.environ.get('PYTHONPATH')}))\n")
    root = Path(__file__).resolve().parents[2]
    team = "Fixture 'quoted' Team $(touch /tmp/never-run) `false`; &"
    request = str(tmp_path / "request with 'quotes' $(literal).json")
    result = subprocess.run(["make", "-s", "export-claims", f"PYRUN={sys.executable} {capture}", f"TEAM={team}", f"REQUEST={request}", f"CLAIMS={tmp_path / 'output file.json'}"], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    captured = json.loads(result.stdout)
    args = captured["argv"]
    assert args[args.index("--team") + 1] == team
    assert args[args.index("--request") + 1] == request
    assert captured["path"] == str(root / "track-2")


@pytest.mark.parametrize("stale", [False, True])
@pytest.mark.parametrize("dashboard_path", ["", "/portfolio", "?view=cpu#cards", "/investigation?view=nodes#details"])
def test_validation_checks_live_same_origin_evaluation(tmp_path, monkeypatch, stale, dashboard_path):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from decision.service import evaluate
    setup_snapshot(monkeypatch)
    output = tmp_path / "claims.json"
    assert cli.main(["export-claims", "--team", "Fixture Team", "--output", str(output)]) == 0
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Dashboard")
        def do_POST(self):
            from decision.contracts import EvaluationRequest
            if self.path != "/v1/decision/evaluate":
                self.send_error(404, "Evaluation API is served at the origin root")
                return
            request = EvaluationRequest.model_validate_json(self.rfile.read(int(self.headers["Content-Length"])))
            result = evaluate(golden_snapshot(), request)
            if stale:
                result.meta.dataset_id = "stale-dashboard"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(result.model_dump_json().encode())
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        assert cli.main(["validate", "--claims", str(output), "--dashboard-url", f"http://127.0.0.1:{server.server_port}{dashboard_path}"]) == int(stale)
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
