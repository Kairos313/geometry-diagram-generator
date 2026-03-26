#!/usr/bin/env python3
"""
JS Pipeline - 3-Stage Batch Test with Real-Time Web UI.

Pipeline: Classify -> Math (Gemini) -> JS Code (DeepSeek) | Interactive HTML Output

Runs all questions through the 3-stage JS pipeline in parallel and shows
real-time progress, timing, cost, and token counts in a dark-themed web UI.

Usage:
    python3 batch_test_js_ui.py                              # Run all questions
    python3 batch_test_js_ui.py --test-set hkdse             # HKDSE questions only
    python3 batch_test_js_ui.py --test-set coord             # Coordinate questions only
    python3 batch_test_js_ui.py --test-set hkdse_new         # New HKDSE questions only
    python3 batch_test_js_ui.py --dim 2d                     # 2D only
    python3 batch_test_js_ui.py --dim 3d                     # 3D only
    python3 batch_test_js_ui.py --workers 10                 # Limit concurrency
    python3 batch_test_js_ui.py --port 5052                  # Custom port
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, send_from_directory

# ======================================================================
# Suppress noisy loggers
# ======================================================================
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("generate_js_pipeline").setLevel(logging.WARNING)
logging.getLogger("generate_code_js").setLevel(logging.WARNING)
logging.getLogger("classify_geometry_type").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Ensure pipeline modules are importable
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

load_dotenv(ROOT_DIR / ".env")

# ======================================================================
# Test Questions - Import from separate modules
# ======================================================================

from hkdse_test_questions import HKDSE_QUESTIONS_2D, HKDSE_QUESTIONS_3D
from coordinate_test_questions import (
    COORDINATE_QUESTIONS_2D_ORIGINAL,
    COORDINATE_QUESTIONS_3D,
)
from hkdse_new_questions import HKDSE_NEW_QUESTIONS


def build_question_list(dim_filter="all", test_set_filter="all"):
    # type: (str, str) -> List[dict]
    """Build the question list with optional filtering."""
    questions = []

    if test_set_filter in ("hkdse", "all"):
        hkdse_2d = [dict(q, test_set="hkdse") for q in HKDSE_QUESTIONS_2D]
        hkdse_3d = [dict(q, test_set="hkdse") for q in HKDSE_QUESTIONS_3D]
        if dim_filter in ("2d", "all"):
            questions.extend(hkdse_2d)
        if dim_filter in ("3d", "all"):
            questions.extend(hkdse_3d)

    if test_set_filter in ("coord", "coordinate", "all"):
        coord_2d = [dict(q, test_set="coordinate") for q in COORDINATE_QUESTIONS_2D_ORIGINAL]
        coord_3d = [dict(q, test_set="coordinate") for q in COORDINATE_QUESTIONS_3D]
        if dim_filter in ("2d", "all"):
            questions.extend(coord_2d)
        if dim_filter in ("3d", "all"):
            questions.extend(coord_3d)

    if test_set_filter in ("hkdse_new", "all"):
        new_2d = [dict(q, test_set="hkdse_new") for q in HKDSE_NEW_QUESTIONS if q.get("dimension", "2d") == "2d"]
        new_3d = [dict(q, test_set="hkdse_new") for q in HKDSE_NEW_QUESTIONS if q.get("dimension", "2d") == "3d"]
        if dim_filter in ("2d", "all"):
            questions.extend(new_2d)
        if dim_filter in ("3d", "all"):
            questions.extend(new_3d)

    return questions


# Will be set by CLI args
ALL_QUESTIONS = []  # type: List[dict]
MAX_WORKERS = 50

# ======================================================================
# Pricing (per million tokens)
# ======================================================================

PRICING = {
    "math": {"input": 0.50, "output": 3.00},       # Gemini 3 Flash
    "codegen": {"input": 0.28, "output": 0.42},     # DeepSeek V3.2 Azure
}


# ======================================================================
# Dataclasses
# ======================================================================

@dataclass
class StageResult:
    success: bool = False
    duration: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    error: Optional[str] = None
    output: Optional[str] = None


@dataclass
class QuestionResult:
    question_id: str
    question_name: str
    question_text: str
    dimension: str = ""
    test_set: str = ""
    math: StageResult = field(default_factory=StageResult)
    codegen: StageResult = field(default_factory=StageResult)
    total_duration: float = 0.0
    total_cost: float = 0.0
    output_path: Optional[str] = None
    success: bool = False


# Global results storage
results = {}  # type: Dict[str, QuestionResult]
batch_status = {"running": False, "completed": 0, "total": 0, "start_time": 0}


# ======================================================================
# Pipeline Runner (Sync, runs in thread pool)
# ======================================================================

def run_single_question(question):
    # type: (dict) -> QuestionResult
    """Run the full 3-stage JS pipeline for a single question."""

    from generate_js_pipeline import generate_diagram

    result = QuestionResult(
        question_id=question["id"],
        question_name=question["name"],
        question_text=question["text"],
        dimension=question.get("dimension", "2d"),
        test_set=question.get("test_set", ""),
    )

    start_time = time.time()
    qid = question["id"]
    dim = question.get("dimension", "auto")
    output_dir = str(SCRIPT_DIR / "output" / "batch_js" / qid)
    output_path = str(Path(output_dir) / "diagram.html")

    try:
        pipeline_result = generate_diagram(
            question_text=question["text"],
            dimension_type=dim,
            output_path=output_path,
            max_retries=1,
        )
    except Exception as e:
        result.math.error = "Pipeline exception: {}".format(str(e))
        result.total_duration = time.time() - start_time
        return result

    # Extract token details from result["tokens"]
    tokens = pipeline_result.get("tokens", {})
    gemini_tokens = tokens.get("gemini_math", {})
    deepseek_tokens = tokens.get("deepseek_js", {})
    deepseek_retry_tokens = tokens.get("deepseek_js_retry", {})

    # --- Math stage ---
    math_prompt = gemini_tokens.get("prompt", 0)
    math_completion = gemini_tokens.get("completion", 0)
    math_total = gemini_tokens.get("total", 0)

    result.math.prompt_tokens = math_prompt
    result.math.completion_tokens = math_completion
    result.math.total_tokens = math_total
    result.math.cost = (
        (math_prompt / 1e6) * PRICING["math"]["input"] +
        (math_completion / 1e6) * PRICING["math"]["output"]
    )

    # Check if math succeeded based on whether we got notes
    if pipeline_result.get("math_notes"):
        result.math.success = True
        result.math.output = pipeline_result.get("math_notes", "")
    else:
        result.math.success = False
        result.math.error = pipeline_result.get("error", "No math notes produced")

    # Estimate math duration from total if not available separately
    # The pipeline doesn't return per-stage durations directly, so we approximate
    total_pipeline_dur = pipeline_result.get("duration", 0)

    # --- CodeGen stage ---
    cg_prompt = deepseek_tokens.get("prompt", 0) + deepseek_retry_tokens.get("prompt", 0)
    cg_completion = deepseek_tokens.get("completion", 0) + deepseek_retry_tokens.get("completion", 0)
    cg_total = deepseek_tokens.get("total", 0) + deepseek_retry_tokens.get("total", 0)

    result.codegen.prompt_tokens = cg_prompt
    result.codegen.completion_tokens = cg_completion
    result.codegen.total_tokens = cg_total
    result.codegen.cost = (
        (cg_prompt / 1e6) * PRICING["codegen"]["input"] +
        (cg_completion / 1e6) * PRICING["codegen"]["output"]
    )

    if pipeline_result.get("success"):
        result.codegen.success = True
        result.success = True
        result.output_path = "/output/batch_js/{}/diagram.html".format(qid)
    else:
        result.codegen.success = False
        if result.math.success:
            result.codegen.error = pipeline_result.get("error", "JS generation failed")
        # If math also failed, error was already set above

    result.dimension = pipeline_result.get("dimension", dim)
    result.total_duration = time.time() - start_time
    result.total_cost = result.math.cost + result.codegen.cost

    # Approximate stage durations (split proportionally by tokens)
    total_tokens = math_total + cg_total
    if total_tokens > 0 and total_pipeline_dur > 0:
        result.math.duration = round(total_pipeline_dur * (math_total / total_tokens), 1)
        result.codegen.duration = round(total_pipeline_dur * (cg_total / total_tokens), 1)
    else:
        result.math.duration = round(total_pipeline_dur * 0.4, 1)
        result.codegen.duration = round(total_pipeline_dur * 0.6, 1)

    return result


# ======================================================================
# Batch Runner (Async with Thread Pool)
# ======================================================================

async def run_batch_async(questions, max_workers=50):
    # type: (List[dict], int) -> None
    """Run all questions in parallel using a thread pool."""
    global results, batch_status

    batch_status["running"] = True
    batch_status["completed"] = 0
    batch_status["total"] = len(questions)
    batch_status["start_time"] = time.time()
    results.clear()

    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = []
        for q in questions:
            task = loop.run_in_executor(executor, run_single_question, q)
            tasks.append((q["id"], task))

        for q_id, task in tasks:
            try:
                result = await task
                results[q_id] = result
                batch_status["completed"] += 1
                status = "SUCCESS" if result.success else "FAILED"
                msg = "[{}/{}] {}: {} [{}] ({:.1f}s, ${:.4f})".format(
                    batch_status["completed"], batch_status["total"],
                    result.question_name, status,
                    result.dimension,
                    result.total_duration, result.total_cost,
                )
                if not result.success:
                    if result.math.error:
                        msg += "\n  -> Math error: {}".format(result.math.error[:120])
                    elif result.codegen.error:
                        msg += "\n  -> CodeGen error: {}".format(result.codegen.error[:120])
                print(msg)
            except Exception as e:
                print("Error processing {}: {}".format(q_id, e))
                batch_status["completed"] += 1

    batch_status["running"] = False
    total_time = time.time() - batch_status["start_time"]
    total_cost = sum(r.total_cost for r in results.values())
    success_count = sum(1 for r in results.values() if r.success)

    print("\n" + "=" * 60)
    print("BATCH COMPLETE: {}/{} successful".format(success_count, len(questions)))
    print("Total time: {:.1f}s".format(total_time))
    print("Total cost: ${:.4f}".format(total_cost))
    print("=" * 60 + "\n")


def start_batch_thread(max_workers=50):
    # type: (int) -> None
    """Start the batch processing in a background thread."""
    def run():
        asyncio.run(run_batch_async(ALL_QUESTIONS, max_workers=max_workers))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


# ======================================================================
# Flask App
# ======================================================================

app = Flask(__name__)


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/start", methods=["POST"])
def start_batch():
    if batch_status["running"]:
        return jsonify({"error": "Batch already running"}), 400
    start_batch_thread(max_workers=MAX_WORKERS)
    return jsonify({"status": "started", "total": len(ALL_QUESTIONS)})


@app.route("/status")
def get_status():
    total_cost = sum(r.total_cost for r in results.values())
    success_count = sum(1 for r in results.values() if r.success)
    elapsed = time.time() - batch_status["start_time"] if batch_status["start_time"] else 0

    results_list = []
    for q in ALL_QUESTIONS:
        if q["id"] in results:
            r = results[q["id"]]
            results_list.append({
                "id": r.question_id,
                "name": r.question_name,
                "text": r.question_text,
                "dimension": r.dimension,
                "test_set": r.test_set,
                "success": r.success,
                "total_duration": round(r.total_duration, 1),
                "total_cost": round(r.total_cost, 6),
                "output_path": r.output_path,
                "math": {
                    "success": r.math.success,
                    "duration": round(r.math.duration, 1),
                    "tokens": r.math.total_tokens,
                    "prompt_tokens": r.math.prompt_tokens,
                    "completion_tokens": r.math.completion_tokens,
                    "cost": round(r.math.cost, 6),
                    "error": r.math.error,
                },
                "codegen": {
                    "success": r.codegen.success,
                    "duration": round(r.codegen.duration, 1),
                    "tokens": r.codegen.total_tokens,
                    "prompt_tokens": r.codegen.prompt_tokens,
                    "completion_tokens": r.codegen.completion_tokens,
                    "cost": round(r.codegen.cost, 6),
                    "error": r.codegen.error,
                },
            })
        else:
            results_list.append({
                "id": q["id"],
                "name": q["name"],
                "text": q["text"],
                "dimension": q.get("dimension", ""),
                "test_set": q.get("test_set", ""),
                "pending": True,
            })

    return jsonify({
        "running": batch_status["running"],
        "completed": batch_status["completed"],
        "total": batch_status["total"],
        "elapsed": round(elapsed, 1),
        "total_cost": round(total_cost, 6),
        "success_count": success_count,
        "results": results_list,
        "pricing": PRICING,
    })


@app.route("/output/<path:filepath>")
def serve_output(filepath):
    return send_from_directory(str(SCRIPT_DIR / "output"), filepath)


# ======================================================================
# HTML Template
# ======================================================================

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JS Pipeline - 3-Stage Batch Test</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0C0C0C;color:#e0e0e0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,monospace;line-height:1.6}
.container{max-width:1400px;margin:0 auto;padding:1.5rem}
.header{text-align:center;margin-bottom:1.5rem;border-bottom:1px solid #2a2a2a;padding-bottom:1rem}
.header h1{color:#4ECDC4;font-size:1.6rem;margin-bottom:.25rem}
.subtitle{color:#888;font-size:.85rem}

.controls{display:flex;gap:1rem;align-items:center;justify-content:center;margin-bottom:1.5rem;flex-wrap:wrap}
#start-btn{background:#4ECDC4;color:#0C0C0C;border:none;padding:.6rem 2rem;border-radius:4px;font-size:1rem;font-weight:700;cursor:pointer}
#start-btn:disabled{background:#333;color:#666;cursor:not-allowed}
.stat{background:#1a1a1a;padding:.5rem 1rem;border-radius:4px;font-size:.9rem}
.stat-val{color:#4ECDC4;font-weight:700}

.filters{display:flex;gap:.5rem;align-items:center;justify-content:center;margin-bottom:1.5rem;flex-wrap:wrap}
.filter-btn{background:#1a1a1a;color:#888;border:1px solid #2a2a2a;padding:.35rem .75rem;border-radius:4px;font-size:.8rem;cursor:pointer;font-family:inherit}
.filter-btn:hover{border-color:#4ECDC4;color:#e0e0e0}
.filter-btn.active{background:#4ECDC4;color:#0C0C0C;border-color:#4ECDC4;font-weight:700}
.filter-sep{color:#333;margin:0 .25rem}

.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:1rem;margin-bottom:1.5rem}
.summary-card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:6px;padding:1rem;text-align:center}
.summary-card .value{font-size:1.6rem;color:#4ECDC4;font-weight:700}
.summary-card .label{color:#888;font-size:.75rem;text-transform:uppercase}
.summary-card .sub-value{color:#E9C46A;font-size:.9rem;font-weight:600;margin-top:.25rem}
.summary-card.highlight{border-color:#4ECDC4;background:#1a2a2a}

.model-breakdown{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem}
.model-panel{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:6px;padding:1rem}
.model-panel-title{font-size:.85rem;font-weight:700;color:#4ECDC4;margin-bottom:.75rem;display:flex;align-items:center;gap:.5rem}
.model-panel-title .model-tag{background:#2a2a2a;color:#aaa;font-size:.7rem;font-weight:400;padding:.15rem .5rem;border-radius:3px}
.token-row{display:flex;justify-content:space-between;align-items:center;padding:.35rem 0;font-size:.82rem}
.token-row:not(:last-child){border-bottom:1px solid #222}
.token-label{color:#888}
.token-val{color:#e0e0e0;font-weight:600}
.token-cost{color:#E9C46A;font-size:.78rem;margin-left:.5rem}
.model-total{margin-top:.5rem;padding-top:.5rem;border-top:1px solid #333;display:flex;justify-content:space-between;font-size:.85rem;font-weight:700}
.model-total .token-label{color:#aaa}
.model-total .token-val{color:#4ECDC4}

.results-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(500px,1fr));gap:1rem}
.result-card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;overflow:hidden}
.result-card.success{border-color:#96CEB4}
.result-card.failed{border-color:#FF6B6B}
.result-card.pending{border-color:#444;opacity:0.6}

.card-header{padding:.75rem 1rem;border-bottom:1px solid #2a2a2a;display:flex;justify-content:space-between;align-items:center}
.card-title{font-weight:600;font-size:.95rem}
.card-badges{display:flex;gap:.35rem;align-items:center}
.card-badge{padding:.15rem .5rem;border-radius:3px;font-size:.75rem;font-weight:700}
.badge-2d{background:#457B9D;color:#fff}
.badge-3d{background:#6A4C93;color:#fff}
.badge-pending{background:#333;color:#888}
.badge-success{background:#96CEB4;color:#0C0C0C}
.badge-failed{background:#FF6B6B;color:#fff}
.badge-hkdse{background:#264653;color:#ccc;font-weight:400;font-size:.65rem}
.badge-coordinate{background:#2a3a2a;color:#ccc;font-weight:400;font-size:.65rem}
.badge-hkdse_new{background:#3a2a3a;color:#ccc;font-weight:400;font-size:.65rem}

.card-body{padding:.75rem 1rem}
.question-text{font-size:.82rem;color:#aaa;margin-bottom:.75rem;line-height:1.5;white-space:pre-wrap;word-wrap:break-word}

.stages{display:flex;gap:.4rem;margin-bottom:.75rem}
.stage{flex:1;background:#0C0C0C;border-radius:4px;padding:.35rem;text-align:center;font-size:.7rem}
.stage.done{background:#1a3a2a;color:#96CEB4}
.stage.error{background:#3a1a1a;color:#FF6B6B}
.stage-name{font-weight:600}
.stage-info{color:#888;font-size:.65rem}

.card-stats{display:flex;gap:.75rem;font-size:.8rem;color:#888;flex-wrap:wrap}
.card-stats span{display:flex;align-items:center;gap:.3rem}
.card-stats .val{color:#e0e0e0;font-weight:600}

.card-diagram{padding:.5rem;background:#0C0C0C;text-align:center}
.card-diagram iframe{width:100%;border:none;border-radius:4px;background:#fff}

.spinner{display:inline-block;width:16px;height:16px;border:2px solid #333;border-top-color:#4ECDC4;border-radius:50%;animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

.hidden{display:none}
</style>
</head>
<body>
<div class="container">

<header class="header">
  <h1>JS Pipeline - 3-Stage Batch Test</h1>
  <p class="subtitle">Classify &rarr; Math (Gemini) &rarr; JS Code (DeepSeek) | Interactive HTML Output</p>
</header>

<div class="controls">
  <button id="start-btn" onclick="startBatch()">Start Batch Test</button>
  <div class="stat">Elapsed: <span class="stat-val" id="elapsed">0.0s</span></div>
  <div class="stat">Progress: <span class="stat-val" id="progress">0/0</span></div>
</div>

<div class="filters" id="filters">
  <button class="filter-btn active" onclick="filterDim('all')">All</button>
  <button class="filter-btn" onclick="filterDim('2d')">2D</button>
  <button class="filter-btn" onclick="filterDim('3d')">3D</button>
  <span class="filter-sep">|</span>
  <button class="filter-btn active" onclick="filterSet('all')">All Sets</button>
  <button class="filter-btn" onclick="filterSet('hkdse')">HKDSE</button>
  <button class="filter-btn" onclick="filterSet('coordinate')">Coordinate</button>
  <button class="filter-btn" onclick="filterSet('hkdse_new')">New HKDSE</button>
</div>

<div class="summary">
  <div class="summary-card">
    <div class="value" id="success-rate">0%</div>
    <div class="label">Success Rate</div>
  </div>
  <div class="summary-card">
    <div class="value" id="throughput">0.0</div>
    <div class="label">Q/min</div>
  </div>
  <div class="summary-card">
    <div class="value" id="input-tokens">0</div>
    <div class="label">Input Tokens</div>
    <div class="sub-value" id="input-cost">$0.0000</div>
  </div>
  <div class="summary-card">
    <div class="value" id="output-tokens">0</div>
    <div class="label">Output Tokens</div>
    <div class="sub-value" id="output-cost">$0.0000</div>
  </div>
  <div class="summary-card highlight">
    <div class="value" id="total-cost">$0.0000</div>
    <div class="label">Total Cost</div>
  </div>
  <div class="summary-card">
    <div class="value" id="cost-per-gen">$0.0000</div>
    <div class="label">Per Diagram</div>
    <div class="sub-value" id="cost-per-gen-hkd">HK$0.0000</div>
  </div>
</div>

<div class="model-breakdown" id="model-breakdown" style="display:none">
  <div class="model-panel">
    <div class="model-panel-title">Math <span class="model-tag">Gemini 3 Flash</span></div>
    <div class="token-row">
      <span class="token-label">Input Tokens</span>
      <span><span class="token-val" id="math-input-tokens">0</span><span class="token-cost" id="math-input-cost">$0.0000</span></span>
    </div>
    <div class="token-row">
      <span class="token-label">Output Tokens</span>
      <span><span class="token-val" id="math-output-tokens">0</span><span class="token-cost" id="math-output-cost">$0.0000</span></span>
    </div>
    <div class="model-total">
      <span class="token-label">Total</span>
      <span class="token-val" id="math-total-cost">$0.0000</span>
    </div>
  </div>
  <div class="model-panel">
    <div class="model-panel-title">JS Code <span class="model-tag">DeepSeek V3.2</span></div>
    <div class="token-row">
      <span class="token-label">Input Tokens</span>
      <span><span class="token-val" id="cg-input-tokens">0</span><span class="token-cost" id="cg-input-cost">$0.0000</span></span>
    </div>
    <div class="token-row">
      <span class="token-label">Output Tokens</span>
      <span><span class="token-val" id="cg-output-tokens">0</span><span class="token-cost" id="cg-output-cost">$0.0000</span></span>
    </div>
    <div class="model-total">
      <span class="token-label">Total</span>
      <span class="token-val" id="cg-total-cost">$0.0000</span>
    </div>
  </div>
</div>

<div class="results-grid" id="results-grid">
</div>

</div>

<script>
var pollInterval = null;
var currentDimFilter = 'all';
var currentSetFilter = 'all';
var latestResults = [];

function startBatch() {
  var btn = document.getElementById('start-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Running...';

  fetch('/start', {method: 'POST'})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.error) {
        alert(d.error);
        btn.disabled = false;
        btn.textContent = 'Start Batch Test';
        return;
      }
      startPolling();
    })
    .catch(function(e) {
      alert('Error: ' + e);
      btn.disabled = false;
      btn.textContent = 'Start Batch Test';
    });
}

function startPolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(fetchStatus, 1000);
  fetchStatus();
}

function fetchStatus() {
  fetch('/status')
    .then(function(r) { return r.json(); })
    .then(updateUI)
    .catch(function(e) { console.error(e); });
}

function filterDim(dim) {
  currentDimFilter = dim;
  var btns = document.querySelectorAll('.filters .filter-btn');
  // Dim buttons: indices 0, 1, 2
  for (var i = 0; i < 3; i++) {
    btns[i].classList.remove('active');
  }
  event.target.classList.add('active');
  renderResults(latestResults);
}

function filterSet(set) {
  currentSetFilter = set;
  var btns = document.querySelectorAll('.filters .filter-btn');
  // Set buttons: indices 4, 5, 6, 7 (index 3 is separator)
  for (var i = 4; i < btns.length; i++) {
    btns[i].classList.remove('active');
  }
  event.target.classList.add('active');
  renderResults(latestResults);
}

function updateUI(data) {
  document.getElementById('elapsed').textContent = data.elapsed + 's';
  document.getElementById('progress').textContent = data.completed + '/' + data.total;
  document.getElementById('total-cost').textContent = '$' + data.total_cost.toFixed(4);

  var successRate = data.completed > 0 ? Math.round((data.success_count / data.completed) * 100) : 0;
  document.getElementById('success-rate').textContent = successRate + '%';

  // Throughput
  var throughput = data.elapsed > 0 ? ((data.completed / data.elapsed) * 60).toFixed(1) : '0.0';
  document.getElementById('throughput').textContent = throughput;

  // Pricing
  var mathInputPrice = data.pricing ? data.pricing.math.input : 0.50;
  var mathOutputPrice = data.pricing ? data.pricing.math.output : 3.00;
  var cgInputPrice = data.pricing ? data.pricing.codegen.input : 0.28;
  var cgOutputPrice = data.pricing ? data.pricing.codegen.output : 0.42;

  // Calculate totals
  var inputTokens = 0, outputTokens = 0, inputCost = 0, outputCost = 0;
  var mathIn = 0, mathOut = 0, cgIn = 0, cgOut = 0;

  data.results.forEach(function(r) {
    if (r.math) {
      mathIn += r.math.prompt_tokens || 0;
      mathOut += r.math.completion_tokens || 0;
    }
    if (r.codegen) {
      cgIn += r.codegen.prompt_tokens || 0;
      cgOut += r.codegen.completion_tokens || 0;
    }
  });

  inputTokens = mathIn + cgIn;
  outputTokens = mathOut + cgOut;
  inputCost = (mathIn / 1e6) * mathInputPrice + (cgIn / 1e6) * cgInputPrice;
  outputCost = (mathOut / 1e6) * mathOutputPrice + (cgOut / 1e6) * cgOutputPrice;

  document.getElementById('input-tokens').textContent = inputTokens.toLocaleString();
  document.getElementById('output-tokens').textContent = outputTokens.toLocaleString();
  document.getElementById('input-cost').textContent = '$' + inputCost.toFixed(4);
  document.getElementById('output-cost').textContent = '$' + outputCost.toFixed(4);

  // Per-diagram cost
  var USD_TO_HKD = 7.8;
  var completedCount = data.completed || 0;
  var costPerGen = completedCount > 0 ? data.total_cost / completedCount : 0;
  document.getElementById('cost-per-gen').textContent = '$' + costPerGen.toFixed(4);
  document.getElementById('cost-per-gen-hkd').textContent = 'HK$' + (costPerGen * USD_TO_HKD).toFixed(4);

  // Model breakdown
  var mathInCost = (mathIn / 1e6) * mathInputPrice;
  var mathOutCost = (mathOut / 1e6) * mathOutputPrice;
  var cgInCost = (cgIn / 1e6) * cgInputPrice;
  var cgOutCost = (cgOut / 1e6) * cgOutputPrice;

  document.getElementById('math-input-tokens').textContent = mathIn.toLocaleString();
  document.getElementById('math-output-tokens').textContent = mathOut.toLocaleString();
  document.getElementById('math-input-cost').textContent = '$' + mathInCost.toFixed(4);
  document.getElementById('math-output-cost').textContent = '$' + mathOutCost.toFixed(4);
  document.getElementById('math-total-cost').textContent = '$' + (mathInCost + mathOutCost).toFixed(4);

  document.getElementById('cg-input-tokens').textContent = cgIn.toLocaleString();
  document.getElementById('cg-output-tokens').textContent = cgOut.toLocaleString();
  document.getElementById('cg-input-cost').textContent = '$' + cgInCost.toFixed(4);
  document.getElementById('cg-output-cost').textContent = '$' + cgOutCost.toFixed(4);
  document.getElementById('cg-total-cost').textContent = '$' + (cgInCost + cgOutCost).toFixed(4);

  if (data.completed > 0) {
    document.getElementById('model-breakdown').style.display = 'grid';
  }

  latestResults = data.results;
  renderResults(data.results);

  if (!data.running && data.completed > 0) {
    clearInterval(pollInterval);
    var btn = document.getElementById('start-btn');
    btn.disabled = false;
    btn.textContent = 'Start Batch Test';
  }
}

function renderResults(results) {
  var grid = document.getElementById('results-grid');
  grid.innerHTML = '';

  results.forEach(function(r) {
    // Apply filters
    var dim = r.dimension || '';
    var testSet = r.test_set || '';
    if (currentDimFilter !== 'all' && dim !== currentDimFilter) return;
    if (currentSetFilter !== 'all' && testSet !== currentSetFilter) return;

    var card = document.createElement('div');
    card.className = 'result-card ' + (r.pending ? 'pending' : (r.success ? 'success' : 'failed'));

    var dimBadge = dim ?
      '<span class="card-badge badge-' + dim + '">' + dim.toUpperCase() + '</span>' :
      '<span class="card-badge badge-pending">PENDING</span>';

    var statusBadge = r.pending ? '' :
      (r.success ? '<span class="card-badge badge-success">SUCCESS</span>' :
                   '<span class="card-badge badge-failed">FAILED</span>');

    var setBadge = testSet ? '<span class="card-badge badge-' + testSet + '">' + testSet.toUpperCase().replace('_', ' ') + '</span>' : '';

    var stagesHtml = '';
    if (!r.pending) {
      var mathClass = r.math && r.math.success ? 'done' : (r.math && r.math.error ? 'error' : '');
      var cgClass = r.codegen && r.codegen.success ? 'done' : (r.codegen && r.codegen.error ? 'error' : '');

      stagesHtml = '<div class="stages">' +
        '<div class="stage ' + mathClass + '"><div class="stage-name">Math</div><div class="stage-info">' +
          (r.math ? r.math.duration || 0 : 0) + 's</div></div>' +
        '<div class="stage ' + cgClass + '"><div class="stage-name">JS Code</div><div class="stage-info">' +
          (r.codegen ? r.codegen.duration || 0 : 0) + 's</div></div>' +
        '</div>';
    }

    var statsHtml = '';
    if (!r.pending) {
      var inTok = (r.math ? r.math.prompt_tokens || 0 : 0) +
                  (r.codegen ? r.codegen.prompt_tokens || 0 : 0);
      var outTok = (r.math ? r.math.completion_tokens || 0 : 0) +
                   (r.codegen ? r.codegen.completion_tokens || 0 : 0);
      statsHtml = '<div class="card-stats">' +
        '<span>Time: <span class="val">' + r.total_duration + 's</span></span>' +
        '<span>Cost: <span class="val">$' + r.total_cost.toFixed(4) + '</span></span>' +
        '<span>In: <span class="val">' + inTok.toLocaleString() + '</span></span>' +
        '<span>Out: <span class="val">' + outTok.toLocaleString() + '</span></span>' +
        '</div>';
    }

    var diagramHtml = '';
    if (r.output_path) {
      var iframeHeight = (dim === '3d') ? '400' : '350';
      diagramHtml = '<div class="card-diagram"><iframe src="' + r.output_path + '?t=' + Date.now() +
        '" height="' + iframeHeight + '" loading="lazy"></iframe></div>';
    }

    card.innerHTML =
      '<div class="card-header">' +
        '<span class="card-title">' + r.name + '</span>' +
        '<span class="card-badges">' + setBadge + ' ' + dimBadge + ' ' + statusBadge + '</span>' +
      '</div>' +
      '<div class="card-body">' +
        '<div class="question-text">' + escapeHtml(r.text) + '</div>' +
        stagesHtml +
        statsHtml +
      '</div>' +
      diagramHtml;

    grid.appendChild(card);
  });
}

function escapeHtml(text) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

// Initial load
fetchStatus();
</script>
</body>
</html>
"""


# ======================================================================
# Entry Point
# ======================================================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="JS Pipeline - 3-Stage Batch Test with Real-Time Web UI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Pipeline: Classify -> Math (Gemini) -> JS Code (DeepSeek) | Interactive HTML Output

Test sets:
  hkdse          - HKDSE 2D + 3D questions
  coord          - Coordinate geometry questions
  hkdse_new      - New HKDSE-style questions
  all            - All question sets (default)

Examples:
  python3 batch_test_js_ui.py                              # Run all questions
  python3 batch_test_js_ui.py --test-set hkdse             # HKDSE only
  python3 batch_test_js_ui.py --test-set coord             # Coordinate only
  python3 batch_test_js_ui.py --test-set hkdse_new         # New HKDSE only
  python3 batch_test_js_ui.py --dim 2d                     # 2D only
  python3 batch_test_js_ui.py --dim 3d                     # 3D only
  python3 batch_test_js_ui.py --workers 10                 # 10 concurrent workers
        """
    )
    parser.add_argument(
        "--dim",
        choices=["2d", "3d", "all"],
        default="all",
        help="Filter by dimension type (default: all)"
    )
    parser.add_argument(
        "--test-set",
        choices=["hkdse", "coord", "coordinate", "hkdse_new", "all"],
        default="all",
        help="Filter by test set source (default: all)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5052,
        help="Port for the web UI (default: 5052)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=50,
        help="Number of concurrent workers (default: 50)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open browser"
    )
    return parser.parse_args()


if __name__ == "__main__":
    import webbrowser

    args = parse_args()

    ALL_QUESTIONS = build_question_list(
        dim_filter=args.dim,
        test_set_filter=args.test_set,
    )
    MAX_WORKERS = args.workers

    if not ALL_QUESTIONS:
        print("ERROR: No questions match the selected filters (--dim={}, --test-set={})".format(
            args.dim, args.test_set))
        sys.exit(1)

    # Count by dimension
    dim_counts = {}
    set_counts = {}
    for q in ALL_QUESTIONS:
        d = q.get("dimension", "unknown")
        s = q.get("test_set", "unknown")
        dim_counts[d] = dim_counts.get(d, 0) + 1
        set_counts[s] = set_counts.get(s, 0) + 1

    # Clean up previous batch output
    batch_dir = SCRIPT_DIR / "output" / "batch_js"
    if batch_dir.exists():
        shutil.rmtree(str(batch_dir))

    port = args.port
    url = "http://127.0.0.1:{}".format(port)

    print("=" * 60)
    print("JS Pipeline - 3-Stage Batch Test")
    print("=" * 60)
    print("URL: {}".format(url))
    print("Questions: {}".format(len(ALL_QUESTIONS)))
    for d, c in sorted(dim_counts.items()):
        print("  {}: {}".format(d, c))
    for s, c in sorted(set_counts.items()):
        print("  [{}]: {}".format(s, c))
    print("Pipeline: Classify -> Math (Gemini) -> JS Code (DeepSeek)")
    print("Workers: {}".format(MAX_WORKERS))
    print("=" * 60)

    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
