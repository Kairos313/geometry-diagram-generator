#!/bin/bash
# ============================================================================
# SANDBOXED MANIM RENDER HELPER
# ============================================================================
# This script provides a convenient interface for running the sandboxed
# Manim renderer. It handles directory setup, Docker execution, and cleanup.
#
# Usage:
#   ./render.sh                    # Render with defaults
#   ./render.sh --quality qh       # High quality render
#   ./render.sh --test             # Test the environment
#   ./render.sh --build            # Rebuild the Docker image
#
# ============================================================================

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$SCRIPT_DIR"
INPUT_DIR="$DOCKER_DIR/input"
OUTPUT_DIR="$DOCKER_DIR/output"
IMAGE_NAME="manim-sandbox:latest"

# Default settings
QUALITY="ql"
MAX_TIME=600
USE_COMPOSE=true
HARDENED=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

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

log_header() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

show_help() {
    cat << 'EOF'
SANDBOXED MANIM RENDER HELPER
=============================

This script helps you run AI-generated Manim code in a secure Docker sandbox.

USAGE:
    ./render.sh [OPTIONS] [COMMAND]

COMMANDS:
    render              Render all scenes (default)
    test                Test the Docker environment
    validate            Validate input files only
    build               Build/rebuild the Docker image
    clean               Remove output files
    prepare             Copy files from pipeline to input/

OPTIONS:
    -q, --quality LEVEL     Set render quality: ql (480p), qm (720p), qh (1080p)
                            Default: ql
    -t, --timeout SECONDS   Max render time per scene
                            Default: 600
    --hardened              Use hardened security profile
    --no-compose            Use docker run instead of docker-compose
    -h, --help              Show this help

EXAMPLES:
    # Prepare input files from the pipeline and render
    ./render.sh prepare
    ./render.sh render

    # One-liner: prepare and render at high quality
    ./render.sh prepare && ./render.sh -q qh render

    # Test the environment
    ./render.sh test

    # Build the Docker image
    ./render.sh build

DIRECTORY STRUCTURE:
    docker/
    ├── Dockerfile              # Container definition
    ├── docker-compose.yml      # Security configuration
    ├── entrypoint.sh           # Container entrypoint
    ├── render.sh               # This helper script
    ├── input/                  # Input files (created by 'prepare')
    │   ├── all_scenes.py       # Generated Manim scenes
    │   ├── figure.py           # Geometric definitions
    │   ├── Audio/              # Audio files
    │   └── Scene/              # Scene audio files
    └── output/                 # Rendered videos (created automatically)

SECURITY:
    The Docker container runs with:
    - No network access
    - Non-root user
    - Resource limits (CPU, memory, processes)
    - Dropped Linux capabilities
    - Read-only input mount

EOF
}

# ============================================================================
# SETUP FUNCTIONS
# ============================================================================

setup_directories() {
    log_info "Setting up directories..."

    mkdir -p "$INPUT_DIR" "$OUTPUT_DIR"
    log_success "Directories ready: input/, output/"
}

prepare_input_files() {
    log_header "PREPARING INPUT FILES"

    setup_directories

    # Copy files from the pipeline directory
    local files_copied=0

    # all_scenes.py (required)
    if [ -f "$PIPELINE_DIR/all_scenes.py" ]; then
        cp "$PIPELINE_DIR/all_scenes.py" "$INPUT_DIR/"
        log_success "Copied all_scenes.py"
        ((files_copied++))
    else
        log_error "all_scenes.py not found in pipeline directory"
        log_error "Expected at: $PIPELINE_DIR/all_scenes.py"
        return 1
    fi

    # figure.py (optional but recommended)
    if [ -f "$PIPELINE_DIR/figure.py" ]; then
        cp "$PIPELINE_DIR/figure.py" "$INPUT_DIR/"
        log_success "Copied figure.py"
        ((files_copied++))
    else
        log_warning "figure.py not found (optional)"
    fi

    # Audio directory (optional)
    if [ -d "$PIPELINE_DIR/Audio" ]; then
        rm -rf "$INPUT_DIR/Audio" 2>/dev/null || true
        cp -r "$PIPELINE_DIR/Audio" "$INPUT_DIR/"
        local audio_count=$(find "$INPUT_DIR/Audio" -name "*.mp3" | wc -l)
        log_success "Copied Audio/ directory ($audio_count files)"
        ((files_copied++))
    else
        log_warning "Audio/ directory not found (optional)"
    fi

    # Scene directory (optional)
    if [ -d "$PIPELINE_DIR/Scene" ]; then
        rm -rf "$INPUT_DIR/Scene" 2>/dev/null || true
        cp -r "$PIPELINE_DIR/Scene" "$INPUT_DIR/"
        local scene_count=$(find "$INPUT_DIR/Scene" -name "*.mp3" | wc -l)
        log_success "Copied Scene/ directory ($scene_count files)"
        ((files_copied++))
    else
        log_warning "Scene/ directory not found (optional)"
    fi

    echo ""
    log_success "Prepared $files_copied items for rendering"
    log_info "Input directory: $INPUT_DIR"

    # Show what's in the input directory
    echo ""
    log_info "Input directory contents:"
    ls -la "$INPUT_DIR"
}

# ============================================================================
# DOCKER FUNCTIONS
# ============================================================================

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        log_error "Install Docker from: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        log_error "Start Docker and try again"
        exit 1
    fi
}

build_image() {
    log_header "BUILDING DOCKER IMAGE"

    cd "$DOCKER_DIR"

    log_info "Building manim-sandbox image..."
    log_info "This may take several minutes on first build..."

    if docker build -t "$IMAGE_NAME" .; then
        log_success "Image built successfully: $IMAGE_NAME"
    else
        log_error "Failed to build Docker image"
        exit 1
    fi
}

check_image() {
    if ! docker image inspect "$IMAGE_NAME" &> /dev/null; then
        log_warning "Docker image not found, building..."
        build_image
    fi
}

run_render() {
    log_header "RUNNING SANDBOXED RENDER"

    check_docker
    check_image
    setup_directories

    # Verify input files exist
    if [ ! -f "$INPUT_DIR/all_scenes.py" ]; then
        log_error "No input files found"
        log_error "Run './render.sh prepare' first to copy files from the pipeline"
        exit 1
    fi

    log_info "Quality: -q$QUALITY"
    log_info "Timeout: ${MAX_TIME}s per scene"
    log_info "Input: $INPUT_DIR"
    log_info "Output: $OUTPUT_DIR"
    echo ""

    cd "$DOCKER_DIR"

    if [ "$USE_COMPOSE" = true ]; then
        local profile_arg=""
        local service="renderer"

        if [ "$HARDENED" = true ]; then
            profile_arg="--profile hardened"
            service="renderer-hardened"
            log_info "Using hardened security profile"
        fi

        QUALITY="$QUALITY" MAX_TIME="$MAX_TIME" \
            docker-compose $profile_arg run --rm "$service" render
    else
        # Direct docker run (without compose)
        docker run --rm \
            --network none \
            --cap-drop ALL \
            --security-opt no-new-privileges:true \
            --memory 8g \
            --cpus 4 \
            --ulimit nproc=256 \
            -e QUALITY="$QUALITY" \
            -e MAX_TIME="$MAX_TIME" \
            -v "$INPUT_DIR:/input:ro" \
            -v "$OUTPUT_DIR:/output" \
            "$IMAGE_NAME" render
    fi

    echo ""
    log_header "RENDER COMPLETE"

    # Show output files
    if ls "$OUTPUT_DIR"/*.mp4 &> /dev/null; then
        log_success "Rendered videos:"
        ls -lh "$OUTPUT_DIR"/*.mp4
    else
        log_warning "No output videos found"
    fi
}

run_test() {
    log_header "TESTING ENVIRONMENT"

    check_docker
    check_image

    cd "$DOCKER_DIR"

    if [ "$USE_COMPOSE" = true ]; then
        docker-compose run --rm renderer test
    else
        docker run --rm "$IMAGE_NAME" test
    fi
}

run_validate() {
    log_header "VALIDATING INPUT FILES"

    check_docker
    check_image
    setup_directories

    cd "$DOCKER_DIR"

    if [ "$USE_COMPOSE" = true ]; then
        docker-compose run --rm renderer validate
    else
        docker run --rm \
            -v "$INPUT_DIR:/input:ro" \
            "$IMAGE_NAME" validate
    fi
}

clean_output() {
    log_header "CLEANING OUTPUT"

    if [ -d "$OUTPUT_DIR" ]; then
        rm -rf "$OUTPUT_DIR"/*
        log_success "Cleaned output directory"
    else
        log_info "Output directory doesn't exist"
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    local command="render"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -q|--quality)
                QUALITY="$2"
                shift 2
                ;;
            -t|--timeout)
                MAX_TIME="$2"
                shift 2
                ;;
            --hardened)
                HARDENED=true
                shift
                ;;
            --no-compose)
                USE_COMPOSE=false
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            render|test|validate|build|clean|prepare)
                command="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Execute command
    case "$command" in
        render)
            run_render
            ;;
        test)
            run_test
            ;;
        validate)
            run_validate
            ;;
        build)
            build_image
            ;;
        clean)
            clean_output
            ;;
        prepare)
            prepare_input_files
            ;;
        *)
            log_error "Unknown command: $command"
            exit 1
            ;;
    esac
}

# Run main
main "$@"
