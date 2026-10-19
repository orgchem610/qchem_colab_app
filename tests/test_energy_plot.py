"""
tests/test_energy_plot.py
-------------------------
qchem_colab_app/gui/energy_plot.py(目盛りの計算・クリックできるSVGグラフのHTML生成)の
単体テスト。Colab/ブラウザなしでテストできる部分だけを対象にする。
エネルギーの換算・相対エネルギーは、バックエンドの共通部品(common_backend/energy.py)にあり、
tests/test_energy.py で確認する。

JavaScriptがColab上で実際に動くか(点のクリック → Python呼び出し)はこのテストでは
確認できないため、Colab上での実機確認が必要(README.md参照)。
"""

import os
import re
import sys
import unittest
import xml.dom.minidom

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import energy  # noqa: E402
from qchem_colab_app.gui import colab_widgets, energy_plot as cw  # noqa: E402


def _svg_part(html_text):
    return re.search(r"<svg.*?</svg>", html_text, re.S).group(0)


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


class TestModuleSplit(unittest.TestCase):
    def test_plot_functions_are_not_in_colab_widgets_any_more(self):
        for name in ("nice_ticks", "build_energy_plot_html"):
            self.assertTrue(hasattr(cw, name), name)
            self.assertFalse(hasattr(colab_widgets, name), name)

    def test_energy_conversion_is_defined_only_in_common_backend(self):
        # 換算と相対エネルギーは、バックエンドからも使うため、common_backend/energy.py に1か所だけ置く
        self.assertIs(cw.relative_energies_kcal, energy.relative_energies_kcal)
        self.assertFalse(hasattr(cw, "HARTREE_TO_KCAL_MOL"))

    def test_safe_id_check_is_shared_with_colab_widgets(self):
        self.assertIs(cw.check_safe_id, colab_widgets.check_safe_id)


if __name__ == "__main__":
    unittest.main()
