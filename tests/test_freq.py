"""
tests/test_freq.py
------------------
pyscf_backend.freq(PySCF版の振動数解析)の単体テスト。
PySCFは使わず、pyscf.hessian.thermo を代用のモジュールに差し替えて、
結果の組み立て(振動数・虚振動の数え方・熱力学量・失敗時の扱い・注意文)を確認する。
PySCFによる実際のHessian計算は、Colab上での実機確認が必要。
"""

import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import vibration  # noqa: E402
from qchem_colab_app.pyscf_backend import freq  # noqa: E402

DEFAULTS = {"frequency": {"temperature_K": 298.15, "pressure_Pa": 101325}}


def _fake_pyscf(freq_info, thermo_result=None, thermo_error=None):
    """pyscf.hessian.thermo の代用品を入れたモジュールの辞書を作る。"""
    def harmonic_analysis(mol, hess):
        return freq_info

    def thermo_fn(mf, freq_au, temperature, pressure):
        if thermo_error is not None:
            raise thermo_error
        return thermo_result

    thermo = types.ModuleType("pyscf.hessian.thermo")
    thermo.harmonic_analysis = harmonic_analysis
    thermo.thermo = thermo_fn
    hessian = types.ModuleType("pyscf.hessian")
    hessian.thermo = thermo
    package = types.ModuleType("pyscf")
    package.hessian = hessian
    return {"pyscf": package, "pyscf.hessian": hessian, "pyscf.hessian.thermo": thermo}


def _mf():
    return SimpleNamespace(mol=object(), Hessian=lambda: SimpleNamespace(kernel=lambda: np.zeros((1, 1, 3, 3))))


def _info(freqs):
    return {"freq_wavenumber": np.array(freqs), "norm_mode": np.zeros((len(freqs), 2, 3)),
            "freq_au": np.array(freqs) * 4.5e-6}


GOOD_THERMO = {"ZPE": (0.0213, "Eh"), "G_tot": (-76.35, "Eh")}


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


class TestRunFrequencyAnalysis(unittest.TestCase):
    def _run(self, freqs, **kwargs):
        with mock.patch.dict(sys.modules, _fake_pyscf(_info(freqs), **kwargs)):
            return freq.run_frequency_analysis(_mf(), DEFAULTS)

    def test_frequencies_and_modes_are_taken_from_pyscf(self):
        result = self._run([1000.0, 1600.0, 3700.0], thermo_result=GOOD_THERMO)
        self.assertEqual(result.frequencies_cm1, [1000.0, 1600.0, 3700.0])
        self.assertEqual(result.normal_modes.shape, (3, 2, 3))
        self.assertEqual(result.n_imaginary, 0)
        self.assertEqual(result.warning_message, "")
        self.assertGreaterEqual(result.elapsed_seconds, 0.0)

    def test_thermochemistry_is_stored_in_the_result(self):
        result = self._run([1000.0], thermo_result=GOOD_THERMO)
        self.assertAlmostEqual(result.zpe_hartree, 0.0213)
        self.assertAlmostEqual(result.gibbs_hartree, -76.35)
        self.assertEqual(result.temperature_K, 298.15)

    def test_the_result_is_the_pyscf_subclass(self):
        self.assertIsInstance(self._run([1000.0], thermo_result=GOOD_THERMO), freq.FrequencyResult)

    def test_negative_frequencies_are_counted_as_imaginary_with_a_warning(self):
        result = self._run([-120.0, 800.0], thermo_result=GOOD_THERMO)
        self.assertEqual(result.n_imaginary, 1)
        self.assertIn("虚振動が1個検出されました", result.warning_message)

    def test_failure_of_the_thermochemistry_keeps_the_frequencies(self):
        result = self._run([1000.0], thermo_error=RuntimeError("boom"))
        self.assertEqual(result.frequencies_cm1, [1000.0])
        self.assertIsNone(result.zpe_hartree)
        self.assertIsNone(result.gibbs_hartree)
        self.assertIsNone(result.temperature_K)
        self.assertIn("熱力学量(ZPE・自由エネルギー)の計算に失敗しました", result.warning_message)
        self.assertIn("boom", result.warning_message)

    def test_missing_free_energy_is_treated_as_a_thermochemistry_failure_without_partial_values(self):
        result = self._run([1000.0], thermo_result={"ZPE": (0.02, "Eh")})
        self.assertIsNone(result.zpe_hartree)
        self.assertIn("計算に失敗しました", result.warning_message)

    def test_alternative_key_names_of_other_pyscf_versions_are_accepted(self):
        info = {"freq_cm-1": [900.0], "normal_mode": np.zeros((1, 2, 3)), "freq_au": np.array([4e-6])}
        with mock.patch.dict(sys.modules, _fake_pyscf(info, thermo_result=GOOD_THERMO)):
            result = freq.run_frequency_analysis(_mf(), DEFAULTS)
        self.assertEqual(result.frequencies_cm1, [900.0])
        self.assertEqual(result.normal_modes.shape, (1, 2, 3))


if __name__ == "__main__":
    unittest.main()
