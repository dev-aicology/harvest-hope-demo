# Synthetic data provenance

The demonstration assets under `data/synthetic/` were created for this draft. They represent illustrative products, receipt fields, label text, and expected matching outcomes. They are not copied from Harvest Hope's inventory, donors, purchase orders, actual food labels, or staff work.

## Included assets

- `catalog.json`: 16 invented catalog entries.
- `sample_receipt.json`: one editable example receipt.
- `evaluation_cases.json`: 62 authored matching cases with expected answers.
- `sample_label_transcripts.json`: authored label text, not a measured OCR result.
- `labels/`: three generated label PNGs for beans, oats, and apples.
- `generate_fixtures.py`: regeneration script for the fixtures and images.

The generated text-evaluation report is at `evaluation/results/report.md`; the complete run data is at `evaluation/results/results.json`. A separate real Tesseract run on the three synthetic label images is recorded in `evaluation/results/ocr_report.md` and `ocr_results.json`. Its extracted text is actual OCR output; the independently authored transcript fixtures remain synthetic text examples. These counts describe this draft's supplied artifacts, not operational coverage.

## What the assets mean

| Asset | Intended use | Limitation |
| --- | --- | --- |
| Product catalog | Exercise known-item matching, unit checks, and required fields | Not a production item master |
| Receipt fixtures | Walk through drafts, validation, and review | No transaction occurred |
| Label images | Exercise image storage and provide readable fictional labels | Generated fixtures, not photographs of real stock |
| Typed/OCR-like text examples | Exercise noisy or ambiguous label inputs | Authored text; no OCR engine's measured output |
| Separate OCR results | Record Tesseract output and catalog matches from the three label images | A tiny synthetic image check, not warehouse-photo validation |
| Expected answers | Independent test labels supplied to the evaluator | Authored ground truth, not field-observed accuracy |

Example barcode strings may have valid check digits so checksum logic can be exercised. They are illustrative identifiers inside this local catalog. Do not represent them as registered GS1 allocations or query outside suppliers with them. The default implementation makes no public barcode lookups.

The evaluator supplies only the permitted barcode/text and catalog to matching methods. Expected labels are held separately for scoring. Keep that separation when adding adapters or benchmarks.

`evaluation/observations.template.csv` contains only a header, with no staff-time, accuracy, or cost observations. The supplied observations summary explicitly reports that no observations exist. Do not treat blank or null values as zero.

## Adding real examples later

Obtain the relevant permissions, minimize fields, remove visible and embedded personal information, and review whether a public example could reveal operational details. Keep private pilot data outside the tracked source tree. Capture its provenance, selection process, labeling method, corrections, and authorization separately.

Do not tune repeatedly on a test set and then call it independent validation. Keep representative held-out examples, include unknown and ambiguous items, and retain failed runs. Record actual timestamps and hardware for performance measurements.

## Original source material

The supplied iBlueprint notes, inventory manual, and planning documents informed scope. Their original contents and private records are not included in the repository. [Sources and decisions](sources-and-decisions.md) records the relevant provenance without redistributing those files.
