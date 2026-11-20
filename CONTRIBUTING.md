# Contributing to the receiving draft

This repository is an internal review draft. Coordinate changes with the project owner in the existing project workspace. A public contribution/contact channel has not been established; do not invent an email address for one.

## Make a change

1. Read the [scope and limits](docs/known-limitations.md) and [license status](LICENSE).
2. Create a focused branch and describe the receiving problem the change addresses.
3. Use synthetic fixtures. Do not commit operational records, photos, model weights, credentials, database files, or private source documents.
4. Preserve server-side approval, revision, role, and idempotency controls.
5. Run `python -m unittest discover -s tests -v`. If matching or scoring changed, run `python -m evaluation.run` and review per-case differences.
6. Update the relevant data dictionary, model card, or integration documentation with the behavior that actually exists.
7. Explain the change, checks, limitations, and any manual test needed in the review request.

Avoid adding tests that merely repeat implementation details. Test meaningful outcomes: an invalid unit cannot be approved; a retry cannot duplicate a handoff; a model response cannot invent an accepted catalog item.

## Matching and evaluation

Keep expected labels separate from the matcher. Report abstentions and failures, not only successful predictions. Do not describe rules as AI, authored text as measured OCR output, or a mocked response as a model benchmark.

## Integration changes

Do not replace a mock adapter with a guessed endpoint. Supply the approved vendor API contract, sandbox plan, mapping, access controls, and reconciliation tests. Production writes require their own authorized deployment plan.

## Reporting issues

Use the issue templates after a private remote is configured, or send a concise report through the existing project workspace. Include the software version, expected and observed behavior, and a minimal synthetic example. For security issues, follow [SECURITY.md](SECURITY.md) and keep reports private.
