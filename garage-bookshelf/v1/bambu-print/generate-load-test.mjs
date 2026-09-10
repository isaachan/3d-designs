import fs from 'node:fs';
import path from 'node:path';

const out = path.join(import.meta.dirname, 'load-test-stl');
fs.mkdirSync(out, { recursive: true });

function normal(a, b, c) {
  const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
  const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
  const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
  const length = Math.hypot(nx, ny, nz) || 1;
  return [nx / length, ny / length, nz / length];
}

function writeSTL(name, triangles) {
  const lines = [`solid ${name}`];
  for (const [a, b, c] of triangles) {
    lines.push(`facet normal ${normal(a, b, c).join(' ')}`, 'outer loop');
    for (const v of [a, b, c]) lines.push(`vertex ${v.join(' ')}`);
    lines.push('endloop', 'endfacet');
  }
  lines.push(`endsolid ${name}`, '');
  fs.writeFileSync(path.join(out, `${name}.stl`), lines.join('\n'));
}

function box(name, x, y, z) {
  const p = [[0,0,0],[x,0,0],[x,y,0],[0,y,0],[0,0,z],[x,0,z],[x,y,z],[0,y,z]];
  const faces = [[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]];
  writeSTL(name, faces.map(face => face.map(i => p[i])));
}

function rib(name, inward) {
  const a = [0,0,0], b = [inward * 25,0,0], c = [0,0,25];
  const d = [0,5,0], e = [inward * 25,5,0], f = [0,5,25];
  writeSTL(name, [[a,b,c],[d,f,e],[a,d,e],[a,e,b],[b,e,f],[b,f,c],[c,f,d],[c,d,a]]);
}

// Two 1:1 lower-panel coupons. Their 180 mm panel width is deliberately
// smaller than the production 215 mm panel, making the root test conservative
// while keeping every part within a 200 mm fallback build area.
for (const side of ['divider', 'right']) {
  box(`01_${side}_base_coupon`, 180, 190, 8);
  box(`02_${side}_back_left`, 90, 150, 5);
  box(`02_${side}_back_right`, 90, 150, 5);
  box(`03_${side}_back_join_plate`, 50, 35, 3);
  box(`04_${side}_lower_panel`, 180, 150, 6);
  rib(`05_${side}_rib_front`, side === 'divider' ? 1 : -1);
  rib(`05_${side}_rib_rear`, side === 'divider' ? 1 : -1);
}

console.log(`Wrote ${fs.readdirSync(out).filter(f => f.endsWith('.stl')).length} load-test STL files to ${out}`);
