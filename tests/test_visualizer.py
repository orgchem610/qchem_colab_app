"""
tests/test_visualizer.py
--------------------------
pyscf_backend.visualizer_pyscf(分子軌道の等値面の表示)の単体テスト。
実物のPySCF(水 RHF/6-31G・メチルラジカル UHF/6-31G)と、実物のpy3Dmolで確認する。
cubeファイルは、PySCFで実際に作る(1秒未満)。ブラウザ上での実際の3D表示だけは、Colab上での実機確認が必要
(py3Dmolが作るJavaScriptの内容までを、ここで確認する)。

(原子電荷の色分け・電荷表は gui/plot_common.py に、cubeファイルの値の読み取りは
common_backend/cube.py に移したため、それぞれ tests/test_plot_common.py・tests/test_cube.py が確認する。)
PySCF・py3Dmolが入っていない環境では、それを使うテストだけをスキップする。
"""

import os
import re
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import real_molecules as rm  # noqa: E402
from qchem_colab_app.pyscf_backend import visualizer_pyscf  # noqa: E402


@unittest.skipUnless(rm.HAS_PYSCF, "PySCFがインストールされていないためスキップ")
class TestMoCoeffForCube(unittest.TestCase):
    """cubeファイルを作るときに渡す軌道係数(1つの軌道の列)の取り出し。"""

    def test_closed_shell_two_dimensional_coefficients(self):
        mf = rm.water_rhf()
        self.assertEqual(mf.mo_coeff.ndim, 2)                                # (基底関数, 軌道)
        column = visualizer_pyscf._mo_coeff_for_cube(mf, 1)
        self.assertEqual(column.shape, (13,))
        self.assertTrue(np.array_equal(column, mf.mo_coeff[:, 1]))

    def test_open_shell_three_dimensional_array_uses_the_alpha_orbitals(self):
        mf = rm.methyl_uhf()
        self.assertEqual(np.asarray(mf.mo_coeff).ndim, 3)                    # (スピン, 基底関数, 軌道)
        column = visualizer_pyscf._mo_coeff_for_cube(mf, 2)
        self.assertEqual(column.shape, (15,))
        self.assertTrue(np.array_equal(column, mf.mo_coeff[0][:, 2]))
        self.assertFalse(np.array_equal(column, mf.mo_coeff[1][:, 2]))       # βの軌道とは違う

    def test_open_shell_pair_of_arrays_uses_the_alpha_orbitals(self):
        base = rm.methyl_uhf()
        mf = rm.modified_copy(base, mo_coeff=(base.mo_coeff[0], base.mo_coeff[1]))
        column = visualizer_pyscf._mo_coeff_for_cube(mf, 0)
        self.assertTrue(np.array_equal(column, base.mo_coeff[0][:, 0]))


@unittest.skipUnless(rm.HAS_PYSCF and rm.HAS_PY3DMOL, "PySCFまたはpy3Dmolがインストールされていないためスキップ")
class TestRenderOrbital(unittest.TestCase):
    """実物のPySCF(cubegen)でcubeファイルを作り、実物のpy3Dmolの表示を組み立てる。"""

    @classmethod
    def setUpClass(cls):
        cls.mf = rm.water_rhf()
        cls.view = visualizer_pyscf.render_orbital(cls.mf.mol, cls.mf, 4)    # HOMO
        cls.js = cls.view.startjs

    def test_it_returns_a_py3dmol_view_with_the_cube_data(self):
        import py3Dmol
        self.assertIsInstance(self.view, py3Dmol.view)
        self.assertEqual(self.js.count("addModel("), 1)
        # cubeファイルの本体は大きいため、失敗したときに全体が表示されないよう、assertTrue で確認する
        self.assertTrue('","cube");' in self.js)                             # addModel の形式の指定
        self.assertTrue("Orbital value in real space" in self.js)            # PySCFが書くcubeファイルの見出し

    def test_positive_and_negative_isosurfaces_are_drawn_in_blue_and_red(self):
        self.assertEqual(self.js.count("addVolumetricData("), 2)
        isovals = [float(v) for v in re.findall(r'"isoval":\s*(-?[0-9.eE+-]+)', self.js)]
        self.assertEqual(len(isovals), 2)
        self.assertGreater(isovals[0], 0.0)
        self.assertAlmostEqual(isovals[1], -isovals[0])
        self.assertTrue('"color": "blue"' in self.js)
        self.assertTrue('"color": "red"' in self.js)

    def test_isovalue_is_a_fraction_of_the_maximum_absolute_value_of_the_orbital(self):
        from pyscf.tools import cubegen
        from qchem_colab_app.common_backend import cube
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "check.cube")
            cubegen.orbital(self.mf.mol, path, self.mf.mo_coeff[:, 4])
            expected = cube.max_abs_value(path) * 0.12
        isoval = float(re.findall(r'"isoval":\s*(-?[0-9.eE+-]+)', self.js)[0])
        self.assertAlmostEqual(isoval, expected, places=4)

    def test_the_fraction_can_be_changed(self):
        view = visualizer_pyscf.render_orbital(self.mf.mol, self.mf, 4, isoval_fraction=0.24)
        wide = float(re.findall(r'"isoval":\s*(-?[0-9.eE+-]+)', view.startjs)[0])
        normal = float(re.findall(r'"isoval":\s*(-?[0-9.eE+-]+)', self.js)[0])
        self.assertAlmostEqual(wide, 2 * normal, places=4)

    def test_open_shell_orbitals_are_drawn_from_the_alpha_coefficients(self):
        mf = rm.methyl_uhf()
        view = visualizer_pyscf.render_orbital(mf.mol, mf, 4)                # αスピンのSOMO
        self.assertEqual(view.startjs.count("addVolumetricData("), 2)


class TestChargeFunctionsAreNotInThisModule(unittest.TestCase):
    def test_charge_drawing_lives_in_the_gui_layer(self):
        for name in ("render_charges", "add_atom_charge_labels", "add_atom_charge_spheres",
                     "atomic_charges_table_html", "_charge_gradient_color", "_max_abs_from_cube_file"):
            self.assertFalse(hasattr(visualizer_pyscf, name), name)


if __name__ == "__main__":
    unittest.main()
