#!/usr/bin/env python3
from manim import *
import numpy as np
import shutil
import sys
from pathlib import Path
from datetime import datetime
from manim_helpers import create_3d_angle_arc_with_connections

# --- Configuration ---
config.background_color = "#FFFFFF"
config.pixel_height = 480
config.pixel_width = 854
config.frame_rate = 15
config.format = "gif"
config.output_file = "diagram"

# --- Hardcoded Coordinates and Data ---
OUTPUT_PATH = "/app/output/diagram.gif"

# Raw coordinates from blueprint
pts_raw = {
    "A": np.array([5.000, 0.000, 0.000]),
    "B": np.array([0.000, 0.000, 0.000]),
    "C": np.array([0.000, 6.667, 0.000]),
    "D": np.array([5.000, 0.000, 16.667]),
    "E": np.array([0.000, 0.000, 16.667]),
    "F": np.array([0.000, 6.667, 16.667]),
}

# Center coordinates around origin
all_coords = np.array(list(pts_raw.values()))
centroid = np.mean(all_coords, axis=0)
pts = {k: v - centroid for k, v in pts_raw.items()}

# Dynamic camera distance
max_radius = max(np.linalg.norm(v) for v in pts.values())
CAM_DISTANCE = max(max_radius * 3.0, 8)

class GeometryScene(ThreeDScene):
    def construct(self):
        # 1. Faces (Z-order 0)
        faces_data = [
            (["A", "B", "C"], "#2A9D8F"),
            (["D", "E", "F"], "#264653"),
            (["A", "B", "E", "D"], "#457B9D"),
            (["B", "C", "F", "E"], "#6A4C93"),
            (["A", "C", "F", "D"], "#E76F51"),
        ]
        for points_keys, color in faces_data:
            face = Polygon(*[pts[k] for k in points_keys], 
                           fill_opacity=0.1, 
                           fill_color=color, 
                           stroke_width=0)
            self.add(face)

        # 2. Lines (Z-order 2)
        edges = [
            ("A", "B"), ("B", "C"), ("A", "C"),
            ("D", "E"), ("E", "F"), ("D", "F"),
            ("A", "D"), ("B", "E"), ("C", "F")
        ]
        for start_key, end_key in edges:
            line = Line(pts[start_key], pts[end_key], color="#444444", stroke_width=4)
            self.add(line)

        # 3. Asked Element: AF (Glow + Main Line)
        line_af_glow = Line(pts["A"], pts["F"], color="#E63946", stroke_width=12).set_opacity(0.2)
        line_af = Line(pts["A"], pts["F"], color="#E63946", stroke_width=4)
        self.add(line_af_glow, line_af)

        # 4. Angle Arcs (Given angle ABC is 90)
        create_3d_angle_arc_with_connections(
            self, 
            vertex=pts["B"], 
            p1=pts["A"], 
            p2=pts["C"], 
            radius=0.5, 
            color="#444444", 
            is_right_angle=True
        )

        # 5. Points (Z-order 4)
        for coord in pts.values():
            dot = Dot3D(coord, color="#1A1A1A", radius=0.08)
            self.add(dot)

        # 6. Labels (Fixed Orientation)
        # Point Labels
        for name, coord in pts.items():
            label = MathTex(name, color="#1A1A1A").scale(0.8)
            # Offset away from centroid
            direction = coord / np.linalg.norm(coord) if np.linalg.norm(coord) > 0 else UP
            label.move_to(coord + 0.6 * direction)
            self.add_fixed_orientation_mobjects(label)

        # Measurement Labels (Given)
        measurements = [
            ("A", "B", "3\\text{ cm}"),
            ("B", "C", "4\\text{ cm}"),
            ("B", "E", "10\\text{ cm}"),
        ]
        for p1, p2, text in measurements:
            mid = (pts[p1] + pts[p2]) / 2
            label = MathTex(text, color="#1A1A1A").scale(0.7)
            direction = mid / np.linalg.norm(mid) if np.linalg.norm(mid) > 0 else UP
            label.move_to(mid + 0.5 * direction)
            self.add_fixed_orientation_mobjects(label)

        # Asked Label (?)
        mid_af = (pts["A"] + pts["F"]) / 2
        label_af = MathTex("?", color="#E63946").scale(1.2).set_weight("BOLD")
        direction_af = mid_af / np.linalg.norm(mid_af) if np.linalg.norm(mid_af) > 0 else UP
        label_af.move_to(mid_af + 0.6 * direction_af)
        self.add_fixed_orientation_mobjects(label_af)

        # 7. Camera Setup
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES, distance=CAM_DISTANCE)
        self.begin_ambient_camera_rotation(rate=PI / 8)
        self.wait(8)
        self.stop_ambient_camera_rotation()

if __name__ == "__main__":
    try:
        scene = GeometryScene()
        scene.render()

        # Generate timestamped output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/app/output/diagram_{timestamp}.gif"

        # Manim output path logic
        # Default: media/videos/render_code/480p15/diagram.gif
        script_name = Path(__file__).stem
        source = Path(f"media/videos/{script_name}/480p15/diagram.gif")

        if source.exists():
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, output_path)
            print(f"Saved: {output_path}")
        else:
            # Fallback search if path differs
            found = list(Path("media").rglob("diagram.gif"))
            if found:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(found[0], output_path)
                print(f"Saved: {output_path}")
            else:
                print("Error: Output GIF not found in media directory.")
                sys.exit(1)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)