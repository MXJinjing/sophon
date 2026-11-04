import contextlib
import io
import json
import unittest
from unittest.mock import patch
from sophon_client import cli, package_cli


class TaskListTests(unittest.TestCase):
    def test_human_and_json_list(self):
        result = {'tasks': [{'task_name': 'check hk4e_cn@4.5.0', 'task_id': 'task-id', 'status': 'running', 'started_at': '2026-10-05T00:00:00+00:00'}]}
        for args in [['tasks', 'list'], ['--json', 'tasks', 'list']]:
            with patch.object(cli.API, 'call', return_value=result) as call, contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(package_cli.main(args), 0)
            call.assert_called_once_with('GET', '/api/tasks')
            if '--json' in args:
                self.assertEqual(json.loads(output.getvalue()), result)
            else:
                self.assertIn('task-id', output.getvalue())
                self.assertIn('处理中', output.getvalue())

    def test_empty_list(self):
        with patch.object(cli.API, 'call', return_value={'tasks': []}), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(package_cli.main(['tasks', 'list']), 0)
        self.assertIn('没有任务', output.getvalue())
