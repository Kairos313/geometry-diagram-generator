#!/usr/bin/env python3
"""
Generate geometry diagrams as self-contained HTML using LLM-generated JS code.

Pipeline: Question text → DeepSeek V3.2 → D3.js (2D) or Three.js (3D) HTML

This replaces the old 4-stage pipeline (classify → blueprint → codegen → execute)
with a simpler 2-stage pipeline (classify → JS codegen). The LLM directly generates
browser-ready rendering code, handling any geometry question without schema limitations.

Usage:
    python3 generate_code_js.py --question "Triangle ABC with AB=12cm..." --dim 2d
    python3 generate_code_js.py --question "A pyramid VABCD..." --dim 3d
    python3 generate_code_js.py --question "..." --dim auto  # auto-classify first
"""

import argparse
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

# Add parent dir (repo root) to path for shared modules
_FRONTEND_DIR = Path(__file__).parent
_ROOT_DIR = _FRONTEND_DIR.parent
sys.path.insert(0, str(_ROOT_DIR))
sys.path.insert(0, str(_FRONTEND_DIR))

load_dotenv(_ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Azure endpoint for DeepSeek-V3.2
DEEPSEEK_ENDPOINT = "https://raksh-m4jj47jc-japaneast.services.ai.azure.com/openai/v1/"
DEEPSEEK_MODEL = "DeepSeek-V3.2"


def generate_js_code(
    question_text,      # type: str
    dimension_type,     # type: str
    api_key=None,       # type: Optional[str]
    error_context=None, # type: Optional[str]
):
    # type: (...) -> dict
    """Generate self-contained HTML with D3.js or Three.js rendering code.

    Args:
        question_text: The geometry question.
        dimension_type: "2d" or "3d".
        api_key: DeepSeek API key (falls back to env var).
        error_context: If retrying, the error from the previous attempt.

    Returns:
        dict with keys: success, html, duration, tokens, error
    """
    from js_code_prompts import get_js_code_prompt

    if not api_key:
        api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return {"success": False, "html": "", "duration": 0, "tokens": {},
                "error": "DEEPSEEK_API_KEY not set"}

    client = OpenAI(base_url=DEEPSEEK_ENDPOINT, api_key=api_key)
    system_prompt = get_js_code_prompt(dimension_type)

    user_message = f"Question: {question_text}"
    if error_context:
        user_message += (
            f"\n\n--- PREVIOUS ATTEMPT FAILED ---\n"
            f"The previous code produced this error:\n{error_context}\n"
            f"Please fix the issue and generate corrected code.\n"
            f"--- END ERROR ---"
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        start = time.time()
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            max_tokens=16384,
            temperature=0.0,
        )
        duration = time.time() - start

        content = response.choices[0].message.content or ""
        tokens = {
            "prompt": response.usage.prompt_tokens if response.usage else 0,
            "completion": response.usage.completion_tokens if response.usage else 0,
            "total": response.usage.total_tokens if response.usage else 0,
        }

        # Extract HTML from response (strip markdown fences if present)
        html = extract_html(content)

        if not html:
            return {"success": False, "html": content, "duration": duration,
                    "tokens": tokens, "error": "No valid HTML found in response"}

        # Post-process: fix common LLM JS code bugs
        html = postprocess_js(html)

        logger.info(
            f"Generated {dimension_type.upper()} JS code in {duration:.1f}s "
            f"({tokens['total']} tokens, {len(html)} chars)"
        )

        return {
            "success": True,
            "html": html,
            "duration": duration,
            "tokens": tokens,
            "error": None,
        }

    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return {"success": False, "html": "", "duration": 0, "tokens": {},
                "error": str(e)}


def postprocess_js(html):
    # type: (str) -> str
    """Fix common LLM-generated JS bugs."""
    fixes_applied = []

    # Fix 1: Replace `function var(` with `function getVar(` (var is reserved)
    if 'function var(' in html:
        html = html.replace('function var(', 'function getVar(')
        # Also fix calls to var() that aren't CSS var() inside style blocks
        # Only replace var() calls in <script> sections
        parts = re.split(r'(<script[^>]*>|</script>)', html)
        in_script = False
        for i, part in enumerate(parts):
            if '<script' in part:
                in_script = True
            elif '</script>' in part:
                in_script = False
            elif in_script:
                # Replace bare var(...) calls that aren't `var ` declarations
                parts[i] = re.sub(
                    r'(?<![a-zA-Z])var\(([^)]+)\)',
                    r'getVar(\1)',
                    parts[i]
                )
        html = ''.join(parts)
        fixes_applied.append("renamed function var() to getVar()")

    # Fix 2: Replace var(--geo-xxx) used as JS string values with hex colors
    css_var_map = {
        'var(--geo-primary)': '"#5b4dc7"',
        'var(--geo-highlight)': '"#d85a30"',
        'var(--geo-construction)': '"#888780"',
        'var(--geo-angle)': '"#ba7517"',
        'var(--geo-green)': '"#0f6e56"',
        'var(--geo-text)': '"#2c2c2a"',
        'var(--geo-bg)': '"#ffffff"',
        'var(--geo-primary-fill)': '"rgba(91, 77, 199, 0.08)"',
        'var(--geo-highlight-fill)': '"rgba(216, 90, 48, 0.12)"',
    }
    # Only apply inside <script> blocks
    parts = re.split(r'(<script[^>]*>|</script>)', html)
    in_script = False
    for i, part in enumerate(parts):
        if '<script' in part:
            in_script = True
        elif '</script>' in part:
            in_script = False
        elif in_script:
            for css_var, hex_val in css_var_map.items():
                if css_var in parts[i]:
                    parts[i] = parts[i].replace(css_var, hex_val)
                    fixes_applied.append(f"replaced {css_var} in JS with {hex_val}")
    html = ''.join(parts)

    if fixes_applied:
        logger.info(f"Post-processing applied {len(fixes_applied)} fixes: {'; '.join(set(fixes_applied))}")

    return html


def extract_html(content):
    # type: (str) -> str
    """Extract HTML from LLM response, stripping markdown fences if present."""
    # Try to find HTML between ```html ... ``` fences
    match = re.search(r'```html\s*\n(.*?)```', content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try to find HTML between ``` ... ``` fences
    match = re.search(r'```\s*\n(.*?)```', content, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        if candidate.startswith('<!DOCTYPE') or candidate.startswith('<html'):
            return candidate

    # If content itself looks like HTML, use it directly
    stripped = content.strip()
    if stripped.startswith('<!DOCTYPE') or stripped.startswith('<html'):
        return stripped

    return ""


def classify_dimension(question_text, gemini_key=None):
    # type: (str, Optional[str]) -> str
    """Auto-classify question as 2d or 3d using Gemini."""
    try:
        from classify_geometry_type import classify_geometry
        result = classify_geometry(question_text)
        dim = result.get("dimension_type", "2d").replace("coordinate_", "")
        logger.info(f"Auto-classified as: {dim}")
        return dim
    except Exception as e:
        logger.warning(f"Classification failed ({e}), defaulting to 2d")
        return "2d"


def generate_diagram(question_text, dimension_type="auto", output_path=None, max_retries=1):
    # type: (str, str, Optional[str], int) -> dict
    """Full pipeline: classify (if needed) → generate JS → save HTML.

    Returns dict with: success, html, dimension, duration, tokens, output_path
    """
    total_start = time.time()

    # Stage 1: Classify if needed
    if dimension_type == "auto":
        dimension_type = classify_dimension(question_text)

    # Stage 2: Generate JS code
    result = generate_js_code(question_text, dimension_type)

    # Retry on failure
    if not result["success"] and max_retries > 0:
        logger.warning(f"First attempt failed: {result['error']}. Retrying...")
        result = generate_js_code(
            question_text, dimension_type,
            error_context=result.get("error", "Unknown error"),
        )

    # Save output
    if result["success"] and output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result["html"], encoding="utf-8")
        logger.info(f"Saved to {output_path}")

    total_duration = time.time() - total_start

    return {
        "success": result["success"],
        "html": result["html"],
        "dimension": dimension_type,
        "duration": total_duration,
        "tokens": result.get("tokens", {}),
        "output_path": str(output_path) if output_path else None,
        "error": result.get("error"),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate geometry diagram as HTML")
    parser.add_argument("--question", "-q", required=True, help="Geometry question text")
    parser.add_argument("--dim", "-d", default="auto", choices=["2d", "3d", "auto"],
                        help="Dimension type (default: auto-classify)")
    parser.add_argument("--output", "-o", default="output/diagram.html",
                        help="Output HTML file path")
    args = parser.parse_args()

    result = generate_diagram(args.question, args.dim, args.output)

    if result["success"]:
        print(f"\nSuccess! Saved to {result['output_path']}")
        print(f"  Dimension: {result['dimension']}")
        print(f"  Duration: {result['duration']:.1f}s")
        print(f"  Tokens: {result['tokens'].get('total', '?')}")
    else:
        print(f"\nFailed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
