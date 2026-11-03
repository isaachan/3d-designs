#!/usr/bin/env python3
"""Derive printable, colour-separated parts from the reviewed assembly CAD.

The assembly source stays immutable. All road/deck joints use two Ø3 PLA pins
in Ø3.3 x 5.2 sockets plus glue. Large foundation panels use underside straps.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
import build as cad
import FreeCAD as App
import Part
import Mesh
import MeshPart

V = App.Vector
P = cad.P
SOURCE = ROOT.parent/'cad/parking-lot-v1-assembly.FCStd'
OUT = ROOT/'parts'
NS = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
ET.register_namespace('', NS)
PARTS = []
JOINTS = []
DOC = None
PRINTDOC = None
PIN_COUNT = 0
COLORS = ['black', 'white', 'lightblue', 'darkblue', 'red']
RGB = [cad.BLACK, cad.WHITE, cad.CYAN, cad.BLUE, cad.RED]


def write_json(file, data):
    Path(file).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def box(x0, x1, y0, y1, z0, z1):
    return cad.mounts.box(x0, x1, y0, y1, z0, z1)


def shape(name):
    return DOC.getObject(name).Shape.copy()


def combine(shapes):
    shapes = [s for s in shapes if s is not None and not s.isNull() and s.Solids]
    if not shapes:
        return None
    if len(shapes) == 1:
        return shapes[0]
    return Part.makeCompound(shapes)


def fuse(shapes):
    shapes = [s for s in shapes if s is not None and not s.isNull() and s.Solids]
    return shapes[0].multiFuse(shapes[1:]).removeSplitter() if len(shapes)>1 else shapes[0]


def structural_curb(s):
    """Extend the outside-net-width wall through the full road slab depth.

    In the illustration CAD its bottom merely met the road's top along an
    edge. The added lower side strip provides a 6.6-mm-high bonded interface.
    """
    below = s.copy()
    below.translate(V(0, 0, -cad.THICK))
    return s.fuse(below).removeSplitter()


def clipped(s, tool):
    if s is None:
        return None
    b1, b2 = s.BoundBox, tool.BoundBox
    if not b1.intersect(b2):
        return None
    result = s.common(tool)
    return result if result.Solids and result.Volume > 1e-7 else None


def inlay(source, normal, plane, depth=.4, raised=.2):
    """Extrude actual glyph/line front faces; embed .4, raise .2 mm."""
    result = []
    for face in source.Faces:
        n = face.normalAt(0, 0)
        if n.dot(normal) > .999999:
            f = face.copy()
            f.translate(normal*(plane-depth-normal.dot(face.CenterOfMass)))
            result.append(f.extrude(normal*(depth+raised)))
    assert result
    return combine(result)


def palette(obj):
    rgb = obj.DesignColor[:3]
    return min(range(5), key=lambda i: sum((a-b)**2 for a, b in zip(rgb, RGB[i])))


def pin_joint(tag, center, direction, width_axis, offsets=(105, 135)):
    global PIN_COUNT
    cutters = []
    for coordinate in offsets:
        p = center+width_axis*coordinate
        cutters.append(Part.makeCylinder(1.65, 10.4, p-direction*5.2, direction))
    PIN_COUNT += 2
    JOINTS.append(dict(id=tag, centers_mm=[list(center+width_axis*v) for v in offsets],
                       axis=list(direction), socket_diameter_mm=3.3, half_depth_mm=5.2,
                       pin_diameter_mm=3, pin_length_mm=10, pins=2, bonding='PLA-compatible glue'))
    return combine(cutters)


def road_joint(tag, theta):
    derivative = (cad.height(theta+1e-5)-cad.height(theta-1e-5))/(2e-5)
    radial = V(math.cos(theta), math.sin(theta), 0)
    tangent = V(-math.sin(theta), math.cos(theta), derivative/120)
    tangent.normalize()
    return pin_joint(tag, V(cad.CX, cad.CY, cad.height(theta)-cad.THICK/2), tangent, radial)


def add_part(name, volumes, family, rotation=None, supports=False, note=''):
    volumes = [(c, s) for c, s in volumes if s is not None and s.Solids and s.Volume>1e-7]
    assert volumes, name
    for color, s in volumes:
        assert s.isValid() and all(v.isClosed() for v in s.Solids), (name, color)
        o = PRINTDOC.addObject('Part::Feature', name+'_'+COLORS[color])
        o.Shape = s
        o.addProperty('App::PropertyString', 'PrintPart').PrintPart = name
        o.addProperty('App::PropertyString', 'FilamentColor').FilamentColor = COLORS[color]
        o.addProperty('App::PropertyColor', 'DesignColor').DesignColor = RGB[color]
    # Independent validate_parts.py fuses every colour region and requires one
    # closed solid per mechanical part. This catches even one floating glyph.
    rotation = rotation or App.Rotation()
    transformed = []
    for color, s in volumes:
        t = s.copy()
        t.Placement = App.Placement(V(), rotation).multiply(t.Placement)
        transformed.append((color, t))
    meshes = [(color, s, MeshPart.meshFromShape(Shape=s, LinearDeflection=.035, AngularDeflection=.12, Relative=False))
              for color, s in transformed]
    # OCCT's spline control-pole bounding box can substantially overestimate
    # a trimmed curved piece. Bed placement must use actual mesh vertices.
    lo = [min(getattr(m.BoundBox, axis+'Min') for _, _, m in meshes) for axis in 'XYZ']
    hi = [max(getattr(m.BoundBox, axis+'Max') for _, _, m in meshes) for axis in 'XYZ']
    translation = V(*[-v for v in lo])
    resources = []
    for index, (color, s, mesh) in enumerate(meshes):
        mesh.translate(translation.x, translation.y, translation.z)
        # Check every constituent solid, since a colour volume can contain
        # several glyphs, hatch stripes or the two disconnected curb strips.
        assert not mesh.hasNonManifolds() and mesh.isSolid(), (name, color, 'mesh')
        f = OUT/f'{name}__{COLORS[color]}.stl'
        mesh.write(str(f))
        restored = Mesh.Mesh(str(f))
        assert restored.isSolid() and not restored.hasNonManifolds(), (name, color)
        resources.append(dict(color=color, file=str(f.relative_to(ROOT)), triangles=restored.CountFacets,
                              volume_mm3=s.Volume, mesh_volume_mm3=abs(restored.Volume)))
    dims = [b-a for a, b in zip(lo, hi)]
    assert min(dims[:2]) <= 220 and max(dims[:2]) <= 240 and dims[2] < 250, (name, dims)
    record = dict(name=name, family=family, supports=supports, dimensions_mm=dims,
                  rotation_quaternion=list(rotation.Q), translation_mm=list(translation),
                  volumes=resources, note=note)
    PARTS.append(record)
    print('PART', name, [round(v, 2) for v in dims], flush=True)
    return record


def deck_marks(k):
    z = P['floor_z'][k]
    colored = {i: [] for i in (1, 2, 3)}
    names = [o for o in DOC.Objects if ('DeliveryVisible' in o.PropertiesList and o.DeliveryVisible) and
             (o.Name.startswith(f'ParkingMarks_{k+1}F_') or o.Name.startswith(f'BayNumber_{k+1}_') or o.Name == f'ParkingP_{k+1}')]
    for obj in names:
        colored[palette(obj)].append(inlay(obj.Shape, V(0, 0, 1), z))
    result = [(color, fuse(ss)) for color, ss in colored.items() if ss]
    white = next(s for c, s in result if c == 1)
    # White bay outlines take precedence where the accessible blue band
    # overlaps their footprint in the illustrative CAD.
    result = [(c, s.cut(white).removeSplitter() if c == 3 else s) for c, s in result]
    return result


def foundation_and_decks():
    foundation = shape('Foundation_And_1F')
    all_marks = deck_marks(0)
    # Ground-floor label is integral with its front trim rather than floating.
    label = inlay(shape('FloorLabel_1'), V(0, -1, 0), 0.)
    all_marks.append((1, label))
    foundation = foundation.fuse(shape('FrontTrim_1F'))
    foundation = foundation.cut(combine([s for _, s in all_marks])).removeSplitter()
    # The four circular underside pads are separate flat prints. This removes
    # the 2-mm full-panel suspension that would otherwise require support.
    below = clipped(foundation, box(-30, 660, -130, 280, -3, 0))
    above = clipped(foundation, box(-30, 660, -130, 280, 0, 20))
    for index, solid in enumerate(below.Solids, 1):
        add_part(f'base_underpad_{index}', [(0, solid)], 'small')
    # Two ground-floor parts have the same paired pin interface as upper decks.
    cutters = pin_joint('deck_1F_y110', V(0, 110, 4.65), V(0, 1, 0), V(1, 0, 0), (60, 140))
    above = above.cut(cutters).removeSplitter()
    for ix, (x0, x1) in enumerate([(-10, 200), (200, 410), (410, 625)]):
        for iy, (y0, y1) in enumerate([(-130, 110), (110, 280)]):
            tool = box(x0, x1, y0, y1, 0, 20)
            main = clipped(above, tool)
            volumes = [(0, main)]+[(c, clipped(s, tool)) for c, s in all_marks] if ix == 0 else [(0, main)]
            add_part(f'foundation_{ix+1}_{iy+1}', volumes, 'foundation', note='Flat underside; glue straps across panel seams')
    for k in range(1, 4):
        z = P['floor_z'][k]
        marks = deck_marks(k)
        base = shape(f'Deck_{k+1}F').cut(combine([s for _, s in marks])).removeSplitter()
        pin = pin_joint(f'deck_{k+1}F_y110', V(0, 110, z-cad.THICK/2), V(0, 1, 0), V(1, 0, 0), (60, 140))
        base = base.cut(pin).removeSplitter()
        trim = shape(f'FrontTrim_{k+1}F')
        for iy, (y0, y1) in enumerate([(-2, 110), (110, 234)]):
            tool = box(-1, 201, y0, y1, z-8, z+1)
            volumes = [(0, clipped(base, tool))]+[(c, clipped(s, tool)) for c, s in marks]
            if iy == 0:
                volumes.append((k+1, trim))
            add_part(f'deck_{k+1}F_{"aisle" if iy==0 else "bays"}', volumes, 'deck')
    # Flat underside straps, separate so all six foundation panels lie flat.
    for i, (x, y, axis) in enumerate([(200, -45, 'x'), (200, 190, 'x'), (410, -45, 'x'), (410, 190, 'x'),
                                      (70, 110, 'y'), (300, 110, 'y'), (535, 110, 'y')], 1):
        s = box(x-30, x+30, y-10, y+10, -1.5, 0) if axis == 'x' else box(x-10, x+10, y-30, y+30, -1.5, 0)
        add_part(f'foundation_glue_strap_{i}', [(0, s)], 'small', note='60 x 20 x 1.5; glue underneath, centered on seam')


def road():
    hole_tools = shape('Road_BlindHole_Tools')
    landing_sources = []
    landing_tools = [[] for _ in range(4)]
    for k in range(3):
        a, b = math.pi+k*cad.TAU+cad.LANDING, math.pi+(k+1)*cad.TAU-cad.LANDING
        # Equal 77.5-degree pieces have narrower bed footprints than 90-degree
        # pieces and leave room for the colour prime tower.
        cuts = [a+(b-a)*i/4 for i in range(5)]
        joint_tools = []
        for j, theta in enumerate(cuts):
            tool = road_joint(f'road_turn{k+1}_joint{j}', theta)
            joint_tools.append(tool)
            if j == 0:
                landing_tools[k].append(tool)
            elif j == 4:
                landing_tools[k+1].append(tool)
        base = shape(f'RisingRoad_{k+1}').cut(hole_tools).cut(combine(joint_tools)).removeSplitter()
        curbs = combine([structural_curb(shape(f'InnerCurb_Rise_{k+1}')),
                         structural_curb(shape(f'OuterCurb_Rise_{k+1}'))])
        arrow_shapes = []
        for j in (1, 2):
            s = shape(f'RoadArrow_{k+1}_{j}')
            pieces = []
            # Add .4 mm down into the road; keep the CAD's original outline.
            for dz in (0, -.1, -.2, -.3, -.4):
                t = s.copy()
                t.translate(V(0, 0, dz))
                pieces.append(t)
            arrow_shapes.append(fuse(pieces))
        arrows = combine(arrow_shapes)
        base = base.cut(arrows).removeSplitter()
        for j, (lo, hi) in enumerate(zip(cuts, cuts[1:]), 1):
            mid = (lo+hi)/2
            # Exact radial cutting planes, large enough to contain the curbs.
            tool = cad.annulus(1, 200, lo, hi, -20, 300)
            volumes = [(0, clipped(base, tool)), (k+2, clipped(curbs, tool)), (1, clipped(arrows, tool))]
            slope = (cad.height(mid+1e-5)-cad.height(mid-1e-5))/(2e-5)/120
            normal = V(slope*math.sin(mid), -slope*math.cos(mid), 1)
            normal.normalize()
            tilt = App.Rotation(normal, V(0, 0, 1))
            rotate = App.Rotation(V(0, 0, 1), -math.degrees(mid)).multiply(tilt)
            add_part(f'road_{k+1}_{j}', volumes, 'road', rotate, True,
                     'Two Ø3 x 10 pins per seam plus glue; drive surface up; remove underside supports before assembly')
    for k, z in enumerate(P['floor_z']):
        base = shape(f'Landing_{k+1}F').fuse(shape(f'Bridge_{k+1}F')).removeSplitter()
        if landing_tools[k]:
            base = base.cut(combine(landing_tools[k])).removeSplitter()
        colored = {}
        for o in DOC.Objects:
            if (o.Name.startswith(f'InnerCurb_Landing_{k+1}_') or
                o.Name.startswith(f'OuterCurb_Landing_{k+1}_') or
                o.Name.startswith(f'BridgeCurb_{k+1}_') or
                (k == 0 and o.Name == 'Curb_1F_EndStop') or
                (k == 3 and o.Name == 'Curb_4F_FlushEnd')):
                colored.setdefault(palette(o), []).append(o.Shape)
        curb_volumes = []
        for c, ss in sorted(colored.items()):
            region = structural_curb(fuse(ss))
            if curb_volumes:
                # The straight bridge rail and the next colour's circular
                # rail overlap at their corner. Give the incoming colour
                # precedence so the multi-material volumes stay disjoint.
                region = region.cut(combine([s for _, s in curb_volumes])).removeSplitter()
            curb_volumes.append((c, region))
        # The 1F transverse stop overlaps the first millimetre of road;
        # remove that overlap from black to keep material volumes disjoint.
        base = base.cut(combine([s for _, s in curb_volumes])).removeSplitter()
        volumes = [(0, base)]+curb_volumes
        add_part(f'landing_{k+1}F', volumes, 'landing')


def supports_and_signs():
    # Purchased hardware is excluded explicitly by role.
    roles = {'original-column', 'post-standard', 'post-cap', 'post-base', 'spacer', 'arm', 'foot-pad'}
    for obj in DOC.Objects:
        if 'DeliveryVisible' not in obj.PropertiesList or not obj.DeliveryVisible or obj.DesignRole not in roles:
            continue
        rot = None
        if obj.DesignRole == 'arm':
            station = int(obj.Name[1])-1
            rot = App.Rotation(V(0, 0, 1), -P['support_angles_deg'][station])
        family = 'columns' if obj.DesignRole in ('original-column', 'post-standard', 'post-cap') else 'arms-feet' if obj.DesignRole in ('post-base', 'arm') else 'small'
        add_part(obj.Name, [(0, obj.Shape)], family, rot, obj.DesignRole == 'arm')
    # Rear wall and all sign faces are printed flat, outward faces up.
    flat = App.Rotation(V(1, 0, 0), -90)
    add_part('Garage_BackWall', [(0, shape('Garage_BackWall'))], 'wall', flat)
    letters = combine([inlay(shape(name), V(0, -1, 0), -226) for name in ('TopBillboard_Text1', 'TopBillboard_Text2')])
    board = shape('TopBillboard').cut(letters).removeSplitter()
    add_part('TopBillboard', [(0, board), (1, letters)], 'signs', flat)
    for name in ('BillboardPost_28', 'BillboardPost_151'):
        obj = DOC.getObject(name)
        add_part(name, [(palette(obj), obj.Shape)], 'signs', flat)
    side_letters = combine([inlay(shape(name), V(0, -1, 0), -63) for name in ('SideText_593', 'SideText_606')])
    panel = shape('SideSignBlue').cut(side_letters).removeSplitter()
    add_part('SideSignBlue', [(3, panel), (1, side_letters)], 'signs', flat)
    add_part('SideSignFrame', [(0, shape('SideSignFrame'))], 'sign-frame', flat, True)
    for k in (2, 3, 4):
        z = P['floor_z'][k-1]
        plate = box(157, 193, -2, -.6, z-17, z-1)
        ink = inlay(shape(f'FloorLabel_{k}'), V(0, -1, 0), 2)
        add_part(f'FloorLabel_{k}', [(0, plate.cut(ink)), (1, ink)], 'signs', flat,
                 note='Glue upper band of back surface to the front trim')
    for x in (29.5, 152.5):
        for z in (217, 248):
            add_part(f'billboard_glue_strap_{x}_{z}', [(0, box(x, x+12, 234, 236, z, z+30))], 'small', flat,
                     note='Glue to the back across wall/post or post/board seam')
    for i, x in enumerate((20, 87.5, 155), 1):
        bracket = box(x, x+25, 234, 242, 1.3, 3.3).fuse(box(x, x+25, 234, 236, 1.3, 16.3)).removeSplitter()
        add_part(f'backwall_angle_{i}', [(0, bracket)], 'small', App.Rotation(V(0, 1, 0), 90),
                 note='Glue to foundation and rear wall; place the 25-mm extrusion on bed')


def pins_and_coupon():
    # Two 25 x 70 x 6.6 halves reproduce the production horizontal pin sockets.
    for side, (x0, x1) in enumerate(((-25, 0), (0, 25)), 1):
        s = box(x0, x1, 0, 70, 0, 6.6)
        tools = [Part.makeCylinder(1.65, 10.4, V(-5.2, y, 3.3), V(1, 0, 0)) for y in (20, 50)]
        add_part(f'joint_coupon_{side}', [(0, s.cut(combine(tools)))], 'coupon')
    positions = [(V(*point), V(*joint['axis'])) for joint in JOINTS for point in joint['centers_mm']]
    for i in range(PIN_COUNT+2):
        if i < PIN_COUNT:
            center, direction = positions[i]
            s = Part.makeCylinder(1.5, 10, center-direction*5, direction)
            rotation = App.Rotation(direction, V(0, 0, 1))
        else:
            s = Part.makeCylinder(1.5, 10, V(680+(i-PIN_COUNT)*10, 0, 0))
            rotation = App.Rotation()
        add_part(f'alignment_pin_{i+1:02}', [(0, s)], 'coupon' if i >= PIN_COUNT else 'pins', rotation,
                 note='Ø3 x 10; remove brim and dry-fit before glue')


def main():
    global DOC, PRINTDOC
    start = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    before = sha(SOURCE)
    DOC = App.openDocument(str(SOURCE))
    PRINTDOC = App.newDocument('ParkingLotV1PrintParts')
    print('Foundation and split decks', flush=True)
    foundation_and_decks()
    print('Segmented road, pin sockets and integral coloured curbs', flush=True)
    road()
    print('Original support parts and flat-faced signs', flush=True)
    supports_and_signs()
    pins_and_coupon()
    PRINTDOC.recompute()
    PRINTDOC.saveAs(str(ROOT/'parking-lot-v1-print-parts.FCStd'))
    assert sha(SOURCE) == before
    data = dict(status='passed', source_cad=str(SOURCE.relative_to(ROOT.parents[2])), source_sha256=before,
                printed_assembly_scope='Complete new build; existing reusable column instances remain included',
                material='PLA', layer_height_mm=.2, nozzle_mm=.4,
                source_unchanged=True, hardware_excluded=True,
                new_design=dict(road_segments=12, road_landings=4, foundation_panels=6, upper_deck_halves=6,
                                road_deck_pin_joints=len(JOINTS), production_alignment_pins=PIN_COUNT,
                                coupon_pins=2, joint_socket_diameter_mm=3.3, pin_diameter_mm=3,
                                markings='0.4 mm embedded + 0.2 mm raised multi-material inlays',
                                curbs='Extend through 6.6-mm slab depth for full-height lateral attachment; clear road stays 70 mm'),
                parts=PARTS, joints=JOINTS, build_seconds=time.time()-start,
                physical_fit_tested=False)
    write_json(ROOT/'parts.json', data)
    print('PASS', len(PARTS), 'parts;', PIN_COUNT, 'production pins; source CAD unchanged;', round(time.time()-start, 1), 'seconds', flush=True)


if __name__ == '__main__':
    main()
