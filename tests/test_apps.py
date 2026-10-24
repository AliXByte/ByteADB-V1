import unittest
from unittest.mock import MagicMock

from byteadb.core import apps

SAMPLE_DUMPSYS = """
Package [com.example.app] (abcdef):
  userId=10123
  pkg=Package{1234 com.example.app}
  versionName=2.3.1
  versionCode=2030100 minSdk=24 targetSdk=34
  requested permissions:
    android.permission.INTERNET: granted=true
    android.permission.CAMERA: granted=false
    android.permission.CAMERA: granted=false
"""


class AppInfoParsingTests(unittest.TestCase):
    def test_extracts_version_name_and_code(self):
        device = MagicMock()
        device.shell.return_value = SAMPLE_DUMPSYS
        import byteadb.core.apps as apps_mod
        apps_mod.package_path = lambda d, p: '/data/app/com.example.app/base.apk'
        info = apps.app_info(device, 'com.example.app')
        self.assertEqual(info.version_name, '2.3.1')
        self.assertEqual(info.version_code, '2030100')
        self.assertIn('android.permission.INTERNET', info.permissions)
        self.assertIn('android.permission.CAMERA', info.permissions)
        # dedup: CAMERA appeared twice in the dump
        self.assertEqual(info.permissions.count('android.permission.CAMERA'), 1)


class ListPackagesTests(unittest.TestCase):
    def test_parses_and_sorts_package_lines(self):
        device = MagicMock()
        device.shell.return_value = "package:com.zeta.app\npackage:com.alpha.app\n\n"
        pkgs = apps.list_packages(device)
        self.assertEqual(pkgs, ['com.alpha.app', 'com.zeta.app'])

    def test_user_only_flag_passed_to_shell(self):
        device = MagicMock()
        device.shell.return_value = ""
        apps.list_packages(device, user_only=True)
        device.shell.assert_called_once_with('pm list packages -3')


class InstallUninstallTests(unittest.TestCase):
    def test_install_raises_on_failure_output(self):
        device = MagicMock()
        device.run.return_value = 'Failure [INSTALL_FAILED_INVALID_APK]'
        with self.assertRaises(RuntimeError):
            apps.install_apk(device, 'bad.apk')

    def test_install_success(self):
        device = MagicMock()
        device.run.return_value = 'Success'
        result = apps.install_apk(device, 'good.apk')
        self.assertEqual(result, 'Success')

    def test_uninstall_raises_on_failure(self):
        device = MagicMock()
        device.run.return_value = 'Failure'
        with self.assertRaises(RuntimeError):
            apps.uninstall_package(device, 'com.example.app')


if __name__ == '__main__':
    unittest.main()
