"""Application-owned contracts. These are NOT WaerLinx or iBlueprint API schemas."""
from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

from receiving.store import digest, now


def approved_payload(receipt):
    return {
        "schema_version": "receiving-draft/1", "receipt_id": receipt["id"],
        "supplier": receipt["supplier"], "delivery_ref": receipt["delivery_ref"],
        "warehouse": receipt["warehouse"], "purchase_order_ref": receipt["purchase_order_ref"],
        "received_on": receipt["received_on"],
        "lines": [{k: line.get(k) for k in (
            "line_id", "product_id", "quantity", "unit", "measured_weight",
            "weight_unit", "lot", "expiry_date", "disposition")}
            for line in sorted(receipt["lines"], key=lambda x: x["line_id"])],
    }


class MockWarehouseAdapter:
    """Persists simulation results in the same local DB transaction as the event."""
    mode = "mock"

    def send(self, payload):
        return {"mode": "mock", "external_receipt_ref": "MOCK-WAER-" + str(uuid4()),
                "accepted_at": now(), "payload_hash": digest(payload),
                "netsuite_status": "pending_mock_reconciliation",
                "message": "Local simulation only. No external inventory was changed."}

    def observe(self, payload, simulate_mismatch=False):
        observed = deepcopy(payload)
        if simulate_mismatch and observed["lines"]:
            line = observed["lines"][0]
            line["quantity"] = str(Decimal(str(line["quantity"])) + 1)
        return observed


def compare_receipts(expected, observed):
    """Compare the complete neutral receipt, not just a vendor success flag."""
    mismatches = []

    def visit(left, right, path):
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(left.keys() | right.keys()):
                if key not in left or key not in right:
                    mismatches.append({"path": f"{path}.{key}", "expected": left.get(key), "observed": right.get(key)})
                else:
                    visit(left[key], right[key], f"{path}.{key}")
        elif isinstance(left, list) and isinstance(right, list):
            if len(left) != len(right):
                mismatches.append({"path": path + ".length", "expected": len(left), "observed": len(right)})
            for index, (a, b) in enumerate(zip(left, right)):
                visit(a, b, f"{path}[{index}]")
        elif left != right:
            mismatches.append({"path": path, "expected": left, "observed": right})

    visit(expected, observed, "receipt")
    return mismatches


class IBlueprintAdapter:
    """Boundary for future licensed, documented vendor integration."""
    def execute(self, *_args, **_kwargs):
        raise NotImplementedError("Confirm iBlueprint execution schema, authentication, data terms and workflow IDs before implementing this adapter.")


class LiveWaerLinxAdapter:
    def send(self, *_args, **_kwargs):
        raise NotImplementedError("Live WaerLinx handoff is not implemented. Validate vendor APIs and receiving controls in a sandbox first.")
