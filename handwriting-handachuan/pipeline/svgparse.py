"""Parse simple M/L/Z polygon loops out of the layered SVGs."""
import re
from xml.etree import ElementTree as ET


def svg_loops(svg_path, canvas_w_px, canvas_h_px, out_w_mm, out_h_mm, z):
    """Return polygon point lists in CAD mm coords (SVG y-down -> CAD y-up)."""
    root = ET.parse(svg_path).getroot()
    loops = []
    for elem in root.iter():
        if not elem.tag.endswith('path'):
            continue
        d = elem.get('d')
        if not d:
            continue
        for sub in re.findall(r'M\s*([^Zz]+)', d):
            nums = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', sub)]
            if len(nums) < 6:
                continue
            pts = []
            for i in range(0, len(nums) - 1, 2):
                x = nums[i] * out_w_mm / canvas_w_px
                y = out_h_mm - nums[i + 1] * out_h_mm / canvas_h_px
                pts.append((x, y, z))
            if len(pts) >= 3:
                loops.append(pts)
    return loops
