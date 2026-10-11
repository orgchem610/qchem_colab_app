"""
tests/test_uma_engine.py
------------------------
uma_app.uma_engine のうち、fairchem・torch・ネットワークを使わない部分
(エラーメッセージの整形・トークンの確認)の単体テスト。
Hugging Faceからの実際の取得やモデルの読み込みは、Colab上での実機確認が必要。
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uma_app import uma_engine  # noqa: E402


class GatedRepoError(Exception):
    """huggingface_hubの例外と同じ名前のダミー(クラス名で判定する実装のため)。"""


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class _HttpError(Exception):
    def __init__(self, status_code):
        super().__init__(f"HTTP {status_code}")
        self.response = _FakeResponse(status_code)


class TestExplainHfError(unittest.TestCase):
    def test_gated_repo_error_explains_license_acceptance(self):
        message = uma_engine.explain_hf_error(GatedRepoError("gated"))
        self.assertIn("利用条件に同意", message)
        self.assertIn("facebook/UMA", message)

    def test_401_and_403_are_treated_as_access_problems(self):
        for status in (401, 403):
            self.assertIn("利用条件に同意", uma_engine.explain_hf_error(_HttpError(status)))

    def test_server_errors_are_treated_as_connection_problems(self):
        self.assertIn("接続できませんでした", uma_engine.explain_hf_error(_HttpError(503)))

    def test_unknown_errors_keep_the_original_message(self):
        message = uma_engine.explain_hf_error(RuntimeError("boom"))
        self.assertIn("boom", message)
        self.assertIn("RuntimeError", message)


class TestTokenHandling(unittest.TestCase):
    def test_empty_token_is_rejected(self):
        for token in ("", "   ", None):
            with self.assertRaises(uma_engine.UmaSetupError):
                uma_engine.login_with_token(token)

    def test_missing_token_is_reported_before_any_download(self):
        with mock.patch.object(uma_engine, "has_hf_token", return_value=False):
            with self.assertRaises(uma_engine.UmaSetupError) as ctx:
                uma_engine.check_model_access()
        self.assertIn("トークン", str(ctx.exception))

    def test_has_hf_token_reads_the_environment_variable(self):
        with mock.patch.dict(os.environ, {"HF_TOKEN": "hf_dummy"}):
            self.assertTrue(uma_engine.has_hf_token())


class TestDevice(unittest.TestCase):
    def test_cpu_description_mentions_the_slowness(self):
        self.assertIn("時間がかかります", uma_engine.describe_device("cpu"))


if __name__ == "__main__":
    unittest.main()
