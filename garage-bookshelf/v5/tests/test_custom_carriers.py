"""Check the actual saved custom CAD and Bambu projects, without a CAD runtime."""
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from garage_bookshelf.paths import read_json
from garage_bookshelf.printing.paint import PALETTE, paint_states
from garage_bookshelf.printing.threemf import NS


class CustomCarrierArtifactTests(unittest.TestCase):
    def setUp(self):
        self.records = read_json(ROOT / 'printing/catalog.json').get('custom_carriers', [])
        if not self.records:
            self.skipTest('No registered custom carriers')

    def test_native_cad_has_one_editable_carrier_and_the_registered_text(self):
        for record in self.records:
            with self.subTest(position=record['position'], variant=record['id']):
                with ZipFile(ROOT / record['source_cad']) as archive:
                    doc = ET.fromstring(archive.read('Document.xml'))
                types = {o.get('name'): o.get('type') for o in doc.findall('./Objects/Object')}
                bodies = [name for name, kind in types.items() if kind == 'PartDesign::Body']
                self.assertEqual(len(bodies), 1)
                props = doc.find(f'./ObjectData/Object[@name="{bodies[0]}"]/Properties')
                text = props.find('./Property[@name="CustomText"]/String').get('value')
                self.assertEqual(text, record['text'])
                tip = props.find('./Property[@name="Tip"]/Link').get('value')
                self.assertEqual(types[tip], 'PartDesign::Pad' if record['position'] == 'upper' else 'PartDesign::Pocket')

    def test_saved_projects_preserve_position_specific_background_and_white_text(self):
        for record in self.records:
            with self.subTest(position=record['position'], variant=record['id']):
                with ZipFile(ROOT / 'printing' / record['project']) as archive:
                    settings = json.loads(archive.read('Metadata/project_settings.config'))
                    self.assertEqual(settings['filament_colour'], [value for _, value in PALETTE])
                    states = set()
                    for name in archive.namelist():
                        if name.startswith('3D/Objects/') and name.endswith('.model'):
                            for triangle in ET.fromstring(archive.read(name)).findall('.//c:triangle', NS):
                                states.update(paint_states(triangle.get('paint_color')))
                    self.assertEqual(states, {1, 2} if record['position'] == 'upper' else {2, 4})
                    self.assertFalse(any(name.endswith('.gcode') for name in archive.namelist()))


if __name__ == '__main__':
    unittest.main()
