
#!/usr/bin/env python3
from manim import *
import numpy as np
import shutil
from pathlib import Path
from manim_helpers import create_3d_coordinate_axes, create_sphere_surface

config.background_color = "#FFFFFF"
config.pixel_height = 360
config.pixel_width = 640
config.frame_rate = 10
config.format = "gif"
config.output_file = "test_manim_helpers"

# Coordinate range
x_range = (-3, 5)
y_range = (-2, 4)
z_range = (-1, 6)

# Sample points
pts = {
    "A": np.array([2.0, 1.0, 3.0]),
    "B": np.array([-1.0, 2.0, 1.0]),
    "C": np.array([0.0, 0.0, 2.0]),  # Sphere center
}

class TestScene(ThreeDScene):
    def construct(self):
        # Camera setup
        x_center = sum(x_range) / 2
        y_center = sum(y_range) / 2
        z_center = sum(z_range) / 2

        self.set_camera_orientation(phi=65*DEGREES, theta=-45*DEGREES, zoom=0.7)
        self.camera.frame_center = np.array([x_center, y_center, z_center])

        # HELPER FUNCTION TEST 1: Draw 3D coordinate axes
        axes, labels = create_3d_coordinate_axes(x_range, y_range, z_range)
        self.add(axes)
        self.add_fixed_orientation_mobjects(*labels)

        # HELPER FUNCTION TEST 2: Create translucent sphere surface
        sphere_surface = create_sphere_surface(
            center=pts["C"],
            radius=2.0,
            color="#457B9D",
            fill_opacity=0.3,
            resolution=(50, 50)  # Higher resolution for smoother appearance
        )
        self.add(sphere_surface)

        # Add sample points
        for name, coord in pts.items():
            dot = Dot3D(point=coord, color="#1A1A1A", radius=0.06)
            self.add(dot)
            label = Text(name, color="#1A1A1A").scale(0.7)
            label.rotate(PI/2, axis=RIGHT).move_to(coord + np.array([0.3, 0.3, 0.3]))
            self.add_fixed_orientation_mobjects(label)

        # Add a sample line
        line_AB = Line3D(start=pts["A"], end=pts["B"], color="#2A9D8F", thickness=0.02)
        self.add(line_AB)

        # Rotation animation
        self.begin_ambient_camera_rotation(rate=0.15)
        self.wait(4)

# Post-render: move output
output_dir = Path("test_output")
output_dir.mkdir(parents=True, exist_ok=True)
media_dir = Path("media/videos/test_manim_helpers/360p10")
if media_dir.exists():
    for gif_file in media_dir.glob("*.gif"):
        output_path = output_dir / "test_manim_helpers.gif"
        shutil.move(str(gif_file), str(output_path))
        print(f"✅ Saved: {output_path}")
        break
