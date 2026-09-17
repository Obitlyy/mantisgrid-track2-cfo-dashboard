"""Explicit audit, atomic claims export and release validation commands."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from decision.config import REPO_ROOT, resolve_paths
from decision.contracts import Evaluation, EvaluationRequest
from decision.errors import DecisionError

TRACK_ROOT = Path(__file__).resolve().parents[1]


def dashboard_check_url(url: str, *, container: bool | None = None) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Dashboard URL must be an HTTP(S) URL without credentials")
    if container is None:
        container = Path("/.dockerenv").exists()
    if container and parsed.hostname in {"localhost", "127.0.0.1"} and parsed.port == 3000:
        if os.environ.get("TRACK2_HOST_DASHBOARD_CHECKED") != url:
            raise ValueError("Check the original URL with host curl first; pass TRACK2_HOST_DASHBOARD_CHECKED with that URL to the tools container")
        checked = urlunsplit((parsed.scheme, "dashboard:3000", parsed.path, parsed.query, parsed.fragment))
    else:
        checked = url
    print(f"Dashboard URL: {url}; actual check URL: {checked}")
    return checked


def _team(team: str, output: Path) -> str:
    value = team.strip()
    if not value or value.casefold() in {"your team", "your team name", "team name", "todo", "tbd", "placeholder"}:
        raise ValueError("Provide a nonblank actual team name")
    if output.resolve() == (REPO_ROOT / "claims.json").resolve() and value.casefold() in {"fixture team", "integration test team", "test team"}:
        raise ValueError("A development team cannot be exported as final root claims.json")
    return value


def _atomic_export(output: Path, claims: dict, data_dir: Path) -> None:
    output = output.expanduser().resolve()
    if output == data_dir.resolve() or output.is_relative_to(data_dir.resolve()) or output.is_relative_to((REPO_ROOT / "data").resolve()):
        raise ValueError("Claims output must not be inside the official data directory")
    text = json.dumps(claims, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, prefix=f".{output.name}.", delete=False) as handle:
            temp = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, output)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def _validate(args, data_dir: Path) -> int:
    from decision.data import load_snapshot
    from decision.service import evaluate
    from decision.validation import validate_claims_semantics

    checked_url = dashboard_check_url(args.dashboard_url) if args.dashboard_url else None
    if checked_url:
        original = urlsplit(args.dashboard_url)
        if checked_url == args.dashboard_url and original.hostname in {"localhost", "127.0.0.1"} and original.port == 3000:
            probe = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--max-time", "15", "--output", os.devnull, args.dashboard_url], check=False)
            if probe.returncode:
                print("FAIL: host dashboard curl check failed", file=sys.stderr)
                return 1
    command = [sys.executable, str(TRACK_ROOT / "scripts/validate_submission.py"), "--claims", str(args.claims)]
    if checked_url:
        command += ["--url", checked_url]
    official = subprocess.run(command, check=False)
    if official.returncode:
        return 1
    claims = json.loads(args.claims.read_text())
    _team(claims.get("team", ""), args.claims)
    request = EvaluationRequest.model_validate(claims["analysis_provenance"]["evaluation_request"])
    evaluation = evaluate(load_snapshot(data_dir), request)
    problems = validate_claims_semantics(claims, evaluation)
    if checked_url:
        origin = urlsplit(checked_url)
        endpoint = urlunsplit((origin.scheme, origin.netloc, "/v1/decision/evaluate", "", ""))
        http_request = Request(endpoint, data=json.dumps(request.model_dump(mode="json"), allow_nan=False).encode(), headers={"Content-Type": "application/json"})
        with urlopen(http_request, timeout=30) as response:
            remote = Evaluation.model_validate_json(response.read())
        problems.extend(f"dashboard: {problem}" for problem in validate_claims_semantics(claims, remote))
    else:
        print("warn: dashboard not checked (no --dashboard-url)")
    for problem in problems:
        print(f"FAIL semantic: {problem}")
    if problems:
        return 1
    print(f"Claims semantic validation passed: dataset_id={evaluation.meta.dataset_id} evaluation_id={evaluation.meta.evaluation_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="track2-decision")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("audit", "export-claims", "validate"):
        child = sub.add_parser(command)
        child.add_argument("--data-dir", type=Path)
        child.add_argument("--output-dir", type=Path)
        if command == "export-claims":
            child.add_argument("--team", required=True)
            child.add_argument("--request", type=Path)
            child.add_argument("--output", type=Path, required=True)
        elif command == "validate":
            child.add_argument("--claims", type=Path, required=True)
            child.add_argument("--dashboard-url")
    args = parser.parse_args(argv)
    try:
        from decision.claims import build_claims
        from decision.data import load_snapshot
        from decision.investigation import run_investigation
        from decision.service import evaluate
        from decision.validation import validate_claims_semantics

        paths = resolve_paths()
        data_dir = (args.data_dir or paths.data_dir).expanduser().resolve()
        output_dir = (args.output_dir or paths.output_dir).expanduser().resolve()
        if args.command == "audit":
            result = asyncio.run(run_investigation(data_dir, output_dir))
            print(f"Audit: {result.status}; dataset_id={result.dataset_id}; calls={len(result.tool_calls)}")
            for limitation in result.limitations:
                print(f"warn: {limitation}")
            return 0 if result.status in {"completed", "partial"} else 1
        if args.command == "validate":
            return _validate(args, data_dir)
        team = _team(args.team, args.output)
        request_path = args.request or TRACK_ROOT / "contracts/fixtures/default-request.json"
        request = EvaluationRequest.model_validate_json(request_path.read_text())
        evaluation = evaluate(load_snapshot(data_dir), request)
        claims = build_claims(evaluation, team)
        problems = validate_claims_semantics(claims, evaluation)
        if problems:
            raise ValueError("; ".join(problems))
        _atomic_export(args.output, claims, data_dir)
        print(f"Exported {args.output}: dataset_id={evaluation.meta.dataset_id} evaluation_id={evaluation.meta.evaluation_id}")
        return 0
    except (DecisionError, ValueError, OSError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
