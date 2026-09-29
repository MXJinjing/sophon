"""Stateless HTTP transport, validation and task observation."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from urllib import request, parse, error

TERMINAL = {'completed', 'failed', 'cancelled'}

class ClientError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


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
            raise ClientError(f'HTTP {exc.code}: {detail}', status_code=exc.code) from exc
        except (error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise ClientError(f'Server request failed: {exc}') from exc


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


def watch(api, task_id, json_mode=False, interval=1, report_path=None):
    from .progress import TaskDisplay
    with TaskDisplay(json_mode) as display:
        return _watch(api, task_id, json_mode, interval, display, report_path)


def _watch(api, task_id, json_mode, interval, display, report_path=None):
    previous = None
    while True:
        status = task_status(api, task_id)
        display.update(status)
        if status['status'] in TERMINAL and report_path:
            display.stop()
            destination=Path(report_path).expanduser().resolve()
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(f'完整任务报告已保存：{destination}',file=sys.stderr if json_mode else sys.stdout)
        snapshot = json.dumps(status, sort_keys=True)
        if snapshot != previous:
            if json_mode:
                emit(status, True)
            elif not display.enabled or status['status'] in TERMINAL:
                if status['status'] in TERMINAL: display.stop()
                event = status.get('last_event') or {}
                percent = status.get('progress')
                suffix = f" {percent:.1f}%" if percent is not None else ''
                label = {'pending':'等待中', 'running':'处理中', 'paused':'已暂停', 'completed':'已完成', 'failed':'失败', 'cancelled':'已取消'}.get(status['status'], status['status'])
                print(f"{label}{suffix}", flush=True)
                if status['status'] in TERMINAL:
                    result = status.get('result') or {}
                    if result:
                        print(f"版本：{result.get('version')}；检查文件：{result.get('checked_files')}；完整性："+('通过' if result.get('healthy') is True else '发现异常' if result.get('healthy') is False else '未知'))
                        issues = result.get('issues') or []
                        for issue in issues[:20]:
                            print(f"  {issue['filename']}: "+{'missing':'文件缺失','size':'大小不符','md5':'MD5 不符'}.get(issue['reason'],issue['reason']))
                        if len(issues) > 20:
                            print(f"  还有 {len(issues) - 20} 项异常未在终端显示。")
                            print(f"完整结果：python run-client.py --json tasks status {task_id}")
                            if not report_path:print(f"保存报告：python run-client.py tasks watch {task_id} --output check-report.json")
                    if status.get('error'):
                        print(status['error'], file=sys.stderr)
            previous = snapshot
        if status['status'] in TERMINAL:
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


