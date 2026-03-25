import * as esbuild from 'esbuild';

const watch = process.argv.includes('--watch');

const config = {
  entryPoints: ['src/index.ts'],
  bundle: true,
  outfile: 'dist/geometry-renderer.js',
  format: 'iife',
  globalName: 'GeometryRenderer',
  sourcemap: true,
  target: 'es2020',
  // D3 and Three.js loaded from CDN, not bundled
  external: ['d3', 'three'],
  define: {
    'process.env.NODE_ENV': '"production"',
  },
};

if (watch) {
  const ctx = await esbuild.context(config);
  await ctx.watch();
  console.log('Watching for changes...');
} else {
  await esbuild.build(config);
  console.log('Built dist/geometry-renderer.js');
}
