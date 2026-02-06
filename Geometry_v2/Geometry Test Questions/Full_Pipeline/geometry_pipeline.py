#!/usr/bin/env python3
"""
Geometry Diagram Pipeline — Orchestrator (v2)

2-stage pipeline that converts geometry question text into a diagram.

Stages:
  1. generate_blueprint.py  → coordinates.txt       (Gemini 3 Flash via Google GenAI)
  2. generate_code.py       → render + output image  (Gemini 3 Flash via Google GenAI)

Usage:
    python3 geometry_pipeline.py --question-text "In triangle ABC, angle ACB = 90°, AD = 12cm."
    python3 geometry_pipeline.py --question-text question.txt --question-image q.png --output-format svg
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class GeometryPipeline:
    """Orchestrate the 2-stage geometry diagram pipeline."""

    def __init__(
        self,
        question_text,       # type: str
        question_image=None, # type: str
        output_format="png", # type: str
    ):
        self.question_text = question_text
        self.question_image = question_image
        self.output_format = output_format
        self.pipeline_dir = Path(__file__).parent
        self.output_dir = self.pipeline_dir / "output"
        self.start_time = time.time()

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    def step_1_generate_blueprint(self):
        # type: () -> bool
        """Stage 1: Question text → coordinates.txt."""
        logger.info("=== Stage 1: Generating blueprint ===")
        cmd = [
            sys.executable,
            str(self.pipeline_dir / "generate_blueprint.py"),
            "--question-text", self.question_text,
        ]
        if self.question_image:
            cmd.extend(["--question-image", self.question_image])
        if not self._run(cmd, "Stage 1"):
            return False
        return self._validate(self.pipeline_dir / "coordinates.txt", "Stage 1")

    def step_2_generate_and_render(self):
        # type: () -> bool
        """Stage 2: coordinates.txt → rendered diagram."""
        logger.info("=== Stage 2: Generating code & rendering ===")
        output_path = str(self.output_dir / f"diagram.{self.output_format}")
        cmd = [
            sys.executable,
            str(self.pipeline_dir / "generate_code.py"),
            "--coordinates", str(self.pipeline_dir / "coordinates.txt"),
            "--output", output_path,
            "--format", self.output_format,
        ]
        return self._run(cmd, "Stage 2")

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run(self):
        # type: () -> bool
        """Execute the full 2-stage pipeline."""
        logger.info("=" * 60)
        logger.info("GEOMETRY DIAGRAM PIPELINE (v2)")
        logger.info(f"Question: {self.question_text[:100]}...")
        logger.info(f"Image: {self.question_image or 'none'}")
        logger.info(f"Format: {self.output_format}")
        logger.info("=" * 60)

        # Validate image if provided
        if self.question_image and not Path(self.question_image).exists():
            logger.error(f"Question image not found: {self.question_image}")
            return False

        for step_fn in [
            self.step_1_generate_blueprint,
            self.step_2_generate_and_render,
        ]:
            if not step_fn():
                elapsed = time.time() - self.start_time
                logger.error(f"Pipeline FAILED after {elapsed:.1f}s")
                return False

        elapsed = time.time() - self.start_time
        logger.info("=" * 60)
        logger.info(f"Pipeline COMPLETED in {elapsed:.1f}s")

        # List output files
        if self.output_dir.exists():
            for f in sorted(self.output_dir.iterdir()):
                if f.is_file():
                    size_kb = f.stat().st_size / 1024
                    logger.info(f"  Output: {f.name} ({size_kb:.1f} KB)")

        logger.info("=" * 60)
        return True

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _run(self, cmd, stage_name):
        # type: (list, str) -> bool
        """Run a subprocess and log output."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.pipeline_dir),
            )
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    logger.info(f"  [{stage_name}] {line}")
            if result.returncode != 0:
                logger.error(f"{stage_name} failed (exit code {result.returncode})")
                if result.stderr:
                    for line in result.stderr.strip().split("\n"):
                        logger.error(f"  [{stage_name}] {line}")
                return False
            return True
        except Exception as e:
            logger.error(f"{stage_name} exception: {e}")
            return False

    def _validate(self, path, stage_name):
        # type: (Path, str) -> bool
        """Validate an expected output file exists."""
        if path.exists() and path.stat().st_size > 0:
            size_kb = path.stat().st_size / 1024
            logger.info(f"  [{stage_name}] Validated: {path.name} ({size_kb:.1f} KB)")
            return True
        logger.error(f"{stage_name} output missing: {path}")
        return False


# ======================================================================
# CLI
# ======================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Geometry Diagram Pipeline — question text to diagram"
    )
    parser.add_argument(
        "--question-text", required=True,
        help="Question text (literal string or path to a .txt file)",
    )
    parser.add_argument(
        "--question-image", default=None,
        help="Optional path to the question image",
    )
    parser.add_argument(
        "--output-format", default="png",
        choices=["png", "svg", "gif", "mp4"],
        help="Output format (default: png)",
    )
    args = parser.parse_args()

    # Resolve question text: if it's a file path, read it
    question_text = args.question_text
    if os.path.isfile(question_text):
        with open(question_text, "r", encoding="utf-8") as f:
            question_text = f.read().strip()
        logger.info(f"Read question text from file: {args.question_text}")

    pipeline = GeometryPipeline(
        question_text=question_text,
        question_image=args.question_image,
        output_format=args.output_format,
    )

    success = pipeline.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
