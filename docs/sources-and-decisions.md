# Sources and implementation decisions

## Project evidence

| Source | What it supports | What it does not establish |
| --- | --- | --- |
| User clarification in this project | A conventional digital receiving form is already used; separate AI tools are used without a connection to it | Actual user counts, selected model IDs, or deployment of an integrated AI product |
| Private project planning notes | Example workflows, proposed orchestration role, barcode-first receiving, staff validation, possible later donation matching, and proposed pilot range | A verified live Harvest Hope integration, a public API contract, or an agreed price |
| Private inventory-process documentation | Existing division of responsibilities and the documented NetSuite purchase-order to WAERlinx receiving sequence | That every old step or interface remains current |
| Internal Mozilla application V1 repository checklist | Requested code, workflow, configuration, synthetic examples, evaluation, governance, and contribution documents | Production readiness or grant eligibility |

Private source files are not copied into this repository. Confirm current operations with the responsible staff before connecting anything.

## Private references

Private workflow URLs and identifiers are omitted from this distribution. Planning references do not establish a supported API, a deployed integration, or permission to redistribute third-party implementations.

## Draft design choices

| Choice | Reason |
| --- | --- |
| Python service, SQLite, plain web interface | Keep a reviewable local demo with few moving parts |
| Synthetic catalog and receipts only | Make behavior reproducible without exposing operational data |
| Deterministic lookup before a model | Test whether ordinary lookup resolves the task before adding inference |
| Optional local-model adapter without a model choice | Permit later experiments without claiming an unverified model or silently sending data externally |
| Separate receiver and reviewer states | Make responsibility and approval visible |
| Approved revision, idempotency, and reconciliation | Demonstrate controls required before inventory integration |
| Mock warehouse adapter | Avoid inventing a vendor API or treating an unverified mapping as operational |
| Proposed MIT license held for review | Make the intended open-code decision concrete while preserving partner ownership review |

These are decisions made for this draft, not previously approved requirements or claims about existing deployed systems.

## Primary technical references

- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Python sqlite3](https://docs.python.org/3/library/sqlite3.html)
- [Pillow image handling](https://pillow.readthedocs.io/en/stable/reference/Image.html)
- [Tesseract command-line usage](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)

Library/runtime versions are pinned in the repository requirements. Documentation links explain mechanisms; they do not validate operational results.
