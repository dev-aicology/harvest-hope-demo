# Synthetic receiving-assistant benchmark

> Generated from synthetic cases. These are software checks, not deployed-user evidence.

Run: 2026-11-18T04:42:29.717037+00:00

62 curated cases; 16 synthetic catalog products.

The form-only row represents **no automated suggestion**. Staff performance was not measured. A model and an OCR engine were not run unless explicitly listed below. Rule matching on hand-authored label text is not OCR.

| Strategy | Suggestions | Correct matches | Wrong suggestions | Correct abstentions | Missed matches | Errors | Coverage | Suggestion precision | Known-item recall | Exact decisions | Median algorithm ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| form_only | 0 | 0 | 0 | 25 | 37 | 0 | 0.0% | — | 0.0% | 40.3% | 0.0018 |
| barcode_only | 18 | 15 | 3 | 22 | 22 | 0 | 29.0% | 83.3% | 40.5% | 59.7% | 0.0030 |
| barcode_plus_label_rules | 35 | 35 | 0 | 25 | 2 | 0 | 56.5% | 100.0% | 94.6% | 96.8% | 0.0602 |
| barcode_then_local_model (not run) | — | — | — | — | — | — | — | — | — | — | — |

## Interpretation

- Barcode-only ignores label text, so contradictory label/scan examples reveal a limitation. Combined rules decline these conflicts.
- Exact decisions include correct abstentions. A system that always abstains may score well on unknown cases while offering no matches; coverage, precision, and known-item recall must be read together.
- Every suggestion still requires staff confirmation. A correct item identity does not verify quantity, weight, condition, expiry, lot, or food safety.
- Elapsed milliseconds measure a single local software call. They exclude scanning, reviewing, corrections, and handoff work; these figures cannot establish staff time saved.
- Staff time and operating cost are unknown. No model performance, token cost, dollar savings, or pilot adoption is inferred from these fixtures.
- The cases are curated and not a blind held-out sample. Production validation requires permission-cleared representative transactions and independent annotations.

See `evaluation/README.md` for the protocol and `results.json` for per-case outcomes.
