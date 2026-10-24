import unittest
from unittest.mock import MagicMock

from byteadb.core import files


class ParseLsLineTests(unittest.TestCase):
    def test_directory_line(self):
        line = "drwxrwx--x 2 u0_a123 sdcard_rw 4096 2026-01-01 12:00 Download"
        entry = files._parse_ls_line(line, '/sdcard')
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, 'Download')
        self.assertTrue(entry.is_dir)
        self.assertFalse(entry.is_link)
        self.assertEqual(entry.path, '/sdcard/Download')

    def test_file_line_with_size(self):
        line = "-rw-rw---- 1 u0_a123 sdcard_rw 123456 2026-01-01 12:00 photo.jpg"
        entry = files._parse_ls_line(line, '/sdcard/DCIM')
        self.assertFalse(entry.is_dir)
        self.assertEqual(entry.size, 123456)
        self.assertEqual(entry.path, '/sdcard/DCIM/photo.jpg')

    def test_symlink_line_strips_target(self):
        line = "lrwxrwxrwx 1 root root 11 2026-01-01 12:00 sdcard -> /storage/self"
        entry = files._parse_ls_line(line, '/')
        self.assertTrue(entry.is_link)
        self.assertEqual(entry.name, 'sdcard')

    def test_dot_entries_skipped(self):
        self.assertIsNone(files._parse_ls_line("drwxr-xr-x 2 root root 4096 2026-01-01 12:00 .", '/sdcard'))
        self.assertIsNone(files._parse_ls_line("drwxr-xr-x 2 root root 4096 2026-01-01 12:00 ..", '/sdcard'))

    def test_malformed_line_returns_none(self):
        self.assertIsNone(files._parse_ls_line("not a valid ls line", '/sdcard'))


class ListDirTests(unittest.TestCase):
    def test_permission_denied_raises(self):
        device = MagicMock()
        device.shell.return_value = "ls: /data: Permission denied\n"
        with self.assertRaises(PermissionError):
            files.list_dir(device, '/data')

    def test_missing_path_raises(self):
        device = MagicMock()
        device.shell.return_value = "ls: /nope: No such file or directory\n"
        with self.assertRaises(FileNotFoundError):
            files.list_dir(device, '/nope')

    def test_successful_listing_sorted_dirs_first(self):
        device = MagicMock()
        device.shell.return_value = (
            "total 16\n"
            "-rw-rw---- 1 u0_a1 sdcard_rw 10 2026-01-01 12:00 b.txt\n"
            "drwxrwx--x 2 u0_a1 sdcard_rw 4096 2026-01-01 12:00 Zeta\n"
            "-rw-rw---- 1 u0_a1 sdcard_rw 20 2026-01-01 12:00 a.txt\n"
        )
        entries = files.list_dir(device, '/sdcard')
        names = [e.name for e in entries]
        self.assertEqual(names, ['Zeta', 'a.txt', 'b.txt'])  # dirs first, then alpha


class HumanSizeTests(unittest.TestCase):
    def test_none(self):
        self.assertEqual(files.human_size(None), '—')

    def test_bytes(self):
        self.assertEqual(files.human_size(512), '512B')

    def test_kilobytes(self):
        self.assertEqual(files.human_size(2048), '2.0KB')

    def test_megabytes(self):
        self.assertEqual(files.human_size(5 * 1024 * 1024), '5.0MB')


if __name__ == '__main__':
    unittest.main()
