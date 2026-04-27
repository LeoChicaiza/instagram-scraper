"""
app.py — API Flask que expone el scraper vía HTTP
Solo usa: flask, flask-cors, y scraper.py (que solo usa requests)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json, os
from scraper import scrape

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    body     = request.get_json() or {}
    username = body.get("username", "").strip().lstrip("@")
    max_posts = min(int(body.get("max_posts", 10)), 50)

    # Cookies opcionales que el usuario puede pegar desde su navegador
    cookies  = body.get("cookies", None)   # dict: {"sessionid": "...", "csrftoken": "..."}

    if not username:
        return jsonify({"success": False, "error": "Username requerido"}), 400

    result = scrape(username, max_posts, cookies)
    return jsonify(result)


@app.route("/api/profiles", methods=["GET"])
def list_profiles():
    profiles = []
    for fname in os.listdir(DATA_DIR):
        if fname.endswith("_profile.json"):
            with open(os.path.join(DATA_DIR, fname), encoding="utf-8") as f:
                try:
                    d = json.load(f)
                    profiles.append({
                        "username":       d.get("username"),
                        "full_name":      d.get("full_name"),
                        "followers":      d.get("followers"),
                        "posts_count":    d.get("posts_count"),
                        "posts_scraped":  d.get("posts_retrieved"),
                        "scraped_at":     d.get("scraped_at"),
                    })
                except Exception:
                    pass
    return jsonify(profiles)


@app.route("/api/profile/<username>", methods=["GET"])
def get_profile(username):
    path = os.path.join(DATA_DIR, f"{username}_profile.json")
    if not os.path.exists(path):
        return jsonify({"error": "No encontrado. Scrapea el perfil primero."}), 404
    with open(path, encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("🚀 API corriendo en http://localhost:5000")
    app.run(debug=True, port=5000)
