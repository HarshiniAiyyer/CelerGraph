# chroma_setup.py
import os
import chromadb


def init_chroma():
    return chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "vectorstore/chroma_db"))


def create_collections(client: chromadb.ClientAPI):
    names = {c.name for c in client.list_collections()}

    if "node_embeddings" not in names:
        client.create_collection(
            name="node_embeddings",
            metadata={"hnsw:space": "cosine"},
        )

    if "code_chunks" not in names:
        client.create_collection(
            name="code_chunks",
            metadata={"hnsw:space": "cosine"},
        )

    if "semantic_cache" not in names:
        client.create_collection(
            name="semantic_cache",
            metadata={"hnsw:space": "cosine"},
        )


if __name__ == "__main__":
    client = init_chroma()
    create_collections(client)
    print("Chroma collections ready.")

