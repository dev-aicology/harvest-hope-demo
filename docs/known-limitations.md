# Known limitations

## Operational

- This is a new local demonstration, not the existing Harvest Hope form or a deployed receiving product.
- The catalog, identifiers, images, receipts, and evaluation examples are synthetic.
- Real supplier records, item mappings, units, devices, network conditions, and staff processes have not been validated.
- Whole/partial acceptance, returns, adjustments, reversal, quarantine release, recall, pallet labeling, and putaway remain outside V1.
- A held or expired line blocks this draft's available-product route. The application does not decide whether food is safe.
- No quantities, hidden counts, weights, or shelf-life conclusions are inferred from images.

## Technical

- iBlueprint, WAERlinx, and NetSuite integration is not implemented; handoff and reconciliation are local simulations.
- The neutral export and conceptual workflow JSON are project-owned representations, not vendor-compatible import formats.
- Browser photo upload is evidence storage only. An optional Tesseract CLI performs a separate OCR check on synthetic labels; it does not provide browser photo inference, optical barcode scanning, counting, or a vision model.
- Default label matching is deterministic; it must not be described as an AI feature.
- Optional model inference requires a separate service and actual model selection. It has not been validated just because the adapter tests pass.
- Local demo identities are freely selectable and do not authenticate real staff.
- The service is limited to loopback and a local data store. No production mode, multi-tenant isolation, SSO, or shared-host hardening is provided.
- Offline sync, concurrent multi-device rollout, camera barcode decoding, and automatic stock updates are absent.
- Audit hashes help detect inconsistent history; they are not an independent or administrator-proof record.
- Photo cleanup runs at application startup and through the maintenance command. No recurring purge runs during a long session; exports and backups are outside its reach.

## Evidence

Synthetic evaluation results establish behavior on authored test cases. The 62-case text comparison and the three-image OCR check use different inputs and denominators. The OCR check produced three correct item suggestions on synthetic label illustrations; it does not establish accuracy on real warehouse photos. No Ollama language-model inference has been run. Staff time and operating cost remain unmeasured; the observation template is empty.

These results do not establish warehouse accuracy, staff-time savings, adoption, model suitability, grant eligibility, or a deployed user count. Browser execution was blocked by the build environment's process/socket restrictions, so a rendered UI, screen-reader use, and real device behavior still need manual verification.

See [pilot and acceptance](pilot-and-acceptance.md) for the next evidence to collect.
