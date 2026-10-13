"""
tests/test_gui_helpers.py
-------------------------
common.gui_helpers(アップロードされたファイルの取り出し・ダウンロードのファイル名)の単体テスト。
ipywidgetsには依存しない(FileUploadの値は、同じ形の辞書・オブジェクトで代用している)。
"""

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import gui_helpers, io_reader  # noqa: E402


class TestExtractUploadedFile(unittest.TestCase):
    CONTENT = b"3\nwater\nO 0 0 0\nH 0 0 1\nH 0 1 0\n"

    def test_dropped_file_has_priority_over_the_upload_button(self):
        upload = SimpleNamespace(value=({"name": "button.xyz", "content": b"x"},))
        content, name = gui_helpers.extract_uploaded_file(
            upload, {"name": "dropped.xyz", "content": self.CONTENT})
        self.assertEqual((content, name), (self.CONTENT, "dropped.xyz"))

    def test_ipywidgets_8_value_is_a_tuple_of_dicts(self):
        upload = SimpleNamespace(value=({"name": "a.xyz", "content": memoryview(self.CONTENT)},))
        content, name = gui_helpers.extract_uploaded_file(upload)
        self.assertEqual((content, name), (self.CONTENT, "a.xyz"))

    def test_ipywidgets_8_value_can_be_objects_with_attributes(self):
        upload = SimpleNamespace(value=[SimpleNamespace(name="b.gjf", content=self.CONTENT)])
        content, name = gui_helpers.extract_uploaded_file(upload)
        self.assertEqual((content, name), (self.CONTENT, "b.gjf"))

    def test_ipywidgets_7_value_is_a_dict_keyed_by_file_name(self):
        upload = SimpleNamespace(value={"c.pdb": {"content": self.CONTENT, "metadata": {}}})
        content, name = gui_helpers.extract_uploaded_file(upload)
        self.assertEqual((content, name), (self.CONTENT, "c.pdb"))

    def test_nothing_selected_raises_a_helpful_error(self):
        for empty in ((), {}, None):
            with self.assertRaises(io_reader.StructureError) as ctx:
                gui_helpers.extract_uploaded_file(SimpleNamespace(value=empty))
            self.assertIn("ドラッグ", str(ctx.exception))

    def test_unexpected_value_type_is_reported(self):
        with self.assertRaises(RuntimeError):
            gui_helpers.extract_uploaded_file(SimpleNamespace(value="unexpected"))


class TestDefaultDownloadStem(unittest.TestCase):
    def test_input_file_name_gets_a_result_suffix(self):
        self.assertEqual(gui_helpers.default_download_stem("water.xyz"), "water_result")
        self.assertEqual(gui_helpers.default_download_stem("ethanol.gjf"), "ethanol_result")

    def test_only_the_last_extension_is_removed(self):
        self.assertEqual(gui_helpers.default_download_stem("mol.v2.xyz"), "mol.v2_result")

    def test_directory_part_is_removed(self):
        self.assertEqual(gui_helpers.default_download_stem("C:\\Users\\me\\water.xyz"), "water_result")
        self.assertEqual(gui_helpers.default_download_stem("../a/water.xyz"), "water_result")

    def test_characters_not_allowed_in_file_names_are_removed(self):
        self.assertEqual(gui_helpers.default_download_stem('a?b*c.xyz'), "abc_result")

    def test_japanese_names_are_kept(self):
        self.assertEqual(gui_helpers.default_download_stem("エタノール.xyz"), "エタノール_result")

    def test_unusable_names_fall_back_to_result(self):
        for bad in ("", None, ".xyz", "???.xyz"):
            self.assertEqual(gui_helpers.default_download_stem(bad), "result")


class TestSanitizeFilenameStem(unittest.TestCase):
    def test_empty_input_falls_back_to_result(self):
        self.assertEqual(gui_helpers.sanitize_filename_stem(""), "result")
        self.assertEqual(gui_helpers.sanitize_filename_stem("   "), "result")
        self.assertEqual(gui_helpers.sanitize_filename_stem(None), "result")

    def test_forbidden_characters_are_removed(self):
        self.assertEqual(gui_helpers.sanitize_filename_stem('my/file:name?'), "myfilename")

    def test_normal_names_are_unchanged(self):
        self.assertEqual(gui_helpers.sanitize_filename_stem("water_result"), "water_result")


if __name__ == "__main__":
    unittest.main()
