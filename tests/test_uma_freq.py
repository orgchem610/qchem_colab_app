"""
tests/test_uma_freq.py
----------------------
uma_backend.uma_freq.run_frequency_analysis と FrequencyResult の単体テスト。

数値計算そのもの(中心差分のHessian・調和解析・ZPEの式)は、common_backend/vibration.py に移したため、
tests/test_vibration.py で確認している。ここでは、UMAの計算器から力を取り出して結果にまとめる部分
(振動数の個数・ZPEの単位換算・虚振動の注意文・原子が1個のときの扱い・結果が共通の FrequencyResult であること)を確認する。

    - TestRunFrequencyAnalysis : ASEもUMAも使わず、バネのモデルを返す代用のAtoms・計算器で確認する
    - TestAgainstAse           : ASEが入っている環境では、ASE付属の簡易ポテンシャル(EMT)を使い、ASEの
                                 Vibrations(力の中心差分)と振動数が一致することも確認する
                                 (ASEが入っていない環境では、この部分だけスキップされる)
UMAを使った実際の振動数計算は、Colab上での実機確認が必要。
"""

import importlib.util
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # 同じフォルダの test_vibration.py を読むため

from qchem_colab_app.common_backend import energy, vibration  # noqa: E402
from qchem_colab_app.uma_backend import uma_freq  # noqa: E402
from test_vibration import (  # noqa: E402
    DELTA, equilibrium_pairs, select_vibrational, signed_frequencies, spring_forces_fn)

HAS_ASE = importlib.util.find_spec("ase") is not None


class FakeAtoms:
    """run_frequency_analysis が使う最小限の機能だけを持つ、ASE Atoms の代用品。

    .calc に、座標を受け取って力を返す関数を入れて使う(バネのモデルの力など)。
    """

    def __init__(self, positions, masses):
        self.positions = np.array(positions, dtype=float)
        self.masses = list(masses)
        self.calc = None

    def __len__(self):
        return len(self.positions)

    def copy(self):
        clone = FakeAtoms(self.positions, self.masses)
        clone.calc = self.calc
        return clone

    def set_positions(self, positions):
        self.positions = np.array(positions, dtype=float)

    def get_positions(self):
        return self.positions.copy()

    def get_masses(self):
        return np.array(self.masses)

    def get_forces(self):
        return self.calc(self.positions)


def diatomic(k, masses=(1.008, 35.45)):
    positions = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.2]])
    atoms = FakeAtoms(positions, masses)
    calculator = spring_forces_fn(equilibrium_pairs(positions, [(0, 1, k)]))
    return atoms, calculator


class TestRunFrequencyAnalysis(unittest.TestCase):
    CFG = {"displacement_angstrom": DELTA, "small_imaginary_cm1": 50}

    def test_diatomic_gives_one_real_mode_and_converted_zpe(self):
        atoms, calculator = diatomic(30.0)
        result = uma_freq.run_frequency_analysis(atoms, calculator, self.CFG)
        self.assertEqual(len(result.frequencies_cm1), 1)
        self.assertEqual(result.normal_modes.shape, (1, 2, 3))
        self.assertEqual(result.n_imaginary, 0)
        self.assertEqual(result.warning_message, "")
        zpe_ev = 0.5 * result.frequencies_cm1[0] * 1.239841984e-4
        self.assertAlmostEqual(result.zpe_hartree * energy.HARTREE_TO_EV, zpe_ev, places=12)
        self.assertAlmostEqual(result.zpe_kcal_per_mol / result.zpe_hartree,
                               energy.HARTREE_TO_KCAL_MOL, places=6)

    def test_the_result_is_the_common_frequency_result(self):
        atoms, calculator = diatomic(30.0)
        result = uma_freq.run_frequency_analysis(atoms, calculator, self.CFG)
        self.assertIs(type(result), vibration.FrequencyResult)
        self.assertFalse(hasattr(uma_freq, "FrequencyResult"))

    def test_input_atoms_are_not_modified(self):
        atoms, calculator = diatomic(30.0)
        before = atoms.get_positions().tolist()
        uma_freq.run_frequency_analysis(atoms, calculator, self.CFG)
        self.assertEqual(atoms.get_positions().tolist(), before)

    def test_progress_is_reported_per_atom(self):
        atoms, calculator = diatomic(30.0)
        calls = []
        uma_freq.run_frequency_analysis(atoms, calculator, self.CFG,
                                        progress=lambda done, total: calls.append((done, total)))
        self.assertEqual(calls, [(1, 2), (2, 2)])

    def test_large_imaginary_frequency_warns_about_a_non_minimum_structure(self):
        atoms, calculator = diatomic(-30.0)
        result = uma_freq.run_frequency_analysis(atoms, calculator, self.CFG)
        self.assertEqual(result.n_imaginary, 1)
        self.assertLess(result.frequencies_cm1[0], -50)
        self.assertIn("真の極小構造", result.warning_message)
        self.assertNotIn("数値誤差", result.warning_message)

    def test_small_imaginary_frequency_warns_about_numerical_noise(self):
        atoms, calculator = diatomic(-0.005)
        result = uma_freq.run_frequency_analysis(atoms, calculator, self.CFG)
        self.assertEqual(result.n_imaginary, 1)
        self.assertGreaterEqual(result.frequencies_cm1[0], -50)
        self.assertIn("数値誤差", result.warning_message)

    def test_single_atom_has_no_modes_and_a_warning(self):
        atoms = FakeAtoms([[0.0, 0.0, 0.0]], [12.0])
        result = uma_freq.run_frequency_analysis(atoms, lambda pos: np.zeros((1, 3)), self.CFG)
        self.assertEqual(result.frequencies_cm1, [])
        self.assertIsNone(result.normal_modes)
        self.assertIn("1個だけ", result.warning_message)


@unittest.skipUnless(HAS_ASE, "ASEがインストールされていないためスキップ")
class TestAgainstAse(unittest.TestCase):
    DELTA = 0.01                                 # ASEのVibrationsの既定値で、uma_defaults.yamlの既定値でもある

    @staticmethod
    def _relaxed(symbols, positions):
        """EMTで、力がほぼ0になるまで緩和した構造(振動数解析の前提)を作る。"""
        from ase import Atoms
        from ase.calculators.emt import EMT
        from ase.optimize import BFGS
        atoms = Atoms(symbols, positions=positions)
        atoms.calc = EMT()
        BFGS(atoms, logfile=None).run(fmax=1e-6, steps=1000)
        return atoms

    def _ase_frequencies(self, atoms):
        from ase.vibrations import Vibrations
        with tempfile.TemporaryDirectory() as tmp:
            vib = Vibrations(atoms, name=os.path.join(tmp, "vib"), delta=self.DELTA)
            vib.run()
            return np.asarray(vib.get_frequencies())

    def _compare_with_vibrations(self, symbols, positions, n_vibrational):
        from ase.calculators.emt import EMT
        atoms = self._relaxed(symbols, positions)
        self.assertLess(np.abs(atoms.get_forces()).max(), 1e-3)       # 緩和できている

        ours = uma_freq.run_frequency_analysis(atoms, EMT(), {"displacement_angstrom": self.DELTA})
        ase_all = self._ase_frequencies(atoms)
        theirs = select_vibrational(ase_all, n_vibrational)

        self.assertEqual(len(ours.frequencies_cm1), n_vibrational)
        np.testing.assert_allclose(ours.frequencies_cm1, theirs, rtol=1e-3, atol=0.5)
        # 並進・回転に由来する値が、振動より十分小さいこと(絶対値の大きいものを振動とみなした前提の確認)
        magnitudes = np.sort(np.abs(signed_frequencies(ase_all)))
        n_other = len(ase_all) - n_vibrational
        self.assertLess(magnitudes[n_other - 1], 0.2 * magnitudes[n_other])

    def test_linear_diatomic_matches_ase_vibrations(self):
        # 直線分子: 振動モードは3N-5=1個(ASEの結果には、ゼロ付近の値が5個含まれる)
        self._compare_with_vibrations("Cu2", [[0.0, 0.0, 0.0], [2.3, 0.3, 0.1]], 1)

    def test_nonlinear_triatomic_matches_ase_vibrations(self):
        self._compare_with_vibrations("Cu3", [[0.0, 0.0, 0.0], [2.5, 0.0, 0.0], [1.25, 2.1, 0.1]], 3)

    def test_tetraatomic_cluster_matches_ase_vibrations(self):
        positions = [[0.0, 0.0, 0.0], [2.5, 0.0, 0.0], [1.25, 2.17, 0.0], [1.3, 0.7, 2.0]]
        self._compare_with_vibrations("Cu4", positions, 6)


if __name__ == "__main__":
    unittest.main()
