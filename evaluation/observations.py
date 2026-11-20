"""Validate and summarize actual pilot observations without inventing missing values."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics

STRATEGIES = ("manual", "barcode_ocr", "small_model")
NUMERIC_FIELDS = ("staff_seconds", "correction_seconds", "compute_seconds",
                  "model_cost_usd", "hosting_cost_usd", "staff_cost_usd")
FIELDS = ("observation_id", "strategy", "transaction_ref", "accepted", "correct_final_record", *NUMERIC_FIELDS)


def read_observations(path: str | Path) -> list[dict]:
    rows = []
    seen = set()
    with Path(path).open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("Use the exact observations.template.csv header and column order.")
        for number, original in enumerate(reader, start=2):
            if None in original or any(value is None for value in original.values()):
                raise ValueError(f"Row {number} has the wrong number of columns.")
            row = {key: value.strip() for key, value in original.items()}
            if not row["observation_id"] or row["observation_id"] in seen:
                raise ValueError(f"Row {number} needs a unique observation_id.")
            seen.add(row["observation_id"])
            if row["strategy"] not in STRATEGIES or not row["transaction_ref"]:
                raise ValueError(f"Row {number} needs a supported strategy and anonymized transaction_ref.")
            for field in ("accepted", "correct_final_record"):
                value = row[field].lower()
                if value == "" and field == "correct_final_record":
                    row[field] = None
                elif value not in {"true", "false"}:
                    raise ValueError(f"Row {number} field {field} must be true or false (final correctness may be blank).")
                else:
                    row[field] = value == "true"
            for field in NUMERIC_FIELDS:
                if row[field] == "":
                    row[field] = None
                    continue
                try:
                    value = float(row[field])
                except ValueError as exc:
                    raise ValueError(f"Row {number} field {field} is not numeric.") from exc
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"Row {number} field {field} must be finite and nonnegative.")
                row[field] = value
            if (row["staff_seconds"] is not None and row["correction_seconds"] is not None
                and row["correction_seconds"] > row["staff_seconds"]):
                raise ValueError(f"Row {number}: correction_seconds is a subset of total staff_seconds.")
            rows.append(row)
    return rows


def summarize(rows: list[dict]) -> dict:
    strategies = {}
    for strategy in STRATEGIES:
        group = [row for row in rows if row["strategy"] == strategy]
        accepted = sum(row["accepted"] for row in group)
        audited = [row for row in group if row["correct_final_record"] is not None]
        summary = {"observations": len(group), "accepted_receipts": accepted,
                   "audited_records": len(audited),
                   "audited_final_record_accuracy": (sum(row["correct_final_record"] for row in audited) / len(audited)) if audited else None}
        for field in ("staff_seconds", "correction_seconds", "compute_seconds"):
            values = [row[field] for row in group if row[field] is not None]
            summary[field] = {"measured_observations": len(values),
                              "median": statistics.median(values) if values else None}
        cost_fields = ("model_cost_usd", "hosting_cost_usd", "staff_cost_usd")
        complete_costs = [sum(row[field] for field in cost_fields) for row in group
                          if all(row[field] is not None for field in cost_fields)]
        complete = bool(group) and len(complete_costs) == len(group)
        total_cost = sum(complete_costs) if complete else None
        summary["cost_complete_observations"] = len(complete_costs)
        summary["measured_total_cost_usd"] = total_cost
        summary["measured_cost_per_accepted_receipt_usd"] = total_cost / accepted if total_cost is not None and accepted else None
        strategies[strategy] = summary
    return {"generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "observed_data_summary" if rows else "no_observations_yet",
            "caution": "No savings or causal comparison inferred. Use matched tasks and report missing-data denominators.",
            "strategies": strategies}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = json.dumps(summarize(read_observations(args.csv_path)), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote observed-data summary to {args.output}")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
