import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from api.main import app


class TestAPIIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")

    def test_cache_clear_endpoint(self):
        response = self.client.post("/api/cache/clear")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("cleared", body)

    def test_chat_endpoint_with_mocked_answer(self):
        with patch("api.controllers.answer_question", return_value="Hello"):
            response = self.client.post("/api/chat", json={"message": "Hi"})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["answer"], "Hello")

    def test_index_endpoint(self):
        abs_path = os.path.join(os.getcwd(), "t_for_testing")
        with patch("core.embeddings.embed_text", return_value=[0.1, 0.2, 0.3]):
            response = self.client.post("/api/index", json={"path": abs_path})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertIn("indexed_files", body)
            self.assertIn("chunks_processed", body)


if __name__ == "__main__":
    unittest.main()
