# Optional local OCR smoke results

> This is a three-image synthetic smoke test. It is separate from the 62-case text benchmark and is not warehouse deployment evidence.

Run: 2026-11-18T04:42:45.760111+00:00

Local Tesseract, fixed eng language and psm 6; no downloads or external calls

OCR succeeded on 3 / 3 images; exact item names were recovered on 3 / 3; item suggestions matched on 3 / 3.

| Case | OCR status | Suggested item | Correct item | OCR call ms |
| --- | --- | --- | --- | ---: |
| OCR-SYN-001 | ok | DEMO-BEANS-CASE | True | 478.34 |
| OCR-SYN-002 | ok | DEMO-OATS-CASE | True | 633.46 |
| OCR-SYN-003 | ok | DEMO-APPLES-LB | True | 366.72 |

The adapter extracts text locally; exact catalog-name rules then propose an item. Expected IDs and expected label strings are used only by the scorer. Embedded catalog-ID text is not used for matching.

The PNGs contain clear synthetic labels and were generated for this demo. These results do not predict performance on damaged, curved, small, rotated or poorly lit real labels. No optical barcode decoder, vision model, quantity inference, or weight inference is involved. Every suggestion needs staff review.

Elapsed time covers image validation and OCR process execution. Staff time and all operational costs are unmeasured. The local language model remains unrun.
