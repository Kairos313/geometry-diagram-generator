#!/usr/bin/env python3
"""
Test script to compare wireframe sphere vs. surface sphere rendering.
"""
import sys
import os
import subprocess
from pathlib import Path

# Test output directory
OUTPUT_DIR = Path("test_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Create the test Manim scene
SCENE_CODE = '''
from manim import *
import numpy as np
from manim_helpers import create_sphere_wireframe, create_sphere_surface

class SphereComparisonScene(ThreeDScene):
    def construct(self):
        # Create two spheres side by side

        # Left: Wireframe sphere
        wireframe = create_sphere_wireframe(
            center=np.array([-2.5, 0.0, 0.0]),
            radius=1.2,
            color="#457B9D",
            stroke_opacity=0.7
        )

        # Right: Surface sphere
        surface = create_sphere_surface(
            center=np.array([2.5, 0.0, 0.0]),
            radius=1.2,
            color="#457B9D",
            fill_opacity=0.7
        )

        # Add labels
        wireframe_label = Text("Wireframe", color="#1A1A1A").scale(0.5)
        wireframe_label.rotate(PI/2, axis=RIGHT)
        wireframe_label.move_to(np.array([-2.5, -2.0, 0]))

        surface_label = Text("Surface", color="#1A1A1A").scale(0.5)
        surface_label.rotate(PI/2, axis=RIGHT)
        surface_label.move_to(np.array([2.5, -2.0, 0]))

        # Add to scene
        self.add(wireframe, surface)
        self.add_fixed_orientation_mobjects(wireframe_label, surface_label)

        # Set camera
        self.set_camera_orientation(phi=65*DEGREES, theta=-45*DEGREES)
        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(10)
'''

# Write scene file in the main directory, not test_output
scene_file = Path("sphere_comparison_scene.py")
with open(scene_file, 'w') as f:
    f.write(SCENE_CODE)

print("=" * 70)
print("SPHERE COMPARISON TEST")
print("=" * 70)
print()

# Run manim
manim_path = "/Users/kairos/.local/bin/manim"
output_gif = OUTPUT_DIR / "sphere_comparison.gif"

print("Rendering comparison (this may take 10-20 seconds)...")
try:
    result = subprocess.run(
        [
            manim_path,
            "render",
            str(scene_file),
            "SphereComparisonScene",
            "-ql",
            "--format", "gif",
            "--output_file", str(output_gif.name)
        ],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        # Move the output file to the correct location
        generated_gif = Path("media") / "videos" / "sphere_comparison_scene" / "360p10" / output_gif.name
        if generated_gif.exists():
            import shutil
            shutil.copy(generated_gif, output_gif)
            print(f"✅ Saved: {output_gif}")
            print()
            print("✅ Test complete! Compare the two sphere styles:")
            print(f"   - Left: Wireframe (3 circles)")
            print(f"   - Right: Surface (full 3D sphere with shading)")
            print()
            print(f"Output: {output_gif}")
        else:
            print(f"⚠️  Generated file not found at expected location: {generated_gif}")
            print(result.stdout)
    else:
        print(f"❌ Manim failed with return code {result.returncode}")
        print(result.stderr)
        sys.exit(1)

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print()
print("=" * 70)
