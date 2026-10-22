"""
tests/test_agents_spec.py
-------------------------
AGENTS.md の仕様書が、ソースとテストの現状と合っているかの検査。
AGENTS.md は main ブランチでは管理対象外のため、ファイルがないときは、すべてスキップする。

検査すること:
    1. ソースの関数・クラス・メソッド・プロパティ・公開定数のすべてに、仕様書の項目がある(逆も同じ)
    2. 仕様書の「呼出先」「呼出元」「関連テスト」の行が、ソースとテストの構文解析の結果と一致する
    3. tests/ のすべてのテストファイルに、仕様書の tests 節の項目がある(逆も同じ)

2 が失敗したときは、`python3 tests/spec_analysis.py --fix` で、該当の行を最新にできる。
1・3 が失敗したときは、仕様書の項目(引数・目的など)を、手で書き足す・消す。
"""

import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec_analysis  # noqa: E402

AGENTS_PATH = os.path.join(ROOT, "AGENTS.md")


@unittest.skipUnless(os.path.exists(AGENTS_PATH), "AGENTS.mdがない(mainブランチ)ためスキップ")
class TestAgentsSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(AGENTS_PATH, encoding="utf-8") as f:
            cls.text = f.read()
        cls.spec = spec_analysis.Spec(ROOT)
        cls.updated, cls.found, cls.problems = spec_analysis.update_agents(cls.spec, cls.text)

    def test_every_entry_has_a_definition(self):
        self.assertEqual(self.problems, [], "ソースにない定義の項目が、仕様書にある")

    def test_every_definition_has_an_entry(self):
        missing = sorted(set(self.spec.nodes) - self.found)
        self.assertEqual(missing, [], "仕様書に項目がない定義(引数・戻り値・目的などを書き足す)")

    def test_call_and_test_lines_are_up_to_date(self):
        old_lines, new_lines = self.text.split("\n"), self.updated.split("\n")
        stale = [new for old, new in zip(old_lines, new_lines) if old != new]
        self.assertEqual(
            self.updated, self.text,
            "「呼出先」「呼出元」「関連テスト」の行が古い(約%d行)。"
            "`python3 tests/spec_analysis.py --fix` で更新できる" % len(stale))

    def test_every_test_file_has_an_entry_in_the_tests_section(self):
        start = self.text.index("### tests")
        section = self.text[start:]
        nxt = re.search(r"\n### ", section[4:])
        section = section[:nxt.start() + 4] if nxt else section
        listed = set(re.findall(r"^- `(test_[A-Za-z0-9_]+\.py)`", section, re.M))
        actual = {f for f in os.listdir(os.path.dirname(os.path.abspath(__file__)))
                  if f.startswith("test_") and f.endswith(".py")}
        self.assertEqual(sorted(actual - listed), [], "仕様書の tests 節に項目がないテストファイル")
        self.assertEqual(sorted(listed - actual), [], "tests/ にない、仕様書の tests 節の項目")


if __name__ == "__main__":
    unittest.main()
