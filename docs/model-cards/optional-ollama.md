# Optional local text-matching model card

**Status:** adapter available; model not selected. Default provider is disabled. No model weights or production-model results are included.

| Field | V1 value |
| --- | --- |
| Intended task | Suggest one known catalog item from typed label text, or abstain |
| Model ID / version / digest | Not selected; set explicitly for each run |
| Parameter count / quantization | Not established |
| Model license | Not established; must be checked for the selected weights |
| Runtime | Operator-configured local Ollama service |
| Hardware | Operator-supplied; not benchmarked here |
| Image processing | Not enabled by the V1 application |
| External inventory permissions | None |
| Performance | Not measured until an actual configured model run succeeds |

## Contract

The adapter sends catalog context and bounded label text to a local `/api/chat` endpoint and requests structured output. Returned data is validated against the application's allowed schema and catalog. Structured output makes the response parseable; it does not guarantee factual correctness. Unknown product IDs must be rejected. Errors must leave the receipt available for manual resolution.

All model output remains a suggestion. It does not approve a receipt, create a product, estimate hidden quantities, establish a weight, or make a food-safety decision.

## Privacy and threat model

Model input is untrusted evidence. A label can contain text that resembles an instruction; that must not give it access to tools, secrets, inventory, or workflow transitions. The model has no handoff authority. The human approval and server validation rules apply regardless of its response.

The configured inference service may keep its own logs. “Local” does not automatically mean confidential, reliable, inexpensive, or suitable for the task. Document the service's settings and hardware before an operational pilot.

## Evaluation plan

Run the same independently labeled cases used for the deterministic baselines, with the exact model settings saved in the report. Report attempted-match precision and coverage together. Record model failures, invalid outputs, abstentions, and latency. Do not fill missing results with estimates. Add staff-time and cost measurements only when collected under a defined study protocol.

## Technical references

- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)

These references define the optional local API mechanism. They do not establish an approved model choice or the capabilities of iBlueprint.
