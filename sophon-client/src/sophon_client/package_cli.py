"""Package-oriented stateless CLI; the server owns all operations and tasks."""
import argparse
from contextlib import contextmanager
import os
import sys
from urllib import parse
from . import cli as backend


def download_threads(text):
    value=int(text)
    if not 1 <= value <= 64:raise argparse.ArgumentTypeError('线程数量必须为 1..64')
    return value


def page_number(text):
    value=int(text)
    if value < 1:raise argparse.ArgumentTypeError('页码必须从 1 开始')
    return value


def parser():
    p = argparse.ArgumentParser(description='Sophon 无状态游戏资源客户端', formatter_class=argparse.RawTextHelpFormatter,
        epilog="""安装与维护（必须指定包和游戏目录）：
  python3 run-client.py install hk4e_cn@4.5.0 --dir ./games/cn
  python3 run-client.py check hk4e_cn@4.5.0 --dir ./games/cn
  python3 run-client.py update hk4e_cn --dir ./games/cn

任务管理（连接正在运行的服务端）：
  python3 run-client.py tasks status TASK_ID
  python3 run-client.py tasks pause TASK_ID
  python3 run-client.py tasks resume TASK_ID
  python3 run-client.py tasks cancel TASK_ID
  python3 run-client.py tasks watch TASK_ID

请先在另一个终端启动服务端：uv run --project sophon-server --locked python run-server.py
客户端只连接已有服务，从不启动或关闭服务端。
客户端不保存安装、任务或文件状态。check/repair 省略版本时从服务端目录状态读取当前版本。
  python3 run-client.py list hk4e_cn
  python3 run-client.py status --dir ./games/cn
服务端没有列出所有任务的接口；提交后请保留 task_id。
Windows 将 python3 换成 python；各命令支持 --help。""")
    p.add_argument('--server',default=os.environ.get('SOPHON_SERVER_URL','http://127.0.0.1:8000'),help='本机服务端地址')
    p.add_argument('--json',action='store_true',help='输出原始 JSON / JSON Lines')
    commands=p.add_subparsers(dest='command')
    def add(name,text):return commands.add_parser(name,help=text,description=text)
    def package(sub):sub.add_argument('package',help='hk4e_cn、hk4e_os、hk4e_bb，可带 @版本，例如 hk4e_cn@4.5.0')
    for name,text in [('install','安装精确版本或最新版'),('update','同步到指定版本或最新版'),('check','检查指定版本文件，不下载'),('repair','修复指定版本文件'),('download','下载指定版本的指定文件')]:
        sub=add(name,text);package(sub)
        if name=='download':
            sub.add_argument('--output',required=True,metavar='OUTPUT_DIR',help='服务端专用输出目录')
            sub.add_argument('files',nargs='+',help='相对游戏根目录的精确文件路径，可连续指定多个，不能传通配符')
            sub.add_argument('--category',choices=['game','en-us','zh-cn','ja-jp','ko-kr'],default='game')
        else:
            sub.add_argument('--dir',required=True,help='服务端游戏文件夹，必须显式指定')
            sub.add_argument('--voice',action='append',choices=['en-us','zh-cn','ja-jp','ko-kr'],help='额外语音分类，可重复')
        if name != 'check':sub.add_argument('--threads',type=download_threads,default=8,help='并行下载文件数，默认 8；范围 1..64，每个文件内 chunk 依次下载')
        sub.add_argument('--limit',type=backend.nonnegative,default=0,help='bytes/s；0 不限速')
        sub.add_argument('--tempdir',help='服务端专用下载缓存目录')
        sub.add_argument('--detach',action='store_true',help='提交后输出 task_id 即退出；必须使用已运行的服务端')
        if name=='update':sub.add_argument('--allow-downgrade',action='store_true',help='允许降级')
        if name in {'check','repair'}:
            sub.add_argument('--output',metavar='REPORT_FILE',help='完成后将完整任务结果保存为客户端本地 JSON 报告（覆盖同名文件）；--detach 时用 tasks watch 保存')
            sub.add_argument('--quick',action='store_true',help='只校验大小；默认大小和 MD5')
            sub.add_argument('--file',action='append',help='只处理指定相对路径，可重复')
    remote=add('list','列出服务端确认可用的全部已索引历史版本，不需指定范围')
    remote.add_argument('package',nargs='?',help='hk4e_cn / hk4e_os / hk4e_bb；省略查询全部地区，可带 @版本过滤')
    remote.add_argument('--refresh',action='store_true',help='忽略服务端十分钟内存缓存，重新确认可用版本')
    status=add('status','查询服务端指定游戏目录的安装版本状态，不校验文件完整性')
    status.add_argument('--dir',required=True,help='服务端游戏文件夹，必须显式指定')
    files=add('files','像 ls 一样浏览包内目录或查看文件');package(files)
    files.add_argument('path',nargs='?',default='.',help='清单相对目录或文件路径，默认根目录')
    files.add_argument('--recursive',action='store_true',help='递归列出路径下文件')
    files.add_argument('--refresh',action='store_true',help='重新下载并验证清单')
    files.add_argument('--match',help='递归搜索当前路径下匹配的文件，通配符需加引号')
    files.add_argument('--category',choices=['game','en-us','zh-cn','ja-jp','ko-kr'],default='game')
    files.add_argument('--page',type=page_number,default=1,help='页码，从 1 开始，默认第 1 页')
    files.add_argument('--count',type=int,default=100,help='每页条数，默认 100，范围 1..1000')
    tasks=add('tasks','直接查询和控制服务端任务，不读取本地记录')
    controls=tasks.add_subparsers(dest='action',required=True)
    for action,text in [('status','GET /api/tasks/{id}/status'),('pause','POST /api/tasks/{id}/pause'),('resume','POST /api/tasks/{id}/resume'),('cancel','DELETE /api/tasks/{id}'),('watch','轮询状态并显示进度，Ctrl+C 只退出观察')]:
        sub=controls.add_parser(action,help=text,description=text);sub.add_argument('task_id',help='服务端返回的 task_id')
        if action=='watch':sub.add_argument('--output',metavar='REPORT_FILE',help='任务结束后保存完整结果到客户端本地 JSON 文件（覆盖同名文件）')
    return p


def spec(text):
    name,sep,version=text.partition('@')
    if name not in {'hk4e_cn','hk4e_os','hk4e_bb'}:
        raise backend.ClientError('请使用 hk4e_cn、hk4e_os 或 hk4e_bb，例如 hk4e_cn@4.5.0')
    if sep:backend.validate_version(version)
    return name.removeprefix('hk4e_'), version if sep else None


@contextmanager
def service(args):
    # Connect only. The client never creates or terminates a server process.
    yield backend.API(args.server)


def run(args):
    if args.command=='status':
        with service(args) as api:
            result=api.call('GET','/api/history/status?'+parse.urlencode({'gamedir':args.dir}))
        if args.json:backend.emit(result,True)
        else:
            labels={'not_installed':'无完整安装版本','directory_missing':'目录不存在','installed':'已安装（完整性未检查）','install_pending':'安装未完成','update_pending':'更新未完成','version_mismatch':'版本记录不一致'}
            print('目录：'+result['directory'])
            print('状态：'+labels[result['status']])
            print('版本：'+(result['version'] or '未知'))
            print('地区：'+(result['region'] or '未知（缺少地区配置）'))
            if result['package']:print('包：'+result['package'])
            if result['pending_version']:print('待完成版本：'+result['pending_version'])
        return 0
    if args.command=='list':
        packages=[args.package] if args.package else ['hk4e_cn','hk4e_os','hk4e_bb']
        specs=[spec(package) for package in packages]
        with service(args) as api:
            failed=False
            # Discovery verifies many historical builds, so allow a longer request timeout.
            api.timeout=1800
            for region,version in specs:
                if not args.json:print(f'正在获取 hk4e_{region} 全部已索引可用版本…',file=sys.stderr)
                try:
                    result=api.call('GET','/api/history/versions?'+parse.urlencode({'region':region,'refresh':str(args.refresh).lower()}))
                except backend.ClientError as exc:
                    if exc.status_code in {404,405}:
                        raise backend.ClientError('当前服务端不支持版本列表接口，请在服务端终端按 Ctrl+C 停止旧进程，然后在 sophon 根目录重新运行：uv run --project sophon-server --locked python run-server.py') from exc
                    raise
                tags=sorted(set(result['versions']),key=backend.validate_version,reverse=True)
                if version:tags=[tag for tag in tags if tag==version]
                if args.json:backend.emit({**result,'versions':tags,'version_count':len(tags)},True)
                else:
                    from .progress import size
                    print(f"{'PACKAGE':24}  {'TOTAL (game)':>14}  {'DOWNLOAD (game)':>16}")
                    for tag in tags:
                        stats=result.get('version_sizes',{}).get(tag,{}).get('game',{})
                        total=size(stats['total_size']) if stats.get('total_size') is not None else '未知'
                        download=size(stats['download_size']) if stats.get('download_size') is not None else '未知'
                        print(f'{"hk4e_"+region+"@"+tag:24}  {total:>14}  {download:>16}')
                    print(f"共 {len(tags)} 个已列出的可用版本（不重复；官方清单确认；历史索引可能滞后）。",file=sys.stderr)
                if result.get('errors'):
                    failed=True
                    if not args.json:print(f"{len(result['errors'])} 个版本因查询错误未能确认，请 --refresh 重试。",file=sys.stderr)
                if version and not tags:failed=True
            return int(failed)
    if args.command=='tasks':
        # No health preflight, local lookup, or auto-start: forward the exact request.
        api=backend.API(args.server)
        endpoint='/api/tasks/'+parse.quote(args.task_id,safe='')
        if args.action=='watch':return backend.watch(api,args.task_id,args.json,report_path=args.output)
        method,path={'status':('GET',endpoint+'/status'),'pause':('POST',endpoint+'/pause'),
                     'resume':('POST',endpoint+'/resume'),'cancel':('DELETE',endpoint)}[args.action]
        backend.emit(api.call(method,path),args.json)
        return 0
    region,version=spec(args.package)
    command=args.command
    if command != 'files':
        directory=args.output if command=='download' else args.dir
    with service(args) as api:
        update_first=False
        if command in {'check','repair'} and not version:
            state=api.call('GET','/api/history/status?'+parse.urlencode({'gamedir':directory}))
            version=state.get('version')
            if not version:raise backend.ClientError('服务端目录没有可识别的安装版本，请显式指定 @版本')
            backend.validate_version(version)
            if state.get('region') and state['region']!=region:
                raise backend.ClientError('指定包地区与服务端安装目录不一致')
            latest=None
            try:
                latest=api.call('GET','/api/history/build?'+parse.urlencode({'region':region}))['version']
                newer=backend.validate_version(latest)>backend.validate_version(version)
                if args.json:
                    backend.emit({'event':'update_available','current_version':version,'latest_version':latest,'available':newer},True)
                else:
                    print(f'当前版本：hk4e_{region}@{version}')
                    print(f'发现新版本：{latest}' if newer else '当前没有更新的版本。')
                if newer and command=='repair':
                    if not args.json and sys.stdin.isatty():
                        try:answer=input(f'是否先更新到 {latest} 再修复？[y/N] ').strip().lower()
                        except EOFError:answer=''
                        update_first=answer in {'y','yes','是'}
                    else:
                        print('未交互确认更新，继续修复当前版本。',file=sys.stderr)
            except backend.ClientError as exc:
                print(f'暂时无法查询更新：{exc}；继续处理当前版本。',file=sys.stderr)
        if not version:version=api.call('GET','/api/history/build?'+parse.urlencode({'region':region}))['version']
        if command=='files':
            api.timeout=300  # First manifest fetch may require up to three network attempts.
            if not 1<=args.count<=1000:raise backend.ClientError('--count 范围 1..1000')
            result=api.call('GET','/api/history/files?'+parse.urlencode({'region':region,'version':version,'category':args.category,'pattern':args.match or '*','path':args.path,'recursive':str(args.recursive or args.match is not None).lower(),'refresh':str(args.refresh).lower(),'offset':(args.page-1)*args.count,'limit':args.count}))
            if args.json:backend.emit(result,True)
            else:
                current=result.get('path',args.path)
                display_path='/' if current in {'','.','/'} else '/'+current.strip('/')
                print(f'pwd: hk4e_{region}@{version} [{args.category}] {display_path}')
                from .file_listing import print_listing
                print_listing(result.get('files',[]),current_path=current)
                total=result.get('total',0)
                pages=max(1,(total+args.count-1)//args.count)
                if total == 0:
                    print('没有匹配的目录或文件。')
                elif args.page > pages:
                    print(f'第 {args.page} 页不存在，共 {pages} 页、{total} 项。')
                else:
                    print(f'共 {total} 项；第 {args.page}/{pages} 页。')
                    if args.page < pages:print(f'下一页：--page {args.page+1}')
            return 0
        body={'gamedir':str(directory),'game_type':'hk4e','region':region,'version':version,
              'download_speed_limit':args.limit,'categories':[args.category] if command=='download' else ['game',*(args.voice or [])]}
        if command != 'check':body['download_threads']=args.threads
        if args.tempdir:body['tempdir']=args.tempdir
        if command in {'download','check','repair'}:body['files']=args.files if command=='download' else (args.file or [])
        if command in {'check','repair'}:body['check_mode']='quick' if args.quick else 'reliable'
        if command=='update':body['allow_downgrade']=args.allow_downgrade
        if update_first:
            update_body={key:value for key,value in body.items() if key not in {'files','check_mode'}}
            update_body['version']=latest
            response=api.call('POST','/api/history/sync',update_body)
            if args.json:backend.emit(response,True)
            else:
                print(f"更新任务已提交：hk4e_{region}@{latest}")
                print('任务 ID：'+response['task_id'])
            # Repair must wait for the update even when the final repair is detached.
            try:code=backend.watch(api,response['task_id'],args.json)
            except KeyboardInterrupt:
                api.call('DELETE','/api/tasks/'+parse.quote(response['task_id'],safe=''))
                return 130
            if code:return code
            version=latest
            body['version']=version
        response=api.call('POST','/api/history/'+('sync' if command=='update' else command),body)
        # Preserve the ID even in human mode: tasks are entirely owned by the server.
        if args.json:
            backend.emit(response,True)
        else:
            labels={'install':'安装','update':'更新','download':'下载','check':'检查','repair':'修复'}
            states={'pending':'等待处理','running':'处理中','paused':'已暂停','completed':'已完成','failed':'失败','cancelled':'已取消'}
            print(f"{labels[command]}任务已提交：hk4e_{region}@{version}")
            print('任务 ID：'+response['task_id'])
            print('状态：'+states.get(response.get('status'),response.get('status') or '未知'))
            if args.detach:
                print('查看进度：python run-client.py tasks watch '+response['task_id'])
        if args.detach:return 0
        task_id=response['task_id']
        try:return backend.watch(api,task_id,args.json,report_path=args.output if command in {'check','repair'} else None)
        except KeyboardInterrupt:
            api.call('DELETE','/api/tasks/'+parse.quote(task_id,safe=''))
            print(f'已请求取消任务 {task_id}',file=sys.stderr)
            return 130


def main(argv=None):
    p=parser();args=p.parse_args(argv)
    if args.command is None:p.print_help();return 0
    try:return run(args)
    except KeyboardInterrupt:return 130
    except (backend.ClientError,OSError,ValueError,KeyError) as exc:
        if args.json:backend.emit({'error':str(exc)},True)
        else:print(f'错误：{exc}',file=sys.stderr)
        return 1
