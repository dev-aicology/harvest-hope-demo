# Matching mechanisms and model cards

No language or vision-language model is selected, bundled, downloaded, or required by the default application. A default run must not be described as a small-language-model deployment. The optional OCR CLI uses an already installed Tesseract engine and English recognition data; that is a separate mechanism and evaluation.

| Mechanism | What it does | What has been established |
| --- | --- | --- |
| Form only | Staff choose the item and enter measured information | Implemented interface and validation; human performance not measured |
| Barcode lookup | Validate an identifier and look it up in a synthetic catalog | Deterministic behavior can be tested; no public barcode database |
| Label rules | Match supported typed phrases conservatively | Deterministic text matching, not OCR or a model |
| Optional local Ollama model | Suggest a known catalog item from typed text | Adapter exists; model choice and real model performance remain unverified until run |
| Optional Tesseract OCR CLI | Extract text from local label images, then match catalog names | Ran on three synthetic label illustrations: three correct suggestions; separate from the 62-case text benchmark |
| Browser photo inference / vision model | Possible later aid for unreadable labels | Not implemented; uploaded browser images remain evidence only |

See [deterministic matching](deterministic-matching.md), [optional Ollama](optional-ollama.md), and the [OCR protocol and measured report](../../evaluation/README.md). Tesseract's executable/version and measured output are recorded in the separate OCR result; this is not a small-language-model benchmark. Add a completed, versioned card for every actual model evaluated. Preserve unsuccessful results as well as successes.

## Required fields for an evaluated model

- Exact model ID, version/digest, parameter count, quantization, license, and source.
- Inference runtime and version, hardware, memory, configuration, and network/data flow.
- Intended task and explicit excluded decisions.
- Evaluation dataset version, selection method, independent labels, and known gaps.
- Coverage, exact-match accuracy, precision among attempted matches, abstention quality, errors, latency distribution, and observed resource/cost measures.
- Human correction effort, staff time, and operational incidents when measured in a real pilot.
- Deployment date, scope, owner, update procedure, and rollback plan.

Leave missing values as “not measured” or “not selected.” A guessed parameter range or a model's own confidence value is not evaluation evidence.
