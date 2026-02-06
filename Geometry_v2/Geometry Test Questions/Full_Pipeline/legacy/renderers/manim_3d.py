"""
3D geometry renderer using Manim.

Generates a ThreeDScene script, executes it via subprocess, and produces
a GIF or MP4 showing a slow camera rotation around the 3D figure.

This renderer is designed to be swappable — a future Blender renderer
would implement the same GeometryRenderer interface.
"""

import glob
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

from .base import GeometryData, GeometryRenderer, RenderConfig


class Manim3DRenderer(GeometryRenderer):
    """Renders 3D geometry using Manim with a rotating camera."""

    def render(self, geometry_data: GeometryData, output_path: Path) -> bool:
        try:
            scene_code = self._generate_scene_code(geometry_data)

            # Write temporary Manim script
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, prefix="geo3d_"
            )
            tmp.write(scene_code)
            tmp.flush()
            tmp_path = tmp.name
            tmp.close()

            # Determine quality
            quality = "ql" if self.config.output_format == "gif" else "qm"

            cmd = [
                "manim",
                f"-q{quality}",
                "--disable_caching",
            ]
            if self.config.output_format == "gif":
                cmd.append("--format=gif")
            cmd.extend([tmp_path, "Geometry3DScene"])

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )

            if result.returncode != 0:
                print(f"Manim 3D render error:\n{result.stderr}")
                return False

            # Find and move the rendered file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return self._collect_output(tmp_path, output_path)

        except subprocess.TimeoutExpired:
            print("Manim 3D render timed out (300s)")
            return False
        except Exception as e:
            print(f"Manim 3D render error: {e}")
            return False

    # ------------------------------------------------------------------
    # Code generation
    # ------------------------------------------------------------------

    def _generate_scene_code(self, data: GeometryData) -> str:
        """Build a complete Manim ThreeDScene Python script."""

        coord_lines = self._build_coordinates(data)
        dot_lines = self._build_dots(data)
        line_lines = self._build_lines(data)
        label_lines = self._build_labels(data)
        circle_lines = self._build_circles(data)

        bg = self.config.background_color
        duration = self.config.rotation_duration
        pitch = self.config.pitch_angle
        yaw = self.config.yaw_angle

        return textwrap.dedent(f"""\
            from manim import *
            import numpy as np

            class Geometry3DScene(ThreeDScene):
                def construct(self):
                    self.camera.background_color = "{bg}"

                    # --- Coordinates ---
            {coord_lines}

                    # --- Dots ---
                    dots = VGroup(
            {dot_lines}
                    )

                    # --- Lines ---
                    lines = VGroup(
            {line_lines}
                    )

                    # --- Labels ---
                    labels = VGroup(
            {label_lines}
                    )

                    # --- Circles ---
                    circles = VGroup(
            {circle_lines}
                    )

                    figure = VGroup(dots, lines, labels, circles)

                    # Set initial camera orientation
                    self.set_camera_orientation(
                        phi={abs(pitch)} * DEGREES,
                        theta={yaw} * DEGREES,
                    )

                    self.add(figure)
                    self.wait(1)

                    # Slow rotation
                    self.begin_ambient_camera_rotation(rate=PI / {duration})
                    self.wait({duration})
                    self.stop_ambient_camera_rotation()
                    self.wait(1)
        """)

    def _build_coordinates(self, data: GeometryData) -> str:
        lines = []
        for name, p in data.points.items():
            lines.append(
                f"        coord_{name} = np.array([{p.x:.3f}, {p.y:.3f}, {p.z:.3f}])"
            )
        return "\n".join(lines)

    def _build_dots(self, data: GeometryData) -> str:
        lines = []
        for name, p in data.points.items():
            lines.append(
                f'            Dot3D(coord_{name}, radius=0.08, color="{p.color}"),'
            )
        return "\n".join(lines)

    def _build_lines(self, data: GeometryData) -> str:
        lines = []
        for seg in data.lines:
            color = seg.color
            lines.append(
                f'            Line3D(coord_{seg.start_point}, coord_{seg.end_point}, '
                f'color="{color}", thickness=0.02),'
            )
        return "\n".join(lines)

    def _build_labels(self, data: GeometryData) -> str:
        lines = []
        for name, p in data.points.items():
            lines.append(
                f'            Text3D("{name}", font_size=24, color="{p.color}")'
                f".move_to(coord_{name} + np.array([0.3, 0.3, 0.0])),"
            )
        return "\n".join(lines)

    def _build_circles(self, data: GeometryData) -> str:
        if not data.circles:
            return '            # (none)'
        lines = []
        for cdef in data.circles:
            lines.append(
                f'            Circle(radius={cdef.radius}, color="{cdef.color}", '
                f'stroke_width={cdef.stroke_width}).move_to(coord_{cdef.center}),'
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Output collection
    # ------------------------------------------------------------------

    def _collect_output(self, script_path: str, output_path: Path) -> bool:
        """Find Manim's rendered file and copy it to the desired output path."""
        stem = Path(script_path).stem
        ext = self.config.output_format
        pattern = f"media/videos/{stem}/**/Geometry3DScene.{ext}"
        matches = glob.glob(pattern, recursive=True)
        if not matches:
            # Also try mp4 if gif wasn't found
            for try_ext in ("gif", "mp4"):
                pattern = f"media/videos/{stem}/**/Geometry3DScene.{try_ext}"
                matches = glob.glob(pattern, recursive=True)
                if matches:
                    break
        if matches:
            shutil.copy2(matches[0], str(output_path))
            return True
        print(f"Could not find Manim output matching: media/videos/{stem}/**/Geometry3DScene.*")
        return False
