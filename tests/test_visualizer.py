"""
tests/test_visualizer.py
--------------------------
qcapp.visualizer のうち、pyscf/py3Dmolを実際には呼ばない部分
(cubeファイルのテキストパース、電荷テーブルのHTML整形)だけを対象にした
単体テスト。isoval計算やMulliken電荷計算そのものはPySCFが必要なため、
Colab上での実機確認が必要(README.md参照)。
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qcapp import visualizer  # noqa: E402


_FAKE_CUBE = """orbital
comment
2 0.0 0.0 0.0
2 1.0 0.0 0.0
2 0.0 1.0 0.0
1 0.0 0.0 0.0 0.0
1 0.0 0.0 0.0 1.0
 0.01 -0.02
 0.5 -0.30
"""


class TestMaxAbsFromCubeFile(unittest.TestCase):
    def test_finds_correct_max_absolute_value(self):
        fd, path = tempfile.mkstemp(suffix=".cube")
        with os.fdopen(fd, "w") as f:
            f.write(_FAKE_CUBE)
        max_abs = visualizer._max_abs_from_cube_file(path)
        self.assertAlmostEqual(max_abs, 0.5)


class TestAtomicChargesTable(unittest.TestCase):
    def test_table_contains_all_atoms_with_signed_charges(self):
        charges = [("O", -0.45), ("H", 0.225), ("H", 0.225)]
        html = visualizer.atomic_charges_table_html(charges)
        self.assertIn("<table", html)
        self.assertIn("O", html)
        self.assertIn("-0.450", html)
        self.assertIn("+0.225", html)


if __name__ == "__main__":
    unittest.main()
