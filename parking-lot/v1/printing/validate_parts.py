#!/usr/bin/env python3
"""Verify that each colour assembly is one connected printable BRep solid."""
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent


def main():
    start = time.time()
    doc = App.openDocument(str(ROOT/'parking-lot-v1-print-parts.FCStd'))
    data = json.loads((ROOT/'parts.json').read_text())
    groups = {}
    for obj in doc.Objects:
        if 'PrintPart' in obj.PropertiesList:
            groups.setdefault(obj.PrintPart, []).append(obj.Shape)
    assert set(groups)=={p['name'] for p in data['parts']}
    rows = []
    for part in data['parts']:
        pieces = groups[part['name']]
        assert all(s.isValid() and all(v.isClosed() for v in s.Solids) for s in pieces)
        joined = pieces[0] if len(pieces)==1 else pieces[0].multiFuse(pieces[1:]).removeSplitter()
        assert joined.isValid(), part['name']
        assert len(joined.Solids)==1, (part['name'], len(joined.Solids), 'disconnected colour assembly')
        # Adjacent material regions must not contain double-counted volume.
        difference = sum(s.Volume for s in pieces)-joined.Volume
        assert abs(difference)<.5, (part['name'], difference)
        rows.append(dict(part=part['name'], valid_closed_single_solid=True,
                         color_volume_overlap_mm3=difference))
        print('PASS connected', part['name'], flush=True)
    (ROOT/'geometry-validation.json').write_text(json.dumps(dict(status='passed',
        source_unchanged=data['source_unchanged'], print_parts=len(rows), all_mechanical_parts_connected=True,
        isolated_color_islands=False, maximum_color_overlap_mm3=max(abs(r['color_volume_overlap_mm3']) for r in rows),
        scope='CAD connectedness, closed BRep and colour-volume contacts; physical fit and strength remain untested.',
        parts=rows, seconds=time.time()-start), ensure_ascii=False, indent=2)+'\n')
    print('PASS', len(rows), 'connected mechanical print parts', flush=True)


if __name__ == '__main__':
    main()
