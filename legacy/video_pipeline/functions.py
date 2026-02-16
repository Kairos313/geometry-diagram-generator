

# =====================================================================
# Universal Auto-Scaling and Positioning Functions
# =====================================================================
from manim import *
import numpy as np

def create_2d_angle_arc_geometric(center, point1, point2, radius=0.5,
                                   num_points=30, use_smaller_angle=True,
                                   show_connections=False, connection_color=WHITE, 
                                   connection_opacity=0.8, connection_style="dashed", 
                                   color=YELLOW) -> "VGroup":
    """
    Creates a 2D angle arc using the same geometric logic as the 3D version.
    This completely avoids Manim's quadrant system by using direct vector mathematics.

    Args:
        center: The vertex of the angle
        point1, point2: Points defining the two vectors of the angle
        radius: The radius of the angle arc
        num_points: Number of points for arc smoothness
        use_smaller_angle: If True, draws the smaller angle; if False, draws the reflex angle
        show_connections: If True, adds connection lines from arc endpoints to center
        connection_color: Color of the connection lines and dots
        connection_opacity: Opacity of the connection lines
        connection_style: Style of connection lines ("solid", "dashed")
        color: The color of the arc itself

    Returns:
        VGroup: A group containing the arc and any optional connection mobjects
    """
    center = np.array(center, dtype=float)
    v1 = np.array(point1, dtype=float) - center
    v2 = np.array(point2, dtype=float) - center

    # Ensure vectors are non-zero
    if np.linalg.norm(v1) < 1e-9 or np.linalg.norm(v2) < 1e-9:
        return VGroup()

    v1_unit = v1 / np.linalg.norm(v1)
    v2_unit = v2 / np.linalg.norm(v2)

    # For 2D, we work in the xy-plane, so we can use 2D cross product
    # 2D cross product gives us the z-component of the 3D cross product
    cross_product_z = v1_unit[0] * v2_unit[1] - v1_unit[1] * v2_unit[0]
    
    # Handle collinear vectors
    if abs(cross_product_z) < 1e-9:
        dot_product = np.dot(v1_unit[:2], v2_unit[:2])
        if dot_product > 0.999:  # Parallel, same direction
            return VGroup()
        else:  # Anti-parallel, opposite directions
            # For opposite vectors, create a half-circle
            if use_smaller_angle:
                return VGroup()  # No smaller angle for opposite vectors
            # For reflex angle (opposite vectors), we'll create a semicircle

    # Create orthonormal basis in 2D
    u_axis = v1_unit[:2]  # First basis vector (along v1)
    
    # Second basis vector perpendicular to u_axis
    # We choose the direction based on the cross product to ensure correct orientation
    if cross_product_z >= 0:  # Counter-clockwise orientation
        v_axis = np.array([-u_axis[1], u_axis[0]])  # 90-degree counter-clockwise rotation
    else:  # Clockwise orientation
        v_axis = np.array([u_axis[1], -u_axis[0]])   # 90-degree clockwise rotation

    # Calculate the angle between vectors
    dot_product = np.dot(v1_unit[:2], v2_unit[:2])
    angle_between = np.arccos(np.clip(dot_product, -1.0, 1.0))
    
    # Determine the arc angle based on preference
    if use_smaller_angle:
        arc_angle = angle_between
    else:
        arc_angle = 2 * np.pi - angle_between

    # Generate points for the arc using parametric equations
    # Same logic as 3D version: center + radius * (cos(t) * u_axis + sin(t) * v_axis)
    arc_points_2d = []
    for t in np.linspace(0, arc_angle, num_points):
        point_2d = center[:2] + radius * (np.cos(t) * u_axis + np.sin(t) * v_axis)
        # Convert back to 3D for Manim (add z=0)
        point_3d = np.array([point_2d[0], point_2d[1], 0])
        arc_points_2d.append(point_3d)

    if len(arc_points_2d) < 2:
        return VGroup()

    # Create the arc using VMobject
    arc = VMobject(stroke_color=color, stroke_width=4).set_points_smoothly(arc_points_2d)
    arc_group = VGroup(arc)

    # Add optional connection lines (similar to 3D version)
    if show_connections and len(arc_points_2d) >= 2:
        arc_start, arc_end = arc_points_2d[0], arc_points_2d[-1]
        center_3d = np.array([center[0], center[1], 0])

        if connection_style == "dashed":
            connection1 = DashedLine(center_3d, arc_start, color=connection_color, 
                                   stroke_width=2, stroke_opacity=connection_opacity)
            connection2 = DashedLine(center_3d, arc_end, color=connection_color, 
                                   stroke_width=2, stroke_opacity=connection_opacity)
        else:  # solid
            connection1 = Line(center_3d, arc_start, color=connection_color, 
                             stroke_width=2, stroke_opacity=connection_opacity)
            connection2 = Line(center_3d, arc_end, color=connection_color, 
                             stroke_width=2, stroke_opacity=connection_opacity)

        dot1 = Dot(point=arc_start, color=connection_color, radius=0.03)
        dot2 = Dot(point=arc_end, color=connection_color, radius=0.03)

        arc_group.add(connection1, connection2, dot1, dot2)

    return arc_group


def _robust_bounds_calculation(geometry_group):
    """
    Robustly calculates the spatial bounds of a VGroup by safely extracting
    points from all contained mobjects. It handles various mobject types and
    avoids errors with uninitialized or complex objects.

    Args:
        geometry_group (VGroup): The group of mobjects to analyze.

    Returns:
        list: A list of all extracted 3D points (as np.ndarray).
    """
    all_points = []

    def extract_points_safely(mobject):
        """Safely extract points from a single mobject."""
        points = []
        try:
            # Method 1: Get center (most reliable fallback)
            if hasattr(mobject, 'get_center'):
                center = mobject.get_center()
                if center is not None and len(center) > 0:
                    points.append(center)
        except Exception:
            pass

        try:
            # Method 2: Get start/end points (for lines)
            if hasattr(mobject, 'get_start') and hasattr(mobject, 'get_end') and hasattr(mobject, 'points') and len(mobject.points) > 0:
                start, end = mobject.get_start(), mobject.get_end()
                if start is not None and end is not None:
                    points.extend([start, end])
        except Exception:
            pass

        try:
            # Method 3: Get vertices (for polygons/polyhedra)
            if hasattr(mobject, 'get_vertices'):
                vertices = mobject.get_vertices()
                if vertices is not None and len(vertices) > 0:
                    points.extend(vertices)
        except Exception:
            pass

        try:
            # Method 4: Get all points (for complex shapes)
            if hasattr(mobject, 'points') and len(mobject.points) > 0:
                # Sample points to avoid performance issues with very complex objects
                sample_points = mobject.points[::max(1, len(mobject.points)//20)]
                points.extend(sample_points)
        except Exception:
            pass

        return points

    # Recursively iterate through all mobjects and submobjects
    for mobject in geometry_group.get_family():
        all_points.extend(extract_points_safely(mobject))

    return all_points


def auto_scale_to_left_screen_2d(geometry_group, margin_factor=0.85):
    """
    Auto-scales and positions a 2D VGroup to fit neatly on the left
    side of the Manim screen.

    Args:
        geometry_group (VGroup): The 2D geometry to transform.
        margin_factor (float): The percentage of the target area to fill (e.g., 0.85 for 85%).

    Returns:
        dict: A dictionary containing details of the transformation applied.
    """
    LEFT_SCREEN_BOUNDS = {
        'center': np.array([-3.5, 0.0, 0.0]),
        'width': 6.0,
        'height': 7.0
    }

    all_points = _robust_bounds_calculation(geometry_group)

    if not all_points:
        # Fallback if no points are found
        current_center = geometry_group.get_center()
        bounds = {'width': 2.0, 'height': 2.0, 'center': current_center}
    else:
        points_array = np.array(all_points)
        min_coords = np.min(points_array, axis=0)
        max_coords = np.max(points_array, axis=0)
        bounds = {
            'width': max(max_coords[0] - min_coords[0], 1e-6),
            'height': max(max_coords[1] - min_coords[1], 1e-6),
            'center': (min_coords + max_coords) / 2
        }

    # Calculate scale factor to fit within the target bounds
    scale_x = (LEFT_SCREEN_BOUNDS['width'] * margin_factor) / bounds['width']
    scale_y = (LEFT_SCREEN_BOUNDS['height'] * margin_factor) / bounds['height']
    scale_factor = min(scale_x, scale_y)

    # Apply transformations: 1. Center at origin, 2. Scale, 3. Move to target
    geometry_group.shift(-bounds['center'])
    geometry_group.scale(scale_factor)
    geometry_group.move_to(LEFT_SCREEN_BOUNDS['center'])

    return {
        'scale_factor': scale_factor,
        'original_center': bounds['center'],
        'final_center': geometry_group.get_center()
    }


def auto_scale_to_left_screen_3d(geometry_group, margin_factor=0.85, pitch_angle=-40, yaw_angle=-20):
    """
    Auto-scales, rotates, and positions a 3D VGroup to fit neatly on the
    left side of the Manim screen with a standard perspective view.

    Args:
        geometry_group (VGroup): The 3D geometry to transform.
        margin_factor (float): The percentage of the target area to fill.
        pitch_angle (float): Initial rotation around the RIGHT axis (X-axis) in degrees.
        yaw_angle (float): Initial rotation around the OUT axis (Z-axis) in degrees.

    Returns:
        dict: A dictionary containing details of the transformation applied.
    """
    LEFT_SCREEN_BOUNDS = {
        'center': np.array([-3.5, 0.0, 0.0]),
        'width': 6.0,
        'height': 7.0
    }

    all_points = _robust_bounds_calculation(geometry_group)

    if not all_points:
        # Fallback if no points are found
        current_center = geometry_group.get_center()
        bounds = {'width': 2.0, 'height': 2.0, 'depth': 2.0, 'center': current_center}
    else:
        points_array = np.array(all_points)
        min_coords = np.min(points_array, axis=0)
        max_coords = np.max(points_array, axis=0)
        bounds = {
            'width': max(max_coords[0] - min_coords[0], 1e-6),
            'height': max(max_coords[1] - min_coords[1], 1e-6),
            'depth': max(max_coords[2] - min_coords[2], 1e-6),
            'center': (min_coords + max_coords) / 2
        }

    # Calculate scale factor to fit all dimensions
    scale_x = (LEFT_SCREEN_BOUNDS['width'] * margin_factor) / bounds['width']
    scale_y = (LEFT_SCREEN_BOUNDS['height'] * margin_factor) / bounds['height']
    scale_z = (LEFT_SCREEN_BOUNDS['height'] * margin_factor) / bounds['depth'] # Depth also scales relative to screen height
    scale_factor = min(scale_x, scale_y, scale_z)

    # Apply transformations in a specific order for predictable results
    geometry_group.shift(-bounds['center'])       # 1. Center the object at the origin
    geometry_group.scale(scale_factor)            # 2. Scale it down uniformly
    geometry_group.rotate(pitch_angle * DEGREES, axis=RIGHT, about_point=ORIGIN) # 3. Apply pitch
    geometry_group.rotate(yaw_angle * DEGREES, axis=OUT, about_point=ORIGIN)     # 4. Apply yaw
    geometry_group.move_to(LEFT_SCREEN_BOUNDS['center']) # 5. Move to final position

    return {
        'scale_factor': scale_factor,
        'original_center': bounds['center'],
        'final_center': geometry_group.get_center()
    }


def auto_scale_to_left_screen(geometry_group, is_3d, margin_factor=0.85, pitch_angle=-40, yaw_angle=-20):
    """
    Universal dispatcher for auto-scaling. Calls the appropriate 2D or 3D
    function based on the 'is_3d' flag.

    Args:
        geometry_group (VGroup): The geometry to scale and position.
        is_3d (bool): Set to True for 3D geometry, False for 2D.
        margin_factor (float): Fraction of screen space to use.
        pitch_angle (float): Rotation around RIGHT axis in degrees (3D only).
        yaw_angle (float): Rotation around OUT axis in degrees (3D only).

    Returns:
        dict: Information about the scaling operation.
    """
    if is_3d:
        return auto_scale_to_left_screen_3d(geometry_group, margin_factor, pitch_angle, yaw_angle)
    else:
        return auto_scale_to_left_screen_2d(geometry_group, margin_factor)


# =====================================================================
# 3D Angle Creation Function
# =====================================================================

def create_3d_angle_arc_with_connections(center, point1, point2, radius=0.5,
                                           num_points=30, show_connections=True,
                                           connection_color=WHITE, connection_opacity=0.8,
                                           connection_style="dashed", color=YELLOW) -> "VGroup":
    """
    Creates a smooth 3D arc to represent an angle between three points in space.
    Optionally adds connection lines from the arc endpoints to the angle's vertex.

    Args:
        center (np.ndarray): The vertex of the angle.
        point1, point2 (np.ndarray): Points defining the two vectors of the angle.
        radius (float): The radius of the angle arc.
        num_points (int): Number of points for arc smoothness.
        show_connections (bool): If True, adds lines and dots connecting arc to center.
        connection_color: Color of the connection lines and dots.
        connection_opacity (float): Opacity of the connection lines.
        connection_style (str): Style of connection line ("solid", "dashed", "dotted").
        color: The color of the arc itself.

    Returns:
        VGroup: A group containing the arc and any optional connection mobjects.
    """
    center = np.array(center, dtype=float)
    v1 = np.array(point1, dtype=float) - center
    v2 = np.array(point2, dtype=float) - center

    # Ensure vectors are non-zero
    if np.linalg.norm(v1) < 1e-9 or np.linalg.norm(v2) < 1e-9:
        return VGroup()

    v1_unit = v1 / np.linalg.norm(v1)
    v2_unit = v2 / np.linalg.norm(v2)

    # Find the normal vector to the plane of the angle
    normal = np.cross(v1_unit, v2_unit)

    # Handle cases where vectors are collinear
    if np.linalg.norm(normal) < 1e-9:
        if np.dot(v1_unit, v2_unit) > 0.999: # Parallel, pointing same direction
            return VGroup()
        else: # Anti-parallel, pointing opposite directions
            # Create an arbitrary perpendicular vector to define the plane
            if abs(v1_unit[0]) < 0.9:
                perp_vector = np.array([1, 0, 0])
            else:
                perp_vector = np.array([0, 1, 0])
            normal = np.cross(v1_unit, perp_vector)

    normal_unit = normal / np.linalg.norm(normal)

    # Create an orthonormal basis in the plane of the angle
    u_axis = v1_unit
    v_axis = np.cross(normal_unit, u_axis)

    # Find the total angle between the vectors
    total_angle = np.arccos(np.clip(np.dot(v1_unit, v2_unit), -1.0, 1.0))

    # Generate points for the arc
    arc_points = [
        center + radius * (np.cos(t) * u_axis + np.sin(t) * v_axis)
        for t in np.linspace(0, total_angle, num_points)
    ]

    arc = VMobject(stroke_color=color, stroke_width=4).set_points_smoothly(arc_points)
    arc_group = VGroup(arc)

    # Add optional connection lines for clarity
    if show_connections and len(arc_points) >= 2:
        arc_start, arc_end = arc_points[0], arc_points[-1]

        if connection_style == "dashed":
            LineClass = DashedLine
            line_kwargs = {"color": connection_color, "stroke_width": 2, "stroke_opacity": connection_opacity}
        else: # "solid"
            LineClass = Line3D
            line_kwargs = {"color": connection_color, "thickness": 0.015, "stroke_opacity": connection_opacity}

        connection1 = LineClass(center, arc_start, **line_kwargs)
        connection2 = LineClass(center, arc_end, **line_kwargs)
        dot1 = Dot3D(point=arc_start, color=connection_color, radius=0.03)
        dot2 = Dot3D(point=arc_end, color=connection_color, radius=0.03)

        arc_group.add(connection1, connection2, dot1, dot2)

    return arc_group

def add_explanation_text(scene, text_content, font_size=36, color=WHITE, 
                        margin=0.2, line_spacing=0.4):
    """
    Adds explanation text to the right side of the screen, automatically managing
    overflow by removing the topmost text when space runs out.
    
    Args:
        scene: The Manim scene object
        text_content (str): The text to display
        font_size (int): Size of the font
        color: Color of the text
        margin (float): Margin from screen edges
        line_spacing (float): Vertical spacing between text elements
        animation_time (float): Duration of animations
    
    Usage:
        add_explanation_text(self, "First line of explanation")
        add_explanation_text(self, "Second line of explanation") 
        # Continue adding text - old text will automatically be removed when space runs out
    """
    
    # Define right side screen bounds
    RIGHT_BOUNDS = {
        'x_min': 0.5,
        'x_max': 6.5,
        'y_min': -3.5,
        'y_max': 3.5,
        'width': 6.0,
        'height': 7.0,
        'center_x': 3.5
    }
    
    # Initialize text tracking list if it doesn't exist
    if not hasattr(scene, 'right_side_texts'):
        scene.right_side_texts = []
    
    # Create the new text element
    if isinstance(text_content, str):
        text_obj = Text(text_content, font_size=font_size, color=color)
    else:
        # Support for MathTex objects
        text_obj = text_content
        if hasattr(text_obj, 'set_color'):
            text_obj.set_color(color)
    
    # Ensure text fits within width bounds
    max_width = RIGHT_BOUNDS['width'] - 2 * margin
    if text_obj.width > max_width:
        scale_factor = max_width / text_obj.width
        text_obj.scale(scale_factor)
    
    # Calculate position for the new text
    def calculate_text_position(text_element, position_index):
        """Calculate Y position for text at given index in the stack"""
        y_pos = RIGHT_BOUNDS['y_max'] - margin
        
        # Account for all previous texts
        for i in range(position_index):
            if i < len(scene.right_side_texts):
                prev_text = scene.right_side_texts[i]
                y_pos -= (prev_text.height + line_spacing)
        
        # Subtract half height of current text to center it
        y_pos -= text_element.height / 2
        return y_pos
    
    # Check if we need to remove texts to make space
    def will_text_fit(text_element, current_texts):
        """Check if adding this text will exceed bottom bounds"""
        test_y = calculate_text_position(text_element, len(current_texts))
        bottom_y = test_y - text_element.height / 2
        return bottom_y >= RIGHT_BOUNDS['y_min'] + margin
    
    # Remove top texts until the new text will fit
    removed_texts = []
    while scene.right_side_texts and not will_text_fit(text_obj, scene.right_side_texts):
        # Remove the topmost (oldest) text
        top_text = scene.right_side_texts.pop(0)
        removed_texts.append(top_text)
        scene.play(FadeOut(top_text), run_time=0.3)
    
    # Reposition all remaining texts to shift up
    if removed_texts:
        reposition_animations = []
        for i, remaining_text in enumerate(scene.right_side_texts):
            new_y_pos = calculate_text_position(remaining_text, i)
            reposition_animations.append(
                remaining_text.animate.move_to([RIGHT_BOUNDS['center_x'], new_y_pos, 0])
            )
        
        if reposition_animations:
            scene.play(*reposition_animations, run_time=0.4)
    
    # Position the new text at the bottom
    final_y_pos = calculate_text_position(text_obj, len(scene.right_side_texts))
    text_obj.move_to([RIGHT_BOUNDS['center_x'], final_y_pos, 0])
    
    # Animate the new text appearing
    scene.play(Write(text_obj), run_time=0.5)
    
    # Add to tracking list
    scene.right_side_texts.append(text_obj)


def clear_explanation_text(scene, animation_time=0.5):
    """
    Clears all explanation text from the right side of the screen.
    
    Args:
        scene: The Manim scene object
        animation_time (float): Duration of fade out animation
    """
    if hasattr(scene, 'right_side_texts') and scene.right_side_texts:
        # Fade out all texts simultaneously
        scene.play(*[FadeOut(text) for text in scene.right_side_texts], 
                  run_time=animation_time)
        scene.right_side_texts.clear()

def scrolling_subtitle(scene, text, total_duration, max_words_per_chunk=8, 
                      transition_time=0.3, gap_time=0.2, font_size=32, 
                      bottom_margin=1.0, max_width_ratio=0.9):
    """
    Creates movie-style scrolling subtitles with chunked text display
    
    Parameters:
    - scene: The Manim scene object (self)
    - text: The sentence text to display (from JSON sentence['text'])
    - total_duration: Total time for the entire sentence (in seconds)
    - max_words_per_chunk: Maximum words per subtitle chunk (default: 8)
    - transition_time: Fade in/out duration (default: 0.3s)
    - gap_time: Pause between chunks (default: 0.2s)
    - font_size: Text size (default: 32)
    - bottom_margin: Distance from bottom edge (default: 1.0 unit)
    - max_width_ratio: Maximum width as ratio of screen width (default: 0.9)
    
    Usage Example:
    scrolling_subtitle(self, "Let's start with part (a). We need to find the measure of angle XWY in triangle WXY.", 
                      total_duration=6.5)
    """
    
    # Split text into words
    words = text.split()
    total_words = len(words)
    
    if total_words == 0:
        return
    
    # Create chunks of max_words_per_chunk
    chunks = []
    for i in range(0, total_words, max_words_per_chunk):
        chunk = " ".join(words[i:i + max_words_per_chunk])
        chunks.append(chunk)
    
    num_chunks = len(chunks)
    
    if num_chunks == 1:
        # Single chunk - no transitions needed
        chunk_duration = total_duration
        gap_time = 0
        transition_time = 0
    else:
        # Calculate timing: total_duration = sum of chunk_durations + transition_times + gap_times
        # Available time for actual text display
        total_transition_time = (num_chunks * 2 * transition_time)  # Each chunk has fade in + fade out
        total_gap_time = (num_chunks - 1) * gap_time  # Gaps between chunks
        available_display_time = total_duration - total_transition_time - total_gap_time
        
        # Ensure we have positive time
        if available_display_time <= 0:
            available_display_time = total_duration * 0.8  # Use 80% of time if calculations go negative
            transition_time = total_duration * 0.1 / num_chunks  # Reduce transition time
            gap_time = total_duration * 0.1 / max(1, num_chunks - 1)  # Reduce gap time
    
    current_time = 0
    
    for i, chunk_text in enumerate(chunks):
        # Calculate chunk duration based on word count proportion
        if num_chunks == 1:
            chunk_display_time = chunk_duration
        else:
            chunk_words = len(chunk_text.split())
            chunk_display_time = (chunk_words / total_words) * available_display_time
        
        # Create subtitle text with movie styling
        subtitle = Text(
            chunk_text,
            font="Arial",
            font_size=font_size,
            color=WHITE,
            stroke_width=3,      # Black outline for readability
            stroke_color=BLACK
        )
        
        # Auto-adjust width if text is too wide
        max_width = config.frame_width * max_width_ratio
        if subtitle.width > max_width:
            subtitle.width = max_width
        
        # Create semi-transparent black background rectangle
        background_padding = 0.2
        background = Rectangle(
            width=subtitle.width + 2 * background_padding,
            height=subtitle.height + 2 * background_padding,
            fill_color=BLACK,
            fill_opacity=0.7,
            stroke_opacity=0
        )
        
        # Position subtitle at bottom center
        subtitle_position = np.array([0, -config.frame_height/2 + bottom_margin, 0])
        subtitle.move_to(subtitle_position)
        background.move_to(subtitle_position)
        
        # Group background and text
        subtitle_group = VGroup(background, subtitle)
        
        # Wait for chunk start time
        if i > 0:  # Add gap between chunks (except for first chunk)
            scene.wait(gap_time)
            current_time += gap_time
        
        # Fade in subtitle
        subtitle_group.set_opacity(0)
        scene.add(subtitle_group)
        scene.play(FadeIn(subtitle_group), run_time=transition_time)
        current_time += transition_time
        
        # Display subtitle for calculated duration
        scene.wait(chunk_display_time)
        current_time += chunk_display_time
        
        # Fade out subtitle
        scene.play(FadeOut(subtitle_group), run_time=transition_time)
        scene.remove(subtitle_group)
        current_time += transition_time




# def add_explanation_step(scene, step_number, description, font_size=36, 
#                         step_color="#FDE047", text_color=WHITE):
#     """
#     Adds a numbered step explanation to the right side of the screen.
    
#     Args:
#         scene: The Manim scene object
#         step_number (int): The step number
#         description (str): Description of the step
#         font_size (int): Size of the font
#         step_color: Color for the step number
#         text_color: Color for the description text
    
#     Usage:
#         add_explanation_step(self, 1, "Given information: angle WYX = 70°")
#         add_explanation_step(self, 2, "Using law of sines to find angle XWY")
#     """
    
#     # Create step text with number and description
#     step_text = f"Step {step_number}: {description}"
    
#     # Create as MathTex for better formatting
#     from manim import MathTex
#     formatted_text = MathTex(
#         f"\\text{{Step {step_number}: }}", f"\\text{{{description}}}",
#         font_size=font_size
#     )
#     formatted_text[0].set_color(step_color)  # Step number
#     formatted_text[1].set_color(text_color)  # Description
    
#     add_explanation_text(scene, formatted_text)


# def add_calculation_text(scene, calculation, result=None, font_size=32, 
#                         calc_color="#22C55E", result_color="#FDE047"):
#     """
#     Adds mathematical calculations to the right side of the screen.
    
#     Args:
#         scene: The Manim scene object
#         calculation (str): The calculation in LaTeX format
#         result (str, optional): The result in LaTeX format
#         font_size (int): Size of the font
#         calc_color: Color for the calculation
#         result_color: Color for the result
    
#     Usage:
#         add_calculation_text(self, "\\frac{\\sin(70°)}{6} = \\frac{\\sin(X)}{5}")
#         add_calculation_text(self, "X = \\sin^{-1}\\left(\\frac{5 \\sin(70°)}{6}\\right)", "X = 51.5°")
#     """
    
#     from manim import MathTex
    
#     if result:
#         # Show calculation and result
#         math_text = MathTex(calculation, "=", result, font_size=font_size)
#         math_text[0].set_color(calc_color)   # Calculation
#         math_text[1].set_color(WHITE)        # Equals sign
#         math_text[2].set_color(result_color) # Result
#     else:
#         # Show just calculation
#         math_text = MathTex(calculation, font_size=font_size)
#         math_text.set_color(calc_color)
    
#     add_explanation_text(scene, math_text)

