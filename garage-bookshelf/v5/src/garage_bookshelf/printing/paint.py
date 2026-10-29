"""Bambu triangle paint, including adaptive splits across CAD colour ribbons.

Encoding follows BambuStudio TriangleSelector::serialize and
FacetsAnnotation::get_triangle_as_string. Filaments are 1-based states.
"""
import math

PALETTE = [('Black', '#16181B'), ('White', '#F4F5F6'),
           ('LightBlue', '#39A9DB'), ('DarkBlue', '#151B65'), ('Red', '#ED242A')]


def leaf(state):
    if not 0 <= state <= 17:
        raise ValueError('Unsupported paint state')
    return f'{state << 2:X}' if state < 3 else f'{state - 3:X}C'


def paint_states(encoded):
    """Validate one serialized triangle and recover its filament states."""
    stream = iter(int(c, 16) for c in reversed(encoded))
    pending, states = 1, set()
    while pending:
        code = next(stream)
        pending -= 1
        children = code & 3
        if children:
            pending += children+1
        elif code == 12:
            state, extra = 3, next(stream)
            while extra == 15:
                state += 15
                extra = next(stream)
            states.add(state+extra)
        else:
            states.add(code >> 2)
    if next(stream, None) is not None:
        raise ValueError('Extra data after triangle paint tree')
    return states


def area(poly):
    return abs(sum(a[0]*b[1]-b[0]*a[1]
                   for a, b in zip(poly, poly[1:]+poly[:1])))*.5


def clip(subject, polygon):
    """Intersect a polygon with a convex CAD profile, in its face plane."""
    signed = sum(a[0]*b[1]-b[0]*a[1]
                 for a, b in zip(polygon, polygon[1:]+polygon[:1]))
    direction = 1 if signed > 0 else -1
    out = list(subject)
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        def distance(p):
            return direction*((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
        before, out = out, []
        if not before:
            break
        previous, dp = before[-1], distance(before[-1])
        for current in before:
            dc = distance(current)
            if (dp >= 0) != (dc >= 0):
                t = dp/(dp-dc)
                out.append(tuple(p+t*(q-p) for p, q in zip(previous, current)))
            if dc >= 0:
                out.append(current)
            previous, dp = current, dc
    return out


def split_longest(triangle):
    # A one-side split bisects the edge opposite special_side. The child
    # ordering is the ordering used by TriangleSelector::perform_split.
    special = max(range(3), key=lambda i: sum((a-b)**2 for a, b in
                  zip(triangle[(i+1) % 3], triangle[(i+2) % 3])))
    a, b, c = (triangle[(special+i) % 3] for i in range(3))
    middle = tuple((x+y)*.5 for x, y in zip(b, c))
    return special, (a, b, middle), (middle, c, a), math.dist(b, c)


def paint_triangle(triangle, base, masks, tolerance=.20):
    """Paint a triangle in a planar CAD face, leaving its geometry unchanged.

    Masks contain (1-based filament state, convex 2-D profile). Mixed leaves
    are at most tolerance mm across. Uniform triangles need no subdivision.
    Returns Bambu's reverse-nibble string and painted leaf surface areas.
    """
    totals = {}

    def terminal(state, size):
        totals[state] = totals.get(state, 0.)+size
        return leaf(state)

    def visit(tri, candidates):
        size = area(list(tri))
        active = []
        for state, polygon in candidates:
            intersection = clip(list(tri), polygon)
            overlap = area(intersection) if len(intersection) >= 3 else 0.
            if overlap >= size-1e-8:
                return terminal(state, size)
            if overlap > 1e-9:
                active.append((state, polygon))
        if not active:
            return terminal(base, size)
        special, child0, child1, edge = split_longest(tri)
        if edge <= tolerance:
            center = tuple(sum(p[i] for p in tri)/3 for i in range(2))
            tiny = [(center[0]-1e-6, center[1]-1e-6),
                    (center[0]+1e-6, center[1]-1e-6),
                    (center[0], center[1]+1e-6)]
            for state, polygon in active:
                if len(clip(tiny, polygon)) >= 3:
                    return terminal(state, size)
            return terminal(base, size)
        result0, result1 = visit(child0, active), visit(child1, active)
        # Serialize visits child1 then child0, then reverses all nibbles.
        return result0+result1+f'{1 | (special << 2):X}'

    return visit(tuple(triangle), masks), totals
