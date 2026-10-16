"""
tests/test_uma_engine.py
------------------------
uma_app.uma_engine(デバイス・モデルの読み込み・Calculator)のうち、fairchem・torch・ネットワークを
使わない部分の単体テスト。fairchemは、代用のモジュールに差し替えて、
uma_hf(認証・例外)との受け渡しを確認する。
モデルの実際の読み込みと推論は、Colab上での実機確認が必要。
"""

import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uma_app import uma_engine, uma_hf  # noqa: E402


class TestDevice(unittest.TestCase):
    def test_cpu_description_mentions_the_slowness(self):
        self.assertIn("時間がかかります", uma_engine.describe_device("cpu"))


class GatedRepoError(Exception):
    """huggingface_hubの例外と同じ名前のダミー(クラス名で判定する実装のため)。"""


def _fake_fairchem(get_predict_unit):
    core = types.ModuleType("fairchem.core")
    core.pretrained_mlip = types.SimpleNamespace(get_predict_unit=get_predict_unit)
    package = types.ModuleType("fairchem")
    package.core = core
    return {"fairchem": package, "fairchem.core": core}


class TestLoadPredictor(unittest.TestCase):
    def setUp(self):
        uma_engine.clear_predictor_cache()
        self.addCleanup(uma_engine.clear_predictor_cache)

    def test_missing_fairchem_is_reported_as_a_setup_error(self):
        with mock.patch.dict(sys.modules, {"fairchem": None, "fairchem.core": None}):
            with self.assertRaises(uma_hf.UmaSetupError) as ctx:
                uma_engine.load_predictor("uma-s-1p2p1", "cpu")
        self.assertIn("fairchem-core", str(ctx.exception))

    def test_gated_repo_error_is_explained_as_a_setup_error(self):
        def raising(name, device):
            raise GatedRepoError("gated")

        with mock.patch.dict(sys.modules, _fake_fairchem(raising)):
            with self.assertRaises(uma_hf.UmaSetupError) as ctx:
                uma_engine.load_predictor("uma-s-1p2p1", "cpu")
        self.assertIn("利用条件に同意", str(ctx.exception))

    def test_other_errors_are_not_wrapped(self):
        def raising(name, device):
            raise RuntimeError("boom")

        with mock.patch.dict(sys.modules, _fake_fairchem(raising)):
            with self.assertRaises(RuntimeError) as ctx:
                uma_engine.load_predictor("uma-s-1p2p1", "cpu")
        self.assertNotIsInstance(ctx.exception, uma_hf.UmaSetupError)

    def test_the_same_model_and_device_are_loaded_only_once(self):
        calls = []

        def loading(name, device):
            calls.append((name, device))
            return object()

        with mock.patch.dict(sys.modules, _fake_fairchem(loading)):
            first = uma_engine.load_predictor("uma-s-1p2p1", "cpu")
            second = uma_engine.load_predictor("uma-s-1p2p1", "cpu")
            uma_engine.clear_predictor_cache()
            third = uma_engine.load_predictor("uma-s-1p2p1", "cpu")
        self.assertIs(first, second)
        self.assertIsNot(first, third)
        self.assertEqual(len(calls), 2)


class TestModuleSplit(unittest.TestCase):
    def test_authentication_names_are_not_in_uma_engine_any_more(self):
        for name in ("UmaSetupError", "login_with_token", "login_from_environment", "has_hf_token",
                     "explain_hf_error", "check_model_access", "MODEL_REPO_ID", "HF_TOKEN_ENV",
                     "LICENSE_FILENAME"):
            self.assertTrue(hasattr(uma_hf, name), name)
            self.assertFalse(hasattr(uma_engine, name), name)

    def test_device_model_and_atoms_functions_remain_in_uma_engine(self):
        for name in ("get_device", "describe_device", "load_predictor", "clear_predictor_cache",
                     "make_calculator", "build_atoms"):
            self.assertTrue(hasattr(uma_engine, name), name)
            self.assertFalse(hasattr(uma_hf, name), name)



if __name__ == "__main__":
    unittest.main()
