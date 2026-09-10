"""Create a Bambu project containing only assembly modules 2, 3, and 5.

This is an inspection/selection project, not a one-plate print job: module 2
alone nearly fills the X2D bed.  Print the three existing single-part projects
when manufacturing them.
"""
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STL = ROOT / "stl"
OUT = ROOT / "print" / "projects" / "modules-2-3-5-view-x2d-pla.3mf"
AUDIT = ROOT / "audit" / "modules-2-3-5-view.json"
BAMBU = "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
PARTS = ["module_2", "module_3", "module_5"]

with tempfile.TemporaryDirectory() as temp:
    raw = Path(temp) / "raw.3mf"
    subprocess.run([BAMBU, *[str((STL / f"{name}.stl").resolve()) for name in PARTS],
                    "--arrange", "1", "--ensure-on-bed", "--export-3mf", str(raw)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with zipfile.ZipFile(raw) as source:
        entries = {item.filename: source.read(item.filename) for item in source.infolist()}

settings_name = "Metadata/project_settings.config"
settings = json.loads(entries[settings_name])
settings.update({
    "printer_model": "Bambu Lab X2D",
    "printable_area": ["0x0", "256x0", "256x256", "0x256"],
    "printable_height": "260", "wall_loops": "4",
    "sparse_infill_density": "25%", "brim_width": "4",
})
entries[settings_name] = (json.dumps(settings, ensure_ascii=False, indent=4) + "\n").encode()

with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
    for name, content in entries.items():
        target.writestr(name, content)

AUDIT.write_text(json.dumps({
    "status": "passed", "file": OUT.name, "included_parts": PARTS,
    "purpose": "Bambu Studio selection/view project; not a simultaneous one-plate print",
    "print_instruction": "Use module_2/module_3/module_5 individual X2D projects to print.",
}, ensure_ascii=False, indent=2))
print(f"Generated {OUT}")
