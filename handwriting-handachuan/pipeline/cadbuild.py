"""Build nameplate.FCStd from config + layered SVGs. Runs inside FreeCAD."""
import os
import FreeCAD as App
import Part

from svgparse import svg_loops


def rounded_solid(w, h, radius, z, height, x=0.0, y=0.0):
    s = Part.makeBox(w - 2 * radius, h, height, App.Vector(x + radius, y, z))
    s = s.fuse(Part.makeBox(w, h - 2 * radius, height, App.Vector(x, y + radius, z)))
    for cx in (x + radius, x + w - radius):
        for cy in (y + radius, y + h - radius):
            s = s.fuse(Part.makeCylinder(radius, height, App.Vector(cx, cy, z)))
    return s


def fuse_all(shapes):
    out = shapes[0]
    for s in shapes[1:]:
        out = out.fuse(s)
    return out


def _inside(p, poly):
    hit = False
    j = len(poly) - 1
    for i in range(len(poly)):
        ax, ay = poly[i][0], poly[i][1]
        bx, by = poly[j][0], poly[j][1]
        if (ay > p[1]) != (by > p[1]) and p[0] < (bx - ax) * (p[1] - ay) / (by - ay) + ax:
            hit = not hit
        j = i
    return hit


def handwriting_solid(svg_path, cfg):
    cw = cfg['canvas']['width_px']
    ch = cfg['canvas']['height_px']
    W = cfg['paper']['width_mm']
    H = cfg['paper']['height_mm']
    top = cfg['paper']['thickness_mm']
    loops = svg_loops(svg_path, cw, ch, W, H, top)
    kept = []
    for i, pts in enumerate(loops):
        try:
            face = Part.Face(Part.makePolygon([App.Vector(*p) for p in pts + [pts[0]]]))
        except Exception:
            continue
        depth = sum(1 for j, other in enumerate(loops) if i != j and _inside(pts[0], other))
        kept.append((face, depth))

    # Attach each counter (odd-depth loop) to its innermost containing glyph.
    def parent_index(idx):
        best, best_depth = None, -1
        for j, other in enumerate(loops):
            if j == idx or j not in valid:
                continue
            if _inside(loops[idx][0], other) and depths[j] < depths[idx] and depths[j] > best_depth:
                best, best_depth = j, depths[j]
        return best

    valid = {i for i, (f, d) in enumerate(kept)}
    depths = {i: d for i, (f, d) in enumerate(kept)}
    min_counter = cfg['handwriting'].get('min_counter_area_mm2', 1.0)

    def poly_area(p):
        return abs(sum(p[k][0] * p[(k + 1) % len(p)][1] - p[(k + 1) % len(p)][0] * p[k][1]
                       for k in range(len(p)))) / 2.0

    holes_of = {i: [] for i in valid}
    for i, (f, d) in enumerate(kept):
        if d % 2 == 1:
            if poly_area(loops[i]) < min_counter:
                continue  # degenerate or printer-irrelevant counter: fill it
            p = parent_index(i)
            if p is not None:
                holes_of[p].append(f)

    # Extrude each glyph first, then subtract only its own counters in 3D;
    # coplanar 2D cut-then-extrude and cross-glyph booleans both yield invalid shapes.
    vec = App.Vector(0, 0, cfg['handwriting']['raise_mm'])
    solids = []
    for i, (face, d) in enumerate(kept):
        if d % 2 != 0:
            continue
        sol = face.extrude(vec)
        for hole in holes_of[i]:
            cut = sol.cut(hole.extrude(vec))
            if not cut.isNull() and cut.isValid():
                sol = cut
        if sol.isNull() or not sol.isValid():
            raise RuntimeError('handwriting glyph %d produced invalid geometry' % i)
        solids.append(sol)
    if not solids:
        raise RuntimeError('no handwriting contours traced from SVG')
    return fuse_all(solids)


SEGMENTS = {
    '0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd',
    '6': 'afgecd', '7': 'abc', '8': 'abcdefg', '9': 'abfgcd',
}


def date_solid(cfg):
    d = cfg['date']
    b = d['base']
    T = b['stroke_mm'] * d['stroke_scale']
    CW = b['digit_width_mm'] * d['character_scale']
    CH = b['digit_height_mm'] * d['character_scale']
    ADV = b['digit_advance_mm'] * d['character_scale']
    DOT_ADV = b['dot_advance_mm'] * d['character_scale']
    Z = cfg['paper']['thickness_mm']
    HGT = d['raise_mm']
    text = d['text']
    x = d['anchor_right_mm']
    # lay out right-to-left so the text is anchored at anchor_right_mm
    for ch in reversed(text):
        if ch == '.':
            x -= DOT_ADV
        else:
            x -= ADV
    parts = []
    for ch in text:
        if ch == '.':
            parts.append(Part.makeCylinder(T / 2.0, HGT, App.Vector(x + DOT_ADV / 2.0, d['anchor_bottom_mm'] + T / 2.0, Z)))
            x += DOT_ADV
            continue
        segs = SEGMENTS.get(ch)
        if segs is None:
            raise ValueError('unsupported date character: %r (digits and dots only)' % ch)
        y = d['anchor_bottom_mm']
        # horizontal bars span the full cell width so unions stay watertight
        boxes = {
            'a': (0, CH - T, CW, T), 'g': (0, CH / 2 - T / 2, CW, T), 'd': (0, 0, CW, T),
            'f': (0, CH / 2 - 0.04, T, CH / 2 - T + 0.04), 'b': (CW - T, CH / 2 - 0.04, T, CH / 2 - T + 0.04),
            'e': (0, T - 0.04, T, CH / 2 - T + 0.04), 'c': (CW - T, T - 0.04, T, CH / 2 - T + 0.04),
        }
        for k, (dx, dy, w, h) in boxes.items():
            if k in segs:
                parts.append(Part.makeBox(w, h, HGT, App.Vector(x + dx, y + dy, Z)))
        x += ADV
    return fuse_all(parts)


def build(project_dir, cfg, svg_dir, out_path):
    W = cfg['paper']['width_mm']
    H = cfg['paper']['height_mm']
    R = cfg['paper']['corner_radius_mm']
    TH = cfg['paper']['thickness_mm']
    line_depth = cfg['ruled_lines']['depth_mm']
    line_w = cfg['ruled_lines']['width_mm']

    doc = App.newDocument('Nameplate')

    # ---- gray layer: ruled-line inlays + border frame ------------------
    gray_parts = []
    ch = cfg['canvas']['height_px']
    from detect import ruled_line_rows
    rows = ruled_line_rows(os.path.join(project_dir, 'step_3_layered_pictures', 'ruled_lines.png'),
                           cfg['ruled_lines'].get('row_min_coverage', 0.5))
    for py in rows:
        y = H - py * H / ch
        gray_parts.append(Part.makeBox(W, line_w, line_depth, App.Vector(0, y - line_w / 2, TH - line_depth)))

    bw = cfg['border']['width_mm']
    bd = cfg['border']['depth_mm']
    outer = rounded_solid(W, H, R, TH - bd, bd)
    inner = rounded_solid(W - 2 * bw, H - 2 * bw, cfg['border']['inner_corner_radius_mm'],
                          TH - bd - 0.01, bd + 0.02, bw, bw)
    border = outer.cut(inner)
    gray = fuse_all(gray_parts)

    # ---- white base: rounded plate minus grooves, border recess, hole --
    base_solid = rounded_solid(W, H, R, 0, TH).cut(gray).cut(border)
    hole_cfg = cfg.get('keyring_hole')
    if hole_cfg:
        cx, cy = hole_cfg['center_mm']
        r = hole_cfg['diameter_mm'] / 2.0
        base_solid = base_solid.cut(Part.makeCylinder(r, TH + 2.0, App.Vector(cx, cy, -1.0)))

    base = doc.addObject('Part::Feature', 'Paper_Base')
    base.Label = 'Paper base — %.1f mm' % TH
    base.Shape = base_solid
    base.addProperty('App::PropertyLength', 'Thickness').Thickness = TH
    base.addProperty('App::PropertyString', 'Description').Description = \
        'Rounded paper plate with ruled-line recesses, border recess and keyring hole'
    if hole_cfg:
        base.addProperty('App::PropertyLength', 'KeyringHoleDiameter').KeyringHoleDiameter = hole_cfg['diameter_mm']
        base.addProperty('App::PropertyString', 'KeyringHoleCenter').KeyringHoleCenter = \
            'X=%.2f mm, Y=%.2f mm' % tuple(hole_cfg['center_mm'])

    gray_obj = doc.addObject('Part::Feature', 'Ruled_Lines_Grooves')
    gray_obj.Label = 'Ruled lines — %.1f mm flush inlay' % line_depth
    gray_obj.Shape = gray
    gray_obj.addProperty('App::PropertyLength', 'RecessDepth').RecessDepth = line_depth
    gray_obj.addProperty('App::PropertyLength', 'Height').Height = line_depth
    gray_obj.addProperty('App::PropertyString', 'Description').Description = \
        'Straight line inlays, flush with the paper top face'

    border_obj = doc.addObject('Part::Feature', 'Border_Frame')
    border_obj.Label = 'Border frame — %.1f mm wide, %.1f mm flush inlay' % (bw, bd)
    border_obj.Shape = border
    border_obj.addProperty('App::PropertyLength', 'BorderWidth').BorderWidth = bw
    border_obj.addProperty('App::PropertyLength', 'Height').Height = bd
    border_obj.addProperty('App::PropertyString', 'Description').Description = \
        'Perimeter frame inlay, flush with the paper top face'

    hand = doc.addObject('Part::Feature', 'Handwriting_Raised')
    hand.Label = 'Handwriting — %.1f mm raised' % cfg['handwriting']['raise_mm']
    hand.Shape = handwriting_solid(os.path.join(svg_dir, 'handwriting.svg'), cfg)
    hand.addProperty('App::PropertyLength', 'Height').Height = cfg['handwriting']['raise_mm']
    hand.addProperty('App::PropertyString', 'Source').Source = 'step_4_layered_svgs/handwriting.svg'

    date = doc.addObject('Part::Feature', 'Date_Raised')
    date.Label = 'Date %s — %d%% size, %d%% bold, %.1f mm raised' % (
        cfg['date']['text'], round(cfg['date']['character_scale'] * 100),
        round(cfg['date']['stroke_scale'] * 100), cfg['date']['raise_mm'])
    date.Shape = date_solid(cfg)
    date.addProperty('App::PropertyLength', 'Height').Height = cfg['date']['raise_mm']
    date.addProperty('App::PropertyString', 'Text').Text = cfg['date']['text']
    date.addProperty('App::PropertyFloat', 'CharacterScale').CharacterScale = cfg['date']['character_scale']
    date.addProperty('App::PropertyFloat', 'StrokeScale').StrokeScale = cfg['date']['stroke_scale']

    doc.recompute()
    for obj in (base, gray_obj, border_obj, hand, date):
        if obj.Shape.isNull() or not obj.Shape.isValid():
            raise RuntimeError('invalid geometry in %s' % obj.Name)
    doc.saveAs(out_path)
    return doc, rows
