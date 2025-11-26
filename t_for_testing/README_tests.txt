Requirements:
- Python 3.10+
- FastAPI and Starlette installed in the environment
- Chromadb available (installed in the provided environment)

Run all tests:
python -m unittest discover -s t_for_testing -p "test_*.py"

Run unit tests only:
python -m unittest discover -s t_for_testing/unit -p "test_*.py"

Run integration tests only:
python -m unittest discover -s t_for_testing/integration -p "test_*.py"

Notes:
- Integration tests mock LLM calls and embeddings to avoid network and heavy downloads.
- Ensure the API server dependencies are available; the tests instantiate the FastAPI app directly.
