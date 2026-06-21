"""autodoc: AI document Q&A automation.

Reads questions from a document and writes answers back in-place,
preserving the original formatting. CLI is the single source of truth;
the HTTP API and web UI are thin layers that call the same core.
"""

__version__ = "0.2.0"
