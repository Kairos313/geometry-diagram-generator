"""
Renderer package — factory for 2D / 3D geometry renderers.
"""

from __future__ import annotations

from typing import Optional

from .base import BlueprintParser, GeometryData, GeometryRenderer, RenderConfig
from .matplotlib_2d import Matplotlib2DRenderer
from .manim_3d import Manim3DRenderer


def get_renderer(dimension_type: str, config: Optional[RenderConfig] = None) -> GeometryRenderer:
    """Return the appropriate renderer for the given dimension type.

    Args:
        dimension_type: "2d" or "3d".
        config: Rendering configuration. Uses defaults if None.

    Returns:
        A GeometryRenderer instance.
    """
    cfg = config or RenderConfig()

    if dimension_type == "2d":
        return Matplotlib2DRenderer(cfg)
    elif dimension_type == "3d":
        return Manim3DRenderer(cfg)
    else:
        raise ValueError(f"Unknown dimension_type: {dimension_type!r}. Expected '2d' or '3d'.")


__all__ = [
    "get_renderer",
    "BlueprintParser",
    "GeometryData",
    "GeometryRenderer",
    "RenderConfig",
    "Matplotlib2DRenderer",
    "Manim3DRenderer",
]
