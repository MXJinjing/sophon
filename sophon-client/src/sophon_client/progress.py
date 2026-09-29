"""Rich terminal progress; transport and JSON output remain independent."""
import sys


def size(value):
    value = max(0, value or 0)
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if value < 1024 or unit == 'TiB':
            return f'{value:.1f} {unit}'
        value /= 1024


def snapshot(event):
    overall = event.get('overall_progress') or {}
    if 'downloaded_size' in overall:
        done, total = overall['downloaded_size'], overall.get('total_size', 0)
        speed = max(0, overall.get('download_speed') or 0)
        eta = max(0, total - done) / speed if speed and total else None
        return {'phase':'下载', 'done':done, 'total':total or None,
                'amount':f'{size(done)} / {size(total)}' if total else size(done),
                'speed':size(speed)+'/s' if speed else '速度待测',
                'eta':f'{int(eta)//60:02d}:{int(eta)%60:02d}' if eta is not None else '--:--'}
    for key, phase in [('checked_files','检查'), ('deleted_files','清理')]:
        if key in overall:
            total = overall.get('total_files', 0)
            return {'phase':phase,'done':overall[key],'total':total or None,
                    'amount':f"{overall[key]} / {total} 文件",'speed':'','eta':''}
    if event.get('type') in {'download_summary','ldiff_download_summary'}:
        total = event.get('download_size',event.get('total_size',0))
        return {'phase':'下载','done':0,'total':total or None,'amount':f'0 B / {size(total)}','speed':'速度待测','eta':'--:--'}
    return None


class TaskDisplay:
    def __init__(self, json_mode=False, console=None):
        self.enabled = False
        self.progress = None
        self.files = {}
        self.phase = None
        if json_mode or (console is None and not sys.stderr.isatty()):
            return
        try:
            from rich.console import Console
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        except ImportError:
            print('提示：安装客户端依赖后可显示图形进度条：python -m pip install -e ./sophon-client',file=sys.stderr)
            return
        self.progress = Progress(SpinnerColumn(), TextColumn('{task.description}',markup=False),
            BarColumn(bar_width=None), TaskProgressColumn(),
            TextColumn('{task.fields[amount]}',markup=False),
            TextColumn('{task.fields[speed]}',markup=False),
            TextColumn('{task.fields[eta]}',markup=False),
            console=console or Console(stderr=True), refresh_per_second=5)
        self.task = self.progress.add_task('准备资源',total=None,amount='',speed='',eta='')
        self.enabled = True

    def __enter__(self):
        if self.enabled:self.progress.start()
        return self

    def stop(self):
        if self.enabled:
            self.progress.stop()
            self.enabled = False

    def __exit__(self, *args):
        self.stop()

    def update(self, status):
        if not self.enabled:return
        event = status.get('last_event') or {}
        state = status.get('status')
        data = snapshot(event)
        if data:
            if self.phase != data['phase']:
                for task in self.files.values(): self.progress.remove_task(task)
                self.files.clear()
                self.progress.reset(self.task,total=data['total'])
                self.phase = data['phase']
            self.progress.update(self.task,description=data['phase'],completed=data['done'],total=data['total'],
                amount=data['amount'],speed=data['speed'],eta=('剩余 '+data['eta']) if data['eta'] else '')
        if state in {'paused','completed','failed','cancelled'}:
            label={'paused':'已暂停','completed':'已完成','failed':'失败','cancelled':'已取消'}[state]
            self.progress.update(self.task,description=label,speed='',eta='')
        if 'active_files' in event:
            active=event['active_files'][:4]
            ids={item['filename'] for item in active}
            for filename in list(self.files):
                if filename not in ids:
                    self.progress.remove_task(self.files.pop(filename))
            for item in active:
                filename=item['filename'];total=item.get('total_size') or None
                if filename not in self.files:
                    self.files[filename]=self.progress.add_task(filename[-45:],total=total,amount='',speed='',eta='')
                self.progress.update(self.files[filename],completed=item.get('downloaded_size',0),total=total,
                    amount=size(item.get('downloaded_size',0)),speed=size(item.get('download_speed',0))+'/s',eta='')
        if state in {'completed','failed','cancelled'}:
            for task in self.files.values():self.progress.remove_task(task)
            self.files.clear()
