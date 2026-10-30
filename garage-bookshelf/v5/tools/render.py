"""Render saved geometry and materials without saving the formal CAD."""
import argparse
import _bootstrap
from garage_bookshelf.paths import CAD, output_directory, sha, source_record, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', help='Empty output directory under v5/build/')
    args = parser.parse_args()
    import FreeCAD as App
    from garage_bookshelf.specification import bodies, appearance_graphics
    from garage_bookshelf.rendering.software import appearance_triangles, render, saved_colors
    output = output_directory(args.output, 'render')
    before = sha(CAD)
    doc = App.openDocument(str(CAD))
    try:
        colors = saved_colors(CAD)
        objects = bodies(doc) + appearance_graphics(doc)
        points, paint = appearance_triangles(doc, colors, objects)
        record = render(points, paint, output / 'assembly.png', [-1.1, -2.4, 1.45], 1800, 1200)
    finally:
        App.closeDocument(doc.Name)
    assert sha(CAD) == before
    write_json(output / 'render.json', dict(source_record(), status='passed', cad_unchanged=True,
                                          native_faces_and_saved_materials=True, previews=[record]))
    print('PASS', output)


if __name__ == '__main__':
    main()
