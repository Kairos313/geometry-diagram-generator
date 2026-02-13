#!/usr/bin/env python3
from manim import *
import numpy as np
import shutil
from pathlib import Path
from manim_helpers import create_3d_angle_arc_with_connections

# Configuration
config.background_color = "#FFFFFF"
config.pixel_height = 360
config.pixel_width = 640
config.frame_rate = 10
config.format = "gif"
config.output_file = "diagram"

# Hardcoded coordinates from blueprint
pts_raw = {
    "A": np.array([0.0, 0.0, 0.0]),
    "B": np.array([5.0, 0.0, 0.0]),
    "C": np.array([2.5, 4.33, 0.0]),
    "V": np.array([2.5, 1.443, 4.082]),
    "M": np.array([3.75, 2.165, 0.0])
}

# Adaptive Scaling
all_coords = np.array(list(pts_raw.values()))
centroid = np.mean(all_coords, axis=0)
centered = all_coords - centroid
max_radius = max(np.linalg.norm(c) for c in centered)
TARGET_SIZE = 3.5
SCALE_FACTOR = min(1.5, TARGET_SIZE / max_radius) if max_radius > 0 else 1.0
pts = {k: (v - centroid) * SCALE_FACTOR for k, v in pts_raw.items()}

class GeometryScene(ThreeDScene):
    def construct(self):
        # Camera setup
        self.set_camera_orientation(phi=65*DEGREES, theta=-45*DEGREES, zoom=0.7)

        # Colors and Styles
        COLOR_DEFAULT = "#1A1A1A"
        COLOR_ASKED = "#E63946"
        THICKNESS_DEFAULT = 0.02
        THICKNESS_ASKED = 0.04

        # 1. Faces
        faces_data = [
            ["A", "B", "C"],
            ["V", "A", "B"],
            ["V", "B", "C"],
            ["V", "C", "A"]
        ]
        for f_pts in faces_data:
            face = Polygon(
                *[pts[p] for p in f_pts],
                fill_opacity=0.08,
                stroke_opacity=0.3,
                color=COLOR_DEFAULT,
                stroke_width=1
            )
            self.add(face)

        # 2. Lines
        lines_data = [
            {"id": "line_AB", "from": "A", "to": "B", "style": "solid"},
            {"id": "line_BC", "from": "B", "to": "C", "style": "solid"},
            {"id": "line_CA", "from": "C", "to": "A", "style": "solid"},
            {"id": "line_VA", "from": "V", "to": "A", "style": "solid"},
            {"id": "line_VB", "from": "V", "to": "B", "style": "solid"},
            {"id": "line_VC", "from": "V", "to": "C", "style": "solid"},
            {"id": "line_VM", "from": "V", "to": "M", "style": "dashed"},
            {"id": "line_AM", "from": "A", "to": "M", "style": "dashed"}
        ]
        
        asked_ids = ["angle_VMA"]
        given_data = {"line_AB": "6 cm"}

        for l in lines_data:
            start, end = pts[l["from"]], pts[l["to"]]
            is_asked = l["id"] in asked_ids
            color = COLOR_ASKED if is_asked else COLOR_DEFAULT
            thickness = THICKNESS_ASKED if is_asked else THICKNESS_DEFAULT
            
            if l["style"] == "dashed":
                # Use Line (VMobject) for DashedVMobject to avoid IndexError with Line3D
                line_obj = DashedVMobject(
                    Line(start, end, color=color, stroke_width=thickness*100),
                    num_dashes=15
                )
            else:
                line_obj = Line3D(start, end, color=color, thickness=thickness)
            self.add(line_obj)

            # Given labels
            if l["id"] in given_data:
                mid = (start + end) / 2
                label = Text(given_data[l["id"]], color=COLOR_DEFAULT).scale(0.6)
                label.move_to(mid + UP * 0.2)
                self.add_fixed_orientation_mobjects(label)

        # 3. Angles
        # angle_VMA: vertex M, p1 V, p2 A
        arc = create_3d_angle_arc_with_connections(
            center=pts["M"],
            point1=pts["V"],
            point2=pts["A"],
            radius=0.4,
            color=COLOR_ASKED
        )
        self.add(arc)
        
        # Asked label "?"
        q_label = Text("?", color=COLOR_ASKED).scale(0.8)
        # Position "?" near the arc
        q_pos = pts["M"] + (pts["V"] - pts["M"]) * 0.15 + (pts["A"] - pts["M"]) * 0.15 + OUT * 0.2
        q_label.move_to(q_pos)
        self.add_fixed_orientation_mobjects(q_label)

        # 4. Points and Labels
        for name, coord in pts.items():
            dot = Dot3D(coord, color=COLOR_DEFAULT, radius=0.06)
            label = Text(name, color=COLOR_DEFAULT).scale(0.8)
            # Offset label slightly
            label.move_to(coord + np.array([0.15, 0.15, 0.15]))
            self.add(dot)
            self.add_fixed_orientation_mobjects(label)

        # 5. Animation
        self.begin_ambient_camera_rotation(rate=0.15)
        self.wait(4)

if __name__ == "__main__":
    scene = GeometryScene()
    scene.render()

    # Post-render: move output file to the expected path
    source = Path("media/videos/360p10/diagram.gif")
    destination = Path("/Users/kairos/Desktop/geometry-video-generator/Geometry_v2/Geometry Test Questions/Full_Pipeline/output/diagram.gif")
    
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))