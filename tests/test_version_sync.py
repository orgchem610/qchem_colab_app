"""
tests/test_version_sync.py
--------------------------
バージョン番号(__version__)が、リポジトリ全体で1つの値になっていることを確認する。

__version__ はリポジトリ全体のリリース番号(Gitタグ)に合わせる決まりで、common_backend/version.py に
1か所だけ書いてある。pyscf_backend(PySCF版)と uma_backend(UMA版)の __version__ は、その値を
そのまま使えるようにした別名。過去に更新漏れ(タグはv0.1.16なのに __version__ は0.1.12のまま)が
あったため、別名が崩れて食い違うことがないかを、テストで確かめている。
新しいタグを打つ前に、このテストが通ることを確認すること。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app import pyscf_backend  # noqa: E402
from qchem_colab_app import uma_backend  # noqa: E402
from qchem_colab_app.common_backend import version  # noqa: E402


class TestVersionSync(unittest.TestCase):
    def test_both_packages_use_the_version_defined_in_common(self):
        self.assertEqual(pyscf_backend.__version__, version.__version__)
        self.assertEqual(uma_backend.__version__, version.__version__)

    def test_qcapp_and_uma_app_have_the_same_version(self):
        self.assertEqual(pyscf_backend.__version__, uma_backend.__version__)

    def test_version_looks_like_major_minor_patch(self):
        self.assertRegex(version.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
