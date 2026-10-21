"""
tests/test_visualizer.py
--------------------------
pyscf_backend.visualizer_pyscf のうち、pyscf/py3Dmolを実際には呼ばない部分
(開殻の軌道係数からα軌道を取り出す処理)だけを対象にした単体テスト。
isoval計算やcubeファイルの生成、分子軌道の3D表示そのものはPySCFが必要なため、
Colab上での実機確認が必要(README.md参照)。

(原子電荷の色分け・電荷表は gui/plot_common.py に、cubeファイルの値の読み取りは
common_backend/cube.py に移したため、それぞれ tests/test_plot_common.py・tests/test_cube.py が確認する。)
"""

import os
import sys
import unittest
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.pyscf_backend import visualizer_pyscf  # noqa: E402


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


class TestChargeFunctionsAreNotInThisModule(unittest.TestCase):
    def test_charge_drawing_lives_in_the_gui_layer(self):
        for name in ("render_charges", "add_atom_charge_labels", "add_atom_charge_spheres",
                     "atomic_charges_table_html", "_charge_gradient_color", "_max_abs_from_cube_file"):
            self.assertFalse(hasattr(visualizer_pyscf, name), name)


if __name__ == "__main__":
    unittest.main()
