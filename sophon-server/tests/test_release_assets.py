"""Release metadata and archives must be safe to publish and unpack."""
import hashlib
import importlib.util
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('release_assets', ROOT / '.github/scripts/release-assets.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseMetadataTests(unittest.TestCase):
    def test_stable_and_prerelease_package_versions(self):
        for tag, version, prerelease in [
            ('v1.2.3', '1.2.3', 'false'),
            ('v0.9.0-alpha', '0.9.0a0', 'true'),
            ('v0.9.0-beta.2', '0.9.0b2', 'true'),
            ('v1.0.0-rc1', '1.0.0rc1', 'true'),
        ]:
            with self.subTest(tag=tag):
                self.assertEqual(release.release_metadata(tag), {'version': version, 'prerelease': prerelease})

    def test_invalid_tags_are_rejected_before_release(self):
        for tag in ['main', 'v1.2', 'v1.2.3-final', 'v1.2.3-alpha\nversion=wrong']:
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release.release_metadata(tag)

    def test_client_version_changes_only_project_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / 'sophon-client/pyproject.toml'
            project.parent.mkdir()
            project.write_text('[project]\nname = "sophon-client"\nversion = "0.1.0"\ndependencies = ["rich>=14"]\n')
            with patch.object(release, 'ROOT', root):
                release.set_client_version('0.9.0a0')
            self.assertIn('version = "0.9.0a0"', project.read_text())
            self.assertIn('dependencies = ["rich>=14"]', project.read_text())


class ReleaseArchiveTests(unittest.TestCase):
    def make_distribution(self, root, platform):
        directory = root / 'build' / f'{platform}-x64/server.dist'
        directory.mkdir(parents=True)
        suffix = '.exe' if platform == 'win32' else ''
        for name in ['sophon-server' + suffix, 'hpatchz' + suffix, 'LICENSE.txt', 'dependency.bin']:
            (directory / name).write_bytes(b'release fixture')
        (directory / ('sophon-server' + suffix)).chmod(0o755)
        return directory

    def test_archives_include_runtime_dependencies_and_license(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for platform in ['linux', 'win32']:
                self.make_distribution(root, platform)
                with patch.object(release, 'ROOT', root):
                    result = release.archive_server(platform, 'x64', root / 'dist')
                if platform == 'win32':
                    with zipfile.ZipFile(result) as archive:
                        names = set(archive.namelist())
                else:
                    with tarfile.open(result) as archive:
                        names = set(archive.getnames())
                        self.assertTrue(archive.getmember('server.dist/sophon-server').mode & 0o111)
                self.assertIn('server.dist/dependency.bin', names)
                self.assertIn('server.dist/LICENSE.txt', names)

    def test_incomplete_distribution_cannot_be_archived(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = self.make_distribution(root, 'linux')
            (directory / 'hpatchz').unlink()
            with patch.object(release, 'ROOT', root), self.assertRaises(FileNotFoundError):
                release.archive_server('linux', 'x64', root / 'dist')

    def test_checksums_match_assets_and_remain_stable_on_rerun(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'asset.zip').write_bytes(b'release data')
            release.checksums(root)
            expected = hashlib.sha256(b'release data').hexdigest() + '  asset.zip\n'
            self.assertEqual((root / 'SHA256SUMS').read_text(), expected)
            release.checksums(root)
            self.assertEqual((root / 'SHA256SUMS').read_text(), expected)
