"""Geometry detection helpers for the layered PNGs."""
from PIL import Image


def _alpha(png_path):
    img = Image.open(png_path).convert('RGBA')
    w, h = img.size
    return w, h, img.tobytes()[3::4]


def ruled_line_rows(png_path, min_coverage=0.15, alpha_threshold=30):
    """Return y-pixel centres of long horizontal ink rows.

    Rows are weighted by their opaque-pixel count so faded lines centre
    correctly; thin/faint rules survive via the low default thresholds.
    """
    w, h, alpha = _alpha(png_path)
    weights = []
    for y in range(h):
        count = 0
        base = y * w
        for x in range(w):
            if alpha[base + x] > alpha_threshold:
                count += 1
        weights.append(count)
    rows = [y for y, c in enumerate(weights) if c >= min_coverage * w]
    centres = []
    group = []
    for y in rows + [10**9]:
        if group and y != group[-1] + 1:
            centres.append(sum(y * weights[y] for y in group) / sum(weights[y] for y in group))
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
        'M {x0r:.1f} {y0:.1f} H {x1r:.1f} '
        'Q {x1:.1f} {y0:.1f} {x1:.1f} {y0r:.1f} V {y1r:.1f} '
        'Q {x1:.1f} {y1:.1f} {x1r:.1f} {y1:.1f} H {x0r:.1f} '
        'Q {x0:.1f} {y1:.1f} {x0:.1f} {y1r:.1f} V {y0r:.1f} '
        'Q {x0:.1f} {y0:.1f} {x0r:.1f} {y0:.1f} Z'.format(
            x0=x0, y0=y0, x1=x1, y1=y1,
            x0r=x0 + r, x1r=x1 - r, y0r=y0 + r, y1r=y1 - r)
    )
