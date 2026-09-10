"""Apply the project-specific X2D and structural-test settings to an exported 3MF."""
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])

with zipfile.ZipFile(source) as incoming:
    entries = {entry.filename: incoming.read(entry.filename) for entry in incoming.infolist()}

settings_name = "Metadata/project_settings.config"
settings = json.loads(entries[settings_name])
settings.update({
    "printer_model": "Bambu Lab X2D",
    "printable_area": ["0x0", "256x0", "256x256", "0x256"],
    "printable_height": "261",
    "wall_loops": "4",
    "sparse_infill_density": "25%",
    "brim_width": "0",
})
entries[settings_name] = (json.dumps(settings, indent=4, ensure_ascii=False) + "\n").encode()

# Bambu Studio's headless arranger keeps a global workspace coordinate when it
# creates multiple plates.  Reposition the six test plates explicitly, both in
# the 3MF build transforms and the project-side matrices used by the GUI.
layout = {
    "01_divider_base_coupon.stl": (-230, 0),
    "01_right_base_coupon.stl": (-470, 0),
    "04_right_lower_panel.stl": (0, 250),
    "03_divider_back_join_plate.stl": (0, 238),
    "03_right_back_join_plate.stl": (0, 238),
    "02_divider_back_left.stl": (-211, 235),
    "02_divider_back_right.stl": (-229, 235),
    "02_right_back_left.stl": (-451, 235),
    "02_right_back_right.stl": (-469, 235),
}

model_settings_name = "Metadata/model_settings.config"
model_settings = ET.fromstring(entries[model_settings_name])
name_by_id = {}
for obj in model_settings.findall("object"):
    name = next(item.get("value") for item in obj.findall("metadata") if item.get("key") == "name")
    name_by_id[obj.get("id")] = name

# Do not re-serialize Bambu Studio's XML: ElementTree changes its required
# namespace prefixes, which makes Bambu Studio discard the project data. Edit
# only the build-item transform text and leave all namespaces untouched.
model_name = "3D/3dmodel.model"
model_text = entries[model_name].decode("utf-8")
for object_id, name in name_by_id.items():
    dx, dy = layout.get(name, (0, 0))
    if dx == 0 and dy == 0:
        continue
    pattern = rf'(<item objectid="{object_id}"[^>]* transform=")([^"]+)(")'
    def move(match):
        values = [float(value) for value in match.group(2).split()]
        values[9] += dx
        values[10] += dy
        return match.group(1) + " ".join(f"{value:g}" for value in values) + match.group(3)
    model_text, count = re.subn(pattern, move, model_text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not update build transform for {name}")
entries[model_name] = model_text.encode("utf-8")

with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as outgoing:
    for name, content in entries.items():
        outgoing.writestr(name, content)
