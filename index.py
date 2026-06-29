# index.py — Vercel Python entrypoint (ASGI).
#
# Vercel's Python runtime serves the module-level ``app`` (ASGI application) defined
# here as a single Serverless Function. This file is *infrastructure only*: it adds
# the backend package root to ``sys.path`` so the existing absolute imports
# (``from api.app import app`` -> ``from forward_ledger import ...``) resolve exactly
# as they do locally, then re-exports the unmodified FastAPI app.
#
# No backend behaviour is changed. The app still serves the /v1/* and /twin/* API and
# mounts the static landing pages from nexus-landing/standalone at "/", identical to
# `uvicorn api.app:app` run from the backend/ directory.
import os
import sys

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from api.app import app  # noqa: E402  (path must be set before this import)

# Vercel looks for a module-level ASGI/WSGI variable named ``app``.
__all__ = ["app"]
