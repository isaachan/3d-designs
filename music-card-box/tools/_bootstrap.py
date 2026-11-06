from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
runtime = Path(sys.executable).parent.parent / 'lib'
if 'FreeCAD.app' in str(runtime):
    sys.path.insert(0, str(runtime))
