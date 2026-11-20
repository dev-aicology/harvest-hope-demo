"""Optional OCR smoke test on three synthetic label illustrations, scored separately."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics

from receiving.matching import load_catalog
from receiving.ocr import extract_text, suggest_from_ocr

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "synthetic"


def run_ocr_smoke() -> dict:
    catalog = load_catalog()
    cases = json.loads((FIXTURES / "ocr_cases.json").read_text(encoding="utf-8"))
    rows = []
    for case in cases:
        extracted = extract_text(FIXTURES / case["image"], allowed_root=FIXTURES / "labels")
        suggestion = suggest_from_ocr(catalog, extracted["text"]) if extracted["status"] == "ok" else None
        predicted = suggestion["product_id"] if suggestion else None
        exact_label = (extracted["status"] == "ok" and
                       case["expected_label_text"].casefold() in {line.strip().casefold() for line in extracted["text"].splitlines()})
        rows.append({"case_id": case["case_id"], "image": case["image"],
                     "expected_product_id": case["expected_product_id"], "suggested_product_id": predicted,
                     "ocr_status": extracted["status"], "error_type": extracted["error_type"],
                     "elapsed_ms": extracted["elapsed_ms"], "exact_label_line_recovered": exact_label,
                     "correct_item": extracted["status"] == "ok" and predicted == case["expected_product_id"],
                     "text": extracted["text"], "suggestion": suggestion})
    success = sum(row["ocr_status"] == "ok" for row in rows)
    return {"schema_version": "1.0", "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Three synthetic text-label illustrations only, not photographs or an operational accuracy sample.",
            "engine": "Local Tesseract, fixed eng language and psm 6; no downloads or external calls",
            "separate_from_text_benchmark": True, "case_count": len(rows), "ocr_success_count": success,
            "error_or_unavailable_count": len(rows) - success,
            "correct_item_count": sum(row["correct_item"] for row in rows),
            "exact_label_line_count": sum(row["exact_label_line_recovered"] for row in rows),
            "median_algorithm_ms": statistics.median(row["elapsed_ms"] for row in rows) if rows else None,
            "staff_time_seconds": None, "operating_cost_usd": None,
            "small_model_status": "not_run", "cases": rows}


def render_report(report: dict) -> str:
    lines = ["# Optional local OCR smoke results", "",
             "> This is a three-image synthetic smoke test. It is separate from the 62-case text benchmark and is not warehouse deployment evidence.", "",
             f"Run: {report['generated_at']}", "",
             report["engine"], "",
             f"OCR succeeded on {report['ocr_success_count']} / {report['case_count']} images; exact item names were recovered on {report['exact_label_line_count']} / {report['case_count']}; item suggestions matched on {report['correct_item_count']} / {report['case_count']}.", "",
             "| Case | OCR status | Suggested item | Correct item | OCR call ms |",
             "| --- | --- | --- | --- | ---: |"]
    for row in report["cases"]:
        lines.append(f"| {row['case_id']} | {row['ocr_status']} | {row['suggested_product_id'] or '—'} | {row['correct_item']} | {row['elapsed_ms']:.2f} |")
    lines += ["", "The adapter extracts text locally; exact catalog-name rules then propose an item. Expected IDs and expected label strings are used only by the scorer. Embedded catalog-ID text is not used for matching.", "",
              "The PNGs contain clear synthetic labels and were generated for this demo. These results do not predict performance on damaged, curved, small, rotated or poorly lit real labels. No optical barcode decoder, vision model, quantity inference, or weight inference is involved. Every suggestion needs staff review.", "",
              "Elapsed time covers image validation and OCR process execution. Staff time and all operational costs are unmeasured. The local language model remains unrun.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation" / "results")
    args = parser.parse_args()
    result = run_ocr_smoke()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "ocr_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (args.output / "ocr_report.md").write_text(render_report(result), encoding="utf-8")
    print(f"OCR: {result['ocr_success_count']}/{result['case_count']} succeeded, {result['correct_item_count']} correct item suggestions.")
    print("This is a separate synthetic smoke test, not warehouse accuracy or staff time savings.")


if __name__ == "__main__":
    main()
