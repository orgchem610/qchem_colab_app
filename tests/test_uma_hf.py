"""
tests/test_uma_hf.py
--------------------
uma_backend.uma_hf(Hugging Faceのトークン管理・アクセス権の確認)のうち、
huggingface_hub・ネットワークを使わない部分(エラーメッセージの整形・トークンの確認)の単体テスト。
Hugging Faceからの実際の取得は、Colab上での実機確認が必要。
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.uma_backend import uma_hf  # noqa: E402


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
        message = uma_hf.explain_hf_error(GatedRepoError("gated"))
        self.assertIn("利用条件に同意", message)
        self.assertIn("facebook/UMA", message)

    def test_401_and_403_are_treated_as_access_problems(self):
        for status in (401, 403):
            self.assertIn("利用条件に同意", uma_hf.explain_hf_error(_HttpError(status)))

    def test_server_errors_are_treated_as_connection_problems(self):
        self.assertIn("接続できませんでした", uma_hf.explain_hf_error(_HttpError(503)))

    def test_unknown_errors_keep_the_original_message(self):
        message = uma_hf.explain_hf_error(RuntimeError("boom"))
        self.assertIn("boom", message)
        self.assertIn("RuntimeError", message)


class TestTokenHandling(unittest.TestCase):
    def test_empty_token_is_rejected(self):
        for token in ("", "   ", None):
            with self.assertRaises(uma_hf.UmaSetupError):
                uma_hf.login_with_token(token)

    def test_missing_token_is_reported_before_any_download(self):
        with mock.patch.object(uma_hf, "has_hf_token", return_value=False):
            with self.assertRaises(uma_hf.UmaSetupError) as ctx:
                uma_hf.check_model_access()
        self.assertIn("トークン", str(ctx.exception))

    def test_has_hf_token_reads_the_environment_variable(self):
        with mock.patch.dict(os.environ, {"HF_TOKEN": "hf_dummy"}):
            self.assertTrue(uma_hf.has_hf_token())


class TestLoginFromEnvironment(unittest.TestCase):
    def test_missing_token_in_environment_raises_a_helpful_error(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HF_TOKEN", None)
            with self.assertRaises(uma_hf.UmaSetupError) as ctx:
                uma_hf.login_from_environment()
        self.assertIn("2.", str(ctx.exception))
        self.assertIn("トークン", str(ctx.exception))

    def test_blank_token_in_environment_is_rejected(self):
        with mock.patch.dict(os.environ, {"HF_TOKEN": "   "}):
            with self.assertRaises(uma_hf.UmaSetupError):
                uma_hf.login_from_environment()

    def test_token_from_environment_is_passed_to_the_login_function(self):
        with mock.patch.dict(os.environ, {"HF_TOKEN": "hf_dummy_value"}):
            with mock.patch.object(uma_hf, "login_with_token") as fake_login:
                uma_hf.login_from_environment()
        fake_login.assert_called_once_with("hf_dummy_value")

    def test_token_is_not_kept_in_any_module_level_variable(self):
        token = "hf_must_not_be_kept_anywhere"
        with mock.patch.dict(os.environ, {"HF_TOKEN": token}):
            with mock.patch.object(uma_hf, "login_with_token"):
                uma_hf.login_from_environment()
        kept = [name for name, value in vars(uma_hf).items()
                if isinstance(value, str) and token in value]
        self.assertEqual(kept, [])

    def test_error_messages_never_contain_the_token(self):
        token = "hf_secret_in_error_test"
        with mock.patch.dict(os.environ, {"HF_TOKEN": token}):
            message = uma_hf.explain_hf_error(GatedRepoError("gated"))
        self.assertNotIn(token, message)


if __name__ == "__main__":
    unittest.main()
