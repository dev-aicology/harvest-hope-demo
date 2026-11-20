# Synthetic fixtures

Every record in this directory is newly authored example data. No Harvest Hope inventory, staff identity, donor record, delivery, or warehouse photo is included. Product descriptions illustrate common donation categories and package ambiguity; they are not a licensed UPC product database.

| File | Purpose | Evidence status |
| --- | --- | --- |
| `catalog.json` | 16 local products and unit/lot/expiry validation settings | Synthetic settings, not Harvest Hope policy |
| `sample_receipt.json` | Two-line receiving draft | Fictional supplier, PO, lot, quantities and measured weight; staff checkboxes start false |
| `evaluation_cases.json` | 62 labeled suggestion cases | Curated examples, not a held-out warehouse sample |
| `ocr_cases.json` | Expected identity and label text for three OCR smoke images | Separate denominator; not included in the 62 text cases |
| `labels/*.png` | Three exact label illustrations for attachment tests | Not warehouse photographs, not scan-ready optical barcodes |
| `sample_label_transcripts.json` | Clean and noisy example label strings | Hand-authored text, not measured OCR output |
| `generate_fixtures.py` | Recreate all fixture files and images | Uses only Python and Pillow; does not fetch data |

The numeric codes have valid UPC-A/EAN-13 **check digits only**. They are illustrative local identifiers and do not assert a GS1 allocation or a real product identity. Never resolve them through a public UPC service or load them into production inventory. Catalog product IDs all begin with `DEMO-`.

The sample dates are fixed for repeatability. Change them deliberately when preparing a future test; expiry validation should eventually block old examples. Fixture quantity and weight values were supplied explicitly by the author and are never inferred from images.

Regenerate from the repository root:

```bash
python data/synthetic/generate_fixtures.py
```

Pillow renders text labels with a locally available font or its built-in fallback. Image bytes may differ by font availability; content and synthetic markings are the stable contract.

Do not add partner records or photos to this directory. Use a separate, access-controlled evaluation store for permission-cleared pilot material and define retention before collecting it.
