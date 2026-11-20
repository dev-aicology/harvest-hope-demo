# Failure handling and recovery

## The draft's behavior

| Condition | Expected behavior | Receiver or reviewer action |
| --- | --- | --- |
| Unknown item or ambiguous label | Matching abstains; no item is created | Resolve against the approved catalog or keep the receipt in draft |
| Invalid or mismatched barcode | Display an issue; never treat it as a verified catalog match | Check the printed identifier and selected item |
| Missing/invalid quantity, wrong unit, missing required weight/lot/date | Block review submission or approval | Measure or correct the actual value |
| Expired product or `hold` disposition | Block the available-product route | Use the organization's established hold process; do not relabel as available |
| Unchecked line | Block submission | Staff inspect and explicitly confirm it |
| Optional model unavailable, malformed output, or invented item | Fail or abstain safely; do not accept a new catalog ID | Continue with manual entry or deterministic lookup |
| Stale receipt version | Return a conflict without overwriting the current record | Reload, compare changes, and reapply the intended edit |
| Unauthorized demo role | Reject the transition on the server | Use the correct demonstration role; production will require real authentication |
| Reviewer attempts to approve own latest content edit | Reject approval | A different reviewer must approve |
| Approved receipt edited before handoff | Return to draft and clear approval | Submit for fresh review |
| Missing purchase-order reference | Block handoff | Establish the correct existing order through the operational process |
| Same successful handoff key and same payload repeated | Return the saved result | Reuse the original key for a genuine retry |
| Same handoff key with different content | Return a conflict | Investigate; do not reuse a key for another receipt |
| Reconciliation difference | Record `mismatch_mock`; no silent correction | Compare the returned and approved values |
| Invalid, oversized, or expired image | Reject upload or read | Use an appropriate image or collect new permitted evidence |
| Server restart | Session tokens expire; saved receipts remain | Select a new demo session and reload the saved record |

## Limits of recovery

The demonstration's database transactions protect individual operations. They are not a distributed transaction across a warehouse system and NetSuite. Real external timeouts require vendor-specific lookup and reconciliation; blindly retrying an uncertain write could duplicate inventory.

There is no offline synchronization queue in V1. A browser's unsaved entries are not proof that a receipt was saved. Confirm the saved status before leaving the page. Preserve any approved operational fallback during a later pilot.

The sent record is immutable in this draft. A mismatch does not authorize changing the original approved values. Production adjustment, reversal, returns, quarantine, and partial acceptance need their own designed and tested workflows.

## What the tests can and cannot show

Automated tests can show that invalid inputs are rejected, roles and revisions are enforced, retries are bounded by stored keys, and mock reconciliation detects a changed payload. They cannot establish actual warehouse accuracy, staff usability under load, food safety, vendor integration reliability, real identity assurance, or production security. Record those separately during an authorized pilot.
