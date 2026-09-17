#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from decision.app import app
from decision.contracts import NETWORK_MODELS


def export(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    definitions = {}
    for model in NETWORK_MODELS:
        schema = model.model_json_schema(ref_template="#/$defs/{model}")
        definitions.update(schema.pop("$defs", {}))
        definitions[model.__name__] = schema
    bundle = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Track 2 Decision Contracts", "$defs": dict(sorted(definitions.items()))}
    (output / "decision.schema.json").write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    (output / "openapi.json").write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    export(parser.parse_args().output)


if __name__ == "__main__": main()
