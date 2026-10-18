"""
tests/test_readme.py
--------------------
ルートの README.md が、コードの現状とずれていないかの確認。
(過去に、コードは v0.1.17 なのに README が v0.1.15 のまま、という食い違いがあったため。)
README の内容そのものの正しさではなく、機械的に確かめられる範囲(バージョン・リンク・
書かれているファイルの存在)だけを検査する。
"""

import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import pyscf_backend  # noqa: E402
import uma_backend  # noqa: E402

# READMEに書かれているが、リポジトリにファイルとしては存在しなくてよいもの
NOT_IN_REPO = {
    "CHANGELOG.md",              # 廃止済みであることの説明として登場する
    "ColabReaction.ipynb",       # 参考にした外部のノートブック
    "requirements-lock.txt",     # Colab上で自動生成される(Git管理対象外)
    "requirements-uma-lock.txt",  # 同上
    "pyscf_backend/dispatch.py",         # 設計方針メモに登場する、将来の例
}


def _readme():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        return f.read()


def _repo_basenames():
    names = set()
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
        names.update(filenames)
    return names


class TestReadme(unittest.TestCase):
    def setUp(self):
        self.text = _readme()

    def test_current_version_matches_the_code(self):
        header = "\n".join(self.text.splitlines()[:30])
        self.assertIn(f"v{pyscf_backend.__version__}", header)
        self.assertEqual(pyscf_backend.__version__, uma_backend.__version__)

    def test_code_fences_are_balanced(self):
        self.assertEqual(self.text.count("```") % 2, 0)

    def test_relative_links_point_to_existing_files(self):
        for link in re.findall(r"\]\(([^)]+)\)", self.text):
            if link.startswith(("http", "#")):
                continue
            self.assertTrue(os.path.exists(os.path.join(ROOT, link.split("#")[0])), link)

    def test_both_notebooks_are_linked_and_exist(self):
        for notebook in ("ColabApp.ipynb", "ColabApp_UMA.ipynb"):
            self.assertIn(f"/blob/main/{notebook}", self.text)
            self.assertTrue(os.path.exists(os.path.join(ROOT, notebook)), notebook)

    def test_files_mentioned_in_backticks_exist(self):
        basenames = _repo_basenames()
        tokens = set(re.findall(r"`([A-Za-z0-9_./-]+\.(?:py|yaml|ipynb|md|txt))`", self.text))
        missing = []
        for token in sorted(tokens):
            if token in NOT_IN_REPO or token.startswith("."):
                continue
            if "/" in token:
                ok = os.path.exists(os.path.join(ROOT, token))
            else:
                ok = token in basenames
            if not ok:
                missing.append(token)
        self.assertEqual(missing, [], "READMEに書かれているが、存在しないファイル")

    def test_removed_files_are_not_mentioned_as_existing(self):
        self.assertNotIn("build_notebook.py", self.text)


if __name__ == "__main__":
    unittest.main()
