import csv
from pathlib import Path
import tempfile
import unittest

from evaluation.observations import FIELDS, read_observations, summarize


class ObservationTests(unittest.TestCase):
    def write(self, rows, directory):
        path = Path(directory) / "observations.csv"
        with path.open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_empty_template_does_not_claim_zero_cost(self):
        report = summarize([])
        self.assertEqual(report["status"], "no_observations_yet")
        self.assertIsNone(report["strategies"]["manual"]["measured_total_cost_usd"])

    def test_missing_costs_stay_unknown_and_timing_has_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write([dict(observation_id="test-1", strategy="manual", transaction_ref="synthetic-test", accepted="true", staff_seconds="20")], directory)
            group = summarize(read_observations(path))["strategies"]["manual"]
        self.assertEqual(group["staff_seconds"], {"measured_observations": 1, "median": 20})
        self.assertIsNone(group["audited_final_record_accuracy"])
        self.assertIsNone(group["measured_cost_per_accepted_receipt_usd"])

    def test_cost_per_accepted_includes_failed_attempt_cost(self):
        # Deliberately fabricated numbers exist only in this unit test, never in
        # the blank pilot template or observed-data report.
        with tempfile.TemporaryDirectory() as directory:
            path = self.write([
                dict(observation_id="test-1", strategy="manual", transaction_ref="test-A", accepted="true", model_cost_usd="0", hosting_cost_usd="0.1", staff_cost_usd="1"),
                dict(observation_id="test-2", strategy="manual", transaction_ref="test-B", accepted="false", model_cost_usd="0", hosting_cost_usd="0.1", staff_cost_usd="1")], directory)
            group = summarize(read_observations(path))["strategies"]["manual"]
        self.assertAlmostEqual(group["measured_cost_per_accepted_receipt_usd"], 2.2)

    def test_nonfinite_negative_and_duplicate_values_fail(self):
        for invalid in ["nan", "inf", "-1"]:
            with tempfile.TemporaryDirectory() as directory:
                path = self.write([dict(observation_id="test-1", strategy="manual", transaction_ref="test", accepted="true", staff_seconds=invalid)], directory)
                with self.assertRaises(ValueError):
                    read_observations(path)
        with tempfile.TemporaryDirectory() as directory:
            row = dict(observation_id="duplicate", strategy="manual", transaction_ref="test", accepted="true")
            with self.assertRaises(ValueError):
                read_observations(self.write([row, row], directory))


if __name__ == "__main__":
    unittest.main()
