# kgbuild/python_extractor.py
import hashlib
import logging
from pathlib import Path
from typing import List
import libcst as cst

from graph_indexing.kgbuild.graph import KG, Resolver
from graph_indexing.kgbuild.treesitter_extractor import compute_module

logger = logging.getLogger(__name__)


class PyExtract(cst.CSTVisitor):
    """
    Python extractor using LibCST.
    Builds:
      - module, class, function nodes
      - docstring and comment nodes
      - CONTAINS, CALLS, IMPORTS, INHERITS, HAS_DOC, HAS_COMMENT edges
    """

    def __init__(self, path: str, root: str, kg: KG, resolver: Resolver):
        self.path = str(Path(path).relative_to(root))
        self.root = root
        self.module = compute_module(path, root)
        self.kg = kg
        self.resolver = resolver

        self.stack: List[str] = []   # class/function nesting
        self.current_fn = None       # fully-qualified name of current function

    # -----------------------------
    # Helper utilities
    # -----------------------------
    def fq(self, name: str) -> str:
        """Build fully qualified name from current nesting."""
        parts = [self.module] + self.stack + [name]
        return ".".join(parts)

    def add_doc(self, node, parent_id: str):
        ds = node.get_docstring()
        if not ds:
            return
        did = f"{parent_id}::doc"
        self.kg.add_node(did, "docstring", text=ds)
        self.kg.add_edge(parent_id, did, "HAS_DOC")

    def add_comments(self, node, parent_id: str):
        comments = []

        # leading comments
        if hasattr(node, "leading_lines"):
            for line in node.leading_lines:
                if line.comment:
                    comments.append(line.comment.value.strip())

        # trailing comment
        if hasattr(node, "trailing_whitespace"):
            tw = node.trailing_whitespace
            if getattr(tw, "comment", None):
                comments.append(tw.comment.value.strip())

        for c in comments:
            cid = f"{parent_id}::c::{hashlib.md5(c.encode()).hexdigest()[:6]}"
            self.kg.add_node(cid, "comment", text=c)
            self.kg.add_edge(parent_id, cid, "HAS_COMMENT")

    # -----------------------------
    # Module
    # -----------------------------
    def visit_Module(self, node: cst.Module):
        self.kg.add_node(self.module, "module", file=self.path)
        self.add_doc(node, self.module)

    # -----------------------------
    # Classes
    # -----------------------------
    def visit_ClassDef(self, node: cst.ClassDef):
        cname = node.name.value
        cid = self.fq(cname)
        parent = self.module if not self.stack else self.fq(self.stack[-1])

        self.kg.add_node(cid, "class", file=self.path, name=cname)
        self.kg.add_edge(parent, cid, "CONTAINS")

        self.add_doc(node, cid)
        self.add_comments(node, cid)

        # INHERITS edges
        for base in node.bases:
            if isinstance(base.value, cst.Name):
                base_name = base.value.value
                resolved = self.resolver.resolve(self.module, base_name)
                self.kg.add_edge(cid, resolved, "INHERITS")

        self.stack.append(cname)

    def leave_ClassDef(self, node: cst.ClassDef):
        self.stack.pop()

    # -----------------------------
    # Functions / Methods
    # -----------------------------
    def visit_FunctionDef(self, node: cst.FunctionDef):
        fname = node.name.value
        fid = self.fq(fname)
        parent = self.module if not self.stack else self.fq(self.stack[-1])

        self.kg.add_node(fid, "function", file=self.path, name=fname)
        self.kg.add_edge(parent, fid, "CONTAINS")

        self.add_doc(node, fid)
        self.add_comments(node, fid)

        self.stack.append(fname)
        self.current_fn = fid

    def leave_FunctionDef(self, node: cst.FunctionDef):
        self.stack.pop()
        self.current_fn = None

    # -----------------------------
    # Calls
    # -----------------------------
    def visit_Call(self, node: cst.Call):
        if not self.current_fn:
            return

        # direct function call: f(...)
        if isinstance(node.func, cst.Name):
            target = self.resolver.resolve(self.module, node.func.value)
            self.kg.add_edge(self.current_fn, target, "CALLS")

        # method/attribute call: obj.method(...)
        elif isinstance(node.func, cst.Attribute):
            method = node.func.attr.value
            if isinstance(node.func.value, cst.Name):
                obj = node.func.value.value
                resolved_obj = self.resolver.resolve(self.module, obj)
                target = f"{resolved_obj}.{method}"
            else:
                target = f"?.{method}"
            self.kg.add_edge(self.current_fn, target, "CALLS")

    # -----------------------------
    # Imports
    # -----------------------------
    def visit_Import(self, node: cst.Import):
        for alias in node.names:
            name = alias.name.value
            asname = alias.asname.name.value if alias.asname else name
            self.resolver.add_import(self.module, asname, name)
            # Edge at module level to imported module/symbol
            self.kg.add_edge(self.module, name, "IMPORTS")

    def visit_ImportFrom(self, node: cst.ImportFrom):
        if not node.module:
            return

        base = node.module.value
        for alias in node.names:
            if isinstance(alias.name, cst.Name):
                name = alias.name.value
            else:
                name = str(alias.name)
            asname = alias.asname.name.value if alias.asname else name

            resolved = f"{base}.{name}"
            self.resolver.add_import(self.module, asname, resolved)
            self.kg.add_edge(self.module, resolved, "IMPORTS")


