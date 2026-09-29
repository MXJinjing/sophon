import pathlib
import tempfile
import unittest
from unittest.mock import patch
import build
import infrastructure.platform as runtime


class PlatformBuildTests(unittest.TestCase):
    def test_configs(self):
        for target, arch, asset, suffix in [('linux','x64','linux-x86_64',''), ('linux','arm64','linux-aarch_64',''), ('win32','x64','win64','.exe'), ('darwin','arm64','osx-universal_binary','')]:
            c = build.configuration(target, arch)
            self.assertTrue(c['protoc_url'].endswith(asset + '.zip'))
            self.assertIn('--output-filename=sophon-server' + suffix, c['command'])
            self.assertEqual(pathlib.Path(c['hpatchz']).name, 'hpatchz' + suffix)
        with self.assertRaises(ValueError):
            build.configuration('win32', 'arm64')

    def test_runtime_platforms(self):
        for target, filename in [('linux','hpatchz'), ('win32','hpatchz.exe')]:
            with tempfile.TemporaryDirectory() as d, patch.object(runtime.sys, 'platform', target), patch.object(runtime.platform, 'machine', return_value='AMD64'), patch.dict(runtime.os.environ, {}, clear=True), patch.object(runtime.shutil, 'which', return_value=None), patch.object(runtime.ctypes, 'CDLL', side_effect=AssertionError('must not load macOS libc')):
                root = pathlib.Path(d)
                tool = root / 'bin' / target / 'x64' / filename
                tool.parent.mkdir(parents=True)
                tool.touch()
                self.assertEqual(runtime.resolve_hpatchz(root), tool)
                runtime.memory_relief()


if __name__ == '__main__':
    unittest.main()
