"""Make the repository root importable for a plain `pytest` invocation (including
CI), regardless of pytest's import mode or whether the package is pip-installed.

pytest loads this root-level conftest before collecting tests, so inserting the
repo root here guarantees `import pipeline` and `from src...` resolve.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
