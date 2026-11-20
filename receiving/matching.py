"""Conservative local catalog lookup. This module performs no OCR or AI calls.

Barcodes are treated as opaque, local catalog identifiers. Never send these
synthetic identifiers to a public UPC/product service. Suggestions always need
staff review and never contain quantities, weights, or inventory instructions.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unicodedata

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "catalog.json"
MAX_LABEL_LENGTH = 4096
VALID_UNITS = {"case", "each", "lb", "kg"}


def validate_barcode(value: str) -> bool:
    """Return whether an ASCII UPC-A (12) or EAN-13 string has a valid check digit.

    This proves syntax only, not a GS1 allocation, product identity, or package
    size. Leading zeros are significant; integers and Unicode digits fail.
    """
    if not isinstance(value, str) or len(value) not in (12, 13):
        return False
    if not value.isascii() or not value.isdigit():
        return False
    body = [int(char) for char in value[:-1]]
    weighted = sum(digit * (3 if index % 2 == 0 else 1)
                   for index, digit in enumerate(reversed(body)))
    return (10 - weighted % 10) % 10 == int(value[-1])


def load_catalog(path: str | Path | None = None) -> list[dict]:
    """Read a catalog with stable IDs and known units; reject malformed data."""
    source = Path(path) if path is not None else CATALOG_PATH
    items = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(items, list) or not items:
        raise ValueError("Catalog must be a nonempty array of products.")
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Catalog entries must be objects.")
        pid = item.get("product_id")
        if not isinstance(pid, str) or not pid or pid in seen_ids:
            raise ValueError("Catalog product IDs must be unique, nonempty strings.")
        seen_ids.add(pid)
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            raise ValueError("Each catalog product requires a name.")
        if item.get("unit") not in VALID_UNITS:
            raise ValueError("Catalog contains an unsupported receiving unit.")
        if item.get("barcode") is not None and not validate_barcode(item["barcode"]):
            raise ValueError("Catalog barcodes must be valid UPC-A or EAN-13 strings.")
        for flag in ("requires_weight", "requires_lot", "requires_expiry"):
            if not isinstance(item.get(flag), bool):
                raise ValueError(f"Catalog field {flag} must be a boolean.")
        aliases = item.get("aliases", [])
        if not isinstance(aliases, list) or not all(isinstance(a, str) for a in aliases):
            raise ValueError("Product aliases must be a list of strings.")
    return items


def _normalize_label(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _label_candidates(catalog: list[dict], text: str) -> set[str]:
    normalized = _normalize_label(text)
    if not normalized:
        return set()
    return {
        item["product_id"] for item in catalog
        if normalized in {_normalize_label(alias)
                          for alias in [item["name"], *item.get("aliases", [])]}
    }


def _decision(product_id: str | None, method: str, reason: str) -> dict:
    return {"product_id": product_id, "method": method, "reason": reason,
            "requires_review": True}


def match_item(catalog: list[dict], barcode: str = "", label_text: str = "") -> dict:
    """Suggest one catalog identity or abstain; never infer a receiving count.

    A supplied invalid or unknown code cannot be silently replaced by a text
    match. Exact normalized aliases are used only when no barcode was supplied.
    Ambiguous labels and barcode/label conflicts require manual resolution.
    """
    if not isinstance(barcode, str) or not isinstance(label_text, str):
        return _decision(None, "abstain", "Barcode and label text must be strings.")
    barcode = barcode.strip()
    if len(label_text) > MAX_LABEL_LENGTH:
        return _decision(None, "abstain", "Label text exceeds the local lookup limit.")
    label_matches = _label_candidates(catalog, label_text)
    if barcode:
        if not validate_barcode(barcode):
            return _decision(None, "abstain", "Barcode length or check digit is invalid; re-scan or resolve manually.")
        candidates = {item["product_id"] for item in catalog if item.get("barcode") == barcode}
        if len(candidates) != 1:
            reason = "Barcode is not in this catalog." if not candidates else "Barcode maps to more than one catalog item."
            return _decision(None, "abstain", reason + " Staff must resolve the item.")
        candidate = next(iter(candidates))
        if label_matches and candidate not in label_matches:
            return _decision(None, "abstain", "Barcode and label identify different items; staff must check the package.")
        return _decision(candidate, "barcode", "Exact local barcode match. Confirm the item and actual receiving unit.")
    if len(label_matches) == 1:
        return _decision(next(iter(label_matches)), "label_rules", "Exact catalog name or alias match. This is a text rule, not OCR or AI.")
    if len(label_matches) > 1:
        return _decision(None, "abstain", "Label could describe multiple package variants; staff must choose the actual item.")
    return _decision(None, "abstain", "No exact catalog match; enter or correct the item manually.")
