"""
tests/test_gui_helpers.py
-------------------------
common.gui_helpers(アップロードされたファイルの取り出し・ダウンロードのファイル名・電荷の表示と読み取り)の単体テスト。
ipywidgetsには依存しない(FileUploadの値は、同じ形の辞書・オブジェクトで代用している)。
"""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

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


class TestLoadUploadedStructure(unittest.TestCase):
    """io_reader の読み込み・検証関数は差し替えて、受け渡しの順序と後始末だけを確認する。"""

    def setUp(self):
        self.calls = []
        self.seen = {}
        self.structure = SimpleNamespace(symbols=["O", "H", "H"])

        def read_structure(path):
            self.seen["path"] = path
            with open(path, "rb") as f:
                self.seen["content"] = f.read()
            self.calls.append("read")
            return self.structure

        patches = [
            mock.patch.object(io_reader, "read_structure", read_structure, create=True),
            mock.patch.object(io_reader, "validate_structure",
                              lambda s, d: self.calls.append(("distance", d)), create=True),
            mock.patch.object(io_reader, "validate_charge_and_multiplicity",
                              lambda s, c, m: self.calls.append(("spin", c, m)), create=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.logs = []

    def _load(self, name="water.xyz", content=b"abc"):
        return gui_helpers.load_uploaded_structure(content, name, 1, 2, 0.4, log=self.logs.append)

    def test_content_is_written_to_a_temporary_file_with_the_same_extension_and_removed_afterwards(self):
        self._load("mol.gjf", b"data")
        self.assertTrue(self.seen["path"].endswith(".gjf"))
        self.assertEqual(self.seen["content"], b"data")
        self.assertFalse(os.path.exists(self.seen["path"]))

    def test_name_without_an_extension_is_treated_as_xyz(self):
        self._load("water")
        self.assertTrue(self.seen["path"].endswith(".xyz"))

    def test_reading_comes_before_the_two_validations(self):
        result = self._load()
        self.assertIs(result, self.structure)
        self.assertEqual(self.calls, ["read", ("distance", 0.4), ("spin", 1, 2)])

    def test_summary_of_the_structure_is_logged(self):
        self._load("water.xyz")
        self.assertEqual(len(self.logs), 1)
        self.assertIn("water.xyz", self.logs[0])
        self.assertIn("原子数: 3", self.logs[0])
        self.assertIn("H, O", self.logs[0])

    def test_temporary_file_is_removed_even_when_reading_fails(self):
        def failing_read(path):
            self.seen["path"] = path
            raise io_reader.StructureError("読めません")

        with mock.patch.object(io_reader, "read_structure", failing_read, create=True):
            with self.assertRaises(io_reader.StructureError):
                self._load()
        self.assertFalse(os.path.exists(self.seen["path"]))

    def test_validation_errors_are_passed_on(self):
        def failing(structure, distance):
            raise io_reader.StructureError("近すぎます")

        with mock.patch.object(io_reader, "validate_structure", failing, create=True):
            with self.assertRaises(io_reader.StructureError):
                self._load()


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


class TestFormatCharge(unittest.TestCase):
    def test_positive_values_get_a_plus_sign(self):
        self.assertEqual(gui_helpers.format_charge(1), "+1")
        self.assertEqual(gui_helpers.format_charge(12), "+12")

    def test_zero_and_negative_values_are_shown_as_they_are(self):
        self.assertEqual(gui_helpers.format_charge(0), "0")
        self.assertEqual(gui_helpers.format_charge(-1), "-1")
        self.assertEqual(gui_helpers.format_charge(-3), "-3")


class TestParseCharge(unittest.TestCase):
    def test_plain_numbers_without_a_plus_sign(self):
        self.assertEqual(gui_helpers.parse_charge("1"), 1)
        self.assertEqual(gui_helpers.parse_charge("0"), 0)
        self.assertEqual(gui_helpers.parse_charge("-2"), -2)

    def test_explicit_plus_sign(self):
        self.assertEqual(gui_helpers.parse_charge("+1"), 1)
        self.assertEqual(gui_helpers.parse_charge("+0"), 0)

    def test_surrounding_and_inner_spaces_are_ignored(self):
        self.assertEqual(gui_helpers.parse_charge("  +1 "), 1)
        self.assertEqual(gui_helpers.parse_charge("- 1"), -1)

    def test_full_width_characters_are_accepted(self):
        self.assertEqual(gui_helpers.parse_charge("１"), 1)
        self.assertEqual(gui_helpers.parse_charge("＋２"), 2)
        self.assertEqual(gui_helpers.parse_charge("－１"), -1)

    def test_unicode_minus_sign_is_accepted(self):
        self.assertEqual(gui_helpers.parse_charge("\u22121"), -1)

    def test_invalid_input_raises_a_helpful_error(self):
        for bad in ("", "+", "-", "abc", "1.5", "1e3", "++1", "1 2", None):
            with self.assertRaises(gui_helpers.ChargeInputError) as ctx:
                gui_helpers.parse_charge(bad)
            self.assertIn("整数", str(ctx.exception))

    def test_round_trip_with_format_charge(self):
        for value in range(-5, 6):
            self.assertEqual(gui_helpers.parse_charge(gui_helpers.format_charge(value)), value)


if __name__ == "__main__":
    unittest.main()
