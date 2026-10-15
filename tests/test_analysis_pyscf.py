"""
tests/test_analysis_pyscf.py
----------------------------
qcapp.analysis_pyscf(軌道・電荷の情報の取り出し)の単体テスト。
PySCFは使わず、必要な属性だけを持つ代用のオブジェクトで確認する。
"""

import os
import sys
import unittest
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qcapp import analysis_pyscf  # noqa: E402


def _closed_shell(n_occ, n_mo):
    return SimpleNamespace(
        mo_occ=np.array([2.0] * n_occ + [0.0] * (n_mo - n_occ)),   # 閉殻のmo_occはnumpy配列
        mo_energy=np.arange(n_mo, dtype=float),
    )


class TestGetHomoLumoIndices(unittest.TestCase):
    def test_closed_shell(self):
        self.assertEqual(analysis_pyscf.get_homo_lumo_indices(_closed_shell(5, 12)), (4, 5))

    def test_open_shell_given_as_a_pair_uses_the_alpha_channel(self):
        mf = SimpleNamespace(mo_occ=(np.array([1.0, 1.0, 1.0, 0.0, 0.0]), np.array([1.0, 1.0, 0.0, 0.0, 0.0])))
        self.assertEqual(analysis_pyscf.get_homo_lumo_indices(mf), (2, 3))

    def test_no_occupied_orbital_falls_back_to_zero(self):
        mf = SimpleNamespace(mo_occ=np.zeros(3))
        self.assertEqual(analysis_pyscf.get_homo_lumo_indices(mf), (0, 1))


class TestHomoLumoWindow(unittest.TestCase):
    def test_labels_around_the_homo(self):
        options, homo = analysis_pyscf.homo_lumo_window(_closed_shell(5, 12), half_width=2)
        self.assertEqual(homo, 4)
        self.assertEqual(
            [label.split(" ")[0] for label, _ in options],
            ["HOMO-1", "HOMO", "LUMO", "LUMO+1"])
        self.assertEqual([i for _, i in options], [3, 4, 5, 6])
        self.assertIn("軌道4番", options[1][0])

    def test_orbitals_outside_the_available_range_are_skipped(self):
        options, homo = analysis_pyscf.homo_lumo_window(_closed_shell(1, 2), half_width=3)
        self.assertEqual(homo, 0)
        self.assertEqual([i for _, i in options], [0, 1])

    def test_mo_energy_may_be_a_plain_list(self):
        mf = _closed_shell(2, 5)
        mf.mo_energy = [0.0] * 5
        options, _ = analysis_pyscf.homo_lumo_window(mf)
        self.assertTrue(all(0 <= i < 5 for _, i in options))


class TestComputeMullikenCharges(unittest.TestCase):
    def test_pairs_each_element_with_its_charge(self):
        mol = SimpleNamespace(natm=3, atom_symbol=lambda i: ["O", "H", "H"][i])
        mf = SimpleNamespace(mulliken_pop=lambda verbose=0: (None, [-0.45, 0.225, 0.225]))
        charges = analysis_pyscf.compute_mulliken_charges(mol, mf)
        self.assertEqual([s for s, _ in charges], ["O", "H", "H"])
        self.assertAlmostEqual(charges[0][1], -0.45)
        self.assertAlmostEqual(sum(c for _, c in charges), 0.0)
        self.assertTrue(all(isinstance(c, float) for _, c in charges))


if __name__ == "__main__":
    unittest.main()
