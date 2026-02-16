#!/usr/bin/env python3
"""
Diagnostic script to identify 2D coordinate geometry failures.
Tests the full pipeline for a simple coordinate_2D question.
"""

import os
import sys
import subprocess
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(".env")

# Test question
TEST_QUESTION = {
    "id": "coord_test",
    "name": "Test 2D Coord",
    "text": """The straight lines L₁: 2x + y = 8 and L₂: x - y = 1 intersect at point P.
(a) Find the coordinates of P.
(b) Points A and B lie on L₁ such that A is on the y-axis and B is on the x-axis.
Find the coordinates of A and B.""",
    "dimension_type": "coordinate_2d"
}

print("=" * 80)
print("2D COORDINATE GEOMETRY DIAGNOSTIC TEST")
print("=" * 80)
print()

# Step 1: Test classification
print("Step 1: Classification")
print("-" * 80)
try:
    from classify_geometry_type import classify_geometry_type

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ GEMINI_API_KEY not set")
        sys.exit(1)

    # Validate key format
    gemini_key = gemini_key.strip()
    print(f"   Using GEMINI_API_KEY: {gemini_key[:10]}...{gemini_key[-4:]}")

    result = classify_geometry_type(gemini_key, TEST_QUESTION["text"])
    detected = result.get("dimension_type", "unknown")
    print(f"✅ Detected dimension: {detected}")
    print(f"   Expected: coordinate_2d")
    print(f"   Match: {'✅' if detected == 'coordinate_2d' else '❌'}")
    print()
except Exception as e:
    print(f"❌ Classification failed: {e}")
    sys.exit(1)

# Step 2: Test blueprint generation
print("Step 2: Blueprint Generation")
print("-" * 80)
try:
    from generate_blueprint_focused import generate_blueprint

    output_dir = Path("test_output/coord_2d_diagnostic")
    output_dir.mkdir(parents=True, exist_ok=True)

    bp_result = generate_blueprint(
        gemini_key,
        TEST_QUESTION["text"],
        str(output_dir),
        dimension_type="coordinate_2d"
    )

    if bp_result["success"]:
        print(f"✅ Blueprint generated")
        print(f"   Tokens: {bp_result['prompt_tokens']} in, {bp_result['completion_tokens']} out")
        blueprint = bp_result["blueprint"]
        print(f"   Blueprint length: {len(blueprint)} chars")

        # Check for key coordinate_2d features
        if "coordinate_range" in blueprint:
            print("   ✅ Has coordinate_range")
        else:
            print("   ⚠️  Missing coordinate_range")

        if "axes" in blueprint:
            print("   ✅ Has axes declaration")
        else:
            print("   ⚠️  Missing axes declaration")

        print()
    else:
        print(f"❌ Blueprint failed: {bp_result.get('error', 'Unknown error')}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Blueprint generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Test code generation
print("Step 3: Code Generation (DeepSeek)")
print("-" * 80)
try:
    from generate_code_deepseek import generate_render_code

    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_key:
        print("❌ DEEPSEEK_API_KEY not set")
        sys.exit(1)

    code_path = str(output_dir / "render_code.py")

    code_result = generate_render_code(
        deepseek_key,
        blueprint,
        code_path,
        output_format="png",
        dimension_type="coordinate_2d"
    )

    if code_result["success"]:
        print(f"✅ Code generated")
        print(f"   Tokens: {code_result['prompt_tokens']} in, {code_result['completion_tokens']} out")
        print(f"   Code length: {len(code_result['code'])} chars")

        # Check for syntax issues
        code = code_result["code"]
        if "fig.subplots_adjust" in code:
            # Check the plt.subplots pattern
            import re
            bad_pattern = re.search(
                r'fig,\s*ax\s*=\s*plt\.subplots\([^)]*\)\s*\n\s*fig\.subplots_adjust\([^)]*\),\s*dpi=',
                code
            )
            if bad_pattern:
                print("   ❌ Found plt.subplots syntax bug (SHOULD HAVE BEEN FIXED!)")
            else:
                print("   ✅ plt.subplots syntax looks correct")

        # Try to parse the code
        try:
            compile(code, code_path, 'exec')
            print("   ✅ Code syntax is valid")
        except SyntaxError as e:
            print(f"   ❌ Syntax error: {e}")
            print(f"      Line {e.lineno}: {e.text}")
            print()
            print("Generated code around error:")
            lines = code.split('\n')
            start = max(0, e.lineno - 5)
            end = min(len(lines), e.lineno + 5)
            for i in range(start, end):
                marker = ">>>" if i == e.lineno - 1 else "   "
                print(f"{marker} {i+1:4d}: {lines[i]}")
            sys.exit(1)

        print()
    else:
        print(f"❌ Code generation failed: {code_result.get('error', 'Unknown error')}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Code generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Test code execution
print("Step 4: Code Execution")
print("-" * 80)
try:
    result = subprocess.run(
        ["python3", code_path],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode == 0:
        print("✅ Code executed successfully")
        print(f"   Output: {result.stdout.strip()}")

        # Check if output file exists
        output_file = output_dir / "diagram.png"
        if output_file.exists():
            size = output_file.stat().st_size
            print(f"   ✅ Output file created: {output_file}")
            print(f"   Size: {size:,} bytes")
        else:
            print(f"   ⚠️  Output file not found: {output_file}")
        print()
    else:
        print(f"❌ Execution failed with return code {result.returncode}")
        print(f"   stdout: {result.stdout}")
        print(f"   stderr: {result.stderr}")
        sys.exit(1)

except subprocess.TimeoutExpired:
    print("❌ Execution timed out (>30s)")
    sys.exit(1)
except Exception as e:
    print(f"❌ Execution failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("✅ ALL TESTS PASSED")
print("=" * 80)
print()
print(f"Output directory: {output_dir}")
print("Files created:")
for f in output_dir.glob("*"):
    print(f"  - {f.name} ({f.stat().st_size:,} bytes)")
