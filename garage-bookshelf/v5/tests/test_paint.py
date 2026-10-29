"""Check geometric colour coverage independently of a particular CAD model."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from garage_bookshelf.printing.paint import paint_triangle, paint_states, clip, area


class PaintTests(unittest.TestCase):
    def test_partial_ribbon_is_not_lost_when_original_triangle_vertices_are_outside(self):
        triangle = [(0., 0.), (120., 0.), (0., 120.)]
        ribbon = [(40., -1.), (80., -1.), (80., 121.), (40., 121.)]
        encoded, areas = paint_triangle(triangle, 1, [(5, ribbon)], tolerance=.20)
        self.assertEqual(paint_states(encoded), {1, 5})
        self.assertAlmostEqual(sum(areas.values()), 7200.)
        # Both boundary segments total 120 mm; at .20 mm resolution their
        # combined possible area error is bounded by 120*.20 mm squared.
        self.assertAlmostEqual(areas[5], 2400., delta=120*.20)

    def test_three_equal_width_ribbons_keep_their_distinct_colours(self):
        triangle = [(0., 0.), (120., 0.), (0., 120.)]
        masks = [(i+3, [(x, -1.), (x+40., -1.), (x+40., 121.), (x, 121.)])
                 for i, x in enumerate((0., 40., 80.))]
        encoded, areas = paint_triangle(triangle, 1, masks, tolerance=.20)
        self.assertEqual(paint_states(encoded), {3, 4, 5})
        self.assertAlmostEqual(sum(areas.values()), 7200.)
        for state, expected in ((3, 4000.), (4, 2400.), (5, 800.)):
            self.assertAlmostEqual(areas[state], expected, delta=3.)

    def test_cad_profile_winding_does_not_change_coverage(self):
        triangle = [(0., 0.), (120., 0.), (0., 120.)]
        rectangle = [(40., -1.), (80., -1.), (80., 121.), (40., 121.)]
        for polygon in (rectangle, rectangle[::-1]):
            self.assertAlmostEqual(area(clip(triangle, polygon)), 2400.)


if __name__ == '__main__':
    unittest.main()
