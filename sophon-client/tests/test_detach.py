import contextlib
import io
import json
import os
import unittest
from unittest.mock import Mock, patch

from sophon_client import cli, package_cli


class DetachTests(unittest.TestCase):
    def test_watch_detaches_without_cancelling_or_writing_report(self):
        api = Mock()
        api.call.return_value = {'status': 'running'}
        with patch.object(cli, 'detach_input') as keyboard, patch.object(cli.Path, 'write_text') as write:
            keyboard.return_value.__enter__.return_value = Mock(return_value=True)
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(cli.TaskDetached) as detached:
                cli.watch(api, 'task-id', report_path='report.json')
        self.assertEqual(detached.exception.task_id, 'task-id')
        api.call.assert_called_once_with('GET', '/api/tasks/task-id/status')
        write.assert_not_called()

    def test_cli_detach_returns_success_and_task_id(self):
        for arguments in [
            ['tasks', 'watch', 'task-id'],
            ['--json', 'tasks', 'watch', 'task-id'],
            ['download', 'hk4e_cn@4.5.0', 'a.bin', '--output', '/server/files'],
        ]:
            with self.subTest(arguments=arguments):
                with patch.object(cli.API, 'call', return_value={'task_id': 'task-id', 'status': 'running'}) as call:
                    with patch.object(cli, 'watch', side_effect=cli.TaskDetached('task-id')):
                        with contextlib.redirect_stdout(io.StringIO()) as output:
                            self.assertEqual(package_cli.main(arguments), 0)
                self.assertTrue(all(item.args[0] != 'DELETE' for item in call.call_args_list))
                self.assertIn('task-id', output.getvalue())
                if '--json' in arguments:
                    self.assertEqual(json.loads(output.getvalue()), {'task_id': 'task-id', 'detached': True})

    def test_redirected_input_is_not_read(self):
        with patch.object(cli.sys, 'stdin', io.StringIO('\x04')), patch.object(cli.time, 'sleep') as sleep:
            with cli.detach_input() as wait:
                self.assertFalse(wait(0.1))
            sleep.assert_called_once_with(0.1)

    @unittest.skipIf(os.name == 'nt', 'POSIX terminal settings')
    def test_ctrl_d_and_terminal_restoration(self):
        import pty
        import termios
        master, slave = pty.openpty()
        try:
            original = termios.tcgetattr(slave)
            with os.fdopen(os.dup(slave), 'r') as terminal, patch.object(cli.sys, 'stdin', terminal):
                with self.assertRaises(cli.TaskDetached):
                    with cli.detach_input() as wait:
                        current = termios.tcgetattr(slave)
                        self.assertFalse(current[3] & termios.ICANON)
                        self.assertTrue(current[3] & termios.ISIG)
                        os.write(master, b'\x04')
                        self.assertTrue(wait(0.5))
                        raise cli.TaskDetached('task-id')
            restored = termios.tcgetattr(slave)
            # macOS may set PENDIN when queued input is reprocessed.
            restored[3] &= ~getattr(termios, 'PENDIN', 0)
            original[3] &= ~getattr(termios, 'PENDIN', 0)
            self.assertEqual(restored, original)
        finally:
            os.close(master)
            os.close(slave)


if __name__ == '__main__':
    unittest.main()
