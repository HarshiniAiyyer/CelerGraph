import unittest
from fastapi.testclient import TestClient
from api.main import app


class TestRateLimit(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_rate_limit(self):
        import time
        time.sleep(6)
        for _ in range(10):
            r = self.client.get("/api/health")
            self.assertEqual(r.status_code, 200)
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 429)


if __name__ == "__main__":
    unittest.main()
