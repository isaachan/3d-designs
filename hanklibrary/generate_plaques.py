#!/usr/bin/env python3
"""Generate five-colour, multipart Hank's Library plaques from the source PNGs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from shapely import affinity
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box
from shapely.ops import unary_union
import trimesh


ROOT = Path(__file__).resolve().parent
IMAGE_DIR = ROOT / "images"
SOURCES = {
    "EN": IMAGE_DIR / "HankLibrary-five-color-no-gray-EN.png",
    "CN": IMAGE_DIR / "HankLibrary-five-color-no-gray-CN.png",
}

COLOR_ORDER = ("blue", "white", "black", "red", "yellow")
DISPLAY_RGB = {
    "blue": (8, 35, 82),
    "white": (245, 245, 238),
    "black": (18, 18, 20),
    "red": (190, 32, 22),
    "yellow": (249, 210, 42),
}


def rounded_rectangle(width: float, height: float, radius: float) -> Polygon:
    inner = box(
        -width / 2 + radius,
        -height / 2 + radius,
        width / 2 - radius,
        height / 2 - radius,
    )
    return inner.buffer(radius, resolution=12)


def classify_five_colours(rgb: np.ndarray) -> np.ndarray:
    """Return labels: blue=0, white=1, black=2, red=3, yellow=4."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, s, v = cv2.split(hsv)

    labels = np.full(h.shape, 2, dtype=np.uint8)  # black fallback
    labels[v >= 145] = 1

    colourful = s >= 70
    labels[colourful & (h >= 88) & (h <= 140)] = 0
    labels[colourful & ((h <= 10) | (h >= 170))] = 3
    labels[colourful & (h >= 16) & (h <= 38)] = 4

    # Very dark navy remains blue even when its saturation is reduced by texture.
    r, g, b = (rgb[..., i].astype(np.int16) for i in range(3))
    navy = (b >= r + 18) & (b >= g + 8) & (b <= 175)
    labels[navy] = 0
    return labels


def remove_small_islands(labels: np.ndarray, minimum_pixels: int) -> np.ndarray:
    """Replace tiny colour islands with the most common colour around them."""
    result = labels.copy()
    kernel = np.ones((3, 3), np.uint8)
    for _ in range(2):
        for colour_id in range(5):
            mask = (result == colour_id).astype(np.uint8)
            count, cc, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
            for component in range(1, count):
                area = int(stats[component, cv2.CC_STAT_AREA])
                if area >= minimum_pixels:
                    continue
                component_mask = (cc == component).astype(np.uint8)
                ring = cv2.dilate(component_mask, kernel, iterations=1).astype(bool)
                ring &= component_mask == 0
                neighbours = result[ring]
                neighbours = neighbours[neighbours != colour_id]
                if neighbours.size:
                    replacement = int(np.bincount(neighbours, minlength=5).argmax())
                    result[cc == component] = replacement
    return result


def mask_to_geometry(mask: np.ndarray, mm_per_pixel: float) -> Polygon | MultiPolygon:
    contours, hierarchy = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    if hierarchy is None:
        return GeometryCollection()
    hierarchy = hierarchy[0]
    polygons = []
    for index, contour in enumerate(contours):
        if hierarchy[index][3] != -1 or len(contour) < 3:
            continue
        shell = contour[:, 0, :].astype(float)
        holes = []
        child = hierarchy[index][2]
        while child != -1:
            if len(contours[child]) >= 3:
                holes.append(contours[child][:, 0, :].astype(float))
            child = hierarchy[child][0]
        polygon = Polygon(shell, holes)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if not polygon.is_empty:
            polygons.append(polygon)
    if not polygons:
        return GeometryCollection()
    geometry = unary_union(polygons)
    # Contours run through pixel centres; expand by half a pixel to recover cells.
    geometry = geometry.buffer(0.5, join_style="mitre")
    geometry = affinity.scale(geometry, xfact=mm_per_pixel, yfact=-mm_per_pixel, origin=(0, 0))
    return geometry


def polygon_parts(geometry):
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    return [g for g in geometry.geoms if isinstance(g, Polygon)]


def regularize_for_printing(geometry, opening: float = 0.01, minimum_area: float = 0.30):
    """Remove sub-nozzle slivers and tiny bodies which can break triangulation."""
    geometry = geometry.buffer(-opening).buffer(opening).buffer(0)
    parts = [part for part in polygon_parts(geometry) if part.area >= minimum_area]
    return unary_union(parts) if parts else GeometryCollection()


def svg_path(geometry: Polygon | MultiPolygon) -> str:
    chunks = []
    for polygon in polygon_parts(geometry):
        for ring in (polygon.exterior, *polygon.interiors):
            points = list(ring.coords)
            if len(points) < 3:
                continue
            chunks.append("M " + " L ".join(f"{x:.3f},{-y:.3f}" for x, y in points) + " Z")
    return " ".join(chunks)


def write_svg(path: Path, layers: dict[str, Polygon | MultiPolygon], width: float, height: float):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" height="{height}mm" '
        f'viewBox="{-width/2} {-height/2} {width} {height}">',
    ]
    for name in COLOR_ORDER:
        colour = "#%02x%02x%02x" % DISPLAY_RGB[name]
        lines.append(
            f'  <path id="{name}" fill="{colour}" fill-rule="evenodd" d="{svg_path(layers[name])}"/>'
        )
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def extrude_geometry(geometry, height: float, z_offset: float = 0.0):
    meshes = []
    for polygon in polygon_parts(geometry):
        if polygon.area < 0.01:
            continue
        mesh = trimesh.creation.extrude_polygon(polygon, height=height, engine="manifold")
        if z_offset:
            mesh.apply_translation((0, 0, z_offset))
        meshes.append(mesh)
    if not meshes:
        raise RuntimeError("No printable polygons were generated")
    return trimesh.util.concatenate(meshes)


def render_preview(path: Path, layers, width: float, height: float, px_per_mm: int = 6):
    canvas = Image.new("RGB", (round(width * px_per_mm), round(height * px_per_mm)), "white")
    draw = ImageDraw.Draw(canvas)
    for name in COLOR_ORDER:
        for polygon in polygon_parts(layers[name]):
            shell = [((x + width / 2) * px_per_mm, (height / 2 - y) * px_per_mm) for x, y in polygon.exterior.coords]
            draw.polygon(shell, fill=DISPLAY_RGB[name])
            for hole in polygon.interiors:
                # Holes are subsequently filled by another colour layer; blue is a safe interim fill.
                coords = [((x + width / 2) * px_per_mm, (height / 2 - y) * px_per_mm) for x, y in hole.coords]
                draw.polygon(coords, fill=DISPLAY_RGB["blue"])
    canvas.save(path)


def build_one(language: str, args) -> dict:
    source = SOURCES[language]
    rgb = np.array(Image.open(source).convert("RGB"))
    source_height, source_width = rgb.shape[:2]

    scale = min(args.width / source_width, args.height / source_height)
    art_width = source_width * scale
    art_height = source_height * scale
    labels = remove_small_islands(classify_five_colours(rgb), args.minimum_island_pixels)

    plaque = rounded_rectangle(args.width, args.height, args.corner_radius)
    raw = {}
    x_shift = -art_width / 2
    y_shift = art_height / 2
    for colour_id, name in enumerate(COLOR_ORDER):
        geom = mask_to_geometry(labels == colour_id, scale)
        geom = affinity.translate(geom, xoff=x_shift, yoff=y_shift)
        raw[name] = geom.intersection(plaque)

    # Resolve half-pixel boundary overlaps in favour of small/accent colours.
    resolved = {}
    occupied = GeometryCollection()
    for name in ("red", "yellow", "black", "white"):
        geom = raw[name].difference(occupied).buffer(0)
        geom = regularize_for_printing(geom)
        resolved[name] = geom
        occupied = unary_union((occupied, geom))
    resolved["blue"] = plaque.difference(occupied).buffer(0)

    out = args.output / language
    out.mkdir(parents=True, exist_ok=True)
    write_svg(out / f"HankLibrary-{language}-five-colour.svg", resolved, args.width, args.height)
    render_preview(out / f"HankLibrary-{language}-preview.png", resolved, args.width, args.height)

    base_mesh = extrude_geometry(plaque, args.base_thickness)
    stats = {}
    for name in COLOR_ORDER:
        face_mesh = extrude_geometry(resolved[name], args.face_thickness, args.base_thickness)
        if name == "blue":
            mesh = trimesh.boolean.union((base_mesh.copy(), face_mesh), engine="manifold")
        else:
            mesh = face_mesh
        mesh.remove_unreferenced_vertices()
        target = out / f"HankLibrary-{language}-{name}.stl"
        mesh.export(target)
        stats[name] = {
            "area_mm2": round(resolved[name].area, 2),
            "bodies": len(polygon_parts(resolved[name])),
            "watertight": bool(mesh.is_watertight),
            "file": target.name,
        }

    report = {
        "language": language,
        "source": source.name,
        "source_pixels": [source_width, source_height],
        "finished_size_mm": [args.width, args.height, args.base_thickness + args.face_thickness],
        "art_size_mm": [round(art_width, 3), round(art_height, 3)],
        "corner_radius_mm": args.corner_radius,
        "minimum_island_pixels": args.minimum_island_pixels,
        "colours": stats,
        "label_pixel_counts": dict(Counter(COLOR_ORDER[int(x)] for x in labels.ravel())),
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=float, default=240.0)
    parser.add_argument("--height", type=float, default=50.0)
    parser.add_argument("--base-thickness", type=float, default=2.4)
    parser.add_argument("--face-thickness", type=float, default=0.6)
    parser.add_argument("--corner-radius", type=float, default=3.0)
    parser.add_argument("--minimum-island-pixels", type=int, default=12)
    parser.add_argument("--output", type=Path, default=ROOT / "generated")
    args = parser.parse_args()
    args.output = args.output.resolve()

    reports = [build_one(language, args) for language in ("EN", "CN")]
    print(json.dumps(reports, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
