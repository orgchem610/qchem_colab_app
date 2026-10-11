"""
tests/test_version_sync.py
--------------------------
qcapp(PySCF版)と uma_app(UMA版)の __version__ が、同じ値になっていることを確認する。

__version__ はリポジトリ全体のリリース番号(Gitタグ)に合わせる決まりだが、
過去に更新漏れ(タグはv0.1.16なのに __version__ は0.1.12のまま)があったため、
少なくとも2つのパッケージ間の食い違いはテストで気づけるようにしている。
新しいタグを打つ前に、このテストが通ることを確認すること。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import qcapp  # noqa: E402
import uma_app  # noqa: E402


class TestVersionSync(unittest.TestCase):
    def test_qcapp_and_uma_app_have_the_same_version(self):
        self.assertEqual(qcapp.__version__, uma_app.__version__)

    def test_version_looks_like_major_minor_patch(self):
        self.assertRegex(uma_app.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
