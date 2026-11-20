"""SQLite transactions, optimistic versions, and a verifiable event chain."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class WorkflowError(Exception):
    def __init__(self, message: str, status: int = 409):
        self.message, self.status = message, status
        super().__init__(message)


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir.resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self.data_dir / "photos").mkdir(exist_ok=True, mode=0o700)
        self.path = self.data_dir / "receiving.sqlite3"
        with self.connection() as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS receipts (
                    id TEXT PRIMARY KEY, warehouse_key TEXT NOT NULL,
                    supplier_key TEXT NOT NULL, delivery_key TEXT NOT NULL,
                    version INTEGER NOT NULL, document TEXT NOT NULL,
                    UNIQUE(warehouse_key, supplier_key, delivery_key)
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id TEXT NOT NULL REFERENCES receipts(id),
                    action TEXT NOT NULL, actor_id TEXT NOT NULL,
                    created_at TEXT NOT NULL, payload TEXT NOT NULL,
                    previous_hash TEXT NOT NULL, hash TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS event_receipt ON events(receipt_id,seq);
                CREATE TABLE IF NOT EXISTS handoffs (
                    idempotency_key TEXT PRIMARY KEY,
                    receipt_id TEXT NOT NULL UNIQUE REFERENCES receipts(id),
                    payload_hash TEXT NOT NULL, payload TEXT NOT NULL, result TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
                BEGIN SELECT RAISE(ABORT, 'Audit events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
                BEGIN SELECT RAISE(ABORT, 'Audit events are append-only'); END;
            """)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def fetch(self, conn, receipt_id):
        row = conn.execute("SELECT document FROM receipts WHERE id=?", (receipt_id,)).fetchone()
        if not row:
            raise WorkflowError("Receipt not found.", 404)
        return json.loads(row["document"])

    @staticmethod
    def check_version(receipt, expected):
        if receipt["version"] != expected:
            raise WorkflowError("This receipt changed. Reload it before making another change.")

    def save(self, conn, receipt, *, create=False):
        fields = (receipt["warehouse"].casefold(), receipt["supplier"].casefold(),
                  receipt["delivery_ref"].casefold(), receipt["version"], canonical(receipt), receipt["id"])
        try:
            if create:
                conn.execute("INSERT INTO receipts(warehouse_key,supplier_key,delivery_key,version,document,id) VALUES(?,?,?,?,?,?)", fields)
            else:
                conn.execute("UPDATE receipts SET warehouse_key=?,supplier_key=?,delivery_key=?,version=?,document=? WHERE id=?", fields)
        except sqlite3.IntegrityError as exc:
            raise WorkflowError("A receipt already exists for this supplier, warehouse and delivery reference. Reopen it instead of entering a duplicate.") from exc

    def event(self, conn, receipt_id, action, actor_id, payload):
        last = conn.execute("SELECT hash FROM events WHERE receipt_id=? ORDER BY seq DESC LIMIT 1", (receipt_id,)).fetchone()
        event = {"receipt_id": receipt_id, "action": action, "actor_id": actor_id,
                 "created_at": now(), "payload": payload, "previous_hash": last["hash"] if last else "0" * 64}
        event["hash"] = digest(event)
        cursor = conn.execute("INSERT INTO events(receipt_id,action,actor_id,created_at,payload,previous_hash,hash) VALUES(?,?,?,?,?,?,?)",
                             (receipt_id, action, actor_id, event["created_at"], canonical(payload), event["previous_hash"], event["hash"]))
        return {"seq": cursor.lastrowid, **event}

    def audit(self, receipt_id):
        with self.connection() as conn:
            self.fetch(conn, receipt_id)
            rows = conn.execute("SELECT * FROM events WHERE receipt_id=? ORDER BY seq", (receipt_id,)).fetchall()
        previous, valid, events = "0" * 64, True, []
        for row in rows:
            event = dict(row)
            event["payload"] = json.loads(event["payload"])
            content = {key: value for key, value in event.items() if key not in {"seq", "hash"}}
            valid = valid and event["previous_hash"] == previous and digest(content) == event["hash"]
            previous = event["hash"]
            events.append(event)
        return {"events": events, "valid": bool(valid)}

    def list_receipts(self):
        with self.connection() as conn:
            rows = conn.execute("SELECT document FROM receipts ORDER BY rowid DESC").fetchall()
        return [json.loads(row["document"]) for row in rows]
