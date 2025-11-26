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
    rel = Path(path).relative_to(root)
    mod = str(rel.with_suffix(""))
    mod = mod.replace("\\", ".").replace("/", ".")
    if mod.endswith(".__init__"):
        mod = mod[:-9]
    return mod


def extract_ts(path: str, root: str, kg: KG):
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
        t = node.type

        if t in ("function_definition", "class_definition"):
            name = None
            for child in node.children:
                if child.type == "identifier":
                    name = source_bytes[child.start_byte:child.end_byte].decode()
                    break
            if name:
                nid = f"{module}.{name}"
                kg.add_node(nid, f"ts_{t}", file=str(Path(path).relative_to(root)))

        for child in node.children:
            walk(child)

    walk(root_node)

