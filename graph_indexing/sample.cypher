// List all nodes
MATCH (n) RETURN n LIMIT 50;

// List all relationship types
CALL db.relationshipTypes();

// Find all functions
MATCH (n:Node {type: "function"}) RETURN n.id LIMIT 50;

// Find all CALLS edges
MATCH (a:Node)-[:CALLS]->(b:Node)
RETURN a.id, b.id LIMIT 20;

// Find all docstrings of classes
MATCH (c:Node {type: "class"})-[:HAS_DOCSTRING]->(d:Node)
RETURN c.id, d.props.text LIMIT 20;
