import os
import unittest
from unittest.mock import MagicMock, patch

from config.settings import EmbeddingConfig, GraphRAGConfig, ChromaConfig, Neo4jConfig, LLMConfig, CacheConfig
from core.embeddings import SentenceTransformerEmbedding
from core.services import SemanticCacheProvider, GroqLLMProvider, JSONDocumentProcessor


class TestEmbeddingService(unittest.TestCase):
    def test_embed_returns_vector(self):
        with patch("core.embeddings.SentenceTransformer") as MockST:
            class _Enc:
                def tolist(self):
                    return [0.1, 0.2, 0.3]
            mock_model = MagicMock()
            mock_model.encode.return_value = _Enc()
            MockST.return_value = mock_model
            emb = SentenceTransformerEmbedding(EmbeddingConfig(model_name="mock"))
            vec = emb.embed("hello")
            self.assertIsInstance(vec, list)
            self.assertEqual(len(vec), 3)

    def test_embed_empty_string(self):
        with patch("core.embeddings.SentenceTransformer") as MockST:
            mock_model = MagicMock()
            mock_model.encode.return_value = []
            MockST.return_value = mock_model
            emb = SentenceTransformerEmbedding(EmbeddingConfig(model_name="mock"))
            vec = emb.embed("")
            self.assertEqual(vec, [])


class TestSemanticCacheProvider(unittest.TestCase):
    def setUp(self):
        base = os.path.join("t_for_testing", "chroma_db_unit")
        self.cfg = GraphRAGConfig(
            chroma=ChromaConfig(path=base),
            embedding=EmbeddingConfig(model_name="mock"),
            neo4j=Neo4jConfig(use_neo4j=False),
            llm=LLMConfig(model_name="mock", api_key="mock"),
            cache=CacheConfig(threshold=0.1),
        )

    def test_store_and_lookup(self):
        with patch("core.embeddings.embed_text", return_value=[0.0, 0.1, 0.2]):
            cache = SemanticCacheProvider(self.cfg)
            cache.store("q1", "ans1")
            hit = cache.lookup("q1")
            self.assertIsNotNone(hit)
            self.assertEqual(hit["answer"], "ans1")


class TestLLMProvider(unittest.TestCase):
    def test_generate_returns_content(self):
        with patch("core.services.ChatGroq") as MockLLM:
            mock = MagicMock()
            mock.invoke.return_value = type("Resp", (), {"content": "OK"})()
            MockLLM.return_value = mock
            prov = GroqLLMProvider(LLMConfig(model_name="mock", api_key="mock"))
            out = prov.generate("hi")
            self.assertEqual(out, "OK")


class TestJSONDocumentProcessor(unittest.TestCase):
    def test_load_documents(self):
        proc = JSONDocumentProcessor()
        path = os.path.join("t_for_testing", "temp_question.json")
        docs = proc.load_documents(path)
        self.assertTrue(isinstance(docs, list) or isinstance(docs, dict))


if __name__ == "__main__":
    unittest.main()
