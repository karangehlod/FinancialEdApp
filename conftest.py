"""Top-level test conftest to ensure the `backend` package is on PYTHONPATH
This makes `import app` work when running pytest from the project root.
"""
import os
import sys

ROOT = os.path.dirname(__file__)
BACKEND = os.path.join(ROOT, "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)
