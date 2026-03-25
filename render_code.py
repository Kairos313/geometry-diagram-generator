#!/usr/bin/env python3
from manim import *
import numpy as np
import shutil
from pathlib import Path
from manim_helpers import (
    create_3d_angle_arc_with_connections,
    create_3d_coordinate_axes,
    create_sphere_wireframe,
)

config.background_color = "#FFFFFF"
config.pixel_height = 360
config.pixel_width = 640
config.frame_rate = 10
config.format = "gif"
config.output_file = "diagram"

# Raw coordinates from blueprint — ALL floats
pts_raw = {
    "A": np.array([6.0, 0.0, 0.0]),
    "B": np.array([0.0, 3.0, 0.0]),
    "C": np.array([0.0, 0.0, -3.0]),
    "D": np.array([4.5, 0.0, 0.0]),
    "E": np.array([0.0, -9.0, 0.0]),
    "F": np.array([0.0, 0.0, 4.5]),
}

# Coordinate range from blueprint
x_min, x_max = -2.0, 8.0
y_min, y_max = -11.0, 5.0
z_min, z_max = -5.0, 6.0

# Center + scale ALL geometry so the scene fits inside the camera frame.
# DO NOT use camera.frame_center — it does not work reliably in manim ThreeDScene.
data_center = np.array([(x_min + x_max) / 2.0,
                         (y_min + y_max) / 2.0,
                         (z_min + z_max) / 2.0], dtype=float)
max_extent = max(x_max - x_min, y_max - y_min, z_max - z_min, 1.0)
COORD_SCALE = min(1.5, 7.0 / max_extent)   # map largest dimension to ~7 manim units

pts = {k: (v - data_center) * COORD_SCALE for k, v in pts_raw.items()}

# Scale the coordinate ranges for the axis helper
x_min_s = (x_min - data_center[0]) * COORD_SCALE
x_max_s = (x_max - data_center[0]) * COORD_SCALE
y_min_s = (y_min - data_center[1]) * COORD_SCALE
y_max_s = (y_max - data_center[1]) * COORD_SCALE
z_min_s = (z_min - data_center[2]) * COORD_SCALE
z_max_s = (z_max - data_center[2]) * COORD_SCALE

# Plane bounding-box clip helper
def plane_polygon_verts(normal, d_orig, xr, yr, zr, center, scale):
    # Transform plane equation ax+by+cz=d to shifted/scaled space, clip to box.
    a, b, c = float(normal[0]), float(normal[1]), float(normal[2])
    d = d_orig - a*center[0] - b*center[1] - c*center[2]
    d *= scale
    a_s, b_s, c_s = a / scale, b / scale, c / scale   # normal in scaled space
    pts_out = []
    for y in [yr[0], yr[1]]:
        for z in [zr[0], zr[1]]:
            if abs(a_s) > 1e-9:
                x = (d/scale - b_s*y - c_s*z) / a_s
                if xr[0] <= x <= xr[1]: pts_out.append(np.array([x, y, z], dtype=float))
    for x in [xr[0], xr[1]]:
        for z in [zr[0], zr[1]]:
            if abs(b_s) > 1e-9:
                y = (d/scale - a_s*x - c_s*z) / b_s
                if yr[0] <= y <= yr[1]: pts_out.append(np.array([x, y, z], dtype=float))
    for x in [xr[0], xr[1]]:
        for y in [yr[0], yr[1]]:
            if abs(c_s) > 1e-9:
                z = (d/scale - a_s*x - b_s*y) / c_s
                if zr[0] <= z <= zr[1]: pts_out.append(np.array([x, y, z], dtype=float))
    if len(pts_out) < 3:
        return pts_out
    ctr = sum(pts_out) / len(pts_out)
    n_hat = np.array([a, b, c], dtype=float)
    n_hat /= (np.linalg.norm(n_hat) + 1e-9)
    u = pts_out[0] - ctr
    u -= np.dot(u, n_hat) * n_hat
    u /= (np.linalg.norm(u) + 1e-9)
    v = np.cross(n_hat, u)
    return sorted(pts_out, key=lambda p: np.arctan2(np.dot(p - ctr, v), np.dot(p - ctr, u)))

class GeometryScene(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=65*DEGREES, theta=-45*DEGREES, zoom=0.9)

        # Draw 3D coordinate axes spanning the scaled range
        axes_group, ax_labels = create_3d_coordinate_axes(
            (x_min_s, x_max_s), (y_min_s, y_max_s), (z_min_s, z_max_s)
        )
        self.add(axes_group)
        self.add_fixed_orientation_mobjects(*ax_labels)

        # Plane P1: x + 2y - 2z = 6
        verts_p1 = plane_polygon_verts([1.0, 2.0, -2.0], 6.0,
                                       (x_min_s, x_max_s), (y_min_s, y_max_s), (z_min_s, z_max_s),
                                       data_center, COORD_SCALE)
        if len(verts_p1) >= 3:
            plane_p1 = Polygon(*verts_p1, color="#2A9D8F", fill_opacity=0.15, stroke_opacity=0.5)
            self.add(plane_p1)
            plane_label_p1 = Text("x+2y-2z=6", color="#2A9D8F").scale(0.45)
            plane_label_p1.rotate(PI/2, axis=RIGHT)
            plane_label_p1.move_to(sum(verts_p1)/len(verts_p1) + np.array([0.3, 0.3, 0.3]))
            self.add_fixed_orientation_mobjects(plane_label_p1)

        # Plane P2: 2x - y + 2z = 9
        verts_p2 = plane_polygon_verts([2.0, -1.0, 2.0], 9.0,
                                       (x_min_s, x_max_s), (y_min_s, y_max_s), (z_min_s, z_max_s),
                                       data_center, COORD_SCALE)
        if len(verts_p2) >= 3:
            plane_p2 = Polygon(*verts_p2, color="#E76F51", fill_opacity=0.15, stroke_opacity=0.5)
            self.add(plane_p2)
            plane_label_p2 = Text("2x-y+2z=9", color="#E76F51").scale(0.45)
            plane_label_p2.rotate(PI/2, axis=RIGHT)
            plane_label_p2.move_to(sum(verts_p2)/len(verts_p2) + np.array([0.3, 0.3, 0.3]))
            self.add_fixed_orientation_mobjects(plane_label_p2)

        # Draw points
        for name, pos in pts.items():
            dot = Dot3D(color="#1A1A1A", radius=0.06)
            dot.move_to(pos)
            self.add(dot)
            label = Text(name, color="#1A1A1A").scale(0.8)
            label.rotate(PI/2, axis=RIGHT)
            label.move_to(pos + np.array([0.2, 0.2, 0.2]))
            self.add_fixed_orientation_mobjects(label)

        # Draw lines between points that appear in the plane vertices
        # Plane P1 vertices: A(6,0,0), B(0,3,0), and two others not in pts
        line_AB = Line3D(pts["A"], pts["B"], color="#264653", thickness=0.02)
        self.add(line_AB)
        
        # Plane P2 vertices: D(4.5,0,0), E(0,-9,0)
        line_DE = Line3D(pts["D"], pts["E"], color="#264653", thickness=0.02)
        self.add(line_DE)

        # Asked dihedral angle - show with "?" label at intersection region
        # Find approximate intersection point by solving the two plane equations
        # Normal vectors
        n1 = np.array([1.0, 2.0, -2.0])
        n2 = np.array([2.0, -1.0, 2.0])
        # Direction of intersection line
        dir_vec = np.cross(n1, n2)
        dir_vec = dir_vec / np.linalg.norm(dir_vec)
        
        # Find a point on the intersection by solving the system
        # Choose z=0 for simplicity
        # x + 2y = 6
        # 2x - y = 9
        # Solve: from second, y = 2x - 9, substitute into first: x + 2(2x-9) = 6 => 5x - 18 = 6 => x = 4.8, y = 2*4.8-9 = 0.6
        # So point (4.8, 0.6, 0) is on intersection
        intersect_pt_raw = np.array([4.8, 0.6, 0.0])
        intersect_pt = (intersect_pt_raw - data_center) * COORD_SCALE
        
        # Add "?" label for the asked dihedral angle
        angle_label = Text("?", color="#E63946").scale(1.2)
        angle_label.rotate(PI/2, axis=RIGHT)
        angle_label.move_to(intersect_pt + np.array([0.5, 0.5, 0.5]))
        self.add_fixed_orientation_mobjects(angle_label)

        self.begin_ambient_camera_rotation(rate=0.15)
        self.wait(4)

output_dir = Path("/private/tmp/geo_test_3d/diagram.gif").parent
output_dir.mkdir(parents=True, exist_ok=True)
media_dir = Path("media/videos/diagram/360p10")
if media_dir.exists():
    for gif_file in media_dir.glob("*.gif"):
        shutil.move(str(gif_file), "/private/tmp/geo_test_3d/diagram.gif")
        print("Saved: /private/tmp/geo_test_3d/diagram.gif")
        break