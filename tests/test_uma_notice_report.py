"""
tests/test_uma_notice_report.py
-------------------------------
uma_backend.uma_notice(UMAに関する注意書き)と uma_backend.uma_report(ログ本文の組み立て)の単体テスト。
どちらも文字列を作るだけで、UMA・ASE・ネットワークには依存しない。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import vibration  # noqa: E402
from qchem_colab_app.uma_backend import uma_notice, uma_optimize, uma_report  # noqa: E402


class TestNotice(unittest.TestCase):
    def test_primary_source_urls_are_the_expected_ones(self):
        self.assertEqual(uma_notice.LICENSE_URL, "https://huggingface.co/facebook/UMA/blob/main/LICENSE")
        self.assertEqual(uma_notice.MODEL_CARD_URL, "https://huggingface.co/facebook/UMA")
        self.assertEqual(uma_notice.PAPER_URL, "https://arxiv.org/abs/2506.23971")

    def test_citation_matches_the_paper_named_on_the_model_card(self):
        self.assertIn("UMA: A Family of Universal Models for Atoms", uma_notice.CITATION)
        self.assertIn("2506.23971", uma_notice.CITATION)
        self.assertTrue(uma_notice.PAPER_URL.endswith("2506.23971"))

    def test_plain_text_notice_links_to_the_primary_sources(self):
        text = uma_notice.notice_text()
        for expected in (uma_notice.UMA_LICENSE_NAME, uma_notice.LICENSE_URL,
                         uma_notice.MODEL_CARD_URL, uma_notice.CITATION, uma_notice.PAPER_URL):
            self.assertIn(expected, text)

    def test_notice_asks_for_the_citation_without_adding_interpretation(self):
        text = uma_notice.notice_text()
        self.assertIn("以下の論文を引用してください", text)
        # ライセンスの条文の解釈・助言にあたる語は含めない(一次情報を読んで利用者が判断する)
        for interpretation in ("同意能力", "未成年", "義務", "予測値", "誤差"):
            self.assertNotIn(interpretation, text)

    def test_gui_only_notice_helpers_are_gone(self):
        # GUIには表示しない(ノートブック冒頭にだけ表示する)方針のため、GUI用の関数・定数は持たない
        for name in ("notice_html", "CONSENT_LABEL", "RESULT_NATURE"):
            self.assertFalse(hasattr(uma_notice, name), name)


def _opt_result(converged=True):
    # 代用品ではなく実物を使う(FrequencyResultと同じ理由)。最終の力の最大値(final_fmax)は、fmax_historyの最後の値
    result = uma_optimize.OptimizationResult()
    result.optimizer_name = "LBFGS"
    result.fmax_target = 0.01
    result.max_steps = 500
    result.converged = converged
    result.energies = [-76.40, -76.42, -76.43]
    result.energies_ev = [-2079.0, -2079.5, -2079.8]
    result.fmax_history = [0.9, 0.2, 0.008] if converged else [0.9, 0.5, 0.2]
    result.elapsed_seconds = 3.2
    return result


def _freq_result():
    # 代用品(SimpleNamespace)ではなく実物を使う: 属性名の変更に、テストが追従できる(AGENTS.mdの「関連テスト」でも検出できる)
    result = vibration.FrequencyResult()
    result.frequencies_cm1 = [-35.0, 1600.5, 3700.2]
    result.elapsed_seconds = 1.5
    result.zpe_hartree = 0.0215
    result.warning_message = "虚振動が1個検出されました。"
    return result


def _build(**overrides):
    kwargs = dict(
        version="0.2.0", model_key="uma-s-1p2p1", task_name="omol",
        device_label="GPU(Tesla T4)", input_filename="water.xyz", charge=0, multiplicity=1,
        opt_result=_opt_result(), freq_result=_freq_result(), total_seconds=5.0)
    kwargs.update(overrides)
    return uma_report.build_log_text(**kwargs)


class TestReport(unittest.TestCase):
    def test_header_contains_conditions(self):
        text = _build()
        for expected in ("v0.2.0", "water.xyz", "uma-s-1p2p1", "omol", "GPU(Tesla T4)",
                         "LBFGS", "収束しました"):
            self.assertIn(expected, text)

    def test_history_table_has_one_row_per_step_with_relative_energy(self):
        text = _build()
        self.assertIn("[最適化の履歴]", text)
        # 最終ステップの相対エネルギーは0
        self.assertRegex(text, r"\n\s+2\s+-76\.43000000\s+0\.000\s+0\.00800")

    def test_not_converged_is_stated_clearly(self):
        text = _build(opt_result=_opt_result(converged=False))
        self.assertIn("収束しませんでした", text)

    def test_frequencies_zpe_and_warning_are_included(self):
        text = _build()
        self.assertIn("-35.00", text)
        self.assertIn("3700.20", text)
        self.assertIn("ゼロ点エネルギー", text)
        self.assertIn("虚振動が1個検出されました。", text)

    def test_zpe_is_shown_in_hartree_and_kcal_per_mol(self):
        text = _build()
        self.assertIn("ゼロ点エネルギー(ZPE): 0.021500 Hartree(13.49 kcal/mol)", text)

    def test_zpe_line_is_omitted_when_it_was_not_calculated(self):
        result = _freq_result()
        result.zpe_hartree = None
        text = _build(freq_result=result)
        self.assertIn("3700.20", text)
        self.assertNotIn("ゼロ点エネルギー", text)

    def test_frequency_section_is_omitted_when_not_calculated(self):
        text = _build(freq_result=None)
        self.assertNotIn("[振動数", text)

    def test_notice_is_always_appended(self):
        text = _build(freq_result=None)
        self.assertIn(uma_notice.CITATION, text)
        self.assertIn(uma_notice.LICENSE_URL, text)

    def test_no_secrets_are_written(self):
        os.environ["HF_TOKEN"] = "hf_secret_for_test"
        try:
            self.assertNotIn("hf_secret_for_test", _build())
        finally:
            os.environ.pop("HF_TOKEN", None)


if __name__ == "__main__":
    unittest.main()
