"""
Matplotlib helper functions for the Geometry Diagram Pipeline.

Provides battle-tested angle arc drawing for 2D matplotlib scenes.
Copied automatically to each run's output directory before execution.

Usage:
    from matplotlib_helpers import draw_angle_arc, draw_right_angle_marker
"""
import numpy as np
import matplotlib.patches as patches


def draw_angle_arc(ax, vertex, p1, p2, expected_degrees=None, radius=0.5,
                   color='#264653', linewidth=1.5, zorder=3, label=None,
                   label_color=None, label_fontsize=10, label_fontweight='normal'):
    """
    Draw an angle arc at *vertex* between rays vertex→p1 and vertex→p2.

    The function computes both possible sweep directions (clockwise and
    counter-clockwise) and picks the one closest to *expected_degrees*.
    If *expected_degrees* is ``None`` the smaller (interior) angle is drawn.

    Args:
        ax:               matplotlib Axes to draw on.
        vertex:           (x, y) or np.array — the vertex of the angle.
        p1:               (x, y) or np.array — endpoint on the first ray.
        p2:               (x, y) or np.array — endpoint on the second ray.
        expected_degrees: Optional expected angle value in degrees.  When
                          provided the sweep direction that best matches this
                          value is selected automatically.
        radius:           Radius of the arc (in data coordinates).
        color:            Arc colour (any matplotlib colour spec).
        linewidth:        Arc stroke width.
        zorder:           Drawing z-order.
        label:            Optional text label placed at the arc midpoint
                          (e.g. ``"75°"`` or ``"?"``).
        label_color:      Color for the label text (defaults to *color*).
        label_fontsize:   Font size for the label.
        label_fontweight: Font weight for the label (e.g. ``'bold'``).

    Returns:
        ``(label_x, label_y)`` — the position where the label was (or would
        be) placed.  Useful if you want to add your own annotation later.
    """
    vertex = np.asarray(vertex, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)

    v1 = p1 - vertex
    v2 = p2 - vertex

    # Degenerate guard
    if np.linalg.norm(v1) < 1e-9 or np.linalg.norm(v2) < 1e-9:
        return (vertex[0], vertex[1])

    # Ray angles in degrees (-180, 180]
    a1 = np.degrees(np.arctan2(v1[1], v1[0]))
    a2 = np.degrees(np.arctan2(v2[1], v2[0]))

    # Two possible CCW sweeps
    sweep_12 = (a2 - a1) % 360  # CCW from a1 to a2
    sweep_21 = (a1 - a2) % 360  # CCW from a2 to a1

    if expected_degrees is not None:
        # Pick the sweep whose angular measure is closest to expected
        if abs(sweep_12 - expected_degrees) <= abs(sweep_21 - expected_degrees):
            theta1, theta2 = a1, a1 + sweep_12
        else:
            theta1, theta2 = a2, a2 + sweep_21
    else:
        # Default: draw the smaller (interior) angle
        if sweep_12 <= 180:
            theta1, theta2 = a1, a1 + sweep_12
        else:
            theta1, theta2 = a2, a2 + sweep_21

    # Draw matplotlib Arc
    arc = patches.Arc(
        vertex, 2 * radius, 2 * radius,
        angle=0, theta1=theta1, theta2=theta2,
        color=color, linewidth=linewidth, zorder=zorder,
    )
    ax.add_patch(arc)

    # Label position at arc midpoint
    mid_angle_rad = np.radians((theta1 + theta2) / 2)
    label_x = vertex[0] + 1.3 * radius * np.cos(mid_angle_rad)
    label_y = vertex[1] + 1.3 * radius * np.sin(mid_angle_rad)

    if label is not None:
        ax.text(
            label_x, label_y, label,
            fontsize=label_fontsize,
            fontweight=label_fontweight,
            color=label_color or color,
            ha='center', va='center',
            zorder=zorder + 2,
        )

    return (label_x, label_y)


def draw_right_angle_marker(ax, vertex, p1, p2, size=0.3,
                            color='#264653', linewidth=1.5, zorder=3):
    """
    Draw a small square marker indicating a right angle at *vertex*.

    The square is aligned to the two rays vertex→p1 and vertex→p2.

    Args:
        ax:        matplotlib Axes.
        vertex:    (x, y) — the vertex.
        p1:        (x, y) — endpoint on the first ray.
        p2:        (x, y) — endpoint on the second ray.
        size:      Side length of the square marker (data coords).
        color:     Line colour.
        linewidth: Line width.
        zorder:    Drawing z-order.
    """
    vertex = np.asarray(vertex, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)

    v1 = p1 - vertex
    v2 = p2 - vertex

    if np.linalg.norm(v1) < 1e-9 or np.linalg.norm(v2) < 1e-9:
        return

    d1 = v1 / np.linalg.norm(v1) * size
    d2 = v2 / np.linalg.norm(v2) * size

    corner1 = vertex + d1
    corner2 = vertex + d1 + d2
    corner3 = vertex + d2

    xs = [corner1[0], corner2[0], corner3[0]]
    ys = [corner1[1], corner2[1], corner3[1]]

    ax.plot(xs, ys, color=color, linewidth=linewidth, zorder=zorder, solid_capstyle='round')
