# Running and configuring the demonstration

## Supported environment

Run the repository on a trusted workstation with Python 3.11 or later. The web interface is served by the Python application, so Node.js and a frontend build are not required. Follow the [README](../README.md) for installation.

The app accepts only the demo mode and loopback binding. It is not designed for hosting on a public URL, a shared server, or a multi-user production network. Use synthetic data. The selectable Receiver and Reviewer identities demonstrate role checks; they do not authenticate a real person.

## Configuration

Read `.env.example` as a configuration template. Setting an environment variable is distinct from merely editing the example file; export the values in your shell unless the launcher explicitly loads an environment file.

| Variable | Default | Meaning |
| --- | --- | --- |
| `HH_MODE` | `demo` | Only supported application mode; production/live values are rejected |
| `HH_HOST` | `127.0.0.1` | Must be loopback |
| `HH_PORT` | `8000` | Local HTTP port |
| `HH_DATA_DIR` | `var` | SQLite database and photo storage; excluded from version control |
| `HH_AI_PROVIDER` | `disabled` | `disabled` or `ollama`; no model requests by default |
| `HH_OLLAMA_URL` | `http://127.0.0.1:11434` | Explicit local Ollama endpoint |
| `HH_OLLAMA_MODEL` | Empty | Operator-selected, already available model; no automatic download |
| `HH_INTEGRATION` | `mock` | Only supported warehouse integration; live values are rejected |
| `HH_PHOTO_RETENTION_DAYS` | `7` | Photo retention period for the demo; allowed range 1–30 days |
| `HH_MAX_PHOTO_BYTES` | `4194304` | Maximum uploaded JPEG/PNG size; allowed range 1 KiB–4 MiB |

Session tokens are held in process memory and are lost at restart. Receipts, handoffs, and audit history remain in the data directory. Restarting the service is not a data reset.

## Optional local-model matching

The default rules work without an AI model. To evaluate a model, separately install a local Ollama service and obtain an appropriate model under its applicable license. Verify its exact name, parameter count, supported capabilities, hardware requirements, and data behavior. Then configure the app, for example in a POSIX shell:

```bash
export HH_AI_PROVIDER=ollama
export HH_OLLAMA_URL=http://127.0.0.1:11434
export HH_OLLAMA_MODEL='YOUR_INSTALLED_MODEL_TAG'
python -m receiving
```

`YOUR_INSTALLED_MODEL_TAG` is a placeholder, not a recommended model. Enabling the adapter does not prove model accuracy, Mozilla eligibility, or a particular model size. See the [local-model card](model-cards/optional-ollama.md). This version sends text for catalog matching, not photo evidence. Keep the service on a controlled local machine. Review deployment-specific request logging before using authorized operational data in a later pilot.

## Optional OCR check

If Tesseract and its English (`eng`) language data are already installed on the machine, run:

```bash
python -m evaluation.ocr_run
```

This command extracts text from the three supplied synthetic label PNGs and applies catalog matching. It uses a bounded local subprocess, no shell, and no downloads or remote OCR. It writes a separate [OCR report](../evaluation/results/ocr_report.md). Missing prerequisites are reported explicitly. This does not enable OCR in the browser photo-upload route or provide a vision model.

## Storage and retention

The configured data directory contains `receiving.sqlite3` and photos. Treat the whole directory as operational data, even when the demonstration currently contains synthetic examples. It must not be committed to Git or attached to a public issue.

Expired photos cannot be read through the application. Physical deletion runs at application startup and can be run during a long session with the maintenance command:

```bash
python -m receiving.maintenance purge-expired-photos
```

The purge is not scheduled while a process remains running; run the maintenance command to remove expired bytes during a long session. If a pilot is later authorized, the operator must arrange and verify an appropriate maintenance schedule. Audit references remain after photo bytes are removed. Retention details and backup limitations are in [privacy and retention](privacy-and-retention.md).

For an isolated test, set `HH_DATA_DIR` to a fresh temporary directory. Shut the application down before making a filesystem backup. If replacing data with a backup, treat the copy as sensitive and verify the audit chain and handoff state before continuing. Do not delete a directory simply to fix a failed transition; preserve the evidence and investigate.

## API and browser checks

The local API specification is available at `/openapi.json`; checked-in JSON Schemas are in `contracts/`. The default Swagger and ReDoc HTML pages are disabled so the demo does not require CDN resources. Refresh the checked-in schemas with `python scripts/export_contracts.py`.

For an optional real-browser check, install the development dependencies and Playwright's browser in a permitted local environment:

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python tests/ui_smoke.py --base-url http://127.0.0.1:8000
```

Run that test against an isolated demo database. It creates synthetic records. The included verification report distinguishes API checks from browser checks.

## Before any shared or operational deployment

The following require implementation and review, not a configuration switch: real authentication, organization-level access boundaries, transport encryption, secure token lifecycle, secrets management, monitoring, reviewed backups, access-controlled audit storage, API contracts, dependency maintenance, support ownership, and disaster recovery. There is intentionally no supported production mode in V1.

To prepare a later repository remote, use a private repository first, review the license and partner permissions, and push only the tracked source tree. Do not include `var/`, model weights, original partner documents, credentials, or exported operational data. This draft does not create or publish a remote repository.
