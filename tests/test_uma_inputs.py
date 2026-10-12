"""
tests/test_uma_inputs.py
------------------------
uma_app.uma_inputs(電荷の入力・表示、ダウンロードの既定ファイル名)の単体テスト。
ipywidgetsには依存しない。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uma_app import uma_inputs  # noqa: E402


class TestFormatCharge(unittest.TestCase):
    def test_positive_values_get_a_plus_sign(self):
        self.assertEqual(uma_inputs.format_charge(1), "+1")
        self.assertEqual(uma_inputs.format_charge(12), "+12")

    def test_zero_and_negative_values_are_shown_as_they_are(self):
        self.assertEqual(uma_inputs.format_charge(0), "0")
        self.assertEqual(uma_inputs.format_charge(-1), "-1")
        self.assertEqual(uma_inputs.format_charge(-3), "-3")


class TestParseCharge(unittest.TestCase):
    def test_plain_numbers_without_a_plus_sign(self):
        self.assertEqual(uma_inputs.parse_charge("1"), 1)
        self.assertEqual(uma_inputs.parse_charge("0"), 0)
        self.assertEqual(uma_inputs.parse_charge("-2"), -2)

    def test_explicit_plus_sign(self):
        self.assertEqual(uma_inputs.parse_charge("+1"), 1)
        self.assertEqual(uma_inputs.parse_charge("+0"), 0)

    def test_surrounding_and_inner_spaces_are_ignored(self):
        self.assertEqual(uma_inputs.parse_charge("  +1 "), 1)
        self.assertEqual(uma_inputs.parse_charge("- 1"), -1)

    def test_full_width_characters_are_accepted(self):
        self.assertEqual(uma_inputs.parse_charge("１"), 1)
        self.assertEqual(uma_inputs.parse_charge("＋２"), 2)
        self.assertEqual(uma_inputs.parse_charge("－１"), -1)

    def test_unicode_minus_sign_is_accepted(self):
        self.assertEqual(uma_inputs.parse_charge("\u22121"), -1)

    def test_invalid_input_raises_a_helpful_error(self):
        for bad in ("", "+", "-", "abc", "1.5", "1e3", "++1", "1 2", None):
            with self.assertRaises(uma_inputs.ChargeInputError) as ctx:
                uma_inputs.parse_charge(bad)
            self.assertIn("整数", str(ctx.exception))

    def test_round_trip_with_format_charge(self):
        for value in range(-5, 6):
            self.assertEqual(uma_inputs.parse_charge(uma_inputs.format_charge(value)), value)


class TestDefaultDownloadStem(unittest.TestCase):
    def test_input_file_name_gets_a_result_suffix(self):
        self.assertEqual(uma_inputs.default_download_stem("water.xyz"), "water_result")
        self.assertEqual(uma_inputs.default_download_stem("ethanol.gjf"), "ethanol_result")

    def test_only_the_last_extension_is_removed(self):
        self.assertEqual(uma_inputs.default_download_stem("mol.v2.xyz"), "mol.v2_result")

    def test_directory_part_is_removed(self):
        self.assertEqual(uma_inputs.default_download_stem("C:\\Users\\me\\water.xyz"), "water_result")
        self.assertEqual(uma_inputs.default_download_stem("../a/water.xyz"), "water_result")

    def test_characters_not_allowed_in_file_names_are_removed(self):
        self.assertEqual(uma_inputs.default_download_stem('a?b*c.xyz'), "abc_result")

    def test_japanese_names_are_kept(self):
        self.assertEqual(uma_inputs.default_download_stem("エタノール.xyz"), "エタノール_result")

    def test_unusable_names_fall_back_to_result(self):
        for bad in ("", None, ".xyz", "???.xyz"):
            self.assertEqual(uma_inputs.default_download_stem(bad), "result")


class TestSanitizeFilenameStem(unittest.TestCase):
    def test_empty_input_falls_back_to_result(self):
        self.assertEqual(uma_inputs.sanitize_filename_stem(""), "result")
        self.assertEqual(uma_inputs.sanitize_filename_stem("   "), "result")
        self.assertEqual(uma_inputs.sanitize_filename_stem(None), "result")

    def test_forbidden_characters_are_removed(self):
        self.assertEqual(uma_inputs.sanitize_filename_stem('my/file:name?'), "myfilename")

    def test_normal_names_are_unchanged(self):
        self.assertEqual(uma_inputs.sanitize_filename_stem("water_result"), "water_result")


if __name__ == "__main__":
    unittest.main()
