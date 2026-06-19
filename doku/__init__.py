"""DOKU — local RAG over Albanian institutional documents.

Adds the repo root to sys.path so `import config` works regardless of the
process working directory (Streamlit, pytest, scripts).
"""
import os
import sys

__version__ = "0.1.0"

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
