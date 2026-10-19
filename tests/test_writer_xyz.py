"""
tests/test_writer_xyz.py
------------------------
common_backend.writer_xyz(xyz形式の出力)の単体テスト。外部ライブラリには依存しない。
"""

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import writer_xyz  # noqa: E402

SYMBOLS = ["O", "H", "H"]
COORDS = [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]]


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


class TestXyzStrings(unittest.TestCase):
    def test_single_frame_has_count_comment_and_one_line_per_atom(self):
        lines = writer_xyz.xyz_string(SYMBOLS, COORDS, "water").splitlines()
        self.assertEqual(lines[0], "3")
        self.assertEqual(lines[1], "water")
        self.assertEqual(len(lines), 5)
        self.assertTrue(lines[2].startswith("O "))

    def test_multiframe_uses_default_or_given_comments(self):
        text = writer_xyz.multiframe_xyz_string(SYMBOLS, [COORDS, COORDS], comments=["a"])
        lines = text.splitlines()
        self.assertEqual(lines[1], "a")
        self.assertEqual(lines[6], "frame 1")


class TestWriteFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_final_structure_is_a_standard_single_frame_xyz(self):
        path = os.path.join(self.tmp, "a.xyz")
        writer_xyz.write_final_structure(SYMBOLS, COORDS, path, comment="Optimized")
        lines = _read(path)
        self.assertEqual((lines[0], lines[1]), ("3", "Optimized"))
        self.assertEqual(len(lines), 5)

    def test_trajectory_has_one_frame_per_step_with_energy_comments(self):
        path = os.path.join(self.tmp, "t.xyz")
        writer_xyz.write_trajectory(SYMBOLS, [COORDS, COORDS], path, energies=[-76.0])
        lines = _read(path)
        self.assertEqual(len(lines), 10)
        self.assertIn("E = -76.00000000 Hartree", lines[1])
        self.assertEqual(lines[6], "step 1")


class TestWriteOptimizationOutputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.result = SimpleNamespace(
            symbols=SYMBOLS, coords_history=[COORDS, COORDS, COORDS], energies=[-75.9, -76.0, -76.1])

    def test_both_files_are_written_with_the_standard_names(self):
        final_path, traj_path = writer_xyz.write_optimization_outputs(
            self.tmp, SYMBOLS, COORDS, "from test", self.result)
        self.assertEqual(os.path.basename(final_path), "final_structure_for_ColabReaction.xyz")
        self.assertEqual(os.path.basename(traj_path), "optimization_trajectory.xyz")
        self.assertEqual(os.path.dirname(final_path), self.tmp)
        self.assertEqual(_read(final_path)[1], "from test")

    def test_trajectory_comes_from_the_optimization_result(self):
        _, traj_path = writer_xyz.write_optimization_outputs(
            self.tmp, SYMBOLS, COORDS, "c", self.result)
        lines = _read(traj_path)
        self.assertEqual(len(lines), 15)                      # 3ステップ × (2行+3原子)
        self.assertIn("-76.10000000", lines[11])

    def test_final_structure_may_differ_from_the_last_trajectory_frame(self):
        other = [[1.0, 1.0, 1.0]] * 3
        final_path, _ = writer_xyz.write_optimization_outputs(self.tmp, SYMBOLS, other, "c", self.result)
        self.assertIn("1.000000000000", _read(final_path)[2])


if __name__ == "__main__":
    unittest.main()
