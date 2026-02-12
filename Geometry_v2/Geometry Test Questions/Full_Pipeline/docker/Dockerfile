# ============================================================================
# SANDBOXED MANIM RENDERER
# ============================================================================
# This Dockerfile creates a secure, isolated environment for executing
# AI-generated Manim code. It provides multiple layers of security to
# prevent malicious code from escaping the container.
#
# Security Features:
# 1. Non-root user execution
# 2. Minimal base image (Debian slim)
# 3. Read-only root filesystem support
# 4. Resource limits via Docker/compose
# 5. No network access (configured in docker-compose)
# 6. Seccomp profile support
# 7. Dropped Linux capabilities
# 8. Temporary filesystem for /tmp
#
# Usage:
#   docker build -t manim-sandbox .
#   docker run --rm -v ./input:/input:ro -v ./output:/output manim-sandbox
# ============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and compile what's needed
# ------------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for clean dependency management
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python packages
# Using specific versions for reproducibility and security auditing
COPY requirements-docker.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Runtime - Minimal image with only what's needed to run
# ------------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

# ============================================================================
# LABELS - Container metadata
# ============================================================================
LABEL maintainer="geometry-video-generator"
LABEL description="Sandboxed environment for rendering AI-generated Manim animations"
LABEL security.sandbox="true"
LABEL version="1.0"

# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================
# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Python optimizations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random

# Manim configuration
ENV MANIM_OUTPUT_DIR=/output
ENV MPLBACKEND=Agg

# Security: Disable Python's ability to write .pyc files (reduces attack surface)
ENV PYTHONDONTWRITEBYTECODE=1

# ============================================================================
# INSTALL RUNTIME DEPENDENCIES
# ============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # FFmpeg for video encoding
    ffmpeg \
    # Cairo and Pango for graphics rendering
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    # LaTeX for mathematical text rendering
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-science \
    dvipng \
    # Fonts
    fonts-freefont-ttf \
    # OpenGL for 3D rendering (software renderer)
    libosmesa6 \
    libgl1-mesa-glx \
    # Audio processing
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ============================================================================
# COPY PYTHON ENVIRONMENT FROM BUILDER
# ============================================================================
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ============================================================================
# CREATE NON-ROOT USER FOR SECURITY
# ============================================================================
# Running as non-root prevents many privilege escalation attacks
RUN groupadd --gid 1000 sandbox && \
    useradd --uid 1000 --gid sandbox --shell /bin/false --create-home sandbox

# ============================================================================
# CREATE DIRECTORY STRUCTURE
# ============================================================================
# /input  - Read-only mount point for AI-generated code and assets
# /output - Write-enabled mount point for rendered videos
# /work   - Working directory for Manim (owned by sandbox user)

RUN mkdir -p /input /output /work /work/media && \
    chown -R sandbox:sandbox /work /output

# ============================================================================
# COPY ENTRYPOINT SCRIPT
# ============================================================================
COPY --chmod=755 entrypoint.sh /entrypoint.sh

# ============================================================================
# SECURITY HARDENING
# ============================================================================
# Remove potentially dangerous commands
RUN rm -f /usr/bin/wget /usr/bin/curl 2>/dev/null || true

# Make the system read-only friendly (logs to stdout)
RUN ln -sf /dev/stdout /var/log/manim.log

# ============================================================================
# RUNTIME CONFIGURATION
# ============================================================================
WORKDIR /work

# Switch to non-root user
USER sandbox

# Health check - verify Manim is working
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import manim; print('OK')" || exit 1

# ============================================================================
# ENTRYPOINT
# ============================================================================
ENTRYPOINT ["/entrypoint.sh"]

# Default command: show help
CMD ["--help"]
