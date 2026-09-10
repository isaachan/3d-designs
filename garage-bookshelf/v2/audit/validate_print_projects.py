"""Validate the packaged X2D projects without relying on a slicer UI."""
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "stl"
PROJECTS = ROOT / "print" / "projects"
OUT = Path(__file__).resolve().parent / "print-validation.json"
CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"

required = {f"{p.stem}-x2d-pla.3mf" for p in STL.glob("*.stl")}
actual = {p.name for p in PROJECTS.glob("*.3mf")}
if required != actual:
    raise AssertionError(f"3MF/STL set mismatch: missing={required-actual}, extra={actual-required}")

checked = []
for path in sorted(PROJECTS.glob("*.3mf")):
    with zipfile.ZipFile(path) as package:
        bad = package.testzip()
        if bad:
            raise AssertionError(f"{path.name}: corrupt ZIP member {bad}")
        names = set(package.namelist())
        for needed in ("3D/3dmodel.model", "Metadata/project_settings.config", "Metadata/model_settings.config"):
            if needed not in names:
                raise AssertionError(f"{path.name}: missing {needed}")
        raw_model = package.read("3D/3dmodel.model")
        # Bambu Studio needs the original declared namespace form; ElementTree
        # re-serialization would turn it into ns0/ns1 and has previously made
        # otherwise valid projects unloadable.
        if b'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"' not in raw_model:
            raise AssertionError(f"{path.name}: core namespace declaration missing")
        model = ET.fromstring(raw_model)
        objects = model.findall(f"{CORE}resources/{CORE}object")
        build = model.findall(f"{CORE}build/{CORE}item")
        if len(objects) != 1 or len(build) != 1:
            raise AssertionError(f"{path.name}: expected exactly one object and one placed build item")
        if not objects[0].findall(f"{CORE}components/{CORE}component"):
            raise AssertionError(f"{path.name}: placed object has no mesh component")
        settings = json.loads(package.read("Metadata/project_settings.config"))
        expected = {
            "printer_model": "Bambu Lab X2D", "printable_height": "260",
            "wall_loops": "4", "sparse_infill_density": "25%", "brim_width": "4",
        }
        for key, value in expected.items():
            if settings.get(key) != value:
                raise AssertionError(f"{path.name}: {key} is {settings.get(key)!r}, not {value!r}")
        checked.append({"file": path.name, "objects": 1, "build_items": 1,
                        "zip_integrity": "passed", "settings": expected})

OUT.write_text(json.dumps({"status": "passed", "project_count": len(checked), "projects": checked}, ensure_ascii=False, indent=2))
print(json.dumps({"status": "passed", "project_count": len(checked)}, ensure_ascii=False))
