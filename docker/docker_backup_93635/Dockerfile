FROM python:3.11-slim

# Install system dependencies for manim (including build tools for pycairo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

# Install manim
RUN pip install --no-cache-dir manim numpy

# Create working directory
WORKDIR /app

# Default command
CMD ["python3", "/app/input/render_code.py"]
