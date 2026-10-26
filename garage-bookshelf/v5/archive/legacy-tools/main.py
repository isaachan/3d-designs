# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Rebuild v4 from source and validate/export. Prior versions are read-only."""
from build import build,ROOT
import FreeCAD as App
from validate_export import main as validate

if __name__=='__main__':
    doc=build()
    doc.saveAs(str(ROOT/'garage-bookshelf-v4-assembly.FCStd'))
    App.closeDocument(doc.Name)
    validate()
