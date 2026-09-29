import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from sophon_client.cli import watch

class TaskReportTests(unittest.TestCase):
    def test_report_preserves_all_issues_and_json_mode(self):
        status={'task_id':'actual-id','status':'completed','result':{'version':'7.0.0','checked_files':30,'healthy':False,'issues':[{'filename':f'data/{i}.blk','reason':'missing'} for i in range(30)]}}
        api=Mock();api.call.return_value=status
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'report.json'
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(watch(api,'actual-id',interval=0,report_path=str(target)),2)
            self.assertEqual(json.loads(target.read_text()),status)
            self.assertIn('还有 10 项异常',output.getvalue())
            self.assertIn('--json tasks status actual-id',output.getvalue())
            self.assertIn('文件缺失',output.getvalue())
            with contextlib.redirect_stdout(io.StringIO()) as output,contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(watch(api,'actual-id',True,interval=0,report_path=str(target)),2)
            self.assertEqual(json.loads(output.getvalue()),status)
    def test_failed_task_is_saved(self):
        api=Mock();api.call.return_value={'task_id':'id','status':'failed','error':'network error'}
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            target=Path(directory)/'report.json'
            self.assertEqual(watch(api,'id',report_path=str(target)),1)
            self.assertEqual(json.loads(target.read_text())['error'],'network error')

if __name__=='__main__':unittest.main()
