"""Printing: paper formats, the documents the modules register
(<app>/documents.py) and their PDF on a chosen paper. See the documentation
site (django-resaas/features/printing)."""
from .formats import PAPER_CHOICES, PAPER_FORMATS, paper  # noqa: F401
from .registry import available, documents, get, register, unregister  # noqa: F401
