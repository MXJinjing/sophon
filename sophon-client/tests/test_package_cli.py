import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from sophon_client import package_cli as ui
from sophon_client import cli

class StatelessClientTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.calls=[]
    def call(self,method,path,body=None):
        self.calls.append((method,path,body))
        if path=='/health':return {'status':'ok'}
        if '/api/history/versions?' in path:return {'versions':['4.5.0'],'errors':[]}
        if '/api/history/build?' in path:return {'version':'4.5.0','region':'cn'}
        if '/api/history/files?' in path:return {'files':[{'filename':'a/b'}],'total':1}
        return {'task_id':'server-task','status':'pending','message':'raw-server-value'}
    def run_cli(self,*args):
        output=io.StringIO()
        with patch.object(cli.API,'call',side_effect=self.call),patch.object(cli,'watch',return_value=0),contextlib.redirect_stdout(output):
            code=ui.main(list(args))
        return code,output.getvalue()
    def test_install_direct_request_no_client_state(self):
        self.assertEqual(self.run_cli('install','hk4e_cn@4.5.0','--dir',str(self.root/'game'),'--voice','zh-cn')[0],0)
        body=self.calls[-1][2]
        self.assertEqual(body['region'],'cn');self.assertEqual(body['categories'],['game','zh-cn']);self.assertEqual(body['download_threads'],8)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_download_direct_request(self):
        self.assertEqual(self.run_cli('download','hk4e_os@4.5.0','a/b','--output',str(self.root/'picked'))[0],0)
        self.assertEqual(self.calls[-1][2]['files'],['a/b'])
        self.assertEqual(list(self.root.iterdir()),[])
    def test_missing_directory_rejected_before_service(self):
        for command in ('install','check','repair','update','status'):
            args=[command] if command=='status' else [command,'hk4e_os@4.5.0']
            with patch.object(ui,'service') as service,contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):ui.main(args)
                service.assert_not_called()
    def test_task_controls_forward_exactly(self):
        endpoints={'status':('GET','/api/tasks/id%2Fwith%20space/status'),
                   'pause':('POST','/api/tasks/id%2Fwith%20space/pause'),
                   'resume':('POST','/api/tasks/id%2Fwith%20space/resume'),
                   'cancel':('DELETE','/api/tasks/id%2Fwith%20space')}
        for action,expected in endpoints.items():
            self.calls.clear();code,output=self.run_cli('--json','tasks',action,'id/with space')
            self.assertEqual(code,0);self.assertEqual(self.calls,[(expected[0],expected[1],None)])
            self.assertEqual(json.loads(output)['message'],'raw-server-value')
    def test_removed_commands(self):
        for command in ('advanced','remove','info','import'):
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):ui.parser().parse_args([command])
        self.assertNotIn('--registry',ui.parser().format_help())
    def test_status_reads_only_server(self):
        remote={'directory':'/server/game','status':'installed','version':'4.5.0','region':'cn','package':'hk4e_cn','pending_version':None}
        with patch.object(cli.API,'call',return_value=remote) as call,patch.object(Path,'resolve',side_effect=AssertionError('local filesystem used')),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(ui.main(['--json','status','--dir','/server/game']),0)
        self.assertEqual(json.loads(output.getvalue()),remote)
        self.assertIn('gamedir=%2Fserver%2Fgame',call.call_args.args[1])

    def test_server_paths_preserved_on_submission(self):
        with patch.object(Path,'resolve',side_effect=AssertionError('local filesystem used')):
            self.assertEqual(self.run_cli('repair','hk4e_cn@4.5.0','--dir','/server/game','--tempdir','/server/cache')[0],0)
        self.assertEqual(self.calls[-1][2]['gamedir'],'/server/game')
        self.assertEqual(self.calls[-1][2]['tempdir'],'/server/cache')

    def test_remote_list_not_local(self):
        self.assertEqual(self.run_cli('list','hk4e_cn@4.5.0')[0],0)
        self.assertIn('/api/history/versions?',self.calls[-1][1]);self.assertIn('region=cn',self.calls[-1][1])
    def test_check_uses_server_version_without_updating(self):
        def call(method,path,body=None):
            self.calls.append((method,path,body))
            if '/status?' in path:return {'version':'4.5.0','region':'cn'}
            if '/build?' in path:return {'version':'5.0.0'}
            return {'task_id':'task','status':'pending'}
        with patch.object(cli.API,'call',side_effect=call),patch.object(cli,'watch',return_value=0),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(ui.main(['check','hk4e_cn','--dir','/server/game']),0)
        self.assertIn('发现新版本：5.0.0',output.getvalue())
        self.assertEqual(self.calls[-1][1],'/api/history/check')
        self.assertEqual(self.calls[-1][2]['version'],'4.5.0')

    def test_repair_update_choice_and_failed_update(self):
        for answer,update_code,expected in [('n',0,['repair']),('y',0,['sync','repair']),('y',1,['sync'])]:
            submitted=[]
            def call(method,path,body=None):
                if '/status?' in path:return {'version':'4.5.0','region':'cn'}
                if '/build?' in path:return {'version':'5.0.0'}
                submitted.append((path.rsplit('/',1)[-1],body['version']))
                return {'task_id':'task','status':'pending'}
            with patch.object(cli.API,'call',side_effect=call),patch.object(cli,'watch',return_value=update_code),patch.object(ui.sys.stdin,'isatty',return_value=True),patch('builtins.input',return_value=answer),contextlib.redirect_stdout(io.StringIO()):
                code=ui.main(['repair','hk4e_cn','--dir','/server/game'])
            self.assertEqual([item[0] for item in submitted],expected)
            self.assertEqual(submitted[-1][1],'4.5.0' if answer=='n' else '5.0.0')
            self.assertEqual(code,update_code)

    def test_old_server_reports_restart_instruction(self):
        @contextlib.contextmanager
        def existing(args):
            yield cli.API(args.server)
        with patch.object(ui,'service',existing),patch.object(cli.API,'call',side_effect=cli.ClientError('Method Not Allowed',status_code=405)),contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(ui.main(['list','hk4e_cn']),1)
            self.assertIn('Ctrl+C',output.getvalue())
            self.assertIn('run-server.py',output.getvalue())

    def test_thread_selection_and_removed_options(self):
        self.assertEqual(self.run_cli('download','hk4e_os@4.5.0','a/b','--output',str(self.root/'picked'),'--threads','3')[0],0)
        self.assertEqual(self.calls[-1][2]['download_threads'],3)
        for args in (['install','hk4e_cn','--dir','./game','--version','4.5.0'],
                     ['--no-start-server','list'],
                     ['install','hk4e_cn','--dir','./game','--threads','0'],
                     ['install','hk4e_cn','--dir','./game','--threads','65']):
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):ui.parser().parse_args(args)

    def test_file_pages_and_last_page_hint(self):
        for total, page, expected_next in ((6,1,False),(101,1,True),(101,2,False)):
            result={'files':[{'filename':'file.bin','size':12}],'total':total}
            output=io.StringIO()
            with patch.object(cli.API,'call',return_value=result) as call,contextlib.redirect_stdout(output):
                self.assertEqual(ui.main(['files','hk4e_os@4.5.0','--page',str(page)]),0)
            self.assertIn('offset='+str((page-1)*100),call.call_args.args[1])
            self.assertEqual('下一页' in output.getvalue(),expected_next)
        for args in (['files','hk4e_os@4.5.0','--page','0'],['files','hk4e_os@4.5.0','--offset','100']):
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):ui.parser().parse_args(args)

    def test_files_show_current_path_before_listing(self):
        for path,expected in (('.', '/'), ('data/sub','/data/sub')):
            output=io.StringIO()
            result={'path':path,'files':[],'total':0}
            with patch.object(cli.API,'call',return_value=result),contextlib.redirect_stdout(output):
                self.assertEqual(ui.main(['files','hk4e_os@4.5.0',path]),0)
            self.assertEqual(output.getvalue().splitlines()[0],f'pwd: hk4e_os@4.5.0 [game] {expected}')

    def test_versions_removed_and_positional_download(self):
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            ui.parser().parse_args(['versions','hk4e_cn'])
        self.assertEqual(self.run_cli('download','hk4e_cn@4.5.0','a/b','c/d','--output',str(self.root/'picked'))[0],0)
        self.assertEqual(self.calls[-1][2]['files'],['a/b','c/d'])
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            ui.parser().parse_args(['download','hk4e_cn@4.5.0','--file','a/b','--output','./picked'])

    def test_list_displays_sizes(self):
        result={'versions':['4.5.0'],'errors':[],'version_sizes':{'4.5.0':{'game':{'total_size':1024,'download_size':512}}}}
        with patch.object(cli.API,'call',return_value=result),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(ui.main(['list','hk4e_cn']),0)
        self.assertIn('1.0 KiB',output.getvalue())
        self.assertIn('512',output.getvalue())

    def test_list_newest_first(self):
        result={'versions':['4.9.0','4.10.0','5.0.0'],'errors':[]}
        with patch.object(cli.API,'call',return_value=result),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(ui.main(['list','hk4e_cn']),0)
        text=output.getvalue()
        self.assertLess(text.index('hk4e_cn@5.0.0'),text.index('hk4e_cn@4.10.0'))
        self.assertLess(text.index('hk4e_cn@4.10.0'),text.index('hk4e_cn@4.9.0'))

    def test_list_count_deduplicates_and_filters(self):
        result={'versions':['4.2.0','4.2.0','7.1.0'],'errors':[]}
        for package,count in [('hk4e_os',2),('hk4e_os@4.2.0',1)]:
            with patch.object(cli.API,'call',return_value=result),contextlib.redirect_stdout(io.StringIO()) as output,contextlib.redirect_stderr(io.StringIO()) as diagnostic:
                self.assertEqual(ui.main(['list',package]),0)
            lines=[line for line in output.getvalue().splitlines() if line.startswith('hk4e_os@')]
            self.assertEqual(len(lines),count)
            self.assertIn(f'共 {count} 个已列出的',diagnostic.getvalue())
            with patch.object(cli.API,'call',return_value=result),contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(ui.main(['--json','list',package]),0)
            value=json.loads(output.getvalue())
            self.assertEqual(value['version_count'],len(value['versions']))

    def test_submission_human_and_json(self):
        args=['download','hk4e_os@4.5.0','a/b','--output',str(self.root/'picked'),'--detach']
        code,text=self.run_cli(*args)
        self.assertEqual(code,0)
        self.assertIn('下载任务已提交：hk4e_os@4.5.0',text)
        self.assertIn('任务 ID：server-task',text)
        self.assertIn('状态：等待处理',text)
        self.assertNotIn('"task_id"',text)
        code,text=self.run_cli('--json',*args)
        self.assertEqual(json.loads(text)['task_id'],'server-task')
        self.assertEqual(json.loads(text)['message'],'raw-server-value')

    def test_region_spec(self):
        self.assertEqual(ui.spec('hk4e_os@4.5.0'),('os','4.5.0'))
        with self.assertRaises(cli.ClientError):ui.spec('hk4e@4.5.0')

if __name__=='__main__':unittest.main()
