# kgbuild/treesitter_extractor.py

import logging
from pathlib import Path

from tree_sitter_languages import get_parser

from graph_indexing.kgbuild.graph import KG

logger = logging.getLogger(__name__)


def compute_module(path: str, root: str) -> str:
    """
    Compute a Python module-like name from a file path,
    handling Windows and __init__.py correctly.
    """
    relative_path = Path(path).relative_to(root)
    module_name = str(relative_path.with_suffix(""))
    module_name = module_name.replace("\\", ".").replace("/", ".")
    if module_name.endswith(".__init__"):
        module_name = module_name[:-9]
    return module_name


def extract_ts(path: str, root: str, knowledge_graph: KG):
    """
    Extract function and class definitions using Tree-sitter (Python).
    This is optional and currently only adds structural nodes.
    """
    try:
        parser = get_parser("python")
    except Exception as e:
        logger.error(f"Tree-sitter could not load Python grammar: {e}")
        return

    try:
        source_bytes = Path(path).read_bytes()
        tree = parser.parse(source_bytes)
        root_node = tree.root_node
    except Exception as e:
        logger.error(f"Tree-sitter failed to parse {path}: {e}")
        return

    module = compute_module(path, root)

    def walk(node):
        node_type = node.type

        if node_type in ("function_definition", "class_definition"):
            name = None
            for child in node.children:
                if child.type == "identifier":
                    name = source_bytes[child.start_byte:child.end_byte].decode()
                    break
            if name:
                node_id = f"{module}.{name}"
                knowledge_graph.add_node(node_id, f"ts_{node_type}", file=str(Path(path).relative_to(root)))

        for child in node.children:
            walk(child)

    walk(root_node)

