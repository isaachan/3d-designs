"""Check that the selection project contains exactly modules 2, 3, and 5."""
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "print" / "projects" / "modules-2-3-5-view-x2d-pla.3mf"
OUT = Path(__file__).resolve().parent / "modules-2-3-5-view-validation.json"
CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"

with zipfile.ZipFile(PATH) as package:
    if package.testzip():
        raise AssertionError("corrupt ZIP")
    model = ET.fromstring(package.read("3D/3dmodel.model"))
    build = model.findall(f"{CORE}build/{CORE}item")
    if len(build) != 3:
        raise AssertionError(f"expected 3 build items, got {len(build)}")
    settings = json.loads(package.read("Metadata/project_settings.config"))
    if settings.get("printer_model") != "Bambu Lab X2D":
        raise AssertionError("wrong printer model")
    model_settings = ET.fromstring(package.read("Metadata/model_settings.config"))
    names = []
    for obj in model_settings.findall("object"):
        for metadata in obj.findall("metadata"):
            if metadata.get("key") == "name": names.append(metadata.get("value"))
    expected = {"module_2.stl", "module_3.stl", "module_5.stl"}
    if set(names) != expected:
        raise AssertionError(f"wrong objects: {names}")

OUT.write_text(json.dumps({"status":"passed", "build_items":3, "object_names":sorted(names),
                            "purpose":"selection/view only; not one-plate print"}, ensure_ascii=False, indent=2))
print(json.dumps({"status":"passed", "build_items":3, "objects":sorted(names)}, ensure_ascii=False))
