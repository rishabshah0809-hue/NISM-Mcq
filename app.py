"""Minimal WSGI app so hosts like Render can serve the static site with `gunicorn app:app`."""
from pathlib import Path

ROOT = Path(__file__).parent
FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/questions.js": ("questions.js", "application/javascript; charset=utf-8"),
}


def app(environ, start_response):
    entry = FILES.get(environ.get("PATH_INFO", "/"))
    if entry is None:
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"Not found"]
    body = (ROOT / entry[0]).read_bytes()
    start_response("200 OK", [("Content-Type", entry[1]), ("Content-Length", str(len(body)))])
    return [body]
