"""Read-only copy of the two existing garage column solids, for local reuse."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App

ROOT = Path(__file__).resolve().parent
REPO = next(p for p in ROOT.parents if (p/'garage-bookshelf').is_dir())
SOURCE = REPO/'garage-bookshelf/v5/cad/garage-bookshelf-v5-assembly.FCStd'


def main():
    dest = ROOT/'reference'; dest.mkdir(exist_ok=True)
    doc = App.openDocument(str(SOURCE))
    records = []
    try:
        for objname, filename in [('column_1_segment_1_Body', 'garage-standard-column.brep'),
                                  ('column_1_segment_4_Body', 'garage-top-cap.brep')]:
            shape = doc.getObject(objname).Shape.copy()
            assert shape.isValid() and len(shape.Solids) == 1
            # Body geometry is local to its assembly container, already centred on Z.
            assert abs(shape.BoundBox.ZMin) < 1e-6
            assert abs(shape.BoundBox.XMin+shape.BoundBox.XMax) < 1e-6
            shape.exportBrep(str(dest/filename))
            records.append(dict(source_body=objname, file=filename,
                                volume_mm3=shape.Volume, height_mm=shape.BoundBox.ZLength))
        report = dict(source_file=str(SOURCE.relative_to(REPO)),
                      source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                      source_modified=False, solids=records)
        (dest/'source.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        App.closeDocument(doc.Name)


if __name__ == '__main__': main()
