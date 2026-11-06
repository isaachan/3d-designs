"""Geometry detection helpers for the layered PNGs."""
from PIL import Image


def _alpha(png_path):
    img = Image.open(png_path).convert('RGBA')
    w, h = img.size
    return w, h, img.tobytes()[3::4]


def ruled_line_rows(png_path, min_coverage=0.5, alpha_threshold=128):
    """Return y-pixel centres of long horizontal ink rows."""
    w, h, alpha = _alpha(png_path)
    rows = []
    for y in range(h):
        count = 0
        base = y * w
        for x in range(w):
            if alpha[base + x] > alpha_threshold:
                count += 1
        if count >= min_coverage * w:
            rows.append(y)
    centres = []
    group = []
    for y in rows + [10**9]:
        if group and y != group[-1] + 1:
            centres.append(sum(group) / len(group))
            group = []
        group.append(y)
    return centres


def paper_bbox(png_path, alpha_threshold=128):
    w, h, alpha = _alpha(png_path)
    xs, ys = [], []
    for y in range(h):
        base = y * w
        for x in range(w):
            if alpha[base + x] > alpha_threshold:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise ValueError('paper_outline.png has no opaque pixels')
    return min(xs), min(ys), max(xs), max(ys)


def rounded_rect_path_px(x0, y0, x1, y1, r):
    return (
        'M %.1f %.1f H %.1f Q %.1f %.1f %.1f %.1f V %.1f Q %.1f %.1f %.1f %.1f H %.1f '
        'Q %.1f %.1f %.1f %.1f V %.1f Q %.1f %.1f %.1f %.1f Z'
        % (x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, y1 - r, x1, y1, x1, y1 - r,
           x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0, x0 + r, y0)
    )
