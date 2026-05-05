"""
Vercel serverless entry point.

Vercel's Python runtime expects to find a WSGI application here.
We just import the existing Flask app from `backend/app.py` and re-export it.

Local development is unaffected — `python backend/app.py` still works.
"""
import os
import sys

# Add backend/ to sys.path so `from services...` and `from utils...` resolve
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

# Import the Flask `app` object — Vercel will treat it as the WSGI handler
from app import app  # noqa: E402, F401
