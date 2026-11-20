"""Run the synthetic lifecycle without a browser, model, or network connection."""
from datetime import date
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from receiving.app import create_app
from receiving.config import Settings


def main():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(create_app(Settings(data_dir=Path(tmp)))) as client:
            def session(identity):
                result = client.post("/api/session", json={"identity": identity})
                result.raise_for_status()
                return {"Authorization": "Bearer " + result.json()["token"]}
            receiver, reviewer = session("receiver"), session("reviewer")
            fixture = json.loads((ROOT / "data/synthetic/sample_receipt.json").read_text())
            fixture["received_on"] = date.today().isoformat()
            result = client.post("/api/receipts", json=fixture, headers=receiver)
            result.raise_for_status()
            receipt = result.json()
            print("1. Draft captured; unchecked rows:", len(receipt["flags"]))
            for line in fixture["lines"]:
                line["checked"] = True  # Scripted demonstration, not a real staff review.
            result = client.put(f"/api/receipts/{receipt['id']}", headers=receiver,
                                json={**fixture, "expected_version": receipt["version"]})
            result.raise_for_status()
            receipt = result.json()
            for index, (action, headers, extra) in enumerate([
                ("submit", receiver, {}), ("approve", reviewer, {}),
                ("handoff", reviewer, {"idempotency_key": "scripted-demo-handoff"}),
                ("reconcile", reviewer, {"simulate_mismatch": True}),
                ("reconcile", reviewer, {"simulate_mismatch": False}),
            ], 2):
                result = client.post(f"/api/receipts/{receipt['id']}/{action}", headers=headers,
                                     json={"expected_version": receipt["version"], **extra})
                result.raise_for_status()
                receipt = result.json().get("receipt", result.json())
                print(f"{index}. {action}: {receipt['status']}")
            audit = client.get(f"/api/receipts/{receipt['id']}/audit", headers=reviewer).json()
            print(f"Audit: {len(audit['events'])} events; chain valid={audit['valid']}")
            print("All values and approvals were synthetic. No warehouse or AI service was contacted.")


if __name__ == "__main__":
    main()
