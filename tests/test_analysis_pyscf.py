"""
tests/test_analysis_pyscf.py
----------------------------
pyscf_backend.analysis_pyscf(軌道・電荷の情報の取り出し)の単体テスト。
PySCFは使わず、必要な属性だけを持つ代用のオブジェクトで確認する。
"""

import os
import sys
import unittest
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import energy  # noqa: E402
from qchem_colab_app.pyscf_backend import analysis_pyscf  # noqa: E402


def _mol(symbols):
    return SimpleNamespace(natm=len(symbols), atom_symbol=lambda i: symbols[i])


def _closed_shell(n_occ, n_mo, energies=None):
    """閉殻(RHF/RKS): mo_occ・mo_energy は1次元のnumpy配列。"""
    return SimpleNamespace(
        mo_occ=np.array([2.0] * n_occ + [0.0] * (n_mo - n_occ)),
        mo_energy=np.arange(n_mo, dtype=float) if energies is None else np.array(energies, dtype=float),
    )


def _open_shell(n_alpha, n_beta, n_mo):
    """開殻(UHF/UKS): mo_occ・mo_energy は、α・βの2行のnumpy配列。"""
    occ_a = [1.0] * n_alpha + [0.0] * (n_mo - n_alpha)
    occ_b = [1.0] * n_beta + [0.0] * (n_mo - n_beta)
    energy = np.arange(n_mo, dtype=float)
    return SimpleNamespace(mo_occ=np.array([occ_a, occ_b]), mo_energy=np.array([energy, energy]))


def _name(label):
    """表示名から、末尾のエネルギー(eV)の部分を除いたもの。"""
    return label.split("  ")[0]


def _names(choices):
    """軌道番号 → 表示名(エネルギーの部分を除く)。"""
    return {i: _name(label) for label, i in choices.options}


def _labels(choices):
    return [label for label, _ in choices.options]


class TestValenceSpaceSize(unittest.TestCase):
    def test_hydrogen_and_second_period_atoms(self):
        self.assertEqual(analysis_pyscf.valence_space_size(_mol(["H", "H"])), (0, 2))
        self.assertEqual(analysis_pyscf.valence_space_size(_mol(["O", "H", "H"])), (1, 6))

    def test_third_period_atoms_have_five_core_orbitals(self):
        self.assertEqual(analysis_pyscf.valence_space_size(_mol(["S"])), (5, 4))

    def test_fourth_and_fifth_period_main_group_atoms(self):
        self.assertEqual(analysis_pyscf.valence_space_size(_mol(["Br"])), (14, 4))
        self.assertEqual(analysis_pyscf.valence_space_size(_mol(["I"])), (23, 4))

    def test_element_symbols_are_normalized_and_unknown_ones_fall_back(self):
        self.assertEqual(analysis_pyscf.valence_space_size(_mol(["cl"])), (5, 4))
        self.assertEqual(analysis_pyscf.valence_space_size(_mol(["Xx"])), (0, 4))

    def test_pure_symbol_is_preferred_when_available(self):
        mol = SimpleNamespace(natm=1, atom_symbol=lambda i: "C1", atom_pure_symbol=lambda i: "C")
        self.assertEqual(analysis_pyscf.valence_space_size(mol), (1, 4))


class TestOrbitalChoicesClosedShell(unittest.TestCase):
    def setUp(self):
        # 水: 占有軌道5個。内殻1+価電子殻6=7番目の軌道(軌道6番)まで表示する
        self.choices = analysis_pyscf.orbital_choices(_mol(["O", "H", "H"]), _closed_shell(5, 13))

    def test_all_occupied_and_valence_virtual_orbitals_are_listed(self):
        self.assertEqual(sorted(i for _, i in self.choices.options), [0, 1, 2, 3, 4, 5, 6])

    def test_lowest_energy_orbital_comes_last_in_the_list(self):
        self.assertEqual([i for _, i in self.choices.options], [6, 5, 4, 3, 2, 1, 0])

    def test_labels_mark_only_homo_and_lumo(self):
        self.assertEqual(_names(self.choices), {
            0: "軌道0番", 1: "軌道1番", 2: "軌道2番", 3: "軌道3番",
            4: "軌道4番(HOMO)", 5: "軌道5番(LUMO)", 6: "軌道6番"})

    def test_default_is_the_highest_occupied_orbital(self):
        self.assertEqual(self.choices.default_index, 4)
        self.assertFalse(self.choices.open_shell)
        self.assertIn(4, [i for _, i in self.choices.options])

    def test_no_homo_minus_one_style_labels(self):
        for label in _labels(self.choices):
            self.assertNotIn("HOMO-", label)
            self.assertNotIn("LUMO+", label)

    def test_degenerate_homo_and_lumo_are_all_marked(self):
        energies = [-1.0, -0.5, -0.5, 0.2, 0.2, 0.9, 1.0, 1.1]
        choices = analysis_pyscf.orbital_choices(_mol(["N", "H", "H", "H"]), _closed_shell(3, 8, energies))
        names = _names(choices)
        self.assertEqual(names[0], "軌道0番")
        self.assertEqual((names[1], names[2]), ("軌道1番(HOMO)", "軌道2番(HOMO)"))
        self.assertEqual((names[3], names[4]), ("軌道3番(LUMO)", "軌道4番(LUMO)"))
        self.assertEqual(choices.default_index, 2)

    def test_slightly_different_energies_are_not_degenerate(self):
        energies = [-1.0, -0.5, -0.4, 0.2, 0.3, 0.9, 1.0, 1.1]
        labels = _labels(analysis_pyscf.orbital_choices(
            _mol(["N", "H", "H", "H"]), _closed_shell(3, 8, energies)))
        self.assertEqual(sum("(HOMO)" in s for s in labels), 1)
        self.assertEqual(sum("(LUMO)" in s for s in labels), 1)

    def test_list_stops_at_the_number_of_available_orbitals(self):
        choices = analysis_pyscf.orbital_choices(_mol(["O", "H", "H"]), _closed_shell(5, 6))
        self.assertEqual(sorted(i for _, i in choices.options), [0, 1, 2, 3, 4, 5])

    def test_all_occupied_orbitals_are_listed_even_beyond_the_valence_count(self):
        # 価電子殻の軌道数(内殻0+価電子殻1=1)より、電子が入っている軌道が多い場合
        choices = analysis_pyscf.orbital_choices(_mol(["H"]), _closed_shell(3, 6))
        self.assertEqual(sorted(i for _, i in choices.options), [0, 1, 2, 3])
        self.assertEqual(choices.default_index, 2)

    def test_mo_energy_may_be_a_plain_list(self):
        mf = _closed_shell(2, 8)
        mf.mo_energy = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        self.assertEqual(analysis_pyscf.orbital_choices(_mol(["H", "H"]), mf).default_index, 1)


class TestOrbitalEnergyDisplay(unittest.TestCase):
    ENERGIES = [-20.5, -1.3, -0.7, -0.5, -0.4, 0.2, 0.5, 0.9, 1.1, 1.3, 1.4, 1.5, 1.6]

    def setUp(self):
        self.choices = analysis_pyscf.orbital_choices(
            _mol(["O", "H", "H"]), _closed_shell(5, 13, self.ENERGIES))

    def _label_of(self, index):
        return next(label for label, i in self.choices.options if i == index)

    def test_energy_in_ev_is_appended_to_each_label(self):
        self.assertTrue(self._label_of(4).endswith("  -10.88 eV"))      # -0.4 Hartree
        self.assertTrue(self._label_of(5).endswith("  +5.44 eV"))       # +0.2 Hartree

    def test_conversion_uses_the_standard_hartree_to_ev_factor(self):
        self.assertAlmostEqual(energy.HARTREE_TO_EV, 27.211386245988)
        self.assertFalse(hasattr(analysis_pyscf, "HARTREE_TO_EV"))     # 換算係数は、common_backend.energyの1か所だけ
        self.assertTrue(self._label_of(0).endswith("  -557.83 eV"))     # -20.5 Hartree

    def test_energies_decrease_down_the_list(self):
        values = [float(label.split("  ")[-1].replace(" eV", "")) for label, _ in self.choices.options]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_open_shell_shows_the_alpha_orbital_energy(self):
        mf = _open_shell(3, 2, 10)
        energy_alpha = np.arange(10, dtype=float) * 0.1
        mf.mo_energy = np.array([energy_alpha, energy_alpha + 5.0])      # βは大きくずらしてある
        choices = analysis_pyscf.orbital_choices(_mol(["C", "H", "H", "H"]), mf)
        label = next(label for label, i in choices.options if i == 2)
        self.assertTrue(label.endswith("  +5.44 eV"))                    # 0.2 Hartree


class TestOrbitalChoicesOpenShell(unittest.TestCase):
    def test_doublet_like_the_ethanol_cation(self):
        # エタノール陽イオン: α電子13個・β電子12個。軌道12番だけに電子が1個
        mol = _mol(["C", "C", "O"] + ["H"] * 6)
        choices = analysis_pyscf.orbital_choices(mol, _open_shell(13, 12, 39))
        self.assertTrue(choices.open_shell)
        self.assertEqual(choices.default_index, 12)
        labels = _labels(choices)
        self.assertEqual([_name(s) for s in labels if "SOMO" in s], ["軌道12番(SOMO)"])
        self.assertTrue(all("HOMO" not in s and "LUMO" not in s for s in labels))
        # 内殻3+価電子殻(4×3+1×6=18)=21番目(軌道20番)まで。エネルギーの低い軌道が最後
        self.assertEqual([i for _, i in choices.options], list(range(20, -1, -1)))

    def test_triplet_marks_both_singly_occupied_orbitals(self):
        choices = analysis_pyscf.orbital_choices(_mol(["O", "O"]), _open_shell(9, 7, 20))
        somo = [i for label, i in choices.options if "SOMO" in label]
        self.assertEqual(sorted(somo), [7, 8])
        self.assertEqual(choices.default_index, 8)

    def test_pair_of_arrays_is_also_accepted(self):
        mf = _open_shell(3, 2, 10)
        mf.mo_occ = (mf.mo_occ[0], mf.mo_occ[1])
        mf.mo_energy = (mf.mo_energy[0], mf.mo_energy[1])
        choices = analysis_pyscf.orbital_choices(_mol(["C", "H", "H", "H"]), mf)
        self.assertTrue(choices.open_shell)
        self.assertEqual(choices.default_index, 2)

    def test_restricted_open_shell_uses_occupation_one(self):
        # ROHF: 1次元の配列で、電子が1個の軌道の占有数が1
        mf = SimpleNamespace(mo_occ=np.array([2.0, 2.0, 1.0, 0.0, 0.0, 0.0]),
                             mo_energy=np.arange(6, dtype=float))
        choices = analysis_pyscf.orbital_choices(_mol(["C", "H", "H", "H"]), mf)
        self.assertTrue(choices.open_shell)
        self.assertEqual(choices.default_index, 2)
        self.assertIn("軌道2番(SOMO)", list(_names(choices).values()))


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
