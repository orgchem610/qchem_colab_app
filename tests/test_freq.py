"""
tests/test_freq.py
------------------
pyscf_backend.freq(PySCF版の振動数解析)の単体テスト。
実物のPySCFで、水(HF/STO-3G)のHessian・調和振動数・熱力学量を実際に計算して確認する(1秒未満)。
虚振動は、鞍点である直線の水で、実際に出す。熱力学量の失敗や、PySCFの版によるキー名の違いを確認する
テストは、実物の pyscf.hessian.thermo の関数だけを差し替える(SCFオブジェクトは実物のまま)。
PySCFが入っていない環境では、PySCFを使うテストだけをスキップする。
"""

import os
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import real_molecules  # noqa: E402
from qchem_colab_app.common_backend import vibration  # noqa: E402
from qchem_colab_app.pyscf_backend import freq  # noqa: E402

DEFAULTS = {"frequency": {"temperature_K": 298.15, "pressure_Pa": 101325}}
SKIP_NO_PYSCF = "PySCFがインストールされていないためスキップ"


class TestFrequencyResultOfPyscf(unittest.TestCase):
    def test_it_extends_the_common_result_with_the_thermochemistry_items(self):
        result = freq.FrequencyResult()
        self.assertIsInstance(result, vibration.FrequencyResult)
        self.assertIsNone(result.gibbs_hartree)
        self.assertIsNone(result.temperature_K)
        self.assertIsNone(result.zpe_hartree)

    def test_the_common_items_work_in_the_subclass(self):
        result = freq.FrequencyResult()
        result.frequencies_cm1 = [-50.0, 100.0]
        result.zpe_hartree = 0.01
        self.assertEqual(result.n_imaginary, 1)
        self.assertGreater(result.zpe_kcal_per_mol, 6.0)


class TestSignedWavenumber(unittest.TestCase):
    """PySCFは、虚振動を、実部が0の複素数で返す。虚振動は、負の値にそろえる。"""

    def test_real_values_are_kept(self):
        self.assertEqual(freq._signed_wavenumber(1600.5), 1600.5)
        self.assertEqual(freq._signed_wavenumber(-35.0), -35.0)
        self.assertEqual(freq._signed_wavenumber(np.float64(2.5)), 2.5)

    def test_a_complex_value_with_an_imaginary_part_is_an_imaginary_frequency(self):
        self.assertEqual(freq._signed_wavenumber(2268.5j), -2268.5)
        self.assertEqual(freq._signed_wavenumber(np.complex128(0 + 100j)), -100.0)

    def test_a_complex_value_without_an_imaginary_part_is_its_real_part(self):
        self.assertEqual(freq._signed_wavenumber(3718.5 + 0j), 3718.5)

    def test_the_result_is_a_plain_float(self):
        self.assertIs(type(freq._signed_wavenumber(np.complex128(1.0 + 0j))), float)


@unittest.skipUnless(real_molecules.HAS_PYSCF, SKIP_NO_PYSCF)
class TestRunFrequencyAnalysis(unittest.TestCase):
    def _run(self, mf=None):
        return freq.run_frequency_analysis(mf or real_molecules.water_equilibrium_rhf(), DEFAULTS)

    def test_frequencies_and_modes_are_taken_from_pyscf(self):
        result = self._run()
        self.assertEqual(len(result.frequencies_cm1), 3)                  # 非直線の三原子分子: 3N-6 = 3
        self.assertTrue(all(1000.0 < f < 5000.0 for f in result.frequencies_cm1), result.frequencies_cm1)
        self.assertEqual(result.frequencies_cm1, sorted(result.frequencies_cm1))
        self.assertEqual(np.asarray(result.normal_modes).shape, (3, 3, 3))
        self.assertEqual(result.n_imaginary, 0)
        self.assertEqual(result.warning_message, "")
        self.assertGreaterEqual(result.elapsed_seconds, 0.0)

    def test_frequencies_agree_with_pyscf_called_directly(self):
        from pyscf.hessian import thermo
        mf = real_molecules.water_equilibrium_rhf()
        expected = thermo.harmonic_analysis(mf.mol, mf.Hessian().kernel())["freq_wavenumber"]
        self.assertTrue(np.allclose(self._run(mf).frequencies_cm1, np.real(expected)))

    def test_thermochemistry_is_stored_in_the_result(self):
        mf = real_molecules.water_equilibrium_rhf()
        result = self._run(mf)
        self.assertTrue(0.01 < result.zpe_hartree < 0.04, result.zpe_hartree)        # 水のZPEは約0.024 Hartree
        self.assertLess(abs(result.gibbs_hartree - mf.e_tot), 0.05)                  # 全エネルギーに熱の補正を足した値
        self.assertEqual(result.temperature_K, 298.15)

    def test_the_result_is_the_pyscf_subclass(self):
        self.assertIsInstance(self._run(), freq.FrequencyResult)

    def test_imaginary_frequencies_of_a_saddle_point_are_counted_with_a_warning(self):
        # 直線の水(鞍点): 曲がる向きの振動が、縮退した2個の虚振動になる。PySCFは、これを複素数で返す
        result = self._run(real_molecules.linear_water_rhf())
        self.assertEqual(result.n_imaginary, 2)
        self.assertEqual(len(result.frequencies_cm1), 4)                              # 直線の三原子分子: 3N-5 = 4
        self.assertTrue(all(f < -1000.0 for f in result.frequencies_cm1[:2]), result.frequencies_cm1)
        self.assertTrue(all(f > 1000.0 for f in result.frequencies_cm1[2:]), result.frequencies_cm1)
        self.assertIn("虚振動が2個検出されました", result.warning_message)

    def test_failure_of_the_thermochemistry_keeps_the_frequencies(self):
        from pyscf.hessian import thermo
        with mock.patch.object(thermo, "thermo", side_effect=RuntimeError("boom")):
            result = self._run()
        self.assertEqual(len(result.frequencies_cm1), 3)
        self.assertIsNone(result.zpe_hartree)
        self.assertIsNone(result.gibbs_hartree)
        self.assertIsNone(result.temperature_K)
        self.assertIn("熱力学量(ZPE・自由エネルギー)の計算に失敗しました", result.warning_message)
        self.assertIn("boom", result.warning_message)

    def test_missing_free_energy_is_treated_as_a_thermochemistry_failure_without_partial_values(self):
        from pyscf.hessian import thermo
        with mock.patch.object(thermo, "thermo", return_value={"ZPE": (0.02, "Eh")}):
            result = self._run()
        self.assertIsNone(result.zpe_hartree)
        self.assertIn("計算に失敗しました", result.warning_message)

    def test_alternative_key_names_of_other_pyscf_versions_are_accepted(self):
        from pyscf.hessian import thermo
        mf = real_molecules.water_equilibrium_rhf()
        actual = thermo.harmonic_analysis(mf.mol, mf.Hessian().kernel())
        renamed = {"freq_cm-1": actual["freq_wavenumber"], "normal_mode": actual["norm_mode"],
                   "freq_au": actual["freq_au"]}
        with mock.patch.object(thermo, "harmonic_analysis", return_value=renamed):
            result = self._run(mf)
        self.assertTrue(np.allclose(result.frequencies_cm1, np.real(actual["freq_wavenumber"])))
        self.assertEqual(np.asarray(result.normal_modes).shape, (3, 3, 3))
        self.assertIsNotNone(result.zpe_hartree)


if __name__ == "__main__":
    unittest.main()
