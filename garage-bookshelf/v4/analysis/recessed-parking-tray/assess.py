"""Read-only recessed parking-tray feasibility study, 2026-10-25.

Uses exact current CAD shapes, including existing markings and corner fillets.
Pockets exist only in memory. No source assembly or print file is saved.
Run with FreeCAD's bundled Python. Reuses the earlier study's verified mesh
parser, C3D10 gravity integration and CalculiX result reader, not its old geometry.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
V4 = ROOT.parents[1]
# Freeze the evaluated pre-retrofit revision after applying the design to CAD.
MODEL = V4 / 'backups' / '2026-10-25-before-parking-recesses.FCStd'
BIN = Path('/Applications/FreeCAD.app/Contents/Resources/bin')
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
import numpy as np

spec = importlib.util.spec_from_file_location('previous_deck_fem',
    ROOT.parent / 'parking-deck-bending' / 'calculate.py')
fem = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fem)

E, NU, RHO = 1000.0, 0.35, 1.24e-9
POCKET_W, POCKET_L, POCKET_R = 40.6, 80.6, 2.3
TRAY_W, TRAY_L, TRAY_T = 40.0, 80.0, 2.0
BAY_Y = 86.5
CASES = {
    'baseline': (2, 0.0, 'standard'),
    'depth1': (2, 1.0, 'standard'),
    'depth1p2': (2, 1.2, 'standard'),
    'depth1p6': (2, 1.6, 'standard'),
    'depth2': (2, 2.0, 'standard'),
    'fullbay2': (2, 2.0, 'full_bay_interior'),
    'twobay1p6': (1, 1.6, 'standard'),
    'compensated1p6': (2, 1.6, 'compensated'),
    'flatthick1p6': (2, 1.6, 'flat_thickened'),
}


def value(doc, alias):
    return fem.evaluate(doc, alias)


def run(command, folder, name):
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2')
    with (folder / name).open('w') as out:
        p = subprocess.run([str(x) for x in command], cwd=folder, env=env,
            stdout=out, stderr=subprocess.STDOUT, timeout=300)
    log = (folder / name).read_text()
    if p.returncode or '*ERROR' in log:
        raise RuntimeError(f'{name}: {log[-5000:]}')


def rounded_box(x, y, width, length, radius, z, height):
    pieces = [Part.makeBox(width-2*radius, length, height,
                  App.Vector(x+radius, y, z)),
              Part.makeBox(width, length-2*radius, height,
                  App.Vector(x, y+radius, z))]
    for cx in (x+radius, x+width-radius):
        for cy in (y+radius, y+length-radius):
            pieces.append(Part.makeCylinder(radius, height, App.Vector(cx, cy, z)))
    return pieces[0].multiFuse(pieces[1:]).removeSplitter()


def geometry(doc, name):
    level, depth, style = CASES[name]
    count = 2 if level == 1 else 3
    body = doc.getObject(f'garage_deck_{level}_Body')
    before = body.Shape.copy()
    width, length, thickness = [value(doc, k) for k in
        ('DeckWidth', 'DeckDepth', 'DeckThickness')]
    sx = width / 199.6
    pitch = 144.0 / count * sx
    centers = [((27.8+(i+.5)*144.0/count)*sx, BAY_Y) for i in range(count)]
    pw = pitch - 2.4 if style == 'full_bay_interior' else POCKET_W
    pl = 86.0 if style == 'full_bay_interior' else POCKET_L
    tools = []
    if depth:
        for cx, cy in centers:
            tool = rounded_box(cx-pw/2, cy-pl/2, pw, pl, POCKET_R,
                               thickness-depth, depth+.1)
            # Small central finger relief, retaining substantial front shoulders.
            notch = Part.makeBox(12, 4.5, depth+.1,
                App.Vector(cx-6, cy-pl/2-4, thickness-depth))
            tools.append(tool.fuse(notch).removeSplitter())
        cut = tools[0].multiFuse(tools[1:]).removeSplitter()
        original = before
        if style == 'compensated':
            pads = []
            for tool in tools:
                pad = tool.copy()
                pad.translate(App.Vector(0, 0, -thickness))
                pads.append(pad)
            original = before.multiFuse(pads).removeSplitter()
        elif style == 'flat_thickened':
            blank = doc.garage_deck_3_Body.Shape.copy()
            blank.translate(App.Vector(0, 0, -depth))
            slab = Part.makeBox(width+2, length+2, depth+.05,
                               App.Vector(-1, -1, -depth))
            pad = blank.common(slab)
            original = before.fuse(pad).removeSplitter()
        shape = original.cut(cut).removeSplitter()
    else:
        shape = before
    assert shape.isValid() and len(shape.Solids) == 1
    supports = [(value(doc, x)-.2, value(doc, y)-.2) for x, y in
        [('ColumnInset', 'ColumnInset'), ('ColumnX2', 'ColumnInset'),
         ('ColumnInset', 'ColumnY2'), ('ColumnX2', 'ColumnY2')]]
    differences = []
    for cx, cy in supports:
        cylinder = Part.makeCylinder(11, thickness, App.Vector(cx, cy, 0))
        diff = abs(before.common(cylinder).Volume-shape.common(cylinder).Volume)
        assert diff < 1e-6, diff
        differences.append(diff)
    # Probe true thickness at pocket floors, independently of the boolean volume.
    floor_heights = []
    for cx, cy in centers:
        ray = Part.makeLine(App.Vector(cx, cy, -3), App.Vector(cx, cy, 6))
        floor_heights.append(max(v.Point.z for v in shape.common(ray).Vertexes))
    if depth:
        assert all(abs(z-(thickness-depth)) < 1e-6 for z in floor_heights)
    return shape, dict(name=name, source_body=body.Name, bay_count=count,
        depth_mm=depth, pocket_style=style,
        pocket_size_mm=[pw, pl], corner_radius_mm=POCKET_R,
        finger_relief_mm=[12, 4], bay_centers_xy_mm=centers,
        source_volume_mm3=before.Volume, removed_volume_mm3=before.Volume-shape.Volume,
        solid_volume_mm3=shape.Volume, source_faces=len(before.Faces),
        trial_faces=len(shape.Faces), floor_heights_mm=floor_heights,
        pocket_floor_thickness_mm=thickness if style in ('compensated', 'flat_thickened') else thickness-depth,
        underside_local_extension_mm=depth if style == 'compensated' else 0,
        underside_full_extension_mm=depth if style == 'flat_thickened' else 0,
        minimum_thickness_mm=thickness if style == 'flat_thickened' else min(thickness-.4,
            thickness if style == 'compensated' else thickness-depth),
        four_support_keepout_radius_mm=11,
        support_keepout_volume_differences_mm3=differences,
        pocket_pitch_x_mm=pitch,
        minimum_web_between_pockets_mm=pitch-pw if depth else None), supports, centers


def surface_height(shape, x, y):
    ray = Part.makeLine(App.Vector(x, y, -1), App.Vector(x, y, 6))
    return max(v.Point.z for v in shape.common(ray).Vertexes)


def patch_load(nodes, shape, points):
    result, patches = {}, []
    for x, y in points:
        z = surface_height(shape, x, y)
        ids = [n for n, p in nodes.items()
            if abs(p[2]-z) < 1e-5 and (p[0]-x)**2+(p[1]-y)**2 <= 4**2]
        assert len(ids) >= 3, (x, y, z, len(ids))
        for n in ids:
            result[n] = result.get(n, 0) - 1/len(points)/len(ids)
        patches.append(dict(center_mm=[x, y, z], nodes=len(ids)))
    assert abs(sum(result.values())+1) < 1e-10
    return result, patches


def input_file(nodes, elements, shape, supports, centers, support_z=0):
    groups = []
    for x, y in supports:
        ids = [n for n, p in nodes.items() if abs(p[2]-support_z) < 1e-5
            and (p[0]-x)**2+(p[1]-y)**2 <= 10**2+1e-5]
        assert len(ids) >= 5
        groups.append(ids)
    a = min(groups[0], key=lambda n: (nodes[n][0]-supports[0][0])**2
        +(nodes[n][1]-supports[0][1])**2)
    b = min(groups[1], key=lambda n: (nodes[n][0]-supports[1][0])**2
        +(nodes[n][1]-supports[1][1])**2)
    points = [(cx+dx, cy+dy) for cx, cy in centers
              for dx in (-10, 10) for dy in (-20, 20)]
    payload, patches = patch_load(nodes, shape, points)
    middle = (value_global['DeckWidth']/2, BAY_Y)
    central, central_patch = patch_load(nodes, shape, [middle])
    lines = ['*HEADING', 'Current v4 recessed tray feasibility, effective PLA',
             '*NODE,NSET=ALLN']
    lines += [f'{n},'+','.join(f'{v:.10g}' for v in p) for n, p in nodes.items()]
    lines += ['*ELEMENT,TYPE=C3D10,ELSET=ALL']
    lines += [str(e)+','+','.join(map(str, el)) for e, el in elements.items()]
    lines += ['*MATERIAL,NAME=EFFECTIVE_PLA', '*ELASTIC', f'{E},{NU}',
              '*DENSITY', str(RHO), '*SOLID SECTION,ELSET=ALL,MATERIAL=EFFECTIVE_PLA',
              '*BOUNDARY']
    fixed = sorted(set(sum(groups, [])))
    lines += [f'{n},3,3,0' for n in fixed]
    lines += [f'{a},1,2,0', f'{b},2,2,0']
    for case, force in [('self', None), ('payload', payload), ('centre', central)]:
        lines += ['*STEP', '*STATIC', '*DLOAD,OP=NEW',
                  f'ALL,GRAV,{9810 if case == "self" else 0},0,0,-1']
        if force:
            lines += ['*CLOAD,OP=NEW']+[f'{n},3,{v:.12g}' for n, v in sorted(force.items())]
        lines += ['*NODE PRINT,NSET=ALLN', 'U,RF', '*END STEP']
    return '\n'.join(lines)+'\n', fixed, dict(
        support_node_counts=list(map(len, groups)),
        distributed_contact_patches=patches, central_patch=central_patch,
        no_stiffness_credit_for_unbonded_trays=True)


def solve(doc, name, size, folder):
    folder.mkdir()
    shape, geo, supports, centers = geometry(doc, name)
    shape.exportBrep(str(folder/'deck.brep'))
    print('MESH', name, size, 'faces', len(shape.Faces), flush=True)
    # Linear geometric edges with quadratic displacement interpolation avoid
    # inverted curved C3D10 elements at the short underside transition edges.
    # CAD/mesh volume error is independently checked after solving.
    mesh_options = ['-setnumber', 'Mesh.SecondOrderLinear', '1'] if name == 'compensated1p6' else []
    run([BIN/'gmsh', folder/'deck.brep', '-3', '-order', '2',
        '-clmin', str(size), '-clmax', str(size), '-format', 'inp',
        '-o', folder/'mesh.inp', '-v', '2']+mesh_options, folder, 'gmsh.log')
    nodes, elements = fem.read_mesh(folder/'mesh.inp')
    print('SOLVE', name, size, len(nodes), len(elements), flush=True)
    support_z = -geo['depth_mm'] if geo['pocket_style'] == 'flat_thickened' else 0
    inp, fixed, setup = input_file(nodes, elements, shape, supports, centers, support_z)
    (folder/'case.inp').write_text(inp)
    run([BIN/'ccx', '-i', 'case'], folder, 'ccx.log')
    data = fem.read_results(folder/'case.dat')
    ids = list(nodes)
    displacement = [np.array([step['u'][n][2] for n in ids]) for step in data]
    forces, volume = fem.gravity_nodal_forces(nodes, elements)
    volume_error = abs(volume-shape.Volume)/shape.Volume
    assert volume_error < .002, volume_error
    reactions = [sum(step['rf'][n][2] for n in fixed) for step in data]
    reactions[0] -= sum(forces[n] for n in fixed)
    weight = shape.Volume*RHO*9810
    equilibrium_error = abs(reactions[0]-weight)/weight
    assert equilibrium_error < .002, (reactions, weight)
    assert all(abs(r-1) < .003 for r in reactions[1:]), reactions
    scenarios = []
    for mass, arrangement, modulus in [
        (60, 'distributed', 1000), (110, 'distributed', 1000),
        (110, 'distributed', 500), (330, 'central_total', 1000),
        (660, 'central_total', 500)]:
        total_g = mass*len(centers) if arrangement == 'distributed' else mass
        k = 1 if arrangement == 'distributed' else 2
        uz = (displacement[0]+total_g/1000*9.81*displacement[k])*E/modulus
        i = int(np.argmin(uz))
        scenarios.append(dict(payload_or_per_car_including_tray_g=mass,
            total_payload_g=total_g, arrangement=arrangement,
            E_effective_MPa=modulus, max_downward_mm=float(-uz.min()),
            max_upward_mm=float(max(0, uz.max())),
            max_downward_xyz_mm=list(nodes[ids[i]])))
    result = dict(geometry=geo, mesh_size_mm=size, nodes=len(nodes),
        quadratic_tetrahedra=len(elements), solid_self_mass_upper_bound_g=shape.Volume*.00124,
        quadratic_geometry_edges='linear midsides' if mesh_options else 'curved',
        self_only_max_downward_mm=float(-displacement[0].min()),
        reactions_N=reactions, volume_relative_error=volume_error,
        self_weight_equilibrium_relative_error=equilibrium_error,
        setup=setup, scenarios=scenarios)
    print('RESULT', json.dumps(dict(name=name, mesh=size,
        normal_mm=scenarios[1]['max_downward_mm'],
        sensitivity_mm=scenarios[-1]['max_downward_mm'])), flush=True)
    return result


def analytical_checks():
    depths = (1, 1.2, 1.6, 2)
    rows = []
    for d in depths:
        rows.append(dict(depth_mm=d, floor_mm=5-d,
            local_strip_bending_rigidity_ratio=((5-d)/5)**3,
            additional_engraving_0p4_floor_mm=5-d-.4,
            ideal_vertical_relative_escape_velocity_m_per_s=math.sqrt(2*9.81*d/1000),
            nominal_2g_wall_contact_pressure_MPa=(.11*2*9.81)/(10*max(d-.3, .01)),
            tray_surface_above_deck_mm=TRAY_T-d,
            vertical_travel_to_clear_square_wall_mm=d))
    # Quasi-static rigid-body rocking about upper pocket edge: h and footprint
    # are sensitivity assumptions, not vehicle measurements or an impact rating.
    rocking = []
    for width in (30, 40):
        for center_height in (15, 20, 25):
            rocking.append(dict(support_width_mm=width,
                COM_height_above_floor_mm=center_height,
                ideal_lateral_rocking_threshold_g=(width/2)/(center_height-1.6)))
    return dict(tray_example_mm=[TRAY_W, TRAY_L, TRAY_T],
        tray_solid_plate_mass_upper_bound_g=TRAY_W*TRAY_L*TRAY_T*.00124,
        car_plus_tray_mass_assumed_g=110, depth_comparison=rows,
        friction_independent_vertical_wall_contact_nominal_width_mm=10,
        nominal_wall_engagement_loss_allowance_mm=.3,
        rocking_sensitivity_only=rocking,
        vertical_detachment_condition='deck downward acceleration exceeds g; hopping height then depends on pulse duration and relative velocity',
        impact_ejection_is_not_predicted_by_static_FEA=True)


def main():
    global value_global
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', type=float, default=6)
    parser.add_argument('--cases', default=','.join(CASES))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    digest = hashlib.sha256(MODEL.read_bytes()).hexdigest()
    assert digest == '2a3f10a9a4c7d0544a9b2cfe2b4e5dfd48f4dd970dbd66d1bd2bd66c1b9191ce'
    doc = App.openDocument(str(MODEL))
    value_global = {k: value(doc, k) for k in
        ('DeckWidth', 'DeckDepth', 'DeckThickness', 'DeckPitch')}
    output = ROOT/f'results-mesh{args.size:g}.json'
    result = dict(status='partial', source_cad=str(MODEL), source_sha256=digest,
        source_cad_modified=False, dimensions_mm=value_global,
        material_assumptions=dict(E_effective_MPa=E, poisson_ratio=NU,
            density_g_per_cm3=1.24, homogenized=True, actual_infill_not_modeled=True),
        supports='four existing collar footprints, vertical translation fixed; minimal in-plane constraints',
        analytical=analytical_checks(), cases=[])
    if args.resume and output.exists():
        old = json.loads(output.read_text())
        assert old['source_sha256'] == digest
        assert old['dimensions_mm'] == value_global
        assert old['material_assumptions'] == result['material_assumptions']
        result['cases'] = old['cases']
    try:
        with tempfile.TemporaryDirectory(prefix='v4-recess-study-') as tmp:
            for name in args.cases.split(','):
                assert name in CASES, name
                if args.refresh:
                    result['cases'] = [case for case in result['cases']
                        if case['geometry']['name'] != name]
                if any(case['geometry']['name'] == name for case in result['cases']):
                    print('REUSE', name, args.size, flush=True)
                    continue
                result['cases'].append(solve(doc, name, args.size, Path(tmp)/name))
                output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        result['status'] = 'numerical_checks_passed'
    finally:
        App.closeDocument(doc.Name)
        assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == digest
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
