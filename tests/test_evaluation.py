from copy import deepcopy
import unittest

from evaluation.run import evaluate_strategy, run_benchmark


def decision(pid):
    return {"product_id": pid, "method": "test", "requires_review": True}


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cases = [
            {"case_id": "known", "input": {"barcode": "", "label_text": "specific item"}, "expected_product_id": "DEMO-A"},
            {"case_id": "unknown", "input": {"barcode": "", "label_text": "unknown item"}, "expected_product_id": None},
        ]

    def test_always_abstain_is_not_perfect_retrieval(self):
        result = evaluate_strategy(self.cases, lambda evidence: decision(None), {"DEMO-A"})
        self.assertEqual(result["correct_abstention_count"], 1)
        self.assertEqual(result["missed_match_count"], 1)
        self.assertEqual(result["known_item_recall"], 0)
        self.assertEqual(result["suggestion_coverage"], 0)
        self.assertIsNone(result["suggestion_precision"])
        self.assertEqual(result["exact_decision_accuracy"], 0.5)

    def test_unknown_false_positive_penalizes_precision(self):
        result = evaluate_strategy(self.cases, lambda evidence: decision("DEMO-A"), {"DEMO-A"})
        self.assertEqual(result["correct_match_count"], 1)
        self.assertEqual(result["wrong_suggestion_count"], 1)
        self.assertEqual(result["suggestion_precision"], 0.5)

    def test_errors_are_not_successful_abstentions(self):
        def fail(evidence):
            raise RuntimeError("Provider unavailable; sensitive details must not reach report.")
        result = evaluate_strategy(self.cases, fail, {"DEMO-A"})
        self.assertEqual(result["error_count"], 2)
        self.assertEqual(result["correct_abstention_count"], 0)
        self.assertEqual(result["exact_decision_accuracy"], 0)
        self.assertNotIn("sensitive details", str(result))

    def test_unknown_product_and_missing_review_are_errors(self):
        result = evaluate_strategy(self.cases, lambda evidence: decision("INVENTED"), {"DEMO-A"})
        self.assertEqual(result["error_count"], 2)
        result = evaluate_strategy(self.cases, lambda evidence: {"product_id": None}, {"DEMO-A"})
        self.assertEqual(result["error_count"], 2)

    def test_provider_safe_fallback_still_counts_as_error(self):
        result = evaluate_strategy(self.cases, lambda evidence: {
            **decision(None), "error_type": "TimeoutException", "reason": "Use manual entry."}, {"DEMO-A"})
        self.assertEqual(result["error_count"], 2)
        self.assertEqual(result["correct_abstention_count"], 0)

    def test_predictors_receive_only_evidence(self):
        received = []
        before = deepcopy(self.cases)
        def predictor(evidence):
            received.append(set(evidence))
            evidence["barcode"] = "mutated"
            return decision(None)
        evaluate_strategy(self.cases, predictor, {"DEMO-A"})
        self.assertEqual(received, [{"barcode", "label_text"}, {"barcode", "label_text"}])
        self.assertEqual(self.cases, before)

    def test_empty_dataset_has_no_fabricated_rates(self):
        result = evaluate_strategy([], lambda evidence: decision(None), {"DEMO-A"})
        self.assertIsNone(result["exact_decision_accuracy"])
        self.assertIsNone(result["algorithm_latency_ms"]["median"])
        self.assertIsNone(result["staff_time_seconds"])
        self.assertIsNone(result["operating_cost_usd"])

    def test_duplicate_cases_or_invalid_ground_truth_fail(self):
        with self.assertRaises(ValueError):
            evaluate_strategy([self.cases[0], self.cases[0]], lambda evidence: decision(None), {"DEMO-A"})
        with self.assertRaises(ValueError):
            evaluate_strategy(self.cases, lambda evidence: decision(None), {"ANOTHER"})

    def test_default_benchmark_does_not_invoke_ai(self):
        report = run_benchmark()
        self.assertGreaterEqual(report["case_count"], 30)
        self.assertEqual(report["strategies"]["barcode_then_local_model"]["status"], "not_run")
        rules = report["strategies"]["barcode_plus_label_rules"]
        self.assertEqual(rules["wrong_suggestion_count"], 0)
        self.assertGreaterEqual(rules["missed_match_count"], 2)
        self.assertIsNone(rules["operating_cost_usd"])


if __name__ == "__main__":
    unittest.main()
