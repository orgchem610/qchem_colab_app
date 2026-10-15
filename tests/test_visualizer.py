"""
tests/test_visualizer.py
--------------------------
qcapp.visualizer_pyscf のうち、pyscf/py3Dmolを実際には呼ばない部分
(cubeファイルのテキストパース、電荷テーブルのHTML整形)だけを対象にした
単体テスト。isoval計算やMulliken電荷計算そのものはPySCFが必要なため、
Colab上での実機確認が必要(README.md参照)。
"""

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qcapp import visualizer_pyscf  # noqa: E402


_FAKE_CUBE = """orbital
comment
2 0.0 0.0 0.0
2 1.0 0.0 0.0
2 0.0 1.0 0.0
1 0.0 0.0 0.0 0.0
1 0.0 0.0 0.0 1.0
 0.01 -0.02
 0.5 -0.30
"""


class TestMaxAbsFromCubeFile(unittest.TestCase):
    def test_finds_correct_max_absolute_value(self):
        fd, path = tempfile.mkstemp(suffix=".cube")
        with os.fdopen(fd, "w") as f:
            f.write(_FAKE_CUBE)
        max_abs = visualizer_pyscf._max_abs_from_cube_file(path)
        self.assertAlmostEqual(max_abs, 0.5)


class TestMoCoeffForCube(unittest.TestCase):
    """cubeファイルを作るときに渡す軌道係数(1つの軌道の列)の取り出し。"""

    def test_closed_shell_two_dimensional_coefficients(self):
        coeff = np.arange(12.0).reshape(4, 3)            # (基底関数, 軌道)
        column = visualizer_pyscf._mo_coeff_for_cube(SimpleNamespace(mo_coeff=coeff), 1)
        self.assertEqual(column.shape, (4,))
        self.assertTrue(np.array_equal(column, coeff[:, 1]))

    def test_open_shell_three_dimensional_array_uses_the_alpha_orbitals(self):
        coeff = np.arange(24.0).reshape(2, 4, 3)         # (スピン, 基底関数, 軌道)
        column = visualizer_pyscf._mo_coeff_for_cube(SimpleNamespace(mo_coeff=coeff), 2)
        self.assertEqual(column.shape, (4,))
        self.assertTrue(np.array_equal(column, coeff[0][:, 2]))

    def test_open_shell_pair_of_arrays_uses_the_alpha_orbitals(self):
        alpha, beta = np.arange(12.0).reshape(4, 3), -np.arange(12.0).reshape(4, 3)
        column = visualizer_pyscf._mo_coeff_for_cube(SimpleNamespace(mo_coeff=(alpha, beta)), 0)
        self.assertTrue(np.array_equal(column, alpha[:, 0]))


class TestAtomicChargesTable(unittest.TestCase):
    def test_table_contains_all_atoms_with_signed_charges(self):
        charges = [("O", -0.45), ("H", 0.225), ("H", 0.225)]
        html = visualizer_pyscf.atomic_charges_table_html(charges)
        self.assertIn("<table", html)
        self.assertIn("O", html)
        self.assertIn("-0.450", html)
        self.assertIn("+0.225", html)


class TestChargeGradientColor(unittest.TestCase):
    def test_neutral_charge_is_green(self):
        self.assertEqual(visualizer_pyscf._charge_gradient_color(0.0, 1.0), "#33cc33")

    def test_max_positive_charge_is_pure_blue(self):
        self.assertEqual(visualizer_pyscf._charge_gradient_color(1.0, 1.0), "#2255ff")

    def test_max_negative_charge_is_pure_red(self):
        self.assertEqual(visualizer_pyscf._charge_gradient_color(-1.0, 1.0), "#ff2222")

    def test_intermediate_positive_charge_is_between_green_and_blue(self):
        color = visualizer_pyscf._charge_gradient_color(0.5, 1.0)
        # 緑(0x33cc33)と青(0x2255ff)のちょうど中間程度になっているはず
        self.assertNotEqual(color, "#33cc33")
        self.assertNotEqual(color, "#2255ff")

    def test_zero_max_abs_does_not_crash(self):
        # 全原子の電荷が0(理論上あり得ないが、防御的に確認)でも例外を出さない
        color = visualizer_pyscf._charge_gradient_color(0.0, 0.0)
        self.assertEqual(color, "#33cc33")


if __name__ == "__main__":
    unittest.main()
