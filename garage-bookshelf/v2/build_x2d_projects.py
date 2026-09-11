"""Build one verified X2D 3MF project per v2 STL using Bambu Studio CLI.

The CLI is invoked with an absolute STL path before options.  XML is edited as
text only: XML re-serialization changes Bambu's namespace prefixes and makes a
project invalid.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


# Optional file stems make it safe to regenerate one experimental part without
# touching every checked-in print project, e.g. ``python build_x2d_projects.py
# module_5_narrow_visual``.  With no arguments the production batch behavior
# remains unchanged.
requested_stems = set(sys.argv[1:])

ROOT = Path(__file__).resolve().parent
STL, OUT = ROOT / "stl", ROOT / "print" / "projects"
OUT.mkdir(parents=True, exist_ok=True)
BAMBU = "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
PROD = "{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}"
MARGIN, BED, HEIGHT = 4.0, 256.0, 260.0


def transform(values, point):
    # 3MF transform order is the column-major form used in existing audits.
    v = [float(x) for x in values.split()]
    return (v[0]*point[0]+v[3]*point[1]+v[6]*point[2]+v[9],
            v[1]*point[0]+v[4]*point[1]+v[7]*point[2]+v[10],
            v[2]*point[0]+v[5]*point[1]+v[8]*point[2]+v[11])


def place_x2d(raw, destination):
    with zipfile.ZipFile(raw) as source:
        entries = {entry.filename: source.read(entry.filename) for entry in source.infolist()}
    settings_name = "Metadata/project_settings.config"
    settings = json.loads(entries[settings_name])
    settings.update({
        "printer_model": "Bambu Lab X2D",
        "printable_area": ["0x0", "256x0", "256x256", "0x256"],
        "printable_height": "260",
        "wall_loops": "4",
        "sparse_infill_density": "25%",
        "brim_width": "4",
    })
    entries[settings_name] = (json.dumps(settings, indent=4, ensure_ascii=False) + "\n").encode()

    model_settings = ET.fromstring(entries["Metadata/model_settings.config"])
    names = {obj.get("id"): next(m.get("value") for m in obj.findall("metadata") if m.get("key") == "name") for obj in model_settings.findall("object")}
    model = ET.fromstring(entries["3D/3dmodel.model"])
    objects = {obj.get("id"): obj for obj in model.findall(f"{CORE}resources/{CORE}object")}
    raw_text = entries["3D/3dmodel.model"].decode("utf-8")

    placements = []
    for item in model.findall(f"{CORE}build/{CORE}item"):
        object_id = item.get("objectid")
        points = []
        for component in objects[object_id].findall(f"{CORE}components/{CORE}component"):
            sub = ET.fromstring(entries[component.get(f"{PROD}path").lstrip("/")])
            sub_obj = next(obj for obj in sub.findall(f"{CORE}resources/{CORE}object") if obj.get("id") == component.get("objectid"))
            for vertex in sub_obj.findall(f"{CORE}mesh/{CORE}vertices/{CORE}vertex"):
                local = (float(vertex.get("x")), float(vertex.get("y")), float(vertex.get("z")))
                points.append(transform(item.get("transform"), transform(component.get("transform"), local)))
        mins = [min(p[i] for p in points) for i in range(3)]
        maxs = [max(p[i] for p in points) for i in range(3)]
        dims = [maxs[i]-mins[i] for i in range(3)]
        if dims[0] + 2*MARGIN > BED or dims[1] + 2*MARGIN > BED or dims[2] > HEIGHT:
            raise RuntimeError(f"{names[object_id]} exceeds X2D envelope: {dims}")
        dx, dy = MARGIN - mins[0], MARGIN - mins[1]
        pattern = rf'(<item objectid="{object_id}"[^>]* transform=")([^"]+)(")'
        def move(match):
            values = [float(x) for x in match.group(2).split()]
            values[9] += dx; values[10] += dy
            return match.group(1) + " ".join(f"{x:g}" for x in values) + match.group(3)
        raw_text, count = re.subn(pattern, move, raw_text, count=1)
        if count != 1: raise RuntimeError(f"Could not reposition {names[object_id]}")
        placements.append({"name":names[object_id],"dimensions_mm":dims,"xy_margin_mm":MARGIN})
    entries["3D/3dmodel.model"] = raw_text.encode()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, content in entries.items(): target.writestr(name, content)
    return placements


report = []
sources = sorted(STL.glob("*.stl"))
if requested_stems:
    unknown = requested_stems - {source.stem for source in sources}
    if unknown:
        raise SystemExit(f"Unknown STL stem(s): {', '.join(sorted(unknown))}")
    sources = [source for source in sources if source.stem in requested_stems]
for source in sources:
    with tempfile.TemporaryDirectory() as temp:
        raw = Path(temp) / "raw.3mf"
        subprocess.run([BAMBU, str(source.resolve()), "--arrange", "1", "--ensure-on-bed", "--export-3mf", str(raw)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        output = OUT / f"{source.stem}-x2d-pla.3mf"
        report.extend(place_x2d(raw, output))
if not requested_stems:
    (ROOT / "audit" / "print-layout.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(f"Generated and placed {len(report)} X2D projects in {OUT}")
