import os
import sys
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api.main import app


def main() -> None:
    client = TestClient(app)

    # Health
    r = client.get('/api/health')
    print('GET /api/health ->', r.status_code, r.json())

    # Non-streaming chat
    r = client.post('/api/chat', json={'message': 'What does answer_question do?', 'bypass_cache': True})
    print('POST /api/chat ->', r.status_code)
    print(r.json())

    # Streaming chat (collect full body)
    r = client.post('/api/chat/stream', json={'message': 'Explain GraphRAG retrieval briefly', 'bypass_cache': True})
    content = r.content.decode('utf-8')
    print('POST /api/chat/stream ->', r.status_code)
    print(content[:200] + ('...' if len(content) > 200 else ''))


if __name__ == '__main__':
    main()
