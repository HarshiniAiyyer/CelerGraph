# kgbuild/runner.py

import json
import logging
from pathlib import Path
import libcst as cst
import argparse

from graph_indexing.kgbuild.graph import KG, Resolver
from graph_indexing.kgbuild.treesitter_extractor import extract_ts
from graph_indexing.kgbuild.python_extractor import PyExtract

# Switch this to True if you want Tree-sitter nodes too
USE_TREESITTER = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_project(root: str) -> KG:
    """Extract a knowledge graph from all Python files under root."""
    root_path = Path(root).resolve()
    root = str(root_path)

    kg = KG()
    resolver = Resolver()

    pyfiles = [
        f for f in root_path.rglob("*.py")
        if "__pycache__" not in f.parts
    ]

    logger.info(f"Found {len(pyfiles)} Python files in {root}")

    for file in pyfiles:
        logger.info(f"Processing {file}")

        if USE_TREESITTER:
            extract_ts(str(file), root, kg)

        # LibCST extraction
        try:
            src = file.read_text(encoding="utf-8")
            tree = cst.parse_module(src)
            tree.visit(PyExtract(str(file), root, kg, resolver))
        except Exception as e:
            logger.error(f"LibCST processing failed for {file}: {e}")

    return kg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract knowledge graph from Python code")
    parser.add_argument("root", nargs="?", default=".", help="Root directory to extract from")
    parser.add_argument("--convert-absolute", help="Convert existing JSON file with absolute paths to relative paths")
    parser.add_argument("--output", default="knowledge_graph.json", help="Output file name")
    
    args = parser.parse_args()
    
    if args.convert_absolute:
        # Convert existing file
        logger.info(f"Converting {args.convert_absolute} to use relative paths")
        output_path = KG.convert_absolute_to_relative(args.convert_absolute, args.root, args.output)
        logger.info(f"Converted file saved to {output_path}")
        print(f"Converted {args.convert_absolute} -> {output_path}")
    else:
        # Extract new knowledge graph
        target_root = args.root
        logger.info(f"Starting extraction for project at: {target_root}")

        kg = extract_project(target_root)

        out_file = args.output
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(kg.to_dict(root_path=target_root), f, indent=2)

        logger.info(f"Knowledge graph saved to {out_file}")
        print(f"Saved {out_file}")


