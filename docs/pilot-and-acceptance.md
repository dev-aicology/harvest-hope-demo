# Proposed pilot and acceptance plan

This is a plan for a later authorized pilot. No warehouse deployment or participant study is reported by this repository.

Pilot duration, transaction count, scope, and budget must be agreed with the participating warehouse. This repository does not report a completed study or an implementation quote.

## Sequence

| Phase | Purpose | Evidence required to continue |
| --- | --- | --- |
| Confirm the work | Map the actual digital form, staff roles, item master, receipt units, and exception paths | Warehouse owner agrees the map and required fields |
| Establish a baseline | Observe current form use with representative delivery types | End-to-end staff time, corrections, errors, and transaction mix recorded using defined measures |
| Shadow the proposed workflow | Test capture, matching, review, and errors without live inventory writes | Staff can complete the work, inspect suggestions, and recover from mistakes |
| Compare assistance | Compare form only, barcode assistance, and any actually implemented OCR/model assistance | Held-out, staff-confirmed examples; all configurations and errors preserved |
| Validate interfaces | Test authorized vendor sandbox operations and reconciliation | Written API mapping, duplicate/retry tests, partial-receipt behavior, and rollback process |
| Limited operational pilot | Use a small agreed scope with active support | Explicit go/no-go decision and documented fallback |

Donation matching is a possible second workflow once receiving data is dependable. Donor outreach is not part of this first build. Vendor capabilities can be researched early, while any production handoff follows validation of receiving and review behavior.

## Measures

| Measure | Definition |
| --- | --- |
| Time per accepted receipt | Total staff time through capture, checking, correction, and accepted completion; do not measure only the model call |
| Correction effort | Fields corrected, rework minutes, and staff interventions |
| Matching precision and coverage | Correct suggestions among attempted suggestions, alongside the proportion of eligible cases receiving one |
| Unknown/ambiguous handling | Cases correctly routed to review versus unsafe or unsupported suggestions |
| Inventory discrepancy rate | Differences between approved receiving evidence and the returned operational records |
| Cost per accepted receipt | Allocated inference, hosting, support, and staff effort under explicit assumptions |
| Staff experience | Task completion, comprehension of suggestions and approval, perceived burden, and continued use |

Set quantitative improvement targets after the baseline is measured. Do not turn an illustrative target into a claim of achieved savings.

## Release acceptance scenarios

- A normal case-count receipt can be captured, checked, independently approved, and reconciled.
- A mixed donation requires its actual measured weight; a photograph cannot replace the measurement.
- A wrong pack size or unit is detected before handoff.
- Unknown products, unclear labels, held product, expired dates, and missing lot data remain unresolved until a person follows the correct procedure.
- A stale edit cannot overwrite a newer receipt; an edit after approval removes that approval.
- An unauthorized person cannot approve or send a receipt; identities are real in the eventual pilot.
- A timeout, repeated request, or server restart does not create an untracked duplicate.
- An incorrect returned quantity or line identity is detected and assigned for investigation.
- Model failure leaves a usable manual path; external content cannot approve or dispatch a record.
- The layout and controls work with the participating staff's devices and access needs.
- Photo access expires and physical cleanup actually runs; retained audit evidence follows the agreed policy.

The production API, identity, security, food-handling, and support requirements cannot be satisfied by the demonstration alone. Record the owner and result of each acceptance scenario before expanding scope.
