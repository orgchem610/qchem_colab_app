"""
tests/test_uma_notice_report.py
-------------------------------
uma_app.uma_notice(UMAに関する注意書き)と uma_app.uma_report(ログ本文の組み立て)の単体テスト。
どちらも文字列を作るだけで、UMA・ASE・ネットワークには依存しない。
"""

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uma_app import uma_notice, uma_report  # noqa: E402


class TestNotice(unittest.TestCase):
    def test_html_links_to_license_model_card_and_paper(self):
        html_text = uma_notice.notice_html()
        for url in (uma_notice.LICENSE_URL, uma_notice.MODEL_CARD_URL,
                    uma_notice.PAPER_URL, uma_notice.FAIRCHEM_URL):
            self.assertIn(f"href='{url}'", html_text)

    def test_html_states_the_nature_of_the_results_and_the_policy(self):
        html_text = uma_notice.notice_html()
        self.assertIn("高速な予測値", html_text)
        self.assertIn("Acceptable Use Policy", html_text)
        self.assertIn("論文", html_text)
        self.assertIn("同意能力", html_text)

    def test_citation_matches_the_paper_named_on_the_model_card(self):
        self.assertIn("UMA: A Family of Universal Models for Atoms", uma_notice.CITATION)
        self.assertIn("2506.23971", uma_notice.CITATION)
        self.assertTrue(uma_notice.PAPER_URL.endswith("2506.23971"))

    def test_plain_text_notice_contains_license_policy_and_citation(self):
        text = uma_notice.notice_text()
        self.assertIn(uma_notice.UMA_LICENSE_NAME, text)
        self.assertIn(uma_notice.LICENSE_URL, text)
        self.assertIn(uma_notice.MODEL_CARD_URL, text)
        self.assertIn(uma_notice.CITATION, text)

    def test_consent_label_mentions_license_and_policy(self):
        self.assertIn("FAIR Chemistry License", uma_notice.CONSENT_LABEL)
        self.assertIn("Acceptable Use Policy", uma_notice.CONSENT_LABEL)


def _opt_result(converged=True):
    return SimpleNamespace(
        optimizer_name="LBFGS", fmax_target=0.01, max_steps=500, converged=converged,
        energies=[-76.40, -76.42, -76.43], energies_ev=[-2079.0, -2079.5, -2079.8],
        fmax_history=[0.9, 0.2, 0.008], elapsed_seconds=3.2,
        final_fmax=0.008 if converged else 0.2)


def _freq_result():
    return SimpleNamespace(
        frequencies_cm1=[-35.0, 1600.5, 3700.2], elapsed_seconds=1.5,
        thermo_summary={"ZPE_Hartree": 0.0215, "ZPE_kcal_per_mol": 13.49},
        warning_message="虚振動が1個検出されました。")


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
