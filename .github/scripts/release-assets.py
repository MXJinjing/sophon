"""Prepare versioned client packages and portable server release assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]


def release_metadata(tag):
    match = re.fullmatch(r'v(\d+\.\d+\.\d+)(?:-(alpha|beta|rc)(?:[.-]?(\d+))?)?', tag)
    if not match:
        raise ValueError('Expected vX.Y.Z or vX.Y.Z-alpha/beta/rc[.N]')
    base, pre, number = match.groups()
    suffix = {'alpha': 'a', 'beta': 'b', 'rc': 'rc'}
    version = base + (suffix[pre] + (number or '0') if pre else '')
    return {'version': version, 'prerelease': str(bool(pre)).lower()}


def set_client_version(version):
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?', version):
        raise ValueError('Invalid client package version')
    path = ROOT / 'sophon-client' / 'pyproject.toml'
    content, count = re.subn(r'(?m)^version = "[^"]+"$', f'version = "{version}"', path.read_text())
    if count != 1:
        raise ValueError('Expected exactly one project version')
    path.write_text(content)


def archive_server(platform, arch, output):
    directory = ROOT / 'build' / f'{platform}-{arch}' / 'server.dist'
    executable = directory / ('sophon-server.exe' if platform == 'win32' else 'sophon-server')
    helper = directory / ('hpatchz.exe' if platform == 'win32' else 'hpatchz')
    for required in (executable, helper, directory / 'LICENSE.txt'):
        if not required.is_file():
            raise FileNotFoundError(required)
    output.mkdir(parents=True, exist_ok=True)
    base = output / f'sophon-server-{platform}-{arch}'
    return shutil.make_archive(str(base), 'zip' if platform == 'win32' else 'gztar',
                               root_dir=directory.parent, base_dir=directory.name)


def smoke_server(platform, arch):
    # Port 0 lets Uvicorn select an available port; discover it from its startup log.
    directory = ROOT / 'build' / f'{platform}-{arch}' / 'server.dist'
    executable = directory / ('sophon-server.exe' if platform == 'win32' else 'sophon-server')
    import tempfile
    with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as log:
        env = dict(os.environ, SOPHON_HOST='127.0.0.1', SOPHON_PORT='0')
        process = subprocess.Popen([str(executable)], cwd=directory, env=env, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                log.seek(0)
                message = log.read()
                if process.poll() is not None:
                    raise RuntimeError(f'Compiled server exited: {message}')
                match = re.search(r'http://127\.0\.0\.1:(\d+)', message)
                if match:
                    try:
                        with urlopen(f'http://127.0.0.1:{match[1]}/health', timeout=2) as response:
                            if json.load(response).get('status') == 'healthy':
                                return
                    except OSError:
                        pass
                time.sleep(.2)
            raise TimeoutError(f'Compiled server health check timed out: {message}')
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def checksums(directory):
    files = sorted(p for p in directory.iterdir() if p.is_file() and p.name != 'SHA256SUMS')
    if not files:
        raise ValueError('No release assets')
    lines = []
    for path in files:
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        lines.append(f'{digest}  {path.name}\n')
    (directory / 'SHA256SUMS').write_text(''.join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    metadata = commands.add_parser('metadata')
    metadata.add_argument('--tag', required=True)
    metadata.add_argument('--output', type=Path, required=True)
    version = commands.add_parser('client-version')
    version.add_argument('--version', required=True)
    for name in ('archive', 'smoke'):
        command = commands.add_parser(name)
        command.add_argument('--platform', choices=['linux', 'win32', 'darwin'], required=True)
        command.add_argument('--arch', choices=['x64', 'arm64'], required=True)
        if name == 'archive':
            command.add_argument('--output', type=Path, default=ROOT / 'dist')
    checksum = commands.add_parser('checksums')
    checksum.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'metadata':
        values = release_metadata(args.tag)
        with args.output.open('a', encoding='utf-8') as stream:
            for key, value in values.items():
                stream.write(f'{key}={value}\n')
    elif args.command == 'client-version':
        set_client_version(args.version)
    elif args.command == 'archive':
        print(archive_server(args.platform, args.arch, args.output))
    elif args.command == 'smoke':
        smoke_server(args.platform, args.arch)
    else:
        checksums(args.directory)


if __name__ == '__main__':
    main()
