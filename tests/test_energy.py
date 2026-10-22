"""
tests/test_energy.py
--------------------
qchem_colab_app/common_backend/energy.py(エネルギーの単位換算・相対エネルギー)の単体テスト。
外部ライブラリには依存しない。
(v0.2.2で、旧 tests/test_energy_plot.py から分けた。SVGグラフと目盛りは、test_energy_plot.py にある。)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import energy  # noqa: E402


class TestRelativeEnergies(unittest.TestCase):
    def test_reference_is_the_last_point_in_kcal_per_mol(self):
        values = energy.relative_energies_kcal([-10.0, -10.01])
        self.assertAlmostEqual(values[0], 6.275094740631222)
        self.assertAlmostEqual(values[1], 0.0)

    def test_empty_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            energy.relative_energies_kcal([])

    def test_nan_raises_value_error(self):
        with self.assertRaises(ValueError):
            energy.relative_energies_kcal([-10.0, float("nan")])


class TestConstant(unittest.TestCase):
    def test_unit_conversion_constant(self):
        self.assertAlmostEqual(energy.HARTREE_TO_KCAL_MOL, 627.5094740631)

    def test_hartree_to_ev(self):
        self.assertAlmostEqual(energy.HARTREE_TO_EV, 27.211386245988, places=9)


if __name__ == "__main__":
    unittest.main()
