# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Read-only renders of all four decorated floors from the formal native CAD."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import numpy as np
from decoration.recessed_layout import FLOORS
from render_parking_recesses import saved_colors,triangles,render


def main():
    file=ROOT/'garage-bookshelf-v4-assembly.FCStd'
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    doc=App.openDocument(str(file));colors=saved_colors(file);records=[]
    for source,(floor,count) in FLOORS.items():
        p,rgb=triangles(doc,colors,[source],local=True)
        if source=='module_1':
            # Isolate the actual base surface, pins and joints for this detail;
            # the complete back wall remains present in the assembly view.
            keep=np.max(p[:,:,2],axis=1)<=11.1
            p,rgb=p[keep],rgb[keep]
        path=ROOT/f'reports/four-floor-decoration-floor-{floor}.png'
        record=render(p,rgb,path,[-.65,-1.9,3.8],width=1600,height=1250)
        record.update(floor=floor,bays=count,source_part=source,proposal_only=False,
                      base_back_wall_omitted_from_detail=source=='module_1')
        records.append(record);print('RENDERED',path.name,flush=True)
    names=[b.SourcePart for b in doc.Objects if b.TypeId=='PartDesign::Body'
           and (b.SourcePart=='module_1' or b.SourcePart.startswith(('garage_deck_','column_')))]
    p,rgb=triangles(doc,colors,names)
    records.append(render(p,rgb,ROOT/'reports/four-floor-decoration-garage.png',[-1,-2.8,1.7],width=1500,height=1500))
    App.closeDocument(doc.Name)
    assert hashlib.sha256(file.read_bytes()).hexdigest()==digest
    (ROOT/'reports/four-floor-decoration-render-validation.json').write_text(json.dumps(dict(
        status='passed',cad_sha256=digest,native_geometry_only=True,saved_face_materials_used=True,
        cad_modified=False,previews=records),indent=2)+'\n')
    print('PASS formal CAD previews; CAD unchanged.',flush=True)


if __name__=='__main__':main()
