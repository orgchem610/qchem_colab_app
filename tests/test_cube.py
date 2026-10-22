"""
tests/test_cube.py
------------------
common_backend.cube.max_abs_value(cubeファイルの格子点上の値の最大絶対値)の単体テスト。
PySCFがなくても、cubeファイルのテキストだけで確認できる。
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import cube  # noqa: E402

# cube形式のヘッダー: コメント2行 + 「原子数と原点」1行 + 軸3行 + 原子2行(原子数2のとき)
_HEADER = """orbital
comment
2 0.0 0.0 0.0
1 1.0 0.0 0.0
1 0.0 1.0 0.0
1 0.0 0.0 1.0
1 0.0 0.0 0.0 0.0
1 0.0 0.0 0.0 1.0
"""


class TestMaxAbsValue(unittest.TestCase):
    def _write(self, body, header=_HEADER):
        fd, path = tempfile.mkstemp(suffix=".cube")
        with os.fdopen(fd, "w") as f:
            f.write(header + body)
        self.addCleanup(os.remove, path)
        return path

    def test_finds_correct_max_absolute_value(self):
        path = self._write(" 0.01 -0.02\n 0.5 -0.30\n")
        self.assertAlmostEqual(cube.max_abs_value(path), 0.5)

    def test_a_negative_value_can_be_the_maximum(self):
        path = self._write(" 0.01 -0.7\n 0.5 -0.30\n")
        self.assertAlmostEqual(cube.max_abs_value(path), 0.7)

    def test_the_header_values_are_not_counted(self):
        # 原子の行にある座標(0.0, 1.0)や電荷が、格子点の値として混ざらないこと
        path = self._write(" 0.01 -0.02\n")
        self.assertAlmostEqual(cube.max_abs_value(path), 0.02)

    def test_file_without_values_returns_zero(self):
        self.assertEqual(cube.max_abs_value(self._write("")), 0.0)

    def test_negative_atom_count_in_the_header_is_handled(self):
        # 原子数が負の値のcube(軌道データ用)でも、絶対値で読み飛ばす行数を数える
        header = _HEADER.replace("2 0.0 0.0 0.0\n", "-2 0.0 0.0 0.0\n", 1)
        path = self._write(" 0.25\n", header)
        self.assertAlmostEqual(cube.max_abs_value(path), 0.25)


if __name__ == "__main__":
    unittest.main()
