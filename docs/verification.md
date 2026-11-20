# V1 verification record

This record describes checks completed on the included local demonstration. It is not evidence of a deployed Harvest Hope system, a production integration, or a completed warehouse pilot. The result files retain their actual UTC run timestamps.

## Completed checks

| Check | Observed result |
| --- | --- |
| Python test suite | **64 tests passed** on Python 3.12.14; no skips in this run |
| Receiving workflow | The scripted walkthrough captured a synthetic receipt, submitted it, approved it, handed it to the mock adapter, detected a mismatch, then recorded a matching simulated reconciliation |
| Walkthrough audit | Seven recorded events; the audit hash chain verified |
| Contract consistency | `python scripts/export_contracts.py --check` passed |
| Browser JavaScript syntax | `node --check receiving/static/app.js` passed |
| Static assets and API | The automated API tests served the HTML, CSS, and JavaScript and exercised the application through FastAPI's test client |
| Text suggestion benchmark | Actual run on 62 curated synthetic cases and 16 invented catalog products; see [the report](../evaluation/results/report.md) |
| Local OCR smoke test | Tesseract ran on three synthetic label images; all three returned text and the correct item suggestion; see [the separate OCR report](../evaluation/results/ocr_report.md) |
| Staff time and cost scaffold | The blank observation template produced `no_observations_yet`; time, final-record accuracy, and cost remain unknown |

The workflow tests cover incomplete and stale records, quantity and unit validation, required weights and lot/expiry fields, held products, conflicting barcodes, permissions, duplicate deliveries, approval revocation, persistent handoff retries, concurrent retries, adapter failure rollback, mismatch detection, audit tampering, photo metadata removal and expiry, request limits, and local-only configuration. Model adapter tests use controlled HTTP responses and failures; they do not exercise actual model weights.

The dependency stack emitted a Starlette notice that its current `httpx` test-client integration is deprecated. All tests completed successfully with the pinned dependencies. Revisit that integration when upgrading the dependencies.

## What the benchmark says

Of the 62 authored text cases, 37 have a known expected item and 25 require abstention.

| Strategy | Correct item suggestions | Wrong suggestions | Correct abstentions | Missed known items |
| --- | ---: | ---: | ---: | ---: |
| Form only: no automated suggestion | 0 | 0 | 25 | 37 |
| Barcode only | 15 | 3 | 22 | 22 |
| Barcode plus conservative label rules | 35 | 0 | 25 | 2 |

The form-only row does not measure human accuracy. The barcode-only strategy ignores contradictory label text; the combined rules decline those conflicts. These cases were written for development and regression testing, not collected as an independent held-out sample. No operational accuracy or savings claim follows from them.

The three-image OCR result is a separate smoke test. It must not be added to the 62-case denominator. Clear synthetic label illustrations do not represent the range of real warehouse photographs. The browser's photo feature stores evidence; it does not run the OCR CLI or infer quantities.

## Checks still pending

- **Browser interaction and visual review:** Chromium could not launch in the execution environment because its socket setup was denied (`socket() failed: Operation not permitted (1)`). No successful browser-level or visual verification is claimed. `tests/ui_smoke.py` is included for a permitted workstation and exercises the form, approval, photo evidence, mismatch recovery, export, keyboard entry, and a narrow viewport.
- **Actual model evaluation:** no model was selected, downloaded, or run. The optional Ollama adapter has software tests only.
- **Live integrations:** no iBlueprint, WAERlinx, or NetSuite service was contacted. The vendor adapters are explicit extension points, and the exported data contract is not a vendor import format.
- **Other environments:** Python 3.11, Windows, macOS, real mobile devices, and assistive technology have not been tested here. The GitHub Actions workflow is included but has not run on a remote repository.
- **Operational evidence:** staff time, correction effort, hosting/model cost, warehouse accuracy, adoption, food recovery, and user satisfaction have not been measured.

## Reproduce the local checks

From an environment with the pinned Python requirements installed:

```bash
python -m unittest discover -s tests -v
python scripts/export_contracts.py --check
python scripts/demo_walkthrough.py
python -m evaluation.run
```

For the optional OCR check, install Tesseract and its English language data separately, then run `python -m evaluation.ocr_run`. The real-engine test is skipped when the executable is absent; the adapter's failure tests still run. Node.js is needed only for the optional JavaScript syntax command, not for the application itself.

Browser setup and the smoke-test command are documented in [deployment](deployment.md). Use an isolated synthetic database for that test.
