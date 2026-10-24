import subprocess
import unittest
from unittest.mock import MagicMock, patch

from byteadb.core import adb


class ListDevicesTests(unittest.TestCase):
    @patch('byteadb.core.adb._run')
    def test_parses_usb_and_wireless_devices(self, mock_run):
        mock_run.return_value = MagicMock(stdout=(
            b"List of devices attached\n"
            b"R58M12ABCDE\tdevice product:panther model:Pixel_7 device:panther transport_id:3\n"
            b"192.168.1.20:5555\tdevice product:redfin model:Pixel_5 device:redfin transport_id:5\n"
            b"HT8A1234\tunauthorized transport_id:1\n"
            b"\n"
        ))
        devices = adb.list_devices()
        self.assertEqual(len(devices), 3)
        self.assertEqual(devices[0].serial, 'R58M12ABCDE')
        self.assertEqual(devices[0].model, 'Pixel_7')
        self.assertEqual(devices[0].transport, 'usb')
        self.assertFalse(devices[0].is_wireless)

        self.assertEqual(devices[1].transport, 'tcp')
        self.assertTrue(devices[1].is_wireless)

        self.assertEqual(devices[2].state, 'unauthorized')
        self.assertIsNone(devices[2].model)

    @patch('byteadb.core.adb._run')
    def test_no_devices_returns_empty_list(self, mock_run):
        mock_run.return_value = MagicMock(stdout=b"List of devices attached\n\n")
        self.assertEqual(adb.list_devices(), [])


class AdbErrorTests(unittest.TestCase):
    def test_error_message_includes_command_and_stderr(self):
        err = adb.AdbError(['adb', 'shell', 'ls', '/root'], 1, 'Permission denied\n')
        self.assertIn('adb shell ls /root', str(err))
        self.assertIn('Permission denied', str(err))
        self.assertEqual(err.returncode, 1)

    @patch('byteadb.core.adb.adb_binary', return_value='/usr/bin/adb')
    @patch('subprocess.run')
    def test_run_raises_adberror_on_nonzero_exit(self, mock_subproc, mock_binary):
        mock_subproc.return_value = MagicMock(returncode=1, stdout=b'', stderr=b'device not found\n')
        with self.assertRaises(adb.AdbError) as ctx:
            adb._run(['devices'])
        self.assertEqual(ctx.exception.returncode, 1)
        self.assertIn('device not found', ctx.exception.stderr)

    @patch('byteadb.core.adb.adb_binary', return_value='/usr/bin/adb')
    @patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='adb', timeout=5))
    def test_run_raises_adberror_on_timeout(self, mock_subproc, mock_binary):
        with self.assertRaises(adb.AdbError):
            adb._run(['shell', 'sleep', '100'], timeout=5)


class AdbDeviceTests(unittest.TestCase):
    def test_shell_with_exit_code_parses_marker(self):
        device = adb.AdbDevice('serial123')
        device.shell = MagicMock(return_value='hello world\n__BYTEADB_EXIT:0\n')
        out, code = device.shell_with_exit_code('echo hello world')
        self.assertEqual(out, 'hello world')
        self.assertEqual(code, 0)

    def test_shell_with_exit_code_nonzero(self):
        device = adb.AdbDevice('serial123')
        device.shell = MagicMock(return_value='ls: nope: No such file or directory\n__BYTEADB_EXIT:1\n')
        out, code = device.shell_with_exit_code('ls nope')
        self.assertEqual(code, 1)
        self.assertIn('No such file', out)

    def test_args_pins_serial(self):
        device = adb.AdbDevice('ABC123')
        self.assertEqual(device._args('shell', 'ls'), ['-s', 'ABC123', 'shell', 'ls'])


if __name__ == '__main__':
    unittest.main()
