"""Exercise packaging without FreeCAD or slicing; protect the curated library."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from garage_bookshelf.paths import CAD, TMP, read_json, sha, write_json
from garage_bookshelf.printing.components import project_destination


class ComponentReleaseTests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TMP)
        self.folder = Path(self.temp.name)
        self.export = self.folder / 'export'
        self.printed = self.folder / 'print'
        self.export.mkdir()
        self.printed.mkdir()
        self.plan = read_json(ROOT / 'printing/plate-plan.json')
        (self.export / 'geometry.txt').write_text('geometry fixture')
        geometry = dict(status='passed', kind='geometry-export', cad_sha256=sha(CAD),
                        print_parts=[dict(part=part) for p in self.plan['plates'] for part in p['parts']],
                        files={'geometry.txt': sha(self.export / 'geometry.txt')})
        write_json(self.export / 'manifest.json', geometry)
        projects = []
        for p in self.plan['plates']:
            file = self.printed / (p['id'] + '.3mf')
            file.write_text(p['id'])
            projects.append(dict(id=p['id'], parts=p['parts'], project=file.name,
                                 project_sha256=sha(file), saved_project_reopened_and_sliced=True,
                                 reload_profile_overrides=False, warning_messages=[],
                                 estimated_seconds=60, estimated_filament_g=1))
        manifest = dict(status='passed', kind='colored-print-projects', cad_sha256=sha(CAD),
                        complete_plan=True, geometry_manifest_sha256=sha(self.export / 'manifest.json'),
                        plan_sha256=sha(ROOT / 'printing/plate-plan.json'), projects=projects,
                        files={p.name: sha(p) for p in self.printed.iterdir()})
        write_json(self.printed / 'manifest.json', manifest)
        self.before = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT / 'printing').rglob('*') if p.is_file()}

    def tearDown(self):
        after = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT / 'printing').rglob('*') if p.is_file()}
        self.assertEqual(self.before, after, 'Packaging must not alter current printing files')
        self.temp.cleanup()

    def package(self, output):
        return subprocess.run([sys.executable, str(ROOT / 'tools/package_release.py'),
                               '--export-dir', str(self.export), '--print-dir', str(self.printed),
                               '--release-id', 'component-test', '--output', str(output)],
                              capture_output=True, text=True)

    def test_complete_package_separates_unlettered_main_and_two_carriers(self):
        output = self.folder / 'package'
        result = self.package(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = read_json(output / 'package-manifest.json')
        self.assertEqual(manifest['plate_count'], 16)
        main = [p for p in manifest['projects'] if p['project'].startswith('main/')]
        self.assertEqual(len(main), 14)
        self.assertEqual(sum(len(p['parts']) for p in main), 40)
        for part, position in [('top_carrier', 'upper'), ('side_cartridge', 'side')]:
            record = next(p for p in manifest['projects'] if p['parts'] == [part])
            self.assertTrue(record['project'].startswith('sign-carriers/' + position + '/default/'))
        for relative, digest in manifest['files'].items():
            self.assertEqual(sha(output / relative), digest)

    def test_package_cannot_write_live_printing(self):
        result = self.package(ROOT / 'printing/main/new-package')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((ROOT / 'printing/main/new-package').exists())

    def test_package_preserves_existing_candidate(self):
        output = self.folder / 'package'
        output.mkdir()
        marker = output / 'personal.3mf'
        marker.write_text('keep')
        result = self.package(output)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), 'keep')

    def test_incomplete_print_set_cannot_be_packaged(self):
        manifest = read_json(self.printed / 'manifest.json')
        manifest['projects'].pop()
        manifest['complete_plan'] = False
        write_json(self.printed / 'manifest.json', manifest)
        result = self.package(self.folder / 'package')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('incomplete', result.stderr)

    def test_project_changed_after_verification_is_rejected(self):
        project = next(self.printed.glob('*.3mf'))
        project.write_text('edited after slicing')
        result = self.package(self.folder / 'package')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing, changed', result.stderr)

    def test_carrier_cannot_share_a_main_structure_plate(self):
        with self.assertRaises(ValueError):
            project_destination(['top_carrier', 'billboard'], 'mixed.3mf')


if __name__ == '__main__':
    unittest.main()
