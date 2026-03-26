#!/usr/bin/env python3
"""
Test the hybrid blueprint prompt (old JSON format + new quality rules).

Runs Pipeline D (hybrid) on 10 questions with 100 workers, generates gallery,
and compares with Pipeline A results if available.

Usage:
    python3 frontend/test/test_hybrid.py
    python3 frontend/test/test_hybrid.py --workers 100
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

TEST_DIR = Path(__file__).parent
FRONTEND_DIR = TEST_DIR.parent
ROOT_DIR = FRONTEND_DIR.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(FRONTEND_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

for name in ["httpx", "httpcore", "google", "google_genai", "openai",
             "generate_js_pipeline", "generate_code_js", "classify_geometry_type"]:
    logging.getLogger(name).setLevel(logging.WARNING)

from hkdse_new_questions import HKDSE_NEW_QUESTIONS

DEEPSEEK_ENDPOINT = "https://raksh-m4jj47jc-japaneast.services.ai.azure.com/openai/v1/"
DEEPSEEK_MODEL = "DeepSeek-V3.2"


def generate_hybrid_blueprint(question_text, dimension_type, api_key=None):
    # type: (str, str, Optional[str]) -> dict
    """Call Gemini with the hybrid blueprint prompt."""
    from js_pipeline_prompts_hybrid import get_hybrid_blueprint_prompt
    from google import genai
    from google.genai import types
    import re

    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)
    prompt = get_hybrid_blueprint_prompt(dimension_type)

    start = time.time()
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[{"role": "user", "parts": [{"text": prompt + "\n\nQuestion: " + question_text}]}],
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
        tokens = {"total": getattr(um, "total_token_count", 0) or 0}

    json_match = re.search(r'\{[\s\S]*\}', raw)
    return {
        "success": bool(json_match),
        "blueprint": json_match.group(0) if json_match else raw,
        "duration": duration,
        "tokens": tokens,
        "error": None if json_match else "No JSON found",
    }


def blueprint_to_notes(blueprint_str):
    # type: (str) -> str
    """Convert JSON blueprint to text notes for DeepSeek."""
    try:
        bp = json.loads(blueprint_str)
    except json.JSONDecodeError:
        return "RAW BLUEPRINT:\n" + blueprint_str

    dim = bp.get("dimension", "2d").upper()
    lines = ["DIMENSION: {}".format(dim), "TITLE: Geometry Diagram", ""]

    lines.append("COORDINATES:")
    for name, coords in bp.get("points", {}).items():
        if len(coords) == 3 and abs(coords[2]) < 0.001:
            lines.append("{} = ({}, {})".format(name, coords[0], coords[1]))
        else:
            lines.append("{} = ({}, {}, {})".format(name, *coords))
    lines.append("")

    lines.append("ELEMENTS:")
    for ln in bp.get("lines", []):
        lines.append("- Segment {} to {} ({})".format(ln["from"], ln["to"], ln.get("style", "solid")))
    for c in bp.get("circles", []):
        lines.append("- Circle center={} radius={}".format(c["center"], c["radius"]))
    for f in bp.get("faces", []):
        lines.append("- Face {} (translucent)".format(" ".join(f.get("points", []))))
    lines.append("")

    angles = bp.get("angles", [])
    asked = bp.get("asked", [])
    if angles:
        lines.append("ANGLES:")
        for a in angles:
            aid = a.get("id", "")
            v, p1, p2 = a.get("vertex", "?"), a.get("p1", "?"), a.get("p2", "?")
            val = a.get("value")
            if aid in asked:
                lines.append("- Angle at {} between {}{} and {}{} = ? (asked, highlight)".format(v, v, p1, v, p2))
            elif val is not None:
                is_right = abs(val - 90) < 1
                lines.append("- Angle at {} between {}{} and {}{} = {} degrees{}".format(
                    v, v, p1, v, p2, val, " (right angle, draw square marker)" if is_right else ""))
        lines.append("")

    given = bp.get("given", {})
    if given:
        lines.append("LABELS:")
        for k, v in given.items():
            lines.append('- {}: "{}"'.format(k, v))
        for k in asked:
            lines.append('- {}: "?" (asked, highlight)'.format(k))
        lines.append("")

        lines.append("GIVEN:")
        for k, v in given.items():
            lines.append("- {} = {}".format(k, v))
        lines.append("")

    if asked:
        lines.append("ASKED:")
        for k in asked:
            lines.append("- {}".format(k))
        lines.append("")

    axes = bp.get("axes", False)
    lines.append("COORDINATE_SYSTEM:")
    lines.append("- axes: {}".format("true" if axes else "false"))
    if axes:
        cr = bp.get("coordinate_range", {})
        lines.append("- x_range: [{}, {}]".format(cr.get("x_min", -10), cr.get("x_max", 10)))
        lines.append("- y_range: [{}, {}]".format(cr.get("y_min", -10), cr.get("y_max", 10)))
    lines.append("")
    lines.append("INTERACTIVE:\n- none")

    return "\n".join(lines)


def run_hybrid(question, output_dir):
    # type: (dict, str) -> dict
    """Run hybrid pipeline: old format blueprint → convert to notes → DeepSeek JS."""
    from generate_code_js import extract_html, postprocess_js
    from js_pipeline_prompts import get_js_prompt
    from openai import OpenAI

    qid = question["id"]
    dim = question.get("dimension", "2d").replace("coordinate_", "")
    output_path = os.path.join(output_dir, qid, "diagram.html")

    start = time.time()

    # Stage 1: Hybrid blueprint
    bp = generate_hybrid_blueprint(question["text"], dim)
    if not bp["success"]:
        return {"question_id": qid, "pipeline": "D", "success": False,
                "duration": time.time() - start, "tokens": {"gemini": bp["tokens"]},
                "error": bp["error"], "output_path": output_path}

    # Stage 2: Convert to notes
    notes = blueprint_to_notes(bp["blueprint"])

    # Stage 3: DeepSeek JS
    api_key = os.getenv("DEEPSEEK_API_KEY")
    client = OpenAI(base_url=DEEPSEEK_ENDPOINT, api_key=api_key)
    system_prompt = get_js_prompt(dim)

    user_message = (
        "=== ORIGINAL QUESTION ===\n{q}\n\n"
        "=== COMPUTATION NOTES ===\n{n}\n=== END ==="
    ).format(q=question["text"], n=notes)

    ds_start = time.time()
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_message}],
        max_tokens=16384, temperature=0.0,
    )
    ds_dur = time.time() - ds_start

    content = response.choices[0].message.content or ""
    ds_tokens = {"total": response.usage.total_tokens if response.usage else 0}

    html = extract_html(content)
    if not html:
        return {"question_id": qid, "pipeline": "D", "success": False,
                "duration": time.time() - start,
                "tokens": {"gemini": bp["tokens"], "deepseek": ds_tokens},
                "error": "No HTML", "output_path": output_path}

    html = postprocess_js(html)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html, encoding="utf-8")

    # Save notes for inspection
    Path(output_path).with_suffix(".notes.txt").write_text(notes, encoding="utf-8")
    Path(output_path).with_suffix(".blueprint.json").write_text(bp["blueprint"], encoding="utf-8")

    return {"question_id": qid, "pipeline": "D", "success": True,
            "duration": time.time() - start,
            "tokens": {"gemini": bp["tokens"], "deepseek": ds_tokens},
            "error": None, "output_path": output_path}


def generate_gallery(results, questions, output_path, output_dir):
    # type: (list, list, str, str) -> None
    """Generate gallery for hybrid results."""
    cards = []
    for q in questions:
        r = next((x for x in results if x["question_id"] == q["id"]), None)
        if not r:
            continue

        g_tok = r.get("tokens", {}).get("gemini", {}).get("total", 0)
        d_tok = r.get("tokens", {}).get("deepseek", {}).get("total", 0)

        iframe = ""
        if r["success"] and r.get("output_path"):
            rel = os.path.relpath(r["output_path"], os.path.dirname(output_path))
            iframe = '<iframe src="{}" loading="lazy"></iframe>'.format(rel)
        else:
            iframe = '<div class="error">{}</div>'.format(str(r.get("error", ""))[:150])

        cards.append("""
        <div class="card {sc}">
            <div class="card-header"><strong>{name}</strong> <span class="qid">{qid}</span>
                <span class="badge">{dim}</span>
                <span class="{sc}">{status}</span></div>
            <div class="card-q">{text}</div>
            <div class="card-render">{iframe}</div>
            <div class="card-stats">{dur:.1f}s | G:{gt} D:{dt}</div>
        </div>""".format(
            sc="pass" if r["success"] else "fail",
            name=q["name"], qid=q["id"], dim=q.get("dimension", "?"),
            status="PASS" if r["success"] else "FAIL",
            text=q["text"][:150], iframe=iframe,
            dur=r["duration"], gt=g_tok, dt=d_tok,
        ))

    passed = sum(1 for r in results if r["success"])
    total = len(results)
    avg_dur = sum(r["duration"] for r in results) / total if total else 0
    g_total = sum(r.get("tokens", {}).get("gemini", {}).get("total", 0) for r in results)
    d_total = sum(r.get("tokens", {}).get("deepseek", {}).get("total", 0) for r in results)
    cost = g_total * 0.5 / 1e6 + d_total * 0.4 / 1e6

    html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Hybrid Pipeline D Results</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0C0C0C;color:#e0e0e0;font-family:monospace}}
.container{{max-width:1400px;margin:0 auto;padding:1.5rem}}
h1{{color:#4ECDC4;text-align:center;margin-bottom:.5rem}}
.subtitle{{text-align:center;color:#888;margin-bottom:1.5rem;font-size:.85rem}}
.summary{{display:flex;gap:1rem;justify-content:center;margin-bottom:1.5rem;flex-wrap:wrap}}
.stat{{background:#1a1a1a;padding:.5rem 1rem;border-radius:4px;text-align:center}}
.stat .val{{color:#4ECDC4;font-weight:700;font-size:1.2rem}}
.stat .label{{color:#888;font-size:.75rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(500px,1fr));gap:1rem}}
.card{{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;overflow:hidden}}
.card.pass{{border-color:#96CEB4}}
.card.fail{{border-color:#FF6B6B}}
.card-header{{padding:.75rem 1rem;border-bottom:1px solid #2a2a2a;display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}}
.qid{{color:#666;font-size:.75rem;font-family:monospace}}
.badge{{background:#457B9D;color:#fff;padding:.1rem .4rem;border-radius:3px;font-size:.7rem}}
.pass{{color:#96CEB4;font-weight:700}}
.fail{{color:#FF6B6B;font-weight:700}}
.card-q{{padding:.5rem 1rem;font-size:.8rem;color:#888}}
.card-render{{height:380px;background:#0C0C0C}}
.card-render iframe{{width:100%;height:100%;border:none}}
.card-stats{{padding:.5rem 1rem;font-size:.75rem;color:#666;border-top:1px solid #2a2a2a}}
.error{{color:#FF6B6B;padding:.5rem;font-size:.75rem}}
</style></head><body>
<div class="container">
<h1>Pipeline D: Hybrid Blueprint</h1>
<p class="subtitle">Old JSON format + New quality rules → DeepSeek JS</p>
<div class="summary">
    <div class="stat"><div class="val">{p}/{t}</div><div class="label">Pass</div></div>
    <div class="stat"><div class="val">{dur:.1f}s</div><div class="label">Avg Time</div></div>
    <div class="stat"><div class="val">${cost:.4f}</div><div class="label">Total Cost</div></div>
    <div class="stat"><div class="val">${per:.4f}</div><div class="label">Per Diagram</div></div>
    <div class="stat"><div class="val">{gt:,}</div><div class="label">Gemini Tokens</div></div>
    <div class="stat"><div class="val">{dt:,}</div><div class="label">DeepSeek Tokens</div></div>
</div>
<div class="grid">{cards}</div>
</div></body></html>""".format(
        p=passed, t=total, dur=avg_dur, cost=cost, per=cost/total if total else 0,
        gt=g_total, dt=d_total, cards="\n".join(cards),
    )

    Path(output_path).write_text(html, encoding="utf-8")
    logger.info("Gallery saved to {}".format(output_path))


def main():
    parser = argparse.ArgumentParser(description="Test hybrid pipeline")
    parser.add_argument("--workers", type=int, default=100)
    parser.add_argument("--output-dir", default=str(TEST_DIR / "output" / "pipeline_d"))
    parser.add_argument("--gallery", default=str(TEST_DIR / "hybrid_gallery.html"))
    args = parser.parse_args()

    questions = HKDSE_NEW_QUESTIONS
    total = len(questions)
    print("Running {} questions with {} workers\n".format(total, args.workers))

    results = []
    wall_start = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_hybrid, q, args.output_dir): q for q in questions}
        for i, f in enumerate(as_completed(futs), 1):
            q = futs[f]
            try:
                r = f.result()
                status = "PASS" if r["success"] else "FAIL"
                g = r.get("tokens", {}).get("gemini", {}).get("total", 0)
                d = r.get("tokens", {}).get("deepseek", {}).get("total", 0)
                print("[{}/{}] {} {} ({:.1f}s, G:{} D:{}) {}".format(
                    i, total, status, r["question_id"], r["duration"], g, d,
                    r.get("error", "") if not r["success"] else ""
                ))
                results.append(r)
            except Exception as e:
                print("[{}/{}] CRASH {} - {}".format(i, total, q["id"], e))
                results.append({"question_id": q["id"], "pipeline": "D",
                                "success": False, "duration": 0, "tokens": {},
                                "error": str(e), "output_path": ""})

    wall_time = time.time() - wall_start
    results.sort(key=lambda r: r["question_id"])

    generate_gallery(results, questions, args.gallery, args.output_dir)

    # Save raw results
    with open(os.path.join(args.output_dir, "results.json"), "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Summary
    passed = sum(1 for r in results if r["success"])
    avg_dur = sum(r["duration"] for r in results) / total
    g_total = sum(r.get("tokens", {}).get("gemini", {}).get("total", 0) for r in results)
    d_total = sum(r.get("tokens", {}).get("deepseek", {}).get("total", 0) for r in results)
    cost = g_total * 0.5 / 1e6 + d_total * 0.4 / 1e6

    print("\n" + "=" * 60)
    print("PIPELINE D: HYBRID BLUEPRINT")
    print("=" * 60)
    print("Pass: {}/{} | Avg: {:.1f}s | Wall: {:.1f}s".format(passed, total, avg_dur, wall_time))
    print("Gemini: {:,} tok (${:.4f})".format(g_total, g_total * 0.5 / 1e6))
    print("DeepSeek: {:,} tok (${:.4f})".format(d_total, d_total * 0.4 / 1e6))
    print("Total cost: ${:.4f} | Per diagram: ${:.4f}".format(cost, cost / total))
    print("Gallery: {}".format(args.gallery))
    print("=" * 60)


if __name__ == "__main__":
    main()
