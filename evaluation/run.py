"""Run repeatable suggestion checks; no operational savings are fabricated.

Usage: python -m evaluation.run
Optional: python -m evaluation.run --ollama-model YOUR_LOCAL_MODEL
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import statistics
import time
from typing import Callable

from receiving.matching import load_catalog, match_item

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data" / "synthetic" / "evaluation_cases.json"
DEFAULT_OUTPUT = ROOT / "evaluation" / "results"


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def evaluate_strategy(cases: list[dict], predictor: Callable[[dict], dict],
                      known_ids: set[str]) -> dict:
    """Score only permitted predictions; ground truth never enters predictor.

    An exception or malformed response is a failed case, NOT a successful
    abstention. Correctly declining an unknown case is counted separately from
    retrieving a known item. Precision is null when there are no suggestions.
    """
    seen: set[str] = set()
    for case in cases:
        if case["case_id"] in seen:
            raise ValueError("Evaluation case IDs must be unique.")
        seen.add(case["case_id"])
        expected = case["expected_product_id"]
        if expected is not None and expected not in known_ids:
            raise ValueError("Ground truth refers to a product absent from the catalog.")
        if not isinstance(case.get("input"), dict):
            raise ValueError("Each case requires an input object.")

    rows: list[dict] = []
    latencies: list[float] = []
    for case in cases:
        expected = case["expected_product_id"]
        # Construct a new evidence-only payload: neither category nor expectation
        # nor expected_product_id is visible to a strategy or a model.
        evidence = {"barcode": case["input"].get("barcode", ""),
                    "label_text": case["input"].get("label_text", "")}
        start = time.perf_counter_ns()
        predicted = None
        method = "error"
        error = None
        try:
            response = predictor(deepcopy(evidence))
            if not isinstance(response, dict) or "product_id" not in response:
                raise ValueError("Prediction lacks product_id.")
            if response.get("error_type"):
                # The UI adapter deliberately fails safely to manual entry. That
                # fallback is still a provider failure, not evaluation success.
                raise RuntimeError("Provider reported an error while returning a safe fallback.")
            predicted = response["product_id"]
            if predicted is not None and (not isinstance(predicted, str) or predicted not in known_ids):
                raise ValueError("Prediction is outside the allowed catalog.")
            if response.get("requires_review") is not True:
                raise ValueError("Prediction does not preserve required staff review.")
            method = str(response.get("method", "unspecified"))
        except Exception as exc:
            # Do not serialize provider URLs, tokens, prompts, or exception text.
            error = type(exc).__name__
            predicted = None
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        latencies.append(elapsed_ms)
        if error:
            outcome = "error"
        elif predicted is None:
            outcome = "correct_abstention" if expected is None else "missed_match"
        elif predicted == expected:
            outcome = "correct_match"
        else:
            outcome = "wrong_suggestion"
        rows.append({"case_id": case["case_id"], "category": case.get("category", "uncategorized"),
                     "expected_product_id": expected, "suggested_product_id": predicted,
                     "method": method, "outcome": outcome, "error_type": error,
                     "elapsed_ms": round(elapsed_ms, 6)})

    counts = {outcome: sum(row["outcome"] == outcome for row in rows)
              for outcome in ("correct_match", "wrong_suggestion", "correct_abstention", "missed_match", "error")}
    total = len(cases)
    expected_matches = sum(case["expected_product_id"] is not None for case in cases)
    suggestions = counts["correct_match"] + counts["wrong_suggestion"]
    abstentions = counts["correct_abstention"] + counts["missed_match"]
    ordered = sorted(latencies)
    p95_index = max(0, (95 * len(ordered) + 99) // 100 - 1)
    return {
        "status": "measured_synthetic", "case_count": total,
        "expected_match_count": expected_matches, "expected_abstain_count": total - expected_matches,
        "suggestion_count": suggestions, "abstention_count": abstentions,
        "unresolved_case_count": abstentions + counts["error"],
        "all_cases_require_human_review": True,
        **{f"{key}_count": value for key, value in counts.items()},
        "suggestion_coverage": _ratio(suggestions, total),
        "suggestion_precision": _ratio(counts["correct_match"], suggestions),
        "known_item_recall": _ratio(counts["correct_match"], expected_matches),
        "exact_decision_accuracy": _ratio(counts["correct_match"] + counts["correct_abstention"], total),
        "algorithm_latency_ms": {"median": round(statistics.median(latencies), 6) if latencies else None,
                                 "p95": round(ordered[p95_index], 6) if ordered else None,
                                 "total": round(sum(latencies), 6)},
        "staff_time_seconds": None,
        "staff_time_status": "not_measured; requires observed receiving study",
        "operating_cost_usd": None,
        "operating_cost_status": "not_measured; no hosting, labor, energy or token prices assumed",
        "cases": rows,
    }


def run_benchmark(cases_path: str | Path = DEFAULT_CASES,
                  catalog_path: str | Path | None = None,
                  ollama_model: str | None = None,
                  ollama_url: str = "http://127.0.0.1:11434") -> dict:
    catalog = load_catalog(catalog_path)
    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    known_ids = {item["product_id"] for item in catalog}
    strategies = {
        "form_only": lambda evidence: {"product_id": None, "method": "manual_entry",
                                        "reason": "No automated suggestion; staff supplies the item.",
                                        "requires_review": True},
        "barcode_only": lambda evidence: match_item(catalog, barcode=evidence["barcode"]),
        "barcode_plus_label_rules": lambda evidence: match_item(catalog, **evidence),
    }
    results = {name: evaluate_strategy(cases, predictor, known_ids)
               for name, predictor in strategies.items()}
    if ollama_model:
        from receiving.ai import suggest_with_ollama

        def model_strategy(evidence: dict) -> dict:
            if evidence["barcode"] or not evidence["label_text"].strip():
                return match_item(catalog, **evidence)
            return suggest_with_ollama(catalog, evidence["label_text"], ollama_url, ollama_model)

        results["barcode_then_local_model"] = evaluate_strategy(cases, model_strategy, known_ids)
        results["barcode_then_local_model"]["model_name"] = ollama_model
        results["barcode_then_local_model"]["model_metadata"] = "Operator must record exact digest, size, quantization, license and hardware."
    else:
        results["barcode_then_local_model"] = {
            "status": "not_run", "reason": "No local model selected or invoked.",
            "model_name": None, "parameter_count": None, "staff_time_seconds": None,
            "operating_cost_usd": None,
        }
    return {
        "schema_version": "1.0", "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": ("Curated synthetic decision cases included with this repository"
                    if Path(cases_path).resolve() == DEFAULT_CASES.resolve()
                    else "Operator-supplied cases; provenance and permissions must be recorded separately"),
        "scope": "Algorithmic suggestion behavior only. Not warehouse outcomes, OCR accuracy, human baseline accuracy or time savings.",
        "evidence_policy": "Only input.barcode and input.label_text are passed to strategies; labels remain in the scorer.",
        "runtime": {"python": platform.python_version(), "platform": platform.system(), "machine": platform.machine()},
        "case_count": len(cases), "catalog_item_count": len(catalog), "strategies": results,
    }


def _percent(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def render_markdown(report: dict) -> str:
    lines = ["# Synthetic receiving-assistant benchmark", "",
             "> Generated from synthetic cases. These are software checks, not deployed-user evidence.", "",
             f"Run: {report['generated_at']}", "",
             f"{report['case_count']} curated cases; {report['catalog_item_count']} synthetic catalog products.", "",
             "The form-only row represents **no automated suggestion**. Staff performance was not measured. A model and an OCR engine were not run unless explicitly listed below. Rule matching on hand-authored label text is not OCR.", "",
             "| Strategy | Suggestions | Correct matches | Wrong suggestions | Correct abstentions | Missed matches | Errors | Coverage | Suggestion precision | Known-item recall | Exact decisions | Median algorithm ms |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name, result in report["strategies"].items():
        if result["status"] == "not_run":
            lines.append(f"| {name} (not run) | — | — | — | — | — | — | — | — | — | — | — |")
            continue
        columns = [name, str(result["suggestion_count"]), str(result["correct_match_count"]),
                   str(result["wrong_suggestion_count"]), str(result["correct_abstention_count"]),
                   str(result["missed_match_count"]), str(result["error_count"]),
                   _percent(result["suggestion_coverage"]), _percent(result["suggestion_precision"]),
                   _percent(result["known_item_recall"]), _percent(result["exact_decision_accuracy"]),
                   f"{result['algorithm_latency_ms']['median']:.4f}"]
        lines.append("| " + " | ".join(columns) + " |")
    lines.extend(["", "## Interpretation", "",
                  "- Barcode-only ignores label text, so contradictory label/scan examples reveal a limitation. Combined rules decline these conflicts.",
                  "- Exact decisions include correct abstentions. A system that always abstains may score well on unknown cases while offering no matches; coverage, precision, and known-item recall must be read together.",
                  "- Every suggestion still requires staff confirmation. A correct item identity does not verify quantity, weight, condition, expiry, lot, or food safety.",
                  "- Elapsed milliseconds measure a single local software call. They exclude scanning, reviewing, corrections, and handoff work; these figures cannot establish staff time saved.",
                  "- Staff time and operating cost are unknown. No model performance, token cost, dollar savings, or pilot adoption is inferred from these fixtures.",
                  "- The cases are curated and not a blind held-out sample. Production validation requires permission-cleared representative transactions and independent annotations.",
                  "", "See `evaluation/README.md` for the protocol and `results.json` for per-case outcomes.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--catalog", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ollama-model", default=None, help="Opt in to calling an already installed local model.")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    report = run_benchmark(args.cases, args.catalog, args.ollama_model, args.ollama_url)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.output / "report.md").write_text(render_markdown(report), encoding="utf-8")
    for name, result in report["strategies"].items():
        if result["status"] == "not_run":
            print(f"{name}: not run")
        else:
            print(f"{name}: {result['correct_match_count']} correct matches, {result['wrong_suggestion_count']} wrong suggestions, {result['error_count']} errors")
    print(f"Wrote {args.output / 'results.json'} and report.md")


if __name__ == "__main__":
    main()
