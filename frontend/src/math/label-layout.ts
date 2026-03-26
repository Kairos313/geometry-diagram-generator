/**
 * Label layout: offset computation and overlap detection.
 */

import type { Vec2 } from '../schema/render-types';
import { sub2, normalize2, add2, scale2 } from './geometry';

const LABEL_OFFSET_DIST = 18; // pixels
const LABEL_APPROX_W = 14;   // approximate label width per character
const LABEL_APPROX_H = 16;   // approximate label height

interface LabelBox {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * Compute offset label positions for all points, pushing away from centroid.
 */
export function computeLabelPositions(
  points: { id: string; pos: Vec2; label: string }[],
  centroid: Vec2,
  offsetDist: number = LABEL_OFFSET_DIST,
): Map<string, Vec2> {
  const positions = new Map<string, Vec2>();

  for (const pt of points) {
    const dir = sub2(pt.pos, centroid);
    const len = Math.sqrt(dir.x * dir.x + dir.y * dir.y);

    let labelPos: Vec2;
    if (len < 1e-9) {
      // Point at centroid — offset upward
      labelPos = { x: pt.pos.x, y: pt.pos.y - offsetDist };
    } else {
      const norm = normalize2(dir);
      labelPos = add2(pt.pos, scale2(norm, offsetDist));
    }

    positions.set(pt.id, labelPos);
  }

  // Nudge overlapping labels
  const boxes = Array.from(positions.entries()).map(([id, pos]) => {
    const pt = points.find(p => p.id === id)!;
    return {
      id,
      x: pos.x - (pt.label.length * LABEL_APPROX_W) / 2,
      y: pos.y - LABEL_APPROX_H / 2,
      w: pt.label.length * LABEL_APPROX_W,
      h: LABEL_APPROX_H,
    };
  });

  nudgeOverlaps(boxes);

  for (const box of boxes) {
    const pt = points.find(p => p.id === box.id)!;
    positions.set(box.id, {
      x: box.x + (pt.label.length * LABEL_APPROX_W) / 2,
      y: box.y + LABEL_APPROX_H / 2,
    });
  }

  return positions;
}

function boxesOverlap(a: LabelBox, b: LabelBox): boolean {
  return !(a.x + a.w < b.x || b.x + b.w < a.x ||
           a.y + a.h < b.y || b.y + b.h < a.y);
}

function nudgeOverlaps(boxes: LabelBox[]): void {
  const maxIterations = 20;
  const nudgeAmount = 8;

  for (let iter = 0; iter < maxIterations; iter++) {
    let anyOverlap = false;
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length; j++) {
        if (boxesOverlap(boxes[i], boxes[j])) {
          anyOverlap = true;
          // Compute overlap in both axes
          const overlapX = Math.min(boxes[i].x + boxes[i].w, boxes[j].x + boxes[j].w)
                         - Math.max(boxes[i].x, boxes[j].x);
          const overlapY = Math.min(boxes[i].y + boxes[i].h, boxes[j].y + boxes[j].h)
                         - Math.max(boxes[i].y, boxes[j].y);

          // Nudge along the axis with less overlap (easier to separate)
          if (overlapX < overlapY) {
            const dx = (boxes[i].x + boxes[i].w / 2) - (boxes[j].x + boxes[j].w / 2);
            const nudge = dx >= 0 ? nudgeAmount : -nudgeAmount;
            boxes[i].x += nudge;
            boxes[j].x -= nudge;
          } else {
            const dy = (boxes[i].y + boxes[i].h / 2) - (boxes[j].y + boxes[j].h / 2);
            const nudge = dy >= 0 ? nudgeAmount : -nudgeAmount;
            boxes[i].y += nudge;
            boxes[j].y -= nudge;
          }
        }
      }
    }
    if (!anyOverlap) break;
  }
}
