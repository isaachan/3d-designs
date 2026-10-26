"""Protect authored files and reject stale or altered manufacturing outputs."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from garage_bookshelf.paths import CAD, TMP, output_directory, read_json, sha, write_json
from garage_bookshelf.printing.manifests import verified_manifest
from garage_bookshelf.printing.threemf import project_bounds


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TMP)
        self.folder = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def fixture_manifest(self):
        file = self.folder / 'artifact.txt'
        file.write_text('verified output')
        manifest = dict(status='passed', kind='geometry-export', cad_sha256=sha(CAD),
                        files={file.name: sha(file)})
        write_json(self.folder / 'manifest.json', manifest)
        return manifest

    def test_generated_output_cannot_overwrite_authored_directories(self):
        for name in ('cad', 'printing/projects', 'studies', 'releases', 'src'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                output_directory(ROOT / name / 'test-output')

    def test_existing_output_is_preserved(self):
        file = self.folder / 'hand-edited.3mf'
        file.write_bytes(b'authored data')
        with self.assertRaises(FileExistsError):
            output_directory(self.folder)
        self.assertEqual(file.read_bytes(), b'authored data')

    def test_manifest_rejects_changed_output(self):
        self.fixture_manifest()
        verified_manifest(self.folder, 'geometry-export')
        (self.folder / 'artifact.txt').write_text('changed after validation')
        with self.assertRaisesRegex(ValueError, 'missing, changed'):
            verified_manifest(self.folder, 'geometry-export')

    def test_manifest_rejects_stale_source(self):
        manifest = self.fixture_manifest()
        manifest['cad_sha256'] = '0' * 64
        write_json(self.folder / 'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'Source CAD changed'):
            verified_manifest(self.folder, 'geometry-export')

    def test_manifest_cannot_read_outside_its_run(self):
        manifest = self.fixture_manifest()
        manifest['files'] = {str(Path(__file__)): sha(__file__)}
        write_json(self.folder / 'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'outside run directory'):
            verified_manifest(self.folder, 'geometry-export')

    def test_saved_trial_3mf_keeps_two_real_objects_in_print_bounds(self):
        project = ROOT / 'studies/parking-tray-fit-2026-10-26/TEMP-3bay-deck-and-one-parking-tray.3mf'
        bounds = project_bounds(project)
        self.assertEqual(len(bounds), 2)
        dimensions = [[hi - lo for lo, hi in zip(p['min_mm'], p['max_mm'])] for p in bounds]
        self.assertAlmostEqual(max(d[0] for d in dimensions), 195.6, places=2)

    def test_plate_plan_covers_current_print_parts_once(self):
        plan = read_json(ROOT / 'printing/plate-plan.json')
        parts = [name for plate in plan['plates'] for name in plate['parts']]
        expected = read_json(ROOT / 'cad/model-spec.json')['print_parts']
        self.assertCountEqual(parts, expected)
        self.assertEqual(len(parts), len(set(parts)))


if __name__ == '__main__':
    unittest.main()
