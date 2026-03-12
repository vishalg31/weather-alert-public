from __future__ import annotations

from flask import Flask

app = Flask(__name__)


@app.get("/")
@app.get("/api/health")
def health():
    return {"ok": True}, 200
