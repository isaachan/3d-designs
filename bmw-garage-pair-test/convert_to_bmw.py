#!/usr/bin/env python3
"""
Convert Garage_Honda.3mf (Bambu Studio project, 1/64 Honda showroom garage)
into a BMW-styled garage: Garage_BMW.3mf

What it does
------------
1. Colors (project_settings.config):
     slot0 black  -> #000000 (kept)   : road base, structure, lettering, roundel ring
     slot1 yellow -> #0166B1 BMW blue : parking lines, curbs, roundel blue quarters
     slot2 gray   -> #8E9089 (kept)   : showroom building, logo strip surface
     slot3 white  -> #FFFFFF (kept)   : glass walls, roundel white quarters, sign base
     slot4 red    -> #D6001C BMW M red: accent/gradient color
2. object_39 (inside logo strip): Honda "HONDA" outline letters + ring emblem
   repainted to background gray (invisible), new "BMW" block letters (black)
   and a BMW roundel (black ring + blue/white quarters) added.
3. object_42 (front sign): winged-Honda emblem + "HONDA" text erased
   (paint removed -> base color), new BMW roundel + "BMW" text added.
4. object_43 (glass walls): red Honda decals erased, new "BMW" letter decal
   + big BMW roundel added.
5. model_settings.config: logo parts now print with white base (extruder 4),
   face counts updated, names renamed, source_file renamed.
6. 3dmodel.model: title/description Honda -> BMW.

New geometry is added as thin painted prisms that sit flush in the top
surface (protruding 0.002 mm, same layer-slicing behavior as the original
painted-in-surface lettering).
"""
import os, re, shutil, math, zipfile

SRC_3MF = 'Garage_Honda.3mf'
SRC = 'extracted_fresh'
BUILD = 'build'
OUT = 'Garage_BMW.3mf'

if not os.path.exists(SRC):
    os.makedirs(SRC)
    with zipfile.ZipFile(SRC_3MF) as z:
        z.extractall(SRC)

if os.path.exists(BUILD):
    shutil.rmtree(BUILD)
shutil.copytree(SRC, BUILD)

# ----------------------------------------------------------------------------
# low level mesh helpers
# ----------------------------------------------------------------------------
def fmt(v):
    s = f'{v:.6f}'
    if s == '-0.000000':
        s = '0.000000'
    return s

class MeshAppender:
    def __init__(self, path):
        self.path = path
        data = open(path).read()
        self.data = data
        m = re.search(r'<vertex x="', data)
        verts = re.findall(r'<vertex x="([-\d.eE]+)" y="([-\d.eE]+)" z="([-\d.eE]+)"/>', data)
        self.nverts = len(verts)
        tris = re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"/?>', data)
        self.ntris = len(re.findall(r'<triangle ', data))
        self.new_verts = []
        self.new_tris = []   # (i,j,k,paint)

    def vert(self, x, y, z):
        self.new_verts.append((x, y, z))
        return self.nverts + len(self.new_verts) - 1

    def tri(self, a, b, c, paint):
        self.new_tris.append((a, b, c, paint))

    # --- geometry primitives -------------------------------------------------
    def polygon_prism(self, pts, z0, z1, paint):
        """pts: CCW 2D polygon (convex or star-triangulatable via fan from v0).
        Adds a closed prism [z0,z1] with all faces painted."""
        n = len(pts)
        # ensure CCW
        area = sum(pts[i][0]*pts[(i+1)%n][1] - pts[(i+1)%n][0]*pts[i][1] for i in range(n))/2
        if area < 0:
            pts = pts[::-1]
        top = [self.vert(x, y, z1) for x, y in pts]
        bot = [self.vert(x, y, z0) for x, y in pts]
        # top face (fan, CCW -> +z)
        for i in range(1, n-1):
            self.tri(top[0], top[i], top[i+1], paint)
        # bottom face (reversed)
        for i in range(1, n-1):
            self.tri(bot[0], bot[i+1], bot[i], paint)
        # sides (outward)
        for i in range(n):
            j = (i+1) % n
            self.tri(top[i], bot[i], bot[j], paint)
            self.tri(top[i], bot[j], top[j], paint)

    def rect(self, x0, y0, x1, y1, z0, z1, paint):
        self.polygon_prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, paint)

    def wedge(self, cx, cy, r, a0, a1, z0, z1, paint, segs=16):
        """circular wedge (pie slice) from angle a0 to a1 (radians, CCW)."""
        pts = [(cx, cy)]
        for i in range(segs+1):
            a = a0 + (a1-a0)*i/segs
            pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
        self.polygon_prism(pts, z0, z1, paint)

    def annulus(self, cx, cy, r0, r1, z0, z1, paint, segs=64):
        """full ring (annulus) as vertical strips between two circles."""
        outer, inner = [], []
        for i in range(segs):
            a = 2*math.pi*i/segs
            outer.append((cx + r1*math.cos(a), cy + r1*math.sin(a)))
            inner.append((cx + r0*math.cos(a), cy + r0*math.sin(a)))
        # build strip quads (each quad = polygon_prism of 4 pts)
        for i in range(segs):
            j = (i+1) % segs
            quad = [outer[i], outer[j], inner[j], inner[i]]
            # CCW check: outer is CCW; quad outer[i]->outer[j]->inner[j]->inner[i] is CCW
            n = 4
            area = sum(quad[k][0]*quad[(k+1)%n][1] - quad[(k+1)%n][0]*quad[k][1] for k in range(n))/2
            if area < 0:
                quad = quad[::-1]
            self.polygon_prism(quad, z0, z1, paint)

    # --- letters --------------------------------------------------------------
    @staticmethod
    def letter_B(H):
        s = 0.245*H; w = 1.18*H
        mids = 0.145*H; stub_w = 0.22*H
        bar_top_y0 = H - s
        mid_y0 = (H - mids)/2
        return [('rect', (0, 0, s, H)),
                ('rect', (s, bar_top_y0, w, H)),
                ('rect', (s, 0, w, s)),
                ('rect', (s, mid_y0, w - stub_w, mid_y0 + mids)),
                ('rect', (w - stub_w, mid_y0 + mids, w, bar_top_y0)),
                ('rect', (w - stub_w, s, w, mid_y0))], w

    @staticmethod
    def letter_M(H):
        s = 0.245*H; w = 1.36*H
        c = w/2
        vb = 0.37*H          # bottom y of the V
        tw = 0.235*H         # top width of diagonal stroke
        bw = tw*1.05         # bottom width
        return [('rect', (0, 0, s, H)),
                ('rect', (w - s, 0, w, H)),
                ('quad', [(s, H), (s + tw, H), (c + bw/2, vb), (c - bw/2, vb)]),
                ('quad', [(w - s - tw, H), (w - s, H), (c + bw/2, vb), (c - bw/2, vb)][::-1])], w

    @staticmethod
    def letter_W(H):
        w = 1.64*H
        tw = 0.227*H
        vb = 0.0
        pk = 0.58*H          # middle peak height
        c1 = w*0.35; c2 = w/2; c3 = w*0.65
        return [('quad', [(0, H), (tw, H), (c1 + tw/2, vb), (c1 - tw/2, vb)]),
                ('quad', [(c1 - tw/2, vb), (c1 + tw/2, vb), (c2 + tw/2, pk), (c2 - tw/2, pk)]),
                ('quad', [(c2 - tw/2, pk), (c2 + tw/2, pk), (c3 + tw/2, vb), (c3 - tw/2, vb)]),
                ('quad', [(c3 - tw/2, vb), (c3 + tw/2, vb), (w, H), (w - tw, H)])], w

    def text(self, word, x_start, y_base, H, z0, z1, paint):
        x = x_start
        for ch in word:
            pieces, w = getattr(self, f'letter_{ch}')(H)
            for kind, p in pieces:
                if kind == 'rect':
                    self.rect(p[0]+x, p[1]+y_base, p[2]+x, p[3]+y_base, z0, z1, paint)
                else:
                    self.polygon_prism([(px+x, py+y_base) for px, py in p], z0, z1, paint)
            x += w + 0.42*H
        return x - 0.42*H  # end x

    def text_width(self, word, H):
        ws = {'B': 1.18*H, 'M': 1.36*H, 'W': 1.64*H}
        return sum(ws[c] for c in word) + 0.42*H*(len(word)-1)

    def roundel(self, cx, cy, r_out, ring_w, z0, z1,
                ring='0C', blue='1C', white='3C'):
        self.annulus(cx, cy, r_out - ring_w, r_out, z0, z1, ring)
        q = math.pi/2
        self.wedge(cx, cy, r_out - ring_w, 0*q, 1*q, z0, z1, blue)    # top-right  blue
        self.wedge(cx, cy, r_out - ring_w, 1*q, 2*q, z0, z1, white)   # top-left   white
        self.wedge(cx, cy, r_out - ring_w, 2*q, 3*q, z0, z1, blue)    # bottom-left blue
        self.wedge(cx, cy, r_out - ring_w, 3*q, 4*q, z0, z1, white)   # bottom-right white

    # --- finish ---------------------------------------------------------------
    def rewrite(self, repaint=None, erase=None):
        """repaint: {'0C':'2C'} change paint attrs; erase: {'0C'} remove paint attr."""
        data = self.data
        if repaint:
            for old, new in repaint.items():
                data = data.replace(f' paint_color="{old}"', f' paint_color="{new}"')
        if erase:
            for old in erase:
                data = data.replace(f' paint_color="{old}"', '')
        vlines = ''.join(f'     <vertex x="{fmt(x)}" y="{fmt(y)}" z="{fmt(z)}"/>\n'
                         for x, y, z in self.new_verts)
        tlines = ''.join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"'
                         + (f' paint_color="{pc}"' if pc else '') + '/>\n'
                         for a, b, c, pc in self.new_tris)
        data = data.replace('   </vertices>', vlines + '   </vertices>')
        data = data.replace('   </triangles>', tlines + '   </triangles>')
        open(self.path, 'w').write(data)
        return len(re.findall(r'<triangle v\d', data))  # real triangle count

# ----------------------------------------------------------------------------
# 1) object_39 : inside logo strip
# ----------------------------------------------------------------------------
m39 = MeshAppender(f'{BUILD}/3D/Objects/object_39.model')
Z0, Z1 = 0.40, 0.502
H = 11.1
x0 = -42.8 - m39.text_width('BMW', H)/2
m39.text('BMW', x0, -H/2, H, Z0, Z1, '0C')
m39.roundel(84.4, 0.25, 8.8, 1.55, Z0, Z1)
n39 = m39.rewrite(repaint={'0C': '2C'})

# ----------------------------------------------------------------------------
# 2) object_42 : front sign
# ----------------------------------------------------------------------------
m42 = MeshAppender(f'{BUILD}/3D/Objects/object_42.model')
m42.roundel(0.0, 6.0, 13.2, 2.2, Z0, Z1)
H2 = 8.0
x0 = -m42.text_width('BMW', H2)/2
m42.text('BMW', x0, -20.0, H2, Z0, Z1, '0C')
n42 = m42.rewrite(erase={'0C'})

# ----------------------------------------------------------------------------
# 3) object_43 : glass wall decals
# ----------------------------------------------------------------------------
m43 = MeshAppender(f'{BUILD}/3D/Objects/object_43.model')
GZ0, GZ1 = 0.88, 1.002
H3 = 11.0
x0 = -58 - m43.text_width('BMW', H3)/2
m43.text('BMW', x0, -H3/2 + 1.5, H3, GZ0, GZ1, '0C')
m43.roundel(47.5, 0.0, 18.0, 3.0, GZ0, GZ1)
n43 = m43.rewrite(erase={'4'})

print(f'object_39: {n39} triangles (was 2616)')
print(f'object_42: {n42} triangles (was 2156)')
print(f'object_43: {n43} triangles (was 2176)')

# ----------------------------------------------------------------------------
# 4) model_settings.config
# ----------------------------------------------------------------------------
p = f'{BUILD}/Metadata/model_settings.config'
d = open(p).read()
d = d.replace('value="Garage_Honda.3mf"', 'value="Garage_BMW.3mf"')
# object 14 (object_39) and object 16 (object_42): white base instead of red
d = d.replace('''<object id="14">
    <metadata key="name" value="Audi (3).stl"/>
    <metadata key="extruder" value="5"/>
    <metadata face_count="2616"/>''',
'''<object id="14">
    <metadata key="name" value="BMW Inside Logo Strip"/>
    <metadata key="extruder" value="4"/>
    <metadata face_count="%d"/>''' % n39)
d = d.replace('''<object id="16">
    <metadata key="name" value="Audi.stl"/>
    <metadata key="extruder" value="5"/>
    <metadata face_count="2156"/>''',
'''<object id="16">
    <metadata key="name" value="BMW Front Sign"/>
    <metadata key="extruder" value="4"/>
    <metadata face_count="%d"/>''' % n42)
d = d.replace('''<object id="18">
    <metadata key="name" value="Audi (4).stl"/>
    <metadata key="extruder" value="4"/>
    <metadata face_count="2176"/>''',
'''<object id="18">
    <metadata key="name" value="BMW Glass Wall Decals"/>
    <metadata key="extruder" value="4"/>
    <metadata face_count="%d"/>''' % n43)
# part-level names + mesh stats
d = d.replace('value="Audi (3).stl"', 'value="BMW Inside Logo Strip"')
d = d.replace('value="Audi.stl"', 'value="BMW Front Sign"')
d = d.replace('value="Audi (4).stl"', 'value="BMW Glass Wall Decals"')
d = d.replace('<mesh_stat face_count="2616"', f'<mesh_stat face_count="{n39}"')
d = d.replace('<mesh_stat face_count="2156"', f'<mesh_stat face_count="{n42}"')
d = d.replace('<mesh_stat face_count="2176"', f'<mesh_stat face_count="{n43}"')
open(p, 'w').write(d)

# ----------------------------------------------------------------------------
# 5) project_settings.config : BMW filament palette
# ----------------------------------------------------------------------------
p = f'{BUILD}/Metadata/project_settings.config'
d = open(p).read()
OLD_NEW = [('"#F4EE2A"', '"#0166B1"'),   # slot1 yellow -> BMW blue
             ('"#C12E1F"', '"#D6001C"')]   # slot4 Honda red -> BMW M red
cnt = sum(d.count(a) for a, _ in OLD_NEW)
assert cnt == 4, f'expected 4 colour occurrences, found {cnt}'
for old, new in OLD_NEW:
    d = d.replace(old, new)
open(p, 'w').write(d)

# ----------------------------------------------------------------------------
# 6) 3dmodel.model : title & description
# ----------------------------------------------------------------------------
p = f'{BUILD}/3D/3dmodel.model'
d = open(p).read()
d = d.replace('本田展厅车库展示', 'BMW展厅车库展示')
d = d.replace('本田展厅', 'BMW展厅').replace('本田品牌', 'BMW品牌').replace('本田美学', 'BMW美学')
assert '本田' not in d
open(p, 'w').write(d)

# ----------------------------------------------------------------------------
# 7) repackage
# ----------------------------------------------------------------------------
if os.path.exists(OUT):
    os.remove(OUT)
names = []
for root, dirs, files in os.walk(BUILD):
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, BUILD)
        names.append(rel.replace(os.sep, '/'))
names.sort(key=lambda n: (n != '[Content_Types].xml', n))
with zipfile.ZipFile(OUT, 'w') as z:
    for rel in names:
        full = os.path.join(BUILD, rel)
        if rel.endswith(('.png', '.webp', '.jpg')):
            z.write(full, rel, zipfile.ZIP_STORED)
        else:
            z.write(full, rel, zipfile.ZIP_DEFLATED)
print('wrote', OUT, os.path.getsize(OUT), 'bytes')
