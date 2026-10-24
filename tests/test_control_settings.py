import unittest
from unittest.mock import MagicMock

from byteadb.core import control, settings


class ControlTests(unittest.TestCase):
    def test_unknown_keyevent_raises(self):
        device = MagicMock()
        with self.assertRaises(ValueError):
            control.keyevent(device, 'not_a_real_key')

    def test_known_keyevent_sends_correct_code(self):
        device = MagicMock()
        control.keyevent(device, 'home')
        device.shell.assert_called_once_with('input keyevent KEYCODE_HOME')

    def test_text_escapes_spaces_and_quotes(self):
        device = MagicMock()
        control.text(device, "hello 'world'")
        called_with = device.shell.call_args[0][0]
        self.assertEqual(called_with, "input text 'hello%s\\'world\\''")
        # the literal space was replaced with Android's %s escape, not left raw
        self.assertNotIn('hello world', called_with)

    def test_reboot_rejects_unknown_mode(self):
        device = MagicMock()
        with self.assertRaises(ValueError):
            control.reboot(device, 'not_a_mode')

    def test_reboot_accepts_known_modes(self):
        device = MagicMock()
        control.reboot(device, 'recovery')
        device.reboot.assert_called_once_with('recovery')


class SettingsTests(unittest.TestCase):
    def test_rejects_unknown_namespace(self):
        device = MagicMock()
        with self.assertRaises(ValueError):
            settings.get(device, 'bogus', 'some_key')

    def test_list_all_parses_key_value_pairs(self):
        device = MagicMock()
        device.shell.return_value = "airplane_mode_on=0\nbluetooth_name=Pixel\nmalformed_line\n"
        result = settings.list_all(device, 'global')
        self.assertEqual(result['airplane_mode_on'], '0')
        self.assertEqual(result['bluetooth_name'], 'Pixel')
        self.assertEqual(len(result), 2)  # malformed line (no '=') is skipped


if __name__ == '__main__':
    unittest.main()
