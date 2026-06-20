"""Format-specific backends.

Modules in this package are the ONLY place allowed to import document
libraries (python-docx, fitz/PyMuPDF, openpyxl, python-pptx). The
public ``core.parse`` / ``core.edit`` dispatchers route to these.
"""
