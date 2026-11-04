"""Reject unsafe generator destinations and mismatched published parking evidence."""
import copy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from garage_bookshelf.parking.artifacts import output_artifact, parking_stem
from garage_bookshelf.paths import CAD, TMP, read_json, sha, write_json
from garage_bookshelf.printing.parking import METHOD, verify_parking_inserts


class ParkingGeneratorPathTests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TMP)
        self.folder = Path(self.temp.name)
        self.out = self.folder / 'run'
        self.out.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_ids_produce_only_paths_inside_the_run(self):
        stem = parking_stem('bmw-m4', 'r1')
        for name in (stem + '.FCStd', stem + '.3mf', 'evidence/' + stem + '.stl'):
            self.assertTrue(output_artifact(self.out, name).is_relative_to(self.out))
        self.assertEqual(list(self.out.iterdir()), [])

    def test_cli_rejects_invalid_identifiers_before_loading_cad_or_creating_output(self):
        before = sha(CAD)
        invalid = ('../../cad/garage-bookshelf-v5', '/tmp/car', '..', 'car/name',
                   'car\\name', '', 'BMW-M4', None)
        for field in ('variant', 'revision'):
            for value in invalid:
                with self.subTest(field=field, value=value):
                    spec = dict(variant='test-car', revision='r1')
                    spec[field] = value
                    file = self.folder / 'measurements.json'
                    write_json(file, spec)
                    output = self.folder / 'rejected-output'
                    result = subprocess.run([sys.executable, str(ROOT / 'tools/make_parking_insert.py'),
                                             '--spec', str(file), '--output', str(output)],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(field + ' must be', result.stderr)
                    self.assertFalse(output.exists())
        self.assertEqual(sha(CAD), before)

    def test_destination_guard_rejects_traversal_and_absolute_paths(self):
        marker = self.folder / 'authored.FCStd'
        marker.write_text('preserve authored file')
        for target in ('../authored.FCStd', str(marker), '../../cad/garage-bookshelf-v5-assembly.FCStd'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                output_artifact(self.out, target)
        self.assertEqual(marker.read_text(), 'preserve authored file')

    def test_destination_guard_rejects_symlink_escape_and_existing_output(self):
        elsewhere = self.folder / 'authored'
        elsewhere.mkdir()
        (self.out / 'evidence').symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaises(ValueError):
            output_artifact(self.out, 'evidence/car.stl')
        current = self.out / 'car.FCStd'
        current.write_text('preserve output')
        with self.assertRaises(FileExistsError):
            output_artifact(self.out, current.name)
        self.assertEqual(current.read_text(), 'preserve output')
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_destination_guard_rejects_authored_output_directories(self):
        with self.assertRaises(ValueError):
            output_artifact(ROOT / 'cad', 'car.FCStd')


class ParkingCatalogTests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TMP)
        self.root = Path(self.temp.name)
        self.cad_dir = self.root / 'cad/parking-inserts/test-car/r1'
        self.print_dir = self.root / 'printing/parking-inserts/test-car/r1'
        self.cad_dir.mkdir(parents=True)
        (self.print_dir / 'evidence').mkdir(parents=True)
        self.cad = self.cad_dir / 'test-car-r1.FCStd'
        self.cad.write_bytes(b'native CAD verified by generator')
        self.project = self.print_dir / 'test-car-r1.3mf'
        self.project.write_bytes(b'saved project verified by generator')
        self.photo = self.root / 'assets/measurements/photo.jpg'
        self.photo.parent.mkdir(parents=True)
        self.photo.write_bytes(b'original measurements')
        values = dict(S=51, Bf=28, Br=28, Df=10, Dr=10, Tf=5.1, Tr=5.1)
        source = dict(path=self.relative(self.photo), sha256=sha(self.photo))
        self.spec = dict(variant='test-car', revision='r1', interface='parking-base-v1',
                         model_label='TEST CAR', measurements_mm=values, measurement_source=source)
        self.measurements = self.cad_dir / 'measurements.json'
        write_json(self.measurements, self.spec)
        self.outline = self.cad_dir / 'model-label-outline.json'
        write_json(self.outline, dict(text='TEST CAR'))
        self.slice = self.print_dir / 'slice-result.json'
        write_json(self.slice, dict(return_code=0, sliced_plates=[dict(objects=[dict(id=1)], warning_message='')]))
        self.log = self.print_dir / 'evidence/slice.log'
        self.log.write_text('raw tool output')
        paths = (self.cad, self.project, self.measurements, self.outline, self.slice, self.log)
        self.report_path = self.print_dir / 'validation.json'
        self.report = dict(status='passed', saved_project_reopened_and_sliced=True,
                           source_cad='cad/assembly.FCStd', cad_sha256='formal CAD revision',
                           variant='test-car', revision='r1', interface='parking-base-v1',
                           model_label='TEST CAR', design_method=METHOD,
                           measurements_mm=values, measurement_source=source, physical_fit_tested=False,
                           files={p.name: sha(p) for p in paths},
                           artifact_locations={p.name: self.relative(p) for p in paths})
        self.record = dict(id='test-car', revision='r1', interface='parking-base-v1',
                           model_label='TEST CAR', design_method=METHOD,
                           source_cad=self.relative(self.cad), source_cad_sha256=sha(self.cad),
                           project=self.project.relative_to(self.root / 'printing').as_posix(),
                           sha256=sha(self.project), measurements=self.relative(self.measurements),
                           evidence=self.relative(self.report_path), measurements_mm=values,
                           physical_fit_tested=False)
        self.catalog = dict(source_cad='cad/assembly.FCStd', cad_sha256='formal CAD revision',
                            parking_inserts=[self.record], files={
                                p.relative_to(self.root / 'printing').as_posix(): sha(p)
                                for p in paths if p.is_relative_to(self.print_dir)})
        self.save_report()

    def relative(self, path):
        return path.relative_to(self.root).as_posix()

    def save_report(self):
        write_json(self.report_path, self.report)
        self.catalog['files'][self.report_path.relative_to(self.root / 'printing').as_posix()] = sha(self.report_path)

    def tearDown(self):
        self.temp.cleanup()

    def verify(self):
        verify_parking_inserts(self.catalog, self.root)

    def test_matching_revision_and_actual_published_legacy_reference_pass(self):
        self.verify()
        verify_parking_inserts(read_json(ROOT / 'printing/catalog.json'))

    def test_changed_cad_measurements_photo_outline_and_raw_evidence_are_rejected(self):
        for path in (self.cad, self.measurements, self.photo, self.outline, self.log):
            original = path.read_bytes()
            with self.subTest(path=path.name):
                path.write_bytes(original + b' ')
                with self.assertRaises(ValueError):
                    self.verify()
                path.write_bytes(original)

    def test_report_from_another_revision_or_cad_and_unverified_status_are_rejected(self):
        for key, value in (('revision', 'r2'), ('cad_sha256', 'another assembly'),
                           ('variant', 'another-car'), ('status', 'failed'),
                           ('saved_project_reopened_and_sliced', False), ('physical_fit_tested', True)):
            original = self.report[key]
            with self.subTest(key=key):
                self.report[key] = value
                self.save_report()
                with self.assertRaises(ValueError):
                    self.verify()
                self.report[key] = original
        self.save_report()

    def test_wrong_directories_and_missing_revision_cannot_bypass_checks(self):
        for key, value in (('source_cad', 'cad/assembly.FCStd'), ('project', '../test-car-r1.3mf'),
                           ('evidence', 'build/validation.json'), ('revision', None)):
            record = self.catalog['parking_inserts'][0]
            original = record[key]
            with self.subTest(key=key):
                record[key] = value
                with self.assertRaises(ValueError):
                    self.verify()
                record[key] = original

    def test_measurement_values_must_agree_across_catalog_input_and_report(self):
        self.record['measurements_mm'] = dict(self.record['measurements_mm'], Bf=30)
        with self.assertRaisesRegex(ValueError, 'measurements differ'):
            self.verify()

    def test_hashes_and_locations_must_cover_all_inputs_and_stay_in_the_variant(self):
        original = copy.deepcopy(self.report)
        del self.report['files']['measurements.json']
        del self.report['artifact_locations']['measurements.json']
        self.save_report()
        with self.assertRaisesRegex(ValueError, 'missing artifact'):
            self.verify()
        self.report = original
        misplaced = self.root / 'build/test-car-r1.FCStd'
        misplaced.parent.mkdir()
        shutil.copy2(self.cad, misplaced)
        self.report['artifact_locations'][self.cad.name] = self.relative(misplaced)
        self.save_report()
        with self.assertRaisesRegex(ValueError, 'misplaced'):
            self.verify()

    def test_failed_slice_is_rejected_even_with_matching_file_hashes(self):
        write_json(self.slice, dict(return_code=1, sliced_plates=[]))
        self.report['files'][self.slice.name] = sha(self.slice)
        self.catalog['files'][self.slice.relative_to(self.root / 'printing').as_posix()] = sha(self.slice)
        self.save_report()
        with self.assertRaisesRegex(ValueError, 'slice result'):
            self.verify()


if __name__ == '__main__':
    unittest.main()
