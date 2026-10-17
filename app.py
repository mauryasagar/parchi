"""Parchi web app.

Run:  python app.py
Then open http://127.0.0.1:5000 in your browser.
"""
import urllib.error

from flask import Flask, jsonify, request, send_from_directory

import core

app = Flask(__name__, static_folder="static", static_url_path="/static")


@app.get("/")
def home():
    return send_from_directory("static", "index.html")


@app.get("/api/models")
def api_models():
    return jsonify(models=core.list_models(), default=core.DEFAULT_MODEL)


@app.get("/api/prices")
def api_prices():
    return jsonify(prices=core.price_rows(core.load_prices()))


@app.get("/api/sample")
def api_sample():
    try:
        with open(core.ORDERS_FILE, encoding="utf-8-sig") as f:
            return jsonify(text=f.read())
    except OSError:
        return jsonify(text="")


@app.post("/api/parse")
def api_parse():
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    model = data.get("model") or core.DEFAULT_MODEL
    if not msg:
        return jsonify(error="empty_message", message="The message is empty."), 400
    prices = core.load_prices()
    try:
        parsed, cached = core.parse_cached(model, msg)
        slip = core.build_slip(msg, parsed, prices)
        slip["cached"] = cached
    except urllib.error.HTTPError as e:
        return jsonify(
            error="model_error",
            message=f"Ollama returned an error ({e.code}). Check that {model} is installed.",
        ), 502
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return jsonify(error="model_unreachable", message="Could not reach Ollama."), 503
    except (ValueError, KeyError, TypeError):
        slip = core.build_slip(msg, {}, prices, error="the model's answer could not be read")
        slip["cached"] = False
    return jsonify(slip)


@app.post("/api/prep")
def api_prep():
    data = request.get_json(silent=True) or {}
    return jsonify(core.make_prep(data.get("slips") or []))


if __name__ == "__main__":
    print("Parchi is running. Open http://127.0.0.1:5000 in your browser. Press Ctrl+C to stop.")
    app.run(host="127.0.0.1", port=5000)
