#!/usr/bin/env python3
"""
Test script to demonstrate the new coordinate geometry helper functions.

This creates:
1. A 2D matplotlib plot with coordinate axes (using draw_coordinate_axes)
2. A 3D manim scene with coordinate axes and a sphere wireframe
"""

import sys
import subprocess
from pathlib import Path

# Test 1: 2D Matplotlib with coordinate axes
def test_matplotlib_coordinate_axes():
    """Test the draw_coordinate_axes helper for matplotlib."""
    print("=" * 70)
    print("TEST 1: Matplotlib Coordinate Axes Helper")
    print("=" * 70)

    test_code = '''
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
from matplotlib_helpers import draw_coordinate_axes

# Create figure
fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
fig.patch.set_facecolor('#FFFFFF')
ax.set_facecolor('#FFFFFF')
ax.set_aspect('equal')
ax.axis('off')

# Set coordinate range
x_min, x_max = -3.0, 7.0
y_min, y_max = -2.0, 8.0
ax.set_xlim(x_min, x_max)
ax.set_ylim(y_min, y_max)

# HELPER FUNCTION TEST: Draw coordinate axes
draw_coordinate_axes(ax, x_min, x_max, y_min, y_max, arrow_size=0.2, zorder=0)

# Add some sample points to show the axes work
points = {"A": np.array([2, 3]), "B": np.array([5, 1]), "C": np.array([-1, 4])}
for name, coord in points.items():
    ax.plot(coord[0], coord[1], 'o', color='#1A1A1A', markersize=8, zorder=4)
    ax.text(coord[0] + 0.3, coord[1] + 0.3, name, fontsize=12, ha='left', va='bottom',
            color='#1A1A1A', zorder=5)

# Add a sample line
ax.plot([points["A"][0], points["B"][0]], [points["A"][1], points["B"][1]],
        color='#2A9D8F', linewidth=2, zorder=2)

Path("test_output").mkdir(parents=True, exist_ok=True)
plt.savefig("test_output/test_matplotlib_axes.png", dpi=100, facecolor='white', bbox_inches='tight')
plt.close()
print("✅ Saved: test_output/test_matplotlib_axes.png")
'''

    # Write and run test
    test_file = Path("test_matplotlib_axes_helper.py")
    test_file.write_text(test_code)

    result = subprocess.run(
        ["python3", str(test_file)],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
    else:
        print("✅ Test passed! Check test_output/test_matplotlib_axes.png")

    test_file.unlink()
    print()


# Test 2: 3D Manim with coordinate axes and sphere wireframe
def test_manim_3d_helpers():
    """Test the create_3d_coordinate_axes and create_sphere_wireframe helpers."""
    print("=" * 70)
    print("TEST 2: Manim 3D Coordinate Axes & Sphere Wireframe Helpers")
    print("=" * 70)

    test_code = '''
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
'''

    # Write and run test
    test_file = Path("test_manim_helpers.py")
    test_file.write_text(test_code)

    print("Running manim (this may take 10-20 seconds)...")
    result = subprocess.run(
        ["/Users/kairos/.local/bin/manim", "render", str(test_file), "TestScene", "-ql", "--format", "gif"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    if result.returncode != 0:
        print(f"❌ Manim error: {result.stderr}")
    else:
        print(result.stdout)
        print("✅ Test passed! Check test_output/test_manim_helpers.gif")

    test_file.unlink()
    print()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("COORDINATE GEOMETRY HELPER FUNCTIONS TEST SUITE")
    print("="*70 + "\n")

    # Test matplotlib helper
    test_matplotlib_coordinate_axes()

    # Test manim helpers
    test_manim_3d_helpers()

    print("="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)
    print("\nOutput files:")
    print("  - test_output/test_matplotlib_axes.png (2D coordinate axes)")
    print("  - test_output/test_manim_helpers.gif (3D axes + sphere wireframe)")
    print()
