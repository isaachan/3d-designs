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

function cylinder(tris, cx, cy, r, h, sides = 20) {
  const bottom = [], top = [];
  for (let i = 0; i < sides; i++) {
    const a = i * 2 * Math.PI / sides;
    bottom.push([cx + r * Math.cos(a), cy + r * Math.sin(a), 0]);
    top.push([cx + r * Math.cos(a), cy + r * Math.sin(a), h]);
  }
  const cb = [cx, cy, 0], ct = [cx, cy, h];
  for (let i = 0; i < sides; i++) {
    const j = (i + 1) % sides;
    tris.push([cb, bottom[j], bottom[i]], [ct, top[i], top[j]], [bottom[i], bottom[j], top[j]], [bottom[i], top[j], top[i]]);
  }
}

function baseOutline(kind) {
  const leftNotch = kind !== 'first';
  const rightTail = kind !== 'last';
  const left = [[0,0],[230,0]];
  const right = rightTail ? [[230,20],[238,20],[238,80],[230,80],[230,140],[238,140],[238,200],[230,200],[230,220]] : [[230,220]];
  const revLeft = leftNotch ? [[0,220],[0,200],[8,200],[8,140],[0,140],[0,80],[8,80],[8,20],[0,20]] : [[0,220]];
  return [...left, ...right, ...revLeft];
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
  const kind = i === 1 ? 'first' : i === 4 ? 'last' : 'middle';
  if (i === 2) {
    // 6.2 mm wide x 4 mm deep groove for the divider tongue at assembled x = 360 mm.
    extrudePolygon(tris, baseOutline(kind), 4);
    box(tris, 0, 0, 4, 130, 220, 4);
    box(tris, 136.2, 0, 4, 93.8, 220, 4);
  } else if (i === 4) {
    // 6 mm deep edge rebate for the right panel tongue at the outer right end.
    extrudePolygon(tris, baseOutline(kind), 4);
    box(tris, 0, 0, 4, 224, 220, 4);
  } else {
    extrudePolygon(tris, baseOutline(kind), 8);
  }
  stl(`01_base_${String(i).padStart(2, '0')}`, tris);
}

// Rear wall: eight flat 230 x 150 panels. Glue the seams on the rear with the supplied join plates.
for (let row = 1; row <= 2; row++) for (let col = 1; col <= 4; col++) panel(`02_back_r${row}_c${col}`, 230, 150, 5);
for (let i = 1; i <= 10; i++) panel(`03_back_join_plate_${String(i).padStart(2, '0')}`, 50, 35, 3);

// Central divider and right end panel, each split at 150 mm to fit a 256 mm build plate.
for (const prefix of ['04_divider', '05_right_panel']) {
  panel(`${prefix}_lower_with_tongue`, 220, 156, 6);
  panel(`${prefix}_upper`, 220, 150, 6);
  panel(`${prefix}_vertical_join_plate`, 45, 70, 3);
}

// Three garage decks, split through their middle to fit a 256 mm build plate.
for (let deck = 1; deck <= 3; deck++) {
  panel(`06_garage_deck_${deck}_left`, 180, 150, 5);
  panel(`06_garage_deck_${deck}_right`, 180, 150, 5);
  panel(`06_garage_deck_${deck}_join_plate`, 42, 50, 3);
}

// Four front columns; print upright with brim (12 mm diameter x 250 mm high).
for (let i = 1; i <= 4; i++) { const tris = []; cylinder(tris, 6, 6, 6, 250); stl(`07_yellow_column_${i}`, tris); }

// Four small triangular ribs: 25 x 25 x 5, placed at the base roots of the divider and right panel.
for (let i = 1; i <= 4; i++) {
  const tris = [];
  const a = [0,0,0], b = [25,0,0], c = [0,0,25], d = [0,5,0], e = [25,5,0], f = [0,5,25];
  tris.push([a,b,c],[d,f,e],[a,d,e],[a,e,b],[b,e,f],[b,f,c],[c,f,d],[c,d,a]);
  stl(`08_reinforcing_rib_${i}`, tris);
}

// Billboard is split into three pieces, with two rear joining plates; posts are individual parts.
for (let i = 1; i <= 3; i++) panel(`09_billboard_${i}`, i < 3 ? 174 : 172, 70, 6);
for (let i = 1; i <= 2; i++) panel(`09_billboard_join_plate_${i}`, 44, 38, 3);
for (let i = 1; i <= 2; i++) { const tris = []; cylinder(tris, 6, 6, 6, 120); stl(`10_billboard_post_${i}`, tris); }

panel('11_book_depot_sign', 180, 36, 6);
labelText('12_billboard_text_lovely_car_ive_driven', "Lovely Car I've Driven", 43, 440, 64);
labelText('13_sign_text_book_depot', 'BOOK DEPOT', 16, 36, 180, true);

console.log(`Wrote ${fs.readdirSync(out).filter(f => f.endsWith('.stl')).length} STL files to ${out}`);
