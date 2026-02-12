"""
2D geometry renderer using Matplotlib.

Produces static PNG or SVG images of geometric figures with points,
lines, circles, angle arcs, regions, and labels on a dark background.
"""

import math
from pathlib import Path
from typing import Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from .base import (
    AngleArc,
    CircleDef,
    GeometryData,
    GeometryRenderer,
    LineSegment,
    Point,
    Region,
    RenderConfig,
)


# Default color palette for elements without explicit colors
_LINE_COLORS = [
    "#00FF00", "#FF0000", "#0000FF", "#FF00FF",
    "#00FFFF", "#FFA500", "#ADFF2F", "#FF6347",
]
_ANGLE_COLORS = ["#FFFF00", "#00FFFF", "#FF00FF", "#FFA500"]


class Matplotlib2DRenderer(GeometryRenderer):
    """Renders 2D geometry diagrams using Matplotlib."""

    def render(self, geometry_data: GeometryData, output_path: Path) -> bool:
        try:
            fig, ax = self._create_figure()
            self._draw_regions(ax, geometry_data)
            self._draw_circles(ax, geometry_data)
            self._draw_lines(ax, geometry_data)
            self._draw_angles(ax, geometry_data)
            self._draw_points(ax, geometry_data)
            self._draw_labels(ax, geometry_data)

            if self.config.annotated and geometry_data.annotations:
                self._draw_annotations(fig, ax, geometry_data)

            self._auto_fit(ax, geometry_data)

            fmt = "svg" if self.config.output_format == "svg" else "png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(
                str(output_path),
                format=fmt,
                dpi=self.config.dpi,
                bbox_inches="tight",
                facecolor=fig.get_facecolor(),
                edgecolor="none",
            )
            plt.close(fig)
            return True
        except Exception as e:
            print(f"Matplotlib render error: {e}")
            plt.close("all")
            return False

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _create_figure(self):
        fig_w = self.config.width / self.config.dpi
        fig_h = self.config.height / self.config.dpi
        fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h), dpi=self.config.dpi)
        ax.set_facecolor(self.config.background_color)
        fig.patch.set_facecolor(self.config.background_color)
        ax.set_aspect("equal")
        ax.axis("off")
        return fig, ax

    # ------------------------------------------------------------------
    # Drawing primitives
    # ------------------------------------------------------------------

    def _draw_points(self, ax, data: GeometryData):
        for point in data.points.values():
            ax.plot(
                point.x, point.y, "o",
                color=point.color, markersize=6, zorder=5,
            )

    def _draw_labels(self, ax, data: GeometryData):
        for point in data.points.values():
            offset = self._label_offset(point, data)
            ax.annotate(
                point.name,
                xy=(point.x, point.y),
                xytext=offset,
                textcoords="offset points",
                fontsize=14,
                color="white",
                fontweight="bold",
                ha="center",
                va="center",
                zorder=6,
            )

    def _draw_lines(self, ax, data: GeometryData):
        for i, line in enumerate(data.lines):
            p1 = data.points.get(line.start_point)
            p2 = data.points.get(line.end_point)
            if p1 is None or p2 is None:
                continue
            color = line.color if line.color != "#FFFFFF" else _LINE_COLORS[i % len(_LINE_COLORS)]
            ls = {"solid": "-", "dashed": "--", "dotted": ":"}
            ax.plot(
                [p1.x, p2.x], [p1.y, p2.y],
                color=color,
                linewidth=line.stroke_width,
                linestyle=ls.get(line.style, "-"),
                zorder=3,
            )

    def _draw_circles(self, ax, data: GeometryData):
        for cdef in data.circles:
            center = data.points.get(cdef.center)
            if center is None:
                continue
            circ = plt.Circle(
                (center.x, center.y),
                cdef.radius,
                fill=cdef.fill_opacity > 0,
                facecolor=cdef.color if cdef.fill_opacity > 0 else "none",
                edgecolor=cdef.color,
                alpha=max(cdef.fill_opacity, 0.8),
                linewidth=cdef.stroke_width,
                zorder=2,
            )
            ax.add_patch(circ)

    def _draw_regions(self, ax, data: GeometryData):
        for region in data.regions:
            coords = [
                data.points[v].coords_2d
                for v in region.vertices
                if v in data.points
            ]
            if len(coords) < 3:
                continue
            polygon = plt.Polygon(
                coords,
                closed=True,
                facecolor=region.fill_color,
                edgecolor=region.stroke_color,
                alpha=region.fill_opacity,
                linewidth=region.stroke_width,
                zorder=1,
            )
            ax.add_patch(polygon)

    def _draw_angles(self, ax, data: GeometryData):
        for i, angle in enumerate(data.angles):
            vertex = data.points.get(angle.vertex)
            p1 = data.points.get(angle.point1)
            p2 = data.points.get(angle.point2)
            if vertex is None or p1 is None or p2 is None:
                continue

            color = _ANGLE_COLORS[i % len(_ANGLE_COLORS)]

            if angle.is_right_angle:
                self._draw_right_angle(ax, vertex, p1, p2, color)
            else:
                self._draw_arc(ax, vertex, p1, p2, angle.value_degrees, color)

            # Label
            label_text = angle.label or f"{angle.value_degrees:.0f}\u00b0"
            label_pos = self._angle_label_position(vertex, p1, p2, radius=0.8)
            ax.text(
                label_pos[0], label_pos[1], label_text,
                color=color, fontsize=10, ha="center", va="center",
                zorder=6,
            )

    # ------------------------------------------------------------------
    # Angle helpers
    # ------------------------------------------------------------------

    def _draw_arc(self, ax, vertex: Point, p1: Point, p2: Point,
                  degrees: float, color: str, radius: float = 0.5):
        """Draw an angle arc from arm1 (vertex->p1) to arm2 (vertex->p2)."""
        v1 = np.array([p1.x - vertex.x, p1.y - vertex.y])
        v2 = np.array([p2.x - vertex.x, p2.y - vertex.y])

        angle1 = math.degrees(math.atan2(v1[1], v1[0]))
        angle2 = math.degrees(math.atan2(v2[1], v2[0]))

        # Pick the smaller sweep
        sweep = (angle2 - angle1) % 360
        if sweep > 180:
            angle1, angle2 = angle2, angle1
            sweep = 360 - sweep

        arc = mpatches.Arc(
            (vertex.x, vertex.y),
            2 * radius, 2 * radius,
            angle=0,
            theta1=angle1,
            theta2=angle1 + sweep,
            color=color,
            linewidth=2,
            zorder=4,
        )
        ax.add_patch(arc)

    def _draw_right_angle(self, ax, vertex: Point, p1: Point, p2: Point,
                          color: str, size: float = 0.3):
        """Draw a small square for a right angle."""
        v1 = np.array([p1.x - vertex.x, p1.y - vertex.y])
        v2 = np.array([p2.x - vertex.x, p2.y - vertex.y])
        n1 = v1 / (np.linalg.norm(v1) + 1e-9) * size
        n2 = v2 / (np.linalg.norm(v2) + 1e-9) * size

        corner1 = np.array([vertex.x, vertex.y]) + n1
        corner2 = np.array([vertex.x, vertex.y]) + n1 + n2
        corner3 = np.array([vertex.x, vertex.y]) + n2

        xs = [corner1[0], corner2[0], corner3[0]]
        ys = [corner1[1], corner2[1], corner3[1]]
        ax.plot(xs, ys, color=color, linewidth=1.5, zorder=4)

    def _angle_label_position(
        self, vertex: Point, p1: Point, p2: Point, radius: float = 0.8
    ) -> Tuple[float, float]:
        """Compute label position at the bisector of the angle."""
        v1 = np.array([p1.x - vertex.x, p1.y - vertex.y])
        v2 = np.array([p2.x - vertex.x, p2.y - vertex.y])
        n1 = v1 / (np.linalg.norm(v1) + 1e-9)
        n2 = v2 / (np.linalg.norm(v2) + 1e-9)
        bisector = n1 + n2
        norm = np.linalg.norm(bisector)
        if norm < 1e-9:
            bisector = np.array([-n1[1], n1[0]])
            norm = np.linalg.norm(bisector)
        bisector = bisector / (norm + 1e-9) * radius
        return (vertex.x + bisector[0], vertex.y + bisector[1])

    # ------------------------------------------------------------------
    # Label offset heuristic
    # ------------------------------------------------------------------

    def _label_offset(self, point: Point, data: GeometryData) -> Tuple[float, float]:
        """Compute a label offset that avoids overlapping with nearby lines."""
        # Collect directions to neighboring points
        neighbors = []
        for line in data.lines:
            if line.start_point == point.name:
                other = data.points.get(line.end_point)
                if other:
                    neighbors.append(np.array([other.x - point.x, other.y - point.y]))
            elif line.end_point == point.name:
                other = data.points.get(line.start_point)
                if other:
                    neighbors.append(np.array([other.x - point.x, other.y - point.y]))

        if not neighbors:
            return (0, 12)

        # Average direction away from neighbors
        avg = sum(neighbors) / len(neighbors)
        norm = np.linalg.norm(avg)
        if norm < 1e-9:
            return (0, 12)
        away = -avg / norm * 14  # offset in points
        return (away[0], away[1])

    # ------------------------------------------------------------------
    # Auto-fit
    # ------------------------------------------------------------------

    def _auto_fit(self, ax, data: GeometryData):
        all_x = [p.x for p in data.points.values()]
        all_y = [p.y for p in data.points.values()]

        # Include circle extents
        for c in data.circles:
            center = data.points.get(c.center)
            if center:
                all_x.extend([center.x - c.radius, center.x + c.radius])
                all_y.extend([center.y - c.radius, center.y + c.radius])

        if not all_x or not all_y:
            return

        span_x = max(all_x) - min(all_x)
        span_y = max(all_y) - min(all_y)
        margin = max(span_x, span_y) * self.config.margin_factor
        margin = max(margin, 0.5)

        ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        ax.set_ylim(min(all_y) - margin, max(all_y) + margin)

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------

    def _draw_annotations(self, fig, ax, data: GeometryData):
        """Draw solution step annotations as text below/beside the figure."""
        texts = []
        for step in data.annotations:
            for sentence in step.get("sentences", []):
                kat = sentence.get("khan_academy_text", "")
                if kat:
                    texts.append(kat)
        if not texts:
            return

        annotation_text = "\n".join(texts[:6])  # limit to avoid overflow
        fig.text(
            0.5, 0.02, annotation_text,
            ha="center", va="bottom",
            fontsize=10, color="#CCCCCC",
            family="monospace",
            transform=fig.transFigure,
        )
