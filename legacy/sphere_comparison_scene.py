
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
