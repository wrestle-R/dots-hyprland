import tempfile
from pathlib import Path
import unittest
from battery_status import snapshot

class BatteryStatusTests(unittest.TestCase):
    def test_above_cap_custom_is_paused_and_adaptive_is_not_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);battery=root/'BAT0';battery.mkdir();ac=root/'AC';ac.mkdir();(ac/'online').write_text('1')
            for name,value in {'charge_control_start_threshold':'90','charge_control_end_threshold':'95','capacity':'97','status':'Not charging','charge_types':'Trickle Standard Adaptive [Custom]'}.items():(battery/name).write_text(value)
            data=snapshot(root,root/'missing.json')['batteries'][0]
            self.assertTrue(data['enforced']);self.assertIn('charging paused',data['label']);self.assertIn('does not drain',data['explanation'])
            (battery/'charge_types').write_text('Trickle Standard [Adaptive] Custom')
            data=snapshot(root,root/'missing.json')['batteries'][0];self.assertFalse(data['enforced']);self.assertIn('Apply',data['label'])
            (ac/'online').write_text('0');(battery/'charge_types').write_text('Trickle Standard Adaptive [Custom]')
            self.assertIn('On battery',snapshot(root,root/'missing.json')['batteries'][0]['label'])

if __name__=='__main__':unittest.main()
