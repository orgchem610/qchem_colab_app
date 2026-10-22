"""
tests/test_version_sync.py
--------------------------
バージョン番号(__version__)が、リポジトリ全体で1か所(common_backend/version.py)だけに定義されていることの確認。

__version__ はリポジトリ全体のリリース番号(Gitタグ)に合わせる決まりで、画面・UMA版の計算ログ・READMEとの整合検査は、
common_backend.version を直接importして使う。pyscf_backend・uma_backend には別名を置かない(定義が複数あると、
更新漏れによる食い違いが起きうるため)。README冒頭の表示との一致は、tests/test_readme.py が確認する。
新しいタグを打つ前に、このテストが通ることを確認すること。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app import pyscf_backend, uma_backend  # noqa: E402
from qchem_colab_app.common_backend import version  # noqa: E402


class TestVersion(unittest.TestCase):
    def test_version_looks_like_major_minor_patch(self):
        self.assertRegex(version.__version__, r"^\d+\.\d+\.\d+$")

    def test_the_backends_do_not_define_their_own_version(self):
        for package in (pyscf_backend, uma_backend):
            self.assertFalse(hasattr(package, "__version__"), package.__name__)


if __name__ == "__main__":
    unittest.main()
