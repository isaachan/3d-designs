"""Check the formal CAD without saving it or exporting geometry."""
import argparse
import _bootstrap
from garage_bookshelf.paths import output_directory, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', help='Empty output directory under v5/build/')
    args = parser.parse_args()
    from garage_bookshelf.validation import validate
    output = output_directory(args.output, 'validate')
    report = validate()
    write_json(output / 'validation.json', report)
    print(report['status'].upper(), output, report.get('counts'), report['errors'], flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
