/**
 * D3.js 2D geometry renderer.
 * Takes a RenderScene2D and produces an SVG string.
 */

import type { RenderScene2D } from '../../schema/render-types';
import { GEOMETRY_STYLES } from './styles';
import { computeLabelPositions } from '../../math/label-layout';
import {
  drawSegment,
  drawCircle,
  drawArc,
  drawRightAngle,
  drawPoint,
  drawPolygon,
  drawAxes,
  drawGrid,
  drawCurve,
} from './primitives';

declare const d3: any;

/**
 * Render a 2D geometry scene to an SVG string.
 * Requires d3 to be available in the global scope.
 */
export function renderGeometry2D(scene: RenderScene2D): string {
  const { viewport, elements, centroid } = scene;

  const svg = d3.create('svg')
    .attr('xmlns', 'http://www.w3.org/2000/svg')
    .attr('viewBox', `0 0 ${viewport.width} ${viewport.height}`)
    .attr('width', viewport.width)
    .attr('height', viewport.height)
    .attr('class', 'geometry-diagram');

  // Inject styles
  svg.append('style').text(GEOMETRY_STYLES);

  // ── Layer 1: Grid (behind everything) ──
  if (elements.axes) {
    const gridLayer = svg.append('g').attr('class', 'layer-grid');
    drawGrid(gridLayer, elements.axes);
  }

  // ── Layer 2: Polygon fills ──
  const fillLayer = svg.append('g').attr('class', 'layer-fills');
  for (const poly of elements.polygons) {
    drawPolygon(fillLayer, poly.vertices, poly.fill);
  }

  // ── Layer 3: Circles ──
  const circleLayer = svg.append('g').attr('class', 'layer-circles');
  for (const c of elements.circles) {
    drawCircle(circleLayer, c.center, c.radius);
  }

  // ── Layer 4: Axes ──
  if (elements.axes) {
    const axesLayer = svg.append('g').attr('class', 'layer-axes');
    drawAxes(axesLayer, elements.axes);
  }

  // ── Layer 5: Curves ──
  const curveLayer = svg.append('g').attr('class', 'layer-curves');
  for (const curve of elements.curves) {
    drawCurve(curveLayer, curve.points);
  }

  // ── Layer 6: Dashed construction lines ──
  const constructionLayer = svg.append('g').attr('class', 'layer-construction');
  for (const seg of elements.segments.filter(s => s.style === 'dashed')) {
    drawSegment(constructionLayer, seg.from, seg.to, {
      style: 'dashed',
      label: seg.label,
      highlight: seg.highlight,
    });
  }

  // ── Layer 7: Solid edges ──
  const edgeLayer = svg.append('g').attr('class', 'layer-edges');
  for (const seg of elements.segments.filter(s => s.style === 'solid')) {
    drawSegment(edgeLayer, seg.from, seg.to, {
      style: 'solid',
      label: seg.label,
      highlight: seg.highlight,
    });
  }

  // ── Layer 8: Angle arcs ──
  const arcLayer = svg.append('g').attr('class', 'layer-arcs');
  for (const arc of elements.arcs) {
    drawArc(
      arcLayer,
      arc.center,
      arc.radius,
      arc.startAngle,
      arc.endAngle,
      arc.label,
      arc.highlight,
    );
  }

  // ── Layer 9: Right-angle markers ──
  for (const ra of elements.rightAngles) {
    drawRightAngle(arcLayer, ra.vertex, ra.p1, ra.p2, ra.size);
  }

  // ── Layer 10: Points and labels (topmost) ──
  const pointLayer = svg.append('g').attr('class', 'layer-points');

  // Compute label positions (pushed away from centroid, de-overlapped)
  const labelPositions = computeLabelPositions(
    elements.points.map(p => ({ id: p.id, pos: p.pos, label: p.label })),
    centroid,
  );

  for (const pt of elements.points) {
    const labelPos = labelPositions.get(pt.id) ?? pt.pos;
    drawPoint(pointLayer, pt.pos, pt.label, labelPos, pt.style);
  }

  // ── Layer 11: Annotations ──
  const annotationLayer = svg.append('g').attr('class', 'layer-annotations');
  for (const ann of elements.annotations) {
    annotationLayer.append('text')
      .attr('x', ann.pos.x)
      .attr('y', ann.pos.y)
      .attr('class', 'annotation')
      .text(ann.text);
  }

  return svg.node().outerHTML;
}
