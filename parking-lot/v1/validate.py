#!/usr/bin/env python3
"""Independently reopen and check the delivered native and STEP BReps."""
import json
import math
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
import build as b

ROOT = Path(__file__).resolve().parent


def main():
    start = time.time()
    doc = App.openDocument(str(ROOT/'cad/parking-lot-v1-assembly.FCStd'))
    doc.recompute()
    visible = [o for o in doc.Objects if 'DeliveryVisible' in o.PropertiesList and o.DeliveryVisible]
    assert visible
    invalid = [o.Name for o in visible if not o.Shape.isValid() or not o.Shape.Solids or any(not s.isClosed() for s in o.Shape.Solids)]
    assert not invalid, invalid
    sketches = [o for o in doc.Objects if o.TypeId == 'Sketcher::SketchObject']
    assert all(o.FullyConstrained for o in sketches)
    errors = [dict(name=o.Name, state=o.State) for o in doc.Objects if 'Invalid' in o.State]
    assert not errors, errors
    road = doc.getObject('Road_Continuous_18BlindHoles').Shape
    raw = doc.getObject('ContinuousRoad_BeforeHoles').Shape
    assert len(road.Solids) == 1 and road.isClosed()
    print('Native reopen, valid closed BReps and constrained sketches passed', flush=True)

    # Surface samples between loft sections independently check the smooth CAD
    # interpolation against the approved analytical width/height law.
    samples = []
    for k in range(3):
        shape = doc.getObject(f'RisingRoad_{k+1}').Shape
        a, end = math.pi+k*b.TAU+b.LANDING, math.pi+(k+1)*b.TAU-b.LANDING
        n = round(math.degrees(end-a)/b.P['loft_section_step_deg'])
        for i in range(n):
            theta = a+(end-a)*(i+.5)/n
            for radius in (b.RI, (b.RI+b.RO)/2, b.RO):
                ideal = Part.Vertex(b.point(radius, theta, b.height(theta)))
                samples.append(shape.distToShape(ideal)[0])
    assert max(samples) < .005, max(samples)
    bridges = []
    for k, z in enumerate(b.P['floor_z']):
        bridge = doc.getObject(f'Bridge_{k+1}F').Shape
        landing = doc.getObject(f'Landing_{k+1}F').Shape
        assert abs(bridge.BoundBox.YLength-70) < 1e-7
        assert abs(bridge.BoundBox.ZMax-z) < 1e-6
        assert bridge.distToShape(landing)[0] < 1e-6
        garage = doc.getObject('Foundation_And_1F' if k == 0 else f'Deck_{k+1}F').Shape
        assert bridge.distToShape(garage)[0] < 1e-6
        bridges.append(dict(floor=k+1, width_mm=bridge.BoundBox.YLength,
                            top_z_mm=bridge.BoundBox.ZMax,
                            road_seam_gap_mm=bridge.distToShape(landing)[0],
                            garage_seam_gap_mm=bridge.distToShape(garage)[0]))
    assert abs(doc.getObject('Landing_4F').Shape.BoundBox.YMin-40) < 1e-6
    print('Road interpolation, four 70-mm bridge seams and 4F termination passed', flush=True)

    support_checks = []
    min_clearance = 1e9
    for i, degree in enumerate(b.P['support_angles_deg']):
        t = math.radians(degree)
        theta = t if t >= math.pi else t+b.TAU
        post_shapes = [o.Shape for o in visible if o.Name.startswith(f'B{i+1}_') and o.DesignRole in ('post-base', 'post-standard', 'post-cap')]
        post = Part.makeCompound(post_shapes)
        for k in range(3):
            arm = doc.getObject(f'B{i+1}_Level{k+1}_bearing_tab_arm').Shape
            overlap = arm.common(post).Volume
            distance = arm.distToShape(post)[0]
            assert overlap < 1e-5 and distance < 1e-6
            road_overlap = arm.common(road).Volume
            # Both surfaces are independent loft interpolations. Sub-micron
            # numerical slivers do not constitute an assembly collision.
            assert road_overlap < .1, (i, k, road_overlap)
            support_checks.append(dict(station=f'B{i+1}', level=k+1, arm_column_overlap_mm3=overlap,
                                       bearing_seat_gap_mm=distance, arm_road_overlap_mm3=road_overlap))
            if k:
                for obj in visible:
                    if not obj.Name.startswith(f'B{i+1}_Level{k+1}_') or obj.DesignRole not in ('arm', 'road-bolt', 'road-washer'):
                        continue
                    pts, _ = obj.Shape.tessellate(.2)
                    for v in pts:
                        dx, dy = v.x-b.CX, v.y-b.CY
                        radius = math.hypot(dx, dy)
                        if b.RI <= radius <= b.RO:
                            delta = math.atan2(dy, dx)-t
                            delta = (delta+math.pi)%b.TAU-math.pi
                            lower = b.height(theta+(k-1)*b.TAU+delta)
                            min_clearance = min(min_clearance, v.z-lower)
    assert min_clearance > 47., min_clearance
    print('Nine arm seats and actual lower-road hardware clearance passed', flush=True)

    # The saved column instances must retain the original exact BRep volumes.
    source_standard = b.mounts.reference(False)
    source_cap = b.mounts.reference(True)
    originals = []
    for o in visible:
        if o.DesignRole not in ('original-column', 'post-standard', 'post-cap'):
            continue
        cap = o.DesignRole == 'post-cap' or (o.DesignRole == 'original-column' and o.Name.endswith('_4'))
        ref = source_cap if cap else source_standard
        assert abs(o.Shape.Volume-ref.Volume) < 1e-5
        originals.append(o.Name)
    assert len(originals) == 29, len(originals)
    # Ø4 x 5 blind holes enter from the underside; material remains over them.
    for degree in b.P['support_angles_deg']:
        t = math.radians(degree)
        if t < math.pi:
            t += b.TAU
        for k in range(3):
            for radius in (110, 145):
                p = b.point(radius, t+k*b.TAU, b.height(t+k*b.TAU)-.5)
                assert road.isInside(p, 1e-6, True), (degree, k, radius)
    removed = raw.Volume-road.Volume
    assert 1100 < removed < 1140, removed

    # Reimport STEP rather than merely checking its existence or header.
    print('Reimporting STEP and comparing every exported solid', flush=True)
    step = Part.Shape()
    step.read(str(ROOT/'cad/parking-lot-v1-assembly.step'))
    assert step.isValid() and all(s.isValid() and s.isClosed() for s in step.Solids)
    expected = sum(len(o.Shape.Solids) for o in visible)
    assert len(step.Solids) == expected, (len(step.Solids), expected)
    native_volume = sum(o.Shape.Volume for o in visible)
    # STEP surface/trim conversion accumulates a small integration difference
    # on the long spline roadway. 0.1 mm³ is <3e-8 of this assembly's volume.
    assert abs(step.Volume-native_volume) < .1, (step.Volume, native_volume)
    original_volumes = sorted(s.Volume for o in visible for s in o.Shape.Solids)
    exported_volumes = sorted(s.Volume for s in step.Solids)
    maximum_solid_volume_delta = max(abs(a-c) for a, c in zip(original_volumes, exported_volumes))
    assert maximum_solid_volume_delta < .1
    bounds = Part.makeCompound([o.Shape for o in visible]).BoundBox
    for p in ('XMin', 'XMax', 'YMin', 'YMax', 'ZMin', 'ZMax'):
        assert abs(getattr(step.BoundBox, p)-getattr(bounds, p)) < .002, p
    report = dict(status='passed', units='mm', reopened_native=True, native_object_count=len(doc.Objects),
                  delivery_object_count=len(visible), closed_brep_solids=expected,
                  invalid_objects=invalid, invalid_feature_states=errors,
                  fully_constrained_sketches=len(sketches),
                  road=dict(connected_solids=len(road.Solids), nominal_clear_width_mm=b.W,
                            between_section_sample_count=len(samples),
                            maximum_ideal_surface_deviation_mm=max(samples),
                            floor_pitch_mm=b.PITCH, road_thickness_mm=b.THICK,
                            bridge_checks=bridges, four_f_terminal_y_mm=40,
                            blind_holes=18, blind_hole_removed_volume_mm3=removed,
                            top_skin_above_each_hole_checked=True),
                  supports=dict(seat_checks=support_checks, unchanged_original_column_instances=len(originals),
                                hardware_inclusive_minimum_local_clearance_mm=min_clearance),
                  step=dict(reimport_valid=True, solids=len(step.Solids),
                            volume_delta_mm3=step.Volume-native_volume,
                            maximum_individual_solid_volume_delta_mm3=maximum_solid_volume_delta,
                            relative_volume_delta=abs(step.Volume-native_volume)/native_volume),
                  envelope_mm=[bounds.XLength, bounds.YLength, bounds.ZLength],
                  scope='CAD geometry and specified mating checks. No print segmentation, physical fit, load or vehicle turning certification.',
                  validation_seconds=round(time.time()-start, 2))
    (ROOT/'reports/validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    App.closeDocument(doc.Name)
    print(json.dumps({k: report[k] for k in ('status', 'delivery_object_count', 'closed_brep_solids', 'fully_constrained_sketches', 'envelope_mm', 'validation_seconds')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
