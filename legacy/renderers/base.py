"""
Base classes and data structures for geometry rendering.

Defines the abstract GeometryRenderer interface and all data classes
used to represent parsed geometric elements. Any renderer (Matplotlib,
Manim, Blender, etc.) must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

import numpy as np


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Point:
    """A named point with 3D coordinates."""
    name: str
    x: float
    y: float
    z: float = 0.0
    color: str = "#FFFFFF"

    @property
    def coords(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    @property
    def coords_2d(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class LineSegment:
    """A line segment between two named points."""
    start_point: str
    end_point: str
    color: str = "#FFFFFF"
    stroke_width: float = 2.0
    style: str = "solid"  # "solid", "dashed", "dotted"
    label: Optional[str] = None
    length: Optional[float] = None


@dataclass
class AngleArc:
    """An angle arc at a vertex."""
    name: str
    vertex: str
    point1: str
    point2: str
    value_degrees: float
    color: str = "#FFFF00"
    label: Optional[str] = None
    is_right_angle: bool = False
    note: Optional[str] = None


@dataclass
class CircleDef:
    """A circle definition."""
    name: str
    center: str
    radius: float
    color: str = "#FFFFFF"
    fill_opacity: float = 0.0
    stroke_width: float = 2.0


@dataclass
class Region:
    """A polygon/region definition."""
    name: str
    vertices: List[str]
    region_type: str = "Polygon"
    fill_color: str = "#FFA500"
    fill_opacity: float = 0.2
    stroke_color: str = "#FFA500"
    stroke_width: float = 2.0


@dataclass
class GeometryData:
    """Complete parsed geometry data for rendering."""
    points: Dict[str, Point] = field(default_factory=dict)
    lines: List[LineSegment] = field(default_factory=list)
    angles: List[AngleArc] = field(default_factory=list)
    circles: List[CircleDef] = field(default_factory=list)
    regions: List[Region] = field(default_factory=list)
    dimension_type: str = "2d"
    title: Optional[str] = None
    annotations: List[dict] = field(default_factory=list)


@dataclass
class RenderConfig:
    """Configuration for rendering."""
    output_format: str = "png"
    width: int = 1920
    height: int = 1080
    background_color: str = "#0C0C0C"
    dpi: int = 150
    annotated: bool = False
    margin_factor: float = 0.15
    # 3D-specific
    rotation_duration: float = 8.0
    rotation_fps: int = 30
    pitch_angle: float = -40.0
    yaw_angle: float = -20.0


# ---------------------------------------------------------------------------
# Blueprint parser
# ---------------------------------------------------------------------------

class BlueprintParser:
    """Parses coordinates.txt markdown tables into GeometryData.

    The blueprint format uses markdown tables for points, lines, angles,
    and faces/solids. Multi-subpart problems have separate sections
    headed by '## Geometric Blueprint for Subpart (x)'.
    """

    @staticmethod
    def parse(coordinates_txt: str, solution_json: Optional[dict] = None) -> List[GeometryData]:
        """Parse a full blueprint into one GeometryData per subpart.

        Returns a list because a single blueprint may contain multiple
        subparts (a), (b), etc.
        """
        # Split into subparts
        subpart_pattern = r'##\s*\*?\*?Geometric Blueprint for Subpart \((\w+)\)\*?\*?'
        splits = re.split(subpart_pattern, coordinates_txt)

        subparts: List[GeometryData] = []

        if len(splits) <= 1:
            # No subpart headers — treat entire text as one subpart
            data = BlueprintParser._parse_subpart(coordinates_txt)
            if solution_json and "solution_steps" in solution_json:
                data.annotations = solution_json["solution_steps"]
            data.dimension_type = BlueprintParser._classify_dimension(data)
            subparts.append(data)
        else:
            # splits[0] is text before first header (usually the intro line)
            # Then alternating: label, content, label, content, ...
            for i in range(1, len(splits), 2):
                label = splits[i]
                content = splits[i + 1] if i + 1 < len(splits) else ""
                data = BlueprintParser._parse_subpart(content)
                data.title = f"Subpart ({label})"
                data.dimension_type = BlueprintParser._classify_dimension(data)
                subparts.append(data)

            # Attach solution annotations to subparts by matching step_ids
            if solution_json and "solution_steps" in solution_json:
                BlueprintParser._distribute_annotations(subparts, solution_json["solution_steps"])

        return subparts

    @staticmethod
    def _parse_subpart(text: str) -> GeometryData:
        """Parse a single subpart's blueprint text."""
        # Strip markdown bold markers so **A** becomes A
        text = re.sub(r'\*\*([^*]+?)\*\*', r'\1', text)
        data = GeometryData()
        data.points = BlueprintParser._parse_points(text)
        data.lines = BlueprintParser._parse_lines(text)
        data.angles = BlueprintParser._parse_angles(text)

        circles, regions = BlueprintParser._parse_faces(text)
        data.circles = circles
        data.regions = regions

        return data

    @staticmethod
    def _parse_points(text: str) -> Dict[str, Point]:
        """Parse the point coordinates table."""
        points = {}
        row_pattern = r'\|\s*([A-Za-z][A-Za-z0-9_]*)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|'
        for match in re.finditer(row_pattern, text):
            name = match.group(1).strip()
            # Skip table header words
            if name.lower() in ('point', 'name'):
                continue
            x, y, z = float(match.group(2)), float(match.group(3)), float(match.group(4))
            points[name] = Point(name=name, x=x, y=y, z=z)
        return points

    @staticmethod
    def _parse_lines(text: str) -> List[LineSegment]:
        """Parse the lines/edges table."""
        lines = []
        # Match: | Label | Start | End | Length |
        row_pattern = r'\|\s*([A-Za-z][^\|]*?)\s*\|\s*([A-Z][A-Za-z0-9_]*)\s*\|\s*([A-Z][A-Za-z0-9_]*)\s*\|\s*([-\d.]+)\s*\|'
        for match in re.finditer(row_pattern, text):
            label_raw = match.group(1).strip()
            start = match.group(2).strip()
            end = match.group(3).strip()
            length = float(match.group(4))

            # Skip header rows
            if start.lower() in ('start', 'start point'):
                continue

            # Extract label text (e.g., "OQ (Radius)" -> "Radius")
            label = None
            paren_match = re.search(r'\(([^)]+)\)', label_raw)
            if paren_match:
                label = paren_match.group(1)

            lines.append(LineSegment(
                start_point=start,
                end_point=end,
                label=label,
                length=length,
            ))
        return lines

    @staticmethod
    def _parse_angles(text: str) -> List[AngleArc]:
        """Parse the angles table.

        Supports two formats:
        - Old: | Angle | Vertex | Defining Points (comma-sep) | Value | Note |
        - New: | Element ID | Vertex | Point 1 | Point 2 | Value | Logic |
        """
        angles = []

        # First, isolate the angles section (between C. Angles and the next section)
        angles_section = ""
        angles_match = re.search(
            r'C\.\s*Angles.*?\s*(.*?)(?=\nD\.|\n---|\n##|\Z)',
            text, re.DOTALL
        )
        if not angles_match:
            return angles
        angles_section = angles_match.group(1)

        # Try new format first: | Name | Vertex | Point1 | Point2 | Value | ... |
        new_pattern = (
            r'\|\s*([A-Za-z][A-Za-z0-9_]*)\s*\|\s*([A-Z][A-Za-z0-9_]*)\s*\|'
            r'\s*([A-Z][A-Za-z0-9_]*)\s*\|\s*([A-Z][A-Za-z0-9_]*)\s*\|'
            r'\s*([-\d.]+)[°]?\s*\|\s*([^\|]*?)\s*\|'
        )
        for match in re.finditer(new_pattern, angles_section):
            name = match.group(1).strip()
            vertex = match.group(2).strip()
            point1 = match.group(3).strip()
            point2 = match.group(4).strip()
            value = float(match.group(5))
            note = match.group(6).strip() or None

            if name.lower() in ('angle', 'name', 'element'):
                continue

            is_right = abs(value - 90.0) < 0.01
            angles.append(AngleArc(
                name=name, vertex=vertex, point1=point1, point2=point2,
                value_degrees=value, is_right_angle=is_right, note=note,
            ))

        if angles:
            return angles

        # Fallback to old format: | Angle | Vertex | Defining Points (comma) | Value | Note |
        old_pattern = (
            r'\|\s*([A-Z][A-Za-z0-9_]*)\s*\|\s*([A-Z][A-Za-z0-9_]*)\s*\|'
            r'\s*([A-Z][^\|]*,[^\|]*?)\s*\|\s*([-\d.]+)\s*\|\s*([^\|]*?)\s*\|'
        )
        for match in re.finditer(old_pattern, angles_section):
            name = match.group(1).strip()
            vertex = match.group(2).strip()
            defining_raw = match.group(3).strip()
            value = float(match.group(4))
            note = match.group(5).strip() or None

            if name.lower() in ('angle', 'name'):
                continue

            def_points = [p.strip() for p in defining_raw.split(',')]
            point1 = def_points[0] if len(def_points) > 0 else ""
            point2 = def_points[-1] if len(def_points) > 1 else ""

            is_right = abs(value - 90.0) < 0.01
            angles.append(AngleArc(
                name=name, vertex=vertex, point1=point1, point2=point2,
                value_degrees=value, is_right_angle=is_right, note=note,
            ))
        return angles

    @staticmethod
    def _parse_faces(text: str) -> Tuple[List[CircleDef], List[Region]]:
        """Parse the faces/surfaces/solids table."""
        circles = []
        regions = []

        # Match: | Component | Type | Defining Elements | [optional area] |
        row_pattern = r'\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|'

        # Find the faces section
        faces_section = ""
        faces_match = re.search(
            r'D\.\s*Faces.*?\s*(.*?)(?=\n---|\n##|\Z)',
            text, re.DOTALL
        )
        if faces_match:
            faces_section = faces_match.group(1)

        for match in re.finditer(row_pattern, faces_section):
            component = match.group(1).strip()
            comp_type = match.group(2).strip()
            defining = match.group(3).strip()

            if component.lower() in ('component', ':---', '----'):
                continue

            if comp_type.lower() == 'circle':
                # Parse "Center O, Radius 2.5"
                center_match = re.search(r'Center\s+(\w+)', defining)
                radius_match = re.search(r'Radius\s+([\d.]+)', defining)
                if center_match and radius_match:
                    circles.append(CircleDef(
                        name=component,
                        center=center_match.group(1),
                        radius=float(radius_match.group(1)),
                    ))
            elif comp_type.lower() == 'polygon':
                # Parse "O, Q, P, R"
                verts = [v.strip() for v in defining.split(',')]
                regions.append(Region(
                    name=component,
                    vertices=verts,
                    region_type=comp_type,
                ))

        return circles, regions

    @staticmethod
    def _classify_dimension(data: GeometryData) -> str:
        """Classify as 2D or 3D based on Z coordinates."""
        for point in data.points.values():
            if abs(point.z) > 0.001:
                return "3d"
        return "2d"

    @staticmethod
    def _distribute_annotations(subparts: List[GeometryData], steps: List[dict]):
        """Distribute solution steps across subparts by step_id matching."""
        for step in steps:
            step_id = step.get("step_id", "").lower()
            assigned = False
            for i, subpart in enumerate(subparts):
                if subpart.title:
                    label = subpart.title.split("(")[-1].rstrip(")")
                    if f"part_{label}" in step_id or f"part_{label.lower()}" in step_id:
                        subpart.annotations.append(step)
                        assigned = True
                        break
            if not assigned:
                # Assign to all subparts (general steps like key_takeaways)
                for subpart in subparts:
                    subpart.annotations.append(step)


# ---------------------------------------------------------------------------
# Abstract renderer
# ---------------------------------------------------------------------------

class GeometryRenderer(ABC):
    """Abstract base class for geometry renderers.

    Implement parse_blueprint() and render() to create a new renderer.
    The interface is designed so the 3D renderer can be swapped
    (Manim -> Blender) without changing any other code.
    """

    def __init__(self, config: RenderConfig):
        self.config = config

    @abstractmethod
    def render(self, geometry_data: GeometryData, output_path: Path) -> bool:
        """Render the geometry to an output file.

        Args:
            geometry_data: Parsed geometry data.
            output_path: Path where output file should be written.

        Returns:
            True if rendering succeeded.
        """
        pass

    def render_all(
        self,
        coordinates_txt: str,
        solution_json: Optional[dict],
        output_dir: Path,
        base_name: str = "geometry",
    ) -> List[Path]:
        """Parse blueprint and render all subparts.

        Returns list of output file paths.
        """
        subparts = BlueprintParser.parse(coordinates_txt, solution_json)
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = []

        for i, data in enumerate(subparts):
            suffix = f"_{chr(97 + i)}" if len(subparts) > 1 else ""
            ext = self.config.output_format
            out_path = output_dir / f"{base_name}{suffix}.{ext}"
            if self.render(data, out_path):
                paths.append(out_path)

        return paths
