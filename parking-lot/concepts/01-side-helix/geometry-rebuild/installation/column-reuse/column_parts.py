"""Garage-column reuse: real existing solids, 6.6-mm arm tabs, height-set feet.

Local station X points radially out, Y tangent; local road top is Z=0.
The root tab is outside the outer curb. The lower collar bears its underside;
the original through-pin enters the socket in the next standard segment.
"""
import math
from pathlib import Path
import mount_parts as old
from mount_parts import (App, Part, V, BLACK, STEEL, GOLD, box, cyl, bolt,
                         washer, record, transformed, base_pad, foot_hardware)

ROOT = Path(__file__).resolve().parent
TAB_BOTTOM, TAB_TOP = -11.6, -5.0
SEGMENT_HEIGHT, TAB_THICKNESS, CAP_HEIGHT = 56.4, 6.6, 33.0
_shapes = {}


def reference(top=False):
    key = 'garage-top-cap.brep' if top else 'garage-standard-column.brep'
    if key not in _shapes:
        s = Part.Shape(); s.read(str(ROOT/'reference'/key))
        assert s.isValid() and len(s.Solids) == 1
        _shapes[key] = s
    return _shapes[key].copy()


def garage_segment(z, top=False):
    s = reference(top); s.translate(V(0, 0, z)); return s


def foot_segment(first_road_height):
    """Custom only below the first arm; preserves the original upper interface."""
    z, seat = 1.3, first_road_height+TAB_BOTTOM
    assert seat-z >= 7.0
    s = cyl(7, z, seat).fuse(cyl(10, seat-4, seat))
    s = s.fuse(Part.makeCone(7, 10, 3, V(0, 0, seat-7)))
    s = s.fuse(cyl(3, seat, seat+9.6)).fuse(cyl(14, z, 4.3))
    for v in [-10.5, 10.5]: s = s.cut(cyl(1.7, 0, 6, 0, v))
    return s.removeSplitter()


def post_parts(road_heights):
    out = [record('height_set_foot', foot_segment(road_heights[0]), 'post-base')]
    for k in range(2):
        out.append(record(f'original_standard_segment_{k+1}',
                          garage_segment(road_heights[k]+TAB_TOP), 'post-standard'))
    out.append(record('original_top_cap', garage_segment(road_heights[2]+TAB_TOP, True), 'post-cap'))
    return out


def sign_post_parts():
    # Original 8-mm garage base datum, carried by a short bolted adapter.
    adapter = cyl(7, 1.3, 8).fuse(cyl(14, 1.3, 4.3)).fuse(cyl(3, 8, 11))
    for v in [-10.5, 10.5]: adapter = adapter.cut(cyl(1.7, 0, 6, 0, v))
    out = [record('sign_base_adapter', adapter.removeSplitter(), 'post-base')]
    for k in range(3):
        z = 8+63*k
        out.append(record(f'original_standard_segment_{k+1}', garage_segment(z), 'post-standard'))
        out.append(record(f'sign_spacer_{k+1}', cyl(10, z+56.4, z+63).cut(cyl(3.25, z+55, z+64)), 'spacer'))
    out.append(record('original_top_cap', garage_segment(197, True), 'post-cap'))
    return out


def upright(road_heights, top=None):
    parts = post_parts(road_heights) if road_heights else sign_post_parts()
    return Part.makeCompound([p['shape'] for p in parts])


def station(theta, height):
    tab = cyl(10, TAB_BOTTOM, TAB_TOP)
    arm = old.arm_loft(theta, height)
    # The tilted beam must not cut into the original collar underneath the tab.
    arm = arm.cut(cyl(10, -35, TAB_BOTTOM)).fuse(tab)
    arm = arm.cut(cyl(3.25, TAB_BOTTOM-1, TAB_TOP+1))
    road = old.road_patch(theta, height)
    hardware = []
    for i, r in enumerate([110, 145]):
        derivative = (height(theta+1e-5)-height(theta-1e-5))/(2e-5)
        slope = derivative/r; n = V(0, -slope, 1); n.normalize()
        p = V(r-169, 0, -6.6)
        arm = arm.cut(Part.makeCylinder(1.7, 18, p-n*12, n))
        road = road.cut(Part.makeCylinder(2, 5, p, n))
        insert = Part.makeCylinder(2.3, 4, p, n).cut(Part.makeCylinder(1.5, 4, p, n))
        under = p-n*(5/math.sqrt(1+slope*slope)+.5)
        hardware += [record(f'road_insert_{i+1}', insert, 'insert', GOLD, (0, 0, 17)),
                     record(f'road_washer_{i+1}', washer(under, n), 'road-washer', STEEL, (0, 0, -18)),
                     record(f'road_bolt_{i+1}', bolt(under, n, 10), 'road-bolt', STEEL, (0, 0, -18))]
    return [record('bearing_tab_arm', arm.removeSplitter(), 'arm'),
            record('road_patch', road, 'road', (.18, .60, .78), (0, 0, 27))]+hardware


def interference_checks(parts, post, road_height):
    arm = next(p['shape'] for p in parts if p['role'] == 'arm')
    local = post.copy(); local.translate(V(0, 0, -road_height))
    values = dict(arm_column_overlap_mm3=arm.common(local).Volume,
                  arm_to_collar_distance_mm=arm.distToShape(local)[0])
    assert values['arm_column_overlap_mm3'] < 1e-5, values
    assert values['arm_to_collar_distance_mm'] < 1e-6, values
    return values
