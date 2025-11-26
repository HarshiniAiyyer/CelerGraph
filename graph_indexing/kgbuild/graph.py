# kgbuild/graph.py

from typing import Dict, List, Any
from pathlib import Path


class KG:
    """
    Knowledge Graph container.
    Includes a fully recursive JSON-safe sanitizer.
    """

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []

    # ------------------------------------------------------
    # Recursive sanitizer for ANY Python object
    # ------------------------------------------------------
    def _sanitize(self, value):
        """Recursively convert any value into a JSON-serializable form."""
        # basic primitives
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        # lists, tuples, sets
        if isinstance(value, (list, tuple, set)):
            return [self._sanitize(v) for v in value]

        # dicts
        if isinstance(value, dict):
            return {k: self._sanitize(v) for k, v in value.items()}

        # everything else, including LibCST nodes → string
        return str(value)

    def _sanitize_props(self, props: Dict[str, Any]) -> Dict[str, Any]:
        return {k: self._sanitize(v) for k, v in props.items()}

    # ------------------------------------------------------
    # Node + Edge creation
    # ------------------------------------------------------
    def add_node(self, nid: str, ntype: str, **props):
        props = self._sanitize_props(props)

        if nid not in self.nodes:
            self.nodes[nid] = {"id": nid, "type": ntype, "props": {}}

        self.nodes[nid]["props"].update(props)

    def add_edge(self, src: str, dst: str, etype: str):
        # edges have no props — avoids any JSON issues
        self.edges.append({
            "src": src,
            "dst": dst,
            "type": etype
        })

    # ------------------------------------------------------
    # Export
    # ------------------------------------------------------
    def to_dict(self, root_path: str = None):
        """
        Return a fully JSON-safe dict.
        We sanitize the whole structure again, in case anything
        sneaked in without going through add_node/add_edge.
        
        If root_path is provided, convert absolute file paths to relative paths.
        """
        raw = {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
        }
        
        sanitized = self._sanitize(raw)
        
        # Convert absolute paths to relative if root_path is provided
        if root_path:
            root_path = str(Path(root_path).resolve())
            for node in sanitized["nodes"]:
                if "props" in node and "file" in node["props"]:
                    file_path = node["props"]["file"]
                    if Path(file_path).is_absolute() and file_path.startswith(root_path):
                        node["props"]["file"] = str(Path(file_path).relative_to(root_path))
        
        return sanitized

    @staticmethod
    def convert_absolute_to_relative(json_file_path: str, root_path: str, output_file_path: str = None):
        """
        Convert an existing knowledge graph JSON file with absolute paths to use relative paths.
        """
        import json
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            kg_data = json.load(f)
        
        root_path = str(Path(root_path).resolve())
        
        # Convert file paths in nodes
        for node in kg_data.get("nodes", []):
            if "props" in node and "file" in node["props"]:
                file_path = node["props"]["file"]
                if Path(file_path).is_absolute() and file_path.startswith(root_path):
                    node["props"]["file"] = str(Path(file_path).relative_to(root_path))
        
        # Save to output file or overwrite original
        output_path = output_file_path or json_file_path
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(kg_data, f, indent=2)
        
        return output_path


class Resolver:
    """
    Tracks imports and resolves them across modules.
    """

    def __init__(self):
        self.imports: Dict[str, Dict[str, str]] = {}

    def add_import(self, module: str, symbol: str, fqn: str):
        self.imports.setdefault(module, {})[symbol] = fqn

    def resolve(self, module: str, symbol: str) -> str:
        # imported?
        if module in self.imports and symbol in self.imports[module]:
            return self.imports[module][symbol]

        # fallback: assume same module
        return f"{module}.{symbol}"


def make_paths_relative(json_file_path: str, root_path: str, output_file_path: str = None):
    """
    Convenience function to convert absolute paths to relative paths in a knowledge graph JSON file.
    
    Args:
        json_file_path: Path to the JSON file with absolute paths
        root_path: Root directory to make paths relative to
        output_file_path: Optional output file path (defaults to overwriting input)
    
    Returns:
        Path to the output file
    """
    return KG.convert_absolute_to_relative(json_file_path, root_path, output_file_path)



