#!/usr/bin/env python3
"""
Flask API server for the geometry diagram generator website.
Handles diagram generation requests from the GitHub Pages frontend.

Deployed on Render.com as a Web Service.
"""

import base64
import json
import logging
import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional, Tuple

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

# Recent generations store (in-memory, resets on restart)
recent_lock = threading.Lock()
recent_generations = []  # type: list
MAX_RECENT = 20
MAX_HTML_SIZE = 50000  # 50KB cap per entry


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


def _store_recent_generation(question, dimension, html):
    """Store a successful generation in the recent list (thread-safe)."""
    entry = {
        "question": question[:150],
        "dimension": dimension,
        "timestamp": time.strftime("%H:%M"),
        "html": html[:MAX_HTML_SIZE],
    }
    with recent_lock:
        recent_generations.append(entry)
        # Keep only the most recent MAX_RECENT entries
        while len(recent_generations) > MAX_RECENT:
            recent_generations.pop(0)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/recent", methods=["GET"])
def get_recent():
    """Return metadata for recent generations (no full HTML)."""
    with recent_lock:
        items = []
        for i, entry in enumerate(recent_generations):
            items.append({
                "index": i,
                "question": entry["question"],
                "dimension": entry["dimension"],
                "timestamp": entry["timestamp"],
            })
    # Return newest first
    items.reverse()
    return jsonify(items)


@app.route("/api/recent/<int:index>", methods=["GET"])
def get_recent_html(index):
    """Return the full HTML for a specific recent generation."""
    with recent_lock:
        if index < 0 or index >= len(recent_generations):
            return jsonify({"error": "Not found"}), 404
        return jsonify({"html": recent_generations[index]["html"]})


SERVER_TIMEOUT = 180  # seconds per attempt (including retry)


def _run_with_timeout(func, timeout=180, **kwargs):
    """Run a function in a thread with a timeout.
    Returns the function's result or a timeout error dict.
    """
    result = [None]
    error = [None]

    def target():
        try:
            result[0] = func(**kwargs)
        except Exception as e:
            error[0] = str(e)

    t = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join(timeout)

    if t.is_alive():
        logger.error("Server-side timeout after %ds", timeout)
        return {
            "success": False,
            "html": "",
            "dimension": kwargs.get("dimension_type", "2d").replace("coordinate_", ""),
            "duration": timeout,
            "error": "Generation timed out after {} seconds. Try using the Fast preset or a simpler question.".format(timeout),
        }

    if error[0]:
        return {
            "success": False,
            "html": "",
            "dimension": kwargs.get("dimension_type", "2d").replace("coordinate_", ""),
            "duration": 0,
            "error": error[0],
        }

    return result[0]


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
        result = _run_with_timeout(
            generate_diagram_openrouter,
            timeout=180,
            question_text=question,
            dimension_type=dimension,
            openrouter_key=os.getenv("OPENROUTER_WEBSITE_API_KEY"),
            preset=preset,
        )
        duration = time.time() - start

        if result["success"]:
            logger.info("Success in %.1fs", duration)
            dim = result.get("dimension", "2d")
            _store_recent_generation(question, dim, result["html"])
            return jsonify({
                "success": True,
                "html": result["html"],
                "dimension": dim,
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


ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def _extract_text_from_image(image_bytes, image_format, context_text=""):
    # type: (bytes, str, str) -> Tuple[bool, str]
    """Use OpenRouter Gemini Flash vision to OCR a geometry question image.
    If context_text is provided, it's included as additional question text.
    Returns (success, extracted_text_or_error).
    """
    from openai import OpenAI

    api_key = os.getenv("OPENROUTER_WEBSITE_API_KEY")
    if not api_key:
        return False, "Server misconfigured: missing API key"

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime = "image/jpeg" if image_format in ("jpg", "jpeg") else "image/{}".format(image_format)
    data_url = "data:{};base64,{}".format(mime, b64)

    if context_text:
        prompt = (
            "This image shows a geometry diagram. The accompanying question text is:\n\n"
            "{}\n\n"
            "Extract the full geometry question by combining the text above with any "
            "additional information visible in the image (labels, measurements, angles). "
            "Return ONLY the complete question text."
        ).format(context_text)
    else:
        prompt = "Extract the geometry question from this image. Return ONLY the question text, nothing else."

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    try:
        response = client.chat.completions.create(
            model="google/gemini-3-flash-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            max_tokens=1024,
            temperature=0.0,
        )
        text = response.choices[0].message.content.strip()
        if not text:
            return False, "Could not extract any text from the image"
        return True, text
    except Exception as e:
        logger.error("Vision OCR failed: %s", str(e))
        return False, "Failed to extract text from image: {}".format(str(e))


@app.route("/api/generate-from-image", methods=["POST"])
def generate_from_image():
    if not check_rate_limit():
        return jsonify({
            "success": False,
            "error": "Rate limit exceeded. Max {} requests per minute.".format(RATE_LIMIT),
        }), 429

    # Validate file upload
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file provided"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"success": False, "error": "No image file selected"}), 400

    # Check file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_TYPES:
        return jsonify({
            "success": False,
            "error": "Unsupported image format. Use PNG, JPG, JPEG, or WEBP.",
        }), 400

    # Read and check size
    image_bytes = file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE:
        return jsonify({
            "success": False,
            "error": "Image too large. Maximum size is 5 MB.",
        }), 400

    if len(image_bytes) == 0:
        return jsonify({"success": False, "error": "Image file is empty"}), 400

    preset = request.form.get("preset", "balanced")
    if preset not in ("fast", "balanced", "best"):
        preset = "balanced"
    dimension = request.form.get("dimension", "auto")
    context_text = request.form.get("context", "").strip()

    logger.info("Generating diagram from image [%s], size=%d bytes, context=%d chars",
                preset, len(image_bytes), len(context_text))

    try:
        # Step 1: Extract text from image via vision (with optional context)
        ocr_success, extracted_text = _extract_text_from_image(image_bytes, ext, context_text)
        if not ocr_success:
            return jsonify({"success": False, "error": extracted_text}), 500

        logger.info("Extracted text: %s", extracted_text[:100])

        # Step 2: Generate diagram from extracted text (skip keyword validation)
        from generate_js_pipeline import generate_diagram_openrouter

        start = time.time()
        result = _run_with_timeout(
            generate_diagram_openrouter,
            timeout=SERVER_TIMEOUT,
            question_text=extracted_text,
            dimension_type=dimension,
            openrouter_key=os.getenv("OPENROUTER_WEBSITE_API_KEY"),
            preset=preset,
        )
        duration = time.time() - start

        if result["success"]:
            logger.info("Success in %.1fs (from image)", duration)
            dim = result.get("dimension", "2d")
            _store_recent_generation(extracted_text, dim, result["html"])
            return jsonify({
                "success": True,
                "html": result["html"],
                "dimension": dim,
                "duration": round(duration, 1),
                "extracted_text": extracted_text,
            })
        else:
            logger.error("Failed (from image): %s", result.get("error", "unknown"))
            return jsonify({
                "success": False,
                "error": result.get("error", "Generation failed"),
                "extracted_text": extracted_text,
            }), 500

    except Exception as e:
        logger.error("Exception (image): %s", str(e))
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5052))
    app.run(host="0.0.0.0", port=port, debug=False)
