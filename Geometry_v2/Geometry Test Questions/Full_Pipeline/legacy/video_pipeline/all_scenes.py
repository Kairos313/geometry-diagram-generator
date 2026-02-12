#!/usr/bin/env python3

import sys
import os
from manim import *
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from functions import *

def create_complete_diagram_main():
    import math
    
    coord_O = np.array([0.000, 0.000, 0.000])
    coord_P = np.array([4.360, 0.000, 0.000])
    coord_Q = np.array([1.434, 2.048, 0.000])
    coord_R = np.array([1.434, -2.048, 0.000])
    
    dots = VGroup(
        Dot(coord_O, radius=0.08, color="#FFFFFF"),
        Dot(coord_P, radius=0.08, color="#FFFFFF"),
        Dot(coord_Q, radius=0.08, color="#FFFFFF"),
        Dot(coord_R, radius=0.08, color="#FFFFFF")
    )
    
    circle_main = Circle(radius=2.5, color="#FFFFFF", stroke_width=2).move_to(coord_O)
    
    lines = VGroup(
        Line(coord_P, coord_Q, color="#00FF00", stroke_width=3),
        Line(coord_P, coord_R, color="#00FF00", stroke_width=3),
        Line(coord_O, coord_Q, color="#FF0000", stroke_width=2),
        Line(coord_O, coord_R, color="#FF0000", stroke_width=2),
        Line(coord_O, coord_P, color="#0000FF", stroke_width=2)
    )
    
    labels = VGroup(
        MathTex("O", font_size=72, color="#FFFFFF").move_to(coord_O + np.array([-0.3, -0.3, 0])),
        MathTex("P", font_size=72, color="#FFFFFF").move_to(coord_P + np.array([0.3, 0.3, 0])),
        MathTex("Q", font_size=72, color="#FFFFFF").move_to(coord_Q + np.array([-0.3, 0.3, 0])),
        MathTex("R", font_size=72, color="#FFFFFF").move_to(coord_R + np.array([-0.3, -0.3, 0]))
    )
    
    angle_QPR = create_2d_angle_arc_geometric(
        center=coord_P, point1=coord_Q, point2=coord_R,
        radius=0.5, num_points=30, use_smaller_angle=True,
        show_connections=False, color="#FFFF00"
    )
    
    angle_QOR = create_2d_angle_arc_geometric(
        center=coord_O, point1=coord_Q, point2=coord_R,
        radius=0.6, num_points=30, use_smaller_angle=True,
        show_connections=False, color="#00FFFF"
    )
    
    angle_OQP = create_2d_angle_arc_geometric(
        center=coord_Q, point1=coord_O, point2=coord_P,
        radius=0.3, num_points=30, use_smaller_angle=True,
        show_connections=False, color="#FF00FF"
    )
    
    angle_ORP = create_2d_angle_arc_geometric(
        center=coord_R, point1=coord_O, point2=coord_P,
        radius=0.3, num_points=30, use_smaller_angle=True,
        show_connections=False, color="#FF00FF"
    )
    
    angle_QPR_label = MathTex("a", font_size=60, color="#FFFF00").move_to(coord_P + np.array([-0.8, 0, 0]))
    angle_QOR_label = MathTex("b", font_size=60, color="#00FFFF").move_to(coord_O + np.array([0.8, 0, 0]))
    angle_OQP_label = MathTex("90°", font_size=48, color="#FF00FF").move_to(coord_Q + np.array([0.5, -0.5, 0]))
    angle_ORP_label = MathTex("90°", font_size=48, color="#FF00FF").move_to(coord_R + np.array([0.5, 0.5, 0]))
    
    region_quadrilateral_OQPR_interior = Polygon(coord_O, coord_Q, coord_P, coord_R, 
                                               fill_opacity=0.2, fill_color="#FFA500", 
                                               stroke_width=2, stroke_color="#FFA500")
    
    complete_figure = VGroup(
        circle_main, dots, lines, labels,
        angle_QPR, angle_QOR, angle_OQP, angle_ORP,
        angle_QPR_label, angle_QOR_label, angle_OQP_label, angle_ORP_label,
        region_quadrilateral_OQPR_interior
    )
    
    complete_figure.set_opacity(0)
    
    return {
        "complete_figure": complete_figure,
        "elements": {
            "circle_main": circle_main,
            "point_O": dots[0],
            "point_P": dots[1],
            "point_Q": dots[2],
            "point_R": dots[3],
            "point_O_label": labels[0],
            "point_P_label": labels[1],
            "point_Q_label": labels[2],
            "point_R_label": labels[3],
            "line_PQ": lines[0],
            "line_PR": lines[1],
            "line_OQ": lines[2],
            "line_OR": lines[3],
            "line_OP": lines[4],
            "angle_QPR": angle_QPR,
            "angle_QOR": angle_QOR,
            "angle_OQP": angle_OQP,
            "angle_ORP": angle_ORP,
            "angle_QPR_label": angle_QPR_label,
            "angle_QOR_label": angle_QOR_label,
            "angle_OQP_label": angle_OQP_label,
            "angle_ORP_label": angle_ORP_label,
            "region_quadrilateral_OQPR_interior": region_quadrilateral_OQPR_interior
        }
    }

class PartASetupScene(Scene):
    def construct(self):
        self.camera.background_color = "#0C0C0C"
        
        complete_diagram = create_complete_diagram_main()
        complete_figure = complete_diagram["complete_figure"]
        elements = complete_diagram["elements"]
        
        auto_scale_to_left_screen(complete_figure, is_3d=False)
        self.add(complete_figure)
        
        try:
            self.add_sound("/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/Scene/part_A_setup_scene.mp3")
        except Exception as e:
            print(f"Warning: Could not add audio file: {e}")
        
        add_explanation_text(self, MathTex(r"\text{Part A: Given a circle with centre O and tangents PQ and PR.}"))
        
        elements["circle_main"].set_opacity(0.2)
        elements["point_O"].set_opacity(1.0)
        elements["point_P"].set_opacity(1.0)
        elements["point_Q"].set_opacity(1.0)
        elements["point_R"].set_opacity(1.0)
        elements["point_O_label"].set_opacity(1.0)
        elements["point_P_label"].set_opacity(1.0)
        elements["point_Q_label"].set_opacity(1.0)
        elements["point_R_label"].set_opacity(1.0)
        elements["line_PQ"].set_opacity(1.0)
        elements["line_PR"].set_opacity(1.0)
        elements["line_OQ"].set_opacity(1.0)
        elements["line_OR"].set_opacity(1.0)
        elements["line_OP"].set_opacity(1.0)
        
        self.play(Create(elements["circle_main"]), Create(elements["point_O"]), Create(elements["point_P"]), 
                 Create(elements["point_Q"]), Create(elements["point_R"]), Create(elements["line_PQ"]), 
                 Create(elements["line_PR"]), Create(elements["line_OQ"]), Create(elements["line_OR"]), 
                 Create(elements["line_OP"]))
        
        num_indicates = int(8.12 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5 + 1.0
        remaining_wait_time = 8.12 - total_animation_time - total_indicate_time
        
        for i in range(num_indicates):
            if i > 0:
                self.wait(max(0.1, 2.0))
            self.play(Indicate(elements["circle_main"], color="#FFFF00"), 
                     Indicate(elements["line_PQ"], color="#FFFF00"), 
                     Indicate(elements["line_PR"], color="#FFFF00"))
        
        self.wait(max(0.1, remaining_wait_time - (num_indicates - 1) * 2.0))
        
        add_explanation_text(self, MathTex(r"\text{Find the relation between } a = \angle QPR \text{ and } b = \angle QOR."))
        
        elements["angle_QPR"].set_opacity(1.0)
        elements["angle_QOR"].set_opacity(1.0)
        elements["angle_QPR_label"].set_opacity(1.0)
        elements["angle_QOR_label"].set_opacity(1.0)
        
        self.play(Create(elements["angle_QPR"]), Create(elements["angle_QOR"]), 
                 Create(elements["angle_QPR_label"]), Create(elements["angle_QOR_label"]))
        
        num_indicates = int(7.89 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5 + 1.0
        remaining_wait_time = 7.89 - total_animation_time - total_indicate_time
        
        for i in range(num_indicates):
            if i > 0:
                self.wait(max(0.1, 2.0))
            self.play(Indicate(elements["angle_QPR"], color="#FFFF00"), 
                     Indicate(elements["angle_QOR"], color="#FFFF00"))
        
        self.wait(max(0.1, remaining_wait_time - (num_indicates - 1) * 2.0))

class RadiusTangentPropertyScene(Scene):
    def construct(self):
        self.camera.background_color = "#0C0C0C"
        
        complete_diagram = create_complete_diagram_main()
        complete_figure = complete_diagram["complete_figure"]
        elements = complete_diagram["elements"]
        
        auto_scale_to_left_screen(complete_figure, is_3d=False)
        self.add(complete_figure)
        
        try:
            self.add_sound("/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/Scene/radius_tangent_property_scene.mp3")
        except Exception as e:
            print(f"Warning: Could not add audio file: {e}")
        
        elements["circle_main"].set_opacity(0.2)
        elements["point_O"].set_opacity(1.0)
        elements["point_O_label"].set_opacity(1.0)
        elements["point_P"].set_opacity(1.0)
        elements["point_P_label"].set_opacity(1.0)
        elements["point_Q"].set_opacity(1.0)
        elements["point_Q_label"].set_opacity(1.0)
        elements["point_R"].set_opacity(1.0)
        elements["point_R_label"].set_opacity(1.0)
        elements["line_PQ"].set_opacity(1.0)
        elements["line_PR"].set_opacity(1.0)
        elements["line_OQ"].set_opacity(1.0)
        elements["line_OR"].set_opacity(1.0)
        elements["line_OP"].set_opacity(1.0)
        elements["angle_QPR_label"].set_opacity(1.0)
        elements["angle_QOR_label"].set_opacity(1.0)
        
        add_explanation_text(self, MathTex(r"\text{Property: Radius } \perp \text{ Tangent}"))
        
        num_indicates = int(6.11 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5
        remaining_wait_time = 6.11 - total_animation_time - total_indicate_time
        
        for i in range(num_indicates):
            if i > 0:
                self.wait(max(0.1, 2.0))
            self.play(Indicate(elements["line_OQ"], color="#FFFF00"), 
                     Indicate(elements["line_PQ"], color="#FFFF00"))
        
        self.wait(max(0.1, remaining_wait_time - (num_indicates - 1) * 2.0))
        
        add_explanation_text(self, MathTex(r"\angle OQP = 90^{\circ} \text{ and } \angle ORP = 90^{\circ}"))
        
        elements["angle_OQP"].set_opacity(1.0)
        elements["angle_ORP"].set_opacity(1.0)
        elements["angle_OQP_label"].set_opacity(1.0)
        elements["angle_ORP_label"].set_opacity(1.0)
        
        self.play(Create(elements["angle_OQP"]), Create(elements["angle_ORP"]), 
                 Create(elements["angle_OQP_label"]), Create(elements["angle_ORP_label"]))
        
        num_indicates = int(5.56 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5 + 1.0
        remaining_wait_time = 5.56 - total_animation_time - total_indicate_time
        
        for i in range(num_indicates):
            if i > 0:
                self.wait(max(0.1, 2.0))
            self.play(Indicate(elements["angle_OQP"], color="#FFFF00"), 
                     Indicate(elements["angle_ORP"], color="#FFFF00"))
        
        self.wait(max(0.1, remaining_wait_time - (num_indicates - 1) * 2.0))

class QuadrilateralAngleSumScene(Scene):
    def construct(self):
        self.camera.background_color = "#0C0C0C"
        
        complete_diagram = create_complete_diagram_main()
        complete_figure = complete_diagram["complete_figure"]
        elements = complete_diagram["elements"]
        
        auto_scale_to_left_screen(complete_figure, is_3d=False)
        self.add(complete_figure)
        
        try:
            self.add_sound("/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/Scene/quadrilateral_angle_sum_scene.mp3")
        except Exception as e:
            print(f"Warning: Could not add audio file: {e}")
        
        elements["circle_main"].set_opacity(0.2)
        elements["point_O"].set_opacity(1.0)
        elements["point_O_label"].set_opacity(1.0)
        elements["point_P"].set_opacity(1.0)
        elements["point_P_label"].set_opacity(1.0)
        elements["point_Q"].set_opacity(1.0)
        elements["point_Q_label"].set_opacity(1.0)
        elements["point_R"].set_opacity(1.0)
        elements["point_R_label"].set_opacity(1.0)
        elements["line_PQ"].set_opacity(1.0)
        elements["line_PR"].set_opacity(1.0)
        elements["line_OQ"].set_opacity(1.0)
        elements["line_OR"].set_opacity(1.0)
        elements["line_OP"].set_opacity(1.0)
        elements["angle_QPR_label"].set_opacity(1.0)
        elements["angle_QOR_label"].set_opacity(1.0)
        elements["angle_OQP_label"].set_opacity(1.0)
        elements["angle_ORP_label"].set_opacity(1.0)
        
        add_explanation_text(self, MathTex(r"\text{In quadrilateral OQPR, sum of angles} = 360^{\circ}"))
        
        elements["region_quadrilateral_OQPR_interior"].set_opacity(0.2)
        self.play(Create(elements["region_quadrilateral_OQPR_interior"]))
        
        num_indicates = int(9.8 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5 + 1.0
        remaining_wait_time = 9.8 - total_animation_time - total_indicate_time
        
        for i in range(num_indicates):
            if i > 0:
                self.wait(max(0.1, 2.0))
            self.play(Indicate(elements["region_quadrilateral_OQPR_interior"], color="#FFFF00"))
        
        self.wait(max(0.1, remaining_wait_time - (num_indicates - 1) * 2.0))
        
        add_explanation_text(self, MathTex(r"\angle QOR + \angle ORP + \angle QPR + \angle OQP = 360^{\circ}"))
        
        num_indicates = int(9.61 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5
        remaining_wait_time = 9.61 - total_animation_time - total_indicate_time
        
        self.wait(max(0.1, remaining_wait_time))
        
        add_explanation_text(self, MathTex(r"b + 90^{\circ} + a + 90^{\circ} = 360^{\circ}"))
        
        num_indicates = int(9.09 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5
        remaining_wait_time = 9.09 - total_animation_time - total_indicate_time
        
        self.wait(max(0.1, remaining_wait_time))

class DerivingTheRelationScene(Scene):
    def construct(self):
        self.camera.background_color = "#0C0C0C"
        
        complete_diagram = create_complete_diagram_main()
        complete_figure = complete_diagram["complete_figure"]
        elements = complete_diagram["elements"]
        
        auto_scale_to_left_screen(complete_figure, is_3d=False)
        self.add(complete_figure)
        
        try:
            self.add_sound("/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/Scene/deriving_the_relation_scene.mp3")
        except Exception as e:
            print(f"Warning: Could not add audio file: {e}")
        
        elements["circle_main"].set_opacity(0.2)
        elements["point_O"].set_opacity(1.0)
        elements["point_O_label"].set_opacity(1.0)
        elements["point_P"].set_opacity(1.0)
        elements["point_P_label"].set_opacity(1.0)
        elements["point_Q"].set_opacity(1.0)
        elements["point_Q_label"].set_opacity(1.0)
        elements["point_R"].set_opacity(1.0)
        elements["point_R_label"].set_opacity(1.0)
        elements["line_PQ"].set_opacity(1.0)
        elements["line_PR"].set_opacity(1.0)
        elements["line_OQ"].set_opacity(1.0)
        elements["line_OR"].set_opacity(1.0)
        elements["line_OP"].set_opacity(1.0)
        elements["angle_QPR_label"].set_opacity(1.0)
        elements["angle_QOR_label"].set_opacity(1.0)
        elements["angle_OQP_label"].set_opacity(1.0)
        elements["angle_ORP_label"].set_opacity(1.0)
        
        add_explanation_text(self, MathTex(r"a + b + 180^{\circ} = 360^{\circ}"))
        
        num_indicates = int(8.02 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5
        remaining_wait_time = 8.02 - total_animation_time - total_indicate_time
        
        self.wait(max(0.1, remaining_wait_time))
        
        add_explanation_text(self, MathTex(r"a + b = 180^{\circ}"))
        
        num_indicates = int(10.27 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5
        remaining_wait_time = 10.27 - total_animation_time - total_indicate_time
        
        self.wait(max(0.1, remaining_wait_time))

class SolvingPartBScene(Scene):
    def construct(self):
        self.camera.background_color = "#0C0C0C"
        
        complete_diagram = create_complete_diagram_main()
        complete_figure = complete_diagram["complete_figure"]
        elements = complete_diagram["elements"]
        
        auto_scale_to_left_screen(complete_figure, is_3d=False)
        self.add(complete_figure)
        
        try:
            self.add_sound("/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/Scene/solving_part_B_scene.mp3")
        except Exception as e:
            print(f"Warning: Could not add audio file: {e}")
        
        elements["circle_main"].set_opacity(0.2)
        elements["point_O"].set_opacity(1.0)
        elements["point_O_label"].set_opacity(1.0)
        elements["point_P"].set_opacity(1.0)
        elements["point_P_label"].set_opacity(1.0)
        elements["point_Q"].set_opacity(1.0)
        elements["point_Q_label"].set_opacity(1.0)
        elements["point_R"].set_opacity(1.0)
        elements["point_R_label"].set_opacity(1.0)
        elements["line_PQ"].set_opacity(1.0)
        elements["line_PR"].set_opacity(1.0)
        elements["line_OQ"].set_opacity(1.0)
        elements["line_OR"].set_opacity(1.0)
        elements["line_OP"].set_opacity(1.0)
        elements["angle_QPR_label"].set_opacity(1.0)
        elements["angle_QOR_label"].set_opacity(1.0)
        elements["angle_OQP_label"].set_opacity(1.0)
        elements["angle_ORP_label"].set_opacity(1.0)
        
        add_explanation_text(self, MathTex(r"\text{Part B: Central angle } = 60^{\circ}"))
        
        num_indicates = int(7.05 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5
        remaining_wait_time = 7.05 - total_animation_time - total_indicate_time
        
        self.wait(max(0.1, remaining_wait_time))
        
        add_explanation_text(self, MathTex(r"\text{Angle between tangents} + \text{Central angle} = 180^{\circ}"))
        
        num_indicates = int(5.43 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5
        remaining_wait_time = 5.43 - total_animation_time - total_indicate_time
        
        self.wait(max(0.1, remaining_wait_time))
        
        add_explanation_text(self, MathTex(r"\text{Angle between tangents} = 180^{\circ} - 60^{\circ} = 120^{\circ}"))
        
        num_indicates = int(5.75 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5
        remaining_wait_time = 5.75 - total_animation_time - total_indicate_time
        
        self.wait(max(0.1, remaining_wait_time))

class KeyTakeawaysScene(Scene):
    def construct(self):
        self.camera.background_color = "#0C0C0C"
        
        complete_diagram = create_complete_diagram_main()
        complete_figure = complete_diagram["complete_figure"]
        elements = complete_diagram["elements"]
        
        auto_scale_to_left_screen(complete_figure, is_3d=False)
        self.add(complete_figure)
        
        try:
            self.add_sound("/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/Scene/key_takeaways_scene.mp3")
        except Exception as e:
            print(f"Warning: Could not add audio file: {e}")
        
        elements["circle_main"].set_opacity(0.2)
        elements["point_O"].set_opacity(1.0)
        elements["point_O_label"].set_opacity(1.0)
        elements["point_P"].set_opacity(1.0)
        elements["point_P_label"].set_opacity(1.0)
        elements["point_Q"].set_opacity(1.0)
        elements["point_Q_label"].set_opacity(1.0)
        elements["point_R"].set_opacity(1.0)
        elements["point_R_label"].set_opacity(1.0)
        elements["line_PQ"].set_opacity(1.0)
        elements["line_PR"].set_opacity(1.0)
        elements["line_OQ"].set_opacity(1.0)
        elements["line_OR"].set_opacity(1.0)
        elements["line_OP"].set_opacity(1.0)
        elements["angle_QPR_label"].set_opacity(1.0)
        elements["angle_QOR_label"].set_opacity(1.0)
        elements["angle_OQP_label"].set_opacity(1.0)
        elements["angle_ORP_label"].set_opacity(1.0)
        
        add_explanation_text(self, MathTex(r"\text{Key Theorem}"))
        
        elements["region_quadrilateral_OQPR_interior"].set_opacity(0.2)
        self.play(Create(elements["region_quadrilateral_OQPR_interior"]))
        
        num_indicates = int(4.18 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5 + 1.0
        remaining_wait_time = 4.18 - total_animation_time - total_indicate_time
        
        for i in range(num_indicates):
            if i > 0:
                self.wait(max(0.1, 2.0))
            self.play(Indicate(elements["region_quadrilateral_OQPR_interior"], color="#FFFF00"))
        
        self.wait(max(0.1, remaining_wait_time - (num_indicates - 1) * 2.0))
        
        add_explanation_text(self, MathTex(r"\text{Angle between tangents} + \text{Central angle} = 180^{\circ}"))
        
        num_indicates = int(9.14 / 2.5)
        total_indicate_time = num_indicates * 0.5
        total_animation_time = 0.5
        remaining_wait_time = 9.14 - total_animation_time - total_indicate_time
        
        for i in range(num_indicates):
            if i > 0:
                self.wait(max(0.1, 2.0))
            self.play(Indicate(elements["angle_QPR"], color="#FFFF00"), 
                     Indicate(elements["angle_QOR"], color="#FFFF00"))
        
        self.wait(max(0.1, remaining_wait_time - (num_indicates - 1) * 2.0))
        
        self.play(FadeOut(complete_figure), run_time=2.0)