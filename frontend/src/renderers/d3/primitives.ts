/**
 * D3 drawing primitives for 2D geometry.
 * Each function takes a D3 selection (SVG <g>) and geometry data.
 */

import type { Vec2 } from '../../schema/render-types';
import { svgArcPath, rightAngleCorners, midpoint2, sub2, normalize2 } from '../../math/geometry';

// We use d3 from the global scope (loaded via CDN)
declare const d3: any;

type Selection = any; // d3.Selection

// ── Segments ──

export function drawSegment(
  g: Selection,
  from: Vec2,
  to: Vec2,
  opts: {
    style: 'solid' | 'dashed';
    label?: string;
    highlight?: boolean;
  },
): void {
  let cls = opts.style === 'dashed' ? 'edge-dashed' : 'edge-solid';
  if (opts.highlight) cls = 'edge-highlight';

  g.append('line')
    .attr('x1', from.x)
    .attr('y1', from.y)
    .attr('x2', to.x)
    .attr('y2', to.y)
    .attr('class', cls);

  // Midpoint label
  if (opts.label) {
    const mid = midpoint2(from, to);
    // Offset label perpendicular to the segment
    const dir = sub2(to, from);
    const perp = normalize2({ x: -dir.y, y: dir.x });
    const offsetDist = 14;

    g.append('text')
      .attr('x', mid.x + perp.x * offsetDist)
      .attr('y', mid.y + perp.y * offsetDist)
      .attr('class', opts.highlight ? 'edge-label-highlight' : 'edge-label')
      .text(opts.label);
  }
}

// ── Circles ──

export function drawCircle(
  g: Selection,
  center: Vec2,
  radius: number,
): void {
  g.append('circle')
    .attr('cx', center.x)
    .attr('cy', center.y)
    .attr('r', radius)
    .attr('class', 'circle-primary');
}

// ── Arcs (angle markers) ──

export function drawArc(
  g: Selection,
  center: Vec2,
  radius: number,
  startAngle: number,
  endAngle: number,
  label?: string,
  highlight?: boolean,
): void {
  const path = svgArcPath(center.x, center.y, radius, startAngle, endAngle);

  g.append('path')
    .attr('d', path)
    .attr('class', highlight ? 'angle-arc-highlight' : 'angle-arc');

  if (label) {
    // Place label at midpoint of arc, slightly further out
    const midAngleRad = ((startAngle + endAngle) / 2) * (Math.PI / 180);
    const labelR = radius * 1.6;
    const lx = center.x + labelR * Math.cos(midAngleRad);
    const ly = center.y - labelR * Math.sin(midAngleRad); // SVG Y flip

    g.append('text')
      .attr('x', lx)
      .attr('y', ly)
      .attr('class', highlight ? 'angle-label-highlight' : 'angle-label')
      .text(label);
  }
}

// ── Right-angle markers ──

export function drawRightAngle(
  g: Selection,
  vertex: Vec2,
  p1: Vec2,
  p2: Vec2,
  size: number = 12,
): void {
  const [c1, c2, c3] = rightAngleCorners(vertex, p1, p2, size);
  g.append('polyline')
    .attr('points', `${c1.x},${c1.y} ${c2.x},${c2.y} ${c3.x},${c3.y}`)
    .attr('class', 'right-angle');
}

// ── Points ──

export function drawPoint(
  g: Selection,
  pos: Vec2,
  label: string,
  labelPos: Vec2,
  style: 'vertex' | 'center' | 'highlight',
): void {
  const r = style === 'highlight' ? 5 : 4;
  const cls = style === 'highlight' ? 'vertex-highlight' : 'vertex';

  g.append('circle')
    .attr('cx', pos.x)
    .attr('cy', pos.y)
    .attr('r', r)
    .attr('class', cls);

  g.append('text')
    .attr('x', labelPos.x)
    .attr('y', labelPos.y)
    .attr('class', style === 'highlight' ? 'label-highlight' : 'label')
    .text(label);
}

// ── Polygons ──

export function drawPolygon(
  g: Selection,
  vertices: Vec2[],
  fill: string,
): void {
  const pointsStr = vertices.map(v => `${v.x},${v.y}`).join(' ');
  g.append('polygon')
    .attr('points', pointsStr)
    .attr('class', 'face-fill')
    .attr('fill', fill);
}

// ── Coordinate axes ──

export function drawAxes(
  g: Selection,
  axes: {
    xRange: [number, number];
    yRange: [number, number];
    origin: Vec2;
    ticks: { pos: Vec2; label: string }[];
  },
): void {
  const { xRange, yRange, origin, ticks } = axes;
  const arrowSize = 6;

  // X axis
  g.append('line')
    .attr('x1', xRange[0])
    .attr('y1', origin.y)
    .attr('x2', xRange[1])
    .attr('y2', origin.y)
    .attr('class', 'axis-line');

  // X arrow
  g.append('polygon')
    .attr('points', [
      `${xRange[1]},${origin.y}`,
      `${xRange[1] - arrowSize * 2},${origin.y - arrowSize}`,
      `${xRange[1] - arrowSize * 2},${origin.y + arrowSize}`,
    ].join(' '))
    .attr('class', 'axis-arrow');

  // X label
  g.append('text')
    .attr('x', xRange[1] - 2)
    .attr('y', origin.y + 18)
    .attr('class', 'axis-label')
    .attr('text-anchor', 'end')
    .text('x');

  // Y axis
  g.append('line')
    .attr('x1', origin.x)
    .attr('y1', yRange[0])
    .attr('x2', origin.x)
    .attr('y2', yRange[1])
    .attr('class', 'axis-line');

  // Y arrow (points up = smaller Y in SVG)
  g.append('polygon')
    .attr('points', [
      `${origin.x},${yRange[0]}`,
      `${origin.x - arrowSize},${yRange[0] + arrowSize * 2}`,
      `${origin.x + arrowSize},${yRange[0] + arrowSize * 2}`,
    ].join(' '))
    .attr('class', 'axis-arrow');

  // Y label
  g.append('text')
    .attr('x', origin.x - 14)
    .attr('y', yRange[0] + 4)
    .attr('class', 'axis-label')
    .text('y');

  // Tick marks and labels
  for (const tick of ticks) {
    const isXTick = Math.abs(tick.pos.y - origin.y) < 1;

    if (isXTick) {
      // X-axis tick
      g.append('line')
        .attr('x1', tick.pos.x)
        .attr('y1', origin.y - 3)
        .attr('x2', tick.pos.x)
        .attr('y2', origin.y + 3)
        .attr('class', 'axis-line');
      g.append('text')
        .attr('x', tick.pos.x)
        .attr('y', origin.y + 14)
        .attr('class', 'tick-label')
        .text(tick.label);
    } else {
      // Y-axis tick
      g.append('line')
        .attr('x1', origin.x - 3)
        .attr('y1', tick.pos.y)
        .attr('x2', origin.x + 3)
        .attr('y2', tick.pos.y)
        .attr('class', 'axis-line');
      g.append('text')
        .attr('x', origin.x - 10)
        .attr('y', tick.pos.y)
        .attr('class', 'tick-label')
        .attr('text-anchor', 'end')
        .text(tick.label);
    }
  }

  // Origin label
  g.append('text')
    .attr('x', origin.x - 10)
    .attr('y', origin.y + 14)
    .attr('class', 'tick-label')
    .attr('text-anchor', 'end')
    .text('O');
}

// ── Grid ──

export function drawGrid(
  g: Selection,
  axes: {
    xRange: [number, number];
    yRange: [number, number];
    ticks: { pos: Vec2; label: string }[];
    origin: Vec2;
  },
): void {
  const { xRange, yRange, ticks, origin } = axes;

  for (const tick of ticks) {
    const isXTick = Math.abs(tick.pos.y - origin.y) < 1;

    if (isXTick) {
      g.append('line')
        .attr('x1', tick.pos.x)
        .attr('y1', yRange[0])
        .attr('x2', tick.pos.x)
        .attr('y2', yRange[1])
        .attr('class', 'grid-line');
    } else {
      g.append('line')
        .attr('x1', xRange[0])
        .attr('y1', tick.pos.y)
        .attr('x2', xRange[1])
        .attr('y2', tick.pos.y)
        .attr('class', 'grid-line');
    }
  }
}

// ── Curves ──

export function drawCurve(
  g: Selection,
  points: Vec2[],
): void {
  if (points.length < 2) return;

  const line = d3.line()
    .x((d: Vec2) => d.x)
    .y((d: Vec2) => d.y)
    .curve(d3.curveCatmullRom.alpha(0.5));

  g.append('path')
    .datum(points)
    .attr('d', line)
    .attr('class', 'curve');
}
