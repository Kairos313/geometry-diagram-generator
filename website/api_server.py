#!/usr/bin/env python3
"""
Flask API server for the geometry diagram generator website.
Handles diagram generation requests from the GitHub Pages frontend.

Deployed on Render.com as a Web Service.
"""

import json
import logging
import os
import sys
import time
import threading
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

# Add parent dir so we can import frontend modules
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "frontend"))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

# Also check for env vars set directly (Render sets them in the environment)
# No .env file needed on Render — env vars are set in the dashboard

# Suppress noisy loggers
for name in ["httpx", "httpcore", "openai", "google", "google_genai"]:
    logging.getLogger(name).setLevel(logging.WARNING)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Rate limiting: 10 requests per minute
rate_lock = threading.Lock()
request_times = []
RATE_LIMIT = 10
RATE_WINDOW = 60  # seconds


def check_rate_limit():
    """Returns True if request is allowed, False if rate limited."""
    now = time.time()
    with rate_lock:
        # Remove old entries
        while request_times and request_times[0] < now - RATE_WINDOW:
            request_times.pop(0)
        if len(request_times) >= RATE_LIMIT:
            return False
        request_times.append(now)
        return True


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def _is_geometry_question(text):
    """Quick check if the input looks like a geometry question.
    Uses keyword matching first (free, instant), falls back to LLM only if ambiguous.
    """
    text_lower = text.lower()

    # Geometry keywords — if any match, it's likely geometry
    geo_keywords = [
        "triangle", "circle", "square", "rectangle", "polygon", "quadrilateral",
        "angle", "degree", "radius", "diameter", "chord", "tangent", "perpendicular",
        "parallel", "bisector", "midpoint", "altitude", "hypotenuse", "diagonal",
        "pyramid", "prism", "cube", "cuboid", "cylinder", "cone", "sphere",
        "tetrahedron", "octahedron", "hexagon", "pentagon",
        "area", "perimeter", "volume", "surface area", "circumference",
        "sin", "cos", "tan", "cosine", "sine", "pythagor",
        "coordinate", "equation", "slope", "intercept", "locus", "graph",
        "vertex", "vertices", "edge", "face", "plane", "vector",
        "inscribed", "circumscribed", "cyclic", "dihedral",
        "cm", "km", "metre", "meter", "length", "height", "width",
        "rhombus", "trapez", "parallelogram", "sector", "arc",
        "x^2", "y^2", "x²", "y²",
    ]

    matches = sum(1 for kw in geo_keywords if kw in text_lower)
    if matches >= 2:
        return True
    if matches == 0:
        return False

    # Ambiguous (1 keyword) — could be geometry or not. Allow it.
    return True


@app.route("/api/generate", methods=["POST"])
def generate():
    if not check_rate_limit():
        return jsonify({
            "success": False,
            "error": "Rate limit exceeded. Max {} requests per minute.".format(RATE_LIMIT),
        }), 429

    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"success": False, "error": "Missing 'question' field"}), 400

    question = data["question"].strip()
    if not question:
        return jsonify({"success": False, "error": "Question is empty"}), 400

    if len(question) > 1000:
        return jsonify({"success": False, "error": "Question too long (max 1000 chars)"}), 400

    # Input validation: check if this is a geometry question
    if not _is_geometry_question(question):
        return jsonify({
            "success": False,
            "error": "This doesn't appear to be a geometry question. Please enter a question about shapes, angles, coordinates, or measurements.",
        }), 400

    dimension = data.get("dimension", "auto")
    preset = data.get("preset", "balanced")
    if preset not in ("fast", "balanced", "best"):
        preset = "balanced"

    logger.info("Generating diagram [%s] for: %s", preset, question[:80])

    try:
        from generate_js_pipeline import generate_diagram_openrouter

        start = time.time()
        result = generate_diagram_openrouter(
            question_text=question,
            dimension_type=dimension,
            openrouter_key=os.getenv("OPENROUTER_WEBSITE_API_KEY"),
            preset=preset,
        )
        duration = time.time() - start

        if result["success"]:
            logger.info("Success in %.1fs", duration)
            return jsonify({
                "success": True,
                "html": result["html"],
                "dimension": result.get("dimension", "2d"),
                "duration": round(duration, 1),
            })
        else:
            logger.error("Failed: %s", result.get("error", "unknown"))
            return jsonify({
                "success": False,
                "error": result.get("error", "Generation failed"),
            }), 500

    except Exception as e:
        logger.error("Exception: %s", str(e))
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5052))
    app.run(host="0.0.0.0", port=port, debug=False)
