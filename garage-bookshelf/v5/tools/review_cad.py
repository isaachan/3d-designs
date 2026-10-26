"""FreeCAD GUI entry; default restores the view in memory, --save persists it."""
import argparse
import _bootstrap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save', action='store_true', help='Save restored colors and view into the formal CAD')
    args = parser.parse_args()
    from garage_bookshelf.appearance.view import review
    review(save=args.save)


if __name__ == '__main__':
    main()
