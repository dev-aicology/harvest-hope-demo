# Data dictionary

This vocabulary belongs to the demonstration. It is not a statement of WAERlinx, NetSuite, or iBlueprint field names. The HTTP schema exposed by the running service is the authoritative validation schema for this version.

## Receipt

| Field | Meaning and validation intent |
| --- | --- |
| `id` | Application-generated receipt identifier |
| `version` | Integer revision used for optimistic concurrency; send the current value as `expected_version` when changing a record |
| `status` | `draft`, `in_review`, `approved`, `sent_mock`, `reconciled_mock`, or `mismatch_mock` |
| `supplier` | Human-readable supplier name for the demo; production should map to a controlled supplier ID |
| `delivery_ref` | Reference for one physical delivery; must not be reused as if it meant a purchase order |
| `warehouse` | Receiving site identifier; synthetic in this draft |
| `purchase_order_ref` | Existing order reference; required before handoff, not created by the app |
| `received_on` | Receiving calendar date in `YYYY-MM-DD` format |
| `notes` | Bounded staff notes; avoid personal information |
| `lines` | Receipt lines, identified by stable `line_id` values |
| `created_by`, `last_edited_by` | Demo actor identifiers attached by the server |
| `approved_by` | Reviewer who approved the current revision, or null |
| `created_at`, `updated_at` | Server timestamps |
| `flags` | Validation findings with `code`, `severity`, `message`, and optional `line_id` |
| `suggestions` | Proposed item matches and their provenance, separate from confirmed line fields |
| `photos` | Local evidence references and retention metadata |
| `handoff` | Persisted mock transaction result, or null |

Drafts may be incomplete. Submitting for review requires at least one valid line and each required field for that line. A completed draft alone is not an accepted stock record.

## Receipt line

| Field | Meaning and validation intent |
| --- | --- |
| `line_id` | Stable unique identifier within a receipt; preserve it when editing |
| `product_id` | Known catalog item; null until resolved; unknown items are not created automatically |
| `barcode` | Typed or scanner-entered identifier; preserve leading zeroes as a string |
| `description` | Staff-observed description, distinct from canonical catalog name |
| `quantity` | Actual positive finite quantity; whole number for `case` and `each` |
| `unit` | `case`, `each`, `lb`, or `kg`; must match the selected catalog item |
| `measured_weight` | Actual positive measured weight when the catalog requires it |
| `weight_unit` | `lb` or `kg` for measured weight; not inferred from an image |
| `lot` | Staff-confirmed lot identifier when required |
| `expiry_date` | Staff-confirmed date when required; expired items cannot proceed through the available-product route |
| `disposition` | `available` or `hold`; a held line blocks this draft's handoff route |
| `checked` | Receiver's explicit confirmation; a suggestion does not set it |

V1 does not convert units, infer pack sizes, decide safe shelf life, or override hold procedures. Those are operational decisions with separate acceptance requirements.

## Catalog item

| Field | Meaning |
| --- | --- |
| `product_id` | Synthetic item identifier beginning `DEMO-` |
| `name` | Canonical demonstration product description |
| `barcode` | Synthetic UPC-A/EAN-13 example or null; not a license to query real suppliers |
| `category` | Demonstration grouping |
| `unit` | Receipt unit accepted for the item |
| `requires_weight`, `requires_lot`, `requires_expiry` | Rules determining mandatory evidence |
| `aliases` | Explicit matching phrases; variants that remain ambiguous require review |

## Suggestion, evidence, and handoff

A suggestion includes `product_id` or null, `method`, `reason`, and `requires_review: true`. `barcode` and `label_rules` identify deterministic mechanisms. An optional model response must identify its method and be checked against the allowed catalog. A model's self-reported confidence is not a calibrated accuracy measurement.

Photo metadata includes an opaque `id`, a display `name`, `media_type`, dimensions, and `expires_at`. Images remain evidence; the current API does not perform OCR or vision inference.

The separate Tesseract evaluation CLI reads permitted local synthetic label files and writes its own measured OCR report. It is not a photo-inference API and does not update receipt fields.

A handoff binds an idempotency key to the approved content. Its identifiers and statuses are marked as mock. A reconciliation result compares the saved approved values with the simulated returned values. A mismatch is an unresolved result, not permission to silently rewrite either side.
