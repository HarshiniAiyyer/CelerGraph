"""loadneo.py

Bulk importer that ingests a `knowledge_graph.json` file into Neo4j.

The script creates a uniqueness constraint on node IDs, then inserts nodes and
edges in batches to avoid overloading the database. Refactored to use dependency
injection following SOLID principles.
"""

import json
from typing import List, Dict, Any

from config.settings import Neo4jConfig
from core.code_exceptions import Neo4jError
from core.interfaces import GraphDatabase
from config.logger import log


class Neo4jImporter:
    """Neo4j bulk importer following Single Responsibility Principle."""
    
    def __init__(self, graph_db: GraphDatabase) -> None:
        """Initialize with graph database service.
        
        Args:
            graph_db: Graph database service implementation.
        """
        self._graph_db = graph_db
        self._create_constraint_query = """
        CREATE CONSTRAINT IF NOT EXISTS
        FOR (n:Node) REQUIRE n.id IS UNIQUE;
        """
        self._node_insert_query = """
        UNWIND $batch AS row
        MERGE (n:Node {id: row.id})
        SET n.type = row.type,
            n += row.props;
        """
        self._edge_insert_query = """
        UNWIND $batch AS row
        MATCH (src:Node {id: row.src})
        MATCH (dst:Node {id: row.dst})
        CALL apoc.create.relationship(src, row.type, row.props, dst)
        YIELD rel
        RETURN count(rel);
        """
    
    def import_knowledge_graph(self, json_path: str = "graph_indexing/knowledge_graph.json") -> None:
        """Import the knowledge graph into Neo4j using batched Cypher queries.
        
        Args:
            json_path: Path to the JSON knowledge graph file.
        
        Raises:
            Neo4jError: If any Neo4j operation fails.
            FileNotFoundError: If the JSON file doesn't exist.
            json.JSONDecodeError: If the JSON file is malformed.
        """
        try:
            log.info(f"Loading JSON: {json_path}")
            kg = self._load_json(json_path)

            nodes = kg.get("nodes", [])
            edges = kg.get("edges", [])

            log.info(f"Nodes: {len(nodes)}, Edges: {len(edges)}")

            self._graph_db.connect()
            
            try:
                self._create_constraint()
                if nodes:
                    self._import_nodes(nodes)
                if edges:
                    self._import_edges(edges)
            finally:
                self._graph_db.close()

            log.info("Graph import complete!")
        except (FileNotFoundError, json.JSONDecodeError):
            log.exception("Failed to load knowledge graph JSON")
            raise
        except Neo4jError:
            raise
        except Exception as exc:
            log.exception("Unexpected error during graph import")
            raise Neo4jError(f"Import failed: {exc}") from exc
    
    def _load_json(self, path: str) -> dict:
        """Load JSON file.
        
        Args:
            path: File path.
            
        Returns:
            Parsed JSON dictionary.
        """
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _create_constraint(self) -> None:
        """Create uniqueness constraint on node IDs."""
        log.info("Creating uniqueness constraint...")
        try:
            # This would need to be implemented in the GraphDatabase interface
            # For now, we'll assume the service handles this
            self._graph_db.execute_query(self._create_constraint_query)
            log.info("Uniqueness constraint created")
        except Exception as exc:
            log.warning(f"Constraint creation failed (may already exist): {exc}")
    
    def _import_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """Import nodes in batches.
        
        Args:
            nodes: List of node dictionaries.
        """
        log.info("Inserting nodes in batches...")
        node_count = 0
        for i, chunk in enumerate(self._batch_chunks(nodes)):
            try:
                self._graph_db.execute_query(self._node_insert_query, batch=chunk)
                node_count += len(chunk)
                log.debug(f"Inserted node batch {i+1} ({len(chunk)} nodes)")
            except Exception as exc:
                log.exception(f"Failed to insert node batch {i+1}")
                raise Neo4jError(f"Node insertion failed: {exc}") from exc
        log.info(f"Inserted {node_count} nodes")
    
    def _import_edges(self, edges: List[Dict[str, Any]]) -> None:
        """Import edges in batches.
        
        Args:
            edges: List of edge dictionaries.
        """
        log.info("Inserting edges in batches...")
        edge_count = 0
        for i, chunk in enumerate(self._batch_chunks(edges)):
            try:
                self._graph_db.execute_query(self._edge_insert_query, batch=chunk)
                edge_count += len(chunk)
                log.debug(f"Inserted edge batch {i+1} ({len(chunk)} edges)")
            except Exception as exc:
                log.exception(f"Failed to insert edge batch {i+1}")
                raise Neo4jError(f"Edge insertion failed: {exc}") from exc
        log.info(f"Inserted {edge_count} edges")
    
    def _batch_chunks(self, data: List[Dict], size: int = 500):
        """Yield successive *size*-length chunks from *data*.

        Args:
            data: List of dictionaries representing nodes or edges.
            size: Maximum number of items per chunk. Defaults to 500.

        Yields:
            List[Dict]: A slice of the input list of length ``<= size``.
        """
        for i in range(0, len(data), size):
            yield data[i:i + size]


# Legacy function for backward compatibility
def importkg() -> None:
    """Legacy function for backward compatibility.
    
    DEPRECATED: Use Neo4jImporter with dependency injection instead.
    """
    from core.services import Neo4jGraphDatabase
    from config.myapikeys import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
    
    config = Neo4jConfig(
        uri=NEO4J_URI,
        username=NEO4J_USERNAME,
        password=NEO4J_PASSWORD,
        use_neo4j=True
    )
    
    graph_db = Neo4jGraphDatabase(config)
    importer = Neo4jImporter(graph_db)
    importer.import_knowledge_graph()


if __name__ == "__main__":
    try:
        importkg()
    except Neo4jError:
        log.error("Graph import failed due to Neo4j error")
        raise SystemExit(1)
    except Exception:
        log.exception("Unexpected error during import")
        raise SystemExit(1)
