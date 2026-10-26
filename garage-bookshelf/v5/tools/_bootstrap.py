"""Make tools runnable from any working directory without installing FreeCAD."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
runtime_lib = Path(sys.executable).parent.parent / 'lib'
if 'FreeCAD.app' in str(runtime_lib) and runtime_lib.is_dir():
    sys.path.insert(0, str(runtime_lib))
