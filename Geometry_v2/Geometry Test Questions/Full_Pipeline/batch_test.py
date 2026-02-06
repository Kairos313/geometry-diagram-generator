#!/usr/bin/env python3
"""
Batch Test Script for Geometry Diagram Pipeline.

Runs test questions in parallel using asyncio,
tracks costs, and displays results in a web interface.

Three test sets test different prompt paths:

1. GEOMETRY (--test-set geometry) - 10 questions, uses ORIGINAL prompts:
   - Stage 1: Question_to_Blueprint_Coordinate_included (outputs DIMENSION: 2D or 3D)
   - Stage 2: Blueprint_to_Code_Gemini
   - Output: PNG (2D) or GIF (3D)

2. COORDINATE (--test-set coordinate) - 15 questions, uses COORDINATE prompts:
   - Stage 1: Question_to_Blueprint_Coordinate_included (outputs DIMENSION: COORDINATE_2D)
   - Stage 2: Blueprint_to_Code_Coordinate
   - Output: PNG

3. HKDSE (--test-set hkdse) - 35 questions, uses ORIGINAL prompts:
   - Stage 1: Question_to_Blueprint_Coordinate_included (outputs DIMENSION: 2D or 3D)
   - Stage 2: Blueprint_to_Code_Gemini
   - Output: PNG (2D) or GIF (3D)
   - Based on HKDSE Grade 12 Mathematics Extended Part Module 2
   - Includes basic (10+10) and advanced M2 Section B style (5+10) questions

Usage:
    python3 batch_test.py                              # Run geometry tests (default)
    python3 batch_test.py --test-set coordinate        # Run coordinate geometry tests
    python3 batch_test.py --test-set hkdse             # Run HKDSE Grade 12 tests
    python3 batch_test.py --test-set hkdse --dim 3d    # Run only HKDSE 3D tests
    python3 batch_test.py --test-set all               # Run all tests
    python3 batch_test.py --dim 3d                     # Run only 3D geometry tests
    python3 batch_test.py --test-set coordinate --topic circles

Dimension filter (for geometry/hkdse):
    --dim 2d   Only 2D questions
    --dim 3d   Only 3D questions

Topic filter:
    geometry:   triangles, circles, quadrilaterals, prisms, pyramids, cylinders
    coordinate: straight_lines, circles, linear_programming, loci, graph_transformations, functions
    hkdse:      circles, triangles, quadrilaterals, pyramids, prisms, cylinders, cones
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
logging.getLogger("werkzeug").setLevel(logging.ERROR)   # Flask HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)     # Gemini SDK HTTP logs
logging.getLogger("httpcore").setLevel(logging.WARNING)  # httpcore transport logs
logging.getLogger("google").setLevel(logging.WARNING)    # All google.* loggers
logging.getLogger("google_genai").setLevel(logging.WARNING)       # google_genai SDK (AFC messages)
logging.getLogger("generate_code").setLevel(logging.WARNING)      # Pipeline code gen
logging.getLogger("generate_code_kimi").setLevel(logging.WARNING) # Kimi code gen
logging.getLogger("generate_blueprint").setLevel(logging.WARNING) # Blueprint gen

# Ensure pipeline modules are importable
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

load_dotenv(SCRIPT_DIR / ".env")

# ======================================================================
# Test Questions - Import from separate modules
# ======================================================================

# Import synthetic geometry test questions (2D + 3D) - uses original prompts
from geometry_test_questions import (
    GEOMETRY_TEST_QUESTIONS,
    TEST_QUESTIONS_2D,
    TEST_QUESTIONS_3D,
    get_questions_by_dimension as get_geometry_by_dimension,
    get_questions_by_topic as get_geometry_by_topic,
)

# Import coordinate geometry test questions - uses coordinate prompts
from coordinate_test_questions import (
    COORDINATE_TEST_QUESTIONS,
    get_questions_by_topic as get_coordinate_by_topic,
)

# Import HKDSE Grade 12 geometry test questions - uses original prompts
from hkdse_test_questions import (
    HKDSE_TEST_QUESTIONS,
    HKDSE_QUESTIONS_2D,
    HKDSE_QUESTIONS_3D,
    get_questions_by_dimension as get_hkdse_by_dimension,
    get_questions_by_topic as get_hkdse_by_topic,
)

# Default to geometry questions; will be updated by CLI args
ALL_QUESTIONS = GEOMETRY_TEST_QUESTIONS
CURRENT_TEST_SET = "geometry"  # Track which test set is active
CODEGEN_MODEL = "gemini"  # Track which model is used for code generation ("gemini" or "kimi")
MAX_WORKERS = 10  # Number of concurrent workers
COMPACT_MODE = False  # Use compact JSON blueprint format

# ======================================================================
# Pricing (per million tokens)
# ======================================================================

PRICING_GEMINI = {
    "blueprint": {"input": 0.50, "output": 3.00},  # Gemini 3 Flash
    "codegen": {"input": 0.50, "output": 3.00},    # Gemini 3 Flash
}

PRICING_KIMI = {
    "blueprint": {"input": 0.50, "output": 3.00},  # Gemini 3 Flash (blueprint always uses Gemini)
    "codegen": {"input": 0.45, "output": 2.50},    # Kimi K2.5
}

# Will be set based on CODEGEN_MODEL
PRICING = PRICING_GEMINI


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
    blueprint: StageResult = field(default_factory=StageResult)
    codegen: StageResult = field(default_factory=StageResult)
    execution: StageResult = field(default_factory=StageResult)
    total_duration: float = 0.0
    total_cost: float = 0.0
    output_path: Optional[str] = None
    success: bool = False


# Global results storage
results: Dict[str, QuestionResult] = {}
batch_status = {"running": False, "completed": 0, "total": 0, "start_time": 0}


# ======================================================================
# Pipeline Runner (Sync, runs in thread pool)
# ======================================================================

def run_single_question(question: dict) -> QuestionResult:
    """Run the full pipeline for a single question."""
    from generate_blueprint import generate_blueprint

    # Import code generation based on selected model
    if CODEGEN_MODEL == "kimi":
        from generate_code_kimi import generate_render_code, execute_code
        codegen_api_key = os.getenv("OPENROUTER_API_KEY")
        codegen_key_name = "OPENROUTER_API_KEY"
    else:  # gemini (default)
        from generate_code import generate_render_code, execute_code
        codegen_api_key = os.getenv("GEMINI_API_KEY")
        codegen_key_name = "GEMINI_API_KEY"

    # Blueprint always uses Gemini
    blueprint_api_key = os.getenv("GEMINI_API_KEY")
    if not blueprint_api_key:
        result = QuestionResult(
            question_id=question["id"],
            question_name=question["name"],
            question_text=question["text"],
        )
        result.blueprint.error = "GEMINI_API_KEY not set"
        return result

    if not codegen_api_key:
        result = QuestionResult(
            question_id=question["id"],
            question_name=question["name"],
            question_text=question["text"],
        )
        result.codegen.error = f"{codegen_key_name} not set"
        return result

    result = QuestionResult(
        question_id=question["id"],
        question_name=question["name"],
        question_text=question["text"],
    )

    start_time = time.time()
    run_id = f"{question['id']}_{uuid.uuid4().hex[:8]}"
    output_dir = str(SCRIPT_DIR / "output" / "batch" / run_id)
    os.makedirs(output_dir, exist_ok=True)

    # --- Stage 1: Blueprint ---
    try:
        bp_result = generate_blueprint(
            api_key=blueprint_api_key,
            question_text=question["text"],
            output_dir=output_dir,
            compact=COMPACT_MODE,
        )

        if bp_result["success"]:
            result.blueprint.success = True
            result.blueprint.duration = bp_result["api_call_duration"]
            result.blueprint.prompt_tokens = bp_result["prompt_tokens"]
            result.blueprint.completion_tokens = bp_result["completion_tokens"]
            result.blueprint.total_tokens = bp_result["total_tokens"]
            result.blueprint.output = bp_result["blueprint"]

            # Calculate cost
            cost = (
                (bp_result["prompt_tokens"] / 1e6) * PRICING["blueprint"]["input"] +
                (bp_result["completion_tokens"] / 1e6) * PRICING["blueprint"]["output"]
            )
            result.blueprint.cost = cost

            blueprint_text = bp_result["blueprint"]
            # Get dimension from blueprint (Stage 1 now declares it explicitly)
            dimension_type = bp_result.get("dimension", "2d")
            result.dimension = dimension_type
        else:
            result.blueprint.error = bp_result.get("error", "Unknown error")
            result.total_duration = time.time() - start_time
            return result

    except Exception as e:
        result.blueprint.error = str(e)
        result.total_duration = time.time() - start_time
        return result

    # --- Stage 2: Code Generation (with retry for "no code block" errors) ---
    # COORDINATE_2D is also a 2D type - uses matplotlib/png
    is_2d = dimension_type in ("2d", "coordinate_2d")
    output_format = "png" if is_2d else "gif"
    output_path = str(Path(output_dir) / f"diagram.{output_format}")
    target_lib = "matplotlib" if is_2d else "manim"

    max_codegen_attempts = 2
    code_result = None

    for attempt in range(1, max_codegen_attempts + 1):
        try:
            code_result = generate_render_code(
                api_key=codegen_api_key,
                blueprint_text=blueprint_text,
                output_path=output_path,
                output_format=output_format,
                dimension_type=dimension_type,
                question_text=question["text"],
                compact=COMPACT_MODE,
            )

            if code_result["success"]:
                result.codegen.duration = code_result["api_call_duration"]
                result.codegen.prompt_tokens = code_result["prompt_tokens"]
                result.codegen.completion_tokens = code_result["completion_tokens"]
                result.codegen.total_tokens = code_result["total_tokens"]
                result.codegen.output = code_result["code"]

                # Calculate cost
                cost = (
                    (code_result["prompt_tokens"] / 1e6) * PRICING["codegen"]["input"] +
                    (code_result["completion_tokens"] / 1e6) * PRICING["codegen"]["output"]
                )
                result.codegen.cost = cost

                # Verify output directory exists (defensive check)
                if not Path(output_dir).exists():
                    print(f"[WARNING] Directory missing, recreating: {output_dir}")
                    os.makedirs(output_dir, exist_ok=True)

                # Write code to file
                code_path = str(Path(output_dir) / "render_code.py")
                with open(code_path, "w", encoding="utf-8") as f:
                    f.write(code_result["code"])

                # Only set success AFTER file write succeeds
                result.codegen.success = True
                break  # Success, exit retry loop

            else:
                error_msg = code_result.get("error", "Unknown error")
                # Retry on "no code block" errors
                if "No Python code block" in error_msg and attempt < max_codegen_attempts:
                    print(f"[{question['id']}] Code gen failed (no code block), retrying...")
                    continue
                result.codegen.error = error_msg
                result.total_duration = time.time() - start_time
                result.total_cost = result.blueprint.cost
                return result

        except Exception as e:
            if attempt < max_codegen_attempts:
                print(f"[{question['id']}] Code gen exception, retrying: {e}")
                continue
            result.codegen.success = False
            result.codegen.error = str(e)
            result.total_duration = time.time() - start_time
            result.total_cost = result.blueprint.cost
            return result

    # Check if code generation succeeded after all attempts
    if not result.codegen.success:
        if code_result:
            result.codegen.error = code_result.get("error", "Code generation failed after retries")
        else:
            result.codegen.error = "Code generation failed after retries"
        result.total_duration = time.time() - start_time
        result.total_cost = result.blueprint.cost
        return result

    # --- Stage 3: Execution ---
    code_path = str(Path(output_dir) / "render_code.py")
    exec_start = time.time()

    try:
        use_manim = (dimension_type == "3d")
        timeout = 300 if use_manim else 120
        exec_result = execute_code(code_path, timeout=timeout, use_manim_cli=use_manim, output_path=output_path)

        result.execution.duration = time.time() - exec_start
        result.execution.success = exec_result["success"] and Path(output_path).exists()
        result.execution.output = exec_result.get("stdout", "") + "\n" + exec_result.get("stderr", "")

        if result.execution.success:
            result.output_path = f"/output/batch/{run_id}/diagram.{output_format}"
            result.success = True
        else:
            result.execution.error = exec_result.get("stderr", "Execution failed")

    except Exception as e:
        result.execution.error = str(e)

    result.total_duration = time.time() - start_time
    result.total_cost = result.blueprint.cost + result.codegen.cost

    return result


async def run_batch_async(questions: List[dict], max_workers: int = 5):
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
                msg = (f"[{batch_status['completed']}/{batch_status['total']}] "
                       f"{result.question_name}: {status} "
                       f"({result.total_duration:.1f}s, ${result.total_cost:.4f})")
                if not result.success:
                    # Show which stage failed and why
                    if result.blueprint.error:
                        msg += f"\n  -> Blueprint error: {result.blueprint.error[:120]}"
                    elif result.codegen.error:
                        msg += f"\n  -> CodeGen error: {result.codegen.error[:120]}"
                    elif result.execution.error:
                        err_lines = result.execution.error.strip().split("\n")
                        # Show last meaningful error line
                        last_err = err_lines[-1] if err_lines else "Unknown"
                        msg += f"\n  -> Execution error: {last_err[:120]}"
                print(msg)
            except Exception as e:
                print(f"Error processing {q_id}: {e}")
                batch_status["completed"] += 1

    batch_status["running"] = False
    total_time = time.time() - batch_status["start_time"]
    total_cost = sum(r.total_cost for r in results.values())
    success_count = sum(1 for r in results.values() if r.success)

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {success_count}/{len(questions)} successful")
    print(f"Total time: {total_time:.1f}s")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"{'='*60}\n")


def start_batch_thread(max_workers: int = 10):
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
                "success": r.success,
                "total_duration": round(r.total_duration, 1),
                "total_cost": round(r.total_cost, 4),
                "output_path": r.output_path,
                "blueprint": {
                    "success": r.blueprint.success,
                    "duration": round(r.blueprint.duration, 1),
                    "tokens": r.blueprint.total_tokens,
                    "prompt_tokens": r.blueprint.prompt_tokens,
                    "completion_tokens": r.blueprint.completion_tokens,
                    "cost": round(r.blueprint.cost, 4),
                    "error": r.blueprint.error,
                },
                "codegen": {
                    "success": r.codegen.success,
                    "duration": round(r.codegen.duration, 1),
                    "tokens": r.codegen.total_tokens,
                    "prompt_tokens": r.codegen.prompt_tokens,
                    "completion_tokens": r.codegen.completion_tokens,
                    "cost": round(r.codegen.cost, 4),
                    "error": r.codegen.error,
                },
                "execution": {
                    "success": r.execution.success,
                    "duration": round(r.execution.duration, 1),
                    "error": r.execution.error,
                },
            })
        else:
            results_list.append({
                "id": q["id"],
                "name": q["name"],
                "text": q["text"],
                "pending": True,
            })

    return jsonify({
        "running": batch_status["running"],
        "completed": batch_status["completed"],
        "total": batch_status["total"],
        "elapsed": round(elapsed, 1),
        "total_cost": round(total_cost, 4),
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
<title>Geometry Pipeline - Batch Test</title>
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

.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem;margin-bottom:1.5rem}
.summary-card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:6px;padding:1rem;text-align:center}
.summary-card .value{font-size:1.6rem;color:#4ECDC4;font-weight:700}
.summary-card .label{color:#888;font-size:.75rem;text-transform:uppercase}
.summary-card .sub-value{color:#E9C46A;font-size:.9rem;font-weight:600;margin-top:.25rem}
.summary-card.highlight{border-color:#4ECDC4;background:#1a2a2a}

.results-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(450px,1fr));gap:1rem}
.result-card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;overflow:hidden}
.result-card.success{border-color:#96CEB4}
.result-card.failed{border-color:#FF6B6B}
.result-card.pending{border-color:#444;opacity:0.6}

.card-header{padding:.75rem 1rem;border-bottom:1px solid #2a2a2a;display:flex;justify-content:space-between;align-items:center}
.card-title{font-weight:600;font-size:.95rem}
.card-badge{padding:.15rem .5rem;border-radius:3px;font-size:.75rem;font-weight:700}
.badge-2d{background:#457B9D;color:#fff}
.badge-3d{background:#6A4C93;color:#fff}
.badge-pending{background:#333;color:#888}
.badge-success{background:#96CEB4;color:#0C0C0C}
.badge-failed{background:#FF6B6B;color:#fff}

.card-body{padding:.75rem 1rem}
.question-text{font-size:.82rem;color:#aaa;margin-bottom:.75rem;line-height:1.5;white-space:pre-wrap;word-wrap:break-word}

.stages{display:flex;gap:.5rem;margin-bottom:.75rem}
.stage{flex:1;background:#0C0C0C;border-radius:4px;padding:.4rem;text-align:center;font-size:.75rem}
.stage.done{background:#1a3a2a;color:#96CEB4}
.stage.error{background:#3a1a1a;color:#FF6B6B}
.stage-name{font-weight:600}
.stage-info{color:#888;font-size:.7rem}

.card-stats{display:flex;gap:.75rem;font-size:.8rem;color:#888;flex-wrap:wrap}
.card-stats span{display:flex;align-items:center;gap:.3rem}
.card-stats .val{color:#e0e0e0;font-weight:600}

.card-image{padding:.5rem;background:#0C0C0C;text-align:center;max-height:250px;overflow:hidden}
.card-image img{max-width:100%;max-height:230px;border-radius:4px}

.spinner{display:inline-block;width:16px;height:16px;border:2px solid #333;border-top-color:#4ECDC4;border-radius:50%;animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

.hidden{display:none}
</style>
</head>
<body>
<div class="container">

<header class="header">
  <h1>Geometry Pipeline - Batch Test</h1>
  <p class="subtitle">10 Questions (5 2D + 5 3D) - Parallel Processing with Cost Tracking</p>
</header>

<div class="controls">
  <button id="start-btn" onclick="startBatch()">Start Batch Test</button>
  <div class="stat">Elapsed: <span class="stat-val" id="elapsed">0.0s</span></div>
  <div class="stat">Progress: <span class="stat-val" id="progress">0/10</span></div>
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
</div>

<div class="results-grid" id="results-grid">
  <!-- Results will be populated here -->
</div>

</div>

<script>
var pollInterval = null;

function startBatch() {
  var btn = document.getElementById('start-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Running...';

  fetch('/start', {method: 'POST'})
    .then(r => r.json())
    .then(d => {
      if (d.error) {
        alert(d.error);
        btn.disabled = false;
        btn.textContent = 'Start Batch Test';
        return;
      }
      startPolling();
    })
    .catch(e => {
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
    .then(r => r.json())
    .then(updateUI)
    .catch(e => console.error(e));
}

function updateUI(data) {
  document.getElementById('elapsed').textContent = data.elapsed + 's';
  document.getElementById('progress').textContent = data.completed + '/' + data.total;
  document.getElementById('total-cost').textContent = '$' + data.total_cost.toFixed(4);

  var successRate = data.total > 0 ? Math.round((data.success_count / data.completed) * 100) || 0 : 0;
  document.getElementById('success-rate').textContent = successRate + '%';

  // Throughput: questions per minute (parallel execution metric)
  var throughput = data.elapsed > 0 ? ((data.completed / data.elapsed) * 60).toFixed(1) : '0.0';
  document.getElementById('throughput').textContent = throughput;

  // Calculate input/output tokens and costs separately
  var inputTokens = 0, outputTokens = 0;
  var inputCost = 0, outputCost = 0;

  // Pricing per million tokens (matches Python PRICING dict)
  var bpInputPrice = data.pricing ? data.pricing.blueprint.input : 0.50;
  var bpOutputPrice = data.pricing ? data.pricing.blueprint.output : 3.00;
  var cgInputPrice = data.pricing ? data.pricing.codegen.input : 0.50;
  var cgOutputPrice = data.pricing ? data.pricing.codegen.output : 3.00;

  data.results.forEach(r => {
    if (r.blueprint) {
      inputTokens += r.blueprint.prompt_tokens || 0;
      outputTokens += r.blueprint.completion_tokens || 0;
      inputCost += ((r.blueprint.prompt_tokens || 0) / 1e6) * bpInputPrice;
      outputCost += ((r.blueprint.completion_tokens || 0) / 1e6) * bpOutputPrice;
    }
    if (r.codegen) {
      inputTokens += r.codegen.prompt_tokens || 0;
      outputTokens += r.codegen.completion_tokens || 0;
      inputCost += ((r.codegen.prompt_tokens || 0) / 1e6) * cgInputPrice;
      outputCost += ((r.codegen.completion_tokens || 0) / 1e6) * cgOutputPrice;
    }
  });

  document.getElementById('input-tokens').textContent = inputTokens.toLocaleString();
  document.getElementById('output-tokens').textContent = outputTokens.toLocaleString();
  document.getElementById('input-cost').textContent = '$' + inputCost.toFixed(4);
  document.getElementById('output-cost').textContent = '$' + outputCost.toFixed(4);

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

  results.forEach(r => {
    var card = document.createElement('div');
    card.className = 'result-card ' + (r.pending ? 'pending' : (r.success ? 'success' : 'failed'));

    var dimBadge = r.dimension ?
      '<span class="card-badge badge-' + r.dimension + '">' + r.dimension.toUpperCase() + '</span>' :
      '<span class="card-badge badge-pending">PENDING</span>';

    var statusBadge = r.pending ? '' :
      (r.success ? '<span class="card-badge badge-success">SUCCESS</span>' :
                   '<span class="card-badge badge-failed">FAILED</span>');

    var stagesHtml = '';
    if (!r.pending) {
      var bpClass = r.blueprint.success ? 'done' : (r.blueprint.error ? 'error' : '');
      var cgClass = r.codegen.success ? 'done' : (r.codegen.error ? 'error' : '');
      var exClass = r.execution.success ? 'done' : (r.execution.error ? 'error' : '');

      stagesHtml = '<div class="stages">' +
        '<div class="stage ' + bpClass + '"><div class="stage-name">Blueprint</div><div class="stage-info">' +
          (r.blueprint.duration || 0) + 's</div></div>' +
        '<div class="stage ' + cgClass + '"><div class="stage-name">CodeGen</div><div class="stage-info">' +
          (r.codegen.duration || 0) + 's</div></div>' +
        '<div class="stage ' + exClass + '"><div class="stage-name">Execute</div><div class="stage-info">' +
          (r.execution.duration || 0) + 's</div></div>' +
        '</div>';
    }

    var statsHtml = '';
    if (!r.pending) {
      var inTok = (r.blueprint.prompt_tokens || 0) + (r.codegen.prompt_tokens || 0);
      var outTok = (r.blueprint.completion_tokens || 0) + (r.codegen.completion_tokens || 0);
      statsHtml = '<div class="card-stats">' +
        '<span>Time: <span class="val">' + r.total_duration + 's</span></span>' +
        '<span>Cost: <span class="val">$' + r.total_cost.toFixed(4) + '</span></span>' +
        '<span>In: <span class="val">' + inTok.toLocaleString() + '</span></span>' +
        '<span>Out: <span class="val">' + outTok.toLocaleString() + '</span></span>' +
        '</div>';
    }

    var imageHtml = '';
    if (r.output_path) {
      imageHtml = '<div class="card-image"><img src="' + r.output_path + '?t=' + Date.now() + '" alt="Diagram"></div>';
    }

    card.innerHTML =
      '<div class="card-header">' +
        '<span class="card-title">' + r.name + '</span>' +
        '<span>' + dimBadge + ' ' + statusBadge + '</span>' +
      '</div>' +
      '<div class="card-body">' +
        '<div class="question-text">' + escapeHtml(r.text) + '</div>' +
        stagesHtml +
        statsHtml +
      '</div>' +
      imageHtml;

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
        description="Batch Test Script for Geometry Diagram Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test sets (--test-set):
  geometry    Original 2D/3D synthetic geometry (10 questions)
              Uses: Question_to_Blueprint + Blueprint_to_Code_Gemini
  coordinate  Coordinate geometry (15 questions)
              Uses: Question_to_Blueprint_Coordinate_included + Blueprint_to_Code_Coordinate
  hkdse       HKDSE Grade 12 geometry (35 questions: 15 2D + 20 3D)
              Uses: Question_to_Blueprint + Blueprint_to_Code_Gemini
              Includes basic + advanced M2 Section B style questions
  all         All questions

Dimension filter (--dim, for geometry/hkdse test sets):
  2d          Only 2D questions
  3d          Only 3D questions

Topic filter (--topic):
  For geometry: triangles, circles, quadrilaterals, prisms, pyramids, cylinders
  For coordinate: straight_lines, circles, linear_programming, loci, graph_transformations, functions
  For hkdse: circles, triangles, quadrilaterals, pyramids, prisms, cylinders, cones

Examples:
  python3 batch_test.py                              # Run geometry tests (default)
  python3 batch_test.py --test-set coordinate        # Run coordinate geometry tests
  python3 batch_test.py --test-set hkdse             # Run HKDSE Grade 12 tests
  python3 batch_test.py --test-set hkdse --dim 3d    # Run only HKDSE 3D tests
  python3 batch_test.py --test-set all               # Run all tests
  python3 batch_test.py --dim 3d                     # Run only 3D geometry tests
  python3 batch_test.py --test-set coordinate --topic circles  # Run coordinate circle tests
        """
    )
    parser.add_argument(
        "--test-set",
        choices=["geometry", "coordinate", "hkdse", "all"],
        default="geometry",
        help="Which test set to run (default: geometry)"
    )
    parser.add_argument(
        "--dim",
        choices=["2d", "3d", "all"],
        default=None,
        help="Filter geometry questions by dimension (2d or 3d)"
    )
    parser.add_argument(
        "--topic",
        default=None,
        help="Filter questions by topic (depends on test set)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5051,
        help="Port for the web UI (default: 5051)"
    )
    parser.add_argument(
        "--codegen-model",
        choices=["gemini", "kimi"],
        default="gemini",
        help="Model for code generation: gemini (default) or kimi (Kimi K2.5)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open browser"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of concurrent workers (default: 10)"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Use compact JSON blueprint format (reduces tokens by ~70%%)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    import webbrowser

    args = parse_args()

    # Set code generation model and pricing
    CODEGEN_MODEL = args.codegen_model
    PRICING = PRICING_KIMI if CODEGEN_MODEL == "kimi" else PRICING_GEMINI

    # Set compact mode for JSON blueprints
    COMPACT_MODE = args.compact

    # Build question list based on CLI args
    if args.test_set == "geometry":
        # Synthetic geometry (2D + 3D) - uses original prompts
        if args.dim and args.dim != "all":
            ALL_QUESTIONS = get_geometry_by_dimension(args.dim)
            test_set_name = f"Geometry ({args.dim.upper()})"
        elif args.topic and args.topic != "all":
            ALL_QUESTIONS = get_geometry_by_topic(args.topic)
            test_set_name = f"Geometry ({args.topic})"
        else:
            ALL_QUESTIONS = GEOMETRY_TEST_QUESTIONS
            test_set_name = "Geometry (2D + 3D)"

    elif args.test_set == "coordinate":
        # Coordinate geometry - uses coordinate prompts
        if args.topic and args.topic != "all":
            ALL_QUESTIONS = get_coordinate_by_topic(args.topic)
            test_set_name = f"Coordinate ({args.topic})"
        else:
            ALL_QUESTIONS = COORDINATE_TEST_QUESTIONS
            test_set_name = "Coordinate Geometry"

    elif args.test_set == "hkdse":
        # HKDSE Grade 12 geometry - uses original prompts
        if args.dim and args.dim != "all":
            ALL_QUESTIONS = get_hkdse_by_dimension(args.dim)
            test_set_name = f"HKDSE ({args.dim.upper()})"
        elif args.topic and args.topic != "all":
            ALL_QUESTIONS = get_hkdse_by_topic(args.topic)
            test_set_name = f"HKDSE ({args.topic})"
        else:
            ALL_QUESTIONS = HKDSE_TEST_QUESTIONS
            test_set_name = "HKDSE Grade 12 (2D + 3D)"

    else:  # all
        # Combine all test sets
        if args.dim and args.dim != "all":
            geom_questions = get_geometry_by_dimension(args.dim)
            hkdse_questions = get_hkdse_by_dimension(args.dim)
            ALL_QUESTIONS = geom_questions + hkdse_questions + COORDINATE_TEST_QUESTIONS
            test_set_name = f"All ({args.dim.upper()} Geometry + HKDSE + Coordinate)"
        elif args.topic and args.topic != "all":
            # Try to filter all sets by topic
            geom_by_topic = get_geometry_by_topic(args.topic)
            coord_by_topic = get_coordinate_by_topic(args.topic)
            hkdse_by_topic = get_hkdse_by_topic(args.topic)
            ALL_QUESTIONS = geom_by_topic + hkdse_by_topic + coord_by_topic
            test_set_name = f"All ({args.topic})"
        else:
            ALL_QUESTIONS = GEOMETRY_TEST_QUESTIONS + HKDSE_TEST_QUESTIONS + COORDINATE_TEST_QUESTIONS
            test_set_name = "All Questions (Geometry + HKDSE + Coordinate)"

    CURRENT_TEST_SET = args.test_set
    MAX_WORKERS = args.workers

    # Clean up previous batch output
    batch_dir = SCRIPT_DIR / "output" / "batch"
    if batch_dir.exists():
        shutil.rmtree(str(batch_dir))

    port = args.port
    url = f"http://127.0.0.1:{port}"
    print(f"Starting Batch Test UI at {url}")
    print(f"Test set: {test_set_name}")
    print(f"Questions: {len(ALL_QUESTIONS)}")
    prompt_path = "Coordinate prompts" if args.test_set == "coordinate" else "Original prompts" if args.test_set in ("geometry", "hkdse") else "Mixed"
    codegen_model_name = "Kimi K2.5" if CODEGEN_MODEL == "kimi" else "Gemini 3 Flash"
    print(f"Prompt path: {prompt_path}")
    print(f"Code generation: {codegen_model_name}")
    print(f"Concurrent workers: {MAX_WORKERS}")

    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
