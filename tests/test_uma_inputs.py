"""
tests/test_uma_inputs.py
------------------------
uma_app.uma_inputs(電荷の入力・表示)の単体テスト。
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


if __name__ == "__main__":
    unittest.main()
