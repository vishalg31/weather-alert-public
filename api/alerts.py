from __future__ import annotations

from flask import Flask, jsonify, request

from lib.weather_service import fetch_nationwide_alerts

app = Flask(__name__)


@app.get("/")
@app.get("/api/alerts")
def alerts():
    force_refresh = request.args.get("refresh", "").lower() == "true"
    try:
        payload = fetch_nationwide_alerts(force_refresh=force_refresh)
    except Exception as exc:
        return jsonify({"error": "Unable to fetch nationwide alerts.", "details": str(exc)}), 502
    return jsonify(payload)
