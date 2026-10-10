"""
test/test_colab_widgets.py
--------------------------
common.colab_widgets のうち、Colab/ブラウザなしでテストできる部分
(エネルギー値の変換・目盛りの計算・SVG/HTMLの生成・ドロップされたファイルの検証)の
単体テスト。

JavaScriptがColab上で実際に動くか(ドロップ・点のクリック → Python呼び出し)は
このテストでは確認できないため、Colab上での実機確認が必要(README.md参照)。
"""

import base64
import os
import re
import sys
import unittest
import xml.dom.minidom

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import colab_widgets as cw  # noqa: E402


def _svg_part(html_text):
    return re.search(r"<svg.*?</svg>", html_text, re.S).group(0)


class TestRelativeEnergies(unittest.TestCase):
    def test_reference_is_the_last_point_in_kcal_per_mol(self):
        values = cw.relative_energies_kcal([-10.0, -10.01])
        self.assertAlmostEqual(values[0], 6.275094740631222)
        self.assertAlmostEqual(values[1], 0.0)

    def test_empty_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            cw.relative_energies_kcal([])

    def test_nan_raises_value_error(self):
        with self.assertRaises(ValueError):
            cw.relative_energies_kcal([-10.0, float("nan")])


class TestNiceTicks(unittest.TestCase):
    def test_integer_ticks_stay_within_range_and_are_whole_numbers(self):
        ticks, step = cw.nice_ticks(0, 17, target=8, integer_only=True)
        self.assertGreaterEqual(step, 1)
        self.assertTrue(all(0 <= t <= 17 for t in ticks))
        self.assertTrue(all(float(t).is_integer() for t in ticks))

    def test_ticks_are_inside_the_requested_range(self):
        ticks, _ = cw.nice_ticks(-2.3, 31.7, target=5)
        self.assertTrue(all(-2.3 <= t <= 31.7 for t in ticks))
        self.assertGreaterEqual(len(ticks), 3)

    def test_zero_span_returns_single_tick(self):
        ticks, _ = cw.nice_ticks(0, 0, integer_only=True)
        self.assertEqual(ticks, [0])


class TestEnergyPlotHtml(unittest.TestCase):
    ENERGIES = [-153.20 - 0.05 * (1 - 0.8 ** i) for i in range(18)]

    def test_svg_is_well_formed_and_has_one_hit_area_per_point(self):
        html_text = cw.build_energy_plot_html(
            self.ENERGIES, callback_name="qchem_cb_x", uid="qchem_plot_t")
        xml.dom.minidom.parseString(_svg_part(html_text))
        self.assertEqual(html_text.count('class="qc-hit"'), len(self.ENERGIES))

    def test_callback_name_is_embedded_when_given(self):
        html_text = cw.build_energy_plot_html(
            self.ENERGIES, callback_name="qchem_cb_x", uid="qchem_plot_t")
        self.assertIn("qchem_cb_x", html_text)
        self.assertIn("invokeFunction", html_text)

    def test_static_plot_has_no_script(self):
        html_text = cw.build_energy_plot_html(self.ENERGIES, uid="qchem_plot_t")
        self.assertNotIn("<script", html_text)
        self.assertNotIn("invokeFunction", html_text)

    def test_default_selection_is_the_last_point_and_index_is_clamped(self):
        last = cw.build_energy_plot_html(self.ENERGIES, uid="qchem_plot_t")
        explicit = cw.build_energy_plot_html(self.ENERGIES, selected_index=17, uid="qchem_plot_t")
        clamped = cw.build_energy_plot_html(self.ENERGIES, selected_index=999, uid="qchem_plot_t")
        self.assertEqual(last, explicit)
        self.assertEqual(last, clamped)

    def test_selected_marker_moves_with_selected_index(self):
        a = cw.build_energy_plot_html(self.ENERGIES, selected_index=0, uid="qchem_plot_t")
        b = cw.build_energy_plot_html(self.ENERGIES, selected_index=5, uid="qchem_plot_t")
        pattern = r'id="qchem_plot_t-sel" transform="([^"]+)"'
        self.assertNotEqual(re.search(pattern, a).group(1), re.search(pattern, b).group(1))

    def test_tooltip_contains_step_number_and_relative_energy(self):
        html_text = cw.build_energy_plot_html([-10.0, -10.01], uid="qchem_plot_t")
        self.assertIn("ステップ 0 / 相対エネルギー +6.28 kcal/mol", html_text)
        self.assertIn("ステップ 1 / 相対エネルギー +0.00 kcal/mol", html_text)

    def test_single_point_does_not_crash(self):
        html_text = cw.build_energy_plot_html([-76.0], callback_name="qchem_cb_x", uid="qchem_plot_t")
        xml.dom.minidom.parseString(_svg_part(html_text))
        self.assertEqual(html_text.count('class="qc-hit"'), 1)

    def test_identical_energies_do_not_crash(self):
        html_text = cw.build_energy_plot_html([-76.0, -76.0, -76.0], uid="qchem_plot_t")
        xml.dom.minidom.parseString(_svg_part(html_text))

    def test_many_points_do_not_crash(self):
        energies = [-76.0 - 0.001 * (1 - 0.97 ** i) for i in range(300)]
        html_text = cw.build_energy_plot_html(energies, uid="qchem_plot_t")
        self.assertEqual(html_text.count('class="qc-hit"'), 300)

    def test_no_negative_zero_tick_labels(self):
        html_text = cw.build_energy_plot_html(self.ENERGIES, uid="qchem_plot_t")
        self.assertNotIn(">-0<", html_text)
        self.assertNotIn(">-0.0<", html_text)

    def test_empty_energies_raise_value_error(self):
        with self.assertRaises(ValueError):
            cw.build_energy_plot_html([])

    def test_unsafe_callback_name_or_uid_is_rejected(self):
        with self.assertRaises(ValueError):
            cw.build_energy_plot_html(self.ENERGIES, callback_name="x');alert(1);//")
        with self.assertRaises(ValueError):
            cw.build_energy_plot_html(self.ENERGIES, uid='a"b')


class TestParseDroppedPayload(unittest.TestCase):
    @staticmethod
    def _payload(name, content=b"3\nwater\nO 0 0 0\nH 0 0 1\nH 0 1 0\n"):
        return {"name": name, "content_b64": base64.b64encode(content).decode("ascii")}

    def test_valid_xyz_returns_name_and_bytes(self):
        content = b"1\nx\nH 0 0 0\n"
        name, data = cw.parse_dropped_payload(self._payload("water.xyz", content))
        self.assertEqual(name, "water.xyz")
        self.assertEqual(data, content)

    def test_extension_check_is_case_insensitive(self):
        name, _ = cw.parse_dropped_payload(self._payload("WATER.XYZ"))
        self.assertEqual(name, "WATER.XYZ")

    def test_directory_part_of_file_name_is_removed(self):
        name, _ = cw.parse_dropped_payload(self._payload("C:\\Users\\me\\water.xyz"))
        self.assertEqual(name, "water.xyz")
        name, _ = cw.parse_dropped_payload(self._payload("../../etc/water.gjf"))
        self.assertEqual(name, "water.gjf")

    def test_unsupported_extension_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            cw.parse_dropped_payload(self._payload("water.mol"))
        self.assertIn("対応形式", str(ctx.exception))

    def test_invalid_base64_is_rejected(self):
        with self.assertRaises(ValueError):
            cw.parse_dropped_payload({"name": "a.xyz", "content_b64": "!!!not base64!!!"})

    def test_empty_file_is_rejected(self):
        with self.assertRaises(ValueError):
            cw.parse_dropped_payload(self._payload("a.xyz", b""))

    def test_too_large_file_is_rejected(self):
        with self.assertRaises(ValueError):
            cw.parse_dropped_payload(self._payload("a.xyz", b"x" * 100), max_bytes=50)

    def test_malformed_payload_is_rejected(self):
        for bad in (None, "text", {"name": "a.xyz"}, {"content_b64": "AAAA"}):
            with self.assertRaises(ValueError):
                cw.parse_dropped_payload(bad)


class TestDropZoneHtml(unittest.TestCase):
    def test_contains_callback_extensions_and_size_limit(self):
        html_text = cw.build_drop_zone_html("qchem_cb_drop", uid="qchem_drop_t")
        self.assertIn("qchem_cb_drop", html_text)
        for ext in (".xyz", ".com", ".gjf", ".pdb"):
            self.assertIn(ext, html_text)
        self.assertIn(str(cw.MAX_DROPPED_FILE_BYTES), html_text)

    def test_all_placeholders_are_replaced(self):
        html_text = cw.build_drop_zone_html("qchem_cb_drop", uid="qchem_drop_t")
        self.assertNotRegex(html_text, r"__[A-Z_]+__")

    def test_unsafe_callback_name_is_rejected(self):
        with self.assertRaises(ValueError):
            cw.build_drop_zone_html("bad name'")


if __name__ == "__main__":
    unittest.main()
