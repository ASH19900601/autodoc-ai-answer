"""Core business logic.

This is the ONLY layer allowed to contain business logic. The CLI, the
HTTP API and the web UI must all call into this package and must not
import document libraries (python-docx, fitz, openpyxl, ...) directly.
This rule is what makes "CLI == GUI" automatically verifiable.
"""
