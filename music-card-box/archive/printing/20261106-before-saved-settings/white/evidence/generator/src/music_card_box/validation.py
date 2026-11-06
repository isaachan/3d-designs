"""Analytical CAD checks; physical fit/adhesive testing is explicitly separate."""
import math
import FreeCAD as App
import Part

def validate(doc,parts,spec):
    p=spec['dimensions_mm']; w=p['InnerWidth']+2*p['Wall']; depth=p['InnerDepth']+2*p['Wall']
    report={'status':'passed','checks':{},'physical_fit':'not_tested','adhesive_load_test':'not_tested',
            'slicing':'not_performed_printer_unspecified','parts':{},'warnings':[]}
    for name,b in parts.items():
        assert b.Shape.isValid() and len(b.Shape.Solids)==1,name
        bb=b.Shape.BoundBox
        report['parts'][name]={'color':b.PrintColor,'volume_mm3':b.Shape.Volume,
            'bounds_mm':[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax],
            'native_tip':b.Tip.TypeId,'solids':len(b.Shape.Solids)}
    sketches=[s for s in doc.Objects if s.TypeId=='Sketcher::SketchObject']
    assert all(s.FullyConstrained for s in sketches)
    assert not any('Invalid' in o.State for o in doc.Objects)
    report['checks']['fully_constrained_sketches']=len(sketches)
    shell=parts['CassetteShell'].Shape
    bounds=shell.BoundBox
    assert abs(bounds.XLength-w)<1e-5 and abs(bounds.YLength-depth)<1e-5 and abs(bounds.ZLength-p['BackHeight'])<1e-5
    # All stack-depth positions, not just a centrally placed reference stack.
    translations=[]
    spare=p['InnerDepth']-p['RearStandOff']-p['StackDepth']
    for y_offset in [0,.01,spare/2,spare-.01,spare]:
        for lift in [0,.5,10,35,70,105,130]:
            card=Part.makeBox(p['CardWidth'],p['StackDepth'],p['CardHeight'],
                App.Vector(-p['CardWidth']/2,p['Wall']+p['RearStandOff']+y_offset,p['Bottom']+lift))
            overlap=sum(b.Shape.common(card).Volume for b in parts.values())
            assert overlap<1e-5,(y_offset,lift,overlap)
            translations.append({'depth_offset_mm':y_offset,'lift_mm':lift,'overlap_mm3':overlap})
    report['checks']['card_insertion_removal']=translations
    pair_checks=[]
    values=list(parts.items())
    for i,(name,b) in enumerate(values):
        for other,c in values[i+1:]:
            overlap=b.Shape.common(c.Shape).Volume
            assert overlap<1e-5,(name,other,overlap)
            pair_checks.append([name,other,overlap])
    report['checks']['part_interference']=pair_checks
    # Four adhesive landing rectangles lie wholly on the flat Y=0 back face.
    zones=[]
    for x,z,zw,zh in spec['adhesive_zones_mm']:
        probe=Part.makeBox(zw,.05,zh,App.Vector(x,0,z))
        area=shell.common(probe).Volume/.05
        assert abs(area-zw*zh)<1e-4,(x,z,area)
        zones.append({'rectangle_x_z_w_h_mm':[x,z,zw,zh],'verified_flat_area_mm2':area})
    report['checks']['flat_adhesive_zones']=zones
    report['checks']['wall_back_plane_y_mm']=0
    report['checks']['clearances_mm']={'total_width':p['InnerWidth']-p['CardWidth'],
        'total_depth':spare,'minimum_card_to_wall_gap':p['Wall']+p['RearStandOff'],
        'front_center_exposed_height':p['Bottom']+p['CardHeight']-p['FrontGripHeight'],
        'rear_center_exposed_height':p['Bottom']+p['CardHeight']-p['RearGripHeight'],
        'reel_diametral_clearance':p['ReelFitClearance']*2,'glue_gap':p['GlueGap']}
    volume=sum(b.Shape.Volume for b in parts.values())
    report['estimated_pla_mass_g']=volume/1000*1.24
    report['mass_note']='Solid-volume estimate at 1.24 g/cm3, excluding cards and glue; sliced mass depends on walls and infill.'
    report['warnings']=['No physical prototype or wall adhesion test.','3MF files contain geometry and colors; no machine/material preset or G-code.']
    return report
