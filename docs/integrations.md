# Integration boundaries

## Implemented, simulated, and proposed

| Interface | V1 behavior | Work still required |
| --- | --- | --- |
| Local form and catalog | Runs in this repository | Compare fields with the real receiving form and item master |
| Ollama | Optional text-matching adapter; configured separately | Select and obtain a model, verify its license/size, measure quality on relevant data |
| iBlueprint | Conceptual workflow and adapter boundary only | Confirm supported execution API, authentication, input/output schema, review mechanism, errors, logging, and licensing with the vendor |
| WAERlinx | Local mock handoff and mock receipt reconciliation | Obtain supported API documentation and sandbox access, map fields, test every write and failure path |
| NetSuite | No direct calls or writes | Validate the existing WAERlinx exchange and reconciliation evidence with the system owner |

No URL in this repository is an invented iBlueprint or WAERlinx execution endpoint. Private planning references do not establish an API contract or a deployed Harvest Hope integration.

## iBlueprint's proposed role

Project planning notes describe orchestration of AI, business rules, human approvals, and external systems. The intended receiving workflow could use those capabilities to select a matching step, route an exception, request staff review, and invoke an approved handoff. The conceptual JSON in `workflows/receiving.workflow.json` describes those decisions in this project's vocabulary. It is **not** a native iBlueprint export and must not be advertised as directly importable.

The application keeps a deterministic fallback and a separate staff review step. A future iBlueprint adapter must not turn an uncertain result into an accepted inventory quantity or use an execution success status as proof that NetSuite inventory reconciled.

## WAERlinx first, with the right prerequisites

The proposed destination for an approved physical receipt is WAERlinx. The existing NetSuite purchase order and its WAERlinx counterpart must already be identified. Creating a purchase order, defining a new item, receiving a pallet, printing an F tag, and changing stock are distinct operations. V1 creates none of them.

The neutral export contains the approved receipt and related mock result. It is for review and adapter development; it is not certified as a WAERlinx import file. Do not upload it into a production system without an approved mapping.

## Required vendor contract decisions

1. Supported API operations, versioning, authentication, and sandbox environment.
2. Immutable item identifiers and the exact interpretation of cases, each, pounds, and kilograms.
3. Purchase-order, receipt-line, lot, expiry, pallet, location, and hold representations.
4. Whether partial receipts and held product use separate lines or a separate exception flow.
5. Idempotency or external-reference guarantees, timeout behavior, and safe retry boundaries.
6. Returned warehouse transaction IDs and evidence of subsequent NetSuite reconciliation.
7. Permissions, rate limits, audit access, export rights, license terms, and support ownership.

Until these are answered, use the mock adapter and reviewed manual entry into the operational tools. Turning on a network URL is not an implementation of a vendor contract.

## Future handoff acceptance

A real adapter should receive only an immutable approved revision. It should persist its own request reference before transmitting, save the vendor response, treat an ambiguous timeout as unresolved, and query by the original reference before retrying. It should reconcile line IDs, products, units, actual quantities, measured weights, lots, and dates. Reconciliation must explicitly identify a difference instead of merely checking that an HTTP request succeeded.

See [failure handling](failure-handling.md) for the draft's behavior and [pilot plan](pilot-and-acceptance.md) for the operational validation sequence.
