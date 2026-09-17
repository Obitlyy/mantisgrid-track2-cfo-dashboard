#!/usr/bin/env python3
"""Read-only HTTP smoke test for the real Track 2 decision path."""

from __future__ import annotations

import argparse
import json
import urllib.request
from decimal import Decimal, ROUND_HALF_UP


def request_json(base: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{base.rstrip('/')}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        assert response.status == 200, (path, response.status)
        assert response.headers.get_content_type() == "application/json", path
        return json.load(response)


def rounded(value: float, digits: int) -> float:
    quantum = Decimal("1").scaleb(-digits)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:3000")
    args = parser.parse_args()

    config = request_json(args.url, "/v1/decision/config")
    evaluation = request_json(args.url, "/v1/decision/evaluate", config["default_request"])
    meta = evaluation["meta"]
    assert meta["data_origin"] == "official_dataset"
    assert meta["dataset_id"] and meta["evaluation_id"]

    action_id = evaluation["request"]["selected_action_ids"][0]
    action = next(item for item in evaluation["actions"] if item["action_id"] == action_id)
    total = 0.0
    offset = 0
    candidates = 0
    while True:
        evidence = request_json(
            args.url,
            f"/v1/decision/actions/{action_id}/evidence?scope=marginal&offset={offset}&limit=200",
            evaluation["request"],
        )
        assert evidence["meta"]["dataset_id"] == meta["dataset_id"]
        assert evidence["meta"]["evaluation_id"] == meta["evaluation_id"]
        for row in evidence["rows"]:
            if row["eligibility"] == "included":
                candidates += 1
                total += row["contribution_gpu_hours"]["point"]
        if evidence["next_offset"] is None:
            break
        offset = evidence["next_offset"]
    if not candidates:
        raise SystemExit("No demonstrable candidates in the official dataset")
    expected = action["marginal_recoverable_gpu_hours"]["point"]
    assert abs(total - expected) <= 1e-6, (total, expected)

    response = request_json(
        args.url,
        "/v1/decision/claims",
        {"team": "Integration Test Team", "evaluation_request": evaluation["request"]},
    )
    claims = response["claims"]
    provenance = claims["analysis_provenance"]
    assert response["meta"]["dataset_id"] == provenance["dataset_id"] == meta["dataset_id"]
    assert response["meta"]["evaluation_id"] == provenance["evaluation_id"] == meta["evaluation_id"]
    assert provenance["evaluation_request"] == evaluation["request"]
    assert claims["recoverable_gpu_hours"]["point"] == rounded(
        evaluation["portfolio"]["recoverable_gpu_hours"]["point"], 6
    )
    assert claims["recoverable_usd"]["point"] == rounded(
        evaluation["portfolio"]["reference_savings_usd"]["point"], 2
    )
    assert claims["cash_savings_claimed"] is False
    print(f"dataset_id={meta['dataset_id']}")
    print(f"evaluation_id={meta['evaluation_id']}")
    print(f"evidence_rows={candidates} contribution_point={total:.6f}")


if __name__ == "__main__":
    main()
