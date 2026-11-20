# Privacy, retention, and local evidence

## Data flow in the default demo

The default application processes synthetic records on the local machine. It makes no calls to a model provider, iBlueprint, WAERlinx, NetSuite, analytics, or a public barcode database. Matching uses the included synthetic catalog. The local browser communicates with the local Python service.

If an operator enables the Ollama adapter, typed label text and the relevant catalog context are sent to the configured model service. That is a separate data processor and should be reviewed accordingly. The V1 photo route does not send images to the model. The model provider, weights, and any service logging are outside this repository's control.

The optional OCR CLI invokes an already installed local Tesseract process on permitted local files. It writes extracted text into a local evaluation report. The included run uses only three synthetic label illustrations. This is separate from the web application's evidence-photo route and makes no remote OCR request.

## Data inventory

| Data | Location | Handling in V1 |
| --- | --- | --- |
| Receipt entries and revisions | Local SQLite database | Kept for demonstration history; no automatic whole-record deletion |
| Suggestions and corrections | Database and audit events | Kept separate from staff-confirmed entries |
| Demo actor IDs | Database and in-memory sessions | Fixed demo identities; not verified personal identities |
| Session tokens | Server and browser memory | Not a persistent sign-in credential |
| Evidence photos | Local photo directory | JPEG/PNG only; size and decode validation; metadata removed; expiry enforced |
| Photo metadata | Database and audit references | Kept after byte removal to explain what happened |
| Mock handoffs and reconciliation | Local database | No external inventory effect |
| Evaluation fixtures/results | Repository/evaluation output | Synthetic; do not replace them with real records in a public branch |

## Photo policy

The demonstration defaults to seven days of photo retention and a 4 MiB upload limit. Access through the API is denied after expiry. Startup and the maintenance command physically remove expired local copies; there is no recurring scheduler during a long session. A manual deletion route is available for draft photo evidence, with the deletion recorded in the audit trail.

Re-encoding removes metadata such as EXIF, but it does not remove personal or confidential information visible in the pixels. The same limitation applies to text notes. Do not upload faces, license plates, donor contact details, account credentials, or other private material to this demo.

Deleting the active image does not erase browser downloads, exported files, backups, operating-system caches, or copies held by other tools. Backups need their own retention policy. This repository does not claim secure erasure from storage media.

## Governance decisions for a pilot

Harvest Hope and the delivery team should agree who can access each record, who can approve exceptions, how long each data type is retained, whether images are necessary, how staff request a correction, and which model providers may receive data. These decisions are proposed operating requirements, not an assertion that the current form already implements them.

Use the minimum evidence needed to resolve a receipt. If barcode and typed fields are sufficient, no photo is required. Keep a manual route available when photography or model processing is inappropriate.

## Publishing

Publish only original code, documented methods, and synthetic or expressly cleared examples. Do not publish the uploaded inventory manual, meeting transcripts, actual product catalogs, receiving photos, purchase orders, private partner links that reveal records, or environment files containing secrets. The supplied source documents are summarized in [sources and decisions](sources-and-decisions.md); their bytes are not redistributed here.
