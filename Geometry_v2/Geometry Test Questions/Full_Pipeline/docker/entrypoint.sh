#!/bin/bash
# ============================================================================
# SANDBOXED MANIM RENDERER - ENTRYPOINT SCRIPT
# ============================================================================
# This script handles the secure execution of Manim rendering within the
# Docker container. It validates inputs, runs the render, and copies output.
#
# Security measures:
# - Input validation before execution
# - Controlled file operations
# - Error handling without exposing system details
# - Timeout enforcement
# ============================================================================

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================
INPUT_DIR="/input"
OUTPUT_DIR="/output"
WORK_DIR="/work"
DEFAULT_QUALITY="ql"
MAX_RENDER_TIME=600  # 10 minutes max per scene

# Colors for output (if terminal supports it)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << 'EOF'
============================================================================
SANDBOXED MANIM RENDERER
============================================================================

Usage: docker run [options] manim-sandbox [command] [arguments]

Commands:
  render          Render all scenes from all_scenes.py
  render-scene    Render a specific scene by name
  validate        Validate input files without rendering
  test            Run a quick test to verify the environment
  --help          Show this help message

Options (passed via environment variables):
  QUALITY         Render quality: ql (480p), qm (720p), qh (1080p)
                  Default: ql
  MAX_TIME        Maximum render time per scene in seconds
                  Default: 600

Examples:
  # Render all scenes at low quality
  docker run --rm \
    -v ./input:/input:ro \
    -v ./output:/output \
    manim-sandbox render

  # Render at high quality
  docker run --rm \
    -e QUALITY=qh \
    -v ./input:/input:ro \
    -v ./output:/output \
    manim-sandbox render

  # Render specific scene
  docker run --rm \
    -v ./input:/input:ro \
    -v ./output:/output \
    manim-sandbox render-scene IntroScene

  # Validate files only (no rendering)
  docker run --rm \
    -v ./input:/input:ro \
    manim-sandbox validate

Security Notes:
  - Input directory is mounted read-only
  - Container runs as non-root user 'sandbox'
  - No network access when using docker-compose
  - Resource limits enforced via Docker

============================================================================
EOF
}

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

validate_input_files() {
    log_info "Validating input files..."

    # Check if input directory exists and has files
    if [ ! -d "$INPUT_DIR" ]; then
        log_error "Input directory not found. Mount with: -v ./input:/input:ro"
        return 1
    fi

    # Check for all_scenes.py
    if [ ! -f "$INPUT_DIR/all_scenes.py" ]; then
        log_error "all_scenes.py not found in input directory"
        return 1
    fi

    # Basic syntax check on all_scenes.py (catches obvious errors)
    # Use ast.parse instead of py_compile to avoid writing .pyc to read-only mount
    if ! python -c "import ast; ast.parse(open('$INPUT_DIR/all_scenes.py').read())" 2>/dev/null; then
        log_error "all_scenes.py has syntax errors"
        return 1
    fi

    log_success "all_scenes.py found and syntax valid"

    # Check for optional files
    if [ -d "$INPUT_DIR/Audio" ]; then
        audio_count=$(find "$INPUT_DIR/Audio" -name "*.mp3" 2>/dev/null | wc -l)
        log_info "Found $audio_count audio files in Audio/"
    fi

    if [ -d "$INPUT_DIR/Scene" ]; then
        scene_audio_count=$(find "$INPUT_DIR/Scene" -name "*.mp3" 2>/dev/null | wc -l)
        log_info "Found $scene_audio_count scene audio files in Scene/"
    fi

    if [ -f "$INPUT_DIR/figure.py" ]; then
        log_success "figure.py found (geometric definitions)"
    fi

    return 0
}

validate_python_safety() {
    # Basic safety checks on the Python code
    # This is NOT a complete sandbox - Docker provides the real isolation
    # These checks catch obvious dangerous patterns

    log_info "Running basic safety checks on code..."

    local file="$INPUT_DIR/all_scenes.py"

    # Check for obviously dangerous imports
    local dangerous_patterns=(
        "import os"
        "import subprocess"
        "import socket"
        "import requests"
        "from os import"
        "from subprocess import"
        "__import__"
        "eval("
        "exec("
        "compile("
        "open("
        "builtins"
        "globals()"
        "locals()"
    )

    local warnings=0
    for pattern in "${dangerous_patterns[@]}"; do
        if grep -q "$pattern" "$file" 2>/dev/null; then
            # Allow specific safe uses
            case "$pattern" in
                "open(")
                    # Check if it's file I/O (dangerous) vs manim's open
                    if grep -E "open\s*\(['\"]" "$file" >/dev/null 2>&1; then
                        log_warning "Potential file I/O detected: $pattern"
                        ((warnings++))
                    fi
                    ;;
                *)
                    log_warning "Potentially dangerous pattern detected: $pattern"
                    ((warnings++))
                    ;;
            esac
        fi
    done

    if [ $warnings -gt 0 ]; then
        log_warning "$warnings potentially dangerous patterns found"
        log_warning "Docker isolation will contain any malicious behavior"
    else
        log_success "No obviously dangerous patterns detected"
    fi

    return 0
}

# ============================================================================
# RENDERING FUNCTIONS
# ============================================================================

setup_workspace() {
    log_info "Setting up workspace..."

    # Copy input files to work directory
    cp "$INPUT_DIR/all_scenes.py" "$WORK_DIR/"

    # Copy optional files if they exist
    [ -f "$INPUT_DIR/figure.py" ] && cp "$INPUT_DIR/figure.py" "$WORK_DIR/"

    # Copy audio directories if they exist
    if [ -d "$INPUT_DIR/Audio" ]; then
        cp -r "$INPUT_DIR/Audio" "$WORK_DIR/"
        log_info "Copied Audio/ directory"
    fi

    if [ -d "$INPUT_DIR/Scene" ]; then
        cp -r "$INPUT_DIR/Scene" "$WORK_DIR/"
        log_info "Copied Scene/ directory"
    fi

    log_success "Workspace ready"
}

extract_scene_names() {
    # Extract scene class names from all_scenes.py
    python3 << 'PYTHON_SCRIPT'
import re
import sys

try:
    with open('/work/all_scenes.py', 'r') as f:
        content = f.read()

    # Find all class definitions that inherit from Scene or ThreeDScene
    pattern = r'class\s+(\w+Scene)\s*\((?:Scene|ThreeDScene)\):'
    matches = re.findall(pattern, content)

    if matches:
        for scene in matches:
            print(scene)
    else:
        sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT
}

render_scene() {
    local scene_name="$1"
    local quality="${QUALITY:-$DEFAULT_QUALITY}"

    log_info "Rendering scene: $scene_name (quality: -q$quality)"

    cd "$WORK_DIR"

    # Run manim with timeout
    if timeout "$MAX_RENDER_TIME" manim -q"$quality" --disable_caching all_scenes.py "$scene_name"; then
        log_success "Rendered: $scene_name"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            log_error "Render timeout after ${MAX_RENDER_TIME}s: $scene_name"
        else
            log_error "Render failed: $scene_name (exit code: $exit_code)"
        fi
        return 1
    fi
}

render_all_scenes() {
    local quality="${QUALITY:-$DEFAULT_QUALITY}"

    log_info "Starting render of all scenes..."
    log_info "Quality setting: -q$quality"

    # Extract scene names
    local scenes
    scenes=$(extract_scene_names)

    if [ -z "$scenes" ]; then
        log_error "No scene classes found in all_scenes.py"
        return 1
    fi

    local total=$(echo "$scenes" | wc -l)
    local current=0
    local failed=0

    log_info "Found $total scenes to render"
    echo "----------------------------------------"

    while IFS= read -r scene; do
        ((current++))
        echo ""
        log_info "[$current/$total] Processing: $scene"

        if ! render_scene "$scene"; then
            ((failed++))
            log_error "Scene $scene failed - stopping"
            return 1
        fi
    done <<< "$scenes"

    echo ""
    echo "========================================"
    log_success "All $total scenes rendered successfully"

    return 0
}

copy_output() {
    log_info "Copying rendered files to output..."

    # Find and copy all rendered MP4 files
    local video_count=0

    if [ -d "$WORK_DIR/media/videos" ]; then
        find "$WORK_DIR/media/videos" -name "*.mp4" -exec cp {} "$OUTPUT_DIR/" \;
        video_count=$(find "$OUTPUT_DIR" -name "*.mp4" 2>/dev/null | wc -l)
    fi

    if [ $video_count -gt 0 ]; then
        log_success "Copied $video_count video files to output"

        # List output files
        log_info "Output files:"
        ls -lh "$OUTPUT_DIR"/*.mp4 2>/dev/null | while read line; do
            echo "  $line"
        done
    else
        log_warning "No video files found to copy"
    fi
}

run_test() {
    log_info "Running environment test..."

    # Test Python
    python --version

    # Test Manim import
    if python -c "import manim; print(f'Manim version: {manim.__version__}')"; then
        log_success "Manim import OK"
    else
        log_error "Manim import failed"
        return 1
    fi

    # Test FFmpeg
    if ffmpeg -version | head -1; then
        log_success "FFmpeg OK"
    else
        log_error "FFmpeg not available"
        return 1
    fi

    # Test LaTeX
    if latex --version | head -1; then
        log_success "LaTeX OK"
    else
        log_warning "LaTeX not fully available (some features may not work)"
    fi

    # Quick render test
    log_info "Running quick render test..."
    cat > /work/test_scene.py << 'EOF'
from manim import *
class TestScene(Scene):
    def construct(self):
        circle = Circle()
        self.play(Create(circle))
        self.wait(0.5)
EOF

    cd /work
    if timeout 120 manim -ql --disable_caching test_scene.py TestScene >/dev/null 2>&1; then
        log_success "Render test passed"
        rm -f /work/test_scene.py
    else
        log_error "Render test failed"
        rm -f /work/test_scene.py
        return 1
    fi

    log_success "All tests passed - environment is ready"
    return 0
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    local command="${1:-}"

    echo "========================================"
    echo "  SANDBOXED MANIM RENDERER"
    echo "========================================"
    echo ""

    case "$command" in
        render)
            validate_input_files || exit 1
            validate_python_safety
            setup_workspace
            render_all_scenes || exit 1
            copy_output
            log_success "Rendering complete!"
            ;;

        render-scene)
            local scene_name="${2:-}"
            if [ -z "$scene_name" ]; then
                log_error "Scene name required. Usage: render-scene SceneName"
                exit 1
            fi
            validate_input_files || exit 1
            setup_workspace
            render_scene "$scene_name" || exit 1
            copy_output
            ;;

        validate)
            validate_input_files || exit 1
            validate_python_safety
            log_success "Validation complete - files are ready for rendering"
            ;;

        test)
            run_test
            ;;

        --help|-h|help|"")
            show_help
            ;;

        *)
            log_error "Unknown command: $command"
            echo "Run with --help for usage information"
            exit 1
            ;;
    esac
}

# Run main with all arguments
main "$@"
