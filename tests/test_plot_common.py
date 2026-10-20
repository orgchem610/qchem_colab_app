"""
tests/test_plot_common.py
-------------------------
gui.plot_common のうち、原子電荷の可視化(色分け・数値ラベル・電荷表)の単体テスト。
py3Dmol・ipywidgetsがなくても動く(py3Dmolのviewは、呼び出しを記録する代用品を使う)。
構造・振動アニメーションの実際の3D表示は、Colab上での実機確認が必要。
"""

import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.gui import plot_common  # noqa: E402


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


class TestRenderCharges(unittest.TestCase):
    """py3Dmolを、代用の view に差し替えて、組み立ての順序と引数だけを確認する。"""

    def _render(self, **kwargs):
        fake_module = types.SimpleNamespace(view=lambda **kw: self.view)
        self.view = FakeView()
        with mock.patch.dict(sys.modules, {"py3Dmol": fake_module}):
            return plot_common.render_charges(WATER_SYMBOLS, WATER_COORDS, WATER_CHARGES, **kwargs)

    def test_structure_spheres_and_labels_are_added(self):
        view = self._render()
        self.assertIs(view, self.view)
        self.assertEqual(len(view.called("addModel")), 1)
        xyz = view.called("addModel")[0][1][0]
        self.assertTrue(xyz.startswith("3\n"))
        self.assertEqual(len(view.called("addSphere")), 3)
        self.assertEqual(len(view.called("addLabel")), 3)
        self.assertEqual(len(view.called("zoomTo")), 1)

    def test_labels_can_be_hidden(self):
        view = self._render(show_labels=False)
        self.assertEqual(len(view.called("addSphere")), 3)
        self.assertEqual(view.called("addLabel"), [])


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
