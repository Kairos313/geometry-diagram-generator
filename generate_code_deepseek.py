#!/usr/bin/env python3
"""
Stage 2: Generate rendering code from a geometric blueprint using DeepSeek-V3.2.

Uses DeepSeek-V3.2 via Azure OpenAI endpoint to write a self-contained
Python script that renders the geometry described in coordinates.txt.

Auto-detects 2D vs 3D from the blueprint's Z coordinates.

Usage:
    python3 generate_code_deepseek.py --coordinates coordinates.txt --output output/diagram.png --format png
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
    Blueprint_to_Code_2D_Gemini,
    Blueprint_to_Code_3D_Gemini,
    Blueprint_to_Code_Coordinate,
    Blueprint_to_Code_2D_Compact,
    Blueprint_to_Code_3D_Compact,
    Blueprint_to_Code_2D_DeepSeek,
    Blueprint_to_Code_3D_DeepSeek,
)

load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Azure endpoint for DeepSeek-V3.2
DEEPSEEK_ENDPOINT = "https://raksh-m4jj47jc-japaneast.services.ai.azure.com/openai/v1/"
DEEPSEEK_MODEL = "DeepSeek-V3.2"


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
    row_pattern = re.compile(
        r"\|\s*\*{0,2}\w+\*{0,2}\s*\|"
        r"\s*(-?[\d.]+)\s*\|"
        r"\s*(-?[\d.]+)\s*\|"
        r"\s*(-?[\d.]+)\s*\|",
    )
    for m in row_pattern.finditer(blueprint_text):
        try:
            z_values.append(float(m.group(3)))
        except ValueError:
            continue

    if not z_values:
        logger.warning("Could not parse Z coordinates; defaulting to 2D")
        return "2d"

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
    """Call DeepSeek-V3.2 via Azure OpenAI to generate rendering code.

    Args:
        compact: If True, use compact prompts for JSON blueprints.

    Returns dict with keys: success, code, api_call_duration, tokens.
    """
    client = OpenAI(
        base_url=DEEPSEEK_ENDPOINT,
        api_key=api_key,
    )

    # Select target library and prompt based on dimension type and compact mode
    # DeepSeek-specific prompts have stronger guardrails (helper imports, prohibited APIs)
    if dimension_type == "coordinate_2d":
        target_library = "matplotlib"
        system_prompt = Blueprint_to_Code_Coordinate
        prompt_label = "COORDINATE"
    elif dimension_type == "3d":
        target_library = "manim"
        if compact:
            system_prompt = Blueprint_to_Code_3D_DeepSeek
            prompt_label = "DEEPSEEK-3D"
        else:
            system_prompt = Blueprint_to_Code_3D_Gemini
            prompt_label = "VERBOSE-3D"
    else:  # "2d"
        target_library = "matplotlib"
        if compact:
            system_prompt = Blueprint_to_Code_2D_DeepSeek
            prompt_label = "DEEPSEEK-2D"
        else:
            system_prompt = Blueprint_to_Code_2D_Gemini
            prompt_label = "VERBOSE-2D"

    logger.info(f"Using {prompt_label} prompt for {target_library} code generation")

    # Format blueprint section label based on mode
    blueprint_label = "JSON BLUEPRINT" if compact else "BLUEPRINT (coordinates.txt)"

    # NOTE: We intentionally do NOT pass the original question text to avoid
    # contamination (e.g., question phrases appearing as labels in the diagram).
    # The blueprint should be self-contained with all necessary information.
    user_message = (
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

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        start = time.time()
        logger.info(f"Calling DeepSeek-V3.2 for {target_library} code generation...")

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            max_tokens=16384,
            temperature=0.0,
        )
        elapsed = time.time() - start

        message = response.choices[0].message
        response_text = message.content
        usage = response.usage

        logger.debug(f"Response text length: {len(response_text) if response_text else 0}")
        logger.debug(f"Response text (first 500): {response_text[:500] if response_text else 'EMPTY'}")

        # Extract Python code from the response
        code = extract_python_code(response_text)
        if not code:
            logger.error(f"Full response text:\n{response_text}")
            return {"success": False, "error": "No Python code block found in response"}

        # Apply defensive post-processing
        code = postprocess_code(code, dimension_type)

        return {
            "success": True,
            "code": code,
            "api_call_duration": elapsed,
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
        }

    except Exception as e:
        logger.error(f"API call failed: {e}")
        return {"success": False, "error": str(e)}


def extract_python_code(response_text):
    # type: (str) -> Optional[str]
    """Extract Python code from a markdown response."""
    if not response_text:
        return None

    # Try ```python ... ``` blocks first
    blocks = re.findall(r"```python\s*(.*?)```", response_text, re.DOTALL)
    if blocks:
        return max(blocks, key=len).strip()

    # Try generic ``` ... ``` blocks
    blocks = re.findall(r"```\s*(.*?)```", response_text, re.DOTALL)
    for block in blocks:
        block = block.strip()
        if "import" in block and ("matplotlib" in block or "manim" in block):
            return block

    # Fallback: detect raw Python code without markdown formatting
    text = response_text.strip()

    # Strip trailing code block marker if present
    if text.endswith("```"):
        text = text[:-3].rstrip()

    # Strip bare language tag prefix
    if re.match(r"^python\s*\n", text):
        text = re.sub(r"^python\s*\n", "", text).strip()

    # Check if it looks like raw Python code
    is_raw_python = (
        text.startswith("#!/usr/bin/env python") or
        text.startswith("from manim import") or
        text.startswith("import matplotlib") or
        text.startswith("from matplotlib")
    )

    if is_raw_python and ("def " in text or "class " in text):
        return text

    return None


MANIM_HELPERS_PATH = Path(__file__).parent / "manim_helpers.py"
MATPLOTLIB_HELPERS_PATH = Path(__file__).parent / "matplotlib_helpers.py"

# Defense-in-depth: auto-patch common DeepSeek code generation mistakes.
# Set to False to disable post-processing and pass generated code through as-is.
ENABLE_CODE_POSTPROCESSING = True


def postprocess_code(code, dimension_type):
    # type: (str, str) -> str
    """Apply defensive patches to generated code to fix known DeepSeek mistakes.

    Only runs when ENABLE_CODE_POSTPROCESSING is True.
    Returns the (potentially modified) code string.
    """
    if not ENABLE_CODE_POSTPROCESSING:
        return code

    original = code
    patches_applied = []

    # --- 3D Manim patches ---
    if dimension_type == "3d":
        # 1. Replace Polyline(...) with VMobject(stroke_width=2).set_points_as_corners([...])
        #    Handles:  Polyline(*arc_points, color=X, stroke_width=N)
        polyline_pattern = re.compile(
            r'Polyline\(\s*\*(\w+)\s*,\s*color\s*=\s*([^,)]+)\s*,\s*stroke_width\s*=\s*(\d+)\s*\)'
        )
        if polyline_pattern.search(code):
            code = polyline_pattern.sub(
                r'VMobject(stroke_color=\2, stroke_width=\3).set_points_as_corners(\1)',
                code,
            )
            patches_applied.append("Polyline→VMobject.set_points_as_corners")

        # Simpler Polyline(*points) without keyword args
        simple_polyline = re.compile(r'Polyline\(\s*\*(\w+)\s*\)')
        if simple_polyline.search(code):
            code = simple_polyline.sub(
                r'VMobject(stroke_width=2).set_points_as_corners(\1)',
                code,
            )
            patches_applied.append("Polyline(simple)→VMobject.set_points_as_corners")

        # 2. Replace DashedLine3D with DashedLine
        if "DashedLine3D" in code:
            code = code.replace("DashedLine3D", "DashedLine")
            patches_applied.append("DashedLine3D→DashedLine")

        # 3. Replace rotation_matrix( with manual Rodrigues (common DeepSeek mistake)
        if "rotation_matrix(" in code and "from manim" in code:
            # Don't patch if it's defined locally — just warn
            patches_applied.append("WARNING: rotation_matrix() used (may not exist)")

        # 4. Ensure manim_helpers import for angle arc helper
        if "from manim_helpers import" not in code:
            if "create_3d_angle_arc_with_connections" in code:
                code = code.replace(
                    "from manim import *",
                    "from manim import *\nfrom manim_helpers import create_3d_angle_arc_with_connections",
                    1,
                )
                patches_applied.append("injected manim_helpers import")

        # 5. If model re-defined the helper function, strip it and ensure import
        redef_pattern = re.compile(
            r'^def create_3d_angle_arc_with_connections\(.*?\n(?:(?:    .*|)\n)*',
            re.MULTILINE,
        )
        if redef_pattern.search(code) and "from manim_helpers import" in code:
            code = redef_pattern.sub("", code)
            patches_applied.append("stripped re-defined helper function")

        # 6. Replace bare `opacity=` with `fill_opacity=` in Mobject constructors
        #    Manim Mobjects (Sphere, Polygon, etc.) don't accept `opacity` — they need `fill_opacity`.
        #    Only replace when it's a keyword arg (not inside .set_stroke() or .set_fill() which accept it).
        opacity_pattern = re.compile(
            r'(\b(?:Sphere|Polygon|Surface|Cube|Prism|Cone|Cylinder|Torus|Mobject)\s*\([^)]*?)'
            r'\bopacity\s*=',
        )
        if opacity_pattern.search(code):
            code = opacity_pattern.sub(r'\1fill_opacity=', code)
            patches_applied.append("opacity=→fill_opacity= in Mobject constructors")

        # 7. Fix aligned_left=True → aligned_edge=LEFT in next_to()
        #    DeepSeek sometimes uses the non-existent `aligned_left` kwarg.
        if "aligned_left" in code:
            code = code.replace("aligned_left=True", "aligned_edge=LEFT")
            patches_applied.append("aligned_left=True→aligned_edge=LEFT")

        # 8. Enforce frame_rate=10 and wait(4) for faster GIF rendering
        code = re.sub(r'config\.frame_rate\s*=\s*\d+', 'config.frame_rate = 10', code)
        code = re.sub(r'self\.wait\(\s*8\s*\)', 'self.wait(4)', code)
        # Fix Manim media path to match new frame rate
        code = re.sub(r'360p15', '360p10', code)

    # --- 2D Matplotlib patches ---
    if dimension_type in ("2d", "coordinate_2d"):
        # 1. Fix malformed plt.subplots() syntax error
        #    DeepSeek sometimes generates: fig, ax = plt.subplots(1, 1, figsize=(8.54, 4.80)
        #                                    fig.subplots_adjust(...), dpi=150)
        #    Should be: fig, ax = plt.subplots(1, 1, figsize=(8.54, 4.80), dpi=150)
        #               fig.subplots_adjust(...)
        subplots_bug = re.compile(
            r'(fig,\s*ax\s*=\s*plt\.subplots\([^)]*\([^)]*\))\s*\n\s*fig\.subplots_adjust\(([^)]*)\),\s*dpi=(\d+)\)'
        )
        if subplots_bug.search(code):
            code = subplots_bug.sub(r'\1, dpi=\3)\nfig.subplots_adjust(\2)', code)
            patches_applied.append("fixed plt.subplots() syntax error")

        # 2. Replace bare matplotlib.patheffects usage
        if "matplotlib.patheffects" in code and "import matplotlib.patheffects" not in code:
            # Remove the path_effects kwarg entirely — it's not worth fixing
            pe_pattern = re.compile(r',?\s*path_effects\s*=\s*\[.*?\]', re.DOTALL)
            if pe_pattern.search(code):
                code = pe_pattern.sub("", code)
                patches_applied.append("removed matplotlib.patheffects usage")

        # 3. Ensure matplotlib_helpers import if draw_angle_arc is used
        if "draw_angle_arc" in code and "from matplotlib_helpers import" not in code:
            code = code.replace(
                "from pathlib import Path",
                "from pathlib import Path\nfrom matplotlib_helpers import draw_angle_arc, draw_right_angle_marker",
                1,
            )
            patches_applied.append("injected matplotlib_helpers import")

        # 4. Fix centroid bug: points[p] for p in points.values() → list(points.values())
        #    DeepSeek sometimes generates: np.mean([points[p] for p in points.values()], axis=0)
        #    which fails with TypeError: unhashable type 'numpy.ndarray'
        centroid_bug = re.compile(
            r'np\.mean\(\[(\w+)\[(\w+)\]\s+for\s+\2\s+in\s+\1\.values\(\)\]'
        )
        if centroid_bug.search(code):
            code = centroid_bug.sub(
                lambda m: f'np.mean(list({m.group(1)}.values())',
                code,
            )
            patches_applied.append("fixed centroid unhashable-ndarray bug")

        # 4. Inject landscape aspect-ratio padding if only simple set_xlim/set_ylim present
        #    This prevents portrait-shaped images when Y range >> X range.
        simple_xlim = re.compile(
            r'ax\.set_xlim\(min\(all_x\)\s*-\s*x_range\s*\*\s*padding\s*,\s*max\(all_x\)\s*\+\s*x_range\s*\*\s*padding\)\s*\n'
            r'\s*ax\.set_ylim\(min\(all_y\)\s*-\s*y_range\s*\*\s*padding\s*,\s*max\(all_y\)\s*\+\s*y_range\s*\*\s*padding\)'
        )
        if simple_xlim.search(code) and "target_ratio" not in code:
            replacement = (
                "target_ratio = 8.54 / 4.80\n"
                "    data_ratio = x_range / y_range if y_range > 0 else target_ratio\n"
                "    x_center = (min(all_x) + max(all_x)) / 2\n"
                "    y_center = (min(all_y) + max(all_y)) / 2\n"
                "    if data_ratio < target_ratio:\n"
                "        x_range = y_range * target_ratio\n"
                "    if data_ratio > target_ratio:\n"
                "        y_range = x_range / target_ratio\n"
                "    ax.set_xlim(x_center - x_range/2 * (1 + padding), x_center + x_range/2 * (1 + padding))\n"
                "    ax.set_ylim(y_center - y_range/2 * (1 + padding), y_center + y_range/2 * (1 + padding))"
            )
            code = simple_xlim.sub(replacement, code)
            patches_applied.append("injected landscape aspect-ratio padding")

        # 5. Remove bbox_inches='tight' from savefig — it overrides figsize and creates
        #    portrait images when data is taller than wide, even with landscape padding.
        bbox_tight = re.compile(r",?\s*bbox_inches\s*=\s*['\"]tight['\"]")
        if bbox_tight.search(code):
            code = bbox_tight.sub("", code)
            patches_applied.append("removed bbox_inches='tight' from savefig")

        # 6. Inject fig.subplots_adjust to remove default matplotlib margins
        #    Without this, ~12% white borders surround the axes even with axis('off').
        if "subplots_adjust" not in code and "plt.subplots(" in code:
            code = re.sub(
                r'(fig\s*,\s*ax\s*=\s*plt\.subplots\([^)]*\))',
                r"\1\nfig.subplots_adjust(left=0, right=1, top=1, bottom=0)",
                code,
            )
            patches_applied.append("injected fig.subplots_adjust for zero margins")

    if patches_applied:
        logger.info(f"Post-processing applied {len(patches_applied)} patch(es): {', '.join(patches_applied)}")

    return code


def ensure_helpers(code_dir, dimension_type="3d"):
    # type: (str, str) -> None
    """Copy helper files into the code directory so render_code.py can import them."""
    # Always copy manim_helpers for 3D
    if dimension_type == "3d":
        dst = Path(code_dir) / "manim_helpers.py"
        if MANIM_HELPERS_PATH.exists() and not dst.exists():
            shutil.copy2(str(MANIM_HELPERS_PATH), str(dst))

    # Always copy matplotlib_helpers for 2D
    if dimension_type in ("2d", "coordinate_2d"):
        dst = Path(code_dir) / "matplotlib_helpers.py"
        if MATPLOTLIB_HELPERS_PATH.exists() and not dst.exists():
            shutil.copy2(str(MATPLOTLIB_HELPERS_PATH), str(dst))


MANIM_CLI_PATH = "/Users/kairos/.local/bin/manim"


def execute_code(code_path, timeout=120, use_manim_cli=False, output_path=None, dimension_type="3d"):
    # type: (str, int, bool, Optional[str], str) -> dict
    """Execute the generated Python script.

    For 3D manim code, use_manim_cli=True to invoke the manim CLI directly
    (works with Python 3.13 where manim is installed).

    Returns dict with keys: success, stdout, stderr, returncode.
    """
    code_dir = str(Path(code_path).parent)
    ensure_helpers(code_dir, dimension_type=dimension_type)

    try:
        if use_manim_cli and Path(MANIM_CLI_PATH).exists():
            result = subprocess.run(
                [MANIM_CLI_PATH, "render", str(code_path), "GeometryScene", "-ql", "--format", "gif"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=code_dir,
            )
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
        description="Generate rendering code from blueprint using DeepSeek-V3.2 and execute it"
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
        stripped = blueprint_text.strip()
        is_json = stripped.startswith("{") and stripped.endswith("}")

    compact_mode = args.compact or is_json
    if is_json and not args.compact:
        logger.info("Auto-detected JSON blueprint; using compact mode")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("DEEPSEEK_API_KEY environment variable not set")
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

        with open(code_path, "w", encoding="utf-8") as f:
            f.write(result["code"])
        logger.info(f"Saved render code to: {code_path}")

        logger.info("Executing generated code...")
        use_manim = (dimension_type == "3d")
        exec_result = execute_code(str(code_path), use_manim_cli=use_manim, output_path=output_path, dimension_type=dimension_type)

        if exec_result["stdout"]:
            for line in exec_result["stdout"].strip().split("\n"):
                logger.info(f"  [render] {line}")

        if exec_result["success"]:
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
