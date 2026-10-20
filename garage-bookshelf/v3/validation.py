"""Evidence-based native feature, geometry, parameter and assembly checks."""
import json,math
from pathlib import Path
from collections import Counter
import FreeCAD as App,Part,Mesh
from assembly import parts,bodies,global_shape
from parameters import evaluate,set_value
from measure import bounds,mesh_volume
ROOT=Path(__file__).resolve().parent

def native(doc):
    doc.recompute()
    bs=[o for o in doc.Objects if o.TypeId=='PartDesign::Body'];sk=[o for o in doc.Objects if o.TypeId=='Sketcher::SketchObject']
    if not bs or not sk:raise AssertionError('No native Bodies/sketches')
    forbidden={'Mesh::Feature','Part::Feature','PartDesign::Feature'}
    assert not [o.Name for o in doc.Objects if o.TypeId in forbidden]
    errors=[dict(name=o.Name,state=o.State) for o in doc.Objects if any(x in ('Invalid','Error') for x in o.State)]
    assert not errors,errors
    visited=set();active=set()
    def visit(o):
        if o.Name in active:raise AssertionError(f'Cycle at {o.Name}')
        if o.Name in visited:return
        active.add(o.Name)
        for dep in o.OutList:visit(dep)
        active.remove(o.Name);visited.add(o.Name)
    for o in doc.Objects:visit(o)
    br=[]
    for b in bs:
        assert not b.Shape.isNull() and b.Shape.isValid() and len(b.Shape.Solids)==1,b.Name
        sketches=[o for o in b.Group if o.TypeId=='Sketcher::SketchObject']
        assert sketches and all(s.FullyConstrained for s in sketches),b.Name
        assert any(o.TypeId=='PartDesign::Pad' for o in b.Group),b.Name
        br.append(dict(body=b.Name,source=b.SourcePart,tip=b.Tip.TypeId,solid_count=1,valid=True,sketches=[dict(name=s.Name,geometry=s.GeometryCount,constraints=s.ConstraintCount,fully_constrained=s.FullyConstrained,expressions=len(s.ExpressionEngine)) for s in sketches],bounds_global=bounds(global_shape(b))))
    return dict(status='passed',document=doc.Name,bodies=len(bs),sketches=len(sk),feature_types=dict(Counter(o.TypeId for o in doc.Objects)),all_sketches_fully_constrained=True,no_cycles=True,no_recompute_errors=True,no_static_final_shapes=True,records=br)

def parameter_tests(doc):
    ps=parts(doc)
    baseline={n:[global_shape(b).Volume for b in bodies(p)] for n,p in ps.items()}
    results=[]
    for alias,delta in [('BaseThickness',1),('DeckThickness',1),('FitClearance',.1),('OverallDepth',2)]:
        old=evaluate(doc,alias)
        set_value(doc,alias,f'{old+delta} mm')
        check=native(doc);checks=[]
        if alias=='BaseThickness':
            for i in range(1,6):
                b=bodies(ps[f'module_{i}'])[0];assert abs(next(o for o in b.Group if o.TypeId=='PartDesign::Pad').Shape.optimalBoundingBox().ZLength-(old+delta))<1e-5
                checks.append(f'module_{i}: Pad_Base thickness +1mm')
            for i in range(1,5):
                z=global_shape(bodies(ps[f'garage_column_{i}'])[0]).optimalBoundingBox().ZMin;assert abs(z-(old+delta))<1e-5
                checks.append(f'garage_column_{i}: bottom Z follows BaseThickness, top fixed')
        elif alias=='DeckThickness':
            for lev in (1,2,3):
                for side in ('left','right'):
                    b=bodies(ps[f'garage_deck_{lev}_{side}'])[0];assert abs(b.Shape.optimalBoundingBox().ZLength-(old+delta))<1e-5
                    checks.append(f'garage_deck_{lev}_{side}: thickness +1mm')
        elif alias=='FitClearance':
            for i in range(2,6):
                n=f'module_{i}';v=global_shape(bodies(ps[n])[0]).Volume
                assert v<baseline[n][0];checks.append(f'{n}: sockets enlarge, solid volume decreases')
        elif alias=='OverallDepth':
            for i in range(1,6):
                bb=global_shape(bodies(ps[f'module_{i}'])[0]).optimalBoundingBox();assert abs(bb.YMax-(old+delta))<1e-5
                checks.append(f'module_{i}: depth and back follow parameter')
            assert abs(ps['billboard_left'].Placement.Base.y-(old+delta))<1e-7
            checks.append('billboard_left: assembly rear placement follows OverallDepth')
        set_value(doc,alias,f'{old} mm');native(doc)
        max_delta=max(abs(global_shape(b).Volume-v) for n,p in ps.items() for b,v in zip(bodies(p),baseline[n]))
        assert max_delta<1e-4,(alias,max_delta)
        results.append(dict(alias=alias,original_mm=old,modified_mm=old+delta,checks=checks,restored=True,max_restored_volume_delta_mm3=max_delta,status='passed'))
    return dict(status='passed',tests=results)

def source_coordinates(name,p):
    ss=[global_shape(b) for b in bodies(p)]
    if name.startswith('garage_column_'):
        for s in ss:s.translate(App.Vector(-p.Placement.Base.x+10,-p.Placement.Base.y+10,0))
    elif name=='module_5_narrow_visual':
        for s in ss:s.translate(App.Vector(-evaluate(p.Document,'NarrowViewOffset5'),0,0))
    elif name=='book_depot_sign':
        for s in ss:s.Placement=p.Placement.inverse().multiply(s.Placement)
    return ss[0] if len(ss)==1 else Part.makeCompound(ss)

def geometry(documents):
    from reference_shapes import shapes,OLD
    refs=shapes();new={name:source_coordinates(name,p) for d in documents for name,p in parts(d).items()}
    assert set(new)==set(refs),(set(new)-set(refs),set(refs)-set(new))
    records=[]
    inventory=json.loads((ROOT/'reference/v2-inventory.json').read_text())
    old_placements={x['name']:x['placement'] for x in inventory['assembly_objects']}
    old_placements.update({x['name']:x['placement'] for x in inventory.get('auxiliary_view_objects',[])})
    containers={n:p for d in documents for n,p in parts(d).items()}
    for name,s in new.items():
        ref=refs[name];m=Mesh.Mesh(str(OLD/'stl'/f'{name}.stl'))
        diff=s.cut(ref).Volume+ref.cut(s).Volume
        bbox_delta=max(abs(a-b) for a,b in zip(bounds(s),bounds(m)))
        vdelta=abs(s.Volume-mesh_volume(m))/s.Volume;adelta=abs(s.Area-m.Area)/s.Area
        points,facets=m.Topology
        # Include vertices and triangle centres, both sampled uniformly and deterministically.
        pts=[points[i] for i in range(0,len(points),max(1,len(points)//64))]
        pts.extend((points[f[0]]+points[f[1]]+points[f[2]])/3 for f in facets[::max(1,len(facets)//64)])
        deviation=max(Part.Vertex(p).distToShape(s)[0] for p in pts)
        global_diff=None
        if name in old_placements:
            values=old_placements[name];placement=App.Placement(App.Vector(*values[:3]),App.Rotation(*values[3:]))
            old_global=ref.copy();old_global.Placement=placement.multiply(old_global.Placement)
            global_ss=[global_shape(b) for b in bodies(containers[name])]
            new_global=global_ss[0] if len(global_ss)==1 else Part.makeCompound(global_ss)
            global_diff=new_global.cut(old_global).Volume+old_global.cut(new_global).Volume
        good=(global_diff is None or global_diff<1e-4) and diff<1e-4 and bbox_delta<.02 and vdelta<.0005 and adelta<.0005 and deviation<.02
        records.append(dict(name=name,status='passed' if good else 'failed',exact_boolean_symmetric_difference_mm3=diff,global_boolean_difference_mm3=global_diff,bounds_mm=bounds(s),bounds_mesh_delta_max_mm=bbox_delta,volume_mm3=s.Volume,mesh_volume_mm3=mesh_volume(m),volume_relative_delta=vdelta,area_mm2=s.Area,area_relative_delta=adelta,mesh_samples=len(pts),sampled_surface_deviation_max_mm=deviation,solid_count=len(s.Solids),reference_solid_count=len(ref.Solids)))
    r=dict(status='passed' if all(r['status']=='passed' for r in records) else 'failed',logical_parts=len(records),tolerances=dict(exact_boolean_difference_mm3=.0001,mesh_bounds_and_sampled_surface_mm=.02,mesh_volume_area_relative=.0005),parts=records,limitations=['Mesh surface sampling is not a complete Hausdorff proof; exact source solids are compared by bidirectional Boolean difference.','Legacy disconnected-text Mesh.Volume is numerically unstable; translated double-precision triangle sums are used.','Bounds use optimalBoundingBox because ordinary OCC spline boxes include unused control poles.'])
    (ROOT/'reports/geometry-comparison.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
    assert r['status']=='passed',[x for x in records if x['status']!='passed']
    return r

def assembly_checks(doc):
    ps=parts(doc);ss={n:global_shape(bodies(p)[0]) for n,p in ps.items() if len(bodies(p))==1}
    paths=[]
    for i in range(1,5):
        for dx in (60,30,15,5,1,0):
            incoming=ss[f'module_{i+1}'].copy();incoming.translate(App.Vector(dx,0,0));vol=ss[f'module_{i}'].common(incoming).Volume
            assert vol<.01,(i,dx,vol)
            paths.append(dict(interface=i,offset_mm=dx,intersection_mm3=vol))
    for lev in (1,2,3):
        for dx in (30,15,5,1,0):
            incoming=ss[f'garage_deck_{lev}_right'].copy();incoming.translate(App.Vector(dx,0,0));vol=ss[f'garage_deck_{lev}_left'].common(incoming).Volume
            assert vol<.01,(lev,dx,vol)
            paths.append(dict(deck_level=lev,offset_mm=dx,intersection_mm3=vol))
    collisions=[]
    items=list(ss.items())
    for i,(name,s) in enumerate(items):
        for other,t in items[i+1:]:
            if not s.optimalBoundingBox().intersect(t.optimalBoundingBox()):continue
            v=s.common(t).Volume
            if v>.01:collisions.append(dict(part_a=name,part_b=other,intersection_mm3=v,status='legacy_design_issue_preserved'))
    return dict(reconstruction_status='passed',insertion_paths=paths,existing_design_interferences=collisions,assembly_function_status='failed_legacy_interferences' if collisions else 'passed_geometry_only',physical_load_and_PLA_fit='not_verified',policy='Preserve geometry and report source design issues; no unauthorized holes, repositioning, or added structures.')

def reopen(path,expected):
    d=App.openDocument(str(path));d.recompute();r=native(d);assert r['bodies']==expected
    # Re-opened expressions must still solve, rather than merely retain cached shapes.
    if 'module_1' in parts(d):r['parameter_edits_after_reopen']=parameter_tests(d)
    App.closeDocument(d.Name);return r
