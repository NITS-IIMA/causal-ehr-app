"""Ensures the repository root is on sys.path so `import pipeline` and
`from src...` resolve under a plain `pytest` invocation (e.g. in CI), without
requiring an editable install. pytest auto-adds the directory containing this
root-level conftest.py to sys.path.
"""
