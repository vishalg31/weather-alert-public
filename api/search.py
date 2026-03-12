from __future__ import annotations

from flask import Flask, jsonify, request

from lib.weather_service import search_city_state

app = Flask(__name__)


@app.get("/")
@app.get("/api/search")
def search():
    city = request.args.get("city", "")
    state = request.args.get("state", "")
    if not city or not state:
        return jsonify({"error": "Both city and state are required."}), 400

    try:
        payload = search_city_state(city, state)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "Unable to search for that city/state.", "details": str(exc)}), 502
    return jsonify(payload)
