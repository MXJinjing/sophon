"""Standard-library client; game work is performed by the local Sophon server."""
import argparse
import configparser
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib import request, parse, error

SUPPORTED = {'hk4e': ('os', 'cn', 'bb')}
TERMINAL = {'completed', 'failed', 'cancelled'}


class ClientError(Exception):
    pass


class API:
    def __init__(self, base, timeout=120):
        url = parse.urlsplit(base)
        if url.scheme not in {'http', 'https'} or url.hostname not in {'127.0.0.1', 'localhost', '::1'} or url.query or url.fragment or url.username:
            raise ClientError('Use a local http(s) server URL; game paths refer to the server computer')
        self.base = base.rstrip('/')
        self.timeout = timeout

    def call(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = request.Request(self.base + path, data=data, method=method,
                              headers={'Content-Type': 'application/json'})
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.load(response)
        except error.HTTPError as exc:
            detail = exc.read().decode(errors='replace')
            raise ClientError(f'HTTP {exc.code}: {detail}') from exc
        except (error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise ClientError(f'Server request failed: {exc}') from exc


class Registry:
    def __init__(self, path):
        self.path = Path(path).expanduser()

    def read(self):
        if not self.path.exists():
            return {'schema': 1, 'games': {}, 'jobs': {}}
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if data.get('schema') != 1 or not isinstance(data.get('games'), dict) or not isinstance(data.get('jobs'), dict):
                raise ValueError('unsupported registry schema')
            return data
        except (ValueError, OSError) as exc:
            raise ClientError(f'Invalid registry {self.path}: {exc}') from exc

    @contextmanager
    def edit(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix('.lock')
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise ClientError(f'Registry locked: {lock}; if a previous client crashed, remove this lock after confirming it has exited') from None
        try:
            os.close(fd)
            data = self.read()
            yield data
            temp = self.path.with_suffix('.tmp')
            with temp.open('w', encoding='utf-8') as stream:
                json.dump(data, stream, indent=2, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.path)
        finally:
            lock.unlink(missing_ok=True)

    def game(self, name):
        try:
            return self.read()['games'][name]
        except KeyError:
            raise ClientError(f'Unknown game directory: {name}; use register first') from None


def installed_version(path):
    cfg = configparser.ConfigParser()
    try:
        cfg.read(Path(path) / 'config.ini', encoding='utf-8-sig')
        return cfg.get('General', 'game_version', fallback=None)
    except (configparser.Error, OSError, UnicodeError):
        return None


def validate_directory(path):
    path = Path(path).expanduser().resolve()
    if path == Path(path.anchor) or path == Path.home().resolve():
        raise ClientError('Choose a dedicated game directory')
    if path.exists() and not path.is_dir():
        raise ClientError(f'Not a directory: {path}')
    return path


def emit(data, json_mode):
    if json_mode:
        print(json.dumps(data, ensure_ascii=False), flush=True)
    elif isinstance(data, dict):
        print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)
    else:
        print(data, flush=True)


def task_status(api, task_id):
    value = api.call('GET', f'/api/tasks/{parse.quote(task_id, safe="")}/status')
    if not value.get('status'):
        raise ClientError(value.get('error') or 'Task not found; server may have restarted')
    return value


def watch(api, registry, task_id, json_mode=False, interval=1):
    previous = None
    while True:
        status = task_status(api, task_id)
        snapshot = json.dumps(status, sort_keys=True)
        if snapshot != previous:
            if json_mode:
                emit(status, True)
            else:
                event = status.get('last_event') or {}
                percent = status.get('progress')
                suffix = f" {percent:.1f}%" if percent is not None else ''
                print(f"{task_id}: {status['status']}{suffix} {event.get('type', '')}", flush=True)
                if status['status'] in TERMINAL:
                    result = status.get('result') or {}
                    if result:
                        print(f"Version {result.get('version')}; files {result.get('checked_files')}; healthy {result.get('healthy')}")
                        issues = result.get('issues') or []
                        for issue in issues[:20]:
                            print(f"  {issue['filename']}: {issue['reason']}")
                        if len(issues) > 20:
                            print(f"  {len(issues) - 20} additional issues; use --json status for the full result")
                    if status.get('error'):
                        print(status['error'], file=sys.stderr)
            previous = snapshot
        if status['status'] in TERMINAL:
            with registry.edit() as data:
                if task_id in data['jobs']:
                    data['jobs'][task_id]['status'] = status['status']
                    data['jobs'][task_id]['result'] = status.get('result')
                    job = data['jobs'][task_id]
                    if status['status'] == 'completed' and job['operation'] in {'install','sync','update'}:
                        name = job['name']
                        if name in data['games'] and (status.get('result') or {}).get('version'):
                            data['games'][name]['version'] = status['result']['version']
                            data['games'][name]['categories'] = status['result'].get('categories', ['game'])
            if status['status'] == 'cancelled':
                return 130
            if status['status'] == 'failed':
                return 1
            result = status.get('result') or {}
            return 2 if result.get('healthy') is False else 0
        time.sleep(interval)


def validate_version(text):
    import re
    if not re.fullmatch(r'\d+\.\d+\.\d+', text):
        raise ClientError('Version must be major.minor.patch')
    return tuple(map(int, text.split('.')))


def nonnegative(text):
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError('must be nonnegative')
    return value


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--server', default=os.environ.get('SOPHON_SERVER_URL', 'http://127.0.0.1:8000'))
    p.add_argument('--registry', default=os.environ.get('SOPHON_REGISTRY', str(Path.home() / '.sophon' / 'registry.json')))
    p.add_argument('--json', action='store_true', help='Emit JSON/JSON-lines')
    commands = p.add_subparsers(dest='command', required=True)
    commands.add_parser('health')
    commands.add_parser('games', help='List supported games/regions')
    versions = commands.add_parser('versions', help='Query latest or exact historical versions; optionally probe a range')
    versions.add_argument('--game', choices=SUPPORTED)
    versions.add_argument('--region', choices=['os','cn','bb'], default='os')
    versions.add_argument('--version', action='append', help='Probe an exact historical tag; repeat to probe multiple versions')
    versions.add_argument('--scan', nargs=2, metavar=('START', 'END'), help='Probe major.minor.0 candidates in a bounded range')
    files = commands.add_parser('files', help='List/filter files in an exact historical version')
    files.add_argument('--version', required=True)
    files.add_argument('--region', choices=['os','cn','bb'], default='os')
    files.add_argument('--category', choices=['game','en-us','zh-cn','ja-jp','ko-kr'], default='game')
    files.add_argument('--pattern', default='*', help='Shell-style pattern; quote it to avoid shell expansion')
    files.add_argument('--offset', type=nonnegative, default=0)
    files.add_argument('--limit', type=int, default=100)
    register = commands.add_parser('register', help='Track a directory; does not download')
    register.add_argument('name')
    register.add_argument('directory')
    register.add_argument('--game', default='hk4e', choices=SUPPORTED)
    register.add_argument('--region', required=True, choices=['os','cn','bb'])
    register.add_argument('--version', help='Default historical version for this directory')
    commands.add_parser('list')
    forget = commands.add_parser('forget', help='Remove registration only; keep game files')
    forget.add_argument('name')
    for name in ('install', 'update', 'sync', 'download', 'predownload', 'check', 'repair'):
        op = commands.add_parser(name)
        op.add_argument('name', help='Registered game directory name')
        op.add_argument('--detach', action='store_true', help='Print task ID and return')
        op.add_argument('--tempdir', help='Dedicated download/cache directory')
        op.add_argument('--limit', type=nonnegative, default=0, help='Bytes per second; 0 unlimited, shared server limiter')
        if name != 'predownload':
            op.add_argument('--version', help='Exact version; check/repair default to installed version')
            op.add_argument('--category', action='append', choices=['game','en-us','zh-cn','ja-jp','ko-kr'])
        if name in ('download','check','repair'):
            op.add_argument('--file', action='append', help='Exact path from files output; repeat for several files')
        if name == 'update':
            op.add_argument('--incremental', action='store_true', help='Use legacy latest-version ldiff update; requires a supported source version and hpatchz')
        if name in ('sync','update'):
            op.add_argument('--allow-downgrade', action='store_true')
        if name in ('check','repair'):
            op.add_argument('--mode', choices=['quick','reliable'], default='reliable')
    commands.add_parser('jobs')
    for name in ('status','watch','pause','resume','cancel'):
        task = commands.add_parser(name)
        task.add_argument('task_id')
    limit = commands.add_parser('limit', help='Change the shared server download limit')
    limit.add_argument('bytes_per_second', type=nonnegative)
    serve = commands.add_parser('serve', help='Run sibling server in foreground using uv')
    serve.add_argument('--server-dir', default=str(Path(__file__).resolve().parents[3] / 'sophon-server'))
    return p


def execute(args):
    registry = Registry(args.registry)
    command = args.command
    if command == 'serve':
        root = Path(args.server_dir).expanduser().resolve()
        source = root / 'src' / 'server.py'
        if not source.is_file():
            source = root / 'server.py'
        if not source.is_file():
            raise ClientError(f'Server not found: {root}; pass --server-dir')
        return subprocess.call(['uv', 'run', '--locked', 'python', str(source)], cwd=root)
    if command == 'games':
        emit(SUPPORTED, args.json)
        return 0
    if command == 'register':
        if args.version:
            validate_version(args.version)
        if args.region not in SUPPORTED[args.game]:
            raise ClientError('Unsupported game/region combination')
        path = validate_directory(args.directory)
        with registry.edit() as data:
            if args.name in data['games']:
                raise ClientError('Name already registered; use forget before replacing it')
            for game in data['games'].values():
                other = Path(game['directory']).resolve()
                if path == other or path.is_relative_to(other) or other.is_relative_to(path):
                    raise ClientError('Registered game directories must not overlap')
            data['games'][args.name] = {'game': args.game, 'region': args.region, 'directory': str(path), 'version': args.version}
        emit({'registered': args.name, 'directory': str(path), 'version': args.version}, args.json)
        return 0
    if command == 'forget':
        with registry.edit() as data:
            if args.name not in data['games']:
                raise ClientError('Unknown registration')
            del data['games'][args.name]
        emit({'forgotten': args.name, 'files_deleted': False}, args.json)
        return 0
    if command == 'list':
        emit({name: {**game, 'installed_version': installed_version(game['directory'])}
              for name, game in registry.read()['games'].items()}, args.json)
        return 0
    if command == 'jobs':
        emit(registry.read()['jobs'], args.json)
        return 0
    api = API(args.server)
    if command == 'health':
        emit(api.call('GET','/health'), args.json)
        return 0
    if command == 'versions':
        if args.scan and args.version:
            raise ClientError('Use --scan or --version, not both')
        versions = args.version or [None]
        if args.scan:
            start, end = map(validate_version, args.scan)
            if start > end or start[2] or end[2]:
                raise ClientError('Scan requires an ascending range of major.minor.0 tags')
            if end[0] - start[0] > 9 or start[1] > 9 or end[1] > 9:
                raise ClientError('Scan is limited to 10 major versions and minor tags 0..9; use --version for other tags')
            versions = [f'{major}.{minor}.0' for major in range(start[0], end[0] + 1)
                        for minor in range(10) if start <= (major, minor, 0) <= end]
            if not versions or len(versions) > 100:
                raise ClientError('Scan supports at most 100 major.minor.0 candidates; use --version for exact patch tags')
        failed = False
        for version in versions:
            if version:
                validate_version(version)
            query = {'region': args.region}
            if version:
                query['version'] = version
            try:
                info = api.call('GET', '/api/history/build?' + parse.urlencode(query))
                emit({'available': True, **info}, args.json)
            except ClientError as exc:
                failed = True
                emit({'version':version, 'region':args.region, 'available':False, 'error':str(exc)}, args.json)
        return 1 if failed else 0
    if command == 'files':
        validate_version(args.version)
        if not 1 <= args.limit <= 1000:
            raise ClientError('--limit must be between 1 and 1000')
        query = {name:getattr(args,name) for name in ('version','region','category','pattern','offset','limit')}
        emit(api.call('GET', '/api/history/files?' + parse.urlencode(query)), args.json)
        return 0
    if command in ('status', 'watch', 'pause', 'resume', 'cancel'):
        task_id = args.task_id
        job = registry.read()['jobs'].get(task_id)
        if job and job['server'] != api.base:
            raise ClientError(f'Task belongs to {job["server"]}; select that server')
        if command == 'watch':
            return watch(api, registry, task_id, args.json)
        if command == 'status':
            emit(task_status(api, task_id), args.json)
        else:
            task_status(api, task_id)  # Server control endpoints silently accept unknown IDs.
            endpoint = '/api/tasks/' + parse.quote(task_id, safe='')
            emit(api.call('DELETE' if command == 'cancel' else 'POST', endpoint + ('' if command == 'cancel' else '/' + command)), args.json)
        return 0
    if command == 'limit':
        emit(api.call('POST','/api/limit', {'download_speed_limit':args.bytes_per_second}), args.json)
        return 0
    game = registry.game(args.name)
    directory = validate_directory(game['directory'])
    if command not in {'install','download'} and not directory.is_dir():
        raise ClientError('Existing installation directory required')
    body = {'gamedir': str(directory), 'game_type':'hk4e', 'download_speed_limit':args.limit}
    if args.tempdir:
        temp = validate_directory(args.tempdir)
        if temp == directory or directory.is_relative_to(temp):
            raise ClientError('Cache directory must not contain the game directory')
        body['tempdir'] = str(temp)
    if command == 'predownload':
        if game['region'] == 'bb':
            raise ClientError('Pre-download not supported for bb')
        if not (directory / 'config.ini').is_file():
            raise ClientError('Pre-download requires an existing full installation')
        body['predownload'] = True
        endpoint = '/api/update'
    elif command == 'update' and args.incremental:
        if args.version or args.category:
            raise ClientError('--incremental cannot select a historical version or categories')
        if game['region'] == 'bb':
            raise ClientError('Legacy incremental updates do not support bb')
        if not (directory / 'config.ini').is_file():
            raise ClientError('Update requires an existing full installation')
        body['predownload'] = False
        endpoint = '/api/update'
    else:
        version = args.version
        if command == 'update' and not version:
            version = api.call('GET', '/api/history/build?' + parse.urlencode({'region':game['region']}))['version']
        if command in {'check','repair'}:
            version = version or installed_version(directory) or game.get('version')
        else:
            version = version or game.get('version')
        if not version and command == 'install':
            version = api.call('GET', '/api/history/build?' + parse.urlencode({'region':game['region']}))['version']
        if not version:
            raise ClientError('Specify --version or register a default version')
        validate_version(version)
        body.update({'region':game['region'], 'version':version, 'categories':args.category or game.get('categories') or ['game']})
        if command in {'download','check','repair'}:
            body['files'] = args.file or []
        if command == 'download' and not body['files']:
            raise ClientError('download requires one or more --file exact paths')
        if command in {'check','repair'}:
            body['check_mode'] = args.mode
        if command in {'update','sync'}:
            body['allow_downgrade'] = args.allow_downgrade
        operation = 'sync' if command == 'update' else command
        endpoint = '/api/history/' + operation
    response = api.call('POST', endpoint, body)
    task_id = response['task_id']
    emit(response, args.json)
    with registry.edit() as data:
        data['jobs'][task_id] = {'name':args.name, 'operation':command, 'server':api.base, 'status':response['status'], 'version':body.get('version')}
    if args.detach:
        return 0
    try:
        return watch(api, registry, task_id, args.json)
    except KeyboardInterrupt:
        api.call('DELETE', '/api/tasks/' + parse.quote(task_id, safe=''))
        print(f'Cancellation requested: {task_id}', file=sys.stderr)
        return 130


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return execute(args)
    except KeyboardInterrupt:
        return 130
    except (ClientError, OSError, ValueError, KeyError) as exc:
        if args.json:
            print(json.dumps({'error':str(exc)}, ensure_ascii=False), file=sys.stderr)
        else:
            print(f'Error: {exc}', file=sys.stderr)
        return 1
