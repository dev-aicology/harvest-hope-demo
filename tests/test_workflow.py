"""Tests for integrity boundaries; no model or external system required."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, timedelta
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from receiving.app import create_app
from receiving.config import Settings
from receiving.integrations import compare_receipts
from receiving.models import HandoffCommand
from receiving.photos import purge_expired


ROOT = Path(__file__).resolve().parents[1]


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app(Settings(data_dir=Path(self.tmp.name)))
        self.client = TestClient(self.app)
        self.wf = self.app.state.workflow
        self.receiver = self.login("receiver")
        self.reviewer = self.login("reviewer")
        self.data = json.loads((ROOT / "data/synthetic/sample_receipt.json").read_text())
        self.data["received_on"] = date.today().isoformat()
        for line in self.data["lines"]:
            line["checked"] = True
            if line["expiry_date"]:
                line["expiry_date"] = (date.today() + timedelta(days=365)).isoformat()

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def login(self, identity):
        result = self.client.post("/api/session", json={"identity": identity})
        self.assertEqual(result.status_code, 200)
        return {"Authorization": "Bearer " + result.json()["token"]}

    def create(self, data=None):
        result = self.client.post("/api/receipts", headers=self.receiver, json=data or self.data)
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()

    def action(self, receipt, action, headers=None, status=200, **extra):
        payload = {"expected_version": receipt["version"], **extra}
        result = self.client.post(f"/api/receipts/{receipt['id']}/{action}", headers=headers or self.receiver, json=payload)
        self.assertEqual(result.status_code, status, result.text)
        return result.json()

    def approved(self):
        receipt = self.create()
        receipt = self.action(receipt, "submit")
        return self.action(receipt, "approve", self.reviewer)

    def test_complete_workflow_mock_mismatch_and_recovery(self):
        receipt = self.approved()
        result = self.action(receipt, "handoff", self.reviewer, idempotency_key="demo-idempotency-123")
        self.assertEqual(result["receipt"]["status"], "sent_mock")
        self.assertEqual(result["handoff"]["mode"], "mock")
        mismatch = self.action(result["receipt"], "reconcile", self.reviewer, simulate_mismatch=True)
        self.assertFalse(mismatch["reconciliation"]["matched"])
        self.assertTrue(mismatch["reconciliation"]["differences"])
        matched = self.action(mismatch["receipt"], "reconcile", self.reviewer)
        self.assertEqual(matched["receipt"]["status"], "reconciled_mock")
        self.assertFalse(matched["reconciliation"]["real_system_verified"])

    def test_role_cannot_be_spoofed_with_header(self):
        receipt = self.action(self.create(), "submit")
        headers = {**self.receiver, "X-Role": "reviewer"}
        self.action(receipt, "approve", headers, status=403)
        result = self.client.post("/api/receipts", headers=self.reviewer, json=self.data)
        self.assertEqual(result.status_code, 403)

    def test_data_and_photos_require_session(self):
        self.assertEqual(self.client.get("/api/receipts").status_code, 401)
        self.assertEqual(self.client.get("/api/photos/unknown").status_code, 401)

    def test_unknown_role_and_server_fields_rejected(self):
        self.assertEqual(self.client.post("/api/session", json={"identity": "admin"}).status_code, 422)
        self.data["approved_by"] = "reviewer"
        self.assertEqual(self.client.post("/api/receipts", headers=self.receiver, json=self.data).status_code, 422)

    def test_draft_incomplete_allowed_but_submit_blocked(self):
        self.data["lines"][0].update(product_id=None, quantity=None, checked=False)
        receipt = self.create()
        self.action(receipt, "submit", status=422)
        self.action(receipt, "handoff", self.reviewer, status=409, idempotency_key="unapproved-key")

    def test_staff_must_enter_actual_weight_and_unit(self):
        self.data["lines"][1]["measured_weight"] = None
        receipt = self.create()
        self.assertIn("missing_weight", {f["code"] for f in receipt["flags"]})
        self.action(receipt, "submit", status=422)

    def test_conflicting_weight_quantity_blocks_review(self):
        self.data["lines"][1]["quantity"] = 40
        self.action(self.create(), "submit", status=422)

    def test_lot_expiry_hold_unit_and_count_require_review(self):
        for change in ({"lot": ""}, {"expiry_date": "2000-01-01"}, {"disposition": "hold"}, {"unit": "each"}, {"quantity": 1.5}):
            with self.subTest(change=change):
                data = deepcopy(self.data)
                data["delivery_ref"] += str(change)
                data["lines"][0].update(change)
                self.action(self.create(data), "submit", status=422)

    def test_barcode_conflict_cannot_be_approved(self):
        self.data["lines"][0]["product_id"] = "DEMO-OATS-CASE"
        self.action(self.create(), "submit", status=422)

    def test_nonfinite_negative_and_boolean_quantities_rejected(self):
        for value in ("NaN", "Infinity", -1, True):
            with self.subTest(value=value):
                self.data["lines"][0]["quantity"] = value
                self.assertEqual(self.client.post("/api/receipts", headers=self.receiver, json=self.data).status_code, 422)

    def test_duplicate_delivery_and_duplicate_line_ids_blocked(self):
        self.create()
        self.assertEqual(self.client.post("/api/receipts", headers=self.receiver, json=self.data).status_code, 409)
        self.data["lines"][1]["line_id"] = self.data["lines"][0]["line_id"]
        self.assertEqual(self.client.post("/api/receipts", headers=self.receiver, json=self.data).status_code, 422)

    def test_stale_edit_fails_without_losing_newer_data(self):
        receipt = self.create()
        payload = {**self.data, "notes": "First update", "expected_version": receipt["version"]}
        url = f"/api/receipts/{receipt['id']}"
        self.assertEqual(self.client.put(url, headers=self.receiver, json=payload).status_code, 200)
        payload["notes"] = "Lost update"
        self.assertEqual(self.client.put(url, headers=self.receiver, json=payload).status_code, 409)
        self.assertEqual(self.client.get(url, headers=self.receiver).json()["notes"], "First update")

    def test_edit_revokes_approval_and_preserves_original(self):
        receipt = self.approved()
        data = {**self.data, "notes": "Correction", "expected_version": receipt["version"]}
        updated = self.client.put(f"/api/receipts/{receipt['id']}", headers=self.receiver, json=data).json()
        self.assertEqual(updated["status"], "draft")
        self.assertIsNone(updated["approved_by"])
        self.action(updated, "handoff", self.reviewer, status=409, idempotency_key="edited-approval")
        audit = self.wf.store.audit(receipt["id"])
        self.assertTrue(audit["valid"])
        self.assertEqual(audit["events"][0]["payload"]["original_entry"]["notes"], self.data["notes"])
        self.assertTrue(audit["events"][-1]["payload"]["approval_revoked"])

    def test_suggestion_does_not_set_item_quantity_or_check(self):
        self.data["lines"][0].update(product_id=None, quantity=None, checked=False)
        receipt = self.create()
        suggested = self.action(receipt, "suggest", line_id=receipt["lines"][0]["line_id"], barcode="029000000018")
        self.assertEqual(suggested["suggestion"]["product_id"], "DEMO-BEANS-CASE")
        line = suggested["receipt"]["lines"][0]
        self.assertIsNone(line["product_id"])
        self.assertIsNone(line["quantity"])
        self.assertFalse(line["checked"])

    def test_ai_disabled_has_no_silent_fallback(self):
        receipt = self.create()
        with patch("receiving.workflow.suggest_with_ollama") as call:
            self.action(receipt, "suggest", status=422, line_id=receipt["lines"][0]["line_id"], label_text="unknown", use_ai=True)
            call.assert_not_called()

    def test_handoff_requires_purchase_order(self):
        self.data["purchase_order_ref"] = ""
        receipt = self.approved()
        self.action(receipt, "handoff", self.reviewer, status=422, idempotency_key="no-purchase-order")

    def test_idempotency_survives_restart_and_different_key_does_not_resend(self):
        receipt = self.approved()
        first = self.action(receipt, "handoff", self.reviewer, idempotency_key="repeat-on-restart")
        repeated = self.action(receipt, "handoff", self.reviewer, idempotency_key="repeat-on-restart")
        self.assertEqual(first["handoff"], repeated["handoff"])
        self.action(first["receipt"], "handoff", self.reviewer, status=409, idempotency_key="new-key-after-send")
        other_app = create_app(Settings(data_dir=Path(self.tmp.name)))
        actor = {"id": "demo-reviewer", "role": "reviewer"}
        result = other_app.state.workflow.handoff(receipt["id"], HandoffCommand(expected_version=receipt["version"], idempotency_key="repeat-on-restart"), actor)
        self.assertEqual(result["handoff"], first["handoff"])

    def test_concurrent_retry_sends_once(self):
        receipt = self.approved()
        command = HandoffCommand(expected_version=receipt["version"], idempotency_key="concurrent-retry")
        actor = {"id": "demo-reviewer", "role": "reviewer"}
        with patch.object(self.wf.adapter, "send", wraps=self.wf.adapter.send) as send:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.wf.handoff(receipt["id"], command, actor), range(2)))
            self.assertEqual(send.call_count, 1)
            self.assertEqual(results[0]["handoff"], results[1]["handoff"])

    def test_adapter_failure_rolls_back_state_and_event(self):
        receipt = self.approved()
        before = len(self.wf.store.audit(receipt["id"])["events"])
        with patch.object(self.wf.adapter, "send", side_effect=RuntimeError("simulated failure")):
            with self.assertRaises(RuntimeError):
                self.wf.handoff(receipt["id"], HandoffCommand(expected_version=receipt["version"], idempotency_key="failure-retry"), {"id": "demo-reviewer", "role": "reviewer"})
        self.assertEqual(self.wf.get(receipt["id"])["status"], "approved")
        self.assertEqual(len(self.wf.store.audit(receipt["id"])["events"]), before)

    def test_locked_after_handoff_and_missing_return_reason(self):
        receipt = self.action(self.create(), "submit")
        self.action(receipt, "return", self.reviewer, status=422)
        receipt = self.action(receipt, "approve", self.reviewer)
        sent = self.action(receipt, "handoff", self.reviewer, idempotency_key="lock-after-send")["receipt"]
        result = self.client.put(f"/api/receipts/{receipt['id']}", headers=self.receiver, json={**self.data, "expected_version": sent["version"]})
        self.assertEqual(result.status_code, 409)

    def test_audit_detects_edit_and_rejects_updates(self):
        receipt = self.create()
        self.assertTrue(self.wf.store.audit(receipt["id"])["valid"])
        import sqlite3
        with self.wf.store.transaction() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE events SET actor_id='altered'")
        with self.wf.store.transaction() as conn:
            conn.execute("DROP TRIGGER events_no_update")
            conn.execute("UPDATE events SET actor_id='altered'")
        self.assertFalse(self.wf.store.audit(receipt["id"])["valid"])

    def test_photo_metadata_stripped_and_expiry_physically_purged(self):
        receipt = self.create()
        raw = BytesIO()
        image = Image.new("RGB", (30, 20), "green")
        exif = Image.Exif(); exif[270] = "private test metadata"
        image.save(raw, format="JPEG", exif=exif)
        url = f"/api/receipts/{receipt['id']}/photos?expected_version={receipt['version']}"
        uploaded = self.client.post(url, headers={**self.receiver, "Content-Type": "image/jpeg"}, content=raw.getvalue())
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        photo = uploaded.json()["photos"][0]
        photo_url = f"/api/photos/{photo['id']}"
        returned = self.client.get(photo_url, headers=self.receiver)
        self.assertEqual(returned.status_code, 200)
        with Image.open(BytesIO(returned.content)) as safe:
            self.assertFalse(safe.getexif())
        with self.wf.store.transaction() as conn:
            current = self.wf.store.fetch(conn, receipt["id"])
            current["photos"][0]["expires_at"] = "2000-01-01T00:00:00+00:00"
            self.wf.store.save(conn, current)
        self.assertEqual(self.client.get(photo_url, headers=self.receiver).status_code, 410)
        self.assertEqual(purge_expired(self.wf)["expired_photos_removed"], 1)
        self.assertEqual(list((Path(self.tmp.name) / "photos").glob("*")), [])
        self.assertTrue(self.wf.store.audit(receipt["id"])["valid"])

    def test_invalid_photo_and_oversized_request_rejected(self):
        receipt = self.create()
        url = f"/api/receipts/{receipt['id']}/photos?expected_version=1"
        result = self.client.post(url, headers={**self.receiver, "Content-Type": "image/png"}, content=b"not an image")
        self.assertEqual(result.status_code, 422)
        result = self.client.post("/api/receipts", headers={**self.receiver, "Content-Type": "application/json"}, content=b" " * 270000)
        self.assertEqual(result.status_code, 413)

    def test_cross_site_and_host_boundary(self):
        self.assertEqual(self.client.post("/api/session", headers={"Origin": "https://attacker.invalid"}, json={"identity": "receiver"}).status_code, 403)
        self.assertEqual(self.client.get("/health", headers={"Host": "attacker.invalid"}).status_code, 400)
        self.assertEqual(self.client.get("/health", headers={"Host": "[::1]:8000"}).status_code, 200)
        self.assertEqual(self.client.get("/health", headers={"Host": "name@localhost:8000"}).status_code, 400)

    def test_static_assets_and_export_honestly_label_mock(self):
        for path in ("/", "/styles.css", "/app.js"):
            self.assertEqual(self.client.get(path).status_code, 200)
        receipt = self.create()
        exported = self.client.get(f"/api/receipts/{receipt['id']}/export", headers=self.reviewer).json()
        self.assertFalse(exported["vendor_import_ready"])
        self.assertEqual(exported["mode"], "demo")

    def test_configuration_refuses_live_and_non_loopback(self):
        for options in ({"host": "0.0.0.0"}, {"mode": "production"}, {"integration": "live"}, {"ollama_url": "https://remote.invalid"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                Settings(**options)

    def test_reconciliation_compares_lot_unit_and_weight(self):
        original = {"lines": [{"quantity": "1", "unit": "case", "lot": "A", "measured_weight": "3"}]}
        observed = deepcopy(original)
        observed["lines"][0].update(unit="each", lot="B", measured_weight="4")
        self.assertEqual(len(compare_receipts(original, observed)), 3)


if __name__ == "__main__":
    unittest.main()
