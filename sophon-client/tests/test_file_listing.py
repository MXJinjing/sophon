import io
import unittest
from rich.console import Console
from sophon_client.file_listing import print_listing

class FileListingTests(unittest.TestCase):
    entries=[{'filename':'data','type':'directory','size':None},{'filename':'data/[red].bin','type':'file','size':2048}]
    def test_types_sizes_and_literal_names(self):
        output=io.StringIO()
        print_listing(self.entries,Console(file=output,width=100,force_terminal=False,color_system=None))
        value=output.getvalue()
        for expected in ('TYPE','directory','file','2.0 KiB','data','data/[red].bin'):self.assertIn(expected,value)
        self.assertNotIn('\x1b',value)
        self.assertEqual(next(line for line in value.splitlines() if 'directory' in line).split()[-1],'data')
    def test_names_relative_to_current_directory(self):
        from sophon_client.file_listing import rows
        values=list(rows([{'filename':'data/sub/file.bin','type':'file','size':12},{'filename':'database/file.bin','type':'file','size':12}], 'data'))
        self.assertEqual(values[0][2],'sub/file.bin')
        self.assertEqual(values[1][2],'database/file.bin')
        self.assertEqual(list(rows([{'filename':'data/sub/file.bin','type':'file','size':12}], 'data/sub/file.bin'))[0][2],'file.bin')

    def test_terminal_colors(self):
        output=io.StringIO()
        print_listing(self.entries,Console(file=output,width=100,force_terminal=True,color_system='standard',no_color=False))
        self.assertIn('\x1b[',output.getvalue())
    def test_empty_listing(self):
        output=io.StringIO()
        print_listing([],Console(file=output))
        self.assertEqual(output.getvalue(),'')

if __name__=='__main__':unittest.main()
