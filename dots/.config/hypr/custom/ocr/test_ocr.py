"""Regression checks for geometric layout, clipboard preservation, cleanup and installer rollback."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import ocr
from layout import reconstruct
import customizations

def box(x,y,width=100,height=12):return [[x,y],[x+width,y],[x+width,y+height],[x,y+height]]

class LayoutTests(unittest.TestCase):
    def test_reading_order_indent_and_blank_lines(self):
        boxes=[box(40,20),box(0,0),box(80,40),box(0,80)]
        self.assertEqual(reconstruct(boxes,['indentedxx','toplinexxx','nestedxxxx','paragraphx']),'toplinexxx\n    indentedxx\n        nestedxxxx\n\nparagraphx\n')
    def test_same_line_fragments(self):
        self.assertEqual(reconstruct([box(0,0,50),box(80,1,50)],['hello','world']),'hello   world\n')
    def test_empty(self):self.assertEqual(reconstruct([],[]),'')
    def test_text_is_not_rewritten(self):
        self.assertEqual(reconstruct([box(0,0)],['a) :  x_y <>']),'a) :  x_y <>\n')

class WorkflowTests(unittest.TestCase):
    def run_main(self,path,result=None,error=None):
        args=['ocr.py','--image',str(path),'--delete-input']
        with patch.object(sys,'argv',args),patch.object(ocr,'extract',return_value=result,side_effect=error),patch.object(ocr,'notify') as notify,patch.object(ocr.subprocess,'run') as command:
            code=ocr.main();return code,command,notify
    def test_empty_preserves_clipboard_and_cleans(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"a 'capture.png";p.write_bytes(b'fixture')
            code,command,notify=self.run_main(p,{'text':'  \n'})
            self.assertEqual(code,1);command.assert_not_called();self.assertFalse(p.exists());notify.assert_called_once()
    def test_failure_preserves_clipboard_and_cleans(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'capture.png';p.write_bytes(b'fixture')
            code,command,_=self.run_main(p,error=RuntimeError('model missing'))
            self.assertEqual(code,1);command.assert_not_called();self.assertFalse(p.exists())
    def test_success_is_one_clipboard_write(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'capture.png';p.write_bytes(b'fixture')
            code,command,_=self.run_main(p,{'text':'    hello\n\nworld\n'})
            self.assertEqual(code,0);command.assert_called_once();self.assertEqual(command.call_args.kwargs['input'],b'    hello\n\nworld\n');self.assertFalse(p.exists())
    def test_cleanup_does_not_delete_newer_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'capture.png';p.write_bytes(b'old');before=ocr.identity(p);p.write_bytes(b'new capture')
            ocr.clean_input(p,before);self.assertTrue(p.exists())
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'real';p.write_bytes(b'original');link=Path(directory)/'link';link.symlink_to(p)
            with self.assertRaises(ValueError):ocr.identity(link)
            self.assertTrue(p.exists())

class InstallerTests(unittest.TestCase):
    def test_install_restore_and_unknown_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'config';backups=Path(directory)/'backups'
            for item in json.loads((HERE/'integration.json').read_text()):
                path=root/item['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_text(item['before'])
            saved=customizations.install(root,backups);self.assertEqual(customizations.plan(root),[])
            customizations.restore(root,saved)
            path=root/'quickshell/ii/modules/common/utils/ScreenshotAction.qml';path.write_text('unrecognized update')
            with self.assertRaises(RuntimeError):customizations.plan(root)
    def test_partial_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);a=root/'a';a.write_bytes(b'original');b=root/'b';original=customizations.write;count=0
            def injected(path,data,mode=0o644):
                nonlocal count
                count+=1
                if count==2:raise OSError('injected')
                original(path,data,mode)
            with patch.object(customizations,'write',injected):
                with self.assertRaises(OSError):customizations.transact([(a,b'original',b'changed'),(b,None,b'new')])
            self.assertEqual(a.read_bytes(),b'original');self.assertFalse(b.exists())

if __name__=='__main__':unittest.main()
