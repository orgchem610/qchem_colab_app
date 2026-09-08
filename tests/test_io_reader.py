"""
tests/test_io_reader.py
------------------------
qcapp.io_reader の単体テスト。

このテストファイルは pyscf / ase をインポートしないため、
PySCFがインストールされていない環境(このリポジトリの開発サンドボックス等)
でも実行できる。実際にColab上でPySCFを使う部分(engine.py / optimize.py /
freq.py)のテストは、Colab上で手動確認する必要がある(README.md参照)。

実行方法:
    python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qcapp import io_reader  # noqa: E402


def _write_tmp_xyz(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".xyz")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class TestReadXyz(unittest.TestCase):
    def test_valid_water(self):
        xyz = (
            "3\n"
            "water molecule\n"
            "O   0.000000   0.000000   0.000000\n"
            "H   0.000000   0.000000   0.960000\n"
            "H   0.930000   0.000000  -0.240000\n"
        )
        path = _write_tmp_xyz(xyz)
        structure = io_reader.read_xyz(path)
        self.assertEqual(structure.symbols, ["O", "H", "H"])
        self.assertEqual(len(structure.coords), 3)
        self.assertAlmostEqual(structure.coords[1][2], 0.96)

    def test_lowercase_and_mixed_case_symbol_is_normalized(self):
        xyz = "1\ncomment\nhe 0.0 0.0 0.0\n"
        path = _write_tmp_xyz(xyz)
        structure = io_reader.read_xyz(path)
        self.assertEqual(structure.symbols, ["He"])

    def test_unknown_element_raises(self):
        xyz = "1\ncomment\nXx 0.0 0.0 0.0\n"
        path = _write_tmp_xyz(xyz)
        with self.assertRaises(io_reader.StructureError):
            io_reader.read_xyz(path)

    def test_truncated_file_raises(self):
        xyz = "3\ncomment\nO 0.0 0.0 0.0\n"  # 原子数3のはずが1行しかない
        path = _write_tmp_xyz(xyz)
        with self.assertRaises(io_reader.StructureError):
            io_reader.read_xyz(path)

    def test_non_numeric_atom_count_raises(self):
        xyz = "abc\ncomment\nO 0.0 0.0 0.0\n"
        path = _write_tmp_xyz(xyz)
        with self.assertRaises(io_reader.StructureError):
            io_reader.read_xyz(path)


class TestValidateStructure(unittest.TestCase):
    def test_empty_structure_raises(self):
        structure = io_reader.Structure(symbols=[], coords=[])
        with self.assertRaises(io_reader.StructureError):
            io_reader.validate_structure(structure)

    def test_overlapping_atoms_raise(self):
        structure = io_reader.Structure(
            symbols=["C", "C"], coords=[[0.0, 0.0, 0.0], [0.01, 0.0, 0.0]])
        with self.assertRaises(io_reader.StructureError):
            io_reader.validate_structure(structure, min_distance=0.4)

    def test_normal_bond_length_passes(self):
        # C-H結合(約1.09Å)は問題なく通ること
        structure = io_reader.Structure(
            symbols=["C", "H"], coords=[[0.0, 0.0, 0.0], [1.09, 0.0, 0.0]])
        io_reader.validate_structure(structure, min_distance=0.4)  # 例外が出なければOK


class TestChargeAndMultiplicity(unittest.TestCase):
    def test_water_singlet_is_valid(self):
        # H2O, 電荷0, 多重度1(全電子数10, 偶数) -> 妥当
        structure = io_reader.Structure(symbols=["O", "H", "H"], coords=[[0, 0, 0]] * 3)
        io_reader.validate_charge_and_multiplicity(structure, charge=0, multiplicity=1)

    def test_multiplicity_below_one_raises(self):
        structure = io_reader.Structure(symbols=["O", "H", "H"], coords=[[0, 0, 0]] * 3)
        with self.assertRaises(io_reader.StructureError):
            io_reader.validate_charge_and_multiplicity(structure, charge=0, multiplicity=0)

    def test_parity_mismatch_raises(self):
        # 全電子数10(偶数)なのに多重度2(不対電子1個=奇数)を指定 -> 化学的に矛盾
        structure = io_reader.Structure(symbols=["O", "H", "H"], coords=[[0, 0, 0]] * 3)
        with self.assertRaises(io_reader.StructureError):
            io_reader.validate_charge_and_multiplicity(structure, charge=0, multiplicity=2)

    def test_radical_doublet_is_valid(self):
        # OHラジカル相当: 全電子数9(奇数) + 多重度2(不対電子1個) -> 妥当
        structure = io_reader.Structure(symbols=["O", "H"], coords=[[0, 0, 0]] * 2)
        io_reader.validate_charge_and_multiplicity(structure, charge=0, multiplicity=2)

    def test_excessive_positive_charge_raises(self):
        # H原子(電子1個)から電荷+2を引くと電子数が負になる
        structure = io_reader.Structure(symbols=["H"], coords=[[0, 0, 0]])
        with self.assertRaises(io_reader.StructureError):
            io_reader.validate_charge_and_multiplicity(structure, charge=2, multiplicity=1)


class TestTransitionMetalDetection(unittest.TestCase):
    def test_organic_molecule_is_false(self):
        structure = io_reader.Structure(symbols=["C", "H", "H", "H", "O"], coords=[[0, 0, 0]] * 5)
        self.assertFalse(io_reader.contains_transition_metal(structure))

    def test_iron_complex_is_true(self):
        structure = io_reader.Structure(symbols=["Fe", "C", "O"], coords=[[0, 0, 0]] * 3)
        self.assertTrue(io_reader.contains_transition_metal(structure))


if __name__ == "__main__":
    unittest.main()
