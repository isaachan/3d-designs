"""Export current solids only; never feed saved appearance faces to a mesh."""
from pathlib import Path
import FreeCAD as App
import Mesh
import MeshPart
import Part
from garage_bookshelf.assembly import global_shape
from garage_bookshelf.paths import CAD, sha, source_record, write_json
from garage_bookshelf.specification import bodies, role
from garage_bookshelf.validation import validate


def export(output):
    report = validate()
    write_json(output / 'validation.json', report)
    if report['status'] != 'passed':
        raise ValueError(report['errors'])
    before = sha(CAD)
    if report['cad_sha256'] != before:
        raise ValueError('CAD changed after validation; run export again')
    doc = App.openDocument(str(CAD))
    records = []
    try:
        for folder in ('stl/assembly', 'stl/print'):
            (output / folder).mkdir(parents=True)
        for body in bodies(doc, ('print',)):
            name = body.SourcePart
            shape = global_shape(body)
            mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.02, AngularDeflection=.12, Relative=False)
            assembly_file = output / 'stl/assembly' / (name + '.stl')
            mesh.write(str(assembly_file))
            flat = name in ('billboard', 'top_carrier', 'side_receiver', 'side_cartridge')
            # The removable signs face -Y; put their broad backs on the bed
            # so the raised lettering and engraved slogan face upwards.
            rotation = -90 if name in ('top_carrier', 'side_cartridge') else 90 if flat else 0
            if rotation:
                mesh.transform(App.Placement(App.Vector(), App.Rotation(App.Vector(1, 0, 0), rotation)).toMatrix())
            box = mesh.BoundBox
            mesh.translate(-box.XMin, -box.YMin, -box.ZMin)
            file = output / 'stl/print' / (name + '.stl')
            mesh.write(str(file))
            check = Mesh.Mesh(str(file))
            box = check.BoundBox
            dimensions = [box.XLength, box.YLength, box.ZLength]
            assert check.isSolid() and not check.hasNonManifolds(), name
            assert len(check.getSeparateComponents()) == 1, name
            assert dimensions[0] + 8 <= 235.501 and dimensions[1] + 8 <= 256.001 and dimensions[2] <= 256.001, (name, dimensions)
            records.append(dict(part=name, role=role(body), print_file=str(file.relative_to(output)),
                                assembly_file=str(assembly_file.relative_to(output)),
                                dimensions_mm=dimensions, rotated_x_degrees=rotation,
                                closed=True, solid_components=1, brim_mm=4))
        step_file = output / 'garage-bookshelf-v5-assembly.step'
        shapes = [global_shape(b) for b in bodies(doc)]
        Part.makeCompound(shapes).exportStep(str(step_file))
        restored = Part.Shape()
        restored.read(str(step_file))
        assert len(restored.Solids) == len(shapes)
        assert all(s.isValid() for s in restored.Solids)
        original_volume = sum(s.Volume for s in shapes)
        volume_error = abs(restored.Volume - original_volume) / original_volume
        assert volume_error < 1e-6, volume_error
        original_box = Part.makeCompound(shapes).BoundBox
        step_box = restored.BoundBox
        bounds_error = max(abs(getattr(original_box, key) - getattr(step_box, key))
                           for key in ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax'))
        assert bounds_error < 1e-4, bounds_error
    finally:
        App.closeDocument(doc.Name)
    assert sha(CAD) == before
    manifest = dict(source_record(), status='passed', kind='geometry-export', cad_unchanged=True,
                    appearance_in_stl=False, samples_exported=False, hardware_in_step=True,
                    hardware_in_stl=False, print_parts=records, step_solids=len(shapes),
                    step_round_trip=dict(relative_volume_error=volume_error, max_bounds_error_mm=bounds_error),
                    printing_status='not_yet_sliced', physical_print_and_fit_tested=False)
    manifest['files'] = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    write_json(output / 'manifest.json', manifest)
    return manifest
