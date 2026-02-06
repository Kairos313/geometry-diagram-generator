#!/usr/bin/env python3

from manim import *
import numpy as np
import os
import sys

# CRITICAL: Add grandparent directory to path to import helpers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from functions import *

class CompleteScene_a(Scene):
    def construct(self):
        self.camera.background_color = "#0C0C0C"
        
        # STEP 1: Create ALL geometric elements from JSON analysis (invisible)
        # Extract coordinates from blueprint tables for subpart (a)
        coord_O = np.array([0.000, 0.000, 0.000])
        coord_P = np.array([4.360, 0.000, 0.000])
        coord_Q = np.array([1.434, 2.048, 0.000])
        coord_R = np.array([1.434, -2.048, 0.000])
        
        # Create points identified in JSON geometric_elements arrays
        dots = VGroup(
            Dot(coord_O, radius=0.08, color="#FFFFFF"),
            Dot(coord_P, radius=0.08, color="#FFFFFF"),
            Dot(coord_Q, radius=0.08, color="#FFFFFF"),
            Dot(coord_R, radius=0.08, color="#FFFFFF")
        )
        
        # Create circle (shape/region element)
        circle_main = Circle(radius=2.5, color="#FFFFFF", stroke_width=2).move_to(coord_O)
        
        # Create lines identified in JSON (structural elements)
        line_PQ = Line(coord_P, coord_Q, color="#00FF00", stroke_width=3)
        line_PR = Line(coord_P, coord_R, color="#00FF00", stroke_width=3)
        line_OQ = Line(coord_O, coord_Q, color="#FF0000", stroke_width=2)
        line_OR = Line(coord_O, coord_R, color="#FF0000", stroke_width=2)
        line_OP = Line(coord_O, coord_P, color="#0000FF", stroke_width=2)
        
        lines = VGroup(line_PQ, line_PR, line_OQ, line_OR, line_OP)
        
        # Create labels (structural elements)
        labels = VGroup(
            MathTex("O", font_size=72, color="#FFFFFF").move_to(coord_O + np.array([-0.3, -0.3, 0])),
            MathTex("P", font_size=72, color="#FFFFFF").move_to(coord_P + np.array([0.3, 0.3, 0])),
            MathTex("Q", font_size=72, color="#FFFFFF").move_to(coord_Q + np.array([-0.3, 0.3, 0])),
            MathTex("R", font_size=72, color="#FFFFFF").move_to(coord_R + np.array([-0.3, -0.3, 0]))
        )
        
        # Create angle arcs using helper functions (structural elements)
        # For angle QPR (a = 70°) - use_smaller_angle=True since 70° ≤ 180°
        angle_QPR = create_2d_angle_arc_geometric(
            center=coord_P, point1=coord_Q, point2=coord_R,
            radius=0.5, num_points=30, use_smaller_angle=True,
            show_connections=False, connection_color="#FFFFFF",
            connection_opacity=0.2, connection_style="solid", color="#FFFF00"
        )
        
        # For angle QOR (b = 110°) - use_smaller_angle=True since 110° ≤ 180°
        angle_QOR = create_2d_angle_arc_geometric(
            center=coord_O, point1=coord_Q, point2=coord_R,
            radius=0.6, num_points=30, use_smaller_angle=True,
            show_connections=False, connection_color="#FFFFFF",
            connection_opacity=0.2, connection_style="solid", color="#00FFFF"
        )
        
        # For angle OQP (90°) - use_smaller_angle=True since 90° ≤ 180°
        angle_OQP = create_2d_angle_arc_geometric(
            center=coord_Q, point1=coord_O, point2=coord_P,
            radius=0.3, num_points=30, use_smaller_angle=True,
            show_connections=False, connection_color="#FFFFFF",
            connection_opacity=0.2, connection_style="solid", color="#FF00FF"
        )
        
        # For angle ORP (90°) - use_smaller_angle=True since 90° ≤ 180°
        angle_ORP = create_2d_angle_arc_geometric(
            center=coord_R, point1=coord_O, point2=coord_P,
            radius=0.3, num_points=30, use_smaller_angle=True,
            show_connections=False, connection_color="#FFFFFF",
            connection_opacity=0.2, connection_style="solid", color="#FF00FF"
        )
        
        # Create angle labels
        angle_labels = VGroup(
            MathTex("a", font_size=60, color="#FFFF00").move_to(coord_P + np.array([-0.8, 0, 0])),
            MathTex("b", font_size=60, color="#00FFFF").move_to(coord_O + np.array([0.8, 0, 0])),
            MathTex("90°", font_size=48, color="#FF00FF").move_to(coord_Q + np.array([0.5, -0.5, 0])),
            MathTex("90°", font_size=48, color="#FF00FF").move_to(coord_R + np.array([0.5, 0.5, 0]))
        )
        
        # Create quadrilateral for highlighting (shape/region element)
        region_quadrilateral_OQPR = Polygon(coord_O, coord_Q, coord_P, coord_R, 
                                          fill_opacity=0.2, fill_color="#FFA500", 
                                          stroke_width=2, stroke_color="#FFA500")
        
        # Combine all elements
        complete_figure = VGroup(
            circle_main, dots, lines, labels, 
            angle_QPR, angle_QOR, angle_OQP, angle_ORP,
            angle_labels, region_quadrilateral_OQPR
        )
        
        # STEP 2: Set all elements invisible initially
        complete_figure.set_opacity(0)
        
        # STEP 3: Auto-scale the complete figure
        auto_scale_to_left_screen(complete_figure, is_3d=False, margin_factor=0.85, pitch_angle=-40, yaw_angle=-20)
        self.add(complete_figure)
        
        # STEP 4: Follow sentence-by-sentence animation from JSON
        
        # Sentence 1: "Let's begin with Part A. We are given a circle with center O, and two tangents, PQ and PR, drawn from an external point P."
        circle_main.set_opacity(0.2)  # Shape/region element
        dots.set_opacity(1)           # Structural elements
        labels.set_opacity(1)         # Structural elements
        lines.set_opacity(1)          # Structural elements
        self.play(Create(circle_main), FadeIn(dots), FadeIn(labels))
        self.play(Create(line_PQ), Create(line_PR), Create(line_OQ), Create(line_OR), Create(line_OP))
        self.wait(0.5)
        
        # Sentence 2: "The problem asks for the relationship between angle 'a', which is angle QPR, and angle 'b', which is angle QOR."
        angle_QPR.set_opacity(1)      # Structural element
        angle_QOR.set_opacity(1)      # Structural element
        angle_labels[0].set_opacity(1) # Label for angle a
        angle_labels[1].set_opacity(1) # Label for angle b
        self.play(Create(angle_QPR), Create(angle_QOR))
        self.play(FadeIn(angle_labels[0]), FadeIn(angle_labels[1]))
        self.wait(0.5)
        
        # Sentence 3: "A key property of circles is that the radius is always perpendicular to the tangent at the point of contact."
        self.play(Indicate(line_OQ, color="#FFFF00"), Indicate(line_PQ, color="#FFFF00"))
        self.wait(0.5)
        
        # Sentence 4: "This means that the angles OQP and ORP are both right angles, measuring 90 degrees."
        angle_OQP.set_opacity(1)      # Structural element
        angle_ORP.set_opacity(1)      # Structural element
        angle_labels[2].set_opacity(1) # Label for 90°
        angle_labels[3].set_opacity(1) # Label for 90°
        self.play(Create(angle_OQP), Create(angle_ORP))
        self.play(FadeIn(angle_labels[2]), FadeIn(angle_labels[3]))
        self.wait(0.5)
        
        # Sentence 5: "Now, let's focus on the shape OQPR. It's a quadrilateral, and the sum of the interior angles of any quadrilateral is 360 degrees."
        region_quadrilateral_OQPR.set_opacity(0.2)  # Shape/region element
        self.play(Indicate(region_quadrilateral_OQPR, color="#FFA500"))
        self.wait(0.5)
        
        # Sentences 6-7: Mathematical equations (no new geometric elements)
        self.wait(1.0)
        
        # Sentences 8-9: Final relationship derivation (no new geometric elements)
        self.wait(1.0)
        
        # Animation ends naturally
        self.wait(2)

class CompleteScene_b(Scene):
    def construct(self):
        self.camera.background_color = "#0C0C0C"
        
        # STEP 1: Create ALL geometric elements from JSON analysis (invisible)
        # Extract coordinates from blueprint tables for subpart (b)
        coord_O = np.array([0.000, 0.000, 0.000])
        coord_P = np.array([2.887, 0.000, 0.000])
        coord_Q = np.array([2.165, 1.250, 0.000])
        coord_R = np.array([2.165, -1.250, 0.000])
        
        # Create points identified in JSON geometric_elements arrays
        dots = VGroup(
            Dot(coord_O, radius=0.08, color="#FFFFFF"),
            Dot(coord_P, radius=0.08, color="#FFFFFF"),
            Dot(coord_Q, radius=0.08, color="#FFFFFF"),
            Dot(coord_R, radius=0.08, color="#FFFFFF")
        )
        
        # Create circle (shape/region element)
        circle_main = Circle(radius=2.5, color="#FFFFFF", stroke_width=2).move_to(coord_O)
        
        # Create lines identified in JSON (structural elements)
        line_PQ = Line(coord_P, coord_Q, color="#00FF00", stroke_width=3)
        line_PR = Line(coord_P, coord_R, color="#00FF00", stroke_width=3)
        line_OQ = Line(coord_O, coord_Q, color="#FF0000", stroke_width=2)
        line_OR = Line(coord_O, coord_R, color="#FF0000", stroke_width=2)
        line_OP = Line(coord_O, coord_P, color="#0000FF", stroke_width=2)
        
        lines = VGroup(line_PQ, line_PR, line_OQ, line_OR, line_OP)
        
        # Create labels (structural elements)
        labels = VGroup(
            MathTex("O", font_size=72, color="#FFFFFF").move_to(coord_O + np.array([-0.3, -0.3, 0])),
            MathTex("P", font_size=72, color="#FFFFFF").move_to(coord_P + np.array([0.3, 0.3, 0])),
            MathTex("Q", font_size=72, color="#FFFFFF").move_to(coord_Q + np.array([-0.3, 0.3, 0])),
            MathTex("R", font_size=72, color="#FFFFFF").move_to(coord_R + np.array([-0.3, -0.3, 0]))
        )
        
        # Create angle arcs using helper functions (structural elements)
        # For angle QPR (a = 120°) - use_smaller_angle=True since 120° ≤ 180°
        angle_QPR = create_2d_angle_arc_geometric(
            center=coord_P, point1=coord_Q, point2=coord_R,
            radius=0.5, num_points=30, use_smaller_angle=True,
            show_connections=False, connection_color="#FFFFFF",
            connection_opacity=0.2, connection_style="solid", color="#FFFF00"
        )
        
        # For angle QOR (b = 60°) - use_smaller_angle=True since 60° ≤ 180°
        angle_QOR = create_2d_angle_arc_geometric(
            center=coord_O, point1=coord_Q, point2=coord_R,
            radius=0.6, num_points=30, use_smaller_angle=True,
            show_connections=False, connection_color="#FFFFFF",
            connection_opacity=0.2, connection_style="solid", color="#00FFFF"
        )
        
        # Create angle labels
        angle_labels = VGroup(
            MathTex("120°", font_size=60, color="#FFFF00").move_to(coord_P + np.array([-0.8, 0, 0])),
            MathTex("60°", font_size=60, color="#00FFFF").move_to(coord_O + np.array([0.8, 0, 0]))
        )
        
        # Combine all elements
        complete_figure = VGroup(
            circle_main, dots, lines, labels, 
            angle_QPR, angle_QOR, angle_labels
        )
        
        # STEP 2: Set all elements invisible initially
        complete_figure.set_opacity(0)
        
        # STEP 3: Auto-scale the complete figure
        auto_scale_to_left_screen(complete_figure, is_3d=False, margin_factor=0.85, pitch_angle=-40, yaw_angle=-20)
        self.add(complete_figure)
        
        # STEP 4: Follow sentence-by-sentence animation from JSON
        
        # Show the basic setup first
        circle_main.set_opacity(0.2)  # Shape/region element
        dots.set_opacity(1)           # Structural elements
        labels.set_opacity(1)         # Structural elements
        lines.set_opacity(1)          # Structural elements
        self.play(Create(circle_main), FadeIn(dots), FadeIn(labels))
        self.play(Create(line_PQ), Create(line_PR), Create(line_OQ), Create(line_OR), Create(line_OP))
        self.wait(0.5)
        
        # Sentence 1: "Now for Part B. We can use this exact same relationship. We're told a chord subtends an angle of 60 degrees at the center."
        angle_QOR.set_opacity(1)      # Structural element
        angle_labels[1].set_opacity(1) # Label for 60°
        self.play(Create(angle_QOR))
        self.play(FadeIn(angle_labels[1]))
        self.wait(0.5)
        
        # Sentence 2: "The angle at the center and the angle between the tangents at the ends of the chord are supplementary."
        self.wait(0.5)
        
        # Sentence 3: "So, the angle between the tangents is 180 degrees minus 60 degrees, which is 120 degrees."
        angle_QPR.set_opacity(1)      # Structural element
        angle_labels[0].set_opacity(1) # Label for 120°
        self.play(Create(angle_QPR))
        self.play(FadeIn(angle_labels[0]))
        self.wait(0.5)
        
        # Final highlight of the key relationship
        self.play(Indicate(angle_QPR, color="#FFFF00"), Indicate(angle_QOR, color="#00FFFF"))
        self.wait(2)