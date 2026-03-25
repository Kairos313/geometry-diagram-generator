/**
 * Three.js 3D geometry renderer.
 * Produces a self-contained HTML string with inline JavaScript.
 * Three.js is loaded from CDN — no bundling required.
 */

import type { RenderScene3D, Vec3 } from '../../schema/render-types';

const THREE_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';

/**
 * Render a 3D geometry scene to a self-contained HTML string.
 */
export function renderGeometry3D(scene: RenderScene3D): string {
  const sceneJson = JSON.stringify(scene);

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3D Geometry</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: ${scene.background}; overflow: hidden; }
  canvas { display: block; width: 100vw; height: 100vh; }
  #legend {
    position: fixed; bottom: 12px; left: 12px;
    background: rgba(255,255,255,0.92); border-radius: 6px;
    padding: 8px 12px; font: 12px "Segoe UI", system-ui, sans-serif;
    box-shadow: 0 1px 4px rgba(0,0,0,0.12);
  }
  .legend-item { display: flex; align-items: center; gap: 6px; margin: 2px 0; }
  .legend-dot { width: 10px; height: 10px; border-radius: 50%; }
</style>
<script src="${THREE_CDN}"></script>
</head>
<body>
<div id="legend"></div>
<script>
(function() {
  const data = ${sceneJson};
  const cam = data.camera;

  // ── Scene setup ──
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(data.background);

  const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 200);
  camera.position.set(
    cam.distance * Math.sin(cam.elevation) * Math.cos(cam.azimuth),
    cam.distance * Math.cos(cam.elevation),
    cam.distance * Math.sin(cam.elevation) * Math.sin(cam.azimuth)
  );
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  document.body.appendChild(renderer.domElement);

  // ── Lights ──
  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(10, 15, 10);
  scene.add(dirLight);

  // ── Faces ──
  for (const face of data.elements.faces) {
    if (face.vertices.length < 3) continue;
    const geo = new THREE.BufferGeometry();
    const verts = [];
    // Triangulate (fan from first vertex)
    for (let i = 1; i < face.vertices.length - 1; i++) {
      const v0 = face.vertices[0], v1 = face.vertices[i], v2 = face.vertices[i+1];
      verts.push(v0.x, v0.y, v0.z, v1.x, v1.y, v1.z, v2.x, v2.y, v2.z);
    }
    geo.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
    geo.computeVertexNormals();
    const mat = new THREE.MeshPhongMaterial({
      color: face.color,
      transparent: true,
      opacity: face.opacity,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    scene.add(new THREE.Mesh(geo, mat));
  }

  // ── Circles (wireframe rings for cones, cylinders) ──
  for (const circle of data.elements.circles || []) {
    const segments = 64;
    const circlePoints = [];
    for (let i = 0; i <= segments; i++) {
      const theta = (i / segments) * Math.PI * 2;
      // Circle lies in the XZ plane at the center's Y height
      circlePoints.push(new THREE.Vector3(
        circle.center.x + circle.radius * Math.cos(theta),
        circle.center.y,
        circle.center.z + circle.radius * Math.sin(theta)
      ));
    }
    const circleGeo = new THREE.BufferGeometry().setFromPoints(circlePoints);
    const circleMat = new THREE.LineBasicMaterial({ color: circle.color, linewidth: 1 });
    scene.add(new THREE.Line(circleGeo, circleMat));
  }

  // ── Spheres (translucent wireframe) ──
  for (const sphere of data.elements.spheres || []) {
    const sphereGeo = new THREE.SphereGeometry(sphere.radius, 24, 16);
    const sphereMat = new THREE.MeshPhongMaterial({
      color: sphere.color,
      transparent: true,
      opacity: sphere.opacity,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
    sphereMesh.position.set(sphere.center.x, sphere.center.y, sphere.center.z);
    scene.add(sphereMesh);

    // Add wireframe overlay for visibility
    const wireGeo = new THREE.SphereGeometry(sphere.radius, 16, 12);
    const wireMat = new THREE.MeshBasicMaterial({
      color: sphere.color,
      wireframe: true,
      transparent: true,
      opacity: 0.15,
    });
    const wireMesh = new THREE.Mesh(wireGeo, wireMat);
    wireMesh.position.set(sphere.center.x, sphere.center.y, sphere.center.z);
    scene.add(wireMesh);
  }

  // ── Edges ──
  for (const edge of data.elements.edges) {
    const points = [
      new THREE.Vector3(edge.from.x, edge.from.y, edge.from.z),
      new THREE.Vector3(edge.to.x, edge.to.y, edge.to.z),
    ];
    const geo = new THREE.BufferGeometry().setFromPoints(points);

    let mat;
    if (edge.style === 'dashed') {
      mat = new THREE.LineDashedMaterial({
        color: edge.color,
        dashSize: 0.3,
        gapSize: 0.15,
        linewidth: 1,
      });
      const line = new THREE.Line(geo, mat);
      line.computeLineDistances();
      scene.add(line);
    } else {
      mat = new THREE.LineBasicMaterial({ color: edge.color, linewidth: 1 });
      scene.add(new THREE.Line(geo, mat));
    }

    // Edge label
    if (edge.label) {
      const mid = new THREE.Vector3().addVectors(
        new THREE.Vector3(edge.from.x, edge.from.y, edge.from.z),
        new THREE.Vector3(edge.to.x, edge.to.y, edge.to.z)
      ).multiplyScalar(0.5);
      addLabel(mid, edge.label, edge.highlight ? '#d85a30' : '#2c2c2a', 0.6);
    }
  }

  // ── Points ──
  for (const pt of data.elements.points) {
    const geo = new THREE.SphereGeometry(pt.radius, 16, 12);
    const mat = new THREE.MeshPhongMaterial({ color: pt.color });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(pt.pos.x, pt.pos.y, pt.pos.z);
    scene.add(mesh);

    // Label
    addLabel(
      new THREE.Vector3(pt.pos.x, pt.pos.y, pt.pos.z),
      pt.label,
      pt.style === 'highlight' ? '#d85a30' : '#2c2c2a',
      0.8
    );
  }

  // ── Angle arcs ──
  for (const arc of data.elements.angleArcs) {
    const center = new THREE.Vector3(arc.center.x, arc.center.y, arc.center.z);
    const p1 = new THREE.Vector3(arc.p1.x, arc.p1.y, arc.p1.z);
    const p2 = new THREE.Vector3(arc.p2.x, arc.p2.y, arc.p2.z);

    const v1 = p1.clone().sub(center).normalize();
    const v2 = p2.clone().sub(center).normalize();
    const arcRadius = 0.6;
    const segments = 24;

    const angle = v1.angleTo(v2);
    const normal = new THREE.Vector3().crossVectors(v1, v2).normalize();

    const arcPoints = [];
    for (let i = 0; i <= segments; i++) {
      const t = i / segments;
      const q = new THREE.Quaternion().setFromAxisAngle(normal, angle * t);
      const pt = v1.clone().applyQuaternion(q).multiplyScalar(arcRadius).add(center);
      arcPoints.push(pt);
    }

    const arcGeo = new THREE.BufferGeometry().setFromPoints(arcPoints);
    const arcMat = new THREE.LineBasicMaterial({
      color: arc.highlight ? '#d85a30' : '#ba7517',
      linewidth: 2,
    });
    scene.add(new THREE.Line(arcGeo, arcMat));

    // Arc label
    if (arc.label) {
      const midQ = new THREE.Quaternion().setFromAxisAngle(normal, angle * 0.5);
      const labelPos = v1.clone().applyQuaternion(midQ).multiplyScalar(arcRadius * 1.6).add(center);
      addLabel(labelPos, arc.label, arc.highlight ? '#d85a30' : '#ba7517', 0.5);
    }
  }

  // ── Label helper (canvas sprite) ──
  function addLabel(position, text, color, scale) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 128;
    canvas.height = 64;
    ctx.font = 'bold 32px "Segoe UI", system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = color;
    ctx.fillText(text, 64, 32);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.copy(position);
    // Offset slightly away from center for labels
    const dir = position.clone().normalize();
    sprite.position.add(dir.multiplyScalar(0.3));
    sprite.scale.set(scale, scale * 0.5, 1);
    scene.add(sprite);
  }

  // ── Orbit controls (hand-rolled) ──
  let isDragging = false;
  let prevX = 0, prevY = 0;
  let azimuth = cam.azimuth;
  let elevation = cam.elevation;

  renderer.domElement.addEventListener('pointerdown', (e) => {
    isDragging = true;
    prevX = e.clientX;
    prevY = e.clientY;
  });

  renderer.domElement.addEventListener('pointermove', (e) => {
    if (!isDragging) return;
    const dx = e.clientX - prevX;
    const dy = e.clientY - prevY;
    azimuth += dx * 0.005;
    elevation = Math.max(0.1, Math.min(Math.PI - 0.1, elevation - dy * 0.005));
    prevX = e.clientX;
    prevY = e.clientY;
    updateCamera();
  });

  renderer.domElement.addEventListener('pointerup', () => { isDragging = false; });
  renderer.domElement.addEventListener('pointerleave', () => { isDragging = false; });

  renderer.domElement.addEventListener('wheel', (e) => {
    cam.distance *= (1 + e.deltaY * 0.001);
    cam.distance = Math.max(3, Math.min(100, cam.distance));
    updateCamera();
    e.preventDefault();
  }, { passive: false });

  function updateCamera() {
    camera.position.set(
      cam.distance * Math.sin(elevation) * Math.cos(azimuth),
      cam.distance * Math.cos(elevation),
      cam.distance * Math.sin(elevation) * Math.sin(azimuth)
    );
    camera.lookAt(0, 0, 0);
  }

  // ── Auto-rotate ──
  let autoRotateActive = data.autoRotate && !isDragging;

  // ── Resize ──
  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  // ── setRotation for GIF export ──
  window.setRotation = function(degrees) {
    azimuth = degrees * (Math.PI / 180);
    updateCamera();
    renderer.render(scene, camera);
  };

  // ── Animation loop ──
  function animate() {
    requestAnimationFrame(animate);
    if (data.autoRotate && !isDragging) {
      azimuth += 0.003;
      updateCamera();
    }
    renderer.render(scene, camera);
  }
  animate();

  // ── Legend ──
  const legendEl = document.getElementById('legend');
  const uniqueColors = new Map();
  for (const pt of data.elements.points) {
    if (!uniqueColors.has(pt.color)) {
      uniqueColors.set(pt.color, pt.label);
    }
  }
  if (uniqueColors.size > 0) {
    for (const [color, label] of uniqueColors) {
      const item = document.createElement('div');
      item.className = 'legend-item';
      item.innerHTML = '<div class="legend-dot" style="background:' + color + '"></div><span>' + label + '</span>';
      legendEl.appendChild(item);
    }
  } else {
    legendEl.style.display = 'none';
  }
})();
</script>
</body>
</html>`;
}
