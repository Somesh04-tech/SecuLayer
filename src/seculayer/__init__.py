"""SecuLayer: a reusable, layered defense against prompt injection.

This package is the library. It must never import seculayer_demo, fastapi or openai
(tests/test_architecture.py enforces this). Its public API arrives in milestone M2.
"""

__all__: list[str] = []
