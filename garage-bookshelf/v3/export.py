"""Export finished native Bodies only; original-coordinate and print-bed STL sets."""
import json,sys
from pathlib import Path
sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD as App,Part,Mesh,MeshPart
from assembly import parts,bodies,global_shape
from parameters import evaluate
from measure import mesh_volume,bounds

def export_document(doc,root):
    root=Path(root);out=root/'stl';bed=root/'print-stl';out.mkdir(exist_ok=True);bed.mkdir(exist_ok=True)
    individual=root/'body-stl';individual.mkdir(exist_ok=True)
    records=[]
    for name,p in parts(doc).items():
        bs=bodies(p);ss=[global_shape(b) for b in bs]
        # Reproduce original v2 per-file coordinates. Body geometry remains local in FCStd.
        if name.startswith('garage_column_'):
            for s in ss:s.translate(App.Vector(-p.Placement.Base.x+evaluate(doc,'ColumnCentreOffset'),-p.Placement.Base.y+evaluate(doc,'ColumnCentreOffset'),0))
        elif name=='module_5_narrow_visual':
            for s in ss:s.translate(App.Vector(-evaluate(doc,'NarrowViewOffset5'),0,0))
        elif name=='book_depot_sign':
            for s in ss:s.Placement=p.Placement.inverse().multiply(s.Placement)
        shape=ss[0] if len(ss)==1 else Part.makeCompound(ss)
        m=MeshPart.meshFromShape(Shape=shape,LinearDeflection=evaluate(doc,'ExportLinearDeflection'),AngularDeflection=.15,Relative=False)
        path=out/f'{name}.stl';m.write(str(path));check=Mesh.Mesh(str(path))
        comps=check.getSeparateComponents()
        if len(comps)!=len(bs) or not all(c.isSolid() for c in comps) or check.hasNonManifolds():raise RuntimeError(f'{name}: export is not closed/manifold')
        body_files=[]
        for body,solid in zip(bs,ss):
            bm=MeshPart.meshFromShape(Shape=solid,LinearDeflection=evaluate(doc,'ExportLinearDeflection'),AngularDeflection=.15,Relative=False)
            body_file=individual/f'{body.Name}.stl';bm.write(str(body_file))
            reread=Mesh.Mesh(str(body_file))
            if not reread.isSolid() or len(reread.getSeparateComponents())!=1 or reread.hasNonManifolds():raise RuntimeError(f'{body.Name}: invalid individual Body STL')
            body_files.append(str(body_file.relative_to(root)))
        dims=[check.BoundBox.XLength,check.BoundBox.YLength,check.BoundBox.ZLength]
        # Keep source orientation for structure, rotate thin billboard pieces/text onto bed.
        flat=Mesh.Mesh(check)
        rotation=App.Rotation()
        if name.startswith('billboard_'):rotation=App.Rotation(App.Vector(1,0,0),90)
        flat.transform(App.Placement(App.Vector(),rotation).toMatrix())
        bb=flat.BoundBox;shift=App.Vector(-bb.XMin,-bb.YMin,-bb.ZMin);flat.translate(*shift)
        flat.write(str(bed/f'{name}.stl'))
        fd=[flat.BoundBox.XLength,flat.BoundBox.YLength,flat.BoundBox.ZLength]
        fit=fd[0]+2*evaluate(doc,'PrintBrim')<=evaluate(doc,'PrintBedWidth')+.001 and fd[1]+2*evaluate(doc,'PrintBrim')<=evaluate(doc,'PrintBedDepth')+.001 and fd[2]<=evaluate(doc,'PrintHeight')+.001
        if not fit:raise RuntimeError(f'{name}: print envelope exceeded {fd}')
        records.append(dict(name=name,status='passed',bodies=[b.Name for b in bs],components=len(comps),individual_body_stls=body_files,individual_body_stls_closed=True,closed=True,non_manifold=False,units='mm',bounds_source=bounds(check),dimensions_mm=dims,volume_mm3=mesh_volume(check),print_dimensions_mm=fd,print_rotation_quaternion=list(rotation.Q),print_translation_mm=list(shift),x2d_with_4mm_brim=True,settings=dict(wall_loops=int(evaluate(doc,'PrintWallLoops')),infill_percent=evaluate(doc,'PrintInfillPercent'),material='PLA',brim_mm=evaluate(doc,'PrintBrim'))))
    return records

if __name__=='__main__':
    import argparse,sys
    parser=argparse.ArgumentParser();parser.add_argument('files',nargs='+');parser.add_argument('--output',default=str(Path(__file__).resolve().parent));args=parser.parse_args()
    records=[]
    for file in args.files:
        d=App.openDocument(str(Path(file).resolve()));d.recompute();records.extend(export_document(d,args.output));App.closeDocument(d.Name)
    (Path(args.output)/'reports/print-validation.json').write_text(json.dumps(dict(status='passed',part_count=len(records),individual_body_stl_count=sum(len(x['individual_body_stls']) for x in records),parts=records,physical_PLA_fit_and_load='not_verified'),indent=2))
    print(f'Exported {len(records)} source-coordinate STL and print-bed STL files')
