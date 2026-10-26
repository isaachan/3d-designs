# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Verify h=0 base geometry and report shallow engraving differences; no CAD writes."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
V4=ROOT.parents[1]
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App


def main():
    source=ROOT/'reference/garage-bookshelf-v4-ribbed-analysis-source.FCStd'
    model=V4/'garage-bookshelf-v4-assembly.FCStd'
    summary=json.loads((ROOT/'summary.json').read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==summary['CAD_sha256']
    old=App.openDocument(str(source));new=App.openDocument(str(model))
    expected=old.garage_deck_1_Body.Tip.BaseFeature.Shape.copy()
    cases=json.loads((ROOT/'results-mesh4.json').read_text())['cases']
    h0=next(case for case in cases if case['rib_height_mm']==0)
    assert abs(expected.Volume-h0['solid_volume_mm3'])<1e-6
    checks=[]
    for level in (1,2,3):
        body=new.getObject(f'garage_deck_{level}_Body');shape=body.Shape
        bb=shape.optimalBoundingBox()
        difference=shape.cut(expected).Volume+expected.cut(shape).Volume
        added=shape.cut(expected).Volume
        assert added<1e-6,added
        if level in (1,2):
            base=next(o for o in body.Group if o.TypeId=='PartDesign::Pocket' and o.Name.startswith('Pocket_FourLocatingHoles'))
            assert base.Shape.cut(expected).Volume+expected.cut(base.Shape).Volume<1e-6
            assert difference>0
        else:assert difference<1e-6,difference
        assert not any('IntegralRibs' in feature.Name for feature in body.Group)
        assert abs(bb.ZMin)<1e-6 and abs(bb.ZMax-5)<1e-6
        checks.append(dict(level=level,dimensions_mm=[bb.XLength,bb.YLength,bb.ZLength],
                           symmetric_difference_from_FEA_h0_mm3=difference,
                           solid_volume_mm3=shape.Volume,extra_rib_height_mm=0))
    assert not new.DesignParameters.getCellFromAlias('DeckRibHeight')
    report=dict(status='passed',analysis_source=str(source.relative_to(ROOT)),
                analysis_source_sha256=summary['CAD_sha256'],
                production_CAD=str(model.relative_to(V4)),
                production_CAD_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
                production_decks_match_FEA_h0=False,base_decks_before_engraving_match_FEA_h0=True,
                production_change='Levels 1 and 2 have 0.2/0.4 mm top engravings; level 3 unchanged. Historical FEA does not include these cuts.',
                deck_rib_features_and_parameters_removed=True,
                deck_checks=checks,physical_load_test='not_performed')
    App.closeDocument(old.Name);App.closeDocument(new.Name)
    (ROOT/'design-application.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('PASS all base decks match h=0; shallow engraving differences explicitly reported')

if __name__=='__main__':main()
