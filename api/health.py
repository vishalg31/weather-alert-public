from __future__ import annotations

from flask import Flask

app = Flask(__name__)


@app.get("/")
def health():
    return {"ok": True}, 200
