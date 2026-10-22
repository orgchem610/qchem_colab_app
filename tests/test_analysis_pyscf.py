"""
tests/test_analysis_pyscf.py
----------------------------
pyscf_backend.analysis_pyscf(軌道・電荷の情報の取り出し)の単体テスト。
実物のPySCFで、水・メチルラジカル・酸素(三重項)・エタノール陽イオン・ベンゼンのSCFを実際に計算して確認する
(どれも1秒未満。tests/real_molecules.py)。

軌道エネルギーの値を指定したいテスト(縮退のしきい値・eVへの換算など)は、実物のSCFの結果を複製して、
軌道エネルギーだけを書き換える。実際には起こらない軌道の数の確認は、計算していない実物のRHFに、仮の軌道の
占有数・エネルギーを入れる。元素記号の表記ゆれ(PySCFが正規化するため、実物では起こらない)は、
実物のMoleの atom_symbol・atom_pure_symbol だけを差し替える。
PySCFが入っていない環境では、このファイルのテストをすべてスキップする。
"""

import os
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import real_molecules as rm  # noqa: E402
from qchem_colab_app.common_backend import energy  # noqa: E402
from qchem_colab_app.pyscf_backend import analysis_pyscf  # noqa: E402

SKIP_NO_PYSCF = "PySCFがインストールされていないためスキップ"


def _name(label):
    """表示名から、末尾のエネルギー(eV)の部分を除いたもの。"""
    return label.split("  ")[0]


def _names(choices):
    """軌道番号 → 表示名(エネルギーの部分を除く)。"""
    return {i: _name(label) for label, i in choices.options}


def _labels(choices):
    return [label for label, _ in choices.options]


@unittest.skipUnless(rm.HAS_PYSCF, SKIP_NO_PYSCF)
class TestValenceSpaceSize(unittest.TestCase):
    def test_hydrogen_and_second_period_atoms(self):
        self.assertEqual(analysis_pyscf.valence_space_size(rm.build_mole("H 0 0 0; H 0 0 0.74")), (0, 2))
        self.assertEqual(analysis_pyscf.valence_space_size(rm.water_rhf().mol), (1, 6))

    def test_third_period_atoms_have_five_core_orbitals(self):
        self.assertEqual(analysis_pyscf.valence_space_size(rm.atom_mole("S")), (5, 4))

    def test_fourth_and_fifth_period_main_group_atoms(self):
        self.assertEqual(analysis_pyscf.valence_space_size(rm.atom_mole("Br")), (14, 4))
        self.assertEqual(analysis_pyscf.valence_space_size(rm.atom_mole("I")), (23, 4))

    def test_element_symbols_are_normalized_and_unknown_ones_fall_back(self):
        # PySCFは元素記号を正規化するため、小文字や未知の記号は実物のMoleでは現れない。
        # 実物のMole(Cl原子)の、元素記号を返す関数だけを差し替える
        mol = rm.atom_mole("Cl")
        with mock.patch.object(mol, "atom_pure_symbol", lambda i: "cl"):
            self.assertEqual(analysis_pyscf.valence_space_size(mol), (5, 4))
        with mock.patch.object(mol, "atom_pure_symbol", lambda i: "Xx"):
            self.assertEqual(analysis_pyscf.valence_space_size(mol), (0, 4))

    def test_pure_symbol_is_preferred_when_available(self):
        # 原子に付けたラベル(C1)は、atom_symbolでは「C1」、atom_pure_symbolでは「C」になる
        mol = rm.build_mole("C1 0 0 0", basis="sto-3g")
        self.assertEqual(mol.atom_symbol(0), "C1")
        self.assertEqual(analysis_pyscf.valence_space_size(mol), (1, 4))


@unittest.skipUnless(rm.HAS_PYSCF, SKIP_NO_PYSCF)
class TestOrbitalChoicesClosedShell(unittest.TestCase):
    def setUp(self):
        # 水 RHF/6-31G: 軌道13個、電子が入った軌道5個。内殻1+価電子殻6=7番目の軌道(軌道6番)まで表示する
        self.mf = rm.water_rhf()
        self.choices = analysis_pyscf.orbital_choices(self.mf.mol, self.mf)

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
        # ベンゼン(D6h)のHOMO(e1g)・LUMO(e2u)は、どちらも2重に縮退している
        mf = rm.benzene_rhf()
        choices = analysis_pyscf.orbital_choices(mf.mol, mf)
        names = _names(choices)
        self.assertEqual(names[18], "軌道18番")
        self.assertEqual((names[19], names[20]), ("軌道19番(HOMO)", "軌道20番(HOMO)"))
        self.assertEqual((names[21], names[22]), ("軌道21番(LUMO)", "軌道22番(LUMO)"))
        self.assertEqual(choices.default_index, 20)
        self.assertEqual(sum("(HOMO)" in s for s in _labels(choices)), 2)
        self.assertEqual(sum("(LUMO)" in s for s in _labels(choices)), 2)

    def test_slightly_different_energies_are_not_degenerate(self):
        energies = [-20.5, -1.3, -0.7, -0.5, -0.4, 0.2, 0.3, 0.9, 1.1, 1.3, 1.4, 1.5, 1.6]
        mf = rm.modified_copy(self.mf, mo_energy=np.array(energies))
        labels = _labels(analysis_pyscf.orbital_choices(mf.mol, mf))
        self.assertEqual(sum("(HOMO)" in s for s in labels), 1)
        self.assertEqual(sum("(LUMO)" in s for s in labels), 1)

    def test_list_stops_at_the_number_of_available_orbitals(self):
        mf = rm.hypothetical_rhf(self.mf.mol, n_occupied=5, n_mo=6)
        choices = analysis_pyscf.orbital_choices(mf.mol, mf)
        self.assertEqual(sorted(i for _, i in choices.options), [0, 1, 2, 3, 4, 5])

    def test_all_occupied_orbitals_are_listed_even_beyond_the_valence_count(self):
        # 価電子殻の軌道数(H2: 内殻0+価電子殻2=2)より、電子が入っている軌道が多い場合
        mf = rm.hypothetical_rhf(rm.build_mole("H 0 0 0; H 0 0 0.74"), n_occupied=3, n_mo=6)
        choices = analysis_pyscf.orbital_choices(mf.mol, mf)
        self.assertEqual(sorted(i for _, i in choices.options), [0, 1, 2, 3])
        self.assertEqual(choices.default_index, 2)

    def test_mo_energy_may_be_a_plain_list(self):
        mf = rm.modified_copy(self.mf, mo_energy=[float(e) for e in self.mf.mo_energy])
        self.assertEqual(analysis_pyscf.orbital_choices(mf.mol, mf).default_index, 4)


@unittest.skipUnless(rm.HAS_PYSCF, SKIP_NO_PYSCF)
class TestOrbitalEnergyDisplay(unittest.TestCase):
    ENERGIES = [-20.5, -1.3, -0.7, -0.5, -0.4, 0.2, 0.5, 0.9, 1.1, 1.3, 1.4, 1.5, 1.6]

    def setUp(self):
        mf = rm.modified_copy(rm.water_rhf(), mo_energy=np.array(self.ENERGIES))
        self.choices = analysis_pyscf.orbital_choices(mf.mol, mf)

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

    def test_real_orbital_energies_are_converted_too(self):
        mf = rm.water_rhf()
        choices = analysis_pyscf.orbital_choices(mf.mol, mf)
        homo = next(label for label, i in choices.options if i == 4)
        self.assertTrue(homo.endswith(f"  {mf.mo_energy[4] * energy.HARTREE_TO_EV:+.2f} eV"))

    def test_open_shell_shows_the_alpha_orbital_energy(self):
        base = rm.methyl_uhf()
        energy_alpha = np.arange(base.mo_energy.shape[1], dtype=float) * 0.1
        mf = rm.modified_copy(base, mo_energy=np.array([energy_alpha, energy_alpha + 5.0]))   # βは大きくずらしてある
        choices = analysis_pyscf.orbital_choices(mf.mol, mf)
        label = next(label for label, i in choices.options if i == 2)
        self.assertTrue(label.endswith("  +5.44 eV"))                    # 0.2 Hartree


@unittest.skipUnless(rm.HAS_PYSCF, SKIP_NO_PYSCF)
class TestOrbitalChoicesOpenShell(unittest.TestCase):
    def test_doublet_like_the_ethanol_cation(self):
        # エタノール陽イオン UHF/6-31G: α電子13個・β電子12個。軌道12番だけに電子が1個
        mf = rm.ethanol_cation_uhf()
        self.assertEqual(mf.mo_occ.shape, (2, 39))
        choices = analysis_pyscf.orbital_choices(mf.mol, mf)
        self.assertTrue(choices.open_shell)
        self.assertEqual(choices.default_index, 12)
        labels = _labels(choices)
        self.assertEqual([_name(s) for s in labels if "SOMO" in s], ["軌道12番(SOMO)"])
        self.assertTrue(all("HOMO" not in s and "LUMO" not in s for s in labels))
        # 内殻3+価電子殻(4×3+1×6=18)=21番目(軌道20番)まで。エネルギーの低い軌道が最後
        self.assertEqual([i for _, i in choices.options], list(range(20, -1, -1)))

    def test_triplet_marks_both_singly_occupied_orbitals(self):
        mf = rm.oxygen_triplet_uhf()                                       # α電子9個・β電子7個
        choices = analysis_pyscf.orbital_choices(mf.mol, mf)
        somo = [i for label, i in choices.options if "SOMO" in label]
        self.assertEqual(sorted(somo), [7, 8])
        self.assertEqual(choices.default_index, 8)

    def test_pair_of_arrays_is_also_accepted(self):
        base = rm.methyl_uhf()
        mf = rm.modified_copy(base, mo_occ=(base.mo_occ[0], base.mo_occ[1]),
                              mo_energy=(base.mo_energy[0], base.mo_energy[1]))
        choices = analysis_pyscf.orbital_choices(mf.mol, mf)
        self.assertTrue(choices.open_shell)
        self.assertEqual(choices.default_index, 4)                          # α電子5個

    def test_restricted_open_shell_uses_occupation_one(self):
        # ROHF: 1次元の配列で、電子が1個の軌道の占有数が1
        mf = rm.methyl_rohf()
        self.assertEqual(mf.mo_occ.ndim, 1)
        choices = analysis_pyscf.orbital_choices(mf.mol, mf)
        self.assertTrue(choices.open_shell)
        self.assertEqual(choices.default_index, 4)
        self.assertIn("軌道4番(SOMO)", list(_names(choices).values()))


@unittest.skipUnless(rm.HAS_PYSCF, SKIP_NO_PYSCF)
class TestComputeMullikenCharges(unittest.TestCase):
    def test_pairs_each_element_with_its_charge(self):
        mf = rm.water_rhf()
        charges = analysis_pyscf.compute_mulliken_charges(mf.mol, mf)
        self.assertEqual([s for s, _ in charges], ["O", "H", "H"])
        self.assertLess(charges[0][1], 0.0)                                  # 酸素は負、水素は正
        self.assertGreater(charges[1][1], 0.0)
        self.assertAlmostEqual(charges[1][1], charges[2][1], places=6)       # 2つの水素は等価
        self.assertAlmostEqual(sum(c for _, c in charges), 0.0, places=6)    # 中性分子の電荷の和は0
        self.assertTrue(all(isinstance(c, float) for _, c in charges))

    def test_charges_agree_with_pyscf_called_directly(self):
        mf = rm.water_rhf()
        expected = mf.mulliken_pop(verbose=0)[1]
        charges = analysis_pyscf.compute_mulliken_charges(mf.mol, mf)
        self.assertTrue(np.allclose([c for _, c in charges], expected))

    def test_open_shell_charges_sum_to_the_total_charge(self):
        mf = rm.ethanol_cation_uhf()
        charges = analysis_pyscf.compute_mulliken_charges(mf.mol, mf)
        self.assertEqual(len(charges), 9)
        self.assertAlmostEqual(sum(c for _, c in charges), 1.0, places=6)    # 陽イオン


if __name__ == "__main__":
    unittest.main()
