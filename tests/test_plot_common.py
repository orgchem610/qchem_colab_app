"""
tests/test_plot_common.py
-------------------------
gui.plot_common のうち、原子電荷の可視化(色分け・数値ラベル・電荷表)の単体テスト。
原子電荷の色分け・ラベル・球の部品は、呼び出しを記録するテスト用のクラス(FakeView)で確認する。
render_charges などの view を作る関数は、実物のpy3Dmolで確認する(組み立てたJavaScriptの内容まで)。
ブラウザ上での実際の3D表示だけは、Colab上での実機確認が必要。py3Dmolが入っていない環境では、
それを使うテストだけをスキップする。
"""

import os
import re
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import real_molecules as rm  # noqa: E402
from qchem_colab_app.gui import plot_common  # noqa: E402

SKIP_NO_PY3DMOL = "py3Dmolがインストールされていないためスキップ"


class FakeView:
    """py3Dmol.view の代用品。呼ばれたメソッドと引数を記録する。"""

    def __init__(self, **kwargs):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return record

    def called(self, name):
        return [c for c in self.calls if c[0] == name]


WATER_SYMBOLS = ["O", "H", "H"]
WATER_COORDS = [[0.0, 0.0, 0.1173], [0.0, 0.7572, -0.4692], [0.0, -0.7572, -0.4692]]
WATER_CHARGES = [("O", -0.45), ("H", 0.225), ("H", 0.225)]


class TestAtomicChargesTable(unittest.TestCase):
    def test_table_contains_all_atoms_with_signed_charges(self):
        html = plot_common.atomic_charges_table_html(WATER_CHARGES)
        self.assertIn("<table", html)
        self.assertIn("O", html)
        self.assertIn("-0.450", html)
        self.assertIn("+0.225", html)
        self.assertEqual(html.count("<tr>"), 4)          # 見出し1行 + 原子3行


class TestChargeGradientColor(unittest.TestCase):
    def test_neutral_charge_is_green(self):
        self.assertEqual(plot_common._charge_gradient_color(0.0, 1.0), "#33cc33")

    def test_max_positive_charge_is_pure_blue(self):
        self.assertEqual(plot_common._charge_gradient_color(1.0, 1.0), "#2255ff")

    def test_max_negative_charge_is_pure_red(self):
        self.assertEqual(plot_common._charge_gradient_color(-1.0, 1.0), "#ff2222")

    def test_intermediate_positive_charge_is_between_green_and_blue(self):
        color = plot_common._charge_gradient_color(0.5, 1.0)
        self.assertNotEqual(color, "#33cc33")
        self.assertNotEqual(color, "#2255ff")

    def test_zero_max_abs_does_not_crash(self):
        # 全原子の電荷が0(理論上あり得ないが、防御的に確認)でも例外を出さない
        self.assertEqual(plot_common._charge_gradient_color(0.0, 0.0), "#33cc33")


class TestAddAtomChargeLabels(unittest.TestCase):
    def test_one_label_per_atom_at_the_atom_position(self):
        view = FakeView()
        plot_common.add_atom_charge_labels(view, WATER_COORDS, WATER_CHARGES)
        labels = view.called("addLabel")
        self.assertEqual(len(labels), 3)
        self.assertEqual(labels[0][1][0], "-0.45")
        self.assertEqual(labels[1][1][0], f"{0.225:+.2f}")
        self.assertEqual(labels[0][1][1]["position"], {"x": 0.0, "y": 0.0, "z": 0.1173})

    def test_positive_is_blue_and_negative_is_red(self):
        view = FakeView()
        plot_common.add_atom_charge_labels(view, WATER_COORDS, WATER_CHARGES)
        colors = [c[1][1]["backgroundColor"] for c in view.called("addLabel")]
        self.assertEqual(colors, ["#ff5b5b", "#5b9bff", "#5b9bff"])

    def test_works_with_plain_lists_without_any_pyscf_object(self):
        # 引数が、PySCFのMoleではなく、プレーンなリストだけで足りること
        view = FakeView()
        plot_common.add_atom_charge_labels(view, [(1, 2, 3)], [("H", 0.1)])
        self.assertEqual(len(view.called("addLabel")), 1)


class TestAddAtomChargeSpheres(unittest.TestCase):
    def test_one_sphere_per_atom_with_charge_colors(self):
        view = FakeView()
        plot_common.add_atom_charge_spheres(view, WATER_COORDS, WATER_CHARGES)
        spheres = [c[1][0] for c in view.called("addSphere")]
        self.assertEqual(len(spheres), 3)
        self.assertEqual(spheres[0]["color"], "#ff2222")          # 最大|電荷|の負電荷=赤
        self.assertEqual(spheres[1]["color"], plot_common._charge_gradient_color(0.225, 0.45))
        self.assertEqual(spheres[0]["center"], {"x": 0.0, "y": 0.0, "z": 0.1173})

    def test_radius_is_based_on_the_van_der_waals_radius(self):
        view = FakeView()
        plot_common.add_atom_charge_spheres(view, WATER_COORDS, WATER_CHARGES, size_variation=0.0)
        radii = [c[1][0]["radius"] for c in view.called("addSphere")]
        self.assertAlmostEqual(radii[0], 1.52)                    # O
        self.assertAlmostEqual(radii[1], 1.20)                    # H

    def test_larger_absolute_charge_gives_a_slightly_larger_sphere(self):
        view = FakeView()
        plot_common.add_atom_charge_spheres(view, [[0, 0, 0], [3, 0, 0]], [("C", 0.5), ("C", 0.1)])
        radii = [c[1][0]["radius"] for c in view.called("addSphere")]
        self.assertGreater(radii[0], radii[1])

    def test_unknown_element_uses_the_default_radius(self):
        view = FakeView()
        plot_common.add_atom_charge_spheres(view, [[0, 0, 0]], [("Xx", 0.1)], size_variation=0.0)
        self.assertAlmostEqual(view.called("addSphere")[0][1][0]["radius"], plot_common._DEFAULT_VDW_RADIUS)

    def test_empty_charges_do_not_crash(self):
        view = FakeView()
        plot_common.add_atom_charge_spheres(view, [], [])
        self.assertEqual(view.called("addSphere"), [])


@unittest.skipUnless(rm.HAS_PY3DMOL, SKIP_NO_PY3DMOL)
class TestRenderCharges(unittest.TestCase):
    """実物のpy3Dmolで view を作り、それが組み立てたJavaScript(呼び出しと引数)を確認する。"""

    def _render(self, **kwargs):
        return plot_common.render_charges(WATER_SYMBOLS, WATER_COORDS, WATER_CHARGES, **kwargs)

    def test_structure_spheres_and_labels_are_added(self):
        import py3Dmol
        view = self._render()
        self.assertIsInstance(view, py3Dmol.view)
        js = view.startjs
        self.assertEqual(js.count("addModel("), 1)
        self.assertTrue('addModel("3\\nstructure' in js)                 # 原子数3の xyz
        self.assertEqual(js.count("addSphere("), 3)
        self.assertEqual(js.count("addLabel("), 3)
        self.assertGreaterEqual(js.count("zoomTo("), 1)

    def test_spheres_and_labels_carry_the_charge_colors_and_values(self):
        js = self._render().startjs
        self.assertTrue('"color": "#ff2222"' in js)                       # 最大|電荷|の負電荷=赤の球
        self.assertTrue('"backgroundColor": "#ff5b5b"' in js)             # 負のラベル=赤系
        self.assertEqual(js.count('"backgroundColor": "#5b9bff"'), 2)     # 正のラベル=青系(水素2個)
        self.assertTrue('addLabel("-0.45"' in js)
        self.assertEqual(js.count('addLabel("+0.23"'), 2)

    def test_labels_can_be_hidden(self):
        js = self._render(show_labels=False).startjs
        self.assertEqual(js.count("addSphere("), 3)
        self.assertEqual(js.count("addLabel("), 0)


@unittest.skipUnless(rm.HAS_PY3DMOL, SKIP_NO_PY3DMOL)
class TestRenderStructureAndVibration(unittest.TestCase):
    """構造・振動アニメーションの表示も、実物のpy3Dmolで、組み立てたJavaScriptまで確認する。"""

    def test_single_structure(self):
        import py3Dmol
        view = plot_common.render_single_structure(WATER_SYMBOLS, WATER_COORDS)
        self.assertIsInstance(view, py3Dmol.view)
        self.assertEqual(view.startjs.count("addModel("), 1)
        self.assertTrue('"stick"' in view.startjs)

    def _vibration(self, frequency):
        modes = np.zeros((3, 3, 3))
        modes[0, 0, 0] = 1.0
        return plot_common.render_vibration(WATER_SYMBOLS, WATER_COORDS, [frequency, 3700.0, 3800.0], modes,
                                            mode_index=0, n_frames=20)

    def test_vibration_is_an_animation_of_the_requested_number_of_frames(self):
        view, label = self._vibration(1600.5)
        js = view.startjs
        self.assertEqual(js.count("addModelsAsFrames("), 1)
        self.assertEqual(len(re.findall(r"frame \d+", js)), 20)
        self.assertEqual(js.count("animate("), 1)
        self.assertTrue('"loop": "backAndForth"' in js)
        self.assertEqual(label, "振動数 1600.5 cm\u207b\u00b9")

    def test_an_imaginary_frequency_is_marked_in_the_label(self):
        _, label = self._vibration(-120.0)
        self.assertEqual(label, "振動数 -120.0 cm\u207b\u00b9(虚振動)")


class TestPlotCommonDoesNotDependOnAnEngine(unittest.TestCase):
    def test_no_engine_package_is_imported(self):
        import ast
        path = os.path.join(os.path.dirname(plot_common.__file__), "plot_common.py")
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        modules = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module]
        modules += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        self.assertFalse([m for m in modules if "pyscf" in m or "uma" in m])


if __name__ == "__main__":
    unittest.main()
