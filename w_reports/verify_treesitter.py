import sys
import os
import tree_sitter
print(f"Tree-sitter version: {tree_sitter.__version__ if hasattr(tree_sitter, '__version__') else 'unknown'}")

try:
    import core.chunker
    print(f"Imported core.chunker from: {core.chunker.__file__}")
    from core.chunker import parser
    
    if parser:
        print("Tree-sitter initialized successfully!")
    else:
        print("Tree-sitter failed to initialize (parser is None).")
except Exception as e:
    print(f"Error during import: {e}")
    import traceback
    traceback.print_exc()

