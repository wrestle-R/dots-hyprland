"""Exercise enrollment outcomes and device cleanup without changing any real scans."""
from unittest import TestCase, main
from unittest.mock import Mock
from fingerprint_settings import FINGERS, describe, enroll, remove


class Device:
    def __init__(self, result='enroll-completed', start_error=False):
        self.calls = []
        self.callback = None
        self.result = result
        self.start_error = start_error
        self.saved = ['right-index-finger']

    def connect_to_signal(self, name, callback):
        self.callback = callback
        return Mock()

    def Claim(self, user): self.calls.append(('claim', user))
    def Release(self): self.calls.append(('release',))
    def EnrollStart(self, finger):
        self.calls.append(('start', finger))
        if self.start_error: raise RuntimeError('reader rejected start')
    def EnrollStop(self): self.calls.append(('stop',))
    def ListEnrolledFingers(self, user): return self.saved
    def DeleteEnrolledFinger(self, finger):
        self.calls.append(('delete', finger))
        if finger in self.saved: self.saved.remove(finger)


class FingerprintSettingsTest(TestCase):
    def run_enrollment(self, device, cancel=False):
        events = []
        loop = Mock()
        def run():
            if cancel: return
            device.callback('enroll-stage-passed', False)
            device.callback(device.result, True)
        loop.run.side_effect = run
        glib = Mock(PRIORITY_DEFAULT=0)
        glib.MainContext.default.return_value.find_source_by_id.return_value = None
        result = enroll(device, 'tester', 'left-thumb', 13, loop, glib,
                        lambda **event: events.append(event))
        return result, events

    def test_success_updates_progress_and_releases_device(self):
        device = Device()
        result, events = self.run_enrollment(device)
        self.assertTrue(result)
        self.assertEqual(events[-1]['completed'], 13)
        self.assertEqual(device.calls, [('claim', 'tester'), ('start', 'left-thumb'), ('stop',), ('release',)])

    def test_failed_scan_is_not_reported_as_saved(self):
        device = Device('enroll-data-full')
        result, events = self.run_enrollment(device)
        self.assertFalse(result)
        self.assertFalse(events[-1]['ok'])
        self.assertIn('full', events[-1]['message'])
        self.assertEqual(device.calls[-2:], [('stop',), ('release',)])

    def test_cancel_keeps_existing_scan_and_releases_device(self):
        device = Device()
        result, events = self.run_enrollment(device, cancel=True)
        self.assertFalse(result)
        self.assertEqual(events[-1]['event'], 'cancelled')
        self.assertEqual(device.saved, ['right-index-finger'])
        self.assertEqual(device.calls[-2:], [('stop',), ('release',)])

    def test_failed_start_releases_claim(self):
        device = Device(start_error=True)
        with self.assertRaises(RuntimeError): self.run_enrollment(device)
        self.assertEqual(device.calls[-1], ('release',))
        self.assertNotIn(('stop',), device.calls)

    def test_remove_is_specific_and_repeatable(self):
        device = Device()
        device.saved.append('left-thumb')
        remove(device, 'tester', 'right-index-finger')
        remove(device, 'tester', 'right-index-finger')
        self.assertEqual(device.saved, ['left-thumb'])
        self.assertEqual(device.calls.count(('delete', 'right-index-finger')), 2)
        self.assertEqual(device.calls.count(('release',)), 2)

    def test_remove_failure_releases_reader_and_does_not_delete_other_fingers(self):
        device = Device()
        device.DeleteEnrolledFinger = Mock(side_effect=RuntimeError('busy'))
        with self.assertRaises(RuntimeError): remove(device, 'tester', 'right-index-finger')
        self.assertEqual(device.saved, ['right-index-finger'])
        self.assertEqual(device.calls[-1], ('release',))

    def test_status_reads_saved_fingers_and_hardware_stages(self):
        properties = Mock()
        properties.Get.side_effect = ['Goodix reader', 13]
        self.assertEqual(describe(Device(), properties, 'tester'), {
            'available': True, 'device': 'Goodix reader', 'stages': 13,
            'enrolled': ['right-index-finger']})
        self.assertEqual(len(set(FINGERS)), 10)


if __name__ == '__main__': main()
