"""
Manim helper functions for the Geometry Diagram Pipeline.

Provides battle-tested angle arc drawing for 2D and 3D scenes,
smart label offset computation, 3D coordinate axes rendering,
and sphere wireframe creation. Copied automatically to each run's
output directory before execution.

Usage:
    from manim_helpers import (
        create_3d_angle_arc_with_connections,
        create_2d_angle_arc_geometric,
        compute_label_offsets,
        create_3d_coordinate_axes,
        create_sphere_wireframe,
    )
"""
from manim import *
import numpy as np


def compute_label_offsets(pts, offset_distance=0.35):
    # type: (dict, float) -> dict
    """Compute outward-facing label offsets for every point so labels don't overlap.

    Each label is pushed away from the figure centroid along the direction
    from centroid to that point.  Points very close to the centroid get an
    upward offset instead.

    Args:
        pts:             Dict mapping label names to 3-D numpy arrays
                         (already scaled / centered).
        offset_distance: Distance to push each label from its point.

    Returns:
        Dict mapping label names to 3-D offset vectors (np.ndarray).
    """
    coords = np.array(list(pts.values()))
    centroid = np.mean(coords, axis=0)

    offsets = {}
    for name, coord in pts.items():
        direction = coord - centroid
        norm = np.linalg.norm(direction)
        if norm > 1e-6:
            offsets[name] = (direction / norm) * offset_distance
        else:
            # Point is at the centroid — push upward
            offsets[name] = np.array([0.0, 0.0, offset_distance])
    return offsets


def create_2d_angle_arc_geometric(center, point1, point2, radius=0.5,
                                   num_points=30, use_smaller_angle=True,
                                   show_connections=False, connection_color=WHITE,
                                   connection_opacity=0.8, connection_style="dashed",
                                   color=YELLOW):
    # type: (...) -> VGroup
    """
    Creates a 2D angle arc using geometric vector math (avoids Manim's quadrant bugs).

    Args:
        center: The vertex of the angle (3D numpy array, z=0).
        point1, point2: Points on the two rays (3D numpy arrays).
        radius: Radius of the arc.
        num_points: Smoothness of the arc curve.
        use_smaller_angle: True for interior angle, False for reflex angle.
        show_connections: If True, adds dashed lines from arc endpoints to vertex.
        connection_color: Color of optional connection lines.
        connection_opacity: Opacity of optional connection lines.
        connection_style: "dashed" or "solid".
        color: Color of the arc itself.

    Returns:
        VGroup containing the arc (and optional connection lines/dots).
    """
    center = np.array(center, dtype=float)
    v1 = np.array(point1, dtype=float) - center
    v2 = np.array(point2, dtype=float) - center

    if np.linalg.norm(v1) < 1e-9 or np.linalg.norm(v2) < 1e-9:
        return VGroup()

    v1_unit = v1 / np.linalg.norm(v1)
    v2_unit = v2 / np.linalg.norm(v2)

    cross_product_z = v1_unit[0] * v2_unit[1] - v1_unit[1] * v2_unit[0]

    if abs(cross_product_z) < 1e-9:
        dot_product = np.dot(v1_unit[:2], v2_unit[:2])
        if dot_product > 0.999:
            return VGroup()
        else:
            if use_smaller_angle:
                return VGroup()

    u_axis = v1_unit[:2]

    if cross_product_z >= 0:
        v_axis = np.array([-u_axis[1], u_axis[0]])
    else:
        v_axis = np.array([u_axis[1], -u_axis[0]])

    dot_product = np.dot(v1_unit[:2], v2_unit[:2])
    angle_between = np.arccos(np.clip(dot_product, -1.0, 1.0))

    if use_smaller_angle:
        arc_angle = angle_between
    else:
        arc_angle = 2 * np.pi - angle_between

    arc_points_2d = []
    for t in np.linspace(0, arc_angle, num_points):
        point_2d = center[:2] + radius * (np.cos(t) * u_axis + np.sin(t) * v_axis)
        point_3d = np.array([point_2d[0], point_2d[1], 0])
        arc_points_2d.append(point_3d)

    if len(arc_points_2d) < 2:
        return VGroup()

    arc = VMobject(stroke_color=color, stroke_width=4).set_points_smoothly(arc_points_2d)
    arc_group = VGroup(arc)

    if show_connections and len(arc_points_2d) >= 2:
        arc_start, arc_end = arc_points_2d[0], arc_points_2d[-1]
        center_3d = np.array([center[0], center[1], 0])

        if connection_style == "dashed":
            connection1 = DashedLine(center_3d, arc_start, color=connection_color,
                                   stroke_width=2, stroke_opacity=connection_opacity)
            connection2 = DashedLine(center_3d, arc_end, color=connection_color,
                                   stroke_width=2, stroke_opacity=connection_opacity)
        else:
            connection1 = Line(center_3d, arc_start, color=connection_color,
                             stroke_width=2, stroke_opacity=connection_opacity)
            connection2 = Line(center_3d, arc_end, color=connection_color,
                             stroke_width=2, stroke_opacity=connection_opacity)

        dot1 = Dot(point=arc_start, color=connection_color, radius=0.03)
        dot2 = Dot(point=arc_end, color=connection_color, radius=0.03)
        arc_group.add(connection1, connection2, dot1, dot2)

    return arc_group


def create_3d_angle_arc_with_connections(center, point1, point2, radius=0.5,
                                           num_points=30, show_connections=True,
                                           connection_color=WHITE, connection_opacity=0.8,
                                           connection_style="dashed", color=YELLOW):
    # type: (...) -> VGroup
    """
    Creates a smooth 3D arc representing an angle between three points in space.

    Args:
        center: The vertex of the angle (3D numpy array).
        point1, point2: Points on the two rays (3D numpy arrays).
        radius: Radius of the arc.
        num_points: Smoothness of the arc curve.
        show_connections: If True, adds lines and dots from arc endpoints to vertex.
        connection_color: Color of connection lines and dots.
        connection_opacity: Opacity of connection lines.
        connection_style: "dashed" or "solid".
        color: Color of the arc itself.

    Returns:
        VGroup containing the arc (and optional connection lines/dots).
    """
    center = np.array(center, dtype=float)
    v1 = np.array(point1, dtype=float) - center
    v2 = np.array(point2, dtype=float) - center

    if np.linalg.norm(v1) < 1e-9 or np.linalg.norm(v2) < 1e-9:
        return VGroup()

    v1_unit = v1 / np.linalg.norm(v1)
    v2_unit = v2 / np.linalg.norm(v2)

    normal = np.cross(v1_unit, v2_unit)

    if np.linalg.norm(normal) < 1e-9:
        if np.dot(v1_unit, v2_unit) > 0.999:
            return VGroup()
        else:
            if abs(v1_unit[0]) < 0.9:
                perp_vector = np.array([1, 0, 0])
            else:
                perp_vector = np.array([0, 1, 0])
            normal = np.cross(v1_unit, perp_vector)

    normal_unit = normal / np.linalg.norm(normal)

    u_axis = v1_unit
    v_axis = np.cross(normal_unit, u_axis)

    total_angle = np.arccos(np.clip(np.dot(v1_unit, v2_unit), -1.0, 1.0))

    arc_points = [
        center + radius * (np.cos(t) * u_axis + np.sin(t) * v_axis)
        for t in np.linspace(0, total_angle, num_points)
    ]

    arc = VMobject(stroke_color=color, stroke_width=4).set_points_smoothly(arc_points)
    arc_group = VGroup(arc)

    if show_connections and len(arc_points) >= 2:
        arc_start, arc_end = arc_points[0], arc_points[-1]

        if connection_style == "dashed":
            LineClass = DashedLine
            line_kwargs = {"color": connection_color, "stroke_width": 2, "stroke_opacity": connection_opacity}
        else:
            LineClass = Line3D
            line_kwargs = {"color": connection_color, "thickness": 0.015, "stroke_opacity": connection_opacity}

        connection1 = LineClass(center, arc_start, **line_kwargs)
        connection2 = LineClass(center, arc_end, **line_kwargs)
        dot1 = Dot3D(point=arc_start, color=connection_color, radius=0.03)
        dot2 = Dot3D(point=arc_end, color=connection_color, radius=0.03)
        arc_group.add(connection1, connection2, dot1, dot2)

    return arc_group


def create_3d_coordinate_axes(x_range, y_range, z_range,
                              color_x="#C44536", color_y="#6A994E", color_z="#457B9D",
                              label_color="#1A1A1A", thickness=0.025, label_scale=0.6,
                              label_offset=0.5):
    # type: (...) -> tuple
    """Create 3D coordinate axes (X, Y, Z) with color-coded arrows and labels.

    Returns a VGroup containing the three axes, plus a list of three Text labels
    that must be added separately using `add_fixed_orientation_mobjects()`.

    Args:
        x_range:        (x_min, x_max) tuple for X-axis range.
        y_range:        (y_min, y_max) tuple for Y-axis range.
        z_range:        (z_min, z_max) tuple for Z-axis range.
        color_x:        Color for X-axis (default: red accent).
        color_y:        Color for Y-axis (default: green accent).
        color_z:        Color for Z-axis (default: blue accent).
        label_color:    Color for axis labels "X", "Y", "Z".
        thickness:      Arrow thickness.
        label_scale:    Scale factor for label Text objects.
        label_offset:   Distance from axis end to label position.

    Returns:
        (axes_group, labels_list):
            axes_group: VGroup containing 3 Arrow3D objects (add with self.add).
            labels_list: List of 3 Text objects (add with self.add_fixed_orientation_mobjects).

    Example:
        axes, labels = create_3d_coordinate_axes((-2, 6), (-2, 5), (-1, 8))
        self.add(axes)
        self.add_fixed_orientation_mobjects(*labels)
    """
    x_min, x_max = x_range
    y_min, y_max = y_range
    z_min, z_max = z_range

    axes_group = VGroup()

    # X-axis (red accent)
    x_axis = Arrow3D(
        start=np.array([x_min, 0.0, 0.0]),
        end=np.array([x_max, 0.0, 0.0]),
        color=color_x,
        thickness=thickness
    )
    x_label = Text("X", color=label_color).scale(label_scale)
    x_label.rotate(PI/2, axis=RIGHT)
    x_label.move_to(np.array([x_max + label_offset, 0, 0]))
    axes_group.add(x_axis)

    # Y-axis (green accent)
    y_axis = Arrow3D(
        start=np.array([0.0, y_min, 0.0]),
        end=np.array([0.0, y_max, 0.0]),
        color=color_y,
        thickness=thickness
    )
    y_label = Text("Y", color=label_color).scale(label_scale)
    y_label.rotate(PI/2, axis=RIGHT)
    y_label.move_to(np.array([0, y_max + label_offset, 0]))
    axes_group.add(y_axis)

    # Z-axis (blue accent)
    z_axis = Arrow3D(
        start=np.array([0.0, 0.0, z_min]),
        end=np.array([0.0, 0.0, z_max]),
        color=color_z,
        thickness=thickness
    )
    z_label = Text("Z", color=label_color).scale(label_scale)
    z_label.rotate(PI/2, axis=RIGHT)
    z_label.move_to(np.array([0, 0, z_max + label_offset]))
    axes_group.add(z_axis)

    return axes_group, [x_label, y_label, z_label]


def create_sphere_wireframe(center, radius, num_circles=3,
                            color="#457B9D", stroke_opacity=0.5):
    # type: (...) -> VGroup
    """Create a wireframe sphere using orthogonal circles.

    The sphere is represented by 3 circles in the XY, XZ, and YZ planes,
    all centered at the given point and rotated appropriately.

    Args:
        center:          3D numpy array or [x, y, z] — sphere center.
        radius:          Sphere radius (in scene units).
        num_circles:     Number of circles (always 3 for XY, XZ, YZ planes).
        color:           Circle stroke color.
        stroke_opacity:  Circle stroke opacity.

    Returns:
        VGroup containing the 3 circles forming the wireframe.

    Example:
        wireframe = create_sphere_wireframe(pts["C"], radius=5.0)
        self.add(wireframe)
    """
    center = np.array(center, dtype=float)
    wireframe = VGroup()

    # XY plane circle (horizontal)
    xy_circle = Circle(radius=radius, color=color, stroke_opacity=stroke_opacity)
    xy_circle.move_to(center)
    wireframe.add(xy_circle)

    # XZ plane circle (rotated around X-axis)
    xz_circle = Circle(radius=radius, color=color, stroke_opacity=stroke_opacity)
    xz_circle.rotate(PI/2, axis=RIGHT)
    xz_circle.move_to(center)
    wireframe.add(xz_circle)

    # YZ plane circle (rotated around Y-axis)
    yz_circle = Circle(radius=radius, color=color, stroke_opacity=stroke_opacity)
    yz_circle.rotate(PI/2, axis=UP)
    yz_circle.move_to(center)
    wireframe.add(yz_circle)

    return wireframe


def create_sphere_surface(center, radius, color="#457B9D", fill_opacity=0.6,
                          resolution=(20, 20)):
    # type: (...) -> Sphere
    """Create a full 3D sphere surface with shading.

    The sphere is rendered as a proper 3D surface with OpenGL shading,
    creating a realistic glossy appearance.

    Args:
        center:          3D numpy array or [x, y, z] — sphere center.
        radius:          Sphere radius (in scene units).
        color:           Sphere surface color.
        fill_opacity:    Surface opacity (0.0-1.0).
        resolution:      (u_resolution, v_resolution) for sphere tessellation.

    Returns:
        Sphere object with surface shading.

    Example:
        sphere = create_sphere_surface(pts["C"], radius=5.0, color=BLUE, fill_opacity=0.7)
        self.add(sphere)
    """
    center = np.array(center, dtype=float)
    sphere = Sphere(
        radius=radius,
        resolution=resolution,
        color=color,
        fill_opacity=fill_opacity
    )
    sphere.move_to(center)
    return sphere
