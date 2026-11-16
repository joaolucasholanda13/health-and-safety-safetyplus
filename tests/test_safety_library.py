import json
import tempfile
import unittest
from pathlib import Path

from app.safety_library import prepare_library


class SafetyLibraryTests(unittest.TestCase):
    def test_uploads_and_deletions_survive_redeployment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundled = root / 'app' / 'info_docs' / 'momentos'
            bundled.mkdir(parents=True)
            items = [{'id': 'legacy', 'file': 'legacy.pdf'}]
            (bundled / 'manifest.json').write_text(json.dumps(items))
            (bundled / 'legacy.pdf').write_bytes(b'%PDF legacy upload')
            library = prepare_library(root / 'storage', bundled)
            self.assertEqual((library / 'legacy.pdf').read_bytes(), b'%PDF legacy upload')
            self.assertEqual(json.loads((library / 'manifest.json').read_text()), items)
            uploaded = [{'id': 'new', 'file': 'new.pdf'}]
            (library / 'new.pdf').write_bytes(b'%PDF new upload')
            (library / 'manifest.json').write_text(json.dumps(uploaded))
            (library / 'legacy.pdf').unlink()
            (bundled / 'manifest.json').write_text('[]')
            self.assertEqual(prepare_library(root / 'storage', bundled), library)
            self.assertEqual(json.loads((library / 'manifest.json').read_text()), uploaded)
            self.assertTrue((library / 'new.pdf').exists())
            self.assertFalse((library / 'legacy.pdf').exists())

    def test_invalid_legacy_manifest_does_not_initialize_empty_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'manifest.json').write_text('invalid')
            with self.assertRaises(ValueError):
                prepare_library(root / 'storage', root)
            self.assertFalse((root / 'storage/safety_moments/manifest.json').exists())
