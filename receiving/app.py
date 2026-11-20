"""Local HTTP API and static UI. Demo identities are not real authentication."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from receiving import __version__
from receiving.config import Settings
from receiving.models import (HandoffCommand, ReceiptInput, ReceiptUpdate, ReconcileCommand,
                              ReviewCommand, SessionInput, SuggestCommand, VersionCommand)
from receiving.photos import add_photo, delete_photo, photo_path, purge_expired
from receiving.store import WorkflowError
from receiving.workflow import Workflow


def create_app(settings=None):
    settings = settings or Settings.from_env()
    workflow = Workflow(settings)
    app = FastAPI(title="Receiving Assistant — local draft", version=__version__,
                  docs_url=None, redoc_url=None,
                  description="Synthetic-data demo. Warehouse handoff and reconciliation are simulated.")
    app.state.workflow = workflow
    app.state.sessions = {}

    @app.exception_handler(WorkflowError)
    async def workflow_error(_request, exc):
        return JSONResponse({"detail": exc.message}, status_code=exc.status)

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        try:
            authority = urlparse("//" + request.headers.get("host", ""))
            valid_host = authority.hostname in {"127.0.0.1", "localhost", "::1", "testserver"}
            valid_host = valid_host and not authority.username and not authority.password and not authority.path
            _ = authority.port
        except ValueError:
            valid_host = False
        if not valid_host:
            return JSONResponse({"detail": "Invalid local Host header."}, status_code=400)
        if request.client and request.client.host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
            return JSONResponse({"detail": "This draft accepts loopback clients only."}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if (origin and urlparse(origin).netloc != request.headers.get("host")) or request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Cross-site changes are disabled."}, status_code=403)
            is_photo = request.url.path.endswith("/photos") and request.method == "POST"
            limit = settings.max_photo_bytes if is_photo else 256 * 1024
            raw = bytearray()
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw) > limit:
                    return JSONResponse({"detail": "Request exceeds the size limit."}, status_code=413)
            # Starlette's BaseHTTPMiddleware replays this cached body to the route.
            request._body = bytes(raw)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        response.headers["Cache-Control"] = "no-store"
        return response

    def actor(request: Request):
        value = request.headers.get("authorization", "")
        token = value[7:] if value.startswith("Bearer ") else ""
        entry = app.state.sessions.get(token)
        if not entry or entry["expires"] <= datetime.now(timezone.utc):
            raise WorkflowError("Choose a demo identity to continue.", 401)
        return entry["actor"]

    @app.get("/health")
    def health():
        return {"ok": True, "mode": "demo", "integration": "mock", "version": __version__}

    @app.post("/api/session")
    def session(data: SessionInput):
        token = secrets.token_urlsafe(32)
        user = {"id": "demo-" + data.identity, "name": "Demo " + data.identity, "role": data.identity}
        stamp = datetime.now(timezone.utc)
        app.state.sessions = {k: v for k, v in app.state.sessions.items() if v["expires"] > stamp}
        if len(app.state.sessions) >= 100:
            raise WorkflowError("Too many local demo sessions. Restart the app to clear them.", 429)
        app.state.sessions[token] = {"actor": user, "expires": stamp + timedelta(hours=8)}
        return {"token": token, "actor": user, "mode": "demo"}

    @app.get("/api/config")
    def configuration(_actor=Depends(actor)):
        return {"mode": "demo", "ai_provider": settings.ai_provider, "integration": "mock",
                "max_photo_bytes": settings.max_photo_bytes,
                "photo_retention_days": settings.photo_retention_days,
                "photo_inference": False, "camera_barcode_scanning": False}

    @app.get("/api/catalog")
    def catalog(_actor=Depends(actor)):
        return {"items": workflow.catalog}

    @app.get("/api/receipts")
    def receipts(_actor=Depends(actor)):
        return {"items": [workflow.present(r) for r in workflow.store.list_receipts()]}

    @app.post("/api/receipts", status_code=201)
    def create(data: ReceiptInput, user=Depends(actor)):
        return workflow.create(data, user)

    @app.get("/api/receipts/{receipt_id}")
    def receipt(receipt_id: str, _actor=Depends(actor)):
        return workflow.get(receipt_id)

    @app.put("/api/receipts/{receipt_id}")
    def edit(receipt_id: str, data: ReceiptUpdate, user=Depends(actor)):
        return workflow.update(receipt_id, data, user)

    @app.post("/api/receipts/{receipt_id}/suggest")
    def suggest(receipt_id: str, data: SuggestCommand, user=Depends(actor)):
        return workflow.suggest(receipt_id, data, user)

    @app.post("/api/receipts/{receipt_id}/submit")
    def submit(receipt_id: str, data: VersionCommand, user=Depends(actor)):
        return workflow.transition(receipt_id, data, user, "submit")

    @app.post("/api/receipts/{receipt_id}/approve")
    def approve(receipt_id: str, data: ReviewCommand, user=Depends(actor)):
        return workflow.transition(receipt_id, data, user, "approve")

    @app.post("/api/receipts/{receipt_id}/return")
    def return_for_changes(receipt_id: str, data: ReviewCommand, user=Depends(actor)):
        return workflow.transition(receipt_id, data, user, "return")

    @app.post("/api/receipts/{receipt_id}/handoff")
    def handoff(receipt_id: str, data: HandoffCommand, user=Depends(actor)):
        return workflow.handoff(receipt_id, data, user)

    @app.post("/api/receipts/{receipt_id}/reconcile")
    def reconcile(receipt_id: str, data: ReconcileCommand, user=Depends(actor)):
        return workflow.reconcile(receipt_id, data, user)

    @app.get("/api/receipts/{receipt_id}/audit")
    def audit(receipt_id: str, _actor=Depends(actor)):
        return workflow.store.audit(receipt_id)

    @app.get("/api/receipts/{receipt_id}/export")
    def export(receipt_id: str, _actor=Depends(actor)):
        result = {"format": "receiving-review-export/1", "mode": "demo", "vendor_import_ready": False,
                  "receipt": workflow.get(receipt_id), "audit": workflow.store.audit(receipt_id)}
        return JSONResponse(result, headers={"Content-Disposition": 'attachment; filename="receiving-review.json"'})

    @app.post("/api/receipts/{receipt_id}/photos")
    async def upload(receipt_id: str, request: Request, expected_version: int = Query(ge=1), user=Depends(actor)):
        if request.headers.get("content-type", "").split(";")[0] not in {"image/png", "image/jpeg"}:
            raise WorkflowError("Upload raw PNG or JPEG bytes.", 415)
        return add_photo(workflow, receipt_id, await request.body(), expected_version, user)

    @app.get("/api/photos/{photo_id}")
    def image(photo_id: str, _actor=Depends(actor)):
        path = photo_path(workflow, photo_id)
        try:
            data = path.read_bytes()
        except FileNotFoundError as exc:
            raise WorkflowError("Photo was removed or expired.", 404) from exc
        return Response(data, media_type="image/jpeg")

    @app.delete("/api/receipts/{receipt_id}/photos/{photo_id}")
    def remove_image(receipt_id: str, photo_id: str, expected_version: int = Query(ge=1), user=Depends(actor)):
        return delete_photo(workflow, receipt_id, photo_id, expected_version, user)

    # Mount last so API errors are never swallowed by a single-page fallback.
    static = Path(__file__).resolve().parent / "static"
    app.mount("/", StaticFiles(directory=static, html=True), name="ui")
    return app
