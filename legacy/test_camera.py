#!/usr/bin/env python3
"""
Quick camera angle tester for 3D Manim scenes.

Renders a single PNG frame of a square pyramid at the given phi/theta.
Much faster than a full GIF — iterate quickly to find the best angle.

Usage:
    python3 test_camera.py                          # default: phi=75, theta=45
    python3 test_camera.py --phi 60 --theta -30
    python3 test_camera.py --phi 70 --theta 30 --distance 10
"""
import argparse
import sys

parser = argparse.ArgumentParser(description="Test 3D camera angles")
parser.add_argument("--phi", type=float, default=75, help="Elevation angle in degrees (0=top-down, 90=side)")
parser.add_argument("--theta", type=float, default=45, help="Azimuthal angle in degrees (horizontal orbit)")
parser.add_argument("--distance", type=float, default=10, help="Camera distance from center")
args = parser.parse_args()

from manim import *
import numpy as np

# --- Config ---
config.background_color = "#FFFFFF"
config.pixel_height = 720
config.pixel_width = 1280
config.format = "png"  # Single frame — fast!
config.output_file = f"camera_phi{int(args.phi)}_theta{int(args.theta)}_d{int(args.distance)}"

# --- Square pyramid coordinates, centered around origin ---
_raw = {
    "A": np.array([0.0, 0.0, 0.0]),
    "B": np.array([5.0, 0.0, 0.0]),
    "C": np.array([5.0, 5.0, 0.0]),
    "D": np.array([0.0, 5.0, 0.0]),
    "M": np.array([2.5, 2.5, 0.0]),   # center of base
    "E": np.array([2.5, 2.5, 3.75]),   # apex
}
_centroid = np.mean([_raw["A"], _raw["B"], _raw["C"], _raw["D"], _raw["E"]], axis=0)
# Shift everything so centroid is at origin
coord_A = _raw["A"] - _centroid
coord_B = _raw["B"] - _centroid
coord_C = _raw["C"] - _centroid
coord_D = _raw["D"] - _centroid
coord_M = _raw["M"] - _centroid
coord_E = _raw["E"] - _centroid

ALL_COORDS = [coord_A, coord_B, coord_C, coord_D, coord_E]
centroid = np.array([0.0, 0.0, 0.0])  # already centered

class CameraTest(ThreeDScene):
    def construct(self):
        # --- Points ---
        dots = VGroup(*[
            Dot3D(c, radius=0.08, color="#1A1A1A")
            for c in [coord_A, coord_B, coord_C, coord_D, coord_E]
        ])

        # --- Labels ---
        label_data = [
            ("A", coord_A, [-0.4, -0.4, 0.0]),
            ("B", coord_B, [0.4, -0.4, 0.0]),
            ("C", coord_C, [0.4, 0.4, 0.0]),
            ("D", coord_D, [-0.4, 0.4, 0.0]),
            ("E", coord_E, [0.0, 0.0, 0.5]),
        ]
        labels = VGroup()
        for name, coord, offset in label_data:
            lbl = Text(name, font_size=36, color="#1A1A1A", font="sans-serif")
            lbl.move_to(coord + np.array(offset))
            labels.add(lbl)

        # --- Base edges ---
        base_edges = VGroup(
            Line3D(coord_A, coord_B, color="#2A9D8F", thickness=0.02),
            Line3D(coord_B, coord_C, color="#264653", thickness=0.02),
            Line3D(coord_C, coord_D, color="#457B9D", thickness=0.02),
            Line3D(coord_D, coord_A, color="#6A4C93", thickness=0.02),
        )

        # --- Slant edges ---
        slant_edges = VGroup(
            Line3D(coord_E, coord_A, color="#E63946", thickness=0.04),  # asked
            Line3D(coord_E, coord_B, color="#B5838D", thickness=0.02),
            Line3D(coord_E, coord_C, color="#B5838D", thickness=0.02),
            Line3D(coord_E, coord_D, color="#B5838D", thickness=0.02),
        )

        # --- Height line ---
        height_line = DashedLine(coord_E, coord_M, color="#444444", dash_length=0.15)

        # --- Base face ---
        base_face = Polygon(coord_A, coord_B, coord_C, coord_D,
                            fill_color="#2A9D8F", fill_opacity=0.08,
                            stroke_color="#2A9D8F", stroke_opacity=0.3)

        # --- "?" label on asked edge ---
        mid_EA = (coord_E + coord_A) / 2
        q_label = Text("?", font_size=42, color="#E63946", font="sans-serif", weight=BOLD)
        q_label.move_to(mid_EA + np.array([-0.5, 0.0, 0.0]))

        # --- Measurement labels ---
        mid_AB = (coord_A + coord_B) / 2
        lbl_8 = Text("8 cm", font_size=24, color="#333333", font="sans-serif")
        lbl_8.move_to(mid_AB + np.array([0.0, -0.5, 0.0]))

        mid_EM = (coord_E + coord_M) / 2
        lbl_6 = Text("6 cm", font_size=24, color="#333333", font="sans-serif")
        lbl_6.move_to(mid_EM + np.array([0.5, 0.0, 0.0]))

        given_labels = VGroup(q_label, lbl_8, lbl_6)

        # --- Assemble ---
        figure = VGroup(base_face, base_edges, slant_edges, height_line, dots)
        self.add(figure, labels, given_labels)
        self.add_fixed_orientation_mobjects(*labels, *given_labels)

        # --- Camera ---
        self.set_camera_orientation(
            phi=args.phi * DEGREES,
            theta=args.theta * DEGREES,
            distance=args.distance,
            frame_center=centroid,
        )

        # --- Angle info overlay ---
        info = Text(
            f"phi={args.phi}  theta={args.theta}  dist={args.distance}",
            font_size=28, color="#999999",
        )
        info.to_corner(DL, buff=0.3)
        self.add_fixed_in_frame_mobjects(info)

        self.wait(0.1)  # single frame

# --- Render ---
if __name__ == "__main__":
    scene = CameraTest()
    scene.render()
    print(f"\nRendered with phi={args.phi}, theta={args.theta}, distance={args.distance}")
    print(f"Output: media/images/camera_phi{int(args.phi)}_theta{int(args.theta)}_d{int(args.distance)}0000.png")
