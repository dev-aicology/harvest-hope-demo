"""Receiving state transitions and staff-controlled approvals."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
from uuid import uuid4

from receiving.ai import suggest_with_ollama
from receiving.integrations import MockWarehouseAdapter, approved_payload, compare_receipts
from receiving.matching import load_catalog, match_item, validate_barcode
from receiving.store import Store, WorkflowError, canonical, digest, now


class Workflow:
    def __init__(self, settings):
        self.settings = settings
        self.store = Store(settings.data_dir)
        self.catalog = load_catalog()
        self.products = {p["product_id"]: p for p in self.catalog}
        self.adapter = MockWarehouseAdapter()

    @staticmethod
    def require_role(actor, role):
        if actor["role"] != role:
            raise WorkflowError(f"This action requires the {role} demo role.", 403)

    def flags(self, receipt):
        flags = []
        def flag(code, message, line_id=None, severity="blocking"):
            flags.append({"code": code, "message": message, "line_id": line_id, "severity": severity})
        if not receipt["lines"]:
            flag("empty_receipt", "Add at least one received item.")
        if date.fromisoformat(receipt["received_on"]) > date.today():
            flag("future_receipt", "The receiving date cannot be in the future.")
        if not receipt["purchase_order_ref"]:
            flag("missing_po", "A verified existing purchase order reference is required before handoff.", severity="warning")
        for line in receipt["lines"]:
            lid = line["line_id"]
            product = self.products.get(line.get("product_id"))
            if not product:
                flag("unknown_item", "Choose an existing catalog item or resolve the item with inventory staff.", lid)
            if line.get("barcode"):
                if not validate_barcode(line["barcode"]):
                    flag("invalid_barcode", "Correct or clear the barcode; its format or check digit is invalid.", lid)
                else:
                    matches = [p for p in self.catalog if p.get("barcode") == line["barcode"]]
                    if matches and line.get("product_id") not in {p["product_id"] for p in matches}:
                        flag("barcode_conflict", "The selected product conflicts with the scanned barcode.", lid)
                    elif not matches:
                        flag("unmapped_barcode", "This barcode has no catalog mapping. Verify the manually selected item.", lid, "warning")
            qty = Decimal(str(line["quantity"])) if line.get("quantity") is not None else None
            if qty is None or qty <= 0:
                flag("missing_quantity", "Enter the actual received quantity, greater than zero.", lid)
            if line.get("unit") in {"case", "each"} and qty is not None and qty != qty.to_integral_value():
                flag("fractional_count", "Case and each counts must be whole numbers.", lid)
            if product and line.get("unit") != product["unit"]:
                flag("unit_mismatch", "Use the catalog unit; this draft does not infer case-to-each or weight conversions.", lid)
            weight = Decimal(str(line["measured_weight"])) if line.get("measured_weight") is not None else None
            if product and product.get("requires_weight") and (weight is None or weight <= 0 or not line.get("weight_unit")):
                flag("missing_weight", "Record an actual scale weight and its unit.", lid)
            if weight is not None and (weight <= 0 or not line.get("weight_unit")):
                flag("weight_unit", "A recorded weight needs a positive amount and a weight unit.", lid)
            if line.get("unit") in {"lb", "kg"} and weight is not None:
                if line.get("weight_unit") != line["unit"] or weight != qty:
                    flag("weight_quantity_conflict", "For a weight-based item, quantity and measured weight must use the same unit and amount.", lid)
            if product and product.get("requires_lot") and not line.get("lot"):
                flag("missing_lot", "Record the lot identifier from the goods.", lid)
            if product and product.get("requires_expiry") and not line.get("expiry_date"):
                flag("missing_expiry", "Record the expiry date from the goods.", lid)
            if line.get("expiry_date") and date.fromisoformat(line["expiry_date"]) < date.today():
                flag("expired", "Expiry requires the warehouse's established review procedure. This demo will not release this item.", lid)
            if line.get("disposition") == "hold":
                flag("on_hold", "Resolve the hold using the warehouse's established process before handoff.", lid)
            if not line.get("checked"):
                flag("not_checked", "A staff member must check the actual item, quantity, unit and condition.", lid)
        return flags

    def present(self, receipt):
        result = deepcopy(receipt)
        result["flags"] = self.flags(receipt)
        return result

    def get(self, receipt_id):
        with self.store.connection() as conn:
            return self.present(self.store.fetch(conn, receipt_id))

    def create(self, data, actor):
        self.require_role(actor, "receiver")
        stamp = now()
        receipt = {**data.model_dump(mode="json"), "id": str(uuid4()), "version": 1,
                   "status": "draft", "created_by": actor["id"], "last_edited_by": actor["id"],
                   "approved_by": None, "approved_snapshot": None, "approved_payload_hash": None,
                   "created_at": stamp, "updated_at": stamp, "suggestions": [], "photos": [], "handoff": None}
        with self.store.transaction() as conn:
            self.store.save(conn, receipt, create=True)
            self.store.event(conn, receipt["id"], "receipt_created", actor["id"], {"original_entry": data.model_dump(mode="json")})
        return self.present(receipt)

    def update(self, receipt_id, data, actor):
        self.require_role(actor, "receiver")
        with self.store.transaction() as conn:
            receipt = self.store.fetch(conn, receipt_id)
            self.store.check_version(receipt, data.expected_version)
            if receipt["status"] not in {"draft", "in_review", "approved"}:
                raise WorkflowError("A handed-off receipt is locked. Resolve corrections through a separate warehouse adjustment process.")
            before = {k: receipt[k] for k in data.model_dump(exclude={"expected_version"})}
            previous_state = receipt["status"]
            receipt.update(data.model_dump(mode="json", exclude={"expected_version"}))
            receipt.update(status="draft", approved_by=None, approved_snapshot=None, approved_payload_hash=None,
                           last_edited_by=actor["id"], version=receipt["version"] + 1, updated_at=now())
            self.store.save(conn, receipt)
            self.store.event(conn, receipt_id, "receipt_edited", actor["id"], {
                "before": before, "after": data.model_dump(mode="json", exclude={"expected_version"}),
                "previous_status": previous_state, "approval_revoked": previous_state == "approved"})
        return self.present(receipt)

    def _validate_ready(self, receipt):
        blockers = [f["message"] for f in self.flags(receipt) if f["severity"] == "blocking"]
        if blockers:
            raise WorkflowError("Resolve these checks: " + " ".join(dict.fromkeys(blockers)), 422)

    def transition(self, receipt_id, command, actor, action):
        required = "receiver" if action == "submit" else "reviewer"
        self.require_role(actor, required)
        with self.store.transaction() as conn:
            receipt = self.store.fetch(conn, receipt_id)
            self.store.check_version(receipt, command.expected_version)
            if action == "submit":
                if receipt["status"] != "draft":
                    raise WorkflowError("Only a draft can be submitted for review.")
                self._validate_ready(receipt)
                receipt["status"] = "in_review"
            elif action == "approve":
                if receipt["status"] != "in_review":
                    raise WorkflowError("Only a receipt awaiting review can be approved.")
                if actor["id"] == receipt["last_edited_by"]:
                    raise WorkflowError("A different staff member must approve the last edit.", 403)
                self._validate_ready(receipt)
                snapshot = approved_payload(receipt)
                receipt.update(status="approved", approved_by=actor["id"], approved_snapshot=snapshot, approved_payload_hash=digest(snapshot))
            elif action == "return":
                if receipt["status"] != "in_review":
                    raise WorkflowError("Only a receipt awaiting review can be returned.")
                if not command.note:
                    raise WorkflowError("Explain what needs to be corrected.", 422)
                receipt.update(status="draft", approved_by=None, approved_snapshot=None, approved_payload_hash=None)
            else:
                raise WorkflowError("Unknown action.", 400)
            receipt.update(version=receipt["version"] + 1, updated_at=now())
            self.store.save(conn, receipt)
            self.store.event(conn, receipt_id, action, actor["id"], {
                "version": receipt["version"], "note": getattr(command, "note", ""),
                "approved_payload_hash": receipt["approved_payload_hash"]})
        return self.present(receipt)

    def suggest(self, receipt_id, command, actor):
        self.require_role(actor, "receiver")
        with self.store.connection() as conn:
            receipt = self.store.fetch(conn, receipt_id)
            self.store.check_version(receipt, command.expected_version)
            if receipt["status"] != "draft":
                raise WorkflowError("Suggestions are available for draft receipts only.")
            if command.line_id not in {l["line_id"] for l in receipt["lines"]}:
                raise WorkflowError("Receipt line not found.", 404)
        result = match_item(self.catalog, command.barcode, command.label_text)
        if command.use_ai:
            if self.settings.ai_provider != "ollama":
                raise WorkflowError("Local AI is disabled. Configure an installed model or use catalog matching.", 422)
            # Do not let model text override a valid barcode or repair an invalid one.
            if not command.barcode and result["product_id"] is None:
                result = suggest_with_ollama(self.catalog, command.label_text, self.settings.ollama_url, self.settings.ollama_model)
        suggestion = {**result, "id": str(uuid4()), "line_id": command.line_id, "created_at": now(),
                      "input": {"barcode": command.barcode, "label_text": command.label_text}}
        # Do not hold a write lock while waiting on an optional model.
        with self.store.transaction() as conn:
            receipt = self.store.fetch(conn, receipt_id)
            self.store.check_version(receipt, command.expected_version)
            if receipt["status"] != "draft":
                raise WorkflowError("The receipt is no longer a draft.")
            receipt["suggestions"].append(suggestion)
            receipt.update(version=receipt["version"] + 1, updated_at=now())
            self.store.save(conn, receipt)
            self.store.event(conn, receipt_id, "suggestion_recorded", actor["id"], suggestion)
        return {"receipt": self.present(receipt), "suggestion": suggestion}

    def handoff(self, receipt_id, command, actor):
        self.require_role(actor, "reviewer")
        with self.store.transaction() as conn:
            receipt = self.store.fetch(conn, receipt_id)
            previous = conn.execute("SELECT * FROM handoffs WHERE idempotency_key=?", (command.idempotency_key,)).fetchone()
            if previous:
                if previous["receipt_id"] != receipt_id:
                    raise WorkflowError("This idempotency key already belongs to a different receipt.")
                return {"receipt": self.present(receipt), "handoff": json.loads(previous["result"])}
            self.store.check_version(receipt, command.expected_version)
            if receipt["status"] != "approved" or not receipt["approved_by"]:
                raise WorkflowError("Staff approval is required before handoff.")
            self._validate_ready(receipt)
            if not receipt["purchase_order_ref"]:
                raise WorkflowError("Confirm the existing NetSuite purchase order that is available in WaerLinx before handoff.", 422)
            payload = approved_payload(receipt)
            if digest(payload) != receipt["approved_payload_hash"] or payload != receipt["approved_snapshot"]:
                raise WorkflowError("The approved receipt changed. Obtain a new review.")
            result = {**self.adapter.send(payload), "idempotency_key": command.idempotency_key}
            conn.execute("INSERT INTO handoffs VALUES(?,?,?,?,?)", (command.idempotency_key, receipt_id, digest(payload), canonical(payload), canonical(result)))
            receipt.update(status="sent_mock", handoff=result, version=receipt["version"] + 1, updated_at=now())
            self.store.save(conn, receipt)
            self.store.event(conn, receipt_id, "mock_handoff", actor["id"], {"payload": payload, "result": result})
        return {"receipt": self.present(receipt), "handoff": result}

    def reconcile(self, receipt_id, command, actor):
        self.require_role(actor, "reviewer")
        with self.store.transaction() as conn:
            receipt = self.store.fetch(conn, receipt_id)
            self.store.check_version(receipt, command.expected_version)
            if receipt["status"] not in {"sent_mock", "mismatch_mock"}:
                raise WorkflowError("Reconciliation requires a mock handoff or unresolved mock mismatch.")
            row = conn.execute("SELECT payload FROM handoffs WHERE receipt_id=?", (receipt_id,)).fetchone()
            if not row:
                raise WorkflowError("No handoff record exists.")
            expected = json.loads(row["payload"])
            observed = self.adapter.observe(expected, command.simulate_mismatch)
            differences = compare_receipts(expected, observed)
            result = {"mode": "mock", "matched": not differences, "differences": differences,
                      "observed_payload": observed, "checked_at": now(), "real_system_verified": False}
            receipt.update(status="mismatch_mock" if differences else "reconciled_mock", reconciliation=result,
                           version=receipt["version"] + 1, updated_at=now())
            self.store.save(conn, receipt)
            self.store.event(conn, receipt_id, "mock_reconciliation", actor["id"], result)
        return {"receipt": self.present(receipt), "reconciliation": result}
