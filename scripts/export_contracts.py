"""Export application-owned schemas; no vendor schema is implied."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from receiving.ai import ModelSuggestion
from receiving.app import create_app
from receiving.config import Settings
from receiving.models import ReceiptInput, ReceiptUpdate, SuggestCommand


def documents():
    schemas = {
        "receipt-input.schema.json": ReceiptInput.model_json_schema(),
        "receipt-update.schema.json": ReceiptUpdate.model_json_schema(),
        "suggestion-request.schema.json": SuggestCommand.model_json_schema(),
        "model-output.schema.json": ModelSuggestion.model_json_schema(),
    }
    for name, schema in schemas.items():
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$comment"] = "Application-owned draft contract. Not an iBlueprint, WaerLinx or NetSuite API specification."
    with tempfile.TemporaryDirectory() as tmp:
        schemas["openapi.json"] = create_app(Settings(data_dir=Path(tmp))).openapi()
    amount = {"type": ["string", "null"], "pattern": "^[0-9]+(?:\\.[0-9]+)?$"}
    line = {"type": "object", "additionalProperties": False,
            "properties": {
                "line_id": {"type": "string"}, "product_id": {"type": "string"},
                "quantity": {"type": "string", "pattern": "^[0-9]+(?:\\.[0-9]+)?$"},
                "unit": {"enum": ["case", "each", "lb", "kg"]},
                "measured_weight": amount, "weight_unit": {"enum": ["lb", "kg", None]},
                "lot": {"type": "string"}, "expiry_date": {"type": ["string", "null"], "format": "date"},
                "disposition": {"const": "available"}},
            "required": ["line_id", "product_id", "quantity", "unit", "measured_weight", "weight_unit", "lot", "expiry_date", "disposition"]}
    schemas["neutral-handoff.schema.json"] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Approved receiving handoff (project-owned draft)",
        "description": "Internal simulation envelope; not a supported vendor import file.",
        "type": "object", "additionalProperties": False,
        "properties": {
            "schema_version": {"const": "receiving-draft/1"}, "receipt_id": {"type": "string"},
            "supplier": {"type": "string"}, "delivery_ref": {"type": "string"},
            "warehouse": {"type": "string"}, "purchase_order_ref": {"type": "string", "minLength": 1},
            "received_on": {"type": "string", "format": "date"},
            "lines": {"type": "array", "minItems": 1, "items": line}},
        "required": ["schema_version", "receipt_id", "supplier", "delivery_ref", "warehouse", "purchase_order_ref", "received_on", "lines"],
    }
    return schemas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if checked-in contracts do not match code.")
    args = parser.parse_args()
    destination = ROOT / "contracts"
    destination.mkdir(exist_ok=True)
    mismatch = []
    for name, document in documents().items():
        content = json.dumps(document, indent=2, sort_keys=True) + "\n"
        path = destination / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                mismatch.append(name)
        else:
            path.write_text(content, encoding="utf-8")
    if mismatch:
        raise SystemExit("Regenerate stale schemas: " + ", ".join(mismatch))
    print("Contracts are current." if args.check else "Wrote application-owned schemas to contracts/.")


if __name__ == "__main__":
    main()
