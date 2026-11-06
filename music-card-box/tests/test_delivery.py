"""Integration checks for the actual delivered artifacts, not modeling internals."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from verify import check_manifest,check_3mf,check_links

class DeliveryTests(unittest.TestCase):
    def test_hashed_native_sources_and_evidence(self):
        self.assertGreater(check_manifest(),20)

    def test_portable_print_meshes_and_outward_normals(self):
        self.assertEqual(check_3mf(),12)

    def test_document_and_image_links(self):
        self.assertGreater(check_links(),30)

if __name__=='__main__':unittest.main()
