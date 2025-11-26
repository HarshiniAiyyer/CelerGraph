import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from api.main import app


class TestStreamingChat(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_stream_endpoint(self):
        def fake_stream():
            yield "A"
            yield "B"
            yield "C"

        with patch("api.controllers.stream_answer", return_value=fake_stream()):
            with self.client.stream("POST", "/api/chat/stream", json={"message": "Hi"}) as r:
                self.assertEqual(r.status_code, 200)
                data = b"".join(list(r.iter_bytes()))
                self.assertEqual(data.decode(), "ABC")


if __name__ == "__main__":
    unittest.main()
