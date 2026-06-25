"""
wsgi.py - WSGI wrapper for ASGI FastAPI app (used for PythonAnywhere and similar WSGI hosts)
"""
from a2wsgi import ASGIMiddleware
from main import app

wsgi_app = ASGIMiddleware(app)
