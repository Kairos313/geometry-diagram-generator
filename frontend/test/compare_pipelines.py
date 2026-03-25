#!/usr/bin/env python3
"""
A/B/C Pipeline Comparison Test.

Runs the same 10 HKDSE questions through 3 different pipelines and generates
a side-by-side comparison gallery.

Pipeline A: New math prompt (text notes) → DeepSeek JS
Pipeline B: Old adaptive blueprint (JSON) → DeepSeek JS (JSON passed directly)
Pipeline C: Old adaptive blueprint (JSON) → convert to text notes → DeepSeek JS

Usage:
    python3 frontend/test/compare_pipelines.py
    python3 frontend/test/compare_pipelines.py --workers 10
    python3 frontend/test/compare_pipelines.py --condition B   # Run only condition B
"""

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

# Setup paths
TEST_DIR = Path(__file__).parent
FRONTEND_DIR = TEST_DIR.parent
ROOT_DIR = FRONTEND_DIR.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(FRONTEND_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
for name in ["httpx", "httpcore", "google", "google_genai", "openai",
             "generate_js_pipeline", "generate_code_js", "classify_geometry_type"]:
    logging.getLogger(name).setLevel(logging.WARNING)

from hkdse_new_questions import HKDSE_NEW_QUESTIONS

# DeepSeek config
DEEPSEEK_ENDPOINT = "https://raksh-m4jj47jc-japaneast.services.ai.azure.com/openai/v1/"
DEEPSEEK_MODEL = "DeepSeek-V3.2"


# ======================================================================
# Pipeline A: New math prompt → DeepSeek JS (current pipeline)
# ======================================================================

def run_pipeline_a(question, output_dir):
    # type: (dict, str) -> dict
    """Current pipeline: new Gemini math prompt → DeepSeek JS."""
    from generate_js_pipeline import generate_diagram

    qid = question["id"]
    output_path = os.path.join(output_dir, qid, "diagram.html")

    result = generate_diagram(
        question["text"],
        question.get("dimension", "auto"),
        output_path,
        max_retries=1,
    )

    return {
        "question_id": qid,
        "pipeline": "A",
        "success": result["success"],
        "duration": result["duration"],
        "tokens": result.get("tokens", {}),
        "error": result.get("error"),
        "output_path": output_path,
        "math_notes": result.get("math_notes", ""),
    }


# ======================================================================
# Pipeline B: Old adaptive blueprint (JSON) → DeepSeek JS
# ======================================================================

def generate_old_blueprint(question_text, dimension_type, api_key=None):
    # type: (str, str, Optional[str]) -> dict
    """Call Gemini with the OLD adaptive blueprint prompt to get JSON blueprint."""
    from individual_prompts import get_adaptive_blueprint_prompt
    from google import genai
    from google.genai import types

    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)
    prompt = get_adaptive_blueprint_prompt(dimension_type)

    user_message = "Question: {}".format(question_text)

    start = time.time()
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[
            {"role": "user", "parts": [{"text": prompt + "\n\n" + user_message}]}
        ],
        config={
            "max_output_tokens": 40000,
            "temperature": 0.1,
            "thinking_config": types.ThinkingConfig(thinking_budget=8000),
        },
    )
    duration = time.time() - start

    raw = ""
    if response.candidates and response.candidates[0].content:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                raw += part.text

    tokens = {}
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        um = response.usage_metadata
        tokens = {
            "total": getattr(um, "total_token_count", 0) or 0,
        }

    # Extract JSON from response
    import re
    json_match = re.search(r'\{[\s\S]*\}', raw)
    blueprint_json = json_match.group(0) if json_match else raw

    return {
        "success": bool(json_match),
        "blueprint": blueprint_json,
        "duration": duration,
        "tokens": tokens,
        "error": None if json_match else "No JSON found in response",
    }


def run_pipeline_b(question, output_dir):
    # type: (dict, str) -> dict
    """Old blueprint (JSON) passed directly to DeepSeek JS prompt."""
    from generate_code_js import extract_html, postprocess_js
    from js_pipeline_prompts import get_js_prompt
    from openai import OpenAI

    qid = question["id"]
    dim = question.get("dimension", "2d").replace("coordinate_", "")
    output_path = os.path.join(output_dir, qid, "diagram.html")

    start = time.time()

    # Stage 1: Get old blueprint
    bp_result = generate_old_blueprint(question["text"], dim)
    if not bp_result["success"]:
        return {
            "question_id": qid, "pipeline": "B", "success": False,
            "duration": time.time() - start, "tokens": {"gemini": bp_result["tokens"]},
            "error": "Blueprint failed: " + str(bp_result["error"]),
            "output_path": output_path, "blueprint": "",
        }

    blueprint = bp_result["blueprint"]

    # Stage 2: Pass JSON blueprint directly to DeepSeek JS prompt
    api_key = os.getenv("DEEPSEEK_API_KEY")
    client = OpenAI(base_url=DEEPSEEK_ENDPOINT, api_key=api_key)
    system_prompt = get_js_prompt(dim)

    user_message = (
        "=== ORIGINAL QUESTION ===\n"
        "{q}\n\n"
        "=== GEOMETRY BLUEPRINT (JSON) ===\n"
        "{bp}\n"
        "=== END ===\n\n"
        "Use the coordinates and elements from the JSON blueprint above to render the diagram."
    ).format(q=question["text"], bp=blueprint)

    ds_start = time.time()
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=16384,
        temperature=0.0,
    )
    ds_duration = time.time() - ds_start

    content = response.choices[0].message.content or ""
    ds_tokens = {
        "total": response.usage.total_tokens if response.usage else 0,
    }

    html = extract_html(content)
    if not html:
        return {
            "question_id": qid, "pipeline": "B", "success": False,
            "duration": time.time() - start, "tokens": {"gemini": bp_result["tokens"], "deepseek": ds_tokens},
            "error": "No HTML in DeepSeek response", "output_path": output_path, "blueprint": blueprint,
        }

    html = postprocess_js(html)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html, encoding="utf-8")

    return {
        "question_id": qid, "pipeline": "B", "success": True,
        "duration": time.time() - start,
        "tokens": {"gemini": bp_result["tokens"], "deepseek": ds_tokens},
        "error": None, "output_path": output_path, "blueprint": blueprint,
    }


# ======================================================================
# Pipeline C: Old blueprint → convert to text notes → DeepSeek JS
# ======================================================================

def blueprint_json_to_notes(blueprint_str, question_text):
    # type: (str, str) -> str
    """Convert a JSON blueprint to the text computation notes format."""
    try:
        bp = json.loads(blueprint_str)
    except json.JSONDecodeError:
        return "DIMENSION: 2D\nTITLE: Unknown\n\nRAW BLUEPRINT:\n" + blueprint_str

    dim = bp.get("dimension", "2d").upper()
    lines = []
    lines.append("DIMENSION: {}".format(dim))
    lines.append("TITLE: Geometry Diagram")
    lines.append("")

    # COORDINATES
    lines.append("COORDINATES:")
    points = bp.get("points", {})
    for name, coords in points.items():
        if len(coords) == 3 and abs(coords[2]) < 0.001:
            lines.append("{} = ({}, {})".format(name, coords[0], coords[1]))
        else:
            lines.append("{} = ({}, {}, {})".format(name, coords[0], coords[1], coords[2]))
    lines.append("")

    # ELEMENTS
    lines.append("ELEMENTS:")
    for line in bp.get("lines", []):
        style = line.get("style", "solid")
        lines.append("- Segment {} to {} ({})".format(line["from"], line["to"], style))

    for circle in bp.get("circles", []):
        lines.append("- Circle center={} radius={}".format(circle["center"], circle["radius"]))

    for face in bp.get("faces", []):
        pts = " ".join(face.get("points", []))
        lines.append("- Face {} (translucent)".format(pts))
    lines.append("")

    # ANGLES
    angles = bp.get("angles", [])
    if angles:
        lines.append("ANGLES:")
        asked = bp.get("asked", [])
        for angle in angles:
            v = angle.get("vertex", "?")
            p1 = angle.get("p1", "?")
            p2 = angle.get("p2", "?")
            val = angle.get("value")
            aid = angle.get("id", "")
            if aid in asked:
                lines.append("- Angle at {} between {}{} and {}{} = ? (asked, highlight)".format(
                    v, v, p1, v, p2))
            elif val is not None:
                lines.append("- Angle at {} between {}{} and {}{} = {} degrees".format(
                    v, v, p1, v, p2, val))
        lines.append("")

    # LABELS
    given = bp.get("given", {})
    asked = bp.get("asked", [])
    if given or asked:
        lines.append("LABELS:")
        for key, val in given.items():
            lines.append('- {}: "{}"'.format(key, val))
        for key in asked:
            lines.append('- {}: "?" (asked, highlight)'.format(key))
        lines.append("")

    # GIVEN / ASKED
    if given:
        lines.append("GIVEN:")
        for key, val in given.items():
            lines.append("- {} = {}".format(key, val))
        lines.append("")

    if asked:
        lines.append("ASKED:")
        for key in asked:
            lines.append("- {}".format(key))
        lines.append("")

    # COORDINATE_SYSTEM
    axes = bp.get("axes", False)
    lines.append("COORDINATE_SYSTEM:")
    lines.append("- axes: {}".format("true" if axes else "false"))
    if axes:
        cr = bp.get("coordinate_range", {})
        lines.append("- x_range: [{}, {}]".format(cr.get("x_min", -10), cr.get("x_max", 10)))
        lines.append("- y_range: [{}, {}]".format(cr.get("y_min", -10), cr.get("y_max", 10)))
        lines.append("- grid: {}".format("true" if bp.get("grid", False) else "false"))
    lines.append("")

    lines.append("INTERACTIVE:")
    lines.append("- none")

    return "\n".join(lines)


def run_pipeline_c(question, output_dir):
    # type: (dict, str) -> dict
    """Old blueprint → convert to text notes → DeepSeek JS."""
    from generate_code_js import extract_html, postprocess_js
    from js_pipeline_prompts import get_js_prompt
    from openai import OpenAI

    qid = question["id"]
    dim = question.get("dimension", "2d").replace("coordinate_", "")
    output_path = os.path.join(output_dir, qid, "diagram.html")

    start = time.time()

    # Stage 1: Get old blueprint
    bp_result = generate_old_blueprint(question["text"], dim)
    if not bp_result["success"]:
        return {
            "question_id": qid, "pipeline": "C", "success": False,
            "duration": time.time() - start, "tokens": {"gemini": bp_result["tokens"]},
            "error": "Blueprint failed: " + str(bp_result["error"]),
            "output_path": output_path, "notes": "",
        }

    blueprint = bp_result["blueprint"]

    # Stage 2: Convert JSON → text notes
    notes = blueprint_json_to_notes(blueprint, question["text"])

    # Stage 3: Pass notes to DeepSeek JS prompt (same as Pipeline A stage 3)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    client = OpenAI(base_url=DEEPSEEK_ENDPOINT, api_key=api_key)
    system_prompt = get_js_prompt(dim)

    user_message = (
        "=== ORIGINAL QUESTION ===\n"
        "{q}\n\n"
        "=== COMPUTATION NOTES ===\n"
        "{notes}\n"
        "=== END ==="
    ).format(q=question["text"], notes=notes)

    ds_start = time.time()
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=16384,
        temperature=0.0,
    )
    ds_duration = time.time() - ds_start

    content = response.choices[0].message.content or ""
    ds_tokens = {
        "total": response.usage.total_tokens if response.usage else 0,
    }

    html = extract_html(content)
    if not html:
        return {
            "question_id": qid, "pipeline": "C", "success": False,
            "duration": time.time() - start, "tokens": {"gemini": bp_result["tokens"], "deepseek": ds_tokens},
            "error": "No HTML in DeepSeek response", "output_path": output_path, "notes": notes,
        }

    html = postprocess_js(html)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html, encoding="utf-8")

    return {
        "question_id": qid, "pipeline": "C", "success": True,
        "duration": time.time() - start,
        "tokens": {"gemini": bp_result["tokens"], "deepseek": ds_tokens},
        "error": None, "output_path": output_path, "notes": notes,
    }


# ======================================================================
# Gallery Generator
# ======================================================================

def generate_comparison_gallery(results_a, results_b, results_c, questions, output_path):
    # type: (list, list, list, list, str) -> None
    """Generate a side-by-side comparison gallery."""

    def get_result(results, qid):
        return next((r for r in results if r["question_id"] == qid), None)

    def card_html(r, pipeline_label, base_dir):
        if not r:
            return '<div class="cell empty">Not run</div>'

        status_class = "pass" if r["success"] else "fail"
        status_text = "PASS" if r["success"] else "FAIL"

        # Token counts
        tokens = r.get("tokens", {})
        g_tok = 0
        d_tok = 0
        if isinstance(tokens, dict):
            g = tokens.get("gemini", tokens.get("gemini_math", {}))
            d = tokens.get("deepseek", tokens.get("deepseek_js", {}))
            g_tok = g.get("total", 0) if isinstance(g, dict) else 0
            d_tok = d.get("total", 0) if isinstance(d, dict) else 0

        iframe_html = ""
        if r["success"] and r.get("output_path"):
            rel = os.path.relpath(r["output_path"], os.path.dirname(output_path))
            iframe_html = '<iframe src="{}" loading="lazy"></iframe>'.format(rel)
        elif r.get("error"):
            iframe_html = '<div class="error">{}</div>'.format(str(r["error"])[:150])

        return """<div class="cell {sc}">
            <div class="cell-header">
                <span class="pipeline-label">{pl}</span>
                <span class="status-{sc}">{st}</span>
            </div>
            <div class="cell-render">{iframe}</div>
            <div class="cell-stats">{dur:.1f}s | G:{gt} D:{dt}</div>
        </div>""".format(
            sc=status_class, pl=pipeline_label, st=status_text,
            iframe=iframe_html, dur=r["duration"], gt=g_tok, dt=d_tok,
        )

    rows_html = []
    for q in questions:
        qid = q["id"]
        ra = get_result(results_a, qid)
        rb = get_result(results_b, qid)
        rc = get_result(results_c, qid)

        row = """
        <div class="row">
            <div class="row-header">
                <strong>{name}</strong>
                <span class="qid">{qid}</span>
                <span class="dim-badge">{dim}</span>
                <p class="q-text">{text}</p>
            </div>
            <div class="row-cells">
                {cell_a}
                {cell_b}
                {cell_c}
            </div>
        </div>""".format(
            name=q["name"], qid=qid, dim=q.get("dimension", "?"),
            text=q["text"][:150],
            cell_a=card_html(ra, "A: New Math Prompt", "pipeline_a"),
            cell_b=card_html(rb, "B: Old Blueprint (JSON)", "pipeline_b"),
            cell_c=card_html(rc, "C: Old Blueprint → Notes", "pipeline_c"),
        )
        rows_html.append(row)

    # Summary stats
    def summarize(results):
        total = len(results)
        passed = sum(1 for r in results if r["success"])
        avg_dur = sum(r["duration"] for r in results) / total if total else 0
        return {"total": total, "passed": passed, "avg_dur": avg_dur}

    sa = summarize(results_a) if results_a else {"total": 0, "passed": 0, "avg_dur": 0}
    sb = summarize(results_b) if results_b else {"total": 0, "passed": 0, "avg_dur": 0}
    sc = summarize(results_c) if results_c else {"total": 0, "passed": 0, "avg_dur": 0}

    html = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>Pipeline A/B/C Comparison</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0C0C0C;color:#e0e0e0;font-family:-apple-system,monospace}}
.container{{max-width:1800px;margin:0 auto;padding:1.5rem}}
h1{{color:#4ECDC4;text-align:center;margin-bottom:.5rem}}
.subtitle{{text-align:center;color:#888;margin-bottom:1.5rem;font-size:.85rem}}
.summary{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:2rem}}
.summary-card{{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:6px;padding:1rem;text-align:center}}
.summary-card h3{{color:#4ECDC4;font-size:.85rem;margin-bottom:.5rem}}
.summary-card .val{{font-size:1.4rem;color:#e0e0e0;font-weight:700}}
.summary-card .sub{{color:#888;font-size:.8rem}}
.col-headers{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:.5rem;padding-left:0}}
.col-headers div{{background:#1a2a2a;color:#4ECDC4;padding:.5rem;border-radius:4px;text-align:center;font-weight:700;font-size:.85rem}}
.row{{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;margin-bottom:1rem;overflow:hidden}}
.row-header{{padding:.75rem 1rem;border-bottom:1px solid #2a2a2a}}
.row-header strong{{color:#e0e0e0}}
.qid{{color:#666;font-size:.75rem;margin-left:.5rem;font-family:monospace}}
.dim-badge{{background:#457B9D;color:#fff;padding:.1rem .4rem;border-radius:3px;font-size:.7rem;margin-left:.5rem}}
.q-text{{color:#888;font-size:.8rem;margin-top:.25rem}}
.row-cells{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0}}
.cell{{border-right:1px solid #2a2a2a;padding:.5rem}}
.cell:last-child{{border-right:none}}
.cell-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;font-size:.8rem}}
.pipeline-label{{color:#888;font-size:.75rem}}
.status-pass{{color:#96CEB4;font-weight:700}}
.status-fail{{color:#FF6B6B;font-weight:700}}
.cell-render{{height:350px;background:#0C0C0C;border-radius:4px;overflow:hidden}}
.cell-render iframe{{width:100%;height:100%;border:none}}
.cell-stats{{font-size:.75rem;color:#666;margin-top:.25rem;text-align:center}}
.cell.empty{{display:flex;align-items:center;justify-content:center;color:#555;font-style:italic}}
.error{{color:#FF6B6B;font-size:.75rem;padding:.5rem}}
</style>
</head><body>
<div class="container">
<h1>Pipeline A/B/C Comparison</h1>
<p class="subtitle">A: New Math Prompt | B: Old Blueprint (JSON direct) | C: Old Blueprint → Notes Conversion</p>

<div class="summary">
    <div class="summary-card">
        <h3>A: New Math Prompt</h3>
        <div class="val">{sa_pass}/{sa_total}</div>
        <div class="sub">Avg {sa_dur:.1f}s per diagram</div>
    </div>
    <div class="summary-card">
        <h3>B: Old Blueprint (JSON)</h3>
        <div class="val">{sb_pass}/{sb_total}</div>
        <div class="sub">Avg {sb_dur:.1f}s per diagram</div>
    </div>
    <div class="summary-card">
        <h3>C: Old Blueprint → Notes</h3>
        <div class="val">{sc_pass}/{sc_total}</div>
        <div class="sub">Avg {sc_dur:.1f}s per diagram</div>
    </div>
</div>

<div class="col-headers">
    <div>A: New Math Prompt (Gemini)</div>
    <div>B: Old Blueprint JSON → DeepSeek</div>
    <div>C: Old Blueprint → Notes → DeepSeek</div>
</div>

{rows}
</div>
</body></html>""".format(
        sa_pass=sa["passed"], sa_total=sa["total"], sa_dur=sa["avg_dur"],
        sb_pass=sb["passed"], sb_total=sb["total"], sb_dur=sb["avg_dur"],
        sc_pass=sc["passed"], sc_total=sc["total"], sc_dur=sc["avg_dur"],
        rows="\n".join(rows_html),
    )

    Path(output_path).write_text(html, encoding="utf-8")
    logger.info("Comparison gallery saved to {}".format(output_path))


# ======================================================================
# Main
# ======================================================================

def run_condition(condition, questions, output_base, max_workers):
    # type: (str, list, str, int) -> list
    """Run a single condition (A, B, or C) for all questions."""
    output_dir = os.path.join(output_base, "pipeline_{}".format(condition.lower()))

    runner = {"A": run_pipeline_a, "B": run_pipeline_b, "C": run_pipeline_c}[condition]

    results = []
    total = len(questions)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(runner, q, output_dir): q for q in questions}
        for i, f in enumerate(as_completed(futs), 1):
            q = futs[f]
            try:
                r = f.result()
                status = "PASS" if r["success"] else "FAIL"
                print("[{}/{}] Pipeline {} | {} {} ({:.1f}s) {}".format(
                    i, total, condition, status, r["question_id"],
                    r["duration"], r.get("error", "") if not r["success"] else ""
                ))
                results.append(r)
            except Exception as e:
                print("[{}/{}] Pipeline {} | CRASH {} - {}".format(
                    i, total, condition, q["id"], e))
                results.append({
                    "question_id": q["id"], "pipeline": condition,
                    "success": False, "duration": 0, "tokens": {},
                    "error": str(e), "output_path": "",
                })

    results.sort(key=lambda r: r["question_id"])
    return results


def main():
    parser = argparse.ArgumentParser(description="A/B/C Pipeline Comparison")
    parser.add_argument("--workers", type=int, default=10,
                        help="Workers per condition (default: 10)")
    parser.add_argument("--condition", choices=["A", "B", "C", "all"], default="all",
                        help="Which condition(s) to run (default: all)")
    parser.add_argument("--output-dir", default=str(TEST_DIR / "output"),
                        help="Output directory")
    parser.add_argument("--gallery", default=str(TEST_DIR / "comparison_gallery.html"),
                        help="Gallery output path")
    args = parser.parse_args()

    questions = HKDSE_NEW_QUESTIONS
    print("Running {} questions x {} condition(s) with {} workers each\n".format(
        len(questions),
        "3" if args.condition == "all" else "1",
        args.workers,
    ))

    results_a, results_b, results_c = [], [], []
    wall_start = time.time()

    if args.condition in ("A", "all"):
        print("\n=== PIPELINE A: New Math Prompt ===")
        results_a = run_condition("A", questions, args.output_dir, args.workers)

    if args.condition in ("B", "all"):
        print("\n=== PIPELINE B: Old Blueprint (JSON) ===")
        results_b = run_condition("B", questions, args.output_dir, args.workers)

    if args.condition in ("C", "all"):
        print("\n=== PIPELINE C: Old Blueprint → Notes ===")
        results_c = run_condition("C", questions, args.output_dir, args.workers)

    wall_time = time.time() - wall_start

    # Generate gallery
    generate_comparison_gallery(results_a, results_b, results_c, questions, args.gallery)

    # Save raw results
    all_results = {
        "A": results_a,
        "B": results_b,
        "C": results_c,
    }
    results_path = os.path.join(args.output_dir, "comparison_results.json")
    Path(results_path).parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)
    for label, res in [("A (New Math)", results_a), ("B (Old JSON)", results_b), ("C (Old→Notes)", results_c)]:
        if res:
            p = sum(1 for r in res if r["success"])
            avg = sum(r["duration"] for r in res) / len(res) if res else 0
            print("  {}: {}/{} pass | avg {:.1f}s".format(label, p, len(res), avg))
    print("Wall time: {:.1f}s".format(wall_time))
    print("Gallery: {}".format(args.gallery))
    print("=" * 60)


if __name__ == "__main__":
    main()
