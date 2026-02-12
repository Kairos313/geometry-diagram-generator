#!/usr/bin/env python3
"""
Stage 2: Generate rendering code from a geometric blueprint, then execute it.

Uses Gemini 3 Flash via the Google GenAI client to write a self-contained
Python script that renders the geometry described in coordinates.txt.

Auto-detects 2D vs 3D from the blueprint's Z coordinates.

Usage:
    python3 generate_code.py --coordinates coordinates.txt --output output/diagram.png --format png
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
from google import genai

from diagram_prompts import (
    Blueprint_to_Code_2D_Gemini,
    Blueprint_to_Code_3D_Gemini,
    Blueprint_to_Code_Coordinate,
    Blueprint_to_Code_2D_Compact,
    Blueprint_to_Code_3D_Compact,
)

load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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

    # First, check for COORDINATE_2D declaration
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

    # Fallback: parse Z coordinates from the point table
    logger.info("No explicit dimension declaration; parsing Z coordinates...")
    z_values = []
    # Match rows like:  | A | 0.000 | 0.000 | 0.000 | ...
    # or with bold:     | **A** | 0.000 | 0.000 | 0.000 | ...
    row_pattern = re.compile(
        r"\|\s*\*{0,2}\w+\*{0,2}\s*\|"   # Point name (optionally bold)
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

    # If all Z values are identical (typically 0), it's 2D
    if len(set(round(z, 3) for z in z_values)) <= 1:
        return "2d"
    return "3d"


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
    """Call Gemini 3 Flash to generate rendering code.

    Args:
        compact: If True, use compact prompts for JSON blueprints.

    Returns dict with keys: success, code, api_call_duration, tokens.
    """
    client = genai.Client(api_key=api_key)

    # Select target library and prompt based on dimension type and compact mode
    if dimension_type == "coordinate_2d":
        target_library = "matplotlib"
        system_prompt = Blueprint_to_Code_Coordinate  # coordinate always uses verbose prompt
    elif dimension_type == "3d":
        target_library = "manim"
        system_prompt = Blueprint_to_Code_3D_Compact if compact else Blueprint_to_Code_3D_Gemini
    else:  # "2d"
        target_library = "matplotlib"
        system_prompt = Blueprint_to_Code_2D_Compact if compact else Blueprint_to_Code_2D_Gemini

    if compact:
        logger.info(f"Using COMPACT prompt for {target_library} code generation")
    else:
        logger.info(f"Using VERBOSE prompt for {target_library} code generation")

    # Format blueprint section label based on mode
    blueprint_label = "JSON BLUEPRINT" if compact else "BLUEPRINT (coordinates.txt)"

    user_message = (
        f"{system_prompt}\n\n"
        f"--- ORIGINAL QUESTION ---\n{question_text}\n--- END QUESTION ---\n\n"
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

    try:
        start = time.time()
        logger.info(f"Calling Gemini 3 Flash for {target_library} code generation...")
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=user_message,
            config={
                "max_output_tokens": 65536,
                "temperature": 0.0,
                "thinking_config": {"thinking_budget": 4096},
            },
        )
        elapsed = time.time() - start

        response_text = response.text
        usage = response.usage_metadata

        logger.debug(f"Response text length: {len(response_text) if response_text else 0}")
        logger.debug(f"Response text (first 500): {response_text[:500] if response_text else 'EMPTY'}")

        # Extract Python code from the response
        code = extract_python_code(response_text)
        if not code:
            logger.error(f"Full response text:\n{response_text}")
            return {"success": False, "error": "No Python code block found in response"}

        return {
            "success": True,
            "code": code,
            "api_call_duration": elapsed,
            "prompt_tokens": usage.prompt_token_count if usage else 0,
            "completion_tokens": usage.candidates_token_count if usage else 0,
            "total_tokens": usage.total_token_count if usage else 0,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def extract_python_code(response_text):
    # type: (str) -> Optional[str]
    """Extract Python code from a markdown response."""
    # Try ```python ... ``` blocks first
    blocks = re.findall(r"```python\s*(.*?)```", response_text, re.DOTALL)
    if blocks:
        # Return the longest block (likely the main script)
        return max(blocks, key=len).strip()

    # Try generic ``` ... ``` blocks
    blocks = re.findall(r"```\s*(.*?)```", response_text, re.DOTALL)
    for block in blocks:
        block = block.strip()
        if "import" in block and ("matplotlib" in block or "manim" in block):
            return block

    # Fallback: detect raw Python code without markdown formatting
    # This handles cases where the model returns code directly
    text = response_text.strip()
    
    # Strip trailing code block marker if present (model sometimes forgets opening marker)
    if text.endswith("```"):
        text = text[:-3].rstrip()
    
    # Strip bare language tag prefix (model returns "python\n#!/usr/bin/env..." without backticks)
    if re.match(r"^python\s*\n", text):
        text = re.sub(r"^python\s*\n", "", text).strip()
    
    # Check if it looks like raw Python code (starts with shebang or imports)
    is_raw_python = (
        text.startswith("#!/usr/bin/env python") or
        text.startswith("from manim import") or
        text.startswith("import matplotlib") or
        text.startswith("from matplotlib")
    )
    
    if is_raw_python and ("def " in text or "class " in text):
        # Verify it has substantial code structure
        return text

    return None


MANIM_HELPERS_PATH = Path(__file__).parent / "manim_helpers.py"


def ensure_helpers(code_dir):
    # type: (str) -> None
    """Copy manim_helpers.py into the code directory so render_code.py can import it."""
    dst = Path(code_dir) / "manim_helpers.py"
    if MANIM_HELPERS_PATH.exists() and not dst.exists():
        shutil.copy2(str(MANIM_HELPERS_PATH), str(dst))


MANIM_CLI_PATH = "/Users/kairos/.local/bin/manim"


def execute_code(code_path, timeout=120, use_manim_cli=False, output_path=None):
    # type: (str, int, bool, Optional[str]) -> dict
    """Execute the generated Python script.

    For 3D manim code, use_manim_cli=True to invoke the manim CLI directly
    (works with Python 3.13 where manim is installed).

    Returns dict with keys: success, stdout, stderr, returncode.
    """
    code_dir = str(Path(code_path).parent)
    ensure_helpers(code_dir)

    try:
        if use_manim_cli and Path(MANIM_CLI_PATH).exists():
            # Use manim CLI for 3D rendering (Python 3.13)
            result = subprocess.run(
                [MANIM_CLI_PATH, "render", str(code_path), "GeometryScene", "-ql", "--format", "gif"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=code_dir,
            )
            # Manim CLI writes to media/videos/render_code/480p15/diagram.gif
            # We need to copy the output to the expected location
            if result.returncode == 0 and output_path:
                media_dir = Path(code_dir) / "media"
                gif_files = list(media_dir.rglob("*.gif")) if media_dir.exists() else []
                if gif_files:
                    dest = Path(output_path)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(gif_files[0]), str(dest))
                    result = subprocess.CompletedProcess(
                        args=result.args,
                        returncode=0,
                        stdout=result.stdout + f"\nSaved: {dest}",
                        stderr=result.stderr,
                    )
        else:
            # Use system Python for 2D matplotlib rendering
            result = subprocess.run(
                [sys.executable, str(code_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=code_dir,
            )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout}s",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }


# ======================================================================
# CLI
# ======================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate rendering code from blueprint and execute it"
    )
    parser.add_argument(
        "--coordinates", required=True,
        help="Path to coordinates.txt (the blueprint)",
    )
    parser.add_argument(
        "--output", default="output/diagram.png",
        help="Output file path for the rendered diagram",
    )
    parser.add_argument(
        "--format", default="png", choices=["png", "svg", "gif", "mp4"],
        help="Output format (default: png)",
    )
    parser.add_argument(
        "--question-text", default="",
        help="Original question text (helps renderer distinguish given vs derived)",
    )
    parser.add_argument(
        "--compact", action="store_true",
        help="Use compact prompts for JSON blueprints (auto-detected if file is .json)",
    )
    args = parser.parse_args()

    coords_path = Path(args.coordinates)
    if not coords_path.exists():
        logger.error(f"Coordinates file not found: {coords_path}")
        sys.exit(1)

    with open(coords_path, "r", encoding="utf-8") as f:
        blueprint_text = f.read()

    # Auto-detect compact mode from file extension or content
    is_json = coords_path.suffix.lower() == ".json"
    if not is_json:
        # Try to detect if content is JSON
        stripped = blueprint_text.strip()
        is_json = stripped.startswith("{") and stripped.endswith("}")

    compact_mode = args.compact or is_json
    if is_json and not args.compact:
        logger.info("Auto-detected JSON blueprint; using compact mode")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    # Auto-detect dimension type
    dimension_type = detect_dimension(blueprint_text, is_json=is_json)
    logger.info(f"Detected dimension type: {dimension_type}")

    # Validate format for dimension type
    output_format = args.format
    if dimension_type in ("2d", "coordinate_2d") and output_format in ("gif", "mp4"):
        logger.info(f"2D geometry uses static images; switching from {output_format} to png")
        output_format = "png"
    if dimension_type == "3d" and output_format in ("png", "svg"):
        logger.info(f"3D geometry uses animations; switching from {output_format} to gif")
        output_format = "gif"

    # Resolve output path
    output_path = str(Path(args.output).resolve())
    if not output_path.endswith(f".{output_format}"):
        output_path = str(Path(output_path).with_suffix(f".{output_format}"))

    pipeline_dir = Path(__file__).parent
    code_path = pipeline_dir / "render_code.py"

    max_attempts = 2
    error_context = None

    for attempt in range(1, max_attempts + 1):
        logger.info(f"--- Attempt {attempt}/{max_attempts} ---")

        # Step A: Generate code
        question_text = args.question_text
        if question_text and os.path.isfile(question_text):
            with open(question_text, "r", encoding="utf-8") as f:
                question_text = f.read().strip()
        result = generate_render_code(
            api_key=api_key,
            blueprint_text=blueprint_text,
            output_path=output_path,
            output_format=output_format,
            dimension_type=dimension_type,
            question_text=question_text,
            error_context=error_context,
            compact=compact_mode,
        )

        if not result["success"]:
            logger.error(f"Code generation failed: {result['error']}")
            sys.exit(1)

        logger.info(
            f"Code generated — Tokens: {result['total_tokens']} "
            f"(in: {result['prompt_tokens']}, out: {result['completion_tokens']}) "
            f"in {result['api_call_duration']:.1f}s"
        )

        # Write the generated code
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(result["code"])
        logger.info(f"Saved render code to: {code_path}")

        # Step B: Execute the code
        logger.info("Executing generated code...")
        use_manim = (dimension_type == "3d")  # coordinate_2d and 2d both use matplotlib
        exec_result = execute_code(str(code_path), use_manim_cli=use_manim, output_path=output_path)

        if exec_result["stdout"]:
            for line in exec_result["stdout"].strip().split("\n"):
                logger.info(f"  [render] {line}")

        if exec_result["success"]:
            # Verify output file exists
            if Path(output_path).exists():
                size_kb = Path(output_path).stat().st_size / 1024
                logger.info(f"Rendered: {output_path} ({size_kb:.1f} KB)")
                sys.exit(0)
            else:
                error_context = (
                    "Script exited successfully but output file was not created "
                    f"at: {output_path}"
                )
                logger.warning(error_context)
        else:
            error_context = exec_result["stderr"][-2000:] if exec_result["stderr"] else "Unknown error"
            logger.warning(f"Execution failed (exit code {exec_result['returncode']}):")
            if exec_result["stderr"]:
                for line in exec_result["stderr"].strip().split("\n")[-10:]:
                    logger.warning(f"  [render] {line}")

        if attempt < max_attempts:
            logger.info("Retrying with error context...")

    logger.error(f"Failed after {max_attempts} attempts")
    sys.exit(1)


if __name__ == "__main__":
    main()
