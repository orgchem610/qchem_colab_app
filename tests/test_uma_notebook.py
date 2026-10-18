"""
tests/test_uma_notebook.py
--------------------------
ColabApp_UMA.ipynb の構成と、書いてはいけないもの(トークン・出力・解釈を加えた文面)の確認。
ノートブックをColabで編集・保存し直したときに、うっかり壊れていないかを検知するためのテスト。
Colab上での実際の動作の確認の代わりにはならない。
"""

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uma_backend import uma_notice  # noqa: E402

NOTEBOOK = os.path.join(os.path.dirname(__file__), "..", "ColabApp_UMA.ipynb")


def _load():
    with open(NOTEBOOK, encoding="utf-8") as f:
        nb = json.load(f)
    for index, cell in enumerate(nb["cells"]):
        cell["text"] = "".join(cell["source"])
        cell["index"] = index
    return nb


class TestMetadata(unittest.TestCase):
    def setUp(self):
        self.nb = _load()

    def test_runtime_version_and_gpu_are_recorded(self):
        meta = self.nb["metadata"]
        self.assertEqual(meta["accelerator"], "GPU")
        self.assertEqual(meta["colab"]["gpuType"], "T4")
        self.assertEqual(meta["colab"]["runtime_attributes"]["runtime_version"], "2026.07")

    def test_cell_ids_are_unique(self):
        ids = [c["id"] for c in self.nb["cells"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_outputs_are_saved(self):
        # Colabで実行した後に保存すると、出力(トークンの入力欄の表示など)が残りうるため
        for cell in self.nb["cells"]:
            if cell["cell_type"] == "code":
                self.assertEqual(cell["outputs"], [], f"cell {cell['index']}")
                self.assertIsNone(cell["execution_count"], f"cell {cell['index']}")

    def test_every_code_cell_is_valid_python(self):
        for cell in self.nb["cells"]:
            if cell["cell_type"] == "code":
                lines = [ln for ln in cell["text"].splitlines() if not ln.lstrip().startswith(("!", "%"))]
                compile("\n".join(lines), f"cell{cell['index']}", "exec")


class TestNoSecrets(unittest.TestCase):
    def setUp(self):
        self.nb = _load()

    def test_no_token_like_strings_anywhere(self):
        for cell in self.nb["cells"]:
            self.assertIsNone(re.search(r"hf_[A-Za-z0-9]{12,}", cell["text"]), f"cell {cell['index']}")

    def test_only_harmless_form_fields_exist(self):
        # トークンを入れる欄を #@param(フォーム)にすると、値がノートブックのファイルに保存されてしまう
        names = []
        for cell in self.nb["cells"]:
            names += re.findall(r"^\s*([A-Za-z_]\w*)\s*=.*#@param", cell["text"], re.M)
        self.assertEqual(sorted(names), ["BRANCH", "FORCE_REENTER"])


class TestTokenAndAccessCell(unittest.TestCase):
    def setUp(self):
        self.nb = _load()
        self.code = [c for c in self.nb["cells"] if c["cell_type"] == "code"]
        self.token_cells = [c for c in self.code if "getpass" in c["text"]]

    def test_there_is_exactly_one_cell_for_token_input_and_access_check(self):
        self.assertEqual(len(self.token_cells), 1)
        cell = self.token_cells[0]
        self.assertEqual(sum("check_model_access" in c["text"] for c in self.code), 1)
        self.assertIn("login_from_environment", cell["text"])
        self.assertIn("check_model_access", cell["text"])

    def test_token_is_passed_through_the_environment_variable_and_not_kept(self):
        text = self.token_cells[0]["text"]
        self.assertIn('os.environ["HF_TOKEN"] = _token', text)
        self.assertTrue(text.index("_token = None                                 # 変数にトークンを残さない")
                        > text.index('os.environ["HF_TOKEN"] = _token'))
        self.assertNotRegex(text, r"print\([^)]*_token")

    def test_cell_comes_after_the_code_is_fetched_and_before_the_install(self):
        cell = self.token_cells[0]
        clone = next(c for c in self.code if "git" in c["text"] and "clone" in c["text"])
        path_cell = next(c for c in self.code if "sys.path.append" in c["text"])
        install = next(c for c in self.code if "pip" in c["text"] and "install" in c["text"])
        self.assertLess(clone["index"], cell["index"])
        self.assertLess(path_cell["index"], cell["index"])     # uma_backend をimportするために必要
        self.assertLess(cell["index"], install["index"])

    def test_the_separate_access_check_cell_is_gone(self):
        titles = [c["text"].splitlines()[0] for c in self.code if c["text"].startswith("#@title")]
        self.assertEqual(sum("アクセス" in t for t in titles), 1)


class TestLicenseNotice(unittest.TestCase):
    def setUp(self):
        self.nb = _load()
        self.intro = self.nb["cells"][0]["text"]
        self.all_markdown = "\n".join(c["text"] for c in self.nb["cells"] if c["cell_type"] == "markdown")

    def test_intro_links_to_the_same_primary_sources_as_uma_notice(self):
        for expected in (uma_notice.LICENSE_URL, uma_notice.MODEL_CARD_URL,
                         uma_notice.PAPER_URL, uma_notice.FAIRCHEM_URL):
            self.assertIn(expected, self.intro)

    def test_intro_asks_for_the_citation_given_on_the_model_card(self):
        self.assertIn("以下の論文を引用してください", self.intro)
        self.assertIn("Wood, B. M. et al.", self.intro)
        self.assertIn("UMA: A Family of Universal Models for Atoms", self.intro)
        self.assertIn("arXiv:2506.23971", self.intro)

    def test_notebook_adds_no_interpretation_of_the_license(self):
        for interpretation in ("同意能力", "未成年", "を守ってください", "明記してください"):
            self.assertNotIn(interpretation, self.all_markdown)

    def test_no_consent_checkbox_is_mentioned(self):
        self.assertNotIn("同意済みです", self.all_markdown)

    def test_license_information_is_only_in_the_intro_cell(self):
        # ライセンスの情報(文面)は、冒頭の1つのセルにまとめる
        cells_with_citation = [c["index"] for c in self.nb["cells"] if "Wood, B. M." in c["text"]]
        self.assertEqual(cells_with_citation, [0])


if __name__ == "__main__":
    unittest.main()
