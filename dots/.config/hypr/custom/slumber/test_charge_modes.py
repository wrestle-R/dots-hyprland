"""Exercise Dell's charge-mode requirement with a temporary sysfs emulator."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('charge_limit',Path(__file__).with_name('charge_limit.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class DellChargeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.battery=self.root/'sys/BAT0';self.battery.mkdir(parents=True)
        self.sys=patch.object(c,'SYSFS',self.root/'sys');self.sys.start();self.state=patch.object(c,'STATE',self.root/'state/settings.json');self.state.start()
        (self.battery/'charge_control_start_threshold').write_text('50');(self.battery/'charge_control_end_threshold').write_text('90')
        (self.battery/'charge_types').write_text('Trickle Fast Standard [Adaptive] Custom')
        original=Path.write_text
        def write(path,text,*args,**kwargs):
            if path.name=='charge_types':
                mode=text.strip()
                text=' '.join('['+m+']' if m==mode else m for m in ['Trickle','Fast','Standard','Adaptive','Custom'])
            return original(path,text,*args,**kwargs)
        self.writer=patch.object(Path,'write_text',write);self.writer.start()
    def tearDown(self):self.writer.stop();self.state.stop();self.sys.stop();self.temp.cleanup()
    def test_enable_enters_custom_and_off_enters_standard(self):
        c.apply(95);self.assertEqual(c.mode_info(self.battery)[1],'Custom');self.assertEqual((self.battery/'charge_control_end_threshold').read_text(),'95')
        self.assertEqual(json.loads(c.STATE.read_text())['original_modes'],{'BAT0':'Adaptive'})
        c.apply(95,False);self.assertEqual(c.mode_info(self.battery)[1],'Standard')
    def test_save_failure_restores_mode_and_thresholds(self):
        with patch.object(c,'atomic',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):c.apply(95)
        self.assertEqual(c.mode_info(self.battery)[1],'Adaptive');self.assertEqual((self.battery/'charge_control_end_threshold').read_text(),'90');self.assertFalse(c.STATE.exists())
    def test_legacy_saved_cap_is_migrated_and_enforced(self):
        c.STATE.parent.mkdir();c.STATE.write_text(json.dumps({'enabled':True,'limit':95,'original':{'BAT0':[50,90]}}))
        c.apply(95);saved=json.loads(c.STATE.read_text());self.assertEqual(saved['original'],{'BAT0':[50,90]});self.assertEqual(c.mode_info(self.battery)[1],'Custom')

if __name__=='__main__':unittest.main()
