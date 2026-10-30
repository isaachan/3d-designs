"""Read-only checks for the current native document, independent of export."""
from itertools import combinations
import FreeCAD as App
from garage_bookshelf.assembly import global_shape
from garage_bookshelf.parameters import evaluate
from garage_bookshelf.paths import CAD, sha, source_record
from garage_bookshelf.specification import bodies, role, specification


def validate(cad=CAD, intersections=True):
    before = sha(cad)
    report = dict(source_record(cad), status='failed', scope='native CAD geometry and assembly',
                  physical_print_and_fit_tested=False, checks=[], errors=[])
    doc = None
    try:
        doc = App.openDocument(str(cad))
        doc.recompute(None, True, True)
        spec = specification()
        all_bodies = [o for o in doc.Objects if o.TypeId == 'PartDesign::Body']
        categorized = {key: [b for b in all_bodies if role(b) == key]
                       for key in ('print', 'hardware', 'sample')}
        for key, spec_key in [('print', 'print_parts'), ('hardware', 'hardware'), ('sample', 'samples')]:
            actual = sorted(b.SourcePart for b in categorized[key])
            assert actual == sorted(spec[spec_key]), (key, actual)
        invalid = [o.Name for o in doc.Objects if any(s in ('Invalid', 'Error') for s in o.State)]
        assert not invalid, invalid
        for b in all_bodies:
            assert b.Tip and b.Shape.isValid() and len(b.Shape.Solids) == 1, b.Name
        sketches = [o for o in doc.Objects if o.TypeId == 'Sketcher::SketchObject']
        assert all(s.FullyConstrained for s in sketches), [s.Name for s in sketches if not s.FullyConstrained]
        report['counts'] = dict(bodies=len(all_bodies), sketches=len(sketches),
                                **{key: len(value) for key, value in categorized.items()})
        report['checks'].append('all native Bodies valid, single-solid, classified; all sketches constrained')
        for name, expected in spec['parameters_mm'].items():
            assert abs(evaluate(doc, name) - expected) < 1e-5, name
        floor_records = []
        for name, expected in spec['parking_floors'].items():
            body = doc.getObject(name + '_Body')
            assert body.ParkingBays == body.TrayRecessCount == expected, name
            if name.startswith('garage_deck_'):
                assert abs(body.Shape.BoundBox.ZLength - 6.6) < 1e-6, name
            floor_records.append(dict(part=name, bays=body.ParkingBays, recesses=body.TrayRecessCount))
        assert sum(r['recesses'] for r in floor_records) == 10
        assert doc.side_cartridge_Body.EngravedSlogan == spec['slogan']
        assert not any(o.Name.startswith('M_Paint_SideSign_') for o in doc.Objects)
        graphics = [o for o in doc.Objects if 'MColor' in o.PropertiesList]
        assert graphics
        for obj in graphics:
            assert obj.Shape.isValid() and not obj.Shape.Solids and abs(obj.Shape.Volume) < 1e-8, obj.Name
        report['parking_floors'] = floor_records
        report['appearance_faces'] = len(graphics)
        report['checks'].append('current dimensions, 10 recesses, M3 roles, slogan and zero-thickness appearance')
        if spec.get('skin_manufacturing'):
            contract = spec['skin_manufacturing']
            from garage_bookshelf.rendering.software import saved_colors
            from garage_bookshelf.appearance.palette import RGB
            saved = saved_colors(cad)
            for key, value in contract['parameters_mm'].items():
                assert abs(doc.SkinParameters.evalExpression(key).Value-value) < 1e-6, key
            for name, item in contract['parts'].items():
                body = doc.getObject(name+'_Body')
                assert body.SkinColor == item['color'] and body.SkinRole == item['role'], name
                expected = 'Part::Extrusion' if contract['mode'] == 'flush-seated-inlays' else 'Part::Cut'
                assert body.Tip.TypeId == 'PartDesign::FeatureBase' and body.BaseFeature.TypeId == expected, name
                if contract['mode'] == 'flush-seated-inlays':
                    box = global_shape(body).BoundBox
                    plane = box.YMin if body.SkinNormal.y else box.ZMax
                    nominal = {'Back':159, 'FrontEdge':0, 'Floor':8, 'TopRim':238}[body.SkinRole]
                    assert abs(plane-nominal) < 1e-6, (name, plane, nominal)
                    thickness = box.YLength if body.SkinNormal.y else box.ZLength
                    assert abs(thickness-contract['parameters_mm']['SkinThickness']) < 1e-6, name
                    for kind, offset in [('Seat', .15), ('GlueWell', -1.5)]:
                        outline = doc.getObject(name+'_'+kind+'Outline')
                        assert abs(float(outline.Value)-offset)<1e-6 and outline.Shape.isValid(), name
                colors = saved[body.Tip.Name]
                assert all(max(abs(a-b) for a,b in zip(rgb,RGB[body.SkinColor])) < 1/255 for rgb in colors), name
            for name in ('module_2', 'module_3'):
                body = doc.getObject(name+'_Body')
                assert all(max(rgb)<.2 for rgb in saved[body.Tip.Name]), name
            report['checks'].append('12 native parametric skins, nominal dimensions, saved colours; black book bodies')
            if contract['mode'] == 'flush-seated-inlays':
                for b in (doc.module_2_Body, doc.module_3_Body):
                    pockets = [o for o in b.Group if o.TypeId == 'PartDesign::Pocket' and
                               ('_SeatPocket' in o.Name or '_GlueWellPocket' in o.Name)]
                    assert pockets and all(o.Shape.isValid() for o in pockets), b.Name
                report['checks'].append('12 inlay fronts flush with original planes; native seating pockets and glue wells')
        shapes = {b.SourcePart: global_shape(b) for b in bodies(doc)}
        overlap_checks = 0
        if intersections:
            for (a, sa), (b, sb) in combinations(shapes.items(), 2):
                if not sa.BoundBox.intersect(sb.BoundBox):
                    continue
                volume = sa.common(sb).Volume
                assert volume < .01, (a, b, volume)
                overlap_checks += 1
            report['checks'].append('assembly Body-pair overlap < 0.01 mm^3 (sample excluded)')
        report['intersection_pairs_checked'] = overlap_checks
        report['intersection_check_enabled'] = intersections
        import Part
        box = Part.makeCompound(list(shapes.values())).BoundBox
        report['assembly_dimensions_mm'] = [box.XLength, box.YLength, box.ZLength]
        report['status'] = 'passed'
    except Exception as exc:
        report['errors'].append(f'{type(exc).__name__}: {exc}')
    finally:
        if doc is not None:
            App.closeDocument(doc.Name)
        report['cad_unchanged'] = sha(cad) == before
        if not report['cad_unchanged']:
            report['status'] = 'failed'
            report['errors'].append('Source CAD changed during validation')
    return report
