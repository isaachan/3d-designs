"""Render the actual V3 STL, with the high back and the open rim in view."""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "preview"))
from render import box, lamp, material, photograph, stage


scene = stage(HERE.parent / "printing/bedside-slope-box.stl")
ground = material("Warm neutral backdrop", (0.58, 0.51, 0.42), 0.70)
box("Studio sweep", (0, 0, -0.013), (3, 3, 0.0258), ground)
lamp("Softbox", (-0.27, 0.21, 0.35), (0, 0.045, 0.04), 23, 0.27, (1, 0.91, 0.79))
lamp("Fill", (0.24, 0.30, 0.21), (0, 0.05, 0.06), 9, 0.25, (0.79, 0.89, 1))
lamp("Rim", (0.08, -0.24, 0.28), (0, 0.03, 0.05), 16, 0.24, (1, 0.96, 0.85))
photograph(scene, HERE / "slope-box.png", (0.33, 0.40, 0.42), (0, 0.048, 0.055), 0.304)
