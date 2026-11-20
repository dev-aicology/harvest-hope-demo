# Evaluation protocol

This harness checks **item suggestion behavior** on curated synthetic inputs. It cannot establish warehouse throughput, food recovery, staff satisfaction, inventory accuracy, operational cost, or grant eligibility.

## Run the available comparison

From the repository root:

```bash
python -m evaluation.run
python -m unittest discover -s tests -p 'test_matching.py'
python -m unittest discover -s tests -p 'test_evaluation.py'
```

Results are written to `evaluation/results/results.json` and `report.md`. The included result is an actual run on the included synthetic dataset. Rerun after code changes; microsecond-scale timings will vary by machine, interpreter and load.

## Optional OCR smoke test

If the local Tesseract executable and its English (`eng`) language data are already installed:

```bash
python -m evaluation.ocr_run
```

This runs Tesseract on the three illustrations in `data/synthetic/labels/`, then applies exact catalog name/alias rules to each extracted line. The results are `evaluation/results/ocr_results.json` and `ocr_report.md`. Input paths must stay within the selected image directory, PNG/JPEG files are limited to 4 MiB and 12 megapixels, subprocess execution uses a fixed argument list with a timeout, and output is bounded. No shell, downloads, remote OCR, or vendor endpoints are used. Missing dependencies or engine errors are reported explicitly.

The included OCR report records an actual local run on **three synthetic text illustrations**, separate from the 62-case text benchmark. Its denominator must never be combined with the text benchmark. It is not evidence of accuracy on real warehouse photos, damaged labels or optical barcode scans. The application's photo upload remains attachment-only; this optional CLI does not add automatic photo inference to the UI.

| Strategy | What actually runs | Limits |
| --- | --- | --- |
| `form_only` | Always produces no automated suggestion | Represents a manual-entry interface, not measured human performance |
| `barcode_only` | Exact local catalog lookup with UPC-A/EAN-13 validation | Does not read label text; conflicting label/scan cases expose this limitation |
| `barcode_plus_label_rules` | Barcode lookup and conservative exact name/alias rules | Text is human supplied; this is neither OCR nor an AI model |
| `barcode_then_local_model` | Optional local-model matching for text-only cases | Not run by default; no model is downloaded or selected for you |

## Optional model run

Once a model has been selected, reviewed, installed and served locally, explicitly enable it for this evaluation:

```bash
python -m evaluation.run --ollama-model YOUR_LOCAL_MODEL --output evaluation/results/local-model
```

The adapter calls the configured local Ollama service. The server must already be running, and the model must support the structured-output schema. No private operational inputs should be used without an approved data-flow and retention decision. Record the exact model tag and digest, total/active parameters if relevant, quantization, license, hardware, runner version and concurrency alongside the result. A model's self-reported confidence is not a calibrated accuracy probability.

The combined strategy keeps supplied barcode decisions deterministic, including abstention on invalid/unknown scans and conflicts. The model receives only the text plus the permitted catalog. It cannot approve a receipt or supply measured quantities. Model failures are counted as errors, not successful abstentions.

## What the metrics mean

- **Suggestion coverage:** cases with a nonempty, in-catalog product suggestion divided by all cases.
- **Suggestion precision:** correct product suggestions divided by all product suggestions. Null when there are no suggestions.
- **Known-item recall:** correct matches divided by cases whose expected result is a known product.
- **Exact decision accuracy:** correct matches plus correct abstentions divided by all cases. Read with coverage: always declining is not useful retrieval.
- **Correct abstention:** ambiguity, conflict, invalid input or unknown item correctly left for staff resolution.
- **Missed match:** an identifiable product receives no automated suggestion.
- **Wrong suggestion:** an incorrect item or a product supplied where the expected safe answer is abstention.
- **Error:** exception, malformed response, missing staff-review requirement, or product outside the allowed catalog. Errors never count as correct abstentions.
- **Algorithm latency:** time inside the Python strategy call; excludes staff scanning, handling, correction and review.

Every case still needs human validation. `staff_time_seconds` and `operating_cost_usd` remain null because neither is measured. No electricity, hosting, staff pay, token price or savings assumptions are inserted.

Ground-truth fields are kept inside the scorer. Strategy calls receive a new object containing only `barcode` and `label_text`; neither the expected product nor the category/annotation is supplied. The tests verify this separation. The curated dataset is useful for regression testing but is not a blind held-out measure of generalization.

## Pilot evaluation to perform later

Pilot duration and transaction count must be agreed with the participating warehouse. No operational study has been completed by this repository.

1. Obtain permission to collect sample transactions and define privacy, retention, access and deletion.
2. Have warehouse staff independently label item identity, unit, lot/expiry requirements, actual quantities and actual weights. Resolve disagreements; preserve uncertainty.
3. Split by delivery and product/label variant so near-duplicates do not leak between development and held-out evaluation.
4. Compare current digital-form work, barcode assistance, actual OCR, and selected model assistance on the **same eligible tasks**. Rotate order or otherwise control learning effects.
5. Measure total staff time through accepted receipt, review and correction time, wrong-item/unit events, retained exceptions, successful handoffs and discrepancies after reconciliation. Include failed cases and outages.
6. Track usage, staff feedback, measured hosting/model cost and actual support effort. Report an uncertainty interval and subgroup results for mixed loads, unreadable labels, units and accessibility needs.
7. Publish only permission-cleared aggregate results and synthetic examples. Keep raw operational evidence private.

## Extending cases

Each JSON case has `case_id`, `category`, an `input` object, `expected_product_id` (known catalog ID or null), and an `expectation` explaining the decision. Null means the correct behavior is to ask a person; it does not imply a nonexistent physical item. The two `ocr_transcription_error` cases contain deliberately noisy text with known identities; conservative rules correctly remain limited and may miss them.

Pass a separate case file with `--cases path/to/cases.json` and a compatible catalog with `--catalog path/to/catalog.json`. Do not commit private paths or data. CI should use only synthetic defaults and must never call a model or live warehouse service implicitly.

## Record observed staff time and cost

`evaluation/observations.template.csv` has a header and **no observations**. Fill a private copy only after an actual receiving study:

```bash
python -m evaluation.observations path/to/private-observations.csv --output path/to/private-summary.json
```

The included `results/observations_summary.json` was generated from the blank template and explicitly says `no_observations_yet`. It contains no human timings, operational accuracy values or costs.

| Column | Meaning |
| --- | --- |
| `observation_id` | Unique anonymous observation ID |
| `strategy` | `manual`, `barcode_ocr`, or `small_model` |
| `transaction_ref` | Anonymized task reference; use matched tasks for meaningful comparison |
| `accepted` | `true` or `false`: whether this attempt produced an accepted receipt |
| `correct_final_record` | Independently audited final correctness; `true`, `false`, or blank if not checked |
| `staff_seconds` | Observed total staff time, including review and correction |
| `correction_seconds` | Measured subset of total staff time spent correcting; do not add it again |
| `compute_seconds` | Observed compute wall time; may overlap staff work and must not automatically be added to staff time |
| `model_cost_usd` | Actual attributable model/inference expense; blank if unknown |
| `hosting_cost_usd` | Actual allocated hosting expense; blank if unknown |
| `staff_cost_usd` | Actual allocated labor expense under an agreed costing method; blank if unknown |

Missing values stay null. Enter zero only when it is an observed or established zero. Each median reports its measured-observation denominator. Audited correctness is `correct audited records / audited records`; unaudited records are excluded from that rate and their missing denominator remains visible. Cost is reported only when **all three cost components are present for every observation in the strategy**. Then total cost is their sum across all attempts, and `cost per accepted receipt = total measured cost / accepted receipt count`. This includes measured failed-attempt expense. No accepted receipts means no per-accepted cost estimate.

The summarizer rejects duplicate observation IDs, unsupported strategies, malformed booleans, nonfinite/negative numbers and correction time greater than total staff time. It does not infer savings, fill in missing wages, treat model suggestions as final record accuracy, or claim a causal comparison between unlike samples.
