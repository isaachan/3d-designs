"""Layered PNG -> handwriting.svg tracing.

Port of the original one-off tracer: alpha threshold, drop tiny specks,
follow pixel boundary loops, simplify with Douglas-Peucker.
"""
from PIL import Image


def alpha_mask(png_path, threshold):
    img = Image.open(png_path).convert('RGBA')
    w, h = img.size
    alpha = img.tobytes()[3::4]
    return w, h, [a > threshold for a in alpha]


def remove_small_components(mask, w, h, min_px):
    seen = [False] * (w * h)
    for start in range(w * h):
        if not mask[start] or seen[start]:
            continue
        stack, comp = [start], []
        seen[start] = True
        while stack:
            p = stack.pop()
            comp.append(p)
            x, y = p % w, p // w
            for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                if 0 <= nx < w and 0 <= ny < h:
                    n = ny * w + nx
                    if mask[n] and not seen[n]:
                        seen[n] = True
                        stack.append(n)
        if len(comp) < min_px:
            for p in comp:
                mask[p] = False


def _rdp(points, epsilon):
    if len(points) < 3:
        return points
    ax, ay = points[0]
    bx, by = points[-1]
    dx, dy = bx - ax, by - ay
    index, max_d = 0, 0.0
    if dx == 0 and dy == 0:
        norm = 0.0
    else:
        norm = (dx * dx + dy * dy) ** 0.5
    for i, (px, py) in enumerate(points):
        d = abs(dy * px - dx * py + bx * ay - by * ax) / norm if norm else ((px-ax)**2 + (py-ay)**2) ** 0.5
        if d > max_d:
            max_d, index = d, i
    if max_d > epsilon:
        left = _rdp(points[:index+1], epsilon)
        right = _rdp(points[index:], epsilon)
        return left[:-1] + right
    return [points[0], points[-1]]


def boundary_loops(mask, w, h, epsilon, min_loop_points=12):
    """Directed exposed-cell edges; each pixel side is one oriented edge."""
    nxt = {}

    def add(a, b):
        nxt.setdefault(a, []).append(b)

    for y in range(h):
        row = y * w
        for x in range(w):
            if not mask[row + x]:
                continue
            if y == 0 or not mask[row - w + x]:
                add((x, y), (x + 1, y))
            if x == w - 1 or not mask[row + x + 1]:
                add((x + 1, y), (x + 1, y + 1))
            if y == h - 1 or not mask[row + w + x]:
                add((x + 1, y + 1), (x, y + 1))
            if x == 0 or not mask[row + x - 1]:
                add((x, y + 1), (x, y))

    loops = []
    while nxt:
        start, outs = next(iter(nxt.items()))
        current = outs.pop()
        if not outs:
            del nxt[start]
        loop = [start]
        while current != start:
            loop.append(current)
            outs = nxt.get(current)
            if not outs:
                break  # open chain (should not happen on closed masks)
            nxt[current] = outs[:-1]
            if not nxt[current]:
                del nxt[current]
            current = outs[-1]
        if len(loop) > min_loop_points:
            loops.append(_rdp(loop + [loop[0]], epsilon))
    return loops


def trace_handwriting_png(png_path, alpha_threshold=48, min_component_px=180, simplify_epsilon=1.7):
    w, h, mask = alpha_mask(png_path, alpha_threshold)
    remove_small_components(mask, w, h, min_component_px)
    loops = boundary_loops(mask, w, h, simplify_epsilon)
    d_attr = ' '.join(
        'M ' + ' L '.join('%.1f %.1f' % p for p in loop) + ' Z' for loop in loops
    )
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n'
        '  <path fill="#006fe6" fill-rule="evenodd" d="%s"/>\n'
        '</svg>\n' % (w, h, w, h, d_attr)
    )
    return svg, len(loops)
