#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from decision.contracts import (ClaimsResponse, DecisionConfig, ErrorResponse, Evaluation,
    EvaluationRequest, EvidencePage, FindingDetail, InvestigationResponse, JobDetail)
from scripts.export_contracts import export

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "track-2" / "contracts"
FIXTURE_MODELS = {
    "default-request.json": EvaluationRequest, "config.json": DecisionConfig,
    "evaluation.json": Evaluation, "evaluation-both-actions.json": Evaluation,
    "evidence-cpu.json": EvidencePage, "evidence-idle.json": EvidencePage,
    "evidence-cpu-default.json": EvidencePage, "evidence-idle-standalone.json": EvidencePage,
    "job.json": JobDetail, "finding.json": FindingDetail,
    "investigation.json": InvestigationResponse, "error-data-not-ready.json": ErrorResponse,
}


def main() -> None:
    with tempfile.TemporaryDirectory() as raw:
        temp = Path(raw); export(temp)
        ts = temp / "contracts.generated.ts"
        env = {**__import__('os').environ, "CONTRACTS_TS_OUTPUT": str(ts)}
        subprocess.run(["npm", "--prefix", str(ROOT / "track-2/dashboard"), "run", "contracts"], env=env, check=True)
        pairs = [(temp / "decision.schema.json", CONTRACTS / "decision.schema.json"), (temp / "openapi.json", CONTRACTS / "openapi.json"), (ts, ROOT / "track-2/dashboard/src/api/contracts.generated.ts")]
        drift = [str(dst.relative_to(ROOT)) for src, dst in pairs if not dst.exists() or src.read_bytes() != dst.read_bytes()]
        if drift: raise SystemExit("contract drift: " + ", ".join(drift))
    fixtures = CONTRACTS / "fixtures"
    missing = set(FIXTURE_MODELS) - {p.name for p in fixtures.glob("*.json")}
    if missing: raise SystemExit("missing fixtures: " + ", ".join(sorted(missing)))
    bundle = json.loads((CONTRACTS / "decision.schema.json").read_text())
    for name, model in FIXTURE_MODELS.items():
        value = json.loads((fixtures / name).read_text())
        model.model_validate(value)
        Draft202012Validator({"$ref": f"#/$defs/{model.__name__}", "$defs": bundle["$defs"]}).validate(value)
    print("Contracts and 12 fixtures are current.")


if __name__ == "__main__": main()
