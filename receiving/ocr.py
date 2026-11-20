"""Optional local Tesseract text extraction for bounded, explicitly selected files.

No image leaves this process's machine. This adapter performs no model downloads,
vendor calls, barcode decoding, counting, weight inference, or receipt approval.
"""
from __future__ import annotations

from pathlib import Path
from io import BytesIO
import shutil
import subprocess
import tempfile
import time
import warnings

from PIL import Image, UnidentifiedImageError

from receiving.matching import match_item

MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000
MAX_OUTPUT_BYTES = 128 * 1024


def extract_text(image_path: str | Path, *, allowed_root: str | Path,
                 timeout_seconds: float = 10) -> dict:
    """Run fixed English-language OCR inside one caller-approved image directory.

    Path/format/size failures and missing binaries are explicit result states. The
    caller must supply an allowed root; this is not an arbitrary-file HTTP API.
    Both inputs and captured outputs are bounded. Error text never leaks paths or
    untrusted process output. No shell is invoked.
    """
    start = time.perf_counter()

    def result(status: str, *, text: str = "", error_type: str | None = None) -> dict:
        return {"status": status, "text": text, "engine": "tesseract", "language": "eng",
                "elapsed_ms": round((time.perf_counter() - start) * 1000, 6),
                "error_type": error_type, "external_calls": False}

    if not isinstance(timeout_seconds, (int, float)) or not 0 < timeout_seconds <= 30:
        return result("error", error_type="invalid_timeout")
    try:
        root = Path(allowed_root).resolve(strict=True)
        candidate = Path(image_path).resolve(strict=True)
        if not root.is_dir() or not candidate.is_relative_to(root) or not candidate.is_file():
            return result("error", error_type="path_not_allowed")
        if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            return result("error", error_type="unsupported_file_type")
        if candidate.stat().st_size > MAX_IMAGE_BYTES:
            return result("error", error_type="image_too_large")
        with candidate.open("rb") as source:
            raw = source.read(MAX_IMAGE_BYTES + 1)
        if len(raw) > MAX_IMAGE_BYTES:
            return result("error", error_type="image_too_large")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as image:
                if image.format not in {"PNG", "JPEG"} or image.width * image.height > MAX_IMAGE_PIXELS:
                    return result("error", error_type="unsupported_image_or_dimensions")
                image.verify()
    except (OSError, ValueError, UnidentifiedImageError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        return result("error", error_type="unreadable_image")
    binary = shutil.which("tesseract")
    if not binary:
        return result("unavailable", error_type="tesseract_not_installed")
    try:
        # Write captured output to temporary files so a large OCR response is not
        # accumulated in memory. Read at most the fixed output cap afterward.
        with tempfile.TemporaryDirectory(prefix="receiving-ocr-") as job_dir, \
             tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            # Tesseract receives the validated bounded snapshot, so changes to
            # the selected source path cannot change its input after validation.
            snapshot = Path(job_dir) / ("input" + candidate.suffix.lower())
            snapshot.write_bytes(raw)
            completed = subprocess.run(
                [binary, str(snapshot), "stdout", "-l", "eng", "--psm", "6"],
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                timeout=timeout_seconds, check=False, shell=False,
            )
            if completed.returncode != 0:
                return result("error", error_type="tesseract_failed")
            if stdout.tell() > MAX_OUTPUT_BYTES or stderr.tell() > MAX_OUTPUT_BYTES:
                return result("error", error_type="ocr_output_too_large")
            stdout.seek(0)
            text = stdout.read(MAX_OUTPUT_BYTES).decode("utf-8", errors="strict")
        return result("ok", text=text)
    except subprocess.TimeoutExpired:
        return result("error", error_type="timeout")
    except (OSError, UnicodeError):
        return result("error", error_type="tesseract_unavailable_or_invalid_output")


def suggest_from_ocr(catalog: list[dict], text: str) -> dict:
    """Apply exact name/alias matching to OCR lines; conflicting matches abstain.

    Metadata such as an embedded DEMO product ID is not read as a prediction.
    No expected label or ground-truth product ID is passed into this function.
    """
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_OUTPUT_BYTES:
        return {"product_id": None, "method": "ocr_label_rules", "requires_review": True,
                "reason": "OCR text is missing or exceeds the allowed limit."}
    candidates = set()
    for line in text.splitlines():
        matched = match_item(catalog, label_text=line.strip())
        if matched["product_id"] is not None:
            candidates.add(matched["product_id"])
    if len(candidates) == 1:
        return {"product_id": next(iter(candidates)), "method": "ocr_label_rules", "requires_review": True,
                "reason": "An OCR line exactly matches a catalog name or alias. Staff must verify the item."}
    reason = "OCR contains conflicting item names." if candidates else "No exact catalog name or alias found in OCR text."
    return {"product_id": None, "method": "ocr_label_rules", "requires_review": True,
            "reason": reason + " Resolve manually."}
