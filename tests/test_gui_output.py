"""
tests/test_gui_output.py
------------------------
common.gui_output(ダウンロードのファイル名・ダウンロード項目)の単体テスト。
ipywidgetsには依存しない。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import gui_output  # noqa: E402


class TestDefaultDownloadStem(unittest.TestCase):
    def test_input_file_name_gets_a_result_suffix(self):
        self.assertEqual(gui_output.default_download_stem("water.xyz"), "water_result")
        self.assertEqual(gui_output.default_download_stem("ethanol.gjf"), "ethanol_result")

    def test_only_the_last_extension_is_removed(self):
        self.assertEqual(gui_output.default_download_stem("mol.v2.xyz"), "mol.v2_result")

    def test_directory_part_is_removed(self):
        self.assertEqual(gui_output.default_download_stem("C:\\Users\\me\\water.xyz"), "water_result")
        self.assertEqual(gui_output.default_download_stem("../a/water.xyz"), "water_result")

    def test_characters_not_allowed_in_file_names_are_removed(self):
        self.assertEqual(gui_output.default_download_stem('a?b*c.xyz'), "abc_result")

    def test_japanese_names_are_kept(self):
        self.assertEqual(gui_output.default_download_stem("エタノール.xyz"), "エタノール_result")

    def test_unusable_names_fall_back_to_result(self):
        for bad in ("", None, ".xyz", "???.xyz"):
            self.assertEqual(gui_output.default_download_stem(bad), "result")


class TestXyzDownloadItems(unittest.TestCase):
    def test_two_items_in_the_form_expected_by_the_download_panel(self):
        items = gui_output.xyz_download_items("/tmp/a.xyz", "/tmp/t.xyz")
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertEqual(len(item), 4)
        self.assertEqual([i[1] for i in items], ["/tmp/a.xyz", "/tmp/t.xyz"])
        self.assertEqual([i[2] for i in items], [".xyz", "_traj.xyz"])
        self.assertEqual([i[3] for i in items], ["最終構造", "トラジェクトリ"])

    def test_the_final_structure_is_described_as_ready_for_colabreaction(self):
        self.assertIn("ColabReaction", gui_output.xyz_download_items("a", "b")[0][0])


class TestSanitizeFilenameStem(unittest.TestCase):
    def test_empty_input_falls_back_to_result(self):
        self.assertEqual(gui_output.sanitize_filename_stem(""), "result")
        self.assertEqual(gui_output.sanitize_filename_stem("   "), "result")
        self.assertEqual(gui_output.sanitize_filename_stem(None), "result")

    def test_forbidden_characters_are_removed(self):
        self.assertEqual(gui_output.sanitize_filename_stem('my/file:name?'), "myfilename")

    def test_normal_names_are_unchanged(self):
        self.assertEqual(gui_output.sanitize_filename_stem("water_result"), "water_result")


if __name__ == "__main__":
    unittest.main()
