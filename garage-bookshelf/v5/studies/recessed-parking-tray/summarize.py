"""Summarize and cross-check the saved recessed-tray numerical studies."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parents[1]/'build/studies/recessed-parking-tray'


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Summarize saved or regenerated study data without changing saved evidence')
    parser.add_argument('--input', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args=parser.parse_args()
    data=args.input.resolve()
    destination=args.output.resolve()
    if not destination.is_relative_to((ROOT.parents[1]/'build').resolve()):
        parser.error('--output must be under v5/build/')
    destination.mkdir(parents=True, exist_ok=True)
    coarse = json.loads((data/'results-mesh6.json').read_text())
    fine = json.loads((data/'results-mesh4.json').read_text())
    assert coarse['status'] == fine['status'] == 'numerical_checks_passed'
    model = ROOT/'reference/2026-10-25-before-parking-recesses.FCStd'
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    assert coarse['source_sha256'] == fine['source_sha256'] == digest
    a = {c['geometry']['name']: c for c in coarse['cases']}
    b = {c['geometry']['name']: c for c in fine['cases']}
    rows, convergence = [], []
    for name, c in a.items():
        best = b.get(name, c)
        g = best['geometry']
        scenario = best['scenarios']
        depth = g['depth_mm']
        compensated = g['pocket_style'] in ('compensated', 'flat_thickened')
        floor = 5 if compensated else 5-depth
        weight = best['solid_self_mass_upper_bound_g']/1000*9.81
        normal_force = scenario[1]['total_payload_g']/1000*9.81
        # A nominal strip estimate, not a four-support local peak stress or rating.
        nominal_section_modulus = 158.6*floor**2/6
        normal_moment = normal_force*172/4+weight*172/8
        extreme_moment = .660*9.81*172/4+weight*172/8
        rows.append(dict(name=name, pocket_depth_mm=depth,
            pocket_floor_thickness_mm=floor,
            underside_extension_mm=depth if compensated else 0,
            underside_extension_type=g['pocket_style'] if compensated else 'none',
            source_mesh_mm=best['mesh_size_mm'],
            normal_payload_g=scenario[1]['total_payload_g'],
            normal_E1000_max_downward_mm=scenario[1]['max_downward_mm'],
            normal_E500_max_downward_mm=scenario[2]['max_downward_mm'],
            central330_E1000_max_downward_mm=scenario[3]['max_downward_mm'],
            central660_E500_max_downward_mm=scenario[4]['max_downward_mm'],
            meets_chosen_0p5mm_sensitivity_target=scenario[4]['max_downward_mm'] <= .5,
            solid_self_mass_upper_bound_g=best['solid_self_mass_upper_bound_g'],
            nominal_strip_normal_stress_MPa=normal_moment/nominal_section_modulus,
            nominal_strip_sensitivity_stress_MPa=extreme_moment/nominal_section_modulus))
        if name in b:
            diffs = [abs(x['max_downward_mm']-y['max_downward_mm'])/y['max_downward_mm']
                for x, y in zip(c['scenarios'], b[name]['scenarios'])]
            convergence.append(dict(name=name, max_relative_difference=max(diffs),
                coarse_nodes=c['nodes'], fine_nodes=b[name]['nodes'],
                coarse_tetrahedra=c['quadratic_tetrahedra'],
                fine_tetrahedra=b[name]['quadratic_tetrahedra']))
    all_cases = coarse['cases']+fine['cases']
    result = dict(date='2026-10-25', calculation_checks='passed',
        source_cad=str(model), source_sha256=digest, source_cad_unchanged=True,
        recommendation='Matching shallow recess is feasible for light static display; 6.6 mm flat-bottom deck with 1.6 mm recess retains 5 mm floor for the conservative stiffness target. Local underside pads add print supports and lack fine-mesh verification.',
        assumed_standard_tray_foot_mm=[40, 80], matching_recess_mm=[40.6, 80.6],
        dimensions_are_design_examples_not_measured_vehicle_sizes=True,
        rows=rows, mesh_convergence=convergence,
        maximum_mesh_comparison_difference=max(c['max_relative_difference'] for c in convergence),
        maximum_mesh_volume_relative_error=max(c['volume_relative_error'] for c in all_cases),
        maximum_gravity_equilibrium_relative_error=max(c['self_weight_equilibrium_relative_error'] for c in all_cases),
        maximum_unit_load_reaction_absolute_error_N=max(abs(r-1) for c in all_cases for r in c['reactions_N'][1:]),
        support_keepouts_unchanged=all(max(c['geometry']['support_keepout_volume_differences_mm3'])<1e-6 for c in all_cases),
        selected_0p5mm_target_is_not_a_standard_or_strength_rating=True,
        exploratory_case_not_fine_mesh_verified='compensated1p6: the 4 mm tetrahedral mesh was rejected by CalculiX for nonpositive Jacobians. Its 6 mm result is exploratory and is not used for the final recommendation.',
        not_modeled=['impact ejection', 'wheel clip or axle stress', 'long-term creep',
            'temperature', 'explicit FDM skins and infill', 'support compliance or glue failure',
            'contact, clearances and rocking dynamics'],
        static_material_assumptions=coarse['material_assumptions'])
    assert result['maximum_mesh_comparison_difference'] < .03
    destination.mkdir(parents=True, exist_ok=True)
    (destination/'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    for row in rows:
        print(row['name'], 'normal', round(row['normal_E1000_max_downward_mm'], 4),
            'sensitivity', round(row['central660_E500_max_downward_mm'], 4),
            'floor', row['pocket_floor_thickness_mm'],
            'nominal_stress', round(row['nominal_strip_normal_stress_MPa'], 3),
            round(row['nominal_strip_sensitivity_stress_MPa'], 3))
    print('CHECKS', json.dumps({k: result[k] for k in (
        'maximum_mesh_comparison_difference', 'maximum_mesh_volume_relative_error',
        'maximum_gravity_equilibrium_relative_error',
        'maximum_unit_load_reaction_absolute_error_N', 'support_keepouts_unchanged',
        'source_cad_unchanged')}, indent=2))


if __name__ == '__main__':
    main()
