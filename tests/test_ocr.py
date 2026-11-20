from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from evaluation.ocr_run import run_ocr_smoke
from receiving.matching import load_catalog
from receiving.ocr import extract_text, suggest_from_ocr

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "synthetic" / "labels"
BEANS = LABELS / "demo-beans-case.png"


class OcrTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("tesseract"), "Optional local Tesseract is not installed")
    def test_real_local_ocr_on_three_synthetic_labels(self):
        report = run_ocr_smoke()
        self.assertEqual(report["case_count"], 3)
        self.assertEqual(report["ocr_success_count"], 3)
        self.assertEqual(report["correct_item_count"], 3)
        self.assertTrue(report["separate_from_text_benchmark"])
        self.assertIsNone(report["staff_time_seconds"])
        self.assertIsNone(report["operating_cost_usd"])

    def test_no_binary_is_explicitly_unavailable(self):
        with patch("receiving.ocr.shutil.which", return_value=None):
            result = extract_text(BEANS, allowed_root=LABELS)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["text"], "")

    def test_timeout_does_not_return_partial_text(self):
        with patch("receiving.ocr.shutil.which", return_value="/usr/bin/tesseract"), \
             patch("receiving.ocr.subprocess.run", side_effect=subprocess.TimeoutExpired("tesseract", 0.1)):
            result = extract_text(BEANS, allowed_root=LABELS, timeout_seconds=0.1)
        self.assertEqual(result["error_type"], "timeout")
        self.assertEqual(result["text"], "")

    def test_engine_failure_is_not_an_abstention_success(self):
        with patch("receiving.ocr.shutil.which", return_value="/usr/bin/tesseract"), \
             patch("receiving.ocr.subprocess.run", return_value=subprocess.CompletedProcess([], 1)) as invoked:
            result = extract_text(BEANS, allowed_root=LABELS)
        self.assertEqual(result["status"], "error")
        self.assertFalse(invoked.call_args.kwargs["shell"])
        self.assertEqual(invoked.call_args.args[0][-4:], ["-l", "eng", "--psm", "6"])

    def test_paths_outside_approved_directory_fail_before_execution(self):
        with patch("receiving.ocr.subprocess.run") as invoked:
            result = extract_text(ROOT / "data" / "synthetic" / "catalog.json", allowed_root=LABELS)
        self.assertEqual(result["error_type"], "path_not_allowed")
        invoked.assert_not_called()

    def test_invalid_image_and_invalid_timeout_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "bad.png"
            image.write_bytes(b"not a png")
            self.assertEqual(extract_text(image, allowed_root=directory)["status"], "error")
        self.assertEqual(extract_text(BEANS, allowed_root=LABELS, timeout_seconds=100)["error_type"], "invalid_timeout")

    def test_ocr_matching_ignores_embedded_ids_and_abstains_on_conflicts(self):
        catalog = load_catalog()
        result = suggest_from_ocr(catalog, "Catalog ID: DEMO-BEANS-CASE")
        self.assertIsNone(result["product_id"])
        result = suggest_from_ocr(catalog, "Black beans, 12 x 15 oz case\nRolled oats, 6 x 18 oz case")
        self.assertIsNone(result["product_id"])
        result = suggest_from_ocr(catalog, "Black beans, 12 x 15 oz case")
        self.assertEqual(result["product_id"], "DEMO-BEANS-CASE")
        self.assertTrue(result["requires_review"])


if __name__ == "__main__":
    unittest.main()
