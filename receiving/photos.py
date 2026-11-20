"""Bounded photo evidence storage with metadata stripping and expiry checks."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
import hashlib
from pathlib import Path
import warnings
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from receiving.store import WorkflowError, now


def _expires(value):
    return datetime.fromisoformat(value) <= datetime.now(timezone.utc)


def safe_image(raw: bytes, limit: int):
    if len(raw) > limit:
        raise WorkflowError("Photo exceeds the size limit.", 413)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if source.format not in {"PNG", "JPEG"}:
                    raise WorkflowError("Use a PNG or JPEG photo.", 422)
                if source.width * source.height > 12_000_000:
                    raise WorkflowError("Photo must be no larger than 12 megapixels.", 422)
                source.load()
                # Copy pixels into a clean image so EXIF/GPS/text chunks are discarded.
                oriented = ImageOps.exif_transpose(source).convert("RGB")
                clean = Image.new("RGB", oriented.size)
                clean.paste(oriented)
                output = BytesIO()
                clean.save(output, format="JPEG", quality=88)
                encoded = output.getvalue()
                if len(encoded) > limit:
                    raise WorkflowError("Decoded photo exceeds the storage limit. Use a smaller photo.", 413)
                return encoded, clean.width, clean.height
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise WorkflowError("The file is not a supported, readable photo.", 422) from exc


def add_photo(workflow, receipt_id, raw, expected_version, actor):
    workflow.require_role(actor, "receiver")
    encoded, width, height = safe_image(raw, workflow.settings.max_photo_bytes)
    photo_id = str(uuid4())
    path = workflow.store.data_dir / "photos" / (photo_id + ".jpg")
    expires_at = (datetime.now(timezone.utc) + timedelta(days=workflow.settings.photo_retention_days)).isoformat()
    photo = {"id": photo_id, "name": "Receiving photo", "media_type": "image/jpeg",
             "width": width, "height": height, "sha256": hashlib.sha256(encoded).hexdigest(),
             "created_at": now(), "expires_at": expires_at}
    try:
        with workflow.store.transaction() as conn:
            receipt = workflow.store.fetch(conn, receipt_id)
            workflow.store.check_version(receipt, expected_version)
            if receipt["status"] != "draft":
                raise WorkflowError("Photos can be added only to a draft.")
            if len(receipt["photos"]) >= 10:
                raise WorkflowError("Use no more than ten photos per draft.", 422)
            with path.open("xb") as file:
                file.write(encoded)
            path.chmod(0o600)
            receipt["photos"].append(photo)
            receipt.update(version=receipt["version"] + 1, updated_at=now())
            workflow.store.save(conn, receipt)
            workflow.store.event(conn, receipt_id, "photo_added", actor["id"], photo)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return workflow.present(receipt)


def photo_path(workflow, photo_id):
    # Look up approved metadata; never derive a file path from an unchecked URL path.
    for receipt in workflow.store.list_receipts():
        for photo in receipt["photos"]:
            if photo["id"] == photo_id:
                if _expires(photo["expires_at"]):
                    raise WorkflowError("Photo retention has expired.", 410)
                path = workflow.store.data_dir / "photos" / (photo["id"] + ".jpg")
                if not path.is_file():
                    raise WorkflowError("Photo is no longer available.", 404)
                return path
    raise WorkflowError("Photo not found.", 404)


def delete_photo(workflow, receipt_id, photo_id, expected_version, actor):
    workflow.require_role(actor, "receiver")
    with workflow.store.transaction() as conn:
        receipt = workflow.store.fetch(conn, receipt_id)
        workflow.store.check_version(receipt, expected_version)
        if receipt["status"] != "draft":
            raise WorkflowError("Photos can be removed only from a draft. Expiry is enforced for all states.")
        photo = next((p for p in receipt["photos"] if p["id"] == photo_id), None)
        if not photo:
            raise WorkflowError("Photo not found.", 404)
        receipt["photos"] = [p for p in receipt["photos"] if p["id"] != photo_id]
        receipt.update(version=receipt["version"] + 1, updated_at=now())
        workflow.store.save(conn, receipt)
        workflow.store.event(conn, receipt_id, "photo_removed", actor["id"], {"id": photo_id, "sha256": photo["sha256"]})
    # Once metadata is removed, reads fail closed even if unlink fails. Maintenance
    # also removes unreferenced images, covering a process crash at this boundary.
    (workflow.store.data_dir / "photos" / (photo_id + ".jpg")).unlink(missing_ok=True)
    return workflow.present(receipt)


def purge_expired(workflow):
    removed = []
    for current in workflow.store.list_receipts():
        with workflow.store.transaction() as conn:
            receipt = workflow.store.fetch(conn, current["id"])
            expired = [p for p in receipt["photos"] if _expires(p["expires_at"])]
            if not expired:
                continue
            expired_ids = {p["id"] for p in expired}
            receipt["photos"] = [p for p in receipt["photos"] if p["id"] not in expired_ids]
            receipt.update(version=receipt["version"] + 1, updated_at=now())
            workflow.store.save(conn, receipt)
            for photo in expired:
                workflow.store.event(conn, receipt["id"], "photo_expired", "maintenance", {"id": photo["id"], "sha256": photo["sha256"]})
                removed.append(photo["id"])
    # Hold the same database lock used by writers while enumerating references.
    # An upload writes bytes and commits metadata inside this lock, so a new
    # upload cannot be mistaken for an orphan between file write and commit.
    with workflow.store.transaction() as conn:
        rows = conn.execute("SELECT document FROM receipts").fetchall()
        import json
        referenced = {p["id"] + ".jpg" for row in rows for p in json.loads(row["document"])["photos"]}
        for path in (workflow.store.data_dir / "photos").glob("*.jpg"):
            if path.name not in referenced:
                path.unlink(missing_ok=True)
    return {"expired_photos_removed": len(removed), "photo_ids": removed}
