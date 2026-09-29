import io
import unittest
from sophon_client.progress import TaskDisplay, snapshot
from rich.console import Console

class ProgressDisplayTests(unittest.TestCase):
    def test_download_snapshot(self):
        data=snapshot({'overall_progress':{'downloaded_size':1024,'total_size':2048,'download_speed':512}})
        self.assertEqual(data['eta'],'00:02');self.assertEqual(data['speed'],'512.0 B/s')
        self.assertEqual(snapshot({'overall_progress':{'downloaded_size':0,'total_size':0}})['total'],None)
    def test_render_stages_and_active_files(self):
        output=io.StringIO();console=Console(file=output,force_terminal=True,width=120)
        with TaskDisplay(console=console) as display:
            display.update({'status':'running','last_event':{'overall_progress':{'downloaded_size':1024,'total_size':2048,'download_speed':512},'active_files':[{'filename':'a[red].bin','total_size':2048,'downloaded_size':1024}]}})
            self.assertEqual(len(display.files),1)
            console.print(display.progress.get_renderable())
            display.update({'status':'running','last_event':{'overall_progress':{'checked_files':2,'total_files':3},'active_files':[]}})
            self.assertEqual(display.phase,'检查');self.assertFalse(display.files)
            display.update({'status':'failed','last_event':{}});display.progress.refresh()
        self.assertIn('下载',output.getvalue());self.assertIn('失败',output.getvalue())
        self.assertFalse(display.enabled)
    def test_json_does_not_render(self):
        with TaskDisplay(True) as display:
            self.assertFalse(display.enabled)
            display.update({'status':'running'})

if __name__=='__main__':unittest.main()
