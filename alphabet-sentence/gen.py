#!/usr/bin/env python3
"""统计英文句子的字母用量，复制 Alphabet 字母网格，拼出一盘可直接打印的 3MF。"""

import argparse
import json
import math
import re
import sys
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

APOSTROPHE = "'"
QUOTE_VARIANTS = ("\u2019", "\u2018", "\u0060", "\u00b4")

LETTER_TO_FILE = {
    "A": 19, "B": 1, "C": 18, "D": 12, "E": 17, "F": 20, "G": 16,
    "H": 21, "I": 15, "J": 22, "K": 11, "L": 23, "M": 13, "N": 14,
    "O": 25, "P": 10, "Q": 26, "R": 9, "S": 2, "T": 8, "U": 3,
    "V": 7, "W": 4, "X": 6, "Y": 5, "Z": 24,
}
APOSTROPHE_FILE = 27

APOSTROPHE_WIDTH = 3.03
APOSTROPHE_HEIGHT = 6.0
LETTER_DEPTH = 5.0
LETTER_HEIGHT = 15.0

SKILL_DIR = Path(__file__).resolve().parent
BUNDLED_BASE = SKILL_DIR / "assets" / "alphabet-base.3mf"
FALLBACK_BASE = Path.home() / "Downloads" / "Alphabet.3mf"
PRINTER_SETTINGS = {
    "x2d": SKILL_DIR / "assets" / "settings-x2d.json",
    "p1s": SKILL_DIR / "assets" / "settings-p1s.json",
}
DEFAULT_PRINTER = "x2d"

NAMESPACE = uuid.UUID("6d5b0c52-92c1-4b0e-9a3c-3f1c8d47a100")
CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PROD_NS = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
BAMBU_NS = "http://schemas.bambulab.com/package/2021"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""


def fmt(value):
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def uid(tag):
    return str(uuid.uuid5(NAMESPACE, tag))


def count_letters(sentence):
    counts = {}
    sequence = []
    unknown = []
    seen = set()
    for char in sentence:
        if char.isspace():
            continue
        letter = char.upper()
        if letter in QUOTE_VARIANTS or letter == APOSTROPHE:
            letter = APOSTROPHE
        elif "A" <= letter <= "Z":
            pass
        else:
            if char not in seen:
                seen.add(char)
                unknown.append(char)
            continue
        counts[letter] = counts.get(letter, 0) + 1
        sequence.append(letter)
    return counts, sequence, unknown


def read_object(zf, file_no):
    path = f"3D/Objects/object_{file_no}.model"
    raw = zf.read(path).decode("utf-8")
    vertices = [
        (float(x), float(y), float(z))
        for x, y, z in re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', raw)
    ]
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    info = {
        "cx": (min(xs) + max(xs)) / 2,
        "cy": (min(ys) + max(ys)) / 2,
        "minz": min(zs),
        "faces": len(re.findall(r"<triangle ", raw)),
    }
    return raw, info


def apostrophe_model():
    x0, x1 = -APOSTROPHE_WIDTH / 2, APOSTROPHE_WIDTH / 2
    y0, y1 = LETTER_HEIGHT / 2 - APOSTROPHE_HEIGHT, LETTER_HEIGHT / 2
    z0, z1 = -LETTER_DEPTH / 2, LETTER_DEPTH / 2
    corners = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
    ]
    vertex_xml = "\n".join(
        f'     <vertex x="{fmt(x)}" y="{fmt(y)}" z="{fmt(z)}"/>' for x, y, z in corners
    )
    triangle_xml = "\n".join(
        f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in faces
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="{CORE_NS}" xmlns:BambuStudio="{BAMBU_NS}" xmlns:p="{PROD_NS}" requiredextensions="p">
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <resources>
  <object id="{2 * APOSTROPHE_FILE - 1}" p:UUID="{uid('object/apostrophe')}" type="model">
   <mesh>
    <vertices>
{vertex_xml}
    </vertices>
    <triangles>
{triangle_xml}
    </triangles>
   </mesh>
  </object>
 </resources>
</model>
"""


def parse_plate(settings_raw):
    settings = json.loads(settings_raw)
    area = settings.get("printable_area") or ["0x0", "256x0", "256x256", "0x256"]
    corners = [tuple(float(n) for n in point.lower().split("x")) for point in area]
    plate_w = max(x for x, _ in corners)
    plate_h = max(y for _, y in corners)
    rects = []
    for key in ("bed_exclude_area", "wrapping_exclude_area"):
        points = settings.get(key) or []
        if len(points) < 2:
            continue
        values = [tuple(float(n) for n in point.lower().split("x")) for point in points]
        xs = [x for x, _ in values]
        ys = [y for _, y in values]
        rects.append((min(xs), min(ys), max(xs), max(ys)))
    return plate_w, plate_h, rects


def validate_printer_settings(settings):
    filaments = settings.get("filament_colour") or []
    if not filaments:
        raise ValueError("缺少 filament_colour，Bambu Studio 会报 Invalid configuration file")
    if "extruder_variant_list" in settings:
        variants = settings.get("filament_extruder_variant") or []
        self_index = settings.get("filament_self_index") or []
        if len(variants) != len(self_index) or len(variants) < len(filaments):
            raise ValueError("filament_extruder_variant 与 filament_self_index 长度不一致")


def layout(sequence, spacing, columns, plate_w, plate_h):
    if columns is None:
        columns = max(1, math.ceil(math.sqrt(len(sequence))))
    rows = math.ceil(len(sequence) / columns)
    cells = []
    for index, letter in enumerate(sequence):
        row, col = divmod(index, columns)
        cell_x = plate_w / 2 + (col - (columns - 1) / 2) * spacing
        cell_y = plate_h / 2 + ((rows - 1) / 2 - row) * spacing
        cells.append((letter, cell_x, cell_y))
    return cells, columns, rows


def render_3dmodel(order, instances, title, description):
    objects = []
    for letter in order:
        file_no = APOSTROPHE_FILE if letter == APOSTROPHE else LETTER_TO_FILE[letter]
        objects.append(
            f"""  <object id="{2 * file_no}" p:UUID="{uid(f'wrapper/{letter}')}" type="model">
   <components>
    <component p:path="/3D/Objects/object_{file_no}.model" objectid="{2 * file_no - 1}" p:UUID="{uid(f'component/{letter}')}" transform="1 0 0 0 1 0 0 0 1 0 0 0" />
   </components>
  </object>"""
        )
    items = []
    for index, inst in enumerate(instances):
        file_no = APOSTROPHE_FILE if inst["letter"] == APOSTROPHE else LETTER_TO_FILE[inst["letter"]]
        items.append(
            f'  <item objectid="{2 * file_no}" p:UUID="{uid(f"item/{index}")}" '
            f'transform="1 0 0 0 1 0 0 0 1 {fmt(inst["tx"])} {fmt(inst["ty"])} {fmt(inst["tz"])}" printable="1" />'
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="{CORE_NS}" xmlns:p="{PROD_NS}" requiredextensions="p" xmlns:BambuStudio="{BAMBU_NS}">
 <metadata name="Application">BambuStudio-01.10.01.50</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <metadata name="Title">{escape(title)}</metadata>
 <metadata name="Description">{escape(description)}</metadata>
 <resources>
{chr(10).join(objects)}
 </resources>
 <build>
{chr(10).join(items)}
 </build>
</model>
"""


def render_model_rels(order):
    rels = []
    for rel_index, letter in enumerate(order, start=1):
        file_no = APOSTROPHE_FILE if letter == APOSTROPHE else LETTER_TO_FILE[letter]
        rels.append(
            f' <Relationship Target="/3D/Objects/object_{file_no}.model" Id="rel-{rel_index}" '
            f'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{chr(10).join(rels)}
</Relationships>
"""


def render_settings(order, instances, face_counts):
    blocks = []
    first_offset = {}
    for inst in instances:
        first_offset.setdefault(inst["letter"], inst)
    for letter in order:
        file_no = APOSTROPHE_FILE if letter == APOSTROPHE else LETTER_TO_FILE[letter]
        inner = 2 * file_no - 1
        wrapper = 2 * file_no
        name = f"Letter {letter}" if letter != APOSTROPHE else "Apostrophe"
        offset = first_offset[letter]
        blocks.append(
            f"""  <object id="{wrapper}">
    <metadata key="name" value="{escape(name)}"/>
    <metadata key="extruder" value="1"/>
    <metadata face_count="{face_counts[letter]}"/>
    <part id="{inner}" subtype="normal_part">
      <metadata key="name" value="{escape(name)}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="source_object_id" value="0"/>
      <metadata key="source_volume_id" value="0"/>
      <metadata key="source_offset_x" value="{fmt(offset["tx"])}"/>
      <metadata key="source_offset_y" value="{fmt(offset["ty"])}"/>
      <metadata key="source_offset_z" value="{fmt(offset["tz"])}"/>
      <mesh_stat face_count="{face_counts[letter]}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>
  </object>"""
        )

    instance_ids = {}
    plate_instances = []
    assemble_items = []
    for index, inst in enumerate(instances):
        letter = inst["letter"]
        file_no = APOSTROPHE_FILE if letter == APOSTROPHE else LETTER_TO_FILE[letter]
        wrapper = 2 * file_no
        instance_id = instance_ids.get(wrapper, 0)
        instance_ids[wrapper] = instance_id + 1
        transform = f"1 0 0 0 1 0 0 0 1 {fmt(inst['tx'])} {fmt(inst['ty'])} {fmt(inst['tz'])}"
        plate_instances.append(
            f"""    <model_instance>
      <metadata key="object_id" value="{wrapper}"/>
      <metadata key="instance_id" value="{instance_id}"/>
      <metadata key="identify_id" value="{1000 + index}"/>
    </model_instance>"""
        )
        assemble_items.append(
            f'   <assemble_item object_id="{wrapper}" instance_id="{instance_id}" '
            f'transform="{transform}" offset="0 0 0" />'
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<config>
{chr(10).join(blocks)}
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value=""/>
    <metadata key="locked" value="false"/>
{chr(10).join(plate_instances)}
  </plate>
  <assemble>
{chr(10).join(assemble_items)}
  </assemble>
</config>
"""


def main():
    parser = argparse.ArgumentParser(description="按句子字母用量生成字母打印盘 3MF")
    parser.add_argument("sentence", help="英文句子，字母统一按大写统计，只保留 A-Z 和撇号")
    parser.add_argument("-o", "--output", help="输出 3MF 路径，默认当前目录下 <句子>.3mf")
    parser.add_argument(
        "--base",
        help="基础 3MF，默认优先用 skill 自带 assets/alphabet-base.3mf，否则 ~/Downloads/Alphabet.3mf",
    )
    parser.add_argument(
        "--printer",
        default=DEFAULT_PRINTER,
        help="打印机预设 x2d（默认）或 p1s，也可给 Bambu Studio project_settings JSON 路径",
    )
    parser.add_argument("--spacing", type=float, default=20.0, help="字母格距，单位 mm，默认 20")
    parser.add_argument("--columns", type=int, help="每行个数，默认按总数取近似方形")
    args = parser.parse_args()
    if args.columns is not None and args.columns < 1:
        parser.error("--columns 必须 >= 1")
    if args.spacing <= 0:
        parser.error("--spacing 必须大于 0")

    base = Path(args.base).expanduser() if args.base else (BUNDLED_BASE if BUNDLED_BASE.is_file() else FALLBACK_BASE)
    if not base.is_file():
        sys.exit(f"找不到基础文件：{base}")

    printer = args.printer.lower()
    if printer in PRINTER_SETTINGS:
        settings_path = PRINTER_SETTINGS[printer]
    else:
        settings_path = Path(args.printer).expanduser()
        if not settings_path.is_file():
            sys.exit(f"不认识的打印机预设：{args.printer}（可选 x2d / p1s，或 profile JSON 路径）")

    counts, sequence, unknown = count_letters(args.sentence)
    if not counts:
        sys.exit("句子里没有可打印的字母")
    if unknown:
        print(f"忽略的字符：{' '.join(repr(c) for c in unknown)}", file=sys.stderr)

    project_settings = settings_path.read_bytes()
    try:
        settings_data = json.loads(project_settings)
        validate_printer_settings(settings_data)
        plate_w, plate_h, exclude_rects = parse_plate(project_settings)
        printer_name = settings_data.get("printer_settings_id") or printer
    except (json.JSONDecodeError, ValueError) as err:
        sys.exit(f"打印机预设不可用（{err}）：{settings_path}")

    with zipfile.ZipFile(base) as zf:
        object_raw = {}
        object_info = {}
        face_counts = {}
        for letter in counts:
            file_no = APOSTROPHE_FILE if letter == APOSTROPHE else LETTER_TO_FILE[letter]
            if letter == APOSTROPHE:
                object_raw[letter] = apostrophe_model().encode("utf-8")
                object_info[letter] = {"cx": 0.0, "cy": 0.0, "minz": -LETTER_DEPTH / 2, "faces": 12}
            else:
                raw, info = read_object(zf, file_no)
                object_raw[letter] = raw.encode("utf-8")
                object_info[letter] = info
            face_counts[letter] = object_info[letter]["faces"]

    order = sorted(counts, key=lambda c: (c == APOSTROPHE, c))
    cells, columns, rows = layout(sequence, args.spacing, args.columns, plate_w, plate_h)

    instances = []
    for letter, cell_x, cell_y in cells:
        info = object_info[letter]
        instances.append({
            "letter": letter,
            "tx": cell_x - info["cx"],
            "ty": cell_y - info["cy"],
            "tz": -info["minz"],
        })

    half = LETTER_HEIGHT / 2
    problems = []
    for letter, cell_x, cell_y in cells:
        if (
            cell_x - half < 0
            or cell_x + half > plate_w
            or cell_y - half < 0
            or cell_y + half > plate_h
        ):
            problems.append(f"{letter} 超出打印板")
            break
    for letter, cell_x, cell_y in cells:
        for x0, y0, x1, y1 in exclude_rects:
            if cell_x + half > x0 and cell_x - half < x1 and cell_y + half > y0 and cell_y - half < y1:
                problems.append(f"{letter} 与排除区（如擦嘴区）重叠")
                break
    if problems:
        print(
            f"警告：{'；'.join(sorted(set(problems)))}。"
            "可调整 --spacing / --columns，或减小句子长度。",
            file=sys.stderr,
        )

    slug_source = re.sub(r"[^A-Za-z0-9]+", "-", args.sentence).strip("-").lower()
    output = Path(args.output) if args.output else Path(f"{slug_source or 'letters'}.3mf")

    model = render_3dmodel(
        order,
        instances,
        f"句子字母 · {args.sentence}",
        f"按句子统计生成的字母盘，共 {len(instances)} 件：{args.sentence}",
    )
    rels = render_model_rels(order)
    settings = render_settings(order, instances, face_counts)

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as out:
        out.writestr("[Content_Types].xml", CONTENT_TYPES)
        out.writestr("_rels/.rels", ROOT_RELS)
        out.writestr("3D/3dmodel.model", model)
        out.writestr("3D/_rels/3dmodel.model.rels", rels)
        for letter in order:
            file_no = APOSTROPHE_FILE if letter == APOSTROPHE else LETTER_TO_FILE[letter]
            out.writestr(f"3D/Objects/object_{file_no}.model", object_raw[letter])
        out.writestr("Metadata/model_settings.config", settings)
        out.writestr("Metadata/project_settings.config", project_settings)

    xs = [cell[1] for cell in cells]
    ys = [cell[2] for cell in cells]
    extent = max(max(xs) - min(xs), max(ys) - min(ys)) + LETTER_HEIGHT
    summary = "  ".join(
        f"{letter} ×{counts[letter]}" if letter != APOSTROPHE else f"' ×{counts[letter]}"
        for letter in order
    )
    print(f"句子：{args.sentence}")
    print(f"打印机：{printer_name}")
    print(f"用件：{summary}")
    print(f"顺序：{' '.join(sequence)}")
    print(
        f"布局：{columns} 列 × {rows} 行，格距 {args.spacing:g} mm，"
        f"占用约 {extent:.0f} mm（板 {plate_w:g} × {plate_h:g} mm）"
    )
    print(f"输出：{output.resolve()}")


if __name__ == "__main__":
    main()
