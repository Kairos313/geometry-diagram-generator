/**
 * Geometry Renderer — entry point.
 *
 * Converts a blueprint JSON (from generate_blueprint_focused.py)
 * into an interactive HTML diagram using D3.js (2D) or Three.js (3D).
 *
 * Usage (browser):
 *   const html = GeometryRenderer.renderFromBlueprint(blueprintJson);
 *   document.getElementById('output').innerHTML = html;
 *
 * Usage (get SVG only, 2D):
 *   const svg = GeometryRenderer.renderToSvg(blueprintJson);
 */

import type { BlueprintJSON } from './schema/blueprint-types';
import type { RenderScene } from './schema/render-types';
import { convertBlueprint } from './schema/converter';
import { renderGeometry2D } from './renderers/d3/renderer';
import { renderGeometry3D } from './renderers/three/renderer';
import { GEOMETRY_STYLES } from './renderers/d3/styles';

/**
 * Render a blueprint JSON to a complete HTML string.
 * For 2D: wraps SVG in an HTML page with D3 CDN (for potential interactivity).
 * For 3D: returns a self-contained Three.js HTML page.
 */
export function renderFromBlueprint(blueprintJson: string | BlueprintJSON): string {
  const blueprint: BlueprintJSON = typeof blueprintJson === 'string'
    ? JSON.parse(blueprintJson)
    : blueprintJson;

  const scene = convertBlueprint(blueprint);

  if (scene.type === '2d') {
    const svg = renderGeometry2D(scene);
    return wrapSvgInHtml(svg);
  } else {
    return renderGeometry3D(scene);
  }
}

/**
 * Render a blueprint to SVG string only (2D only).
 * Returns the raw <svg>...</svg> string for embedding.
 */
export function renderToSvg(blueprintJson: string | BlueprintJSON): string {
  const blueprint: BlueprintJSON = typeof blueprintJson === 'string'
    ? JSON.parse(blueprintJson)
    : blueprintJson;

  const scene = convertBlueprint(blueprint);

  if (scene.type !== '2d') {
    throw new Error('renderToSvg only supports 2D blueprints');
  }

  return renderGeometry2D(scene);
}

/**
 * Convert a blueprint JSON to the intermediate render scene.
 * Useful for debugging the conversion step.
 */
export function convertToScene(blueprintJson: string | BlueprintJSON): RenderScene {
  const blueprint: BlueprintJSON = typeof blueprintJson === 'string'
    ? JSON.parse(blueprintJson)
    : blueprintJson;

  return convertBlueprint(blueprint);
}

function wrapSvgInHtml(svgString: string): string {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>2D Geometry</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: #f8f7f4;
  }
  @media (prefers-color-scheme: dark) {
    body { background: #1a1a1e; }
  }
  svg { max-width: 100%; height: auto; }
</style>
</head>
<body>
${svgString}
</body>
</html>`;
}

// Re-export types for external use
export type { BlueprintJSON } from './schema/blueprint-types';
export type { RenderScene, RenderScene2D, RenderScene3D } from './schema/render-types';
