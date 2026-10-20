"""Validate contract schemas, fixtures and representative invalid payloads offline."""

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]


def main():
    schema = json.loads((ROOT / "contracts/finance-v1.schema.json").read_text(encoding="utf-8"))
    examples = json.loads((ROOT / "contracts/examples.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    names = {entry["$ref"].split("/")[-1] for entry in schema["oneOf"]}
    if set(examples) != names:
        raise ValueError("Every top-level contract must have exactly one example")
    checker = FormatChecker()
    validators = {
        name: Draft202012Validator(
            {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": f"#/$defs/{name}"},
            format_checker=checker,
        )
        for name in examples
    }
    root_validator = Draft202012Validator(schema, format_checker=checker)
    for name, example in examples.items():
        validators[name].validate(example)
        root_validator.validate(example)

    # These are common integration mistakes: local timestamps, float money,
    # guessed tickers and accidental client-supplied execution fields.
    invalid_cases = [
        ("News", "fetched_at", "2026-10-20 09:00:00"),
        ("News", "published_at", "not-a-date"),
        ("News", "url", "https://"),
        ("News", "symbols", ["THYAO.IS"]),
        ("News", "symbols", ["DEMO", "DEMO"]),
        ("Analysis", "impacts", [{"symbol": "DEMO", "direction": "buy", "confidence": 0.8, "reason": "x"}]),
        ("Analysis", "impacts", [{"symbol": "DEMO", "direction": "neutral", "confidence": 1.5, "reason": "x"}]),
        ("Quote", "price", 100.0),
        ("Quote", "price", "100,00"),
        ("Wallet", "cash_balance", "-1.00"),
        ("TradeRequest", "quantity", 0),
        ("TradeRequest", "quantity", 1.5),
        ("TradeRequest", "idempotency_key", "not-a-uuid"),
        ("TradeRequest", "execution_price", "1.00"),
    ]
    rejected = 0
    for name, field, value in invalid_cases:
        payload = copy.deepcopy(examples[name])
        payload[field] = value
        if validators[name].is_valid(payload):
            raise ValueError(f"Invalid payload accepted: {name}.{field}")
        rejected += 1
    for name, example in examples.items():
        payload = copy.deepcopy(example)
        del payload["schema_version"]
        if validators[name].is_valid(payload):
            raise ValueError(f"Missing version accepted: {name}")
        rejected += 1
    print(f"PASS: schema valid; {len(examples)} examples accepted; {rejected} invalid payloads rejected")


if __name__ == "__main__":
    main()
