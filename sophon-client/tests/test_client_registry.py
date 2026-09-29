import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sophon_client.cli import API, ClientError, Registry, main, validate_directory


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / 'registry.json'

    def tearDown(self):
        self.temp.cleanup()

    def cli(self,*args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(['--registry',str(self.registry),*args])

    def test_register_overlap_and_forget_preserves_files(self):
        game = self.root / 'game'
        game.mkdir()
        (game/'keep').write_text('keep')
        self.assertEqual(self.cli('register','one',str(game),'--region','os'),0)
        self.assertEqual(self.cli('register','nested',str(game/'nested'),'--region','os'),1)
        self.assertEqual(self.cli('forget','one'),0)
        self.assertEqual((game/'keep').read_text(),'keep')

    def test_invalid_registry_is_preserved(self):
        self.registry.write_text('invalid')
        self.assertEqual(self.cli('register','one',str(self.root/'game'),'--region','os'),1)
        self.assertEqual(self.registry.read_text(),'invalid')
        self.assertFalse(self.registry.with_suffix('.lock').exists())

    def test_active_registry_lock_is_respected(self):
        self.registry.with_suffix('.lock').touch()
        with self.assertRaises(ClientError):
            with Registry(self.registry).edit():
                pass
        self.assertTrue(self.registry.with_suffix('.lock').exists())

    def test_server_url_and_directory_constraints(self):
        for url in ['http://example.org:8000','ftp://localhost','http://user@localhost']:
            with self.assertRaises(ClientError):
                API(url)
        for path in [Path.home(),Path(self.root.anchor)]:
            with self.assertRaises(ClientError):
                validate_directory(path)

    def test_hk4e_only_and_exact_version_validation(self):
        self.assertEqual(self.cli('register','one',str(self.root/'game'),'--region','os','--version','latest'),1)
        self.assertFalse(self.registry.exists())


if __name__ == '__main__':
    unittest.main()
