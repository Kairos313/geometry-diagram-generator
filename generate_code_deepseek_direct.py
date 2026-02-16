#!/usr/bin/env python3
"""
Stage 2 (DeepSeek Direct): Generate rendering code from a geometric blueprint.

Uses deepseek-chat via direct DeepSeek API (no reasoning mode) for fast code generation.

Same interface as generate_code_deepseek.py so it can be swapped in batch_test.py.

Usage:
    python3 generate_code_deepseek_direct.py --coordinates coordinates.json --output diagram.png
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from diagram_prompts import (
    Blueprint_to_Code_2D_DeepSeek,
    Blueprint_to_Code_3D_DeepSeek,
)

load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Direct DeepSeek API endpoint
DEEPSEEK_ENDPOINT = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"  # Fast chat model (no reasoning)


def detect_dimension(blueprint_text, is_json=False):
    # type: (str, bool) -> str
    """Detect dimension type from the blueprint.

    First checks for explicit DIMENSION declaration (preferred).
    Falls back to Z-coordinate parsing if not found.

    Returns "2d", "3d", or "coordinate_2d".
    """
    # Handle JSON blueprint
    if is_json:
        try:
            data = json.loads(blueprint_text)
            dim = data.get("dimension", "2d").lower()
            if dim in ("2d", "3d", "coordinate_2d"):
                logger.info(f"Found dimension in JSON blueprint: {dim}")
                return dim
        except json.JSONDecodeError:
            pass
        logger.warning("Could not parse JSON blueprint dimension; defaulting to 2d")
        return "2d"

    # Check for COORDINATE_2D declaration
    coord_match = re.search(r'\*{0,2}DIMENSION:\s*(COORDINATE_2D)\*{0,2}', blueprint_text, re.IGNORECASE)
    if coord_match:
        logger.info("Found explicit dimension declaration: coordinate_2d")
        return "coordinate_2d"

    # Check for explicit 2D/3D DIMENSION declaration
    match = re.search(r'\*{0,2}DIMENSION:\s*(2D|3D)\*{0,2}', blueprint_text, re.IGNORECASE)
    if match:
        dim = match.group(1).lower()
        logger.info(f"Found explicit dimension declaration: {dim}")
        return dim

    # Fallback: parse Z coordinates
    logger.info("No explicit dimension declaration; parsing Z coordinates...")
    z_values = []
    row_pattern = re.compile(
        r"\|\s*\*{0,2}\w+\*{0,2}\s*\|"   # Point name
        r"\s*(-?[\d.]+)\s*\|"              # X
        r"\s*(-?[\d.]+)\s*\|"              # Y
        r"\s*(-?[\d.]+)\s*\|",             # Z
    )
    for m in row_pattern.finditer(blueprint_text):
        try:
            z_values.append(float(m.group(3)))
        except ValueError:
            continue

    if not z_values:
        logger.warning("Could not parse Z coordinates; defaulting to 2D")
        return "2d"

    non_zero = [z for z in z_values if abs(z) > 1e-6]
    if non_zero:
        logger.info(f"Found {len(non_zero)}/{len(z_values)} non-zero Z coordinates; inferring 3D")
        return "3d"

    logger.info("All Z coordinates are zero; inferring 2D")
    return "2d"


def extract_python_code(response_text):
    # type: (str) -> Optional[str]
    """Extract Python code from markdown code blocks."""
    pattern = r"```python\n(.*?)\n```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    if matches:
        return matches[0]
    return None


def generate_render_code(
    api_key,           # type: str
    blueprint_text,    # type: str
    output_path,       # type: str
    output_format,     # type: str
    dimension_type,    # type: str
    question_text="",  # type: str
    error_context=None,  # type: Optional[str]
    compact=False,     # type: bool
):
    # type: (...) -> dict
    """Call DeepSeek-Chat to generate rendering code.

    Args:
        compact: If True, use compact prompts for reduced token usage.
        error_context: If provided, includes previous error for retry.

    Returns a dict with keys: success, code, code_file,
    api_call_duration, prompt_tokens, completion_tokens, total_tokens.
    """
    client = OpenAI(
        base_url=DEEPSEEK_ENDPOINT,
        api_key=api_key,
    )

    # Use provided dimension type (already detected by caller)
    is_json = compact or blueprint_text.strip().startswith("{")

    # Select appropriate prompt
    if dimension_type == "3d":
        target_library = "manim"
        system_prompt = Blueprint_to_Code_3D_DeepSeek
    else:  # "2d" or "coordinate_2d"
        target_library = "matplotlib"
        system_prompt = Blueprint_to_Code_2D_DeepSeek

    logger.info(f"Using DeepSeek-Chat for {target_library} code generation (dimension: {dimension_type})")

    # Format user message (NOTE: No question text to avoid contamination)
    blueprint_label = "JSON BLUEPRINT" if is_json else "BLUEPRINT"
    user_message = (
        f"{system_prompt}\n\n"
        f"--- {blueprint_label} ---\n{blueprint_text}\n--- END BLUEPRINT ---\n\n"
        f"Target library: {target_library}\n"
        f"Output path: {output_path}\n"
        f"Output format: {output_format}\n"
    )

    if error_context:
        user_message += (
            f"\n--- PREVIOUS ATTEMPT FAILED ---\n"
            f"The previous code produced this error:\n{error_context}\n"
            f"Please fix the issue and generate corrected code.\n"
            f"--- END ERROR ---\n"
        )

    messages = [{"role": "user", "content": user_message}]

    try:
        start = time.time()
        logger.info(f"Calling DeepSeek-Chat for {target_library} code generation...")

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            max_tokens=8192,  # DeepSeek API max limit
            temperature=0.0,
        )

        elapsed = time.time() - start
        response_text = response.choices[0].message.content
        usage = response.usage

        logger.info(f"API call completed in {elapsed:.2f}s")
        logger.info(f"Token usage - Input: {usage.prompt_tokens}, Output: {usage.completion_tokens}, Total: {usage.total_tokens}")

        # Extract Python code
        code = extract_python_code(response_text)
        if not code:
            logger.error(f"No Python code block found in response")
            return {
                "success": False,
                "error": "No Python code block found in response",
                "api_call_duration": elapsed,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }

        # Save code to render_code.py
        code_file = Path(output_path).parent / "render_code.py"
        with open(code_file, "w") as f:
            f.write(code)
        logger.info(f"Generated code saved to: {code_file}")

        return {
            "success": True,
            "code": code,
            "code_file": str(code_file),
            "api_call_duration": elapsed,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }

    except Exception as e:
        logger.error(f"API call failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "api_call_duration": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }


MANIM_HELPERS_PATH = Path(__file__).parent / "manim_helpers.py"
MATPLOTLIB_HELPERS_PATH = Path(__file__).parent / "matplotlib_helpers.py"


def ensure_helpers(code_dir, dimension_type="3d"):
    # type: (str, str) -> None
    """Copy helper files into the code directory so render_code.py can import them."""
    if dimension_type == "3d":
        dst = Path(code_dir) / "manim_helpers.py"
        if MANIM_HELPERS_PATH.exists() and not dst.exists():
            shutil.copy2(str(MANIM_HELPERS_PATH), str(dst))
    if dimension_type in ("2d", "coordinate_2d"):
        dst = Path(code_dir) / "matplotlib_helpers.py"
        if MATPLOTLIB_HELPERS_PATH.exists() and not dst.exists():
            shutil.copy2(str(MATPLOTLIB_HELPERS_PATH), str(dst))


def execute_code(code_path, timeout=120, use_manim_cli=False, output_path=None, dimension_type="3d"):
    # type: (str, int, bool, Optional[str], str) -> dict
    """Execute the generated Python code.

    Args:
        code_path: Path to render_code.py
        timeout: Maximum execution time in seconds
        use_manim_cli: Whether to use manim CLI (always True for 3D)
        output_path: Expected output file path
        dimension_type: "2d" or "3d"

    Returns a dict with keys: success, execution_time, error (if failed).
    """
    # Copy helper files to code directory
    code_dir = str(Path(code_path).parent)
    ensure_helpers(code_dir, dimension_type=dimension_type)

    try:
        start = time.time()

        if dimension_type == "3d":
            # Execute manim directly (use_manim_cli is implicit for 3D)
            manim_path = "/Users/kairos/.local/bin/manim"
            cmd = [manim_path, "render", code_path, "GeometryScene", "-ql", "--format", "gif"]
            logger.info(f"Executing: {' '.join(cmd)}")
        else:
            # Execute matplotlib script with python3
            cmd = ["python3", code_path]
            logger.info(f"Executing: python3 {code_path}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(code_path).parent,
        )

        elapsed = time.time() - start

        if result.returncode != 0:
            logger.error(f"Execution failed with code {result.returncode}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            return {
                "success": False,
                "execution_time": elapsed,
                "error": result.stderr or result.stdout or "Unknown error",
            }

        # For 3D manim renders, move the output file from manim's default location
        if dimension_type == "3d" and output_path:
            manim_output = Path(code_path).parent / "media" / "videos" / "render_code" / "360p10" / "diagram.gif"
            if manim_output.exists():
                shutil.move(str(manim_output), output_path)
                logger.info(f"Moved manim output to: {output_path}")

        # Check if output file was created
        if output_path and not Path(output_path).exists():
            logger.error(f"Output file not created: {output_path}")
            return {
                "success": False,
                "execution_time": elapsed,
                "error": f"Output file not created: {output_path}",
            }

        logger.info(f"Execution completed successfully in {elapsed:.2f}s")
        return {
            "success": True,
            "execution_time": elapsed,
        }

    except subprocess.TimeoutExpired:
        logger.error(f"Execution timed out after {timeout}s")
        return {
            "success": False,
            "execution_time": timeout,
            "error": f"Execution timed out after {timeout}s",
        }
    except Exception as e:
        logger.error(f"Execution error: {e}")
        return {
            "success": False,
            "execution_time": 0,
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser(description="Generate rendering code using DeepSeek-Chat")
    parser.add_argument("--coordinates", required=True, help="Path to coordinates file (JSON or txt)")
    parser.add_argument("--output", required=True, help="Output file path for diagram")
    parser.add_argument("--format", default="png", choices=["png", "svg", "gif"], help="Output format")
    parser.add_argument("--compact", action="store_true", help="Use compact prompts")
    parser.add_argument("--no-execute", action="store_true", help="Generate code only, don't execute")

    args = parser.parse_args()

    # Get API key
    api_key = os.getenv("NEW_DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("NEW_DEEPSEEK_API_KEY environment variable not set")
        sys.exit(1)

    # Read blueprint
    with open(args.coordinates, "r") as f:
        blueprint_text = f.read()

    # Detect if JSON
    is_json = args.coordinates.endswith(".json") or blueprint_text.strip().startswith("{")

    # Detect dimension type
    dimension = detect_dimension(blueprint_text, is_json=is_json)

    # Generate code
    result = generate_render_code(
        api_key=api_key,
        blueprint_text=blueprint_text,
        output_path=args.output,
        output_format=args.format,
        dimension_type=dimension,
        compact=is_json,
    )

    if not result["success"]:
        print(f"✗ Code generation failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    print(f"✓ Code generated successfully")
    print(f"  Code file: {result['code_file']}")
    print(f"  Time: {result['api_call_duration']:.2f}s")
    print(f"  Tokens: {result['total_tokens']} ({result['prompt_tokens']} in, {result['completion_tokens']} out)")

    if args.no_execute:
        sys.exit(0)

    # Execute code
    exec_result = execute_code(
        code_path=result['code_file'],
        output_path=args.output,
        dimension_type=dimension,
        use_manim_cli=(dimension == "3d")
    )

    if exec_result["success"]:
        print(f"✓ Diagram generated successfully")
        print(f"  Output: {args.output}")
        print(f"  Execution time: {exec_result['execution_time']:.2f}s")
        sys.exit(0)
    else:
        print(f"✗ Execution failed: {exec_result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
