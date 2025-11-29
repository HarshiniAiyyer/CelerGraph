"""GraphRAG: Retrieval-Augmented Generation with Knowledge Graph Integration.

A hybrid RAG system that combines semantic search over code chunks and knowledge
graph nodes with LLM-powered answer generation. Features semantic caching to
reduce redundant LLM calls and provides citation-rich responses with references.

Main Components:
    - Semantic retrieval from ChromaDB (code chunks and nodes)
    - Graph expansion via Neo4j (optional)
    - LLM-powered answer generation via Groq
    - Semantic caching for similar questions
    - Response formatting with citations and references

Usage:
    python graphrag.py
"""

import os
import re
import sys
import time
from typing import Dict, List, Any, Optional, Tuple, Sequence, Mapping, TypedDict, cast

import chromadb
from config.myapikeys import (
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD
)
from core.code_exceptions import ChromaError, EmbeddingError, LLMError, Neo4jError
from config.logger import log
from core.embeddings import embed_text, get_model
from core.semantic_cache import SemanticCache
from core.retrieval import retrieve_similar_nodes
from observability.rag.rag_events import log_rag_event
from observability.rag.rag_metrics import record_retrieval_metrics, record_generation_metrics

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnableParallel,
    RunnableLambda,
    RunnablePassthrough,
)
from dotenv import load_dotenv
load_dotenv()



#groq
MODEL_NAME = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-120b")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "800"))

try:
    log.info("Initializing LLM")
    llm = ChatGroq(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    log.info("LLM initialized successfully")
except Exception as exc:
    log.exception("Failed to initialize LLM")
    raise LLMError(f"LLM initialization failed: {exc}") from exc

# Preload embedding model at startup to avoid first-request latency
try:
    _ = get_model()
    log.info("Embedding model preloaded")
except Exception:
    log.warning("Embedding model preload failed")


# chromadb (code chunks + node embeddings)
try:
    log.info("Connecting to ChromaDB")
    client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "vectorstore/chroma_db"))

    code_collection = client.get_or_create_collection(
        name="code_chunks",
        metadata={"hnsw:space": "cosine"},
    )

    node_collection = client.get_or_create_collection(
        name="node_embeddings",
        metadata={"hnsw:space": "cosine"},
    )
    log.info("ChromaDB collections ready")
except Exception as exc:
    log.exception("Failed to initialize ChromaDB")
    raise ChromaError(f"ChromaDB initialization failed: {exc}") from exc

# Neo4j graph neighbors
USE_NEO4J = False
driver = None

if USE_NEO4J:
    try:
        log.info(f"Connecting to Neo4j at {NEO4J_URI}")
        from neo4j import GraphDatabase
        if NEO4J_URI is None:
            raise Neo4jError("NEO4J_URI is not set")
        if NEO4J_USERNAME is None:
            raise Neo4jError("NEO4J_USERNAME is not set")
        if NEO4J_PASSWORD is None:
            raise Neo4jError("NEO4J_PASSWORD is not set")
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        driver.verify_connectivity()
        log.info("Neo4j connection established")
    except Exception as exc:
        log.exception("Failed to connect to Neo4j")
        raise Neo4jError(f"Neo4j connection failed: {exc}") from exc


def expand_graph(node_ids: List[str], depth: int = 1) -> List[str]:
    """Expand a set of node IDs by retrieving their neighbors from Neo4j.
    
    Performs a graph traversal to find all nodes connected to the given node IDs
    up to a specified depth. Only executes if USE_NEO4J is True.
    
    Args:
        node_ids: List of node identifiers to expand.
        depth: Maximum depth of the graph traversal. Defaults to 1.
    
    Returns:
        List of neighbor node IDs found in the graph. Returns empty list if
        USE_NEO4J is False or if no neighbors are found.
    
    Raises:
        Neo4jError: If Neo4j query execution fails.
    """
    if not USE_NEO4J:
        log.debug("Neo4j expansion disabled")
        return []
    
    if not driver:
        raise Neo4jError("Neo4j driver not initialized")

    try:
        log.debug(f"Expanding graph for {len(node_ids)} nodes (depth={depth})")
        query = """
        UNWIND $ids AS id
        MATCH (n {id: id})-[*1..$depth]-(m)
        RETURN DISTINCT m.id AS id
        """
        with driver.session() as s:
            result = s.run(query, ids=node_ids, depth=depth)
            neighbors = [r["id"] for r in result]
            log.debug(f"Found {len(neighbors)} neighbor nodes")
            return neighbors
    except Exception as exc:
        log.exception("Graph expansion failed")
        raise Neo4jError(f"Graph expansion failed: {exc}") from exc


# Retrieve code chunks with citations
def retrieve_code_chunks(q: str, top_k: int = 8) -> List[Dict[str, Any]]:
    """Retrieve the most similar code chunks from ChromaDB based on a query.
    
    Embeds the query text and performs semantic similarity search against
    the code_chunks collection in ChromaDB.
    
    Args:
        q: Query string to search for.
        top_k: Maximum number of results to return. Defaults to 8.
    
    Returns:
        List of dictionaries containing:
            - id: Unique identifier for the chunk
            - text: The actual code chunk content
            - similarity: Similarity score (0-1, higher is better)
            - metadata: Additional metadata about the chunk
    
    Raises:
        ChromaError: If ChromaDB query fails.
        EmbeddingError: If text embedding fails.
    """
    if not q:
        log.warning("Empty query provided for code chunk retrieval")
        return []
    
    try:
        log.debug(f"Retrieving code chunks (query: {q[:50]}..., top_k={top_k})")
        t0 = time.perf_counter()
        vec: Sequence[float] = embed_text(q)

        class RetrievedItem(TypedDict):
            id: str
            text: str
            similarity: float
            metadata: Mapping[str, Any]

        out: List[RetrievedItem] = []

        res = code_collection.query(query_embeddings=[vec], n_results=top_k)
        ids = cast(List[List[str]], res.get("ids", [[]]) if hasattr(res, "get") else [[]])[0]
        docs = cast(List[List[str]], res.get("documents", [[]]) if hasattr(res, "get") else [[]])[0]
        dists = cast(List[List[float]], res.get("distances", [[]]) if hasattr(res, "get") else [[]])[0]
        metas = cast(List[List[Mapping[str, Any]]], res.get("metadatas", [[]]) if hasattr(res, "get") else [[]])[0]

        if not ids:
            log.debug("No code chunks found for query")
            log.info(f"Code chunk retrieval took {(time.perf_counter() - t0) * 1000:.3f}ms")
            return []

        for doc_id, doc, dist, meta in zip(ids, docs, dists, metas):
            out.append(
                {
                    "id": doc_id,
                    "text": doc,
                    "similarity": 1 - dist,
                    "metadata": meta,
                }
            )
        log.info(f"Retrieved {len(out)} code chunks")
        retrieval_latency_ms = (time.perf_counter() - t0) * 1000
        log.info(f"Code chunk retrieval took {retrieval_latency_ms:.3f}ms")

        num_candidates = top_k
        num_selected = len(out)
        avg_score = sum([r["similarity"] for r in out]) / num_selected if num_selected > 0 else 0

        record_retrieval_metrics(
            num_candidates=num_candidates,
            num_selected=num_selected,
            retrieval_latency_ms=retrieval_latency_ms,
            avg_score=avg_score,
        )
        return cast(List[Dict[str, Any]], out)
    except (ChromaError, EmbeddingError):
        raise
    except Exception as exc:
        log.exception("Code chunk retrieval failed")
        raise ChromaError(f"Code chunk retrieval failed: {exc}") from exc


# Build citation-rich context
def build_context(nodes: List[Dict[str, Any]], chunks: List[Dict[str, Any]], 
                   neighbors: List[str]) -> str:
    """Build a formatted context string from retrieved nodes, chunks, and neighbors.
    
    Combines retrieved nodes, code chunks, and graph neighbors into a single
    formatted string suitable for passing to the LLM prompt. Includes similarity
    scores and citations for traceability.
    
    Args:
        nodes: List of retrieved node dictionaries with 'id', 'text', and 'similarity'.
        chunks: List of retrieved code chunk dictionaries with 'id', 'text', and 'similarity'.
        neighbors: List of neighbor node IDs from graph expansion.
    
    Returns:
        Formatted context string with sections for nodes, chunks, and neighbors,
        each with citations and similarity scores.
    """
    parts = []

    parts.append("=== Nodes ===")
    for n in nodes[:8]:
        parts.append(f"[node:{n['id']}] score={n['similarity']:.3f}")
        parts.append(n["text"])
        parts.append("")

    parts.append("=== Code Chunks ===")
    for c in chunks[:8]:
        parts.append(f"[chunk:{c['id']}] score={c['similarity']:.3f}")
        parts.append(c["text"])
        parts.append("")

    if neighbors:
        parts.append("=== Neighbor Nodes ===")
        parts.append("\n".join([f"[neighbor:{nid}]" for nid in neighbors]))

    return "\n".join(parts)


# Prompt template with citations
PROMPT = ChatPromptTemplate.from_template(
    """
You are a codebase analysis assistant.

Use only the following context. Format your response as follows:
1. First, provide a comprehensive answer in natural sentence structure, weaving in the information naturally.
2. Then, on a new line with "References:", list all the citations used in the format [node:ID] or [chunk:ID] with their locations.

If information is missing, say:
"The context does not contain the required information."

---------------------
CONTEXT:
{context}
---------------------

Question:
{question}

Answer:
"""
)

# LCEL Pipeline

nodes_retriever = RunnableLambda(lambda q: retrieve_similar_nodes(q, top_k=8))
chunks_retriever = RunnableLambda(lambda q: retrieve_code_chunks(q, top_k=8))

parallel_retrieval = RunnableParallel(
    question=RunnablePassthrough(),
    nodes=nodes_retriever,
    chunks=chunks_retriever,
)

neighbors_step = RunnableLambda(
    lambda d: expand_graph([n["id"] for n in d["nodes"]], depth=1)
)

with_neighbors = RunnablePassthrough.assign(neighbors=neighbors_step)


def ctx_builder(data: Dict[str, Any]) -> Dict[str, str]:
    """Build context from retrieval pipeline output.
    
    Intermediate function in the LCEL pipeline that takes the output from
    parallel retrieval and graph expansion, then formats it into a context
    string suitable for the prompt template.
    
    Args:
        data: Dictionary containing 'question', 'nodes', 'chunks', and 'neighbors'.
    
    Returns:
        Dictionary with 'question' and 'context' keys for prompt template.
    """
    ctx = build_context(data["nodes"], data["chunks"], data.get("neighbors", []))
    return {"question": data["question"], "context": ctx}


context_builder = RunnableLambda(ctx_builder)

rag_chain = (
    parallel_retrieval
    | with_neighbors
    | context_builder
    | PROMPT
    | llm
    | StrOutputParser()
)

# Semantic Cache (previous implementation)
try:
    cache = SemanticCache(threshold=0.9)
    log.info("Semantic cache initialized")
except Exception as exc:
    log.exception("Failed to initialize semantic cache")
    raise ChromaError(f"Cache initialization failed: {exc}") from exc


def format_response(answer: str) -> Tuple[str, List[str]]:
    """Format LLM response with citations organized into a References section.
    
    Ensures response follows the desired format:
    1. Natural sentence structure first
    2. References section at the end with all citations
    
    Extracts citations in the format [node:ID] or [chunk:ID] and reorganizes
    them into a dedicated References section at the end of the response.
    
    Args:
        answer: Raw LLM response text potentially containing inline citations.
    
    Returns:
        Tuple of (formatted_answer, list_of_references).
    """
    log.info("Entering format_response")
    log.debug(f"Raw answer for format_response: {answer}")
    # If response already has References section, return as-is
    if "References:" in answer or "references:" in answer:
        # Extract references from existing section if present
        existing_refs = re.findall(r'\[(?:node|chunk):[^\]]+\]', answer)
        log.debug(f"Existing references found: {existing_refs}")
        return answer, list(dict.fromkeys(existing_refs))
    
    # Otherwise, extract citations and reorganize
    lines = answer.split("\n")
    citations: List[str] = []
    body_lines: List[str] = []
    
    for line in lines:
        # Collect lines with citations
        if "[node:" in line or "[chunk:" in line:
            # Extract citation references
            refs = re.findall(r'\[(?:node|chunk):[^\]]+\]', line)
            citations.extend(refs)
            # Keep the line in body but mark for later processing
            body_lines.append(line)
        else:
            body_lines.append(line)
    
    # If we found citations, reorganize
    if citations:
        body = "\n".join(body_lines).strip()
        unique_citations = list(dict.fromkeys(citations))  # Remove duplicates while preserving order
        references_section = "\n".join([f"- {cite}" for cite in unique_citations])
        formatted_answer = f"{body}\n\nReferences:\n{references_section}"
        log.debug(f"Formatted answer with new references: {formatted_answer}")
        log.debug(f"Unique citations: {unique_citations}")
        return formatted_answer, unique_citations
    
    log.debug("No citations found in answer.")
    return answer, []


def is_greeting(question: str) -> bool:
    """Check if the question is a greeting."""
    greetings = [
        "hi", "hello", "hey", "greetings", "good morning", "good afternoon", 
        "good evening", "howdy", "what's up", "sup", "yo"
    ]
    question_lower = question.strip().lower()
    return any(greeting in question_lower for greeting in greetings)

def summarize_question(question: str) -> str:
    """Summarize a question into a short 3-5 word title."""
    try:
        log.info(f"Summarizing question: {question[:50]}...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Summarize the following question into a short, concise title of 3-5 words. Do not use quotes."),
            ("human", "{question}")
        ])
        chain = prompt | llm | StrOutputParser()
        summary = chain.invoke({"question": question})
        return summary.strip().strip('"')
    except Exception as e:
        log.error(f"Failed to summarize question: {e}")
        return question # Fallback to original question


def direct_llm_answer(question: str, llm_overrides: Optional[Dict[str, Any]] = None) -> str:
    """Get a direct answer from the LLM without using knowledge graph."""
    try:
        log.info(f"Using direct LLM for question: {question[:50]}...")
        
        # Create a simple conversation prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant. Answer the user's question directly and conversationally."),
            ("human", "{question}")
        ])
        
        # Use either override LLM or default LLM
        current_llm = llm
        if llm_overrides:
            current_llm = ChatGroq(
                model=llm_overrides.get("model_name", MODEL_NAME),
                temperature=llm_overrides.get("temperature", TEMPERATURE),
                max_tokens=llm_overrides.get("max_tokens", MAX_TOKENS),
            )
        
        chain = prompt | current_llm | StrOutputParser()
        answer = chain.invoke({"question": question})
        
        return answer
    except Exception as exc:
        log.exception("Direct LLM answer failed")
        raise LLMError(f"Direct LLM answer failed: {exc}") from exc


def answer_question(question: str, bypass_cache: bool = False, llm_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    print("*** ENTERED answer_question FUNCTION ***")
    log.debug("DEBUG: Inside answer_question function.")
    log.info("Entering answer_question")
    log.info(f"bypass_cache: {bypass_cache}")
    """Answer a question using the RAG pipeline with semantic caching.
    
    Processes a user question through the retrieval-augmented generation pipeline.
    First checks the semantic cache for similar previously answered questions.
    If not found, retrieves relevant nodes and code chunks, builds context,
    and generates an answer using the LLM. Results are cached for future queries.
    
    Args:
        question: The user's question as a string.
    
    Returns:
        Formatted answer with citations and references section.
    
    Raises:
        LLMError: If LLM invocation fails.
        ChromaError: If retrieval operations fail.
        EmbeddingError: If text embedding fails.
    """
    if not question:
        log.warning("Empty question provided")
        return {"answer": "Please provide a valid question.", "references": []}
    
    try:
        log.info(f"Processing question: {question[:50]}...")
        
        # Check if it's a greeting - use direct LLM response
        if is_greeting(question):
            log.info("Detected greeting, using direct LLM response")
            return {"answer": direct_llm_answer(question, llm_overrides), "references": []}
        
        # Check cache first (unless bypassed)
        if not bypass_cache:
            cached = cache.lookup(question)
            if cached:
                log.info("Returning cached answer")
                return {"answer": cached["answer"], "references": cached["references"]}

        # Generate new answer using RAG pipeline
        log.debug("Generating new answer via RAG pipeline")
        t0 = time.perf_counter()
        
        # Execute retrieval and context building explicitly to capture context
        t_retrieval_start = time.perf_counter()
        retrieval_results = parallel_retrieval.invoke(question)
        t_retrieval_end = time.perf_counter()
        retrieval_ms = (t_retrieval_end - t_retrieval_start) * 1000
        
        # Calculate retrieval metrics
        chunks = retrieval_results.get("chunks", [])
        nodes = retrieval_results.get("nodes", [])
        total_items = len(chunks) + len(nodes)
        scores = [c["similarity"] for c in chunks] + [n["similarity"] for n in nodes]
        avg_sim = sum(scores) / len(scores) if scores else 0.0
        
        record_retrieval_metrics(
            num_candidates=total_items,
            num_selected=total_items,
            retrieval_latency_ms=retrieval_ms,
            avg_score=avg_sim
        )
        
        graph_data = with_neighbors.invoke(retrieval_results)
        final_context = context_builder.invoke(graph_data)
        context_text = final_context["context"]
        
        # Generate answer
        if llm_overrides:
            override_llm = ChatGroq(
                model=llm_overrides.get("model_name", MODEL_NAME),
                temperature=llm_overrides.get("temperature", TEMPERATURE),
                max_tokens=llm_overrides.get("max_tokens", MAX_TOKENS),
            )
            chain = PROMPT | override_llm | StrOutputParser()
        else:
            chain = PROMPT | llm | StrOutputParser()
            
        t_gen_start = time.perf_counter()
        answer = chain.invoke(final_context)
        t_gen_end = time.perf_counter()
        gen_ms = (t_gen_end - t_gen_start) * 1000
        
        record_generation_metrics(
            generation_latency_ms=gen_ms
        )
        
        log.info(f"RAG pipeline generation took {time.perf_counter() - t0:.3f}s")
        log.debug(f"Raw LLM output before formatting: {answer}")
        formatted_answer, references = format_response(answer)
        log.info(f"Formatted answer: {formatted_answer}")
        log.info(f"References: {references}")
        
        # Check if RAG provided insufficient context - fallback to direct LLM
        negative_markers = [
            "The context does not contain the required information",
            "I don't have enough information",
            "No relevant information found",
            "Unable to find specific information"
        ]
        
        should_fallback = any(marker in formatted_answer for marker in negative_markers)
        
        if should_fallback:
            log.info("RAG provided insufficient context, falling back to direct LLM")
            return {"answer": direct_llm_answer(question, llm_overrides), "references": [], "context": context_text}
        
        # Cache the result unless bypassed
        if not bypass_cache:
            cache.store(question, formatted_answer, references)
        log.info("Answer generated and cached successfully")
        return {
            "answer": formatted_answer, 
            "references": references, 
            "context": context_text,
            "retrieved_context": retrieval_results, # Contains raw nodes and chunks
            "metrics": {
                "retrieval_latency_ms": retrieval_ms,
                "generation_latency_ms": gen_ms,
                "avg_similarity_score": avg_sim
            }
        }
    except (ChromaError, EmbeddingError):
        # For Chroma/Embedding errors, fallback to direct LLM
        log.info("RAG system error, falling back to direct LLM")
        return {"answer": direct_llm_answer(question, llm_overrides), "references": []}
    except Exception as exc:
        log.exception("Answer generation failed, attempting direct LLM fallback")
        try:
            return {"answer": direct_llm_answer(question, llm_overrides), "references": []}
        except Exception as fallback_exc:
            log.exception("Direct LLM fallback also failed")
            raise LLMError(f"Both RAG and direct LLM failed: {exc}") from fallback_exc


def clear_cache() -> None:
    cache.clear()


def stream_answer(question: str, bypass_cache: bool = False, llm_overrides: Optional[Dict[str, Any]] = None):
    if not question:
        yield "Please provide a valid question."
        return
    try:
        # Check if it's a greeting - use direct LLM response
        if is_greeting(question):
            log.info("Detected greeting, using direct LLM response (streaming)")
            answer = direct_llm_answer(question, llm_overrides)
            yield answer
            return
            
        if not bypass_cache:
            cached = cache.lookup(question)
            if cached:
                yield cached["answer"]
                return
        
        # Try RAG pipeline first
        chain = rag_chain
        if llm_overrides:
            override_llm = ChatGroq(
                model=llm_overrides.get("model_name", MODEL_NAME),
                temperature=llm_overrides.get("temperature", TEMPERATURE),
                max_tokens=llm_overrides.get("max_tokens", MAX_TOKENS),
            )
            chain = (
                parallel_retrieval
                | with_neighbors
                | context_builder
                | PROMPT
                | override_llm
                | StrOutputParser()
            )
        
        buf = []
        for chunk in chain.stream(question):
            s = chunk if isinstance(chunk, str) else str(chunk)
            buf.append(s)
            yield s
        final = "".join(buf)
        
        # Check if RAG provided insufficient context - fallback to direct LLM
        negative_markers = [
            "The context does not contain the required information",
            "I don't have enough information",
            "No relevant information found",
            "Unable to find specific information"
        ]
        
        should_fallback = any(marker in final for marker in negative_markers)
        
        if should_fallback:
            log.info("RAG provided insufficient context, falling back to direct LLM (streaming)")
            answer = direct_llm_answer(question, llm_overrides)
            yield answer
            return
        
        if not bypass_cache:
            formatted_final, references = format_response(final)
            cache.store(question, formatted_final, references)
    except (ChromaError, EmbeddingError):
        # For Chroma/Embedding errors, fallback to direct LLM
        log.info("RAG system error, falling back to direct LLM (streaming)")
        answer = direct_llm_answer(question, llm_overrides)
        yield answer
        return
    except Exception as exc:
        log.exception("Streaming answer generation failed, attempting direct LLM fallback")
        try:
            answer = direct_llm_answer(question, llm_overrides)
            yield answer
        except Exception:
            log.exception("Direct LLM fallback also failed")
            yield f"Error: Both RAG and direct LLM failed: {exc}"


# CLI
if __name__ == "__main__":
    print("Initializing GraphRAG...")
    print("  - Loading embedding model...")
    print("  - Connecting to ChromaDB...")
    print("  - Setting up LLM chain...")
    print("\nGraphRAG Ready. Type 'exit' to stop.\n")
    
    try:
        while True:
            q = input("\nAsk: ").strip()
            if q.lower() in {"exit", "quit"}:
                break
            if not q:
                continue
            
            try:
                answer = answer_question(q)
                print("\n" + answer["answer"] + "\n")
                
                # Ask if user wants to continue
                while True:
                    follow_up = input("Would you like to ask another question? [yes/no]: ").strip().lower()
                    if follow_up in {"yes", "y"}:
                        break
                    elif follow_up in {"no", "n"}:
                        print("Goodbye! See you soon!")
                        sys.exit(0)
                    else:
                        print("Please enter 'yes' or 'no'.")
            except (LLMError, ChromaError, EmbeddingError) as exc:
                log.error(f"Failed to answer question: {exc}")
                print(f"\nSorry, I encountered an error: {exc}\n")
                continue
            except KeyboardInterrupt:
                print("\nGoodbye! See you soon!")
                sys.exit(0)
                
    except KeyboardInterrupt:
        print("\nGoodbye! See you soon!")
        sys.exit(0)
    except Exception as exc:
        log.exception("Unexpected error in CLI")
        print(f"\nUnexpected error: {exc}")
        sys.exit(1)
    finally:
        if driver:
            try:
                driver.close()
                log.info("Neo4j connection closed")
            except Exception:
                pass
