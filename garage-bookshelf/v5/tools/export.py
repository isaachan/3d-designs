"""Validate and export STEP and both STL coordinate conventions into build/."""
import argparse
import _bootstrap
from garage_bookshelf.paths import output_directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', help='Empty output directory under v5/build/')
    args = parser.parse_args()
    from garage_bookshelf.exporting import export
    output = output_directory(args.output, 'export')
    manifest = export(output)
    print('PASS', len(manifest['print_parts']), 'print parts;', manifest['step_solids'], 'STEP solids;', output)


if __name__ == '__main__':
    main()
