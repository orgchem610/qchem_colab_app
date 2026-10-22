"""
tests/test_ase_bridge.py
------------------------
common_backend.ase_bridge(共通の構造 -> ASE の Atoms)の単体テスト。
ASEは、代用のモジュールに差し替えて確認する(ASEが入っていない環境でも動く)。
ASEが入っている環境では、本物の Atoms でも確認する(入っていなければ、その部分だけスキップ)。
"""

import importlib.util
import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import ase_bridge, io_reader  # noqa: E402

HAS_ASE = importlib.util.find_spec("ase") is not None


def _structure():
    return io_reader.Structure(symbols=["O", "H", "H"],
                               coords=[[0.0, 0.0, 0.1], [0.0, 0.76, -0.47], [0.0, -0.76, -0.47]])


class FakeAtoms:
    def __init__(self, symbols, positions):
        self.symbols = symbols
        self.positions = positions
        self.info = {}


class TestWithFakeAse(unittest.TestCase):
    def _convert(self, structure):
        fake = types.ModuleType("ase")
        fake.Atoms = FakeAtoms
        with mock.patch.dict(sys.modules, {"ase": fake}):
            return ase_bridge.structure_to_atoms(structure)

    def test_symbols_and_positions_are_passed_on(self):
        atoms = self._convert(_structure())
        self.assertEqual(atoms.symbols, ["O", "H", "H"])
        self.assertEqual(atoms.positions[1], [0.0, 0.76, -0.47])

    def test_the_input_structure_is_not_shared_with_the_atoms(self):
        structure = _structure()
        atoms = self._convert(structure)
        atoms.positions[0][2] = 99.0
        self.assertEqual(structure.coords[0][2], 0.1)

    def test_no_charge_or_spin_is_set_here(self):
        self.assertEqual(self._convert(_structure()).info, {})

    def test_missing_ase_raises_import_error_when_called(self):
        with mock.patch.dict(sys.modules, {"ase": None}):
            with self.assertRaises(ImportError):
                ase_bridge.structure_to_atoms(_structure())


@unittest.skipUnless(HAS_ASE, "ASEがインストールされていないためスキップ")
class TestWithRealAse(unittest.TestCase):
    def test_real_atoms(self):
        atoms = ase_bridge.structure_to_atoms(_structure())
        self.assertEqual(atoms.get_chemical_symbols(), ["O", "H", "H"])
        self.assertAlmostEqual(atoms.get_positions()[1][1], 0.76)
        self.assertEqual(len(atoms), 3)


if __name__ == "__main__":
    unittest.main()
