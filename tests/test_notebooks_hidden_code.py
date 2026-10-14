"""
tests/test_notebooks_hidden_code.py
-----------------------------------
ColabApp.ipynb / ColabApp_UMA.ipynb の、コードセルがすべて「フォーム表示(コード非表示)」に
なっていることの確認。エンドユーザーがコードを見ずに、各セルの題名だけを見て実行できるようにするため。

Colabでは、セルのメタデータ "cellView": "form" と、先頭行の「#@title 題名」の両方があると、
コードが折りたたまれて題名だけが表示される(クリックすると開ける)。
ノートブックをColabで編集・保存し直したときに、うっかりこの設定が外れていないかを検知する。
Colab上での実際の表示の確認の代わりにはならない。
"""

import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NOTEBOOKS = ("ColabApp.ipynb", "ColabApp_UMA.ipynb")


def _code_cells(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        nb = json.load(f)
    return [(i, c) for i, c in enumerate(nb["cells"]) if c["cell_type"] == "code"]


class TestCodeIsHiddenByDefault(unittest.TestCase):
    def test_every_code_cell_is_shown_as_a_form(self):
        for name in NOTEBOOKS:
            for index, cell in _code_cells(name):
                self.assertEqual(cell["metadata"].get("cellView"), "form", f"{name} cell {index}")

    def test_every_code_cell_starts_with_a_title_line(self):
        for name in NOTEBOOKS:
            for index, cell in _code_cells(name):
                first = "".join(cell["source"]).splitlines()[0]
                self.assertRegex(first, r"^#@title \S", f"{name} cell {index}")

    def test_titles_are_unique_within_a_notebook(self):
        for name in NOTEBOOKS:
            titles = ["".join(c["source"]).splitlines()[0] for _, c in _code_cells(name)]
            self.assertEqual(len(titles), len(set(titles)), name)

    def test_cell_ids_are_kept(self):
        for name in NOTEBOOKS:
            for index, cell in _code_cells(name):
                self.assertTrue(cell["metadata"].get("id"), f"{name} cell {index}")


if __name__ == "__main__":
    unittest.main()
