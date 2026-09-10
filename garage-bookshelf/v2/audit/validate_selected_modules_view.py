"""Check that the selection project contains exactly modules 2, 3, and 5."""
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    "production": ("modules-2-3-5-view-x2d-pla.3mf", "modules-2-3-5-view-validation.json", {"module_2.stl", "module_3.stl", "module_5.stl"}),
    "narrow": ("modules-2-5-narrow-visual-x2d-pla.3mf", "modules-2-5-narrow-visual-validation.json", {"module_2_narrow_visual.stl", "module_5_narrow_visual.stl"}),
}
profile = sys.argv[1] if len(sys.argv) > 1 else "production"
if profile not in PROFILES:
    raise SystemExit(f"usage: {Path(__file__).name} [{'|'.join(PROFILES)}]")
file_name, audit_name, expected = PROFILES[profile]
PATH = ROOT / "print" / "projects" / file_name
OUT = Path(__file__).resolve().parent / audit_name
CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"

with zipfile.ZipFile(PATH) as package:
    if package.testzip():
        raise AssertionError("corrupt ZIP")
    model = ET.fromstring(package.read("3D/3dmodel.model"))
    build = model.findall(f"{CORE}build/{CORE}item")
    if len(build) != len(expected):
        raise AssertionError(f"expected {len(expected)} build items, got {len(build)}")
    settings = json.loads(package.read("Metadata/project_settings.config"))
    if settings.get("printer_model") != "Bambu Lab X2D":
        raise AssertionError("wrong printer model")
    model_settings = ET.fromstring(package.read("Metadata/model_settings.config"))
    names = []
    for obj in model_settings.findall("object"):
        for metadata in obj.findall("metadata"):
            if metadata.get("key") == "name": names.append(metadata.get("value"))
    if set(names) != expected:
        raise AssertionError(f"wrong objects: {names}")
    plates = model_settings.findall("plate")
    if len(plates) != len(expected):
        raise AssertionError(f"expected {len(expected)} dedicated plates, got {len(plates)}")
    plate_object_ids = []
    for index, plate in enumerate(plates, 1):
        instance = plate.find("model_instance")
        object_id = next((m.get("value") for m in instance.findall("metadata") if m.get("key") == "object_id"), None)
        if not object_id or f"Metadata/plate_{index}.json" not in package.namelist():
            raise AssertionError(f"plate {index} missing object association or manifest")
        plate_object_ids.append(object_id)
    if len(set(plate_object_ids)) != len(expected):
        raise AssertionError("plates do not map one-to-one to objects")

OUT.write_text(json.dumps({"status":"passed", "build_items":len(expected), "object_names":sorted(names),
                            "plates":len(expected), "purpose":"individually printable X2D plates"}, ensure_ascii=False, indent=2))
print(json.dumps({"status":"passed", "build_items":len(expected), "plates":len(expected), "objects":sorted(names)}, ensure_ascii=False))
