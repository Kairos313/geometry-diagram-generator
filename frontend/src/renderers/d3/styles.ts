/**
 * CSS styles for 2D SVG geometry diagrams.
 * Supports light and dark mode via CSS variables.
 */

export const GEOMETRY_STYLES = `
  :root {
    --geo-primary: #5b4dc7;
    --geo-primary-fill: rgba(91, 77, 199, 0.08);
    --geo-highlight: #d85a30;
    --geo-highlight-fill: rgba(216, 90, 48, 0.12);
    --geo-construction: #888780;
    --geo-angle: #ba7517;
    --geo-green: #0f6e56;
    --geo-text: #2c2c2a;
    --geo-annotation: #5f5e5a;
    --geo-axis: #3a3a38;
    --geo-grid: #e0dfdb;
    --geo-bg: #ffffff;
  }

  @media (prefers-color-scheme: dark) {
    :root {
      --geo-primary: #b8a9ff;
      --geo-primary-fill: rgba(184, 169, 255, 0.1);
      --geo-highlight: #ff6b4a;
      --geo-highlight-fill: rgba(255, 107, 74, 0.15);
      --geo-construction: #b4b2a9;
      --geo-angle: #ef9f27;
      --geo-green: #4ae0b0;
      --geo-text: #e8e6df;
      --geo-annotation: #b4b2a9;
      --geo-axis: #c8c6bf;
      --geo-grid: #3a3a38;
      --geo-bg: #1a1a1e;
    }
  }

  svg.geometry-diagram {
    background: var(--geo-bg);
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
  }

  .edge-solid {
    stroke: var(--geo-primary);
    stroke-width: 1.8;
    stroke-linecap: round;
    fill: none;
  }

  .edge-dashed {
    stroke: var(--geo-construction);
    stroke-width: 1.2;
    stroke-dasharray: 6 4;
    stroke-linecap: round;
    fill: none;
  }

  .edge-highlight {
    stroke: var(--geo-highlight);
    stroke-width: 2.2;
    stroke-linecap: round;
    fill: none;
  }

  .circle-primary {
    stroke: var(--geo-primary);
    stroke-width: 1.4;
    fill: none;
  }

  .face-fill {
    stroke: none;
  }

  .vertex {
    fill: var(--geo-primary);
    stroke: #fff;
    stroke-width: 1;
  }

  .vertex-highlight {
    fill: var(--geo-highlight);
    stroke: #fff;
    stroke-width: 1.5;
  }

  .label {
    font-size: 14px;
    font-weight: 500;
    fill: var(--geo-text);
    text-anchor: middle;
    dominant-baseline: central;
    pointer-events: none;
  }

  .label-highlight {
    font-size: 14px;
    font-weight: 700;
    fill: var(--geo-highlight);
    text-anchor: middle;
    dominant-baseline: central;
    pointer-events: none;
  }

  .edge-label {
    font-size: 12px;
    font-weight: 400;
    fill: var(--geo-text);
    text-anchor: middle;
    dominant-baseline: central;
    pointer-events: none;
  }

  .edge-label-highlight {
    font-size: 13px;
    font-weight: 700;
    fill: var(--geo-highlight);
    text-anchor: middle;
    dominant-baseline: central;
    pointer-events: none;
  }

  .angle-arc {
    stroke: var(--geo-angle);
    stroke-width: 1.4;
    fill: none;
  }

  .angle-arc-highlight {
    stroke: var(--geo-highlight);
    stroke-width: 1.8;
    fill: none;
  }

  .angle-label {
    font-size: 11px;
    font-weight: 400;
    fill: var(--geo-angle);
    text-anchor: middle;
    dominant-baseline: central;
    pointer-events: none;
  }

  .angle-label-highlight {
    font-size: 12px;
    font-weight: 700;
    fill: var(--geo-highlight);
    text-anchor: middle;
    dominant-baseline: central;
    pointer-events: none;
  }

  .right-angle {
    stroke: var(--geo-text);
    stroke-width: 1.2;
    fill: none;
    stroke-linecap: square;
  }

  .axis-line {
    stroke: var(--geo-axis);
    stroke-width: 1.5;
    fill: none;
  }

  .axis-arrow {
    fill: var(--geo-axis);
  }

  .axis-label {
    font-size: 13px;
    font-weight: 500;
    fill: var(--geo-axis);
  }

  .tick-label {
    font-size: 10px;
    font-weight: 400;
    fill: var(--geo-annotation);
    text-anchor: middle;
    dominant-baseline: central;
  }

  .grid-line {
    stroke: var(--geo-grid);
    stroke-width: 0.5;
    fill: none;
  }

  .curve {
    stroke: var(--geo-green);
    stroke-width: 2;
    fill: none;
  }

  .annotation {
    font-size: 12px;
    font-weight: 400;
    fill: var(--geo-annotation);
  }
`;
