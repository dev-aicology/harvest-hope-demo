"""Optional-model contract tests; no model service is called."""
import json
import unittest
from unittest.mock import MagicMock, patch
import httpx

from receiving.ai import suggest_with_ollama
from receiving.config import Settings
from receiving.matching import load_catalog


class LocalModelTest(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()

    def client_mock(self, output):
        manager = MagicMock()
        client = manager.return_value.__enter__.return_value
        info, answer = MagicMock(), MagicMock()
        info.json.return_value = {"details": {"parameter_size": "test-only"}}
        answer.content = json.dumps(output).encode()
        answer.json.return_value = {"message": {"content": json.dumps(output)}, "prompt_eval_count": 12, "eval_count": 9}
        client.post.side_effect = [info, answer]
        return manager, client

    def test_schema_validation_and_known_catalog_gate(self):
        output = {"product_id": "DEMO-BEANS-CASE", "reason": "Matching label", "evidence": "black beans", "certainty": "possible"}
        manager, client = self.client_mock(output)
        with patch("receiving.ai.httpx.Client", manager):
            result = suggest_with_ollama(self.catalog, "black beans", "http://127.0.0.1:11434", "test-model")
        self.assertEqual(result["product_id"], "DEMO-BEANS-CASE")
        self.assertTrue(result["requires_review"])
        payload = client.post.call_args.kwargs["json"]
        self.assertFalse(payload["stream"])
        self.assertNotIn("tools", payload)
        self.assertFalse(manager.call_args.kwargs["trust_env"])
        self.assertFalse(manager.call_args.kwargs["follow_redirects"])

    def test_unsupported_item_or_extra_write_fields_abstain(self):
        for output in (
            {"product_id": "INVENTED-ID", "reason": "untrusted", "certainty": "likely"},
            {"product_id": "DEMO-BEANS-CASE", "reason": "untrusted", "certainty": "likely", "approve": True},
        ):
            manager, _ = self.client_mock(output)
            with patch("receiving.ai.httpx.Client", manager):
                result = suggest_with_ollama(self.catalog, "anything", "http://localhost:11434", "test-model")
            self.assertIsNone(result["product_id"])
            self.assertIn("error_type", result)

    def test_timeout_fails_to_manual_without_remote_fallback(self):
        manager = MagicMock()
        client = manager.return_value.__enter__.return_value
        client.post.side_effect = httpx.TimeoutException("Do not expose private response data")
        with patch("receiving.ai.httpx.Client", manager):
            result = suggest_with_ollama(self.catalog, "label", "http://localhost:11434", "test-model")
        self.assertIsNone(result["product_id"])
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(client.post.call_count, 1)

    def test_cloud_configuration_and_nonlocal_url_refused(self):
        with self.assertRaises(ValueError):
            Settings(ai_provider="ollama", ollama_model="some-model:cloud")
        for url in ("https://api.example.invalid", "http://localhost:11434/evil", "http://token@localhost:11434"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                suggest_with_ollama(self.catalog, "label", url, "test-model")

    def test_remote_backed_model_refused_before_inference(self):
        manager = MagicMock()
        client = manager.return_value.__enter__.return_value
        client.post.return_value.json.return_value = {"remote_host": "remote.invalid"}
        with patch("receiving.ai.httpx.Client", manager):
            result = suggest_with_ollama(self.catalog, "label", "http://localhost:11434", "test-model")
        self.assertIsNone(result["product_id"])
        self.assertEqual(client.post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
