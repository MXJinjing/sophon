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
import history
from test_history import HistoricalFileTests
HistoricalFileTests.setUpClass()
def fixture(region, version=None):
    version = version or '5.0.0'
    if version not in HistoricalFileTests.builds:
        raise ValueError('Unavailable fixture version')
    return copy.deepcopy(HistoricalFileTests.builds[version])
history.query_build = fixture
import server, uvicorn
import time
from sophon_api import wait_if_paused
from task_errors import TaskCancelledError
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
        cls.env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT/'sophon-server'/'src'),str(ROOT/'sophon-server'/'tests'),str(ROOT/'sophon-client'/'src')]), PYTHONDONTWRITEBYTECODE='1')
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
        self.registry = self.root/'registry.json'

    def tearDown(self):
        self.work.cleanup()

    def cli(self,*args,code=0):
        result = subprocess.run([sys.executable,'-m','sophon_client','--server',self.url,'--registry',str(self.registry),'--json',*args],env=self.env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,code,result.stdout+'\n'+result.stderr)
        return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]

    def test_selected_file_download_check_repair_and_tracking(self):
        path=self.root/'selected'
        self.cli('register','selected',str(path),'--region','os','--version','4.5.0')
        files=self.cli('files','--version','4.5.0','--pattern','*/selected.*')[0]
        self.assertEqual(files['total'],1)
        self.cli('download','selected','--file','data/selected.bin')
        self.assertEqual((path/'data/selected.bin').read_bytes(),b'old-data')
        self.assertFalse((path/'data/removed.bin').exists())
        (path/'data/selected.bin').write_bytes(b'BAD-DATA')
        checked=self.cli('check','selected','--file','data/selected.bin',code=2)
        self.assertFalse(checked[-1]['result']['healthy'])
        self.assertEqual((path/'data/selected.bin').read_bytes(),b'BAD-DATA')
        self.cli('repair','selected','--file','data/selected.bin')
        self.assertEqual((path/'data/selected.bin').read_bytes(),b'old-data')
        jobs=self.cli('jobs')[0]
        task_id=next(iter(jobs))
        self.cli('status',task_id)
        self.cli('forget','selected')
        self.assertTrue((path/'data/selected.bin').exists())

    def test_whole_install_sync_and_explicit_downgrade(self):
        path=self.root/'full'
        self.cli('register','full',str(path),'--region','os','--version','4.5.0')
        self.cli('install','full')
        self.assertIn('game_version=4.5.0',(path/'config.ini').read_text())
        self.cli('update','full','--version','5.0.0')
        self.assertIn('game_version=5.0.0',(path/'config.ini').read_text())
        self.assertFalse((path/'data/removed.bin').exists())
        self.cli('sync','full','--version','4.5.0',code=1)
        self.cli('sync','full','--version','4.5.0','--allow-downgrade')
        self.assertIn('game_version=4.5.0',(path/'config.ini').read_text())

    def test_errors_are_not_silent_fallbacks(self):
        version=self.cli('versions','--version','99.99.99',code=1)[0]
        self.assertFalse(version['available'])
        self.cli('status','unknown-task',code=1)
        self.cli('register','test',str(self.root/'files'),'--region','os')
        self.cli('download','test','--version','4.5.0',code=1)
        self.cli('download','test','--version','4.5.0','--file','missing',code=1)
        self.assertFalse((self.root/'files/data').exists())

    def test_detached_pause_resume_cancel_and_busy_guard(self):
        self.cli('register','control',str(self.root/'control'),'--region','os','--version','4.5.0')
        task = self.cli('download','control','--file','control-fixture','--detach')[0]['task_id']
        try:
            self.cli('status',task)
            self.cli('pause',task)
            self.cli('resume',task)
            self.cli('download','control','--file','control-fixture','--detach',code=1)
            self.cli('cancel',task)
            self.cli('watch',task,code=130)
        finally:
            self.cli('cancel',task)

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
