import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const out = path.join(import.meta.dirname, 'stl');
fs.mkdirSync(out, { recursive: true });

function normal(a, b, c) {
  const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
  const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
  const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
  const len = Math.hypot(nx, ny, nz) || 1;
  return [nx / len, ny / len, nz / len];
}

function stl(name, triangles) {
  const lines = [`solid ${name}`];
  for (const [a, b, c] of triangles) {
    const n = normal(a, b, c);
    lines.push(`facet normal ${n.join(' ')}`, 'outer loop');
    for (const v of [a, b, c]) lines.push(`vertex ${v.join(' ')}`);
    lines.push('endloop', 'endfacet');
  }
  lines.push(`endsolid ${name}`, '');
  fs.writeFileSync(path.join(out, `${name}.stl`), lines.join('\n'));
}

function box(tris, x, y, z, dx, dy, dz) {
  const p = [[x,y,z],[x+dx,y,z],[x+dx,y+dy,z],[x,y+dy,z], [x,y,z+dz],[x+dx,y,z+dz],[x+dx,y+dy,z+dz],[x,y+dy,z+dz]];
  const faces = [[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]];
  for (const f of faces) tris.push(f.map(i => p[i]));
}

function extrudePolygon(tris, points, z) {
  const n = points.length;
  const low = points.map(([x,y]) => [x,y,0]);
  const high = points.map(([x,y]) => [x,y,z]);
  const area = points.reduce((sum, p, i) => { const q = points[(i + 1) % n]; return sum + p[0] * q[1] - q[0] * p[1]; }, 0);
  const indices = [...Array(n).keys()];
  const cross2 = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
  const inside = (p, a, b, c) => {
    const s1 = cross2(a, b, p), s2 = cross2(b, c, p), s3 = cross2(c, a, p);
    return area > 0 ? s1 >= 0 && s2 >= 0 && s3 >= 0 : s1 <= 0 && s2 <= 0 && s3 <= 0;
  };
  while (indices.length > 3) {
    let clipped = false;
    for (let i = 0; i < indices.length; i++) {
      const ia = indices[(i - 1 + indices.length) % indices.length], ib = indices[i], ic = indices[(i + 1) % indices.length];
      if ((area > 0 ? 1 : -1) * cross2(points[ia], points[ib], points[ic]) <= 0) continue;
      if (indices.some(j => j !== ia && j !== ib && j !== ic && inside(points[j], points[ia], points[ib], points[ic]))) continue;
      tris.push([low[ia], low[ic], low[ib]], [high[ia], high[ib], high[ic]]);
      indices.splice(i, 1); clipped = true; break;
    }
    if (!clipped) throw new Error('Could not triangulate outline');
  }
  tris.push([low[indices[0]], low[indices[2]], low[indices[1]]], [high[indices[0]], high[indices[1]], high[indices[2]]]);
  for (let i = 0; i < n; i++) { const j = (i + 1) % n; tris.push([low[i], low[j], high[j]], [low[i], high[j], high[i]]); }
}

function cylinder(tris, cx, cy, r, h, sides = 20, z = 0) {
  const bottom = [], top = [];
  for (let i = 0; i < sides; i++) {
    const a = i * 2 * Math.PI / sides;
    bottom.push([cx + r * Math.cos(a), cy + r * Math.sin(a), z]);
    top.push([cx + r * Math.cos(a), cy + r * Math.sin(a), z + h]);
  }
  const cb = [cx, cy, z], ct = [cx, cy, z + h];
  for (let i = 0; i < sides; i++) {
    const j = (i + 1) % sides;
    tris.push([cb, bottom[j], bottom[i]], [ct, top[i], top[j]], [bottom[i], bottom[j], top[j]], [bottom[i], top[j], top[i]]);
  }
}

function frustum(tris, cx, cy, r1, r2, z, h, sides = 20) {
  const low = [], high = [];
  for (let i = 0; i < sides; i++) {
    const a = i * 2 * Math.PI / sides;
    low.push([cx + r1 * Math.cos(a), cy + r1 * Math.sin(a), z]);
    high.push([cx + r2 * Math.cos(a), cy + r2 * Math.sin(a), z + h]);
  }
  const cb = [cx, cy, z], ct = [cx, cy, z + h];
  for (let i = 0; i < sides; i++) {
    const j = (i + 1) % sides;
    tris.push([cb, low[j], low[i]], [ct, high[i], high[j]],
      [low[i], low[j], high[j]], [low[i], high[j], high[i]]);
  }
}

function baseOutline(hasLeftSocket, hasRightTongue) {
  // The tongue is 7.6 mm wide and the socket 8 mm wide: 0.4 mm total
  // clearance prevents impossible solid overlap while retaining alignment.
  const points = [[0, 0], [230, 0]];
  if (hasRightTongue) {
    points.push([230, 21], [237.6, 21], [237.6, 79], [230, 79],
      [230, 141], [237.6, 141], [237.6, 199], [230, 199]);
  }
  points.push([230, 220], [0, 220]);
  if (hasLeftSocket) {
    points.push([0, 200], [8, 200], [8, 140], [0, 140],
      [0, 80], [8, 80], [8, 20], [0, 20]);
  }
  return points;
}

function panel(name, w, h, t) { const tris = []; box(tris, 0, 0, 0, w, h, t); stl(name, tris); }

function labelText(name, text, fontSize, width, height, vertical = false) {
  const mask = JSON.parse(execFileSync('/usr/bin/swift', [path.join(import.meta.dirname, 'generate-label-mask.swift'), text, String(fontSize), String(width), String(height), vertical ? 'vertical' : 'horizontal'], { encoding: 'utf8' }));
  const tris = [];
  // 1 mm high white PLA characters; glue them onto the coloured sign faces.
  for (const [x, y, run] of mask) box(tris, x, y, 0, run, 1, 1);
  stl(name, tris);
}

for (let i = 1; i <= 4; i++) {
  const tris = [];
  extrudePolygon(tris, baseOutline(i > 1, i < 4), 8);
  stl(`01_base_${String(i).padStart(2, '0')}`, tris);
}

// Rear wall: eight flat 230 x 150 panels. Glue the seams on the rear with the supplied join plates.
for (let row = 1; row <= 2; row++) for (let col = 1; col <= 4; col++) panel(`02_back_r${row}_c${col}`, 230, 150, 5);
for (let i = 1; i <= 10; i++) panel(`03_back_join_plate_${String(i).padStart(2, '0')}`, 50, 35, 3);

// Central divider and right end panel sit on the 8 mm base, touch the rear wall,
// and meet exactly at Z=158 mm. Their wide rear/side splice plates carry lateral load.
for (const prefix of ['04_divider', '05_right_panel']) {
  panel(`${prefix}_lower`, 215, 150, 6);
  panel(`${prefix}_upper`, 215, 150, 6);
  panel(`${prefix}_vertical_join_plate`, 45, 70, 3);
}

function garageDeckHalf(name, right) {
  const tris = [];
  const [left, rightEdge] = right ? [153, 167] : [3, 17];
  // Front/rear entry notches are one continuous, watertight outline. Their
  // 14 mm width gives 1 mm radial clearance around Ø12 columns.
  extrudePolygon(tris, [
    [0, 0], [left, 0], [left, 17], [rightEdge, 17], [rightEdge, 0], [180, 0],
    [180, 215], [rightEdge, 215], [rightEdge, 188], [left, 188], [left, 215], [0, 215],
  ], 5);
  stl(name, tris);
}

// Three 360 × 215 mm garage decks. Each reaches the rear wall and is carried
// by continuous columns through clearance holes, with integral support collars below.
for (let deck = 1; deck <= 3; deck++) {
  garageDeckHalf(`06_garage_deck_${deck}_left`, false);
  garageDeckHalf(`06_garage_deck_${deck}_right`, true);
  panel(`06_garage_deck_${deck}_join_plate`, 42, 50, 3);
}

// Four Ø12 × 250 mm continuous columns. The Ø22 collars sit immediately under
// every deck, so vertical load goes through a shoulder instead of a glue line.
for (let i = 1; i <= 4; i++) {
  const tris = [];
  cylinder(tris, 10, 10, 6, 250);
  for (const z of [54, 117, 180]) {
    frustum(tris, 10, 10, 6, 14, z - 8, 8);
    cylinder(tris, 10, 10, 14, 4, 20, z);
  }
  stl(`07_yellow_column_${i}`, tris);
}

function reinforcingRib(name, inward) {
  const tris = [];
  const a = [0,0,0], b = [inward * 25,0,0], c = [0,0,25];
  const d = [0,5,0], e = [inward * 25,5,0], f = [0,5,25];
  tris.push([a,b,c],[d,f,e],[a,d,e],[a,e,b],[b,e,f],[b,f,c],[c,f,d],[c,d,a]);
  stl(name, tris);
}
reinforcingRib('08_reinforcing_rib_1', 1);
reinforcingRib('08_reinforcing_rib_2', 1);
reinforcingRib('08_reinforcing_rib_3', -1);
reinforcingRib('08_reinforcing_rib_4', -1);

// Front and rear garage headers finish the columns and keep their tops from splaying.
for (const side of ['front', 'rear']) {
  panel(`14_garage_header_${side}_left`, 180, 20, 6);
  panel(`14_garage_header_${side}_right`, 180, 20, 6);
  panel(`14_garage_header_${side}_join_plate`, 42, 20, 3);
}

// Billboard is split into three pieces, with two rear joining plates; posts are individual parts.
for (let i = 1; i <= 3; i++) panel(`09_billboard_${i}`, i < 3 ? 174 : 172, 70, 6);
for (let i = 1; i <= 2; i++) panel(`09_billboard_join_plate_${i}`, 44, 38, 3);
for (let i = 1; i <= 2; i++) panel(`10_billboard_post_${i}`, 28, 130, 6);

// Front-facing external vertical sign: 36 mm wide × 180 mm tall × 6 mm deep.
panel('11_book_depot_sign', 36, 180, 6);
labelText('12_billboard_text_lovely_car_ive_driven', "Lovely Car I've Driven", 30, 440, 64);
labelText('13_sign_text_book_depot', 'BOOK DEPOT', 16, 36, 180, true);

console.log(`Wrote ${fs.readdirSync(out).filter(f => f.endsWith('.stl')).length} STL files to ${out}`);
