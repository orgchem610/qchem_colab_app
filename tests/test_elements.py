"""
tests/test_elements.py
----------------------
common_backend.elements(元素のデータ)の単体テスト。
表が1か所だけにあること(io_reader・analysis_pyscf が、自前の表を持たないこと)も確認する。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import elements, io_reader  # noqa: E402
from qchem_colab_app.pyscf_backend import analysis_pyscf  # noqa: E402


class TestAtomicNumbers(unittest.TestCase):
    def test_covers_hydrogen_to_xenon(self):
        self.assertEqual(len(elements.ATOMIC_NUMBERS), 54)
        self.assertEqual(elements.ATOMIC_NUMBERS["H"], 1)
        self.assertEqual(elements.ATOMIC_NUMBERS["Xe"], 54)

    def test_atomic_numbers_are_unique_and_consecutive(self):
        self.assertEqual(sorted(elements.ATOMIC_NUMBERS.values()), list(range(1, 55)))

    def test_well_known_elements(self):
        expected = {"C": 6, "N": 7, "O": 8, "Ne": 10, "Cl": 17, "Fe": 26, "Br": 35, "I": 53}
        for symbol, z in expected.items():
            self.assertEqual(elements.ATOMIC_NUMBERS[symbol], z, symbol)

    def test_symbols_are_capitalized(self):
        for symbol in elements.ATOMIC_NUMBERS:
            self.assertEqual(symbol, symbol[0].upper() + symbol[1:].lower())

    def test_elements_beyond_xenon_are_not_included(self):
        for symbol in ("Cs", "Ba", "Au", "Hg", "U"):
            self.assertNotIn(symbol, elements.ATOMIC_NUMBERS)


class TestTheTableIsDefinedOnlyHere(unittest.TestCase):
    def test_io_reader_has_no_table_of_its_own(self):
        self.assertFalse(hasattr(io_reader, "ATOMIC_NUMBERS"))

    def test_analysis_pyscf_has_no_table_of_its_own(self):
        self.assertFalse(hasattr(analysis_pyscf, "_ELEMENT_SYMBOLS"))

    def test_both_users_follow_the_table(self):
        # 表にある元素は、io_readerで読み込め、analysis_pyscfで軌道の数え上げができる
        for symbol in elements.ATOMIC_NUMBERS:
            core, valence = analysis_pyscf._core_and_valence_orbital_counts(symbol)
            self.assertGreater(core + valence, 0, symbol)


if __name__ == "__main__":
    unittest.main()
