#!/bin/bash
# Run manim rendering in Docker container

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Docker is available
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found. Please install Docker Desktop."
    exit 1
fi

# Build the image if needed
echo "Building manim Docker image..."
docker compose build

# Run the rendering
echo "Running manim render..."
docker compose run --rm manim

# Check for output
if ls output/*.gif 1> /dev/null 2>&1 || ls output/*.mp4 1> /dev/null 2>&1; then
    echo "Success! Output saved to docker/output/"
    ls -la output/
else
    echo "Warning: No output files found in docker/output/"
fi
