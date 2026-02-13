#!/usr/bin/env python3
"""
Focused 4-Stage Batch Test for Geometry Diagram Pipeline.

Pipeline: Classify -> Blueprint -> CodeGen -> Execute

Uses an LLM classifier (Gemini 3 Flash) to detect the dimension type
(2d/3d/coordinate_2d/coordinate_3d), then routes to focused prompts
for blueprint generation (Gemini) and code generation (DeepSeek).

40 questions total:
  - 10 HKDSE 2D (traditional geometry)
  - 10 HKDSE 3D (traditional geometry)
  - 10 Coordinate 2D (coordinate geometry with axes)
  - 10 Coordinate 3D (coordinate geometry with 3D axes)

Usage:
    python3 batch_test_focused.py                          # Run all 40 questions
    python3 batch_test_focused.py --dim 2d                 # Run only 2D questions
    python3 batch_test_focused.py --dim coordinate_3d      # Run only coordinate 3D
    python3 batch_test_focused.py --test-set hkdse         # Run only HKDSE questions
    python3 batch_test_focused.py --test-set coordinate    # Run only coordinate questions
    python3 batch_test_focused.py --workers 3              # Limit concurrency
    python3 batch_test_focused.py --port 5002              # Custom port
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
logging.getLogger("generate_code_deepseek").setLevel(logging.WARNING)
logging.getLogger("generate_blueprint").setLevel(logging.WARNING)
logging.getLogger("generate_blueprint_focused").setLevel(logging.WARNING)
logging.getLogger("classify_geometry_type").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Ensure pipeline modules are importable
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

load_dotenv(SCRIPT_DIR / ".env")

# ======================================================================
# Test Questions - Import from separate modules
# ======================================================================

from hkdse_test_questions import HKDSE_QUESTIONS_2D, HKDSE_QUESTIONS_3D
from coordinate_test_questions import (
    COORDINATE_QUESTIONS_2D_ORIGINAL,
    COORDINATE_QUESTIONS_3D,
)


def build_question_list(dim_filter="all", test_set_filter="all"):
    # type: (str, str) -> List[dict]
    """Build the question list with optional filtering.

    Returns up to 40 questions (10 per dimension type).
    """
    questions = []

    if test_set_filter in ("hkdse", "all"):
        hkdse_2d = [dict(q, test_set="hkdse") for q in HKDSE_QUESTIONS_2D[0:10]]
        hkdse_3d = [dict(q, test_set="hkdse") for q in HKDSE_QUESTIONS_3D[0:10]]
        if dim_filter in ("2d", "all"):
            questions.extend(hkdse_2d)
        if dim_filter in ("3d", "all"):
            questions.extend(hkdse_3d)

    if test_set_filter in ("coordinate", "all"):
        coord_2d = [dict(q, test_set="coordinate") for q in COORDINATE_QUESTIONS_2D_ORIGINAL[0:10]]
        coord_3d = [dict(q, test_set="coordinate") for q in COORDINATE_QUESTIONS_3D[0:10]]
        if dim_filter in ("coordinate_2d", "all"):
            questions.extend(coord_2d)
        if dim_filter in ("coordinate_3d", "all"):
            questions.extend(coord_3d)

    return questions


# Will be set by CLI args
ALL_QUESTIONS = []  # type: List[dict]
MAX_WORKERS = 5

# ======================================================================
# Pricing (per million tokens)
# ======================================================================

PRICING = {
    "classify": {"input": 0.50, "output": 3.00},     # Gemini 3 Flash
    "blueprint": {"input": 0.50, "output": 3.00},    # Gemini 3 Flash
    "codegen": {"input": 0.28, "output": 0.42},      # DeepSeek-V3.2 Azure
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
    ground_truth_dimension: str = ""
    detected_dimension: str = ""
    classifier_correct: bool = False
    test_set: str = ""
    dimension: str = ""
    classify: StageResult = field(default_factory=StageResult)
    blueprint: StageResult = field(default_factory=StageResult)
    codegen: StageResult = field(default_factory=StageResult)
    execution: StageResult = field(default_factory=StageResult)
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
    """Run the full 4-stage pipeline for a single question."""

    from classify_geometry_type import classify_geometry_type
    from generate_blueprint_focused import generate_blueprint
    from generate_code_deepseek import generate_render_code, execute_code

    gemini_key = os.getenv("GEMINI_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    result = QuestionResult(
        question_id=question["id"],
        question_name=question["name"],
        question_text=question["text"],
        ground_truth_dimension=question.get("dimension", ""),
        test_set=question.get("test_set", ""),
    )

    # Check API keys
    if not gemini_key:
        result.classify.error = "GEMINI_API_KEY not set"
        return result
    if not deepseek_key:
        result.codegen.error = "DEEPSEEK_API_KEY not set"
        return result

    start_time = time.time()
    run_id = "{}_{}".format(question["id"], uuid.uuid4().hex[:8])
    output_dir = str(SCRIPT_DIR / "output" / "batch" / run_id)
    os.makedirs(output_dir, exist_ok=True)

    # --- Stage 0: Classify ---
    try:
        classify_result = classify_geometry_type(
            api_key=gemini_key,
            question_text=question["text"],
        )

        dimension_type = classify_result.get("dimension_type", "2d")
        result.classify.success = True
        result.classify.duration = classify_result.get("duration", 0.0)
        result.classify.prompt_tokens = classify_result.get("tokens_input", 0)
        result.classify.completion_tokens = classify_result.get("tokens_output", 0)
        result.classify.total_tokens = classify_result.get("tokens_total", 0)
        result.classify.cost = classify_result.get("cost", 0.0)
        result.classify.output = dimension_type

        result.detected_dimension = dimension_type
        result.dimension = dimension_type
        result.classifier_correct = (dimension_type == result.ground_truth_dimension)

    except Exception as e:
        result.classify.error = str(e)
        result.total_duration = time.time() - start_time
        return result

    # --- Stage 1: Blueprint ---
    try:
        bp_result = generate_blueprint(
            api_key=gemini_key,
            question_text=question["text"],
            output_dir=output_dir,
            dimension_type=dimension_type,
        )

        if bp_result["success"]:
            result.blueprint.success = True
            result.blueprint.duration = bp_result.get("api_call_duration", 0.0)
            result.blueprint.prompt_tokens = bp_result.get("prompt_tokens", 0)
            result.blueprint.completion_tokens = bp_result.get("completion_tokens", 0)
            result.blueprint.total_tokens = bp_result.get("total_tokens", 0)
            result.blueprint.output = bp_result.get("blueprint", "")

            # Calculate cost
            cost = (
                (result.blueprint.prompt_tokens / 1e6) * PRICING["blueprint"]["input"] +
                (result.blueprint.completion_tokens / 1e6) * PRICING["blueprint"]["output"]
            )
            result.blueprint.cost = cost

            blueprint_text = bp_result["blueprint"]
        else:
            result.blueprint.error = bp_result.get("error", "Unknown error")
            result.total_duration = time.time() - start_time
            result.total_cost = result.classify.cost
            return result

    except Exception as e:
        result.blueprint.error = str(e)
        result.total_duration = time.time() - start_time
        result.total_cost = result.classify.cost
        return result

    # --- Stage 2: Code Generation (with retry) ---
    # Map coordinate_3d to 3d for codegen (generate_code_deepseek doesn't handle coordinate_3d)
    codegen_dim = "3d" if dimension_type == "coordinate_3d" else dimension_type
    is_2d = dimension_type in ("2d", "coordinate_2d")
    output_format = "png" if is_2d else "gif"
    output_path = str(Path(output_dir) / "diagram.{}".format(output_format))

    max_codegen_attempts = 2
    code_result = None

    for attempt in range(1, max_codegen_attempts + 1):
        try:
            code_result = generate_render_code(
                api_key=deepseek_key,
                blueprint_text=blueprint_text,
                output_path=output_path,
                output_format=output_format,
                dimension_type=codegen_dim,
                question_text=question["text"],
                compact=True,
            )

            if code_result["success"]:
                result.codegen.duration = code_result.get("api_call_duration", 0.0)
                result.codegen.prompt_tokens = code_result.get("prompt_tokens", 0)
                result.codegen.completion_tokens = code_result.get("completion_tokens", 0)
                result.codegen.total_tokens = code_result.get("total_tokens", 0)
                result.codegen.output = code_result.get("code", "")

                # Calculate cost
                cost = (
                    (result.codegen.prompt_tokens / 1e6) * PRICING["codegen"]["input"] +
                    (result.codegen.completion_tokens / 1e6) * PRICING["codegen"]["output"]
                )
                result.codegen.cost = cost

                # Write code to file
                if not Path(output_dir).exists():
                    os.makedirs(output_dir, exist_ok=True)

                code_path = str(Path(output_dir) / "render_code.py")
                with open(code_path, "w", encoding="utf-8") as f:
                    f.write(code_result["code"])

                result.codegen.success = True
                break

            else:
                error_msg = code_result.get("error", "Unknown error")
                if "No Python code block" in error_msg and attempt < max_codegen_attempts:
                    print("[{}] Code gen failed (no code block), retrying...".format(question["id"]))
                    continue
                result.codegen.error = error_msg
                result.total_duration = time.time() - start_time
                result.total_cost = result.classify.cost + result.blueprint.cost
                return result

        except Exception as e:
            if attempt < max_codegen_attempts:
                print("[{}] Code gen exception, retrying: {}".format(question["id"], e))
                continue
            result.codegen.success = False
            result.codegen.error = str(e)
            result.total_duration = time.time() - start_time
            result.total_cost = result.classify.cost + result.blueprint.cost
            return result

    if not result.codegen.success:
        if code_result:
            result.codegen.error = code_result.get("error", "Code generation failed after retries")
        else:
            result.codegen.error = "Code generation failed after retries"
        result.total_duration = time.time() - start_time
        result.total_cost = result.classify.cost + result.blueprint.cost
        return result

    # --- Stage 3: Execution ---
    code_path = str(Path(output_dir) / "render_code.py")
    exec_start = time.time()

    try:
        use_manim = dimension_type in ("3d", "coordinate_3d")
        timeout = 300 if use_manim else 120
        # Pass codegen_dim so execute_code finds the right helpers
        exec_result = execute_code(
            code_path,
            timeout=timeout,
            use_manim_cli=use_manim,
            output_path=output_path,
            dimension_type=codegen_dim,
        )

        result.execution.duration = time.time() - exec_start
        result.execution.success = exec_result["success"] and Path(output_path).exists()
        result.execution.output = exec_result.get("stdout", "") + "\n" + exec_result.get("stderr", "")

        if result.execution.success:
            result.output_path = "/output/batch/{}/diagram.{}".format(run_id, output_format)
            result.success = True
        else:
            result.execution.error = exec_result.get("stderr", "Execution failed")

    except Exception as e:
        result.execution.error = str(e)

    result.total_duration = time.time() - start_time
    result.total_cost = result.classify.cost + result.blueprint.cost + result.codegen.cost

    return result


# ======================================================================
# Batch Runner (Async with Thread Pool)
# ======================================================================

async def run_batch_async(questions, max_workers=5):
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
                classifier_match = "OK" if result.classifier_correct else "MISMATCH"
                msg = "[{}/{}] {}: {} [{}->{}:{}] ({:.1f}s, ${:.4f})".format(
                    batch_status["completed"], batch_status["total"],
                    result.question_name, status,
                    result.ground_truth_dimension, result.detected_dimension, classifier_match,
                    result.total_duration, result.total_cost,
                )
                if not result.success:
                    if result.classify.error:
                        msg += "\n  -> Classify error: {}".format(result.classify.error[:120])
                    elif result.blueprint.error:
                        msg += "\n  -> Blueprint error: {}".format(result.blueprint.error[:120])
                    elif result.codegen.error:
                        msg += "\n  -> CodeGen error: {}".format(result.codegen.error[:120])
                    elif result.execution.error:
                        err_lines = result.execution.error.strip().split("\n")
                        last_err = err_lines[-1] if err_lines else "Unknown"
                        msg += "\n  -> Execution error: {}".format(last_err[:120])
                print(msg)
            except Exception as e:
                print("Error processing {}: {}".format(q_id, e))
                batch_status["completed"] += 1

    batch_status["running"] = False
    total_time = time.time() - batch_status["start_time"]
    total_cost = sum(r.total_cost for r in results.values())
    success_count = sum(1 for r in results.values() if r.success)
    classifier_correct = sum(1 for r in results.values() if r.classifier_correct)
    classifier_total = sum(1 for r in results.values() if r.classify.success)

    print("\n" + "=" * 60)
    print("BATCH COMPLETE: {}/{} successful".format(success_count, len(questions)))
    print("Classifier accuracy: {}/{} ({:.0f}%)".format(
        classifier_correct, classifier_total,
        (classifier_correct / classifier_total * 100) if classifier_total > 0 else 0,
    ))
    print("Total time: {:.1f}s".format(total_time))
    print("Total cost: ${:.4f}".format(total_cost))
    print("=" * 60 + "\n")


def start_batch_thread(max_workers=5):
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

    # Classifier accuracy
    classifier_correct = sum(1 for r in results.values() if r.classifier_correct)
    classifier_total = sum(1 for r in results.values() if r.classify.success)

    results_list = []
    for q in ALL_QUESTIONS:
        if q["id"] in results:
            r = results[q["id"]]
            results_list.append({
                "id": r.question_id,
                "name": r.question_name,
                "text": r.question_text,
                "dimension": r.dimension,
                "ground_truth": r.ground_truth_dimension,
                "detected": r.detected_dimension,
                "classifier_correct": r.classifier_correct,
                "test_set": r.test_set,
                "success": r.success,
                "total_duration": round(r.total_duration, 1),
                "total_cost": round(r.total_cost, 6),
                "output_path": r.output_path,
                "classify": {
                    "success": r.classify.success,
                    "duration": round(r.classify.duration, 1),
                    "tokens": r.classify.total_tokens,
                    "prompt_tokens": r.classify.prompt_tokens,
                    "completion_tokens": r.classify.completion_tokens,
                    "cost": round(r.classify.cost, 6),
                    "error": r.classify.error,
                },
                "blueprint": {
                    "success": r.blueprint.success,
                    "duration": round(r.blueprint.duration, 1),
                    "tokens": r.blueprint.total_tokens,
                    "prompt_tokens": r.blueprint.prompt_tokens,
                    "completion_tokens": r.blueprint.completion_tokens,
                    "cost": round(r.blueprint.cost, 6),
                    "error": r.blueprint.error,
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
                "ground_truth": q.get("dimension", ""),
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
        "classifier_accuracy": {
            "correct": classifier_correct,
            "total": classifier_total,
            "rate": round(classifier_correct / classifier_total * 100, 1) if classifier_total > 0 else 0,
        },
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
<title>Focused Pipeline - 4-Stage Batch Test</title>
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
.summary-card.accuracy{border-color:#E9C46A;background:#1a1a10}

.model-breakdown{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1.5rem}
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

.results-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(450px,1fr));gap:1rem}
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
.badge-coordinate_2d{background:#2A9D8F;color:#fff}
.badge-coordinate_3d{background:#E76F51;color:#fff}
.badge-pending{background:#333;color:#888}
.badge-success{background:#96CEB4;color:#0C0C0C}
.badge-failed{background:#FF6B6B;color:#fff}
.badge-hkdse{background:#264653;color:#ccc;font-weight:400;font-size:.65rem}
.badge-coordinate{background:#2a3a2a;color:#ccc;font-weight:400;font-size:.65rem}
.classifier-match{font-size:.7rem;padding:.1rem .4rem;border-radius:3px;font-weight:600}
.classifier-ok{background:#1a3a2a;color:#96CEB4}
.classifier-miss{background:#3a1a1a;color:#FF6B6B}

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
  <h1>Focused Pipeline - 4-Stage Batch Test</h1>
  <p class="subtitle">Classify &rarr; Blueprint &rarr; CodeGen &rarr; Execute | Gemini 3 Flash + DeepSeek-V3.2</p>
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
  <button class="filter-btn" onclick="filterDim('coordinate_2d')">Coord 2D</button>
  <button class="filter-btn" onclick="filterDim('coordinate_3d')">Coord 3D</button>
  <span class="filter-sep">|</span>
  <button class="filter-btn active" onclick="filterSet('all')">All Sets</button>
  <button class="filter-btn" onclick="filterSet('hkdse')">HKDSE</button>
  <button class="filter-btn" onclick="filterSet('coordinate')">Coordinate</button>
</div>

<div class="summary">
  <div class="summary-card">
    <div class="value" id="success-rate">0%</div>
    <div class="label">Success Rate</div>
  </div>
  <div class="summary-card accuracy">
    <div class="value" id="classifier-accuracy">0%</div>
    <div class="label">Classifier Accuracy</div>
    <div class="sub-value" id="classifier-detail">0/0</div>
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
    <div class="model-panel-title">Classify <span class="model-tag">Gemini 3 Flash</span></div>
    <div class="token-row">
      <span class="token-label">Input Tokens</span>
      <span><span class="token-val" id="cl-input-tokens">0</span><span class="token-cost" id="cl-input-cost">$0.0000</span></span>
    </div>
    <div class="token-row">
      <span class="token-label">Output Tokens</span>
      <span><span class="token-val" id="cl-output-tokens">0</span><span class="token-cost" id="cl-output-cost">$0.0000</span></span>
    </div>
    <div class="model-total">
      <span class="token-label">Total</span>
      <span class="token-val" id="cl-total-cost">$0.0000</span>
    </div>
  </div>
  <div class="model-panel">
    <div class="model-panel-title">Blueprint <span class="model-tag">Gemini 3 Flash</span></div>
    <div class="token-row">
      <span class="token-label">Input Tokens</span>
      <span><span class="token-val" id="bp-input-tokens">0</span><span class="token-cost" id="bp-input-cost">$0.0000</span></span>
    </div>
    <div class="token-row">
      <span class="token-label">Output Tokens</span>
      <span><span class="token-val" id="bp-output-tokens">0</span><span class="token-cost" id="bp-output-cost">$0.0000</span></span>
    </div>
    <div class="model-total">
      <span class="token-label">Total</span>
      <span class="token-val" id="bp-total-cost">$0.0000</span>
    </div>
  </div>
  <div class="model-panel">
    <div class="model-panel-title">CodeGen <span class="model-tag">DeepSeek-V3.2</span></div>
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
  // Only update dim buttons (first 5)
  for (var i = 0; i < 5; i++) {
    btns[i].classList.remove('active');
  }
  event.target.classList.add('active');
  renderResults(latestResults);
}

function filterSet(set) {
  currentSetFilter = set;
  var btns = document.querySelectorAll('.filters .filter-btn');
  // Update set buttons (index 5,6,7 after separator)
  for (var i = 6; i < btns.length; i++) {
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

  // Classifier accuracy
  var ca = data.classifier_accuracy || {};
  document.getElementById('classifier-accuracy').textContent = (ca.rate || 0) + '%';
  document.getElementById('classifier-detail').textContent = (ca.correct || 0) + '/' + (ca.total || 0);

  // Throughput
  var throughput = data.elapsed > 0 ? ((data.completed / data.elapsed) * 60).toFixed(1) : '0.0';
  document.getElementById('throughput').textContent = throughput;

  // Pricing
  var clInputPrice = data.pricing ? data.pricing.classify.input : 0.50;
  var clOutputPrice = data.pricing ? data.pricing.classify.output : 3.00;
  var bpInputPrice = data.pricing ? data.pricing.blueprint.input : 0.50;
  var bpOutputPrice = data.pricing ? data.pricing.blueprint.output : 3.00;
  var cgInputPrice = data.pricing ? data.pricing.codegen.input : 0.28;
  var cgOutputPrice = data.pricing ? data.pricing.codegen.output : 0.42;

  // Calculate totals
  var inputTokens = 0, outputTokens = 0, inputCost = 0, outputCost = 0;
  var clIn = 0, clOut = 0, bpIn = 0, bpOut = 0, cgIn = 0, cgOut = 0;

  data.results.forEach(function(r) {
    if (r.classify) {
      clIn += r.classify.prompt_tokens || 0;
      clOut += r.classify.completion_tokens || 0;
    }
    if (r.blueprint) {
      bpIn += r.blueprint.prompt_tokens || 0;
      bpOut += r.blueprint.completion_tokens || 0;
    }
    if (r.codegen) {
      cgIn += r.codegen.prompt_tokens || 0;
      cgOut += r.codegen.completion_tokens || 0;
    }
  });

  inputTokens = clIn + bpIn + cgIn;
  outputTokens = clOut + bpOut + cgOut;
  inputCost = (clIn / 1e6) * clInputPrice + (bpIn / 1e6) * bpInputPrice + (cgIn / 1e6) * cgInputPrice;
  outputCost = (clOut / 1e6) * clOutputPrice + (bpOut / 1e6) * bpOutputPrice + (cgOut / 1e6) * cgOutputPrice;

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
  var clInCost = (clIn / 1e6) * clInputPrice;
  var clOutCost = (clOut / 1e6) * clOutputPrice;
  var bpInCost = (bpIn / 1e6) * bpInputPrice;
  var bpOutCost = (bpOut / 1e6) * bpOutputPrice;
  var cgInCost = (cgIn / 1e6) * cgInputPrice;
  var cgOutCost = (cgOut / 1e6) * cgOutputPrice;

  document.getElementById('cl-input-tokens').textContent = clIn.toLocaleString();
  document.getElementById('cl-output-tokens').textContent = clOut.toLocaleString();
  document.getElementById('cl-input-cost').textContent = '$' + clInCost.toFixed(4);
  document.getElementById('cl-output-cost').textContent = '$' + clOutCost.toFixed(4);
  document.getElementById('cl-total-cost').textContent = '$' + (clInCost + clOutCost).toFixed(4);

  document.getElementById('bp-input-tokens').textContent = bpIn.toLocaleString();
  document.getElementById('bp-output-tokens').textContent = bpOut.toLocaleString();
  document.getElementById('bp-input-cost').textContent = '$' + bpInCost.toFixed(4);
  document.getElementById('bp-output-cost').textContent = '$' + bpOutCost.toFixed(4);
  document.getElementById('bp-total-cost').textContent = '$' + (bpInCost + bpOutCost).toFixed(4);

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
    var groundTruth = r.ground_truth || '';
    var testSet = r.test_set || '';
    if (currentDimFilter !== 'all' && groundTruth !== currentDimFilter) return;
    if (currentSetFilter !== 'all' && testSet !== currentSetFilter) return;

    var card = document.createElement('div');
    card.className = 'result-card ' + (r.pending ? 'pending' : (r.success ? 'success' : 'failed'));

    var dimBadge = r.dimension ?
      '<span class="card-badge badge-' + r.dimension + '">' + r.dimension.replace('_', ' ').toUpperCase() + '</span>' :
      (r.ground_truth ? '<span class="card-badge badge-' + r.ground_truth + '">' + r.ground_truth.replace('_', ' ').toUpperCase() + '</span>' :
      '<span class="card-badge badge-pending">PENDING</span>');

    var statusBadge = r.pending ? '' :
      (r.success ? '<span class="card-badge badge-success">SUCCESS</span>' :
                   '<span class="card-badge badge-failed">FAILED</span>');

    var setBadge = testSet ? '<span class="card-badge badge-' + testSet + '">' + testSet.toUpperCase() + '</span>' : '';

    var classifierBadge = '';
    if (!r.pending && r.classify) {
      if (r.classifier_correct) {
        classifierBadge = '<span class="classifier-match classifier-ok" title="Detected: ' + (r.detected || '') + ' | Truth: ' + (r.ground_truth || '') + '">&#10003;</span>';
      } else if (r.classify.success) {
        classifierBadge = '<span class="classifier-match classifier-miss" title="Detected: ' + (r.detected || '') + ' | Truth: ' + (r.ground_truth || '') + '">&#10007; ' + (r.detected || '') + '</span>';
      }
    }

    var stagesHtml = '';
    if (!r.pending) {
      var clClass = r.classify && r.classify.success ? 'done' : (r.classify && r.classify.error ? 'error' : '');
      var bpClass = r.blueprint && r.blueprint.success ? 'done' : (r.blueprint && r.blueprint.error ? 'error' : '');
      var cgClass = r.codegen && r.codegen.success ? 'done' : (r.codegen && r.codegen.error ? 'error' : '');
      var exClass = r.execution && r.execution.success ? 'done' : (r.execution && r.execution.error ? 'error' : '');

      stagesHtml = '<div class="stages">' +
        '<div class="stage ' + clClass + '"><div class="stage-name">Classify</div><div class="stage-info">' +
          (r.classify ? r.classify.duration || 0 : 0) + 's</div></div>' +
        '<div class="stage ' + bpClass + '"><div class="stage-name">Blueprint</div><div class="stage-info">' +
          (r.blueprint ? r.blueprint.duration || 0 : 0) + 's</div></div>' +
        '<div class="stage ' + cgClass + '"><div class="stage-name">CodeGen</div><div class="stage-info">' +
          (r.codegen ? r.codegen.duration || 0 : 0) + 's</div></div>' +
        '<div class="stage ' + exClass + '"><div class="stage-name">Execute</div><div class="stage-info">' +
          (r.execution ? r.execution.duration || 0 : 0) + 's</div></div>' +
        '</div>';
    }

    var statsHtml = '';
    if (!r.pending) {
      var inTok = (r.classify ? r.classify.prompt_tokens || 0 : 0) +
                  (r.blueprint ? r.blueprint.prompt_tokens || 0 : 0) +
                  (r.codegen ? r.codegen.prompt_tokens || 0 : 0);
      var outTok = (r.classify ? r.classify.completion_tokens || 0 : 0) +
                   (r.blueprint ? r.blueprint.completion_tokens || 0 : 0) +
                   (r.codegen ? r.codegen.completion_tokens || 0 : 0);
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
        '<span class="card-badges">' + setBadge + ' ' + dimBadge + ' ' + classifierBadge + ' ' + statusBadge + '</span>' +
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
        description="Focused 4-Stage Batch Test (Classify + Blueprint + CodeGen + Execute)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
40 questions total (10 per dimension type):
  HKDSE 2D (10)         - Traditional 2D geometry
  HKDSE 3D (10)         - Traditional 3D geometry
  Coordinate 2D (10)    - 2D coordinate geometry with axes
  Coordinate 3D (10)    - 3D coordinate geometry with axes

Pipeline: Classify (Gemini) -> Blueprint (Gemini) -> CodeGen (DeepSeek) -> Execute

Examples:
  python3 batch_test_focused.py                              # Run all 40 questions
  python3 batch_test_focused.py --dim 3d                     # Run only 3D questions (20)
  python3 batch_test_focused.py --dim coordinate_2d          # Run only coordinate 2D (10)
  python3 batch_test_focused.py --test-set hkdse             # Run only HKDSE (20)
  python3 batch_test_focused.py --test-set coordinate        # Run only coordinate (20)
  python3 batch_test_focused.py --workers 3                  # Limit concurrency
        """
    )
    parser.add_argument(
        "--dim",
        choices=["2d", "3d", "coordinate_2d", "coordinate_3d", "all"],
        default="all",
        help="Filter by dimension type (default: all)"
    )
    parser.add_argument(
        "--test-set",
        choices=["hkdse", "coordinate", "all"],
        default="all",
        help="Filter by test set source (default: all)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="Port for the web UI (default: 5001)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of concurrent workers (default: 5)"
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
    for q in ALL_QUESTIONS:
        d = q.get("dimension", "unknown")
        dim_counts[d] = dim_counts.get(d, 0) + 1

    # Clean up previous batch output
    batch_dir = SCRIPT_DIR / "output" / "batch"
    if batch_dir.exists():
        shutil.rmtree(str(batch_dir))

    port = args.port
    url = "http://127.0.0.1:{}".format(port)

    print("=" * 60)
    print("Focused 4-Stage Batch Test")
    print("=" * 60)
    print("URL: {}".format(url))
    print("Questions: {}".format(len(ALL_QUESTIONS)))
    for d, c in sorted(dim_counts.items()):
        print("  {}: {}".format(d, c))
    print("Pipeline: Classify (Gemini) -> Blueprint (Gemini) -> CodeGen (DeepSeek-V3.2) -> Execute")
    print("Workers: {}".format(MAX_WORKERS))
    print("=" * 60)

    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
