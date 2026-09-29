"""Offline real-HTTP integration using tiny synthetic Sophon manifests/chunks."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ClientHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sophon-cli-test-')
        cls.base = Path(cls.temp.name)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{port}'
        runner = cls.base / 'runner.py'
        runner.write_text('''import copy
from services import history, manifest_browser
from test_history import HistoricalFileTests
HistoricalFileTests.setUpClass()
def fixture(region, version=None):
    version = version or '5.0.0'
    if version not in HistoricalFileTests.builds:
        raise ValueError('Unavailable fixture version')
    return copy.deepcopy(HistoricalFileTests.builds[version])
history.query_build = fixture
manifest_browser.query_build = fixture
from api import server
import uvicorn
import time
from engine.control import wait_if_paused
from infrastructure.errors import TaskCancelledError
original = server.run_history
def controlled(manager, tasks, task_id, operation, payload, cancel, pause):
    if payload.files != ['control-fixture']:
        return original(manager,tasks,task_id,operation,payload,cancel,pause)
    while True:
        wait_if_paused(pause,cancel)
        time.sleep(.05)
server.run_history = controlled
uvicorn.run(server.app, host='127.0.0.1', port=PORT, log_level='warning')
'''.replace('PORT', str(port)))
        cls.env = dict(os.environ, SOPHON_MANIFEST_CACHE=str(cls.base/'manifest-cache'), PYTHONPATH=os.pathsep.join([str(ROOT/'sophon-server'/'src'),str(ROOT/'sophon-server'/'tests'),str(ROOT/'sophon-client'/'src')]), PYTHONDONTWRITEBYTECODE='1')
        cls.log = (cls.base/'server.log').open('w')
        cls.proc = subprocess.Popen([sys.executable,str(runner)], cwd=ROOT/'sophon-server',env=cls.env,stdout=cls.log,stderr=cls.log)
        from urllib.request import urlopen
        for _ in range(100):
            try:
                with urlopen(cls.url+'/health', timeout=.5):
                    break
            except OSError:
                if cls.proc.poll() is not None:
                    raise RuntimeError((cls.base/'server.log').read_text())
                time.sleep(.05)
        else:
            raise RuntimeError('Server failed to start')

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill(); cls.proc.wait()
        cls.log.close()
        cls.temp.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=self.base)
        self.root = Path(self.work.name)

    def tearDown(self):
        self.work.cleanup()

    def cli(self,*args,code=0):
        result = subprocess.run([sys.executable,'-m','sophon_client','--server',self.url,'--json',*args],env=self.env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,code,result.stdout+'\n'+result.stderr)
        return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]

    def test_selected_file_download_check_repair(self):
        path=self.root/'selected'
        files=self.cli('files','hk4e_os@4.5.0','--match','*/selected.*')[0]
        self.assertEqual(files['total'],1)
        response=self.cli('download','hk4e_os@4.5.0','--output',str(path),'data/selected.bin')
        self.assertEqual((path/'data/selected.bin').read_bytes(),b'old-data')
        self.assertFalse((path/'data/removed.bin').exists())
        (path/'data/selected.bin').write_bytes(b'BAD-DATA')
        self.cli('check','hk4e_os@4.5.0','--dir',str(path),'--file','data/selected.bin',code=2)
        self.assertEqual((path/'data/selected.bin').read_bytes(),b'BAD-DATA')
        self.cli('repair','hk4e_os@4.5.0','--dir',str(path),'--file','data/selected.bin')
        self.assertEqual((path/'data/selected.bin').read_bytes(),b'old-data')
        self.cli('tasks','status',response[0]['task_id'])

    def test_whole_install_sync_and_explicit_downgrade(self):
        path=self.root/'full'
        self.cli('install','hk4e_os@4.5.0','--dir',str(path))
        self.assertIn('game_version=4.5.0',(path/'config.ini').read_text())
        self.cli('update','hk4e_os@5.0.0','--dir',str(path))
        self.assertIn('game_version=5.0.0',(path/'config.ini').read_text())
        self.assertFalse((path/'data/removed.bin').exists())
        self.cli('update','hk4e_os@4.5.0','--dir',str(path),code=1)
        self.cli('update','hk4e_os@4.5.0','--dir',str(path),'--allow-downgrade')
        self.assertIn('game_version=4.5.0',(path/'config.ini').read_text())
        status=self.cli('status','--dir',str(path))[0]
        self.assertEqual(status['version'],'4.5.0')
        self.assertEqual(status['integrity'],'not_checked')

    def test_errors_are_not_silent_fallbacks(self):
        self.cli('files','hk4e_os@99.99.99',code=1)
        self.cli('tasks','status','unknown-task',code=1)
        self.cli('download','hk4e_os@4.5.0','--output',str(self.root/'files'),'missing',code=1)
        self.assertFalse((self.root/'files/data').exists())

    def test_detached_pause_resume_cancel_and_busy_guard(self):
        args=['download','hk4e_os@4.5.0','--output',str(self.root/'control'),'control-fixture','--detach']
        task=self.cli(*args)[0]['task_id']
        try:
            self.cli('tasks','status',task)
            self.cli('tasks','pause',task)
            self.cli('tasks','resume',task)
            self.cli(*args,code=1)
            self.cli('tasks','cancel',task)
            self.cli('tasks','watch',task,code=130)
        finally:self.cli('tasks','cancel',task)

    def test_legacy_request_mismatch_and_new_validation(self):
        from urllib.error import HTTPError
        from urllib.request import Request,urlopen
        for endpoint,payload in [('/api/install',{'gamedir':'unused','game_type':'hk4e'}),
                                 ('/api/history/download',{'gamedir':'unused','version':'4.5.0'}),
                                 ('/api/history/install',{'gamedir':'unused','version':'not-a-version'})]:
            with self.assertRaises(HTTPError) as raised:
                urlopen(Request(self.url+endpoint,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}),timeout=5)
            self.assertEqual(raised.exception.code,422)


if __name__=='__main__':
    unittest.main()
